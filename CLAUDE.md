# wrnty landing page + blog

Landing page and blog for the **wrnty** iOS app (warranty & receipt tracker),
deployed via GitHub Pages at **wrnty.12f.dk**. Built by 12F ApS.

App Store: <https://apps.apple.com/us/app/wrnty-warranty-receipts/id6747742961>
App repo: `12fdk/wrnty` (separate repo — this is the marketing site only).

## Project structure

- `index.html` — landing page
- `posts/<slug>.md` — **blog source of truth**: frontmatter + markdown, one per post
- `prompt.md` — the brief the weekly automated blog job follows (see below)
- `blog/index.html`, `blog/<slug>/index.html` — **generated** from `posts/` by `tools/build.py`
- `about.html` — who builds wrnty + how the posts are written (the E-E-A-T page)
- `contact.html` — on-site contact details (wrnty@12f.dk)
- `privacy-policy.html`, `404.html`
- `css/style.css` — the whole design system (CSS custom properties, light + dark)
- `js/main.js` — scroll reveals, sticky-header state, mobile nav
- `images/` — app icon, favicons, OG image, App Store badge, `screenshots/<locale>/`, `blog/<slug>.png`
- `tools/build.py` — renders the blog and every file that lists posts
- `tools/make-cover.py` — branded gradient cover card (Pillow); the ComfyUI-down fallback
- `tools/optimise-images.py` — PNG → WebP + og.jpg for `images/blog/` (Pillow)
- `tools/reddit-topics.py` — what people are asking about warranties/receipts, ranked
- `feed.xml` — RSS feed for the blog (generated)
- `CNAME` — GitHub Pages custom domain (wrnty.12f.dk)
- `robots.txt` / `sitemap.xml` / `llms.txt` / `llms-full.txt` — SEO + AI crawlers (blog parts generated)
- `b0b687723d7b1c12e407c2dfb52947d1.txt` + `.github/workflows/indexnow.yml` — IndexNow on deploy

## Brand

- **Green** `#12934F` (primary) → **Teal** `#0D9488` (gradient)
- **Amber** `#F59E0B` (highlighter / alerts / premium accent)
- System font stack; no web fonts, no frameworks, no build step for the static pages.

## Development

No build tools for the static pages. Serve locally:

```bash
python3 -m http.server 8000
```

Use absolute paths (`/css/style.css`, `/images/...`) so blog subfolders resolve.

## Adding a blog post — `posts/*.md` is the source of truth

The blog is **generated**. Write markdown in `posts/<slug>.md`, generate its cover,
then build — never hand-edit `blog/<slug>/index.html`, it will be overwritten.

```bash
python3 tools/make-cover.py <slug> "<Title>" <tag>   # cover → images/blog/<slug>.png
python3 tools/optimise-images.py                      # → <slug>.webp + <slug>-og.jpg, deletes the PNG
python3 tools/build.py --check                        # validate only (schema, links, lengths)
python3 tools/build.py                                # write everything
```

**Images never ship as PNG.** The covers are photographs, so PNG costs ~700KB each
against ~25KB as WebP — on the very image each post marks `fetchpriority="high"`.
`optimise-images.py` writes the WebP for on-page use and a JPEG for `og:image`
(WebP support across social scrapers is still unreliable), then deletes the source.
`build.py` fails if the derivatives are missing.

**A deleted post must not leave its directory behind.** `build.py` removes any
`blog/<slug>/` whose `posts/<slug>.md` is gone — otherwise the page stays live and
indexable while vanishing from the sitemap, feed and index. To keep a retired URL
alive, add it to `REDIRECTS` in `build.py` and it gets a noindex redirect stub
instead of being deleted.

`tools/build.py` renders each post page and rewrites every derived file: the blog
index grid + schema, the homepage teaser, `feed.xml`, the blog URLs in
`sitemap.xml`, and the `## Blog` sections of `llms.txt` and `llms-full.txt`.
Generated regions inside hand-written files are fenced with `BLOG:*:START` /
`BLOG:*:END` markers — leave them in place. The frontmatter schema is documented in
`prompt.md` §5 and enforced by the build. Tags: `warranty-tips`, `organizing`,
`buying-guides` (edit `TAGS` in `build.py` to change the set).

Every post must carry, and the build enforces:
- `answer:` — a 40–70 word standalone answer rendered under the H1. This is what a
  featured snippet lifts, so it has to work with the article removed.
- `sources:` — at least one external primary source (regulator, statute, or a
  manufacturer's own terms; never our own domain). Rendered as "Where this comes
  from" and emitted as schema.org `citation`. `prompt.md` §3 carries the vetted list.
- `coverAlt:` — also used as the alt text on the blog-index card.
- a `<title>` (`metaTitle`, else `"<title> | wrnty"`) of at most 62 characters.

Optional: `howto:` + `howtoName:` emit HowTo schema for genuinely step-by-step posts;
`modified:` sets `dateModified` independently of `date:`.

Authorship: posts are drafted by the weekly job and reviewed before publishing, so
schema names the Organization (12F ApS) as `author` and a Person (Robert Jensen) as
`editor`. `ORG`, `EDITOR`, `CONTACT_EMAIL` and `SAMEAS` are constants at the top of
`build.py`. `about.html` states the arrangement openly — keep the two in step.

## The weekly post writes itself

A **Hermes cron job on the spark** (`wrnty Blog Post`, **Thursdays 09:00
Europe/Copenhagen**) clones this repo and publishes one post a week, generating its
cover on the co-resident ComfyUI. **`prompt.md` is the brief it follows** —
audience, the factual app description, topic selection, tone and the one-mention
nudge budget, factual-accuracy rules (esp. consumer law is not universal), schema,
images, publishing. The cron prompt is a thin wrapper that only says "read
prompt.md and follow it", so **change the strategy by editing `prompt.md` here, in
git** — never by editing the job. Sister setups run the same pattern for
snapdeck.12f.dk, home-stories.12f.dk, event-stories.12f.dk and meugrana.12f.dk.

Topics come from live reader demand rather than invention:

```bash
python3 tools/reddit-topics.py          # ranked digest of what shoppers are asking
python3 tools/reddit-topics.py --json
```

It reads ~12 consumer subreddits (r/personalfinance, r/BuyItForLife, r/appliances,
r/HomeImprovement, r/Insurance …) over Reddit's Atom feeds (the JSON API 403s),
filters out brag-posts and venting, clusters the real questions into themes, and
marks the themes an existing post already covers. Reddit rate-limits it hard, so it
paces, backs off on 429, caches to `.cache/` for a day, and gives up gracefully — a
failed scrape is expected, and `prompt.md` falls back to a ranked topic bank.

## Deployment

Push to `main` → GitHub Pages auto-deploys. The IndexNow workflow submits changed
URLs to Bing/Yandex/Seznam/Naver/Yep after each successful deploy (Google doesn't
participate — it's covered by Search Console + the sitemap).

## Key notes

- Static site — no frameworks, no dependencies for the pages themselves.
- Screenshots come from the app repo's `fastlane/screenshots/en-US/`, resized to
  640px WebP in `images/screenshots/en-US/`.
- Analytics: Umami (privacy-focused) at umami.robert-jensen.dk — the tag is on every page.
- The App Store badge is self-hosted at `/images/app-store-badge.svg`; every page
  carries the Apple Smart App Banner meta (`apple-itunes-app`, app-id 6747742961).
- The homepage "Who it's for" section uses personas, **not** testimonials — the app
  has no public reviews yet. Don't invent quotes; swap in real ones when they exist.
