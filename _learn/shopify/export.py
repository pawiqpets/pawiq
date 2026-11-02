"""Turn Learn posts into Shopify article payloads (one JSON file per post) for the Admin GraphQL API.

Source of truth stays the same as the GitHub Pages build: _learn/posts/<handle>.html + _learn/posts.json.
Each payload is the `article` input for articleCreate (or articleUpdate when the handle already exists
in Shopify), plus the metafields the theme section pawiq-learn-article.liquid reads.

Usage:
  python3 _learn/shopify/export.py                 # every post in posts.json
  python3 _learn/shopify/export.py <handle> ...    # only these
  --launch   use the post-launch closing line instead of the pre-launch signup line
Output: _learn/shopify/out/<handle>.json  {"handle", "mode_hint", "article": {...}}
The blogId is filled in by the caller (gid://shopify/Blog/122597278066 is the "learn" blog).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build  # noqa: E402  (the GitHub Pages builder: same parsing, so both sites match)

BLOG_ID = "gid://shopify/Blog/122597278066"
SITE = build.SITE
PRELAUNCH_LINK = 'href="https://www.pawiqpets.com/#signupBlock"'
# Post-launch closing line: board session Nov 2, 2026, Roger picked it the same day (MIGRATION.md, D2).
LAUNCH_CLOSING = '<p class="closing">pawIQ makes soft chew supplements for dogs. <a href="/collections/all">See what each formula is for</a>.</p>'


def body_for_shopify(p, launch):
    body = p["body"].replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    body = re.sub(r"<p>pawIQ ", '<p class="closing">pawIQ ', body, count=1)
    if launch:
        body = re.sub(r'<p class="closing">pawIQ .*?</p>', LAUNCH_CLOSING, body, count=1, flags=re.S)
    else:
        body = body.replace(PRELAUNCH_LINK, 'href="%s"' % build.signup_href(p["handle"]))
    # Internal links become root-relative so they work on the Shopify domain before DNS moves too.
    body = body.replace('href="https://www.pawiqpets.com/blogs/learn', 'href="/blogs/learn')
    return body


def payload(entry, launch=False):
    p = build.load(entry["handle"])
    hub = entry.get("hub") or p.get("hub") or ""
    cites = re.findall(r'<li id="src-\d+">.*?<a href="([^"]+)"[^>]*>(.*?)</a>', p["body"], re.S)
    citations = [{"@type": "CreativeWork", "name": re.sub(r"<[^>]+>", "", n).strip(), "url": u} for u, n in cites]
    faqs = [{"q": q, "a": a} for q, a in build.faq_items(p["body"])]
    img = SITE + "/assets/learn/img/%s.jpg" % entry["handle"] if p.get("local_img") else p["hero_img"]
    mf = [
        {"namespace": "global", "key": "title_tag", "type": "single_line_text_field", "value": p["mtitle"]},
        {"namespace": "global", "key": "description_tag", "type": "single_line_text_field", "value": p["mdesc"]},
        {"namespace": "learn", "key": "hero_credit", "type": "single_line_text_field", "value": p["credit"]},
        {"namespace": "learn", "key": "hero_page", "type": "url", "value": p["hero_page"]},
        {"namespace": "learn", "key": "reviewed", "type": "date", "value": entry.get("updated") or entry["date"]},
        {"namespace": "learn", "key": "citations", "type": "json", "value": json.dumps(citations, ensure_ascii=False)},
        {"namespace": "learn", "key": "faq", "type": "json", "value": json.dumps(faqs, ensure_ascii=False)},
    ]
    article = {
        "blogId": BLOG_ID,
        "title": p["title"],
        "handle": entry["handle"],
        "body": body_for_shopify(p, launch),
        "summary": "<p>%s</p>" % build.e(p["standfirst"]),
        "author": {"name": "pawIQ team"},
        "image": {"url": img, "altText": p["alt"]},
        "isPublished": True,
        "publishDate": entry["date"] + "T16:00:00Z",
        "tags": ["hub:" + hub] if hub else [],
        "templateSuffix": "learn",
        "metafields": mf,
    }
    return {"handle": entry["handle"], "article": article}


def main(argv):
    launch = "--launch" in argv
    want = [a for a in argv if not a.startswith("--")]
    reg = json.load(open(os.path.join(build.ROOT, "_learn", "posts.json"), encoding="utf-8"))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    n = 0
    for entry in reg:
        if want and entry["handle"] not in want:
            continue
        pl = payload(entry, launch)
        body = pl["article"]["body"]
        assert "—" not in body and "–" not in body, entry["handle"] + ": em or en dash"
        json.dump(pl, open(os.path.join(HERE, "out", entry["handle"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n += 1
    print("exported", n, "posts to", os.path.join(HERE, "out"))


if __name__ == "__main__":
    main(sys.argv[1:])
