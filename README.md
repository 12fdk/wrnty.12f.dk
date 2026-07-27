# wrnty.12f.dk

Landing page for **wrnty**, the warranty & receipt tracker for iPhone and iPad, deployed via GitHub Pages at [wrnty.12f.dk](https://wrnty.12f.dk/).

App Store: <https://apps.apple.com/us/app/wrnty-warranty-receipts/id6747742961>

## Structure

- `index.html` — the landing page
- `privacy-policy.html` — privacy policy
- `404.html` — custom not-found page
- `css/style.css` — the whole design system (CSS custom properties, light + dark)
- `js/main.js` — scroll reveals, sticky-header state, mobile nav
- `images/` — app icon, favicons, OG image, and `screenshots/<locale>/`
- `CNAME` — GitHub Pages custom domain (`wrnty.12f.dk`)
- `robots.txt` / `sitemap.xml` / `llms.txt` — SEO + AI crawlers
- `b0b687723d7b1c12e407c2dfb52947d1.txt` — shared 12F IndexNow key
- `.github/workflows/indexnow.yml` — pings IndexNow on each successful Pages deploy

## Brand

- **Green** `#12934F` (primary) → **Teal** `#0D9488` (gradient)
- **Amber** `#F59E0B` (highlighter / alerts / premium accent)
- System font stack; no web fonts, no frameworks, no build step.

## Develop

No build tools. Serve locally with:

```bash
python3 -m http.server 8000
```

Use absolute paths (`/css/style.css`, `/images/...`) so every page resolves.

## Deploy

Push to `main` → GitHub Pages auto-deploys from the branch root. The IndexNow
workflow runs automatically after a successful deploy and submits changed URLs
to Bing, Yandex, Seznam, Naver and Yep (Google does not participate).

## Assets

Screenshots are resized to 640px-wide WebP from the app's
`fastlane/screenshots/en-US/` renders. The app icon and favicons are derived
from the 1024px App Store icon (black corners flood-filled to transparent).
The OG image is generated with `tools`-style Pillow compositing — regenerate it
if the tagline or brand changes.
