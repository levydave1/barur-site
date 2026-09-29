"""Publish scheduled organic posts to the Barur Facebook page and Instagram.

Queue: social/posts.json
  {
    "live": false,            # false = dry run: log what would be posted, change nothing
    "posts": [
      {
        "id": "2026-10-01-refi-1",
        "publish_at": "2026-10-01T09:00",      # Israel local time
        "text": "...",                          # caption / post body
        "image": "social/img/refi-1.jpg",       # path in this repo (served by Vercel) or full https URL
        "link": "https://barur-mashkanta.co.il/check.html",   # optional, Facebook only (IG links aren't clickable)
        "platforms": ["facebook", "instagram"],
        "status": "pending"                     # draft | pending | published | failed | stale
      }
    ]
  }

Only posts with status "pending" whose time has come are published. A post that is
more than STALE_HOURS late (e.g. the workflow was off for days) is marked "stale"
instead of flooding the page with old posts.

Secrets (GitHub → Settings → Secrets and variables → Actions):
  META_PAGE_TOKEN     system-user token with pages_manage_posts + instagram_content_publish
  TELEGRAM_BOT_TOKEN  optional, for success/failure notices
  TELEGRAM_CHAT_ID    optional
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

GRAPH = "https://graph.facebook.com/v21.0"
PAGE_ID = "1311897388675254"  # ברור משכנתאות
SITE = "https://barur-mashkanta.co.il"
QUEUE = Path(__file__).resolve().parent.parent / "social" / "posts.json"
TZ = ZoneInfo("Asia/Jerusalem")
STALE_HOURS = 24
IG_CAPTION_MAX = 2200

TOKEN = os.environ.get("META_PAGE_TOKEN", "").strip()
FORCE_DRY = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


# ---------- helpers ----------

def log(msg):
    print(msg, flush=True)


def notify(text):
    bot = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot or not chat:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{bot}/sendMessage",
                      json={"chat_id": chat, "text": text}, timeout=20)
    except Exception as e:  # never let a notice break publishing
        log(f"telegram notice failed: {e}")


def scrub(text):
    """Never let a token end up in logs or in posts.json (the repo is public)."""
    text = str(text)
    for secret in (TOKEN, _page_token):
        if secret:
            text = text.replace(secret, "***")
    return text[:500]


def graph(method, path, token, **params):
    # Token goes in the header, never in the URL, so it can't leak into error messages.
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.request(method, f"{GRAPH}/{path}", headers=headers,
                             data=params if method == "POST" else None,
                             params=params if method == "GET" else None, timeout=60)
    except requests.RequestException as e:
        raise RuntimeError(scrub(f"network error: {type(e).__name__}"))
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or "error" in body:
        err = body.get("error", {})
        raise RuntimeError(scrub(f"{err.get('message', r.status_code)} (code {err.get('code')}/{err.get('error_subcode')})"))
    return body


def image_url(post):
    img = (post.get("image") or "").strip()
    if not img:
        return None
    if img.startswith("http"):
        return img
    return f"{SITE}/{img.lstrip('/')}"


def parse_time(s):
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


def validate(post):
    problems = []
    if not post.get("id"):
        problems.append("missing id")
    if not post.get("text", "").strip():
        problems.append("empty text")
    try:
        parse_time(post.get("publish_at", ""))
    except Exception:
        problems.append(f"bad publish_at: {post.get('publish_at')!r}")
    plats = post.get("platforms") or []
    if not plats or any(p not in ("facebook", "instagram") for p in plats):
        problems.append(f"bad platforms: {plats}")
    if "instagram" in plats:
        if not post.get("image"):
            problems.append("instagram needs an image")
        if len(post.get("text", "")) > IG_CAPTION_MAX:
            problems.append("caption longer than 2200 chars")
    return problems


# ---------- Meta ----------

_page_token = None
_ig_id = None


def page_token():
    """A system-user token is exchanged for the page's own token."""
    global _page_token
    if _page_token is None:
        data = graph("GET", PAGE_ID, TOKEN, fields="access_token")
        _page_token = data.get("access_token") or TOKEN
    return _page_token


def ig_account():
    global _ig_id
    if _ig_id is None:
        data = graph("GET", PAGE_ID, page_token(), fields="instagram_business_account")
        acct = data.get("instagram_business_account")
        if not acct:
            raise RuntimeError("no Instagram business account is linked to the page")
        _ig_id = acct["id"]
    return _ig_id


def post_facebook(post):
    tok = page_token()
    img = image_url(post)
    text = post["text"]
    if img:
        if post.get("link"):
            text = f"{text}\n\n{post['link']}"
        res = graph("POST", f"{PAGE_ID}/photos", tok, url=img, caption=text)
        return res.get("post_id") or res.get("id")
    params = {"message": text}
    if post.get("link"):
        params["link"] = post["link"]
    return graph("POST", f"{PAGE_ID}/feed", tok, **params)["id"]


def post_instagram(post):
    tok = page_token()
    ig = ig_account()
    container = graph("POST", f"{ig}/media", tok, image_url=image_url(post), caption=post["text"])["id"]
    for _ in range(20):  # wait for Meta to fetch and process the image
        status = graph("GET", container, tok, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"instagram media container {status}")
        time.sleep(3)
    return graph("POST", f"{ig}/media_publish", tok, creation_id=container)["id"]


PUBLISHERS = {"facebook": post_facebook, "instagram": post_instagram}


# ---------- main ----------

def main():
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    live = bool(queue.get("live")) and not FORCE_DRY
    if live and not TOKEN:
        log("live=true but META_PAGE_TOKEN is not set; running as dry run")
        live = False
    now = datetime.now(TZ)
    log(f"now {now:%Y-%m-%d %H:%M} Israel | mode: {'LIVE' if live else 'DRY RUN'}")

    changed = False
    for post in queue.get("posts", []):
        if post.get("status") != "pending":
            continue
        problems = validate(post)
        if problems:
            log(f"[{post.get('id')}] invalid: {'; '.join(problems)}")
            if live:
                post["status"] = "failed"
                post["error"] = "; ".join(problems)
                changed = True
                notify(f"⚠️ פוסט לא תקין ולא פורסם: {post.get('id')}\n{post['error']}")
            continue

        when = parse_time(post["publish_at"])
        if when > now:
            continue
        if now - when > timedelta(hours=STALE_HOURS):
            log(f"[{post['id']}] stale (was due {when:%Y-%m-%d %H:%M}), skipping")
            if live:
                post["status"] = "stale"
                changed = True
                notify(f"⏭️ פוסט דולג כי איחר ביותר מ-{STALE_HOURS} שעות: {post['id']}")
            continue

        if not live:
            log(f"[{post['id']}] WOULD publish to {post['platforms']} | image: {image_url(post)}")
            log("    " + post["text"][:120].replace("\n", " ") + ("…" if len(post["text"]) > 120 else ""))
            continue

        results = post.setdefault("results", {})
        errors = []
        for plat in post["platforms"]:
            if results.get(plat, {}).get("id"):
                continue  # already went out on an earlier run
            try:
                pid = PUBLISHERS[plat](post)
                results[plat] = {"id": pid, "at": datetime.now(TZ).isoformat(timespec="minutes")}
                log(f"[{post['id']}] {plat}: published {pid}")
            except Exception as e:
                results[plat] = {"error": scrub(e)}
                errors.append(f"{plat}: {scrub(e)}")
                log(f"[{post['id']}] {plat}: FAILED {scrub(e)}")
        changed = True
        if errors:
            post["status"] = "failed"
            post["error"] = " | ".join(errors)
            notify(f"❌ פרסום נכשל: {post['id']}\n" + "\n".join(errors))
        else:
            post["status"] = "published"
            post.pop("error", None)
            notify(f"✅ פורסם: {post['id']} ({', '.join(post['platforms'])})")

    if changed:
        QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
