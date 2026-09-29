"""Render post images (1080x1080 JPG) in the Barur visual language.

Each post in social/posts.json may carry a "card" object; this script renders it to
social/img/<post id>.jpg and sets the post's "image" field.

  python3 social/cards.py            # render every post that has a card
  python3 social/cards.py <post-id>  # render one

Card types: headline, number, rates, sms, photo, list  (see TEMPLATES below).
Needs: pip install playwright (Chromium). Brand rules: docs "שפה חזותית" in the project.
"""

import html
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "social" / "posts.json"
OUT = ROOT / "social" / "img"
A = (ROOT / "assets").as_uri()

NAVY, TEAL, TEAL_DARK, PAPER, TEAL_SOFT, STONE, LINE = (
    "#0F2A47", "#11978A", "#4FB3A2", "#F5F3EE", "#DCEFEB", "#7C8794", "#DCD8CF")

BASE_CSS = f"""
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-400.woff2);font-weight:400}}
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-600.woff2);font-weight:600}}
@font-face{{font-family:Plex;src:url({A}/fonts/plex-he-700.woff2);font-weight:700}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1080px;font-family:Plex,Arial,sans-serif;background:{PAPER};color:{NAVY};
  display:flex;flex-direction:column;padding:96px;overflow:hidden}}
.main{{flex:1;display:flex;flex-direction:column}}
.label{{font-size:30px;font-weight:600;letter-spacing:.08em;color:{TEAL}}}
h1{{font-size:96px;font-weight:700;line-height:1.1;margin-top:36px}}
.body{{font-size:40px;line-height:1.45;color:{STONE};margin-top:36px;max-width:860px}}
.fine{{font-size:24px;line-height:1.4;color:{STONE}}}
.foot{{display:flex;justify-content:space-between;align-items:center;border-top:3px solid {LINE};padding-top:40px}}
.foot img{{height:88px}}
.url{{font-size:30px;font-weight:600;direction:ltr}}
body.dark{{background:{NAVY};color:{PAPER}}}
body.dark .label{{color:{TEAL_DARK}}}
body.dark .body,body.dark .fine{{color:#AEB8C4}}
body.dark .foot{{border-color:#2A4563}}
"""


def esc(s):
    return html.escape(s or "").replace("\n", "<br>")


def foot(dark=False):
    logo = "logo-horizontal-white.svg" if dark else "logo-horizontal-color.svg"
    return f'<div class="foot"><img src="{A}/img/{logo}"><div class="url">barur-mashkanta.co.il</div></div>'


def page(inner, css="", cls=""):
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
            f'<style>{BASE_CSS}{css}</style></head><body class="{cls}">{inner}</body></html>')


# ---------- templates ----------

def headline(c):
    return page(f'<div class="main"><div class="label">{esc(c.get("label"))}</div>'
                f'<h1>{esc(c["title"])}</h1><div class="body">{esc(c.get("body"))}</div></div>{foot()}')


def number(c):
    css = f""".num{{font-size:260px;font-weight:700;line-height:1;color:{TEAL_DARK};margin-top:40px;letter-spacing:-.02em}}
    .unit{{font-size:52px;font-weight:600;margin-top:24px;line-height:1.3}} .fine{{margin-top:auto;padding-bottom:36px}}"""
    return page(f'<div class="main"><div class="label">{esc(c.get("label"))}</div>'
                f'<div class="num">{esc(c["number"])}</div><div class="unit">{esc(c.get("line"))}</div>'
                f'<div class="fine">{esc(c.get("fine"))}</div></div>{foot(True)}', css, "dark")


def rates(c):
    css = f""".row{{display:flex;gap:48px;margin-top:56px}}
    .box{{flex:1;min-width:0;border:3px solid #2A4563;border-radius:24px;padding:40px 36px}}
    .box b{{display:block;font-size:124px;line-height:1;color:{TEAL_DARK};direction:ltr;text-align:right;white-space:nowrap}}
    .box span{{display:block;font-size:34px;font-weight:600;margin-top:20px}}
    h1{{font-size:84px;margin-top:64px}} .fine{{margin-top:auto;padding-bottom:36px}}"""
    boxes = "".join(f'<div class="box"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in c["items"])
    return page(f'<div class="main"><div class="label">{esc(c.get("label"))}</div><div class="row">{boxes}</div>'
                f'<h1>{esc(c["title"])}</h1><div class="fine">{esc(c.get("fine"))}</div></div>{foot(True)}', css, "dark")


def sms(c):
    css = f""".phone{{background:#fff;border:3px solid {LINE};border-radius:36px;padding:40px 44px;margin-top:40px}}
    .meta{{font-size:24px;color:{STONE};text-align:center;margin-bottom:24px}}
    .bubble{{background:#E9E9EB;border-radius:30px;padding:26px 32px;font-size:36px;line-height:1.4;max-width:80%}}
    .empty{{font-size:32px;color:{STONE};text-align:center;padding:24px 0 8px}}
    h1{{font-size:72px;margin-top:56px}}"""
    return page(f'<div class="main"><div class="label">{esc(c.get("label"))}</div>'
                f'<div class="phone"><div class="meta">{esc(c.get("meta"))}</div><div class="bubble">{esc(c["message"])}</div></div>'
                f'<h1>{esc(c["title"])}</h1><div class="body">{esc(c.get("body"))}</div></div>{foot()}', css)


def photo(c):
    css = f"""body{{padding:0;flex-direction:row}}
    .pic{{width:440px;height:1080px;background:url({A}/img/{c.get("photo", "david-standing.jpg")}) center 18%/cover}}
    .txt{{flex:1;display:flex;flex-direction:column;padding:96px 80px 96px 72px}}
    h1{{font-size:88px}} .body{{font-size:38px}} .foot img{{height:76px}} .url{{font-size:24px}}"""
    return page(f'<div class="txt"><div class="main"><div class="label">{esc(c.get("label"))}</div>'
                f'<h1>{esc(c["title"])}</h1><div class="body">{esc(c.get("body"))}</div></div>{foot()}</div>'
                f'<div class="pic"></div>', css)


def listing(c):
    css = f"""h1{{font-size:72px}} ol{{list-style:none;margin-top:44px}}
    li{{display:flex;gap:28px;align-items:baseline;font-size:36px;line-height:1.35;padding:20px 0;border-bottom:2px solid {LINE}}}
    li:last-child{{border:0}} li b{{color:{TEAL};font-size:40px;min-width:36px}}"""
    items = "".join(f"<li><b>{i}</b><span>{esc(t)}</span></li>" for i, t in enumerate(c["items"], 1))
    return page(f'<div class="main"><div class="label">{esc(c.get("label"))}</div>'
                f'<h1>{esc(c["title"])}</h1><ol>{items}</ol></div>{foot()}', css)


TEMPLATES = {"headline": headline, "number": number, "rates": rates, "sms": sms, "photo": photo, "list": listing}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": 1080, "height": 1080})
        for post in queue["posts"]:
            card = post.get("card")
            if not card or (only and post["id"] != only):
                continue
            tmp = OUT.parent / "templates" / "_render.html"
            tmp.write_text(TEMPLATES[card["type"]](card), encoding="utf-8")
            pg.goto(tmp.as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            target = OUT / f"{post['id']}.jpg"
            pg.screenshot(path=str(target), type="jpeg", quality=90)
            post["image"] = f"social/img/{target.name}"
            print("rendered", target.name)
        browser.close()
    (OUT.parent / "templates" / "_render.html").unlink(missing_ok=True)
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
