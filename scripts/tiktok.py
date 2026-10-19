"""TikTok publishing for publish_social.py (Content Posting API, FILE_UPLOAD).

Two modes (env TIKTOK_MODE, default "inbox"):
  inbox   the video lands as a draft in the TikTok app (notification); David adds a
          sound if he wants and taps Post. Works before TikTok audits the app.
          The caption can't be sent with a draft, so it goes to Telegram for copying.
  direct  posts publicly with the caption. Only after TikTok approves the app audit
          (before that, direct posts are forced to private).

Secrets (GitHub Actions):
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET   from developers.tiktok.com -> the app
  TIKTOK_REFRESH_TOKEN                      shown once by barur-mashkanta.co.il/api/tiktok-auth

TikTok may rotate the refresh token. The newest one is kept in social/tiktok-token.enc,
encrypted with a key derived from the client secret, so the public repo never holds it
in readable form.
"""

import base64
import hashlib
import math
import os
import time
from pathlib import Path

import requests

API = "https://open.tiktokapis.com/v2"
ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "social" / "tiktok-token.enc"
CAPTION_MAX = 2200
CHUNK = 10 * 1024 * 1024

KEY = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
MODE = (os.environ.get("TIKTOK_MODE", "") or "inbox").strip().lower()

_access = None
_secrets = []  # anything sensitive, for scrubbing


def configured():
    return bool(KEY and SECRET and (os.environ.get("TIKTOK_REFRESH_TOKEN") or STORE.exists()))


def scrub(text):
    text = str(text)
    for s in _secrets + [SECRET]:
        if s:
            text = text.replace(s, "***")
    return text[:500]


def _fernet():
    from cryptography.fernet import Fernet
    k = hashlib.sha256(("barur-tiktok-store:" + SECRET).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(k))


def _stored_refresh():
    if STORE.exists():
        try:
            return _fernet().decrypt(STORE.read_bytes()).decode()
        except Exception:
            pass
    return os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip()


def access_token():
    global _access
    if _access:
        return _access
    refresh = _stored_refresh()
    _secrets.append(refresh)
    r = requests.post(f"{API}/oauth/token/", timeout=30, data={
        "client_key": KEY, "client_secret": SECRET,
        "grant_type": "refresh_token", "refresh_token": refresh})
    body = r.json() if r.content else {}
    if "access_token" not in body:
        raise RuntimeError(scrub(f"token refresh failed: {body.get('error_description') or body.get('error') or r.status_code}"))
    _access = body["access_token"]
    _secrets.append(_access)
    new = body.get("refresh_token")
    if new and new != refresh:
        _secrets.append(new)
        STORE.write_bytes(_fernet().encrypt(new.encode()))
    return _access


def _call(path, payload):
    r = requests.post(f"{API}/{path}", timeout=60, json=payload, headers={
        "Authorization": f"Bearer {access_token()}",
        "Content-Type": "application/json; charset=UTF-8"})
    body = r.json() if r.content else {}
    err = body.get("error") or {}
    if r.status_code >= 400 or err.get("code") not in (None, "ok"):
        raise RuntimeError(scrub(f"{path}: {err.get('code')} {err.get('message') or r.status_code}"))
    return body.get("data") or {}


def _upload(upload_url, path):
    size = path.stat().st_size
    count = max(1, size // CHUNK)  # TikTok: last chunk absorbs the remainder
    with path.open("rb") as f:
        for i in range(count):
            start = i * CHUNK
            end = size - 1 if i == count - 1 else start + CHUNK - 1
            f.seek(start)
            data = f.read(end - start + 1)
            r = requests.put(upload_url, data=data, timeout=300, headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(f"upload chunk {i + 1}/{count} failed: HTTP {r.status_code}")


def _source(path):
    size = path.stat().st_size
    count = max(1, size // CHUNK)
    chunk = size if count == 1 else CHUNK
    return {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}


def _wait(publish_id, minutes=4):
    deadline = time.time() + minutes * 60
    status = "?"
    while time.time() < deadline:
        d = _call("post/publish/status/fetch/", {"publish_id": publish_id})
        status = d.get("status", "?")
        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            return status, (d.get("publicaly_available_post_id") or [None])[0]
        if status == "FAILED":
            raise RuntimeError(f"TikTok processing failed: {d.get('fail_reason')}")
        time.sleep(10)
    return status, None


def caption(post):
    return (post.get("tiktok_text") or post["text"]).strip()[:CAPTION_MAX]


def publish(post, notify):
    vid = (post.get("video") or "").strip()
    path = (ROOT / vid).resolve()
    if not vid or vid.startswith("http") or not path.is_file():
        raise RuntimeError(f"tiktok needs a video file in the repo, got {vid!r}")

    if MODE == "direct":
        info = _call("post/publish/creator_info/query/", {})
        levels = info.get("privacy_level_options") or []
        privacy = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in levels else (levels[0] if levels else "SELF_ONLY")
        d = _call("post/publish/video/init/", {
            "post_info": {
                "title": caption(post),
                "privacy_level": privacy,
                "disable_comment": False, "disable_duet": False, "disable_stitch": False,
                "is_aigc": bool(post.get("tiktok_aigc", True)),
                "brand_organic_toggle": bool(post.get("tiktok_own_brand", False)),
                "brand_content_toggle": False,
            },
            "source_info": _source(path)})
    else:
        d = _call("post/publish/inbox/video/init/", {"source_info": _source(path)})

    _upload(d["upload_url"], path)
    status, post_id = _wait(d["publish_id"])
    if MODE != "direct":
        notify("📥 טיוטה חדשה בטיקטוק: " + post["id"] + "\n"
               "פתחו את ההתראה באפליקציה, הדביקו את הכיתוב ופרסמו.\n"
               "לסמן \"תוכן שנוצר ב-AI\"" + (" ו\"המותג שלך\"" if post.get("tiktok_own_brand") else "") + ".\n\n"
               + caption(post))
    return post_id or f"{status}:{d['publish_id']}"
