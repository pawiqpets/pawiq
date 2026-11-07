"""pawIQ Learn site builder (pre-launch, GitHub Pages).

Only APPROVED posts live in this repo (the repo is public). Drafts stay on the review page.
Source posts: _learn/posts/<handle>.html (house template body + header comments)
Registry:     _learn/posts.json  [{"handle": "...", "date": "YYYY-MM-DD", "hub": "Gut health", "updated": "YYYY-MM-DD" (optional, only after a real body-text change)}]
              hub can also come from a <!-- HUB: ... --> header comment in the post file.
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
CSS_HREF = "/assets/learn/learn.css?v=14"
ORG_ID = SITE + "/#organization"
HUBS = ["Gut health", "Skin and coat", "Joints and mobility", "Calm and behavior", "Senior and life stages",
        "Food and safety", "Labels and ingredients", "Daily routines", "Seasonal care"]
NEIGHBOURS = {
    "Gut health": ["Food and safety", "Labels and ingredients"],
    "Skin and coat": ["Labels and ingredients", "Daily routines"],
    "Joints and mobility": ["Senior and life stages", "Daily routines"],
    "Calm and behavior": ["Daily routines", "Senior and life stages"],
    "Senior and life stages": ["Joints and mobility", "Food and safety"],
    "Food and safety": ["Gut health", "Labels and ingredients"],
    "Labels and ingredients": ["Gut health", "Skin and coat"],
    "Daily routines": ["Calm and behavior", "Skin and coat"],
    "Seasonal care": ["Food and safety", "Daily routines"],
}
SIZES = (480, 800, 1200)
e = html.escape



def mark_wide(html):
    """Tables with 3 or more columns get class wide (they scroll sideways on a phone); narrower ones fit as is."""
    def one(m):
        t = m.group(0)
        head = re.search(r"<thead>(.*?)</thead>", t, re.S)
        n = len(re.findall(r"<th[ >]", head.group(1))) if head else 0
        return t.replace("<table>", '<table class="wide">', 1) if n >= 3 else t
    return re.sub(r"<table>.*?</table>", one, html, flags=re.S)


def label_cells(html):
    """Phone tables: copy each column heading onto its cells (data-label) so the CSS can stack rows into cards."""
    def one(m):
        t = m.group(0)
        head = re.search(r"<thead>(.*?)</thead>", t, re.S)
        if not head:
            return t
        names = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1), re.S)]
        def row(r):
            i = [-1]
            def cell(c):
                i[0] += 1
                if c.group(1) == "th" and "scope=\"row\"" in c.group(2): return c.group(0)
                lab = names[i[0]] if i[0] < len(names) else ""
                return "<td%s data-label=\"%s\">" % (c.group(2), lab.replace('"', "&quot;")) if c.group(1) == "td" else c.group(0)
            return re.sub(r"<(td|th)([^>]*)>", cell, r.group(0))
        body = re.search(r"<tbody>.*?</tbody>", t, re.S)
        return t.replace(body.group(0), re.sub(r"<tr>.*?</tr>", row, body.group(0), flags=re.S)) if body else t
    return re.sub(r"<table>.*?</table>", one, html, flags=re.S)

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
        "hero_img": (SITE + "/assets/learn/img/%s.jpg" % handle) if os.path.exists(os.path.join(ROOT, "assets", "learn", "img", handle + ".jpg")) else meta(src, "HERO IMG"),
        "hero_page": hero_page,
        "credit": credit.replace("Credit: ", ""),
        "alt": alt.replace("ALT: ", ""),
        "body": body,
        "mins": max(1, round(words / 230)),
        "url": f"{SITE}/blogs/learn/{handle}",
        "hub": meta(src, "HUB"),
        "local_img": os.path.exists(os.path.join(ROOT, "assets", "learn", "img", handle + ".jpg")),
    }


def make_sizes(handle):
    """Write 480/800/1200 px copies of the hero next to the 1600 px original (needs Pillow; skipped without it)."""
    src = os.path.join(ROOT, "assets", "learn", "img", handle + ".jpg")
    if not os.path.exists(src):
        return
    try:
        from PIL import Image
    except ImportError:
        return
    im = None
    for w in SIZES:
        out = os.path.join(ROOT, "assets", "learn", "img", "%s-%d.jpg" % (handle, w))
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
            continue
        im = im or Image.open(src).convert("RGB")
        h = round(im.height * w / im.width)
        im.resize((w, h), Image.LANCZOS).save(out, "JPEG", quality=72, optimize=True, progressive=True)


def srcset(p):
    """srcset for a local hero, empty for a hotlinked one."""
    if not p.get("local_img"):
        return ""
    parts = []
    for w in SIZES:
        if os.path.exists(os.path.join(ROOT, "assets", "learn", "img", "%s-%d.jpg" % (p["handle"], w))):
            parts.append("%s/assets/learn/img/%s-%d.jpg %dw" % (SITE, p["handle"], w, w))
    if not parts:
        return ""
    parts.append("%s %dw" % (p["hero_img"], 1600))
    return ' srcset="%s"' % ", ".join(parts)


def card_img(p):
    """Card image: the 800 px copy when it exists, else the original."""
    if p.get("local_img") and os.path.exists(os.path.join(ROOT, "assets", "learn", "img", "%s-800.jpg" % p["handle"])):
        return "%s/assets/learn/img/%s-800.jpg" % (SITE, p["handle"])
    return p["hero_img"]


def signup_href(handle):
    return "https://www.pawiqpets.com/?src=learn-%s#signupBlock" % handle


GA_ID = "G-8HJWP2B6DD"  # Google Analytics 4, stream "pawIQ site" (Roger, Nov 2, 2026)


def head(title, desc, url, og_type, og_image, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');
document.addEventListener('click',function(ev){{var a=ev.target.closest&&ev.target.closest('a[href*="#signupBlock"]');if(a)gtag('event','learn_signup_click',{{link_url:a.href,page_path:location.pathname}});}});</script>
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
<link rel="preload" href="/assets/fonts/Thunder-LC.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/Satoshi-Variable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{CSS_HREF}">
<link rel="alternate" type="application/atom+xml" title="pawIQ Learn" href="{SITE}/blogs/learn/feed.xml">
{extra}</head>
<body>
<header class="site-head"><a class="logo" href="/" aria-label="pawIQ home"><img src="{LOGO}" alt="pawIQ" width="120" height="36"></a><a class="head-link" href="/#signupBlock">Get launch updates</a></header>
"""


FOOT = """<footer class="site-foot"><a href="/blogs/learn">Learn</a><span aria-hidden="true"> · </span><a href="/tools">Tools</a><span aria-hidden="true"> · </span><a href="/">Home</a><span aria-hidden="true"> · </span><a href="/#signupBlock">Get launch updates</a><span aria-hidden="true"> · </span><a href="/policies/privacy-policy">Privacy policy</a></footer>
<script>document.querySelectorAll(".table-wrap").forEach(function(w){function f(){w.classList.toggle("more",w.scrollWidth-w.clientWidth-w.scrollLeft>4)}f();w.addEventListener("scroll",f,{passive:true});addEventListener("resize",f)})</script>
</body>
</html>
"""


def faq_items(body):
    sec = re.search(r'<section class="learn-faq">(.*?)</section>', body, re.S)
    if not sec:
        return []
    clean = lambda t: html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<sup>.*?</sup>", "", t, flags=re.S))).strip()
    return [(clean(q), clean(a)) for q, a in re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", sec.group(1), re.S)]


def fmt_date(d):
    return datetime.date.fromisoformat(d).strftime("%B %-d, %Y")


def render_post(p, date, review_html="", others=()):
    article_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"],
        "description": p["mdesc"], "image": [p["hero_img"]],
        "author": {"@type": "Organization", "@id": ORG_ID, "name": "pawIQ", "url": SITE + "/"},
        "publisher": {"@type": "Organization", "@id": ORG_ID, "name": "pawIQ", "url": SITE + "/", "logo": {"@type": "ImageObject", "url": SITE + "/assets/learn/logo-charcoal.png"}},
        "mainEntityOfPage": p["url"], "url": p["url"], "inLanguage": "en-US",
        "isPartOf": {"@type": "Blog", "@id": SITE + "/blogs/learn", "name": "pawIQ Learn"},
        "wordCount": len(re.sub(r"<[^>]+>", " ", p["body"]).split()),
    }
    cites = re.findall(r'<li id="src-\d+">.*?<a href="([^"]+)"[^>]*>(.*?)</a>', p["body"], re.S)
    if cites:
        article_ld["citation"] = [{"@type": "CreativeWork", "name": n.strip(), "url": u} for u, n in cites]
    if date:
        article_ld["datePublished"] = date
        article_ld["dateModified"] = p.get("updated") or date
    lds = [article_ld]
    faqs = faq_items(p["body"])
    if faqs:
        lds.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})
    lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Learn", "item": SITE + "/blogs/learn"},
        {"@type": "ListItem", "position": 3, "name": p["mtitle"].replace(" | pawIQ", ""), "item": p["url"]}]})
    extra = "".join('<script type="application/ld+json">%s</script>\n' % json.dumps(x, ensure_ascii=False) for x in lds)
    body = mark_wide(p["body"]).replace("<table", '<div class="table-wrap"><table').replace("</table>", "</table></div>")
    body = re.sub(r"<p>pawIQ ", '<p class="closing">pawIQ ', body, count=1)
    # Tag the launch-list link with the post it came from, so signups can be traced to Learn.
    body = body.replace('href="https://www.pawiqpets.com/#signupBlock"', 'href="%s"' % signup_href(p["handle"]))
    credit = re.sub(r"Photo by (.*?) on Unsplash",
                    r'Photo by \1 on <a href="%s" rel="noopener" target="_blank">Unsplash</a>' % e(p["hero_page"]), e(p["credit"]))
    reviewed = p.get("updated") or date
    date_label = fmt_date(reviewed) if reviewed else "Draft, not published"
    return head(p["mtitle"], p["mdesc"], p["url"], "article", p["hero_img"], extra) + f"""<main>
<div class="wrap">
<p class="crumb"><a href="/">Home</a> / <a href="/blogs/learn">Learn</a></p>
<h1>{e(p["title"])}</h1>
<p class="standfirst">{e(p["standfirst"])}</p>
<p class="meta">Written by the pawIQ team · {("Last reviewed <time datetime=\"%s\">%s</time>" % (reviewed, date_label)) if reviewed else date_label} · {p["mins"]} min read</p>
</div>
<figure class="hero"><img src="{e(p["hero_img"])}"{srcset(p)} sizes="(max-width: 1100px) 100vw, 1100px" alt="{e(p["alt"])}" width="1600" height="1067" fetchpriority="high"><figcaption>{credit}</figcaption></figure>
<article class="wrap post">
{body}
</article>
{more_block(related(p, others))}</main>
{review_html}""" + FOOT


DIGESTIVE_SYMPTOMS = re.compile(r"\b(stool|poop|diarrh\w*|vomit\w*|stomach upset|upset stomach|upset (?:your|a|the) (?:dog's )?stomach|gurgl\w*|constipat\w*|gas|bloat\w*)\b", re.I)


LOAD = {}  # how many related-cards each post has been given so far: spreads links so no guide is left with almost none (Nov 6, 2026)


def related(p, others):
    """Up to 3 related posts: same hub, then neighbouring hubs, then newest. Evergreen posts never show seasonal ones."""
    pool = [x for x in others if not (p.get("hub") != "Seasonal care" and x[0].get("hub") == "Seasonal care")]
    # Never show a gut-health card on a post that discusses digestive symptoms (Roger, Nov 5, 2026).
    if p.get("hub") != "Gut health" and DIGESTIVE_SYMPTOMS.search(re.sub(r"<[^>]+>", " ", p.get("body", ""))):
        pool = [x for x in pool if x[0].get("hub") != "Gut health"]
    hub = p.get("hub")
    order = [hub] + NEIGHBOURS.get(hub, []) if hub else []
    picks = []
    for h in order:
        picks += sorted([x for x in pool if x[0].get("hub") == h and x not in picks], key=lambda x: LOAD.get(x[0]["handle"], 0))
    picks += sorted([x for x in pool if x not in picks], key=lambda x: LOAD.get(x[0]["handle"], 0))
    picks = picks[:3]
    for x in picks:
        LOAD[x[0]["handle"]] = LOAD.get(x[0]["handle"], 0) + 1
    return picks


def more_block(others):
    picks = list(others)[:3]
    if not picks:
        return '<section class="wrap more"><h2>More from Learn.</h2><p><a href="/blogs/learn">Browse all Learn articles</a></p></section>\n'
    cards = "\n".join(f"""<li class="card"><a href="/blogs/learn/{p["handle"]}">
<img src="{e(card_img(p))}" alt="{e(p["alt"])}" width="800" height="533" loading="lazy">
<span class="card-title">{e(p["title"])}</span></a></li>""" for p, _ in picks)
    return f'<section class="wrap wide more"><h2>More from Learn.</h2><ul class="cards">\n{cards}\n</ul><p><a href="/blogs/learn">Browse all Learn articles</a></p></section>\n'


def card(p, d):
    return f"""<li class="card"><a href="/blogs/learn/{p["handle"]}">
<img src="{e(card_img(p))}" alt="{e(p["alt"])}" width="800" height="533" loading="lazy">
<span class="card-meta">{fmt_date(d)} · {p["mins"]} min read</span>
<span class="card-title">{e(p["title"])}</span>
<span class="card-sf">{e(p["standfirst"])}</span></a></li>"""


def render_index(posts):
    url = SITE + "/blogs/learn"
    title = "Dog health and care guides | pawIQ Learn"
    desc = "Plain answers to the questions dog owners ask about digestion, skin and coat, nutrition and daily care, with every fact linked to its source."
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": "pawIQ Learn", "url": url, "description": desc,
          "publisher": {"@type": "Organization", "@id": ORG_ID, "name": "pawIQ", "url": SITE + "/"},
          "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"], "datePublished": d} for p, d in posts]}
    # Group by hub only once a hub has 3+ posts (single-card rows look empty); the rest go under "More guides".
    big = [h for h in HUBS if sum(1 for p, _ in posts if p.get("hub") == h) >= 3]
    groups = [(h, [(p, d) for p, d in posts if p.get("hub") == h]) for h in big]
    rest = [(p, d) for p, d in posts if p.get("hub") not in big]
    if rest:
        groups.append(("More guides", rest))
    if big:
        sections = "\n".join(f"""<section class="hub"><h2>{e(h)}.</h2><ul class="cards">
{chr(10).join(card(p, d) for p, d in items)}
</ul></section>""" for h, items in groups)
    else:
        sections = '<ul class="cards">\n' + "\n".join(card(p, d) for p, d in posts) + "\n</ul>"
    empty = '<p class="standfirst">New posts are on the way.</p>' if not posts else ""
    return head(title, desc, url, "website", posts[0][0]["hero_img"] if posts else SITE + "/assets/og-image.png",
                '<script type="application/ld+json">%s</script>\n' % json.dumps(ld, ensure_ascii=False)) + f"""<main class="wrap wide">
<h1>Learn.</h1>
<p class="standfirst">Plain answers to the questions dog owners ask, with every fact linked to its source.</p>
{empty}{sections}
<p class="edit-note"><a href="/pages/editorial-policy">How we write Learn</a></p>
</main>
""" + FOOT


def link_report(posts):
    """Warn about posts with fewer than 2 in-body links from other posts, and evergreen posts linking to seasonal ones."""
    hub = {p["handle"]: p.get("hub") for p, _ in posts}
    inbound = {h: 0 for h in hub}
    for p, _ in posts:
        targets = set(re.findall(r'href="(?:https://www\.pawiqpets\.com)?/blogs/learn/([a-z0-9-]+)"', p["body"]))
        for t in targets - {p["handle"]}:
            if t in inbound:
                inbound[t] += 1
            if hub.get(p["handle"]) != "Seasonal care" and hub.get(t) == "Seasonal care":
                print("WARN evergreen links to seasonal:", p["handle"], "->", t)
    for h, n in inbound.items():
        if n < 2 and len(posts) > 2:
            print("WARN fewer than 2 inbound links:", h, "(%d)" % n)
    for h, v in hub.items():
        if not v:
            print("WARN no hub set:", h)


PAGES = [
    # (source file, output path, url path, title, description, h1, article class)
    ("privacy-policy.html", "policies/privacy-policy.html", "/policies/privacy-policy", "Privacy policy | pawIQ",
     "How pawIQ (Pawz Best Group Inc.) collects, uses and protects your personal information.", "Privacy policy.", ""),
    ("editorial-policy.html", "pages/editorial-policy.html", "/pages/editorial-policy", "How we write Learn | pawIQ",
     "Where pawIQ Learn gets its facts, how we use AI, and how we keep guides current.", "How we write Learn.", "quiet"),
    ("dog-age-calculator.html", "tools/dog-age-calculator.html", "/tools/dog-age-calculator", "Dog age calculator: dog years to human years | pawIQ",
     "Free dog age calculator. See your dog's estimated age in human years using a 2020 study, not the old times-7 rule.", "Dog age calculator.", "tool"),
    ("dog-supplement-cost-calculator.html", "tools/dog-supplement-cost-calculator.html", "/tools/dog-supplement-cost-calculator", "Dog supplement cost per day calculator | pawIQ",
     "Free calculator: cost per day and per month for any dog chew, treat or supplement, from the package price and label serving.", "Dog supplement cost calculator.", "tool"),
    ("tools-index.html", "tools/index.html", "/tools", "Free dog calculators and checklists | pawIQ",
     "Free dog age and supplement cost calculators plus printable checklists for boarding, winter walks and reading a supplement label.", "Tools and checklists.", "tool"),
    ("dog-boarding-checklist.html", "tools/dog-boarding-checklist.html", "/tools/dog-boarding-checklist", "Dog boarding checklist: first stay, printable | pawIQ",
     "Printable dog boarding checklist: choosing a facility, vaccines, what to pack, emergency contacts and pickup day, from vet school and AVMA guidance.", "Dog boarding checklist.", "tool"),
    ("cold-weather-dog-walk-checklist.html", "tools/cold-weather-dog-walk-checklist.html", "/tools/cold-weather-dog-walk-checklist", "Cold weather dog walk checklist, printable | pawIQ",
     "Printable winter dog walk checklist: what to check before, during and after a cold walk, from veterinary school and AVMA guidance.", "Cold weather dog walk checklist.", "tool"),
    ("dog-supplement-label-checklist.html", "tools/dog-supplement-label-checklist.html", "/tools/dog-supplement-label-checklist", "Dog supplement label checklist, printable | pawIQ",
     "Printable checklist for reading a dog supplement label: front panel, guaranteed analysis, ingredients, directions and lot number, from AAFCO and FDA.", "Dog supplement label checklist.", "tool"),
]


def render_page(src, url_path, title, desc, h1, cls=""):
    body = open(os.path.join(ROOT, "_learn", "pages", src), encoding="utf-8").read()
    return head(title, desc, SITE + url_path, "website", SITE + "/assets/og-image.png") + f"""<main>
<article class="wrap post{(" " + cls) if cls else ""}">
<h1>{e(h1)}</h1>
{body}
</article>
</main>
""" + FOOT


def update_sitemap(posts):
    path = os.path.join(ROOT, "sitemap.xml")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"\s*<!-- LEARN START -->.*?<!-- LEARN END -->\s*", "\n", s, flags=re.S)
    s = re.sub(r"\n{3,}", "\n\n", s)
    latest = max([d for _, d in posts], default=None)
    entries = [f"  <url>\n    <loc>{SITE}/blogs/learn</loc>\n" + (f"    <lastmod>{latest}</lastmod>\n" if latest else "") + "  </url>",
               f"  <url>\n    <loc>{SITE}/pages/editorial-policy</loc>\n  </url>",
               f"  <url>\n    <loc>{SITE}/tools/dog-age-calculator</loc>\n  </url>",
               f"  <url>\n    <loc>{SITE}/tools/dog-supplement-cost-calculator</loc>\n  </url>"]
    entries += [f"  <url>\n    <loc>{SITE}/tools</loc>\n  </url>"] + [f"  <url>\n    <loc>{SITE}/tools/{h}</loc>\n  </url>" for h in ("dog-boarding-checklist", "cold-weather-dog-walk-checklist", "dog-supplement-label-checklist")]
    entries += [f"  <url>\n    <loc>{p['url']}</loc>\n    <lastmod>{p.get('updated') or d}</lastmod>\n  </url>" for p, d in posts]
    block = "\n  <!-- LEARN START -->\n" + "\n\n".join(entries) + "\n  <!-- LEARN END -->\n"
    s = s.rstrip().replace("</urlset>", "").rstrip() + "\n" + block + "\n</urlset>\n"
    open(path, "w", encoding="utf-8").write(s)


def update_feed(posts):
    """Atom feed of Learn guides. Submitted in Search Console as a sitemap and pinged to the WebSub hub on deploy."""
    hub = "https://pubsubhubbub.appspot.com/"
    furl = SITE + "/blogs/learn/feed.xml"
    latest = max([(p.get("updated") or d) for p, d in posts], default=datetime.date.today().isoformat())
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
           "  <title>pawIQ Learn</title>", "  <subtitle>Dog health and care guides from pawIQ.</subtitle>",
           f'  <link rel="self" type="application/atom+xml" href="{furl}"/>', f'  <link rel="hub" href="{hub}"/>',
           f'  <link rel="alternate" type="text/html" href="{SITE}/blogs/learn"/>', f"  <id>{furl}</id>",
           f"  <updated>{latest}T00:00:00Z</updated>", "  <author><name>pawIQ</name></author>"]
    for p, d in posts:
        out += ["  <entry>", f"    <title>{e(p['title'])}</title>", f'    <link rel="alternate" type="text/html" href="{p["url"]}"/>',
                f"    <id>{p['url']}</id>", f"    <published>{d}T00:00:00Z</published>",
                f"    <updated>{p.get('updated') or d}T00:00:00Z</updated>", f"    <summary>{e(p['mdesc'])}</summary>", "  </entry>"]
    out.append("</feed>")
    open(os.path.join(ROOT, "blogs", "learn", "feed.xml"), "w", encoding="utf-8").write("\n".join(out) + "\n")


def seo_lint(posts):
    """Build-time SEO checks (warnings only): title and meta length, duplicates, hero alt text, H1/title match, canonical host."""
    seen_t, seen_d = {}, {}
    for p, _ in posts:
        h = p["handle"]
        t, d = p["mtitle"], p["mdesc"]
        if len(t) > 62: print("WARN title over 62 chars (%d): %s" % (len(t), h))
        if not 120 <= len(d) <= 165: print("WARN meta description %d chars (aim 120 to 165): %s" % (len(d), h))
        if t in seen_t: print("WARN duplicate title:", h, "=", seen_t[t])
        if d in seen_d: print("WARN duplicate meta description:", h, "=", seen_d[d])
        seen_t[t], seen_d[d] = h, h
        if len(p["alt"].split()) < 4: print("WARN hero alt text too short:", h)
        if not p["url"].startswith("https://www.pawiqpets.com/"): print("WARN non-canonical host:", h)
        if re.search(r"<h1", p["body"]): print("WARN body contains an H1 (template adds one):", h)
        if "learn-sources" not in p["body"]: print("WARN no sources block:", h)


def update_home(posts):
    """Homepage: the 3 newest Learn guides as plain links between the LATEST markers (internal links for crawling)."""
    path = os.path.join(ROOT, "index.html")
    s = open(path, encoding="utf-8").read()
    top = sorted(posts, key=lambda x: (x[1], x[0].get("updated") or ""), reverse=True)[:3]
    lis = "".join('<li><a href="/blogs/learn/%s">%s</a></li>' % (p["handle"], e(p["title"])) for p, _ in top)
    s = re.sub(r"(<!-- LATEST START -->.*?<ul>).*?(</ul></nav>)", lambda m: m.group(1) + lis + m.group(2), s, flags=re.S)
    open(path, "w", encoding="utf-8").write(s)


def main():
    reg = json.load(open(os.path.join(ROOT, "_learn", "posts.json"), encoding="utf-8"))
    reg = sorted(reg, key=lambda r: r["date"], reverse=True)
    posts = []
    for r in reg:
        p = load(r["handle"])
        if r.get("updated"):
            p["updated"] = r["updated"]
        if r.get("hub"):
            p["hub"] = r["hub"]
        make_sizes(r["handle"])
        posts.append((p, r["date"]))
    os.makedirs(os.path.join(ROOT, "blogs", "learn"), exist_ok=True)
    for p, d in posts:
        open(os.path.join(ROOT, "blogs", "learn", p["handle"] + ".html"), "w", encoding="utf-8").write(render_post(p, d, others=[x for x in posts if x[0]["handle"] != p["handle"]]))
    open(os.path.join(ROOT, "blogs", "learn.html"), "w", encoding="utf-8").write(render_index(posts))
    update_sitemap(posts)
    update_feed(posts)
    update_home(posts)
    link_report(posts)
    seo_lint(posts)
    for src, out, url_path, title, desc, h1, cls in PAGES:
        path = os.path.join(ROOT, out)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(render_page(src, url_path, title, desc, h1, cls))
    print("built", len(posts), "posts and", len(PAGES), "pages")


if __name__ == "__main__":
    main()
