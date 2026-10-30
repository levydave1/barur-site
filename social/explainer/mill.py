"""Millennium series editor (same look as millennium_series.py): captions, frozen frame + slogan, end card.
usage: python3 mill.py spec.json
spec: {src, out, L, caps:[[start,end,[[text,"w"|"t"],...]]]}
"""
import json, subprocess, sys, os
from playwright.sync_api import sync_playwright
sys.path.insert(0, "/home/claude/heygen")
import edit

spec = json.load(open(sys.argv[1]))
wd = os.path.splitext(spec["out"])[0] + "_work"
os.makedirs(wd, exist_ok=True)
W, H, L = 1080, 1920, spec["L"]
HERE = os.path.dirname(os.path.abspath(__file__))

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
    for i, (s, e, parts) in enumerate(spec["caps"]):
        html = "".join(f'<span style="color:{"#4FB3A2" if c == "t" else "#fff"}">{t}</span>' for t, c in parts)
        pg.set_content(f"""<html><head><meta charset="utf-8"><style>{edit.FONTS}
.c{{position:absolute;left:0;right:0;top:{spec.get('y', 1500)}px;transform:translateY(-50%);display:flex;justify-content:center}}
.c div{{background:rgba(15,42,71,.88);font-weight:700;font-size:74px;line-height:1.25;padding:22px 44px 32px;border-radius:32px;max-width:1000px;text-align:center}}
</style></head><body><div class="c"><div>{html}</div></div></body></html>""")
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(60)
        pg.screenshot(path=f"{wd}/cap{i}.png", omit_background=True)
    if not os.path.exists(f"{HERE}/slogan.png"):
        pg.set_content(f"""<html><head><meta charset="utf-8"><style>{edit.FONTS}
body{{background:linear-gradient(to bottom, rgba(15,42,71,0) 0px, rgba(15,42,71,0) 680px, rgba(15,42,71,.92) 1360px, rgba(15,42,71,.92) 1920px)}}
.t{{position:absolute;left:0;right:0;top:1195px;text-align:center;color:#4FB3A2;font-weight:600;font-size:50px}}
.s{{position:absolute;left:0;right:0;top:1290px;text-align:center;color:#fff;font-weight:700;font-size:100px;line-height:1.2}}
</style></head><body><div class="t">מחזור משכנתה</div><div class="s">לא צריך לחכות<br>מילניום.</div></body></html>""")
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(60)
        pg.screenshot(path=f"{HERE}/slogan.png", omit_background=True)
    b.close()

ins = ["-i", spec["src"]]
ch = [f"[0:v]trim=end={L},setpts=PTS-STARTPTS,scale=1080:1920:flags=lanczos,fps=24,format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=1.9[v0]"]
last = "v0"
for i, (s, e, _) in enumerate(spec["caps"]):
    ins += ["-i", f"{wd}/cap{i}.png"]
    ch.append(f"[{last}][{i + 1}:v]overlay=0:0:enable='between(t,{s},{e})'[c{i}]"); last = f"c{i}"
n = len(spec["caps"])
ins += ["-loop", "1", "-t", "1.9", "-framerate", "24", "-i", f"{HERE}/slogan.png",
        "-loop", "1", "-t", "2.9", "-framerate", "24", "-i", f"{HERE}/endcard.png"]
ch.append(f"[{n + 1}:v]format=rgba,fade=in:st=0:d=0.25:alpha=1,setpts=PTS+{L}/TB[sl]")
ch.append(f"[{last}][sl]overlay=0:0:eof_action=pass,format=yuv420p,setsar=1[main]")
ch.append(f"[{n + 2}:v]scale=1080:1920,fps=24,format=yuv420p,setsar=1[end]")
off = L + 1.4; tot = off + 2.9
ch.append(f"[main][end]xfade=transition=fade:duration=0.5:offset={off}[v]")
ch.append(f"[0:a]atrim=end={L},asetpts=PTS-STARTPTS,loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000,afade=t=out:st={L - 0.3}:d=0.3,apad=whole_dur={tot}[a]")
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", ";".join(ch), "-map", "[v]", "-map", "[a]", "-t", str(tot),
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", spec["out"]], check=True)
print("ok", spec["out"], tot)
