# pawIQ Learn: moving from GitHub Pages to Shopify

Owner: Roger. Prepared Nov 2, 2026. Goal: every Learn post keeps its URL, structured data, sources, dates, byline and look when pawiqpets.com moves to Shopify at launch (planned Jan to early Feb 2027), and the scheduled runs keep publishing without a gap.

## What lives where today
- Live site: GitHub Pages (repo pawiqpets/pawiq), built by `_learn/build.py`.
- Shopify: store s7fghk-ij (pawiq-3.myshopify.com), Paused plan, password on. Blog "learn" (gid://shopify/Blog/122597278066) already exists at /blogs/learn, so URLs match.
- Latest theme: "pawIQ v116 Instagram feed" (gid://shopify/OnlineStoreTheme/195377332594, unpublished). Its blog index section is `pawiq-blog`; its article template is the stock `main-article` (stock Article schema, staff author, no citations or FAQ).
- One article already in Shopify: "How do I build a daily supplement routine for my dog?" (handle daily-supplement-routine-for-dogs, template suffix why-daily-routines-matter, hardcoded copy in sections/pawiq-learn-routines.liquid). The Approved Learn post has the same handle: at import it REPLACES that article in place (articleUpdate), same URL. The Learn Bridge section links to it by article picker, so it keeps working.

## The kit (in this folder)
| File | What it does |
|---|---|
| theme/sections/pawiq-learn-article.liquid | Shopify version of the Learn post page: crumb, H1, standfirst, byline, hero with credit, body, related posts by hub, BlogPosting (with citations), FAQPage and BreadcrumbList JSON-LD. Does not output the stock Article schema. |
| theme/templates/article.learn.json | Article template "learn" using that section. Every imported post gets templateSuffix "learn". |
| theme/assets/pawiq-learn.css | The Learn stylesheet scoped under `.plx` so it cannot touch the theme. Rebuild with `make_css.py` after any learn.css change. |
| theme/snippets/pawiq-learn-head.liquid | noindex on /blogs/learn/tagged/* pages; Bing verification meta tag (replaces BingSiteAuth.xml, which Shopify cannot serve). |
| export.py | Turns `_learn/posts/*.html` + posts.json into articleCreate payloads in out/ (body, summary, image, original publish date, hub tag, SEO title and description, credit, citations, FAQ, reviewed date). `--launch` swaps the pre-launch signup line for the launch closing line. |
| parity.py | `snapshot` saves what every live post carries now; `check [base]` compares the same URLs after cutover and fails on any regression. |

Tested Nov 2, 2026: all 6 live posts export cleanly; the template renders all 6 (via liquidjs) with 3 valid JSON-LD blocks each, the same citation and FAQ counts as live, related posts by hub, no horizontal scroll at 375 px. Baseline snapshot saved (baseline.json). Not yet tested inside Shopify itself (needs decision D1).

## Decisions for Roger
- D1. Test inside Shopify now: upload the 4 theme files to a COPY of the v116 theme and import 1 post as a hidden article, then preview it with you. Nothing goes public (store is paused and password protected). Shopify write: needs your OK.
- D2. Launch closing line (replaces "launching soon, Get launch updates" in every post at cutover): proposed `pawIQ makes daily soft chews for dogs. See the formulas.` linking to /collections/all.
- D3. llms.txt: Shopify cannot serve root files. Proposed: drop it at cutover (Ahrefs, Jun 2026: 97% of llms.txt files get no requests). IndexNow key file goes too; Bing gets the sitemap instead.
- D4. Editorial policy: recreate as a Shopify page with handle editorial-policy (same URL /pages/editorial-policy). Privacy policy moves into Shopify's own policy (same URL /policies/privacy-policy).

## Cutover runbook
Two weeks before (T-14)
1. Add the 4 theme files to the theme that will go live; add `{% render 'pawiq-learn-head' %}` inside `<head>` in layout/theme.liquid.
2. Create the editorial-policy page in Shopify (D4).
3. `python3 _learn/shopify/export.py --launch`, then import every published post: articleCreate with the payload (articleUpdate for daily-supplement-routine-for-dogs). Original publish dates are kept.
4. Preview 2 posts on the theme with Roger. Fix anything, re-export, re-import.

Day before (T-1)
5. Pause Learn publishing: set meta/settings.siteApproved to false on the review page.
6. Re-export and update any article that changed. `python3 _learn/shopify/parity.py snapshot` against the GitHub site.

Cutover (T0)
7. Shopify: choose the plan, remove the password, point www.pawiqpets.com at Shopify (Porkbun DNS: www CNAME to shops.myshopify.com, apex A to 23.227.38.65, per Shopify's domain setup screen).
8. `python3 _learn/shopify/parity.py check`. All OK, or roll back (step 12).
9. Google Search Console: submit https://www.pawiqpets.com/sitemap.xml (Shopify's), request indexing for the 6 oldest posts. Bing Webmaster: verify with the meta tag, submit the same sitemap.
10. Switch the scheduled runs to Shopify publishing (next section), set meta/settings.publishTarget to "shopify", then siteApproved back to true.
11. Check /blogs/learn/tagged/... shows noindex, the index lists every post, and the homepage, editorial policy and privacy policy load.

Rollback
12. Point www DNS back to GitHub Pages (the repo and CNAME file stay in place until 30 days after a clean cutover), set publishTarget back to "github".

After (T+1 to T+30)
13. Tuesdays: the quick check's Search Console inspection covers every post; watch for 404s and "Duplicate, Google chose different canonical".

## Publishing after cutover (paste into the 3 scheduled tasks at T0)
Replaces the push-to-GitHub part of step 5 (Mon + Thu task), step 2 (quick check) and step 3 (urgent publisher). Selection rules (1 a day, approval as the trigger) do not change. Roger's Approve click on the review page is the confirmation for this Shopify write.

```
Publishing target (meta/settings.publishTarget == "shopify", set at launch): for each post to publish:
a. Clone the repo as before. Write _learn/posts/<handle>.html and its posts.json entry (handle, date, hub) exactly as before, so the repo stays the source of truth. Commit "Learn: publish <handle>" and push.
b. Run: python3 _learn/shopify/export.py --launch <handle>. Read _learn/shopify/out/<handle>.json.
c. Load mcp__Shopify__graphql_query and mcp__Shopify__graphql_mutation with ToolSearch. Look up the handle: blog(id:"gid://shopify/Blog/122597278066"){ articles(first:1, query:"handle:<handle>"){ nodes { id } } }. If found, articleUpdate(id, article: payload without blogId); else articleCreate(article: payload). Set publishDate to now. Never touch any other article, product, page, theme or setting.
d. Wait about 1 minute, confirm https://www.pawiqpets.com/blogs/learn/<handle> returns the post with 1 BlogPosting, 1 FAQPage and 1 BreadcrumbList JSON-LD block and the right canonical, then update the review page as before.
Edits to a live post (refresh, search tuning, rules updates): same path, articleUpdate only.
```
