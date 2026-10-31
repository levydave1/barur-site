"""Real-person hook: "תקשיבו לזה" + phone with green screen -> insert video takes over the frame.
usage: python3 hook.py <hook.mp4> <insert.mp4> <out.mp4> [start] [cut] [caption]
"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

hook, ins, out = sys.argv[1:4]
T0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.45
TC = float(sys.argv[5]) if len(sys.argv) > 5 else 2.25
CAP = sys.argv[6] if len(sys.argv) > 6 else "תקשיבו לזה."
W, H, FPS, ZOOM = 1080, 1920, 30, 0.30
NAVY, CREAM = (15, 42, 71), (245, 243, 238)
work = "work"
subprocess.run(["mkdir", "-p", work])


def run(*a):
    subprocess.run(list(a), check=True)


def frames(path, start, dur):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path, "-vf",
                          f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    fb = W * H * 3
    while True:
        b = p.stdout.read(fb)
        if len(b) < fb:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


# thumbnail shown on the phone: the insert's title frame
thumb = next(frames(ins, 1.5, 0.1)).astype(np.float32)

# caption (brand style) for the spoken hook
font = ImageFont.truetype("/home/claude/heygen/site/assets/fonts/plex-he-700.ttf", 64) if False else None


def caption_png():
    from playwright.sync_api import sync_playwright
    import edit
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(f"""<html><head><meta charset="utf-8"><style>{edit.FONTS}
.c{{position:absolute;left:70px;right:70px;top:1490px;display:flex;justify-content:center}}
.c span{{background:#0F2A47;color:#F5F3EE;font-weight:700;font-size:64px;line-height:1.3;padding:12px 34px 18px;border-radius:16px}}</style></head>
<body><div class="c"><span>{CAP}</span></div></body></html>""")
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(100)
        pg.screenshot(path=f"{work}/cap.png", omit_background=True); b.close()
    return np.asarray(Image.open(f"{work}/cap.png").convert("RGBA"), np.float32)


sys.path.insert(0, "/home/claude/heygen")
cap = caption_png() if CAP else np.zeros((H, W, 4), np.float32)
ca = cap[..., 3:4] / 255.0

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p", f"{work}/hookv.mp4"], stdin=subprocess.PIPE)
last = None
n = 0
for f in frames(hook, T0, TC - T0):
    x = f.astype(np.float32)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mm = ((g > 110) & (g > r * 1.35) & (b < g * 1.08)) | (np.minimum(np.minimum(r, g), b) > 215) | ((g > 180) & (b > 180) & (r < g * 0.92))
    from scipy import ndimage
    lab, nl = ndimage.label(mm)
    if nl > 1:
        sizes = ndimage.sum(mm, lab, range(1, nl + 1)); mm = lab == (1 + int(np.argmax(sizes)))
    mm = ndimage.binary_fill_holes(mm)
    m = mm.astype(np.uint8) * 255
    mi = Image.fromarray(m).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    a = (np.asarray(mi, np.float32) / 255.0)[..., None]
    ys, xs = np.nonzero(m > 128)
    if len(xs) > 500:
        x0, x1, y0, y1 = np.percentile(xs, 1), np.percentile(xs, 99), np.percentile(ys, 1), np.percentile(ys, 99)
        bw, bh = max(2, int(x1 - x0)), max(2, int(y1 - y0))
        s = max(bw / W, bh / H)
        tw, th = int(W * s) + 2, int(H * s) + 2
        t = np.asarray(Image.fromarray(thumb.astype(np.uint8)).resize((tw, th), Image.LANCZOS), np.float32)
        canvas = np.zeros_like(x)
        ox, oy = int((x0 + x1) / 2 - tw / 2), int((y0 + y1) / 2 - th / 2)
        sx0, sy0 = max(0, -ox), max(0, -oy)
        dx0, dy0 = max(0, ox), max(0, oy)
        dx1, dy1 = min(W, ox + tw), min(H, oy + th)
        canvas[dy0:dy1, dx0:dx1] = t[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0]
        # despill: pull green toward the average of r/b on the soft edge
        sp = np.minimum(g, (r + b) / 2 + 10)
        x = np.stack([r, sp, b], -1)
        x = x * (1 - a) + canvas * a
    cov = float((m > 128).mean())
    k = max(0.0, min(1.0, 1 - (cov - 0.12) / 0.15))
    x = x * (1 - ca * k) + cap[..., :3] * ca * k
    last = x
    enc.stdin.write(x.clip(0, 255).astype(np.uint8).tobytes()); n += 1
enc.stdin.close(); enc.wait()
Image.fromarray(last.clip(0, 255).astype(np.uint8)).save(f"{work}/last.png")
DH = n / FPS

# transition: insert zooms from the phone size to full frame over the frozen last hook frame
run("ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "60", "-i", f"{work}/last.png", "-i", ins, "-filter_complex",
    f"[1:v]fps={FPS},scale='trunc(if(lt(t,{ZOOM}),{W}*(0.78+0.22*t/{ZOOM}),{W})/2)*2':'trunc(if(lt(t,{ZOOM}),{H}*(0.78+0.22*t/{ZOOM}),{H})/2)*2':eval=frame[s];"
    f"[0:v][s]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[v]",
    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", f"{work}/insv.mp4")

# hook audio: denoise + level, then a whoosh into the cut
run("ffmpeg", "-v", "error", "-y", "-ss", str(T0), "-t", f"{DH:.3f}", "-i", hook, "-f", "lavfi", "-t", "0.5", "-i",
    "anoisesrc=d=0.5:c=pink:r=48000:a=0.5", "-filter_complex",
    "[0:a]highpass=f=90,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000,pan=stereo|c0=c0|c1=c0[v];"
    f"[1:a]highpass=f=300,lowpass=f=6000,afade=t=in:d=0.35,volume=0.3,pan=stereo|c0=c0|c1=c0,adelay={int(max(0, DH - .4) * 1000)}|{int(max(0, DH - .4) * 1000)}[w];"
    "[v][w]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k", f"{work}/hooka.m4a")
run("ffmpeg", "-v", "error", "-y", "-i", f"{work}/hookv.mp4", "-i", f"{work}/hooka.m4a", "-c:v", "copy", "-c:a", "copy", "-shortest", f"{work}/hook.mp4")
run("ffmpeg", "-v", "error", "-y", "-i", f"{work}/hook.mp4", "-i", f"{work}/insv.mp4", "-filter_complex",
    "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "19",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out)
print("ok", out, round(DH, 2))
