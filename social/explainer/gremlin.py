"""Interest-gremlin episode builder: clean intro/caught clips (raw/esc.mp4, raw/peek.mp4) + end card and soundtrack of episode 3.
usage: python3 gremlin.py <image.png> <out.mp4> <hint_html> <place>
place: "ring:cx,cy,rin,rout,dx,dy,w"  (head peeks from behind a ring, coords in image px)
       "win:x0,y0,x1,y1,w"            (head peeks up from the bottom of a window)
"""
import subprocess, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright
sys.path.insert(0, "/home/claude/heygen")
import edit

SRC = "/home/claude/mil/gremlin3.mp4"
img_path, out, hint, place = sys.argv[1:5]
W, H, FPS = 1080, 1920, 30
T_INTRO_END, FLASH1, T_CD0, FLASH2, T_REV, T_ZOOM0, T_CUT = 3.83, 4.0, 4.2, 10.95, 11.13, 12.0, 13.37
HINT_T = 1.70

# ---- composite the gremlin head into the image
base = Image.open(img_path).convert("RGB")
iw, ih = base.size
head = Image.open("/home/claude/mil/head.png").convert("RGBA")
kind, vals = place.split(":")
v = [float(x) for x in vals.split(",")]
if kind == "ring":
    cx, cy, rin, rout, dx, dy, hw = v
    hx, hy = cx + dx, cy + dy
else:
    x0, y0, x1, y1, hw = v
hh = hw * head.height / head.width
hs = head.resize((max(1, round(hw * 4)), max(1, round(hh * 4))), Image.LANCZOS)  # supersample
big = base.resize((iw * 4, ih * 4), Image.LANCZOS).convert("RGBA")
layer = Image.new("RGBA", big.size, (0, 0, 0, 0))
if kind == "ring":
    px, py = round((hx - hw / 2) * 4), round((hy - hh / 2) * 4)
else:
    px, py = round(((x0 + x1) / 2 - hw / 2) * 4), round((y1 - hh * 0.88) * 4)
layer.alpha_composite(hs, (px, py))
la = np.asarray(layer, np.float32)
yy, xx = np.mgrid[0:big.height, 0:big.width].astype(np.float32) / 4.0
if kind == "ring":
    r = np.hypot(xx - cx, yy - cy)
    keep = ~((r > rin) & (r < rout))  # the ring itself stays in front
    la[..., 3] *= keep
    centre_y = hy
else:
    inside = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    la[..., 3] *= inside
    la[..., :3] *= 0.88  # window interior is a touch darker
    centre_y = y1 - hh * 0.3
layer = Image.fromarray(la.clip(0, 255).astype(np.uint8))
big.alpha_composite(layer)
comp = big.resize((iw, ih), Image.LANCZOS).convert("RGB")
comp.save(out.replace(".mp4", "-image.png"))
gx = (hx if kind == "ring" else (x0 + x1) / 2) * W / iw
gy = centre_y * H / ih
canvas = np.asarray(comp.resize((W, H), Image.LANCZOS), np.float32)

# ---- text overlays in the gremlin series style (yellow/white, heavy dark stroke)
TXT = [  # key, text, colour, font px, glyph top
    ("q1", "יכולים למצוא", "#FDD540", 96, 1294),
    ("q2", "את השדון בתמונה?", "#FDD540", 96, 1406),
    ("hint", hint, "#FFFFFF", 56, 1555),
    ("sec", "יש לכם 7 שניות", "#FFFFFF", 62, 1668),
    ("top", "תפסנו אותך", "#FDD540", 70, 300),
    ("lm", "לא מצאתם אותו?", "#FFFFFF", 80, 1346),
    ("bd", "בדיוק בגלל זה", "#FDD540", 88, 1468),
    ("hs", "הוא עדיין שם.", "#FDD540", 88, 1594),
]
OV = {}
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
    for key, text, col, fs, gt in TXT:
        pg.set_content(f"""<html><head><meta charset="utf-8"><style>{edit.FONTS}
.t{{position:absolute;left:0;right:0;top:{gt - 0.2 * fs:.0f}px;text-align:center;font-weight:700;font-size:{fs}px;line-height:1;color:{col};
-webkit-text-stroke:{max(8, fs * 0.13):.0f}px #1b1a22;paint-order:stroke fill;text-shadow:0 4px 10px rgba(0,0,0,.35)}}
em{{font-style:normal;color:#FDD540}}</style></head><body><div class="t">{text}</div></body></html>""")
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(60)
        pg.screenshot(path=f"/home/claude/mil/ov_{key}.png", omit_background=True)
        OV[key] = np.asarray(Image.open(f"/home/claude/mil/ov_{key}.png").convert("RGBA"), np.float32)
    b.close()


def pop(f, key, t, t0, d=0.18):
    if t < t0:
        return f
    k = min(1, (t - t0) / d)
    o = OV[key]
    if k < 1:
        sc = 0.85 + 0.15 * k
        im = Image.fromarray(o.astype(np.uint8))
        bb = im.getbbox()
        if bb:
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            sm = im.resize((int(W * sc), int(H * sc)), Image.LANCZOS)
            canvas_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            canvas_.alpha_composite(sm, (int(cx - cx * sc), int(cy - cy * sc)))
            o = np.asarray(canvas_, np.float32).copy()
        o = o.copy(); o[..., 3] *= k
    return over(f, o, 0, 0)


def clip_frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out_ = []
    while True:
        bb_ = p.stdout.read(W * H * 3)
        if len(bb_) < W * H * 3:
            break
        out_.append(np.frombuffer(bb_, np.uint8).reshape(H, W, 3))
    return out_


def badge(d, frac):
    s = 4; R = 70 * s
    im = Image.new("RGBA", (2 * R + 20 * s, 2 * R + 20 * s), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    c = R + 10 * s
    dr.ellipse([c - R, c - R, c + R, c + R], fill=(15, 42, 71, 240))
    dr.ellipse([c - R + 5 * s, c - R + 5 * s, c + R - 5 * s, c + R - 5 * s], outline=(60, 82, 110, 255), width=9 * s)
    col = (232, 180, 76, 255) if d > 2 else (217, 99, 76, 255)
    dr.arc([c - R + 5 * s, c - R + 5 * s, c + R - 5 * s, c + R - 5 * s], -90, -90 + 360 * frac, fill=col, width=9 * s)
    from PIL import ImageFont
    f = ImageFont.truetype("/home/claude/mil/plex700.ttf", 78 * s) if False else None
    return im, c, s


# digits rendered once via browser for proper font
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 200, "height": 200})
    for dgt in range(1, 8):
        pg.set_content(f"""<html><head><meta charset="utf-8"><style>{edit.FONTS} html,body{{width:200px;height:200px}}
div{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:88px;padding-bottom:10px}}</style></head>
<body><div>{dgt}</div></body></html>""")
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(40)
        pg.screenshot(path=f"/home/claude/mil/d{dgt}.png", omit_background=True)
    b.close()
DIG = {d: Image.open(f"/home/claude/mil/d{d}.png").convert("RGBA") for d in range(1, 8)}


def timer_img(t):
    k = t - FLASH1
    d = max(1, 7 - int(k))
    frac = 1 - (k - int(k))
    im, c, s = badge(d, frac)
    im = im.resize((im.width // s, im.height // s), Image.LANCZOS)
    dg = DIG[d]
    pop = 1 + 0.25 * max(0, 1 - (k - int(k)) / 0.18)
    dgs = dg.resize((int(200 * pop), int(200 * pop)), Image.LANCZOS)
    im.alpha_composite(dgs, (im.width // 2 - dgs.width // 2, im.height // 2 - dgs.height // 2))
    return np.asarray(im, np.float32)


def over(dst, src, x, y):
    h, w = src.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]; a = s[..., 3:4] / 255.0
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + s[..., :3] * a
    return dst


def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def view(z, fx, fy):
    """zoom z toward focus (fx,fy) keeping it inside the frame"""
    if z <= 1.0001:
        return canvas.copy(), (lambda x, y: (x, y))
    cw, ch = W / z, H / z
    lx = min(max(fx - cw / 2, 0), W - cw); ty = min(max(fy - ch / 2, 0), H - ch)
    crop = Image.fromarray(canvas.astype(np.uint8)).crop((int(lx), int(ty), int(lx + cw), int(ty + ch))).resize((W, H), Image.LANCZOS)
    return np.asarray(crop, np.float32), (lambda x, y: ((x - lx) * z, (y - ty) * z))


def ring_layer(cx, cy, r, alpha):
    s = 3
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    big = Image.new("RGBA", (int(r * 2 * s + 40 * s), int(r * 2 * s + 40 * s)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(big); c = big.width / 2
    dr.ellipse([c - r * s, c - r * s, c + r * s, c + r * s], outline=(230, 40, 40, int(255 * alpha)), width=int(max(6, r * 0.12) * s))
    big = big.resize((big.width // s, big.height // s), Image.LANCZOS)
    im.alpha_composite(big, (int(cx - big.width / 2), int(cy - big.height / 2)))
    return np.asarray(im, np.float32)


# ---- render 0..T_CUT
intro = clip_frames("/home/claude/mil/raw/esc.mp4")
caught = clip_frames("/home/claude/mil/raw/peek.mp4")
T_FL3, T_CAUGHT, T_END = 13.45, 13.53, 19.47
fb = W * H * 3

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p", "/home/claude/mil/_head.mp4"], stdin=subprocess.PIPE)
N = round(T_END * FPS)
white = np.full((H, W, 3), 255, np.float32)
R0 = 70
for i in range(N):
    t = i / FPS
    if t < T_INTRO_END:
        f = intro[min(i, len(intro) - 1)].astype(np.float32)
        f = pop(f, "q1", t, 0.35); f = pop(f, "q2", t, 0.7); f = pop(f, "hint", t, HINT_T); f = pop(f, "sec", t, 2.55, 0.25)
    elif t < T_CD0:
        # white flash: intro -> white -> image
        if t < FLASH1:
            k = (t - T_INTRO_END) / (FLASH1 - T_INTRO_END)
            f0 = intro[min(i, len(intro) - 1)].astype(np.float32)
            for kk, tt in (("q1", 0.35), ("q2", 0.7), ("hint", HINT_T), ("sec", 2.55)):
                f0 = pop(f0, kk, t, tt)
            f = f0 * (1 - k) + white * k
        else:
            k = (t - FLASH1) / (T_CD0 - FLASH1)
            img, _ = view(1.0, 0, 0)
            img = over(img, timer_img(t), W // 2 - 80, 70)
            f = white * (1 - k) + img * k
    elif t < T_REV:
        img, _ = view(1 + 0.02 * (t - T_CD0) / 7, W / 2, H / 2)
        if t < FLASH2 - 0.12:
            f = over(img, timer_img(t), W // 2 - 80, 70)
        else:
            k = (t - (FLASH2 - 0.12)) / 0.12 if t < FLASH2 else 1 - (t - FLASH2) / (T_REV - FLASH2)
            f = img * (1 - k) + white * k
    elif t < T_ZOOM0:
        img, m = view(1.02, W / 2, H / 2)
        x, y = m(gx, gy)
        k = min(1, (t - T_REV) / 0.25)
        r = R0 * (1.6 - 0.6 * ease(k))
        f = over(img, ring_layer(x, y, r, k), 0, 0)
    elif t >= T_CUT:
        j = min(len(caught) - 1, int((t - T_CAUGHT) * FPS)) if t >= T_CAUGHT else 0
        g = caught[max(0, j)].astype(np.float32)
        if t >= T_CAUGHT:
            g = pop(g, "top", t, 13.63) if t < 14.63 else g
            g = pop(g, "lm", t, 15.45); g = pop(g, "bd", t, 17.0); g = pop(g, "hs", t, 18.0)
        if t < T_FL3:
            k = (t - T_CUT) / (T_FL3 - T_CUT)
            img, m = view(2.62, gx, gy)
            f = img * (1 - k) + white * k
        elif t < T_CAUGHT:
            k = (t - T_FL3) / (T_CAUGHT - T_FL3)
            f = white * (1 - k) + g * k
        else:
            f = g
    else:
        k = ease((t - T_ZOOM0) / (T_CUT - T_ZOOM0 - 0.1))
        z = 1.02 + 1.6 * k
        img, m = view(z, gx, gy)
        x, y = m(gx, gy)
        f = over(img, ring_layer(x, y, R0 * z / 1.02, 1), 0, 0)
    enc.stdin.write(f.clip(0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

# tail of the reference episode (flash, "caught", end card) + the reference audio track
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{T_END}", "-i", SRC, "-an", "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                "-pix_fmt", "yuv420p", "-r", "30", "/home/claude/mil/_tail.mp4"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "/home/claude/mil/_head.mp4", "-i", "/home/claude/mil/_tail.mp4", "-i", SRC,
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "19",
                "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
print("ok", out, "gremlin at", round(gx), round(gy))
