"""Intro sketch: real David -> crossfade to David 2.0 -> shrink into circle -> series explainer -> end card.
Run: python3 -I intro_handoff.py <david.mp4> <out.mp4> [preview]
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
from dkengine import (W, H, FPS, SAFE_TOP, NAVY, TQ, TQD, TQL, PAPER, STONE, AMBER, LOGO,
                      text_img, rich_line, paste, rounded, pill, icon, icon2, Header, Background,
                      caption_img, whoosh, clamp, ease, back, prog)

DAVID = sys.argv[1]; OUT = sys.argv[2]; PREVIEW = len(sys.argv) > 3
AV = '/home/claude/barur-site/social/heygen/raw/dk01-david2.mp4'

# ---- timeline (seconds, output clock) ----
X0, X1 = 23.0, 23.6          # crossfade window (David clock == output clock here)
PUSH0 = 21.8                 # David push-in starts
AV_END = 21.2                # cut avatar before the old CTA
T_AV = lambda t: t - X0      # avatar local time
END0 = X0 + AV_END           # end card starts
TOTAL = END0 + 3.2

# alignment (measured on frames): eyes + scale
D_EYE = (520, 800); A_EYE = (552, 532); MEET = (536, 640)
SD, SA = 1.15, 1.242

def xform(img, s, src_pt, dst_pt):
    """scale img by s around src_pt, place src_pt at dst_pt, crop to frame."""
    if abs(s - 1) < 1e-3 and src_pt == dst_pt: return img.convert('RGBA')
    nw, nh = int(round(img.width * s)), int(round(img.height * s))
    big = img.resize((nw, nh), Image.BILINEAR)
    ox = int(round(dst_pt[0] - src_pt[0] * s)); oy = int(round(dst_pt[1] - src_pt[1] * s))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.paste(big.convert('RGBA'), (ox, oy)); return out

def lerp(a, b, p): return a + (b - a) * p
def lerp2(a, b, p): return (lerp(a[0], b[0], p), lerp(a[1], b[1], p))

def frames(src, fps=FPS):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'fps={fps},scale={W}:{H}:flags=lanczos',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield Image.frombytes('RGB', (W, H), b)

# ---- assets ----
HD = Header(); BG = Background(seed=1)
AI = pill([("נוצר באמצעות AI", STONE)], 26, bg=(255, 255, 255), pad=(22, 10), shadow=False)
TAG = pill([("דוד לוי · ", NAVY), ("המקורי", TQ)], 40, bg=(255, 255, 255), pad=(34, 16))
STAMP = pill([("דקה ברורה", (255, 255, 255))], 64, bg=TQ, pad=(52, 22)).rotate(3, expand=True, resample=Image.BICUBIC)
FOLLOW = pill([("+ עקבו", (255, 255, 255))], 58, bg=NAVY, pad=(56, 24))
LOGO_BIG = Image.open(f'{LOGO}/logo-horizontal-color.png').convert('RGBA')
LOGO_BIG = LOGO_BIG.resize((520, int(LOGO_BIG.height * 520 / LOGO_BIG.width)), Image.LANCZOS)

def rich(spec, size=66, w=700):
    """'*x*' marks highlighted words (TQ)."""
    parts = []; hl = False
    for seg in spec.split('*'):
        if seg: parts.append((seg, TQ if hl else NAVY))
        hl = not hl
    return rich_line(parts, size, w)

# captions (avatar clock), script text over Whisper timings
CAPS_SRC = [
    (0.38, [("נעים מאוד, אני ", 0), ("דוד 2.0.", 1)]),
    (3.20, [("אני נראה כמוהו, נשמע כמוהו", 0)]),
    (6.28, [("ולא צריך ", 0), ("הפסקת קפה.", 1)]),
    (7.96, [("הוא יושב ", 0), ("מול הבנקים,", 1)]),
    (9.60, [("ואני אביא לכם ", 0), ("כל יום", 1)]),
    (11.54, [("טיפ אחד ", 1), ("על משכנתה ונדל״ן,", 0)]),
    (13.52, [("מתוך ", 0), ("עשרים שנה", 1), (" של ניסיון שלו.", 0)]),
    (16.36, [("וכשתרצו לבדוק ", 0), ("באמת", 1), (" את המשכנתה,", 0)]),
    (19.16, [("את זה עושים ", 0), ("מול המקור.", 1)]),
]
CAPS = []
for k, (t0, parts) in enumerate(CAPS_SRC):
    t1 = CAPS_SRC[k + 1][0] - 0.04 if k + 1 < len(CAPS_SRC) else AV_END
    CAPS.append((t0 - 0.02, t1, caption_img([(s, TQD if h else (255, 255, 255)) for s, h in parts])))

def fit(im, maxw=W - 120): return min(1.0, maxw / im.width)

# graphic scenes after the shrink (avatar clock)
L_BANK = rich('דוד *המקורי*', 76); L_BANK2 = rich('יושב מול הבנקים', 64)
L_DAY = rich('כל יום · *טיפ אחד*', 70)
CH1 = pill([("משכנתה", NAVY)], 48, icon=icon2('house', 46, TQ, 5)); CH2 = pill([("נדל״ן", NAVY)], 48, icon=icon2('building', 46, TQ, 5))
N20 = text_img('20', 300, TQ, 700); L20 = rich('שנה של *ניסיון*', 66)
L_REAL = rich('רוצים לבדוק *באמת?*', 70); L_SRC = rich('עושים את זה *מול המקור*', 66)
SCENES = [(8.30, 9.50, 'בנק'), (9.50, 13.40, 'דקה'), (13.40, 16.25, 'שנה'), (16.25, AV_END, 'מקור')]

def draw_scene(base, ta):
    cur = [s for s in SCENES if s[0] <= ta < s[1]]
    if not cur: return None
    t0, t1, word = cur[0]
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    def ap(t, d=0.35): return prog(ta, t, d)
    if word == 'בנק':
        p = ap(8.35); paste(layer, icon('bank', 150, NAVY, 5), W / 2, 820, scale=0.6 + 0.4 * back(p), alpha=ease(p))
        p = ap(8.46); paste(layer, L_BANK, W / 2, 1010 + 30 * (1 - ease(p)), alpha=ease(p))
        p = ap(8.84); paste(layer, L_BANK2, W / 2, 1110 + 30 * (1 - ease(p)), alpha=ease(p))
    elif word == 'דקה':
        p = ap(9.6); paste(layer, STAMP, W / 2, 800, scale=0.5 + 0.5 * back(p), alpha=ease(p))
        p = ap(10.86); paste(layer, L_DAY, W / 2, 980 + 30 * (1 - ease(p)), scale=fit(L_DAY), alpha=ease(p))
        p = ap(12.30); paste(layer, CH1, W / 2 + 160, 1140, scale=0.6 + 0.4 * back(p), alpha=ease(p))
        p = ap(12.85); paste(layer, CH2, W / 2 - 160, 1140, scale=0.6 + 0.4 * back(p), alpha=ease(p))
    elif word == 'שנה':
        p = ap(14.10, 0.45); paste(layer, N20, W / 2, 870, scale=0.5 + 0.5 * back(p), alpha=ease(p))
        p = ap(14.56); paste(layer, L20, W / 2, 1100 + 30 * (1 - ease(p)), alpha=ease(p))
    elif word == 'מקור':
        p = ap(16.36); paste(layer, L_REAL, W / 2, 860 + 30 * (1 - ease(p)), scale=fit(L_REAL), alpha=ease(p))
        p = ap(19.16); paste(layer, icon('check', 140, TQ, 6), W / 2, 1010, scale=0.6 + 0.4 * back(p), alpha=ease(p))
        p = ap(19.84); paste(layer, L_SRC, W / 2, 1160 + 30 * (1 - ease(p)), scale=fit(L_SRC), alpha=ease(p))
    a = min(clamp((t1 - ta) / 0.25) if t1 < AV_END else 1.0, clamp((ta - t0) / 0.15))
    if a < 0.999: layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    base.alpha_composite(layer)
    return word

# shrink: whole avatar frame -> circle (crop square 0,200,1080 -> 2R at header center)
SH0, SH1 = 7.50, 8.45
K = 2 * HD.R / 1080; SQ_C = (540, 740)
def shrink_frame(face, ta, t_out):
    p = ease(prog(ta, SH0, SH1 - SH0))
    base = BG.draw(t_out, 'בנק' if p > 0.6 else None, ease(prog(ta, SH1 - 0.2, 0.5)))
    s = math.exp(lerp(0, math.log(K), p)); c = lerp2(SQ_C, (HD.cx, HD.cy), p)
    r_src = lerp(1320, 540, p); r_out = r_src * s
    img = xform(face, s, SQ_C, (int(c[0]), int(c[1]))).convert('RGBA')
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).ellipse([c[0] - r_out, c[1] - r_out, c[0] + r_out, c[1] + r_out], fill=255)
    if p > 0.85:  # ring fades in
        ra = ease((p - 0.85) / 0.15); R = r_out + 10
        ring = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], fill=TQL + (int(255 * ra),)); base.alpha_composite(ring)
    from PIL import ImageChops
    base.paste(img, (0, 0), ImageChops.multiply(m, img.getchannel('A')))
    q = ease(prog(ta, SH1 - 0.15, 0.4))
    if q > 0:
        paste(base, HD.name, HD.cx, HD.cy + HD.R + 40, alpha=q); paste(base, HD.title, HD.cx, HD.cy + HD.R + 78, alpha=q)
        paste(base, HD.logo, W - 70, HD.cy, anchor='r', alpha=q)
    draw_scene(base, ta)
    return base

def avatar_frame(face, ta, t_out):
    if ta < SH0:  # full screen, zoom from matched framing to normal
        p = ease(prog(ta, 0.6, 1.4))
        s = lerp(SA, 1.0, p); dst = lerp2(MEET, A_EYE, p)
        base = xform(face, s, A_EYE, (int(dst[0]), int(dst[1]))).convert('RGBA')
    elif ta < SH1 + 0.3:
        base = shrink_frame(face, ta, t_out)
    else:
        sc = [s for s in SCENES if s[0] <= ta < s[1]]
        word = sc[0][2] if sc else None
        base = BG.draw(t_out, word, ease(prog(ta, sc[0][0], 0.5)) if sc else 1.0)
        HD.draw(base, face.crop((0, 200, 1080, 1280)))
        draw_scene(base, ta)
    for t0, t1, ci in CAPS:
        if t0 <= ta < t1:
            p = prog(ta, t0, 0.12); paste(base, ci, W / 2, 1480 + 10 * (1 - ease(p)), scale=fit(ci, W - 60), alpha=ease(p))
    paste(base, AI, W - 40, SAFE_TOP + 330 if ta >= SH1 else SAFE_TOP + 40, anchor='r', alpha=0.95)
    return base

def david_frame(f, t):
    p = ease(prog(t, PUSH0, X1 - PUSH0))
    s = lerp(1.0, SD, p); dst = lerp2(D_EYE, MEET, p)
    img = xform(f, s, D_EYE, (int(dst[0]), int(dst[1]))).convert('RGBA')
    q = ease(prog(t, 0.5, 0.4)) * (1 - ease(prog(t, 5.0, 0.4)))
    if q > 0: paste(img, TAG, W / 2, SAFE_TOP + 1150, scale=0.8 + 0.2 * back(prog(t, 0.5, 0.4)), alpha=q)
    return img

def end_frame(t):
    im = Image.new('RGBA', (W, H), PAPER + (255,)); te = t - END0
    p = ease(prog(te, 0.0, 0.5)); paste(im, LOGO_BIG, W / 2, 640, scale=0.9 + 0.1 * p, alpha=p)
    q = prog(te, 0.35, 0.4); paste(im, FOLLOW, W / 2, 860, scale=0.6 + 0.4 * back(q), alpha=ease(q))
    cw, chh = 820, 200; cd = rounded(cw, chh, 26, (255, 255, 255, 255), shadow=True); dd = ImageDraw.Draw(cd)
    dd.rectangle([30 + cw - 10, 30, 30 + cw, 30 + chh], fill=AMBER + (255,))
    lab = text_img('מחר בדקה ברורה', 34, AMBER, 700); cd.alpha_composite(lab, (30 + cw - lab.width - 40, 52))
    li = rich('*סרטון 1*, מתחילים', 56); cd.alpha_composite(li, (30 + cw - li.width - 40, 108))
    r = prog(te, 0.8, 0.45); paste(im, cd, W / 2, 1120 + 40 * (1 - ease(r)), alpha=ease(r))
    paste(im, AI, W / 2, 1420, alpha=ease(prog(te, 1.0, 0.4)))
    return im

def render():
    n = int(TOTAL * FPS); dv = None; av = None; lastd = lasta = None
    tmp = '/home/claude/dk/tmp'; os.makedirs(tmp, exist_ok=True); whoosh(f'{tmp}/whoosh.wav')
    ws1 = X0 + SH0 - 0.05; ws2 = END0 - 0.1
    if PREVIEW:
        ts = [1.0, 22.6, 23.3, 25.5, 30.75, 31.6, 33.5, 35.4, 37.8, 40.2, 43.5, 45.6]
        def grab(src, tt):
            b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, tt):.3f}', '-i', src, '-frames:v', '1', '-vf', f'scale={W}:{H}:flags=lanczos',
                                '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            return Image.frombytes('RGB', (W, H), b)
        out = []
        for t in ts:
            out.append(compose(t, grab(DAVID, t) if t < X1 else None, grab(AV, min(T_AV(t), AV_END - 0.05)) if t >= X0 else None))
        S = Image.new('RGB', (270 * len(out), 480), 'white')
        for k, im in enumerate(out): S.paste(im.convert('RGB').resize((270, 480)), (k * 270, 0))
        S.save(OUT); return
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-i', DAVID, '-i', AV, '-i', f'{tmp}/whoosh.wav', '-filter_complex',
        f'[1:a]atrim=0:{X1},afade=t=out:st={X0}:d={X1 - X0},loudnorm=I=-16:TP=-1.5,aresample=48000[d];'
        f'[2:a]atrim=0:{AV_END},afade=t=out:st={AV_END - 0.2}:d=0.2,loudnorm=I=-16:TP=-1.5,aresample=48000,adelay={int(X0 * 1000)}|{int(X0 * 1000)}[a];'
        f'[3:a]asplit=2[w1][w2];[w1]adelay={int(ws1 * 1000)}|{int(ws1 * 1000)},volume=0.8[x1];[w2]adelay={int(ws2 * 1000)}|{int(ws2 * 1000)},volume=0.6[x2];'
        f'[d][a][x1][x2]amix=inputs=4:duration=longest:normalize=0,apad=whole_dur={TOTAL}[m]',
        '-map', '0:v', '-map', '[m]', '-t', str(TOTAL), '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for k in range(n):
        t = k / FPS; fd = fa = None
        if t < X1:
            if dv is None: dv = frames(DAVID)
            try: lastd = next(dv)
            except StopIteration: pass
            fd = lastd
        if t >= X0:
            if av is None: av = frames(AV)
            if T_AV(t) < AV_END:
                try: lasta = next(av)
                except StopIteration: pass
            fa = lasta
        enc.stdin.write(compose(t, fd, fa).convert('RGB').tobytes())
        if k % 150 == 0: print(k, '/', n, flush=True)
    enc.stdin.close(); enc.wait(); print('done', OUT, round(TOTAL, 2))

def compose(t, fd, fa):
    if t >= END0: return end_frame(t)
    if t < X0: return david_frame(fd, t)
    A = avatar_frame(fa, T_AV(t), t)
    if t < X1:
        D = david_frame(fd, t); a = ease(prog(t, X0, X1 - X0))
        return Image.blend(D.convert('RGB'), A.convert('RGB'), a)
    if t >= END0 - 0.3:
        return Image.blend(A.convert('RGB'), end_frame(t).convert('RGB'), ease(prog(t, END0 - 0.3, 0.3)))
    return A

if __name__ == '__main__':
    render()
