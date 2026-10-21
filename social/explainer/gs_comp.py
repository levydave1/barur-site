"""Green-screen composite of real David into David 2.0's virtual office.
plate (empty office) -> keyed David (scaled/placed to match avatar eyes) -> desk foreground (from plate).
"""
import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920
# measured: source 2160x3840 eyes centre (985,1675), eye distance 202; avatar eyes centre (543,542), distance 135
SCALE = 135 / 202
SRC_EYE = (985, 1675)
DST_EYE = (543, 542)
CROP = (int(SRC_EYE[0] - DST_EYE[0] / SCALE), int(SRC_EYE[1] - DST_EYE[1] / SCALE))  # source top-left
CROP_WH = (int(round(W / SCALE)), int(round(H / SCALE)))
DESK_Y = 1490   # back edge of the desk in the plate (1080x1920)

def ffmpeg_filter():
    """crop+scale applied while decoding the 4K source -> 1080x1920 aligned frame."""
    x, y = CROP; w, h = CROP_WH
    return f'crop={w}:{h}:{x}:{y},scale={W}:{H}:flags=lanczos'

_plate = {}
def plate(path):
    if path not in _plate:
        p = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)
        _plate[path] = np.asarray(p).astype(np.float32)
    return _plate[path]

def desk_mask(pl):
    """foreground = everything from the desk's back edge down (soft 4px edge)."""
    m = np.zeros((H, W), np.float32); m[DESK_Y + 3:, :] = 1.0
    ramp = np.linspace(0, 1, 6); m[DESK_Y - 3:DESK_Y + 3, :] = ramp[:, None]
    return m

_sess = None
def person_mask(rgb):
    """u2net human segmentation at 540x960 -> soft mask 1080x1920, slightly dilated (fine edges come from the key)."""
    global _sess
    from rembg import new_session, remove
    if _sess is None: _sess = new_session('u2net_human_seg')
    small = Image.fromarray(rgb.astype(np.uint8)).resize((540, 960), Image.BILINEAR)
    m = remove(small, session=_sess, only_mask=True)
    m = m.resize((W, H), Image.BILINEAR).point(lambda v: 255 if v > 150 else 0)
    m = m.filter(ImageFilter.GaussianBlur(2))
    return np.asarray(m).astype(np.float32) / 255

def key(rgb, use_person=True):
    """rgb float32 HxWx3 (0-255). returns alpha 0..1 and despilled rgb."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = g - np.maximum(r, b)                      # green excess: bg ~ +12, skin/shirt/beard <= -4
    a = np.clip((7.0 - d) / 6.0, 0, 1)
    am = Image.fromarray((a * 255).astype(np.uint8))
    am = am.filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(am).astype(np.float32) / 255
    if use_person: a = a * person_mask(rgb)   # drops the chair and anything else that isn't David
    # garbage matte: chair corners peek beside the body in the last ~90px above the desk
    gm = np.ones_like(a)
    gm[1395:, :70] = 0; gm[1395:, 1000:] = 0; gm[1430:, :150] = 0; gm[1430:, 930:] = 0
    gm = np.asarray(Image.fromarray((gm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a = a * gm
    # despill: clamp green to the max of red/blue
    out = rgb.copy(); lim = np.maximum(r, b) + 2
    out[..., 1] = np.where(g > lim, lim, g)
    return a, out

SAT, WARM = 1.35, (1.04, 1.0, 0.95)
def grade(rgb, gain, bias):
    x = rgb * gain + bias
    l = (0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2])[..., None]
    x = l + (x - l) * SAT
    x = x * np.array(WARM, np.float32)
    return np.clip(x, 0, 255)

def fit_grade(src_rgb, src_mask, ref_rgb, ref_mask):
    """per-channel mean/std transfer from david (masked) to avatar (masked)."""
    s = src_rgb[src_mask]; t = ref_rgb[ref_mask]
    gain = t.std(0) / (s.std(0) + 1e-6); bias = t.mean(0) - s.mean(0) * gain
    return gain.astype(np.float32), bias.astype(np.float32)

def composite(frame_rgb, pl, gain, bias, dm=None):
    a, fg = key(frame_rgb)
    fg = grade(fg, gain, bias)
    a3 = a[..., None]
    out = pl * (1 - a3) + fg * a3
    if dm is None: dm = desk_mask(pl)
    d3 = dm[..., None]
    out = out * (1 - d3) + pl * d3
    return out.astype(np.uint8), a
