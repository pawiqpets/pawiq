"""pawIQ Learn site builder (pre-launch, GitHub Pages).

Only APPROVED posts live in this repo (the repo is public). Drafts stay on the review page.
Source posts: _learn/posts/<handle>.html (house template body + header comments)
Registry:     _learn/posts.json  [{"handle": "...", "date": "YYYY-MM-DD"}]
Outputs:      blogs/learn.html                 -> https://www.pawiqpets.com/blogs/learn
              blogs/learn/<handle>.html        -> https://www.pawiqpets.com/blogs/learn/<handle>
              sitemap.xml (Learn URLs inside the LEARN markers only; other entries untouched)
Addresses match Shopify's blog URLs so posts can be imported at launch without redirects.
Usage: python3 _learn/build.py
"""
import datetime
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.pawiqpets.com"
LOGO = "/assets/learn/logo-charcoal.svg"
CSS_HREF = "/assets/learn/learn.css?v=1"
e = html.escape


def meta(src, key):
    m = re.search(r"<!-- %s: (.*?) -->" % re.escape(key), src, re.S)
    return m.group(1).strip() if m else ""


def load(handle):
    src = open(os.path.join(ROOT, "_learn", "posts", handle + ".html"), encoding="utf-8").read()
    hero_page, credit, alt = [x.strip() for x in meta(src, "HERO").split("|")]
    body = re.sub(r"<!--.*?-->", "", src, flags=re.S).strip()
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    return {
        "handle": handle,
        "title": meta(src, "TITLE"),
        "standfirst": meta(src, "STANDFIRST (excerpt)"),
        "mtitle": meta(src, "META TITLE"),
        "mdesc": meta(src, "META DESCRIPTION"),
        "hero_img": meta(src, "HERO IMG"),
        "hero_page": hero_page,
        "credit": credit.replace("Credit: ", ""),
        "alt": alt.replace("ALT: ", ""),
        "body": body,
        "mins": max(1, round(words / 230)),
        "url": f"{SITE}/blogs/learn/{handle}",
    }


def head(title, desc, url, og_type, og_image, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#F6F6F1">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="pawIQ">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(og_image)}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="/assets/fonts/Thunder-LC.ttf" as="font" type="font/ttf" crossorigin>
<link rel="preload" href="/assets/fonts/Satoshi-Variable.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="{CSS_HREF}">
{extra}</head>
<body>
<header class="site-head"><a class="logo" href="/" aria-label="pawIQ home"><img src="{LOGO}" alt="pawIQ" width="120" height="36"></a><a class="head-link" href="/#signupBlock">Get launch updates</a></header>
"""


FOOT = """<footer class="site-foot"><a href="/blogs/learn">Learn</a><span aria-hidden="true"> · </span><a href="/">Home</a><span aria-hidden="true"> · </span><a href="/#signupBlock">Get launch updates</a></footer>
</body>
</html>
"""


def faq_items(body):
    sec = re.search(r'<section class="learn-faq">(.*?)</section>', body, re.S)
    if not sec:
        return []
    clean = lambda t: html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
    return [(clean(q), clean(a)) for q, a in re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", sec.group(1), re.S)]


def fmt_date(d):
    return datetime.date.fromisoformat(d).strftime("%B %-d, %Y")


def render_post(p, date, review_html=""):
    article_ld = {
        "@context": "https://schema.org", "@type": "Article", "headline": p["title"],
        "description": p["mdesc"], "image": [p["hero_img"]],
        "author": {"@type": "Organization", "name": "pawIQ", "url": SITE + "/"},
        "publisher": {"@type": "Organization", "name": "pawIQ", "logo": {"@type": "ImageObject", "url": SITE + "/assets/logo-white.png"}},
        "mainEntityOfPage": p["url"], "inLanguage": "en-US",
    }
    if date:
        article_ld["datePublished"] = date
        article_ld["dateModified"] = date
    lds = [article_ld]
    faqs = faq_items(p["body"])
    if faqs:
        lds.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})
    lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Learn", "item": SITE + "/blogs/learn"},
        {"@type": "ListItem", "position": 2, "name": p["title"], "item": p["url"]}]})
    extra = "".join('<script type="application/ld+json">%s</script>\n' % json.dumps(x, ensure_ascii=False) for x in lds)
    body = p["body"].replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    body = re.sub(r"<p>pawIQ ", '<p class="closing">pawIQ ', body, count=1)
    credit = re.sub(r"Photo by (.*?) on Unsplash",
                    r'Photo by \1 on <a href="%s" rel="noopener" target="_blank">Unsplash</a>' % e(p["hero_page"]), e(p["credit"]))
    date_label = fmt_date(date) if date else "Draft, not published"
    return head(p["mtitle"], p["mdesc"], p["url"], "article", p["hero_img"], extra) + f"""<main>
<div class="wrap">
<p class="crumb"><a href="/blogs/learn">Learn</a></p>
<h1>{e(p["title"])}</h1>
<p class="standfirst">{e(p["standfirst"])}</p>
<p class="meta">{date_label} · {p["mins"]} min read</p>
</div>
<figure class="hero"><img src="{e(p["hero_img"])}" alt="{e(p["alt"])}" width="1600" height="1067" fetchpriority="high"><figcaption>{credit}</figcaption></figure>
<article class="wrap post">
{body}
</article>
</main>
{review_html}""" + FOOT


def render_index(posts):
    url = SITE + "/blogs/learn"
    title = "Learn | pawIQ"
    desc = "Plain answers to the questions dog owners ask about digestion, skin and coat, nutrition and daily care, with every fact linked to its source."
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": "pawIQ Learn", "url": url, "description": desc,
          "publisher": {"@type": "Organization", "name": "pawIQ", "url": SITE + "/"},
          "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"], "datePublished": d} for p, d in posts]}
    cards = "\n".join(f"""<li class="card"><a href="/blogs/learn/{p["handle"]}">
<img src="{e(p["hero_img"])}" alt="{e(p["alt"])}" width="800" height="533" loading="lazy">
<span class="card-meta">{fmt_date(d)} · {p["mins"]} min read</span>
<span class="card-title">{e(p["title"])}</span>
<span class="card-sf">{e(p["standfirst"])}</span></a></li>""" for p, d in posts)
    empty = '<p class="standfirst">New posts are on the way.</p>' if not posts else ""
    return head(title, desc, url, "website", posts[0][0]["hero_img"] if posts else SITE + "/assets/og-image.png",
                '<script type="application/ld+json">%s</script>\n' % json.dumps(ld, ensure_ascii=False)) + f"""<main class="wrap wide">
<h1>Learn.</h1>
<p class="standfirst">Plain answers to the questions dog owners ask, with every fact linked to its source.</p>
{empty}<ul class="cards">
{cards}
</ul>
</main>
""" + FOOT


def update_sitemap(posts):
    path = os.path.join(ROOT, "sitemap.xml")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"\n  <!-- LEARN START -->.*?<!-- LEARN END -->\n", "\n", s, flags=re.S)
    latest = max([d for _, d in posts], default=None)
    entries = [f"  <url>\n    <loc>{SITE}/blogs/learn</loc>\n" + (f"    <lastmod>{latest}</lastmod>\n" if latest else "") + "  </url>"]
    entries += [f"  <url>\n    <loc>{p['url']}</loc>\n    <lastmod>{d}</lastmod>\n  </url>" for p, d in posts]
    block = "\n  <!-- LEARN START -->\n" + "\n\n".join(entries) + "\n  <!-- LEARN END -->\n"
    s = s.replace("\n</urlset>", block + "\n</urlset>")
    open(path, "w", encoding="utf-8").write(s)


def main():
    reg = json.load(open(os.path.join(ROOT, "_learn", "posts.json"), encoding="utf-8"))
    reg = sorted(reg, key=lambda r: r["date"], reverse=True)
    posts = [(load(r["handle"]), r["date"]) for r in reg]
    os.makedirs(os.path.join(ROOT, "blogs", "learn"), exist_ok=True)
    for p, d in posts:
        open(os.path.join(ROOT, "blogs", "learn", p["handle"] + ".html"), "w", encoding="utf-8").write(render_post(p, d))
    open(os.path.join(ROOT, "blogs", "learn.html"), "w", encoding="utf-8").write(render_index(posts))
    update_sitemap(posts)
    print("built", len(posts), "posts")


if __name__ == "__main__":
    main()
