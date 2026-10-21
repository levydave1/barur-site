"""Final intro: real David (composited into the virtual office) -> magic handoff -> David 2.0 -> circle + series slides -> end card.
Inputs are prepared by render_david.py (david_comp.mp4) and the cleaned voice (david_clean.wav).
Run: python3 -I intro_final.py <work_dir> <out.mp4> [preview]
"""
import sys, os, math, subprocess, json, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from dkengine import (W, H, FPS, SAFE_TOP, NAVY, TQ, TQD, TQL, PAPER, STONE, AMBER, CORAL, LOGO,
                      text_img, rich_line, paste, rounded, pill, icon, icon2, Header, Background,
                      caption_img, clamp, ease, back, prog)

WK = sys.argv[1]; OUT = sys.argv[2]; PREVIEW = len(sys.argv) > 3
REPO = '/home/claude/barur-site/social/heygen/'
DAV = f'{WK}/david_comp.mp4'; DAV_WAV = f'{WK}/david_clean.wav'
AV = REPO + 'raw/dk00-handoff-v2.mp4'

X = 24.30                  # handoff moment (output clock == David clock before it)
AV_LEN = 29.95
END0 = X + AV_LEN          # end card
TOTAL = END0 + 2.4
FL0, FL1 = X - 0.40, X + 0.55   # magic flash window
XF0, XF1 = X - 0.12, X + 0.12   # actual crossfade, hidden in the flash peak

def rich(spec, size=66, w=700, base=NAVY, hl=TQ):
    parts = []; on = False
    for seg in spec.split('*'):
        if seg: parts.append((seg, hl if on else base))
        on = not on
    return rich_line(parts, size, w)
def capt(spec):
    parts = []; on = False
    for seg in spec.split('*'):
        if seg: parts.append((seg, TQD if on else (255, 255, 255)))
        on = not on
    return caption_img(parts)
def fit(im, maxw=W - 120): return min(1.0, maxw / im.width)

# ---------------- captions ----------------
DCAPS_SRC = [  # David clock (what he actually said)
    (0.00, 'לפני כמה שנים עשיתי סדרה'), (1.98, 'על השקעות *נדל״ן.*'),
    (3.18, 'לאחרונה אני רואה שהרבה אנשים'), (5.00, 'משאירים *כסף על הרצפה,*'),
    (6.44, 'וזה בעיקר בנושאים של *משכנתה.*'), (9.02, 'וזה די חבל, כי זה נשאר'),
    (10.88, 'על *הרצפה של הבנק.*'), (12.29, 'אז אני חוזר, והפעם עם סדרה'),
    (14.16, '*יסודית וקבועה*'), (15.46, 'על השקעות, ובעיקר על *משכנתאות.*'),
    (18.00, 'אז בלי הקדמות,'), (18.98, 'אני מעביר את השרביט'),
    (20.34, '*לדוד 2.0,*'), (21.76, 'הגרסה הדיגיטלית שלי.'),
]
ACAPS_SRC = [  # avatar clock
    (0.00, 'היי, אני *דוד*, הגרסה הדיגיטלית.'), (2.64, 'נוצרתי באמצעות *AI*,'),
    (4.24, 'ודוד האמיתי *כותב ובודק*'), (6.46, 'כל מילה שאני אומר.'),
    (7.72, 'אני כאן כדי להעביר את הידע'), (9.36, 'בצורה *מסודרת.*'),
    (10.46, 'כל יום *טיפה*,'), (11.42, 'בסדרה שנקראת *דקה ברורה.*'),
    (13.38, 'ואם תרצו להעמיק,'), (14.50, 'יש גם אתר: *ברור משכנתאות*'),
    (16.66, 'עם כל המידע במקום אחד.'), (18.48, 'אתם מוזמנים *לעקוב,*'),
    (19.72, '*לשתף ולהגיב,*'), (20.94, 'וכל מה ש*האלגוריתם* אוהב כל כך.'),
    (22.96, 'וכמובן, אם יש לכם'), (24.00, '*משכנתה* לטפל בה,'),
    (25.26, '*דוד האמיתי* פה כדי לעזור.'), (27.30, 'מחר, *סרטון ראשון.*'), (28.76, 'נתראה שם.'),
]
def build_caps(src, end):
    out = []
    for k, (t0, s) in enumerate(src):
        t1 = src[k + 1][0] - 0.04 if k + 1 < len(src) else end
        out.append((t0 - 0.03, t1, capt(s)))
    return out
DCAPS = build_caps(DCAPS_SRC, 23.7); ACAPS = build_caps(ACAPS_SRC, AV_LEN - 0.1)
def draw_caps(base, caps, t):
    for t0, t1, ci in caps:
        if t0 <= t < t1:
            p = prog(t, t0, 0.12); paste(base, ci, W / 2, 1480 + 10 * (1 - ease(p)), scale=fit(ci, W - 60), alpha=ease(p))

# ---------------- assets ----------------
HD = Header(); BG = Background(seed=7)
AI = pill([("נוצר באמצעות AI", STONE)], 26, bg=(255, 255, 255), pad=(22, 10), shadow=False)
TAG = pill([("דוד לוי · ", NAVY), ("המקורי", TQ)], 40, bg=(255, 255, 255), pad=(34, 16))
STAMP = pill([("דקה ברורה", (255, 255, 255))], 70, bg=TQ, pad=(56, 24)).rotate(3, expand=True, resample=Image.BICUBIC)
L_KNOW = rich('הידע, *בצורה מסודרת*', 70); L_DAY = rich('כל יום · *טיפה*', 76)
L_DEEP = rich('רוצים *להעמיק?*', 74); L_ALL = rich('כל המידע *במקום אחד*', 60)
P_FOLLOW = pill([("+ עקבו", (255, 255, 255))], 56, bg=NAVY, pad=(52, 22))
P_SHARE = pill([("שתפו", NAVY)], 50, icon=icon2('share', 44, TQ, 5), pad=(40, 18))
P_COMM = pill([("הגיבו", NAVY)], 50, icon=icon2('chat', 44, TQ, 5), pad=(40, 18))
L_ALGO = rich('והאלגוריתם *אוהב את זה*', 58)
L_MORT = rich('יש לכם *משכנתה?*', 76); L_REAL = rich('דוד האמיתי *פה לעזור*', 62)
FOLLOW_END = pill([("+ עקבו", (255, 255, 255))], 58, bg=NAVY, pad=(56, 24))
LOGO_BIG = Image.open(f'{LOGO}/logo-horizontal-color.png').convert('RGBA')
LOGO_BIG = LOGO_BIG.resize((520, int(LOGO_BIG.height * 520 / LOGO_BIG.width)), Image.LANCZOS)
SLOGAN = text_img('ברור שמשלמים פחות.', 40, STONE, 600)

def site_card():
    cw, ch = 860, 250; im = rounded(cw, ch, 30, (255, 255, 255, 255), shadow=True); d = ImageDraw.Draw(im)
    # browser dots + url bar
    for k, c in enumerate([(222, 98, 72), (232, 176, 64), (17, 151, 138)]): d.ellipse([60 + k * 30, 58, 76 + k * 30, 74], fill=c + (255,))
    d.rounded_rectangle([170, 46, cw - 10, 86], 20, fill=(240, 238, 232, 255))
    url = text_img('barur-mashkanta.co.il', 30, STONE, 500); im.alpha_composite(url, (int(170 + (cw - 180 - url.width) / 2), 48))
    lg = LOGO_BIG.resize((380, int(LOGO_BIG.height * 380 / LOGO_BIG.width)), Image.LANCZOS)
    im.alpha_composite(lg, (int(30 + (cw - lg.width) / 2), int(30 + 70 + (ch - 70 - lg.height) / 2)))
    return im
SITE = site_card()

def heart(s=70, color=CORAL):
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = color + (255,)
    r = s * 0.26; d.ellipse([s * 0.08, s * 0.12, s * 0.08 + 2 * r, s * 0.12 + 2 * r], fill=c)
    d.ellipse([s * 0.92 - 2 * r, s * 0.12, s * 0.92, s * 0.12 + 2 * r], fill=c)
    d.polygon([(s * 0.1, s * 0.42), (s * 0.9, s * 0.42), (s * 0.5, s * 0.9)], fill=c); return im
HEART = heart(80)

def circle_face(img, R=95, ring=TQL):
    sq = img.crop((0, 200, 1080, 1280)).resize((2 * R, 2 * R), Image.LANCZOS).convert('RGBA')
    m = Image.new('L', (2 * R, 2 * R), 0); ImageDraw.Draw(m).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255); sq.putalpha(m)
    out = Image.new('RGBA', (2 * R + 16, 2 * R + 16), (0, 0, 0, 0)); ImageDraw.Draw(out).ellipse([0, 0, 2 * R + 15, 2 * R + 15], fill=ring + (255,))
    out.alpha_composite(sq, (8, 8)); return out
REAL = None   # filled from David's last frame

def teaser_card():
    cw, chh = 860, 200; cd = rounded(cw, chh, 26, (255, 255, 255, 255), shadow=True); dd = ImageDraw.Draw(cd)
    dd.rectangle([30 + cw - 10, 30, 30 + cw, 30 + chh], fill=AMBER + (255,))
    lab = text_img('מחר בדקה ברורה', 34, AMBER, 700); cd.alpha_composite(lab, (30 + cw - lab.width - 40, 52))
    li = rich('*סרטון 1*, מתחילים', 58); cd.alpha_composite(li, (30 + cw - li.width - 40, 106)); return cd
TEASER = teaser_card()

SCENES = [(8.30, 10.40, 'ידע'), (10.40, 13.30, 'דקה'), (13.30, 18.40, 'אתר'), (18.40, 22.90, 'עקבו'),
          (22.90, 27.20, 'עזרה'), (27.20, AV_LEN, 'מחר')]

def draw_scene(base, ta):
    cur = [s for s in SCENES if s[0] <= ta < s[1]]
    if not cur: return
    t0, t1, word = cur[0]; L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    def ap(t, d=0.35): return prog(ta, t, d)
    def up(im, t, x, y, sc=1.0, pop=False):
        p = ap(t)
        if pop: paste(L, im, x, y, scale=sc * (0.6 + 0.4 * back(p)), alpha=ease(p))
        else: paste(L, im, x, y + 30 * (1 - ease(p)), scale=sc, alpha=ease(p))
    if word == 'ידע':
        up(icon('doc', 150, NAVY, 5), 8.45, W / 2, 860, pop=True); up(L_KNOW, 9.0, W / 2, 1060, fit(L_KNOW))
    elif word == 'דקה':
        up(L_DAY, 10.46, W / 2, 840, fit(L_DAY)); up(STAMP, 12.40, W / 2, 1050, pop=True)
    elif word == 'אתר':
        up(L_DEEP, 13.38, W / 2, 780, fit(L_DEEP)); up(SITE, 14.95, W / 2, 1010, fit(SITE, W - 100), pop=True)
        up(L_ALL, 16.95, W / 2, 1240, fit(L_ALL))
    elif word == 'עקבו':
        up(P_FOLLOW, 19.05, W / 2, 800, pop=True); up(P_SHARE, 19.70, W / 2 + 170, 940, pop=True); up(P_COMM, 20.15, W / 2 - 170, 940, pop=True)
        up(L_ALGO, 21.45, W / 2, 1120, fit(L_ALGO))
        p = ap(22.05, 0.3)
        if p > 0: paste(L, HEART, W / 2, 1250 - 10 * math.sin(ta * 6), scale=0.6 + 0.4 * back(p), alpha=ease(p))
    elif word == 'עזרה':
        up(icon2('house', 140, NAVY, 5), 23.0, W / 2, 790, pop=True); up(L_MORT, 23.9, W / 2, 970, fit(L_MORT))
        if REAL is not None:
            up(REAL, 25.2, W / 2, 1160, pop=True)
        up(L_REAL, 25.6, W / 2, 1330, fit(L_REAL))
    elif word == 'מחר':
        up(TEASER, 27.30, W / 2, 980, fit(TEASER, W - 100))
    a = min(clamp((t1 - ta) / 0.25) if t1 < AV_LEN else 1.0, clamp((ta - t0) / 0.15))
    if a < 0.999: L.putalpha(L.getchannel('A').point(lambda v: int(v * a)))
    base.alpha_composite(L)

# shrink full-frame avatar into the header circle
SH0, SH1 = 7.62, 8.50
K = 2 * HD.R / 1080; SQ_C = (540, 740)
def lerp(a, b, p): return a + (b - a) * p
def xform(img, s, src_pt, dst_pt):
    nw, nh = int(round(img.width * s)), int(round(img.height * s))
    big = img.resize((max(1, nw), max(1, nh)), Image.BILINEAR)
    ox = int(round(dst_pt[0] - src_pt[0] * s)); oy = int(round(dst_pt[1] - src_pt[1] * s))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.paste(big.convert('RGBA'), (ox, oy)); return out
def shrink_frame(face, ta, t_out):
    p = ease(prog(ta, SH0, SH1 - SH0))
    base = BG.draw(t_out, 'ידע' if p > 0.6 else None, ease(prog(ta, SH1 - 0.2, 0.5)))
    s = math.exp(lerp(0, math.log(K), p)); c = (lerp(SQ_C[0], HD.cx, p), lerp(SQ_C[1], HD.cy, p))
    r_out = lerp(1320, 540, p) * s
    img = xform(face, s, SQ_C, (int(c[0]), int(c[1])))
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).ellipse([c[0] - r_out, c[1] - r_out, c[0] + r_out, c[1] + r_out], fill=255)
    if p > 0.85:
        ra = ease((p - 0.85) / 0.15); R = r_out + 10; ring = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], fill=TQL + (int(255 * ra),)); base.alpha_composite(ring)
    base.paste(img, (0, 0), ImageChops.multiply(m, img.getchannel('A')))
    q = ease(prog(ta, SH1 - 0.15, 0.4))
    if q > 0:
        paste(base, HD.name, HD.cx, HD.cy + HD.R + 40, alpha=q); paste(base, HD.title, HD.cx, HD.cy + HD.R + 78, alpha=q)
        paste(base, HD.logo, W - 70, HD.cy, anchor='r', alpha=q)
    draw_scene(base, ta); return base

def avatar_frame(face, ta, t_out):
    if ta < SH0:
        base = face.convert('RGBA')
    elif ta < SH1 + 0.3:
        base = shrink_frame(face, ta, t_out)
    else:
        sc = [s for s in SCENES if s[0] <= ta < s[1]]; word = sc[0][2] if sc else None
        base = BG.draw(t_out, word, ease(prog(ta, sc[0][0], 0.5)) if sc else 1.0)
        HD.draw(base, face.crop((0, 200, 1080, 1280))); draw_scene(base, ta)
    draw_caps(base, ACAPS, ta)
    paste(base, AI, W - 40, SAFE_TOP + 330 if ta >= SH1 else SAFE_TOP + 40, anchor='r', alpha=0.95)
    return base

def david_frame(f, t):
    img = f.convert('RGBA')
    q = ease(prog(t, 0.4, 0.4)) * (1 - ease(prog(t, 4.6, 0.4)))
    if q > 0: paste(img, TAG, W / 2, SAFE_TOP + 1130, scale=0.8 + 0.2 * back(prog(t, 0.4, 0.4)), alpha=q)
    draw_caps(img, DCAPS, t)
    return img

# ---------------- magic flash ----------------
rng = np.random.default_rng(11)
NP = 90
P_X = rng.uniform(260, 820, NP); P_Y = rng.uniform(320, 1420, NP)
ang = rng.uniform(0, 2 * np.pi, NP); spd = rng.uniform(120, 520, NP)
P_VX = np.cos(ang) * spd; P_VY = np.sin(ang) * spd - 260
P_T0 = rng.uniform(FL0 - 0.05, X + 0.15, NP); P_LIFE = rng.uniform(0.6, 1.1, NP)
P_S = rng.uniform(10, 30, NP); P_C = [(255, 255, 255), AMBER, TQL, (255, 236, 170)]
P_CI = rng.integers(0, 4, NP); P_PH = rng.uniform(0, 6, NP)
def star(s, color, a):
    im = Image.new('RGBA', (int(s * 2) + 4, int(s * 2) + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = int(s) + 2
    pts = []
    for k in range(8):
        r = s if k % 2 == 0 else s * 0.28; th = k * math.pi / 4
        pts.append((c + r * math.cos(th), c + r * math.sin(th)))
    d.polygon(pts, fill=color + (int(255 * a),)); return im.filter(ImageFilter.GaussianBlur(0.6))
GLOW = None
def glow_layer(a):
    global GLOW
    if GLOW is None:
        yy, xx = np.mgrid[0:H, 0:W]; d = np.sqrt(((xx - 540) / 620.0) ** 2 + ((yy - 760) / 900.0) ** 2)
        GLOW = np.clip(1.15 - d, 0, 1) ** 1.6
    g = (GLOW * 255 * a).astype(np.uint8)
    im = Image.new('RGBA', (W, H), (255, 252, 240, 0)); im.putalpha(Image.fromarray(g)); return im
def magic(base, t):
    if not (FL0 <= t <= FL1 + 0.8): return base
    # glow: up fast, peak at X, down
    if t <= X: ga = ease(prog(t, FL0, X - FL0)) * 0.92
    else: ga = 0.92 * (1 - ease(prog(t, X, FL1 - X)))
    if ga > 0.01: base.alpha_composite(glow_layer(ga))
    for i in range(NP):
        age = t - P_T0[i]
        if age < 0 or age > P_LIFE[i]: continue
        u = age / P_LIFE[i]; a = math.sin(math.pi * u) * (0.6 + 0.4 * math.sin(t * 25 + P_PH[i]))
        x = P_X[i] + P_VX[i] * age; y = P_Y[i] + P_VY[i] * age + 160 * age * age
        st = star(P_S[i] * (1 - 0.4 * u), P_C[P_CI[i]], max(0, a))
        base.alpha_composite(st, (int(x - st.width / 2), int(y - st.height / 2)))
    return base

def end_frame(t):
    im = Image.new('RGBA', (W, H), PAPER + (255,)); te = t - END0
    p = ease(prog(te, 0.0, 0.5)); paste(im, LOGO_BIG, W / 2, 760, scale=0.9 + 0.1 * p, alpha=p)
    paste(im, SLOGAN, W / 2, 900, alpha=ease(prog(te, 0.3, 0.4)))
    q = prog(te, 0.5, 0.4); paste(im, FOLLOW_END, W / 2, 1080, scale=0.6 + 0.4 * back(q), alpha=ease(q))
    paste(im, AI, W / 2, 1300, alpha=ease(prog(te, 0.8, 0.4)))
    return im

def compose(t, fd, fa):
    if t >= END0: return end_frame(t)
    if t < XF0: base = david_frame(fd, t)
    elif t < XF1:
        a = ease(prog(t, XF0, XF1 - XF0))
        base = Image.blend(david_frame(fd, t).convert('RGB'), avatar_frame(fa, max(0, t - X), t).convert('RGB'), a).convert('RGBA')
    else:
        base = avatar_frame(fa, t - X, t)
        if t >= END0 - 0.3:
            base = Image.blend(base.convert('RGB'), end_frame(t).convert('RGB'), ease(prog(t, END0 - 0.3, 0.3))).convert('RGBA')
    return magic(base, t)

# ---------------- audio: chime + magical music bed ----------------
SR = 48000
def bell(f, dur, amp=1.0, dec=2.2):
    t = np.arange(int(dur * SR)) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t * 2) + 0.2 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 4)
         + 0.08 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t * 6))
    att = np.clip(t / 0.004, 0, 1)
    return amp * y * att * np.exp(-t * dec)
def add(buf, y, at):
    i = int(at * SR); j = min(len(buf), i + len(y))
    if j > i: buf[i:j] += y[:j - i]
def make_audio(path):
    n = int((TOTAL + 1) * SR); mus = np.zeros(n); fx = np.zeros(n)
    # chime: ascending glissando into the flash + sparkle tail
    notes = [523.25, 587.33, 659.25, 783.99, 880, 1046.5, 1174.7, 1318.5, 1568, 1760, 2093]
    for k, f in enumerate(notes): add(fx, bell(f, 1.8, 0.22, 3.0), FL0 + k * 0.045)
    r = np.random.default_rng(3)
    for k in range(18): add(fx, bell(r.choice(notes[5:]), 0.9, 0.08, 6.0), X + r.uniform(0, 0.9))
    # whoosh-ish shimmer: filtered noise swell
    m = int(0.9 * SR); nz = r.standard_normal(m); nz = nz - np.convolve(nz, np.ones(6) / 6, 'same')
    env = np.sin(np.linspace(0, np.pi, m)) ** 2; add(fx, nz * env * 0.05, FL0)
    # music bed: F major pentatonic arpeggio + soft pad, from the handoff to the end card
    bpm = 100; step = 60 / bpm / 2
    prog_ch = [[174.61, 220, 261.63], [146.83, 174.61, 220], [116.54, 146.83, 174.61], [130.81, 164.81, 196]]   # F Dm Bb C
    arp_hi = [[698.46, 880, 1046.5, 880], [587.33, 698.46, 880, 698.46], [587.33, 698.46, 932.33, 698.46], [523.25, 659.25, 783.99, 659.25]]
    t = X + 0.2; bar = 0
    while t < END0 + 2.0:
        ch = prog_ch[bar % 4]; ah = arp_hi[bar % 4]
        for f in ch:  # pad: slow sine swell
            d = 8 * step; tt = np.arange(int(d * SR)) / SR
            pad = np.sin(2 * np.pi * f * tt) * np.sin(np.pi * tt / d) ** 1.5 * 0.05
            add(mus, pad, t)
        for k in range(8): add(mus, bell(ah[k % 4] * (1 if k < 4 else 1.0), 1.2, 0.07, 3.5), t + k * step)
        t += 8 * step; bar += 1
    fade = np.ones(n); i0 = int((END0 + 1.6) * SR); fade[i0:] = np.clip(1 - (np.arange(n - i0) / (0.8 * SR)), 0, 1); mus *= fade
    fi = int((X + 0.2) * SR); mus[fi:fi + int(1.2 * SR)] *= np.linspace(0, 1, int(1.2 * SR))[:len(mus[fi:fi + int(1.2 * SR)])]
    y = np.stack([mus, fx], 1)
    for k, nm in enumerate(['music', 'fx']):
        z = y[:, k] / (np.abs(y[:, k]).max() + 1e-9) * 0.7
        with wave.open(path.replace('.wav', f'_{nm}.wav'), 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((z * 32767).astype(np.int16).tobytes())

def frames(src, ss=0):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(ss), '-i', src, '-vf', f'fps={FPS},scale={W}:{H}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    nb = W * H * 3
    while True:
        b = p.stdout.read(nb)
        if len(b) < nb: break
        yield Image.frombytes('RGB', (W, H), b)
def grab(src, t):
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.3f}', '-i', src, '-frames:v', '1', '-vf', f'scale={W}:{H}',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return Image.frombytes('RGB', (W, H), b)

def main():
    global REAL
    REAL = circle_face(grab(DAV, X - 0.3), R=105)
    if PREVIEW:
        ts = [1.0, 6.0, 23.9, 24.1, 24.3, 24.5, 24.8, 26.5, X + 8.0, X + 9.5, X + 12.8, X + 16.5, X + 20.2, X + 22.3, X + 26.0, X + 28.0, END0 + 1.5]
        out = [compose(t, grab(DAV, t) if t < XF1 else None, grab(AV, min(max(0, t - X), AV_LEN - 0.1)) if t >= XF0 else None) for t in ts]
        S = Image.new('RGB', (270 * len(out), 480), 'white')
        for k, im in enumerate(out): S.paste(im.convert('RGB').resize((270, 480)), (k * 270, 0))
        S.save(OUT); return
    tmp = f'{WK}/aud.wav'; make_audio(tmp); AV_FIRST = grab(AV, 0)
    n = int(TOTAL * FPS); dv = frames(DAV); av = None; lastd = lasta = None
    xd = int(X * 1000)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-i', DAV_WAV, '-i', AV, '-i', tmp.replace('.wav', '_music.wav'), '-i', tmp.replace('.wav', '_fx.wav'), '-filter_complex',
        f'[1:a]atrim=0:{X + 0.1},afade=t=out:st={X - 0.25}:d=0.3,aresample=48000[d];'
        f'[2:a]highpass=f=60,loudnorm=I=-16:TP=-1.5,aresample=48000,adelay={xd}|{xd}[a];'
        f'[3:a]volume=0.16[m];[4:a]volume=0.55[f];'
        f'[d][a][m][f]amix=inputs=4:duration=longest:normalize=0,alimiter=limit=0.95,apad=whole_dur={TOTAL}[mix]',
        '-map', '0:v', '-map', '[mix]', '-t', str(TOTAL), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for k in range(n):
        t = k / FPS; fd = fa = None
        if t < XF1:
            try: lastd = next(dv)
            except StopIteration: pass
            fd = lastd
        if XF0 <= t < X:
            fa = AV_FIRST
        elif t >= X:
            if av is None: av = frames(AV)
            if t - X < AV_LEN:
                try: lasta = next(av)
                except StopIteration: pass
            fa = lasta
        enc.stdin.write(compose(t, fd, fa).convert('RGB').tobytes())
        if k % 150 == 0: print(k, '/', n, flush=True)
    enc.stdin.close(); enc.wait(); print('done', OUT, round(TOTAL, 2))

if __name__ == '__main__':
    main()
