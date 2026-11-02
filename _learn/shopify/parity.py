"""Before/after check for the Shopify cutover.

  python3 _learn/shopify/parity.py snapshot            # save what each live Learn page carries now -> baseline.json
  python3 _learn/shopify/parity.py check [base_url]    # compare the same URLs (default https://www.pawiqpets.com) to the baseline

Checks per page: HTTP 200, canonical, <title>, meta description, robots meta, H1, JSON-LD types
(BlogPosting, FAQPage, BreadcrumbList), citation count, FAQ count, datePublished, author, word count
(within 5%), number of source links, number of <sup> citations, internal Learn links, hero image,
no em or en dashes. Exit code 1 if anything regressed.
"""
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://www.pawiqpets.com"
BASELINE = os.path.join(HERE, "baseline.json")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pawIQ-parity/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def facts(src):
    g = lambda pat: (re.search(pat, src, re.S | re.I) or [None, ""])[1] if re.search(pat, src, re.S | re.I) else ""
    lds = []
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        try:
            lds.append(json.loads(m))
        except ValueError:
            lds.append({"@type": "INVALID"})
    types = sorted(x.get("@type", "?") for x in lds if isinstance(x, dict))
    bp = next((x for x in lds if isinstance(x, dict) and x.get("@type") == "BlogPosting"), {})
    faq = next((x for x in lds if isinstance(x, dict) and x.get("@type") == "FAQPage"), {})
    post = g(r'<article class="wrap post">(.*?)</article>')
    text = html.unescape(re.sub(r"<[^>]+>", " ", post))
    return {
        "title": html.unescape(g(r"<title>(.*?)</title>")).strip(),
        "description": html.unescape(g(r'<meta name="description" content="(.*?)"')),
        "canonical": g(r'<link rel="canonical" href="(.*?)"'),
        "robots": g(r'<meta name="robots" content="(.*?)"'),
        "h1": html.unescape(re.sub(r"<[^>]+>", "", g(r"<h1[^>]*>(.*?)</h1>"))).strip(),
        "ld_types": types,
        "citations": len(bp.get("citation", [])),
        "faq": len(faq.get("mainEntity", [])),
        "datePublished": bp.get("datePublished", ""),
        "author": (bp.get("author") or {}).get("name", ""),
        "words": len(text.split()),
        "sources": len(re.findall(r'<li id="src-\d+">', post)),
        "sups": len(re.findall(r"<sup>", post)),
        "learn_links": sorted(set(re.findall(r'href="(?:https://www\.pawiqpets\.com)?/blogs/learn/([a-z0-9-]+)"', post))),
        "hero": bool(re.search(r'<figure class="hero"><img', src)),
        "dashes": len(re.findall("[—–]", text)),
    }


def urls_from_baseline_or_index():
    _, idx = fetch(BASE + "/blogs/learn")
    return sorted(set(re.findall(r'href="/blogs/learn/([a-z0-9-]+)"', idx)))


def snapshot():
    out = {}
    for h in urls_from_baseline_or_index():
        st, src = fetch(BASE + "/blogs/learn/" + h)
        out[h] = dict(facts(src), status=st)
    json.dump(out, open(BASELINE, "w"), indent=1, ensure_ascii=False)
    print("saved baseline for", len(out), "posts:", ", ".join(out))


def check(base):
    base_data = json.load(open(BASELINE))
    bad = 0
    for h, want in base_data.items():
        try:
            st, src = fetch(base.rstrip("/") + "/blogs/learn/" + h)
        except Exception as ex:  # noqa: BLE001
            print("FAIL", h, "fetch:", ex)
            bad += 1
            continue
        got = dict(facts(src), status=st)
        probs = []
        for k in ("status", "canonical", "title", "description", "h1", "datePublished", "author", "citations", "faq", "sources", "sups", "hero"):
            if got[k] != want[k]:
                probs.append("%s: %r -> %r" % (k, want[k], got[k]))
        for t in ("BlogPosting", "FAQPage", "BreadcrumbList"):
            if t in want["ld_types"] and got["ld_types"].count(t) != 1:
                probs.append("JSON-LD %s count %d" % (t, got["ld_types"].count(t)))
        if "INVALID" in got["ld_types"]:
            probs.append("invalid JSON-LD")
        if "noindex" in (got["robots"] or ""):
            probs.append("noindex on post")
        if want["words"] and abs(got["words"] - want["words"]) > 0.05 * want["words"]:
            probs.append("words %d -> %d" % (want["words"], got["words"]))
        if set(want["learn_links"]) - set(got["learn_links"]):
            probs.append("lost links %s" % sorted(set(want["learn_links"]) - set(got["learn_links"])))
        if got["dashes"]:
            probs.append("%d em or en dashes" % got["dashes"])
        print(("OK  " if not probs else "FAIL"), h, "; ".join(probs))
        bad += bool(probs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    snapshot() if cmd == "snapshot" else check(sys.argv[2] if len(sys.argv) > 2 else BASE)
