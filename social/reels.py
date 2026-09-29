"""Render vertical reels (1080x1920 MP4, H.264 + AAC) in the Barur visual language.

  python3 social/reels.py counter social/video/<name>.mp4

Each template is an HTML page with a deterministic window.renderFrame(t) (t in seconds),
screenshotted frame by frame and piped into ffmpeg. Sound is generated here (no licensed
music): a short tick per beat, and a soft tone under the end card. When licensed tracks
are available, pass --music path.mp3 to mix one underneath.

Also writes a cover image next to the video (<name>-cover.jpg) for Instagram.
Reel safe zones: keep key text out of the top ~220px and bottom ~420px (Instagram UI).
"""

import argparse
import json
import subprocess
import wave
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
A = (ROOT / "assets").as_uri()
FPS = 30
W, H = 1080, 1920
SR = 44100


# ---------- template: "המונה" (the counter) ----------

def counter_schedule():
    n, t0, span = 44, 1.2, 7.8
    return [round(t0 + span * (i / (n - 1)) ** 0.6, 3) for i in range(n)]


def counter_html():
    beats = counter_schedule()
    items = "".join('<span class="it">עוד 14 ₪.</span>' for _ in beats)
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-400.woff2);font-weight:400}}
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-600.woff2);font-weight:600}}
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-700.woff2);font-weight:700}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:#0F2A47;color:#F5F3EE;font-family:Plex,Arial,sans-serif;overflow:hidden;position:relative}}
.layer{{position:absolute;inset:0;padding:230px 90px 420px}}
.label{{font-size:40px;font-weight:600;color:#4FB3A2;line-height:1.35}}
.block{{margin-top:48px;font-size:48px;font-weight:700;line-height:1.45;max-height:780px;overflow:hidden}}
.it{{display:inline-block;width:25%;opacity:0;white-space:nowrap}}
.total{{position:absolute;right:90px;left:90px;bottom:430px;display:flex;justify-content:space-between;align-items:baseline;border-top:3px solid #2A4563;padding-top:24px}}
.total small{{font-size:36px;color:#AEB8C4;font-weight:600}}
.total b{{font-size:96px;color:#4FB3A2;font-variant-numeric:tabular-nums}}
#punch{{display:flex;flex-direction:column;justify-content:center;gap:28px;opacity:0}}
#punch .big{{font-size:150px;font-weight:700;color:#4FB3A2;line-height:1}}
#punch .t{{font-size:64px;font-weight:700;line-height:1.3}}
#punch .s{{font-size:40px;color:#AEB8C4}}
#end{{background:#F5F3EE;color:#0F2A47;display:flex;flex-direction:column;justify-content:center;gap:40px;opacity:0}}
#end h1{{font-size:118px;line-height:1.1;font-weight:700}}
#end .sub{{font-size:46px;color:#7C8794;line-height:1.4}}
#end .cta{{font-size:44px;font-weight:600;color:#11978A;direction:ltr;text-align:right}}
#end img{{height:120px;align-self:flex-start;margin-top:30px}}
#end .fine{{position:absolute;bottom:330px;right:90px;left:90px;font-size:26px;color:#7C8794}}
</style></head><body>
<div class="layer" id="count">
  <div class="label">משכנתה של מיליון ₪.<br>פער ריבית של 0.75%.</div>
  <div class="block" id="block">{items}</div>
</div>
<div class="total" id="totalRow"><small>יצא מהכיס עד עכשיו</small><b id="total">0 ₪</b></div>
<div class="layer" id="punch"><div class="t">וזה ממשיך כל יום,<br>עד סוף המשכנתה.</div><div class="big">כ-128,000 ₪</div><div class="s">לאורך 25 שנה.</div></div>
<div class="layer" id="end"><h1>הבנק לא יגיד.<br>הבדיקה כן.</h1><div class="sub">3 דקות. בלי מסמכים.<br>אם לא משתלם, נגיד לך.</div>
  <div class="cta">barur-mashkanta.co.il/check</div><img src="{A}/img/logo-horizontal-color.svg">
  <div class="fine">להמחשה: משכנתה של מיליון ₪, 25 שנה, פער ריבית של 0.75%.</div></div>
<script>
const beats = {json.dumps(beats)};
const its = [...document.querySelectorAll('.it')];
const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);
window.renderFrame = (t) => {{
  let shown = 0;
  its.forEach((el, i) => {{
    const k = ease((t - beats[i]) / 0.14);
    if (t >= beats[i]) shown++;
    el.style.opacity = k;
    el.style.transform = `translateY(${{(1 - k) * 18}}px)`;
  }});
  document.getElementById('total').textContent = (shown * 14).toLocaleString('en-US') + ' ₪';
  const dim = 1 - 0.93 * ease((t - 9.3) / 0.6);
  document.getElementById('count').style.opacity = dim;
  document.getElementById('totalRow').style.opacity = dim;
  const p = ease((t - 9.6) / 0.5) * (1 - ease((t - 12.6) / 0.4));
  const pe = document.getElementById('punch');
  pe.style.opacity = p; pe.style.transform = `translateY(${{(1 - ease((t - 9.6) / 0.5)) * 30}}px)`;
  document.getElementById('end').style.opacity = ease((t - 12.8) / 0.4);
}};
</script></body></html>"""


def counter_audio(duration):
    """Clock-like ticks on every beat, a soft two-note tone under the end card."""
    n = int(duration * SR)
    out = np.zeros(n, dtype=np.float64)
    tick_len = int(0.035 * SR)
    tt = np.arange(tick_len) / SR
    tick = np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 160) * 0.5
    tick += np.sin(2 * np.pi * 1150 * tt) * np.exp(-tt * 120) * 0.25
    for b in counter_schedule():
        i = int(b * SR)
        out[i:i + tick_len] += tick[: max(0, min(tick_len, n - i))]
    # low swell under the punchline, then a warm resolve on the end card
    for start, freqs, length, gain in ((9.6, (110, 165), 3.0, 0.12), (12.8, (220, 330, 440), 3.4, 0.10)):
        m = int(length * SR)
        tt = np.arange(m) / SR
        env = np.minimum(1, tt / 0.25) * np.exp(-tt * 0.9)
        tone = sum(np.sin(2 * np.pi * f * tt) for f in freqs) / len(freqs) * env * gain
        i = int(start * SR)
        out[i:i + m] += tone[: max(0, min(m, n - i))]
    out = np.clip(out, -1, 1)
    return (out * 32767).astype(np.int16)



# ---------- template: "אל תבדוק" (reverse psychology, kinetic type) ----------

DONT_BEATS = [0.3, 1.9, 3.4, 5.6, 6.9, 8.9]  # each phrase lands on a beat; 8.9 = end card


def dont_check_html():
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-400.woff2);font-weight:400}}
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-600.woff2);font-weight:600}}
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-700.woff2);font-weight:700}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:#0F2A47;color:#F5F3EE;font-family:Plex,Arial,sans-serif;overflow:hidden;position:relative}}
.scene{{position:absolute;inset:0;padding:230px 90px 420px;display:flex;flex-direction:column;justify-content:center;gap:36px;opacity:0}}
.xl{{font-size:170px;font-weight:700;line-height:1.05}}
.l{{font-size:120px;font-weight:700;line-height:1.1}}
.m{{font-size:84px;font-weight:600;line-height:1.2;color:#AEB8C4}}
.teal{{color:#4FB3A2}}
.w{{display:inline-block;opacity:0}}
#end{{background:#F5F3EE;color:#0F2A47;gap:40px}}
#end h1{{font-size:118px;line-height:1.1;font-weight:700}}
#end .sub{{font-size:46px;color:#7C8794;line-height:1.4}}
#end .cta{{font-size:44px;font-weight:600;color:#11978A;direction:ltr;text-align:right}}
#end img{{height:120px;align-self:flex-start;margin-top:30px}}
</style></head><body>
<div class="scene" id="s1"><div class="xl w" data-t="{DONT_BEATS[0]}">אל תבדוק.</div><div class="m w" data-t="{DONT_BEATS[1]}">באמת.</div></div>
<div class="scene" id="s2"><div class="l w" data-t="{DONT_BEATS[2]}">הבנק<br>מעדיף<br>שלא.</div></div>
<div class="scene" id="s3"><div class="l w" data-t="{DONT_BEATS[3]}">כי מי שבודק,</div><div class="xl w" data-t="{DONT_BEATS[4]}">מגלה <span class="teal">כמה.</span></div></div>
<div class="scene" id="end"><h1>הבנק לא יגיד.<br>הבדיקה כן.</h1><div class="sub">3 דקות. בלי מסמכים.<br>אם לא משתלם, נגיד לך.</div>
  <div class="cta">barur-mashkanta.co.il/check</div><img src="{A}/img/logo-horizontal-color.svg"></div>
<script>
const B = {json.dumps(DONT_BEATS)};
const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);
const scenes = [["s1", B[0], B[2] - 0.15], ["s2", B[2], B[3] - 0.15], ["s3", B[3], B[5] - 0.15], ["end", B[5], 99]];
window.renderFrame = (t) => {{
  scenes.forEach(([id, a, b]) => {{
    document.getElementById(id).style.opacity = (t >= a - 0.01 && t < b) ? 1 : (t >= b ? 1 - ease((t - b) / 0.15) : 0);
  }});
  document.querySelectorAll('.w').forEach((el) => {{
    const k = ease((t - parseFloat(el.dataset.t)) / 0.22);
    el.style.opacity = k;
    el.style.transform = `scale(${{1.08 - 0.08 * k}})`;
    el.style.transformOrigin = 'right center';
  }});
  document.getElementById('end').style.opacity = ease((t - B[5]) / 0.35);
}};
</script></body></html>"""


def dont_check_audio(duration):
    """A deep hit on every phrase, a warm resolve on the end card."""
    n = int(duration * SR)
    out = np.zeros(n)
    m = int(0.6 * SR)
    tt = np.arange(m) / SR
    hit = (np.sin(2 * np.pi * 70 * tt * (1 - 0.25 * tt)) * np.exp(-tt * 7) * 0.7
           + np.random.default_rng(1).normal(0, 1, m) * np.exp(-tt * 60) * 0.08)
    for b in DONT_BEATS[:-1]:
        i = int(b * SR)
        out[i:i + m] += hit[: max(0, min(m, n - i))]
    k = int(3.8 * SR)
    tt = np.arange(k) / SR
    env = np.minimum(1, tt / 0.3) * np.exp(-tt * 0.8)
    tone = sum(np.sin(2 * np.pi * f * tt) for f in (220, 277.2, 330, 440)) / 4 * env * 0.12
    i = int(DONT_BEATS[-1] * SR)
    out[i:i + k] += tone[: max(0, min(k, n - i))]
    return (np.clip(out, -1, 1) * 32767).astype(np.int16)


TEMPLATES = {  # html, audio, seconds, cover time
    "counter": (counter_html, counter_audio, 16.0, 10.6),
    "dont-check": (dont_check_html, dont_check_audio, 13.0, 3.9),
}


# ---------- render ----------

def render(name, target, music=None):
    make_html, make_audio, duration, cover_t = TEMPLATES[name]
    target = Path(target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = target.parent / f"_{name}.html"
    tmp_wav = target.parent / f"_{name}.wav"
    tmp_html.write_text(make_html(), encoding="utf-8")
    with wave.open(str(tmp_wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(make_audio(duration).tobytes())

    frames = int(duration * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
           "-i", str(tmp_wav)]
    if music:
        cmd += ["-i", str(music), "-filter_complex",
                f"[2:a]volume=0.35,atrim=0:{duration},afade=t=out:st={duration - 1.5}:d=1.5[m];[1:a][m]amix=inputs=2:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "128k", "-ar", str(SR), "-movflags", "+faststart", "-shortest", str(target)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": W, "height": H})
        pg.goto(tmp_html.as_uri(), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        for f in range(frames):
            pg.evaluate(f"window.renderFrame({f / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
        pg.evaluate(f"window.renderFrame({cover_t})")
        pg.screenshot(path=str(target.with_name(target.stem + "-cover.jpg")), type="jpeg", quality=90)
        browser.close()
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")
    tmp_html.unlink(); tmp_wav.unlink()
    print("rendered", target, f"{target.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("template", choices=TEMPLATES)
    ap.add_argument("target")
    ap.add_argument("--music")
    a = ap.parse_args()
    render(a.template, a.target, a.music)
