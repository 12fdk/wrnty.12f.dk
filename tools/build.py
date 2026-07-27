#!/usr/bin/env python3
"""build.py — regenerate the wrnty blog from posts/*.md.

The site is hand-written static HTML with no build step, which is fine for a
landing page and hopeless for a blog: every new post has to be threaded into the
post page itself, the blog index, the homepage teaser, the RSS feed, the
sitemap, llms.txt and llms-full.txt. So the markdown in posts/ is the source of
truth and this script renders everything else.

    python3 tools/build.py            # validate, then write
    python3 tools/build.py --check    # validate only, write nothing (exit 1 on error)

Zero dependencies, stdlib only. Everything it writes is deterministic: run it
twice and the second run is a no-op.

Generated (do not hand-edit):
    blog/<slug>/index.html
    feed.xml
and the regions between BLOG:START / BLOG:END markers in:
    blog/index.html, index.html, sitemap.xml, llms.txt, llms-full.txt
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
BLOG_DIR = ROOT / "blog"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "post.html"

SITE = "https://wrnty.12f.dk"
TAGS = {"warranty-tips", "organizing", "buying-guides"}
WORDS_PER_MINUTE = 200

MAX_TITLE = 70
MAX_DESCRIPTION = 160
MAX_EXCERPT = 220
MIN_WORDS = 700

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class BuildError(Exception):
    pass


# --- frontmatter -----------------------------------------------------------
#
# A deliberately tiny YAML subset — enough for the post schema and nothing more,
# so there is no PyYAML dependency. Supported: `key: scalar`, `key: [a, b]`,
# block scalars (`>` / `|`), `- item` lists, and lists of single-key mappings.

def _scalar(raw: str):
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] in "\"'" and raw[-1] == raw[0] and len(raw) > 1:
        return raw[1:-1].replace('\\"', '"')
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [_scalar(p) for p in inner.split(",")] if inner else []
    if raw in ("true", "false"):
        return raw == "true"
    return raw


def parse_frontmatter(text: str, where: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise BuildError(f"{where}: file must start with a `---` frontmatter block")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise BuildError(f"{where}: frontmatter block is never closed with `---`")
    head, body = text[4:end + 1], text[end + 5:]

    data: dict = {}
    lines = head.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            raise BuildError(f"{where}: cannot parse frontmatter line {i + 1}: {line!r}")
        key, rest = m.group(1), m.group(2).strip()

        if rest in (">", "|", ">-", "|-"):            # block scalar
            i += 1
            chunk = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith("  ")):
                chunk.append(lines[i].strip())
                i += 1
            joined = "\n".join(chunk) if rest[0] == "|" else " ".join(c for c in chunk if c)
            data[key] = joined.strip()
            continue

        if rest == "":                                 # nested list
            i += 1
            items: list = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith("  ")):
                item_line = lines[i]
                i += 1
                if not item_line.strip():
                    continue
                stripped = item_line.strip()
                if stripped.startswith("- "):
                    after = stripped[2:].strip()
                    sub = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", after)
                    if sub:                            # list of mappings (faq:)
                        items.append({sub.group(1): _scalar(sub.group(2))})
                    else:
                        items.append(_scalar(after))
                else:                                  # continuation of a mapping item
                    sub = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", stripped)
                    if sub and items and isinstance(items[-1], dict):
                        items[-1][sub.group(1)] = _scalar(sub.group(2))
                    else:
                        raise BuildError(f"{where}: cannot parse list item {stripped!r} under {key}:")
            data[key] = items
            continue

        data[key] = _scalar(rest)
        i += 1
    return data, body


# --- markdown --------------------------------------------------------------

INLINE_CODE = re.compile(r"`([^`]+)`")
STRONG = re.compile(r"\*\*(.+?)\*\*")
EM = re.compile(r"(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)$")


def inline(text: str) -> str:
    """Escape, then re-introduce the handful of inline constructs we allow."""
    out = html.escape(text, quote=False)
    placeholders: list[str] = []

    def stash(markup: str) -> str:
        placeholders.append(markup)
        return f"\x00{len(placeholders) - 1}\x00"

    out = INLINE_CODE.sub(lambda m: stash(f"<code>{m.group(1)}</code>"), out)
    out = LINK.sub(lambda m: stash(f'<a href="{m.group(2)}">{m.group(1)}</a>'), out)
    out = STRONG.sub(lambda m: stash(f"<strong>{m.group(1)}</strong>"), out)
    out = EM.sub(lambda m: stash(f"<em>{m.group(1)}</em>"), out)
    for n, markup in enumerate(placeholders):
        markup = STRONG.sub(lambda m: f"<strong>{m.group(1)}</strong>", markup)
        markup = EM.sub(lambda m: f"<em>{m.group(1)}</em>", markup)
        markup = LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', markup)
        out = out.replace(f"\x00{n}\x00", markup)
    return out


def markdown_to_html(md: str, where: str) -> tuple[str, list[str]]:
    """Return (html, image_paths). Blocks are separated by blank lines."""
    blocks = re.split(r"\n\s*\n", md.strip())
    parts: list[str] = []
    images: list[str] = []

    for raw in blocks:
        block = raw.strip("\n")
        if not block.strip():
            continue
        lines = [ln for ln in block.split("\n")]
        first = lines[0].strip()

        if first.startswith("# "):
            raise BuildError(f"{where}: no `# ` heading in the body — the template renders "
                             f"the H1 from `title`. Use `## ` for sections.")
        if first.startswith("### "):
            parts.append(f"<h3>{inline(first[4:].strip())}</h3>")
        elif first.startswith("## "):
            parts.append(f"<h2>{inline(first[3:].strip())}</h2>")
        elif first in ("---", "***", "___"):
            parts.append("<hr>")
        elif IMAGE.match(first):
            m = IMAGE.match(first)
            alt, src, caption = m.group(1), m.group(2), m.group(3)
            if not alt.strip():
                raise BuildError(f"{where}: image {src} has no alt text")
            images.append(src)
            fig = [f'<figure class="post-figure">',
                   f'  <img src="{src}" alt="{html.escape(alt, quote=True)}" '
                   f'width="1200" height="675" loading="lazy" decoding="async">']
            if caption:
                fig.append(f"  <figcaption>{inline(caption)}</figcaption>")
            fig.append("</figure>")
            parts.append("\n".join(fig))
        elif first.startswith("> "):
            inner = "\n".join(ln.strip()[2:] if ln.strip().startswith("> ")
                              else ln.strip().lstrip(">").strip() for ln in lines)
            paras = "\n".join(f"  <p>{inline(p.strip())}</p>"
                              for p in re.split(r"\n\s*\n", inner) if p.strip())
            parts.append(f"<blockquote>\n{paras}\n</blockquote>")
        elif re.match(r"^[-*] ", first):
            items = _list_items(lines, r"^[-*] ", where)
            parts.append("<ul>\n" + "\n".join(f"  <li>{i}</li>" for i in items) + "\n</ul>")
        elif re.match(r"^\d+[.)] ", first):
            items = _list_items(lines, r"^\d+[.)] ", where)
            parts.append("<ol>\n" + "\n".join(f"  <li>{i}</li>" for i in items) + "\n</ol>")
        elif first.startswith("!["):
            raise BuildError(f"{where}: malformed image {first[:80]!r} — an image must be "
                             f"`![alt text](/images/blog/<slug>-N.png)` on its own line, "
                             f"with the path in parentheses")
        else:
            for ln in lines:
                if ln.strip().startswith(("#", ">", "- ", "* ")):
                    raise BuildError(f"{where}: block starting {first!r} mixes a paragraph "
                                     f"with {ln.strip()[:30]!r} — separate them with a blank line")
                if ln.strip().startswith("!["):
                    raise BuildError(f"{where}: image {ln.strip()[:60]!r} must be on its own "
                                     f"line, separated by blank lines")
            parts.append(f"<p>{inline(' '.join(ln.strip() for ln in lines))}</p>")

    return "\n\n".join(parts), images


def _list_items(lines: list[str], marker: str, where: str) -> list[str]:
    items: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        if re.match(marker, stripped):
            items.append(inline(re.sub(marker, "", stripped, count=1)))
        elif stripped and items:
            items[-1] += " " + inline(stripped)          # wrapped list item
        elif stripped:
            raise BuildError(f"{where}: list block starts with a non-item line {stripped!r}")
    return items


# --- post model ------------------------------------------------------------

REQUIRED = ["title", "description", "lede", "excerpt", "tag", "date", "summary", "keywords"]


class Post:
    def __init__(self, path: Path):
        self.path = path
        self.slug = path.stem
        where = f"posts/{path.name}"
        self.where = where
        meta, body_md = parse_frontmatter(path.read_text(encoding="utf-8"), where)
        self.meta = meta
        self.draft = bool(meta.get("draft", False))

        missing = [k for k in REQUIRED if not str(meta.get(k, "")).strip()]
        if missing:
            raise BuildError(f"{where}: missing frontmatter field(s): {', '.join(missing)}")

        self.title = str(meta["title"]).strip()
        self.description = str(meta["description"]).strip()
        self.lede = str(meta["lede"]).strip()
        self.excerpt = str(meta["excerpt"]).strip()
        self.teaser_excerpt = str(meta.get("teaserExcerpt") or self.lede).strip()
        self.summary = str(meta["summary"]).strip()
        self.keywords = str(meta["keywords"]).strip()
        self.tag = str(meta["tag"]).strip()
        self.meta_title = str(meta.get("metaTitle") or f"{self.title} | wrnty").strip()
        self.og_title = str(meta.get("ogTitle") or self.title).strip()
        self.og_description = str(meta.get("ogDescription") or self.description).strip()
        self.twitter_description = str(meta.get("twitterDescription") or self.og_description).strip()
        self.cover_alt = str(meta.get("coverAlt", "")).strip()
        self.hero = bool(meta.get("hero", False))
        self.related = [str(s).strip() for s in (meta.get("related") or [])]
        self.faq = [f for f in (meta.get("faq") or []) if isinstance(f, dict)]

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise BuildError(f"{where}: filename must be a lowercase-kebab slug")
        if self.tag not in TAGS:
            raise BuildError(f"{where}: tag {self.tag!r} is not one of {sorted(TAGS)}")
        try:
            self.date = datetime.strptime(str(meta["date"]).strip(), "%Y-%m-%d").date()
        except ValueError:
            raise BuildError(f"{where}: date must be YYYY-MM-DD, got {meta['date']!r}")
        modified = str(meta.get("modified", "")).strip()
        if modified:
            try:
                self.modified = datetime.strptime(modified, "%Y-%m-%d").date()
            except ValueError:
                raise BuildError(f"{where}: modified must be YYYY-MM-DD, got {modified!r}")
        else:
            self.modified = self.date

        if len(self.title) > MAX_TITLE:
            raise BuildError(f"{where}: title is {len(self.title)} chars, max {MAX_TITLE}")
        if len(self.description) > MAX_DESCRIPTION:
            raise BuildError(f"{where}: description is {len(self.description)} chars, "
                             f"max {MAX_DESCRIPTION}")
        if len(self.excerpt) > MAX_EXCERPT:
            raise BuildError(f"{where}: excerpt is {len(self.excerpt)} chars, max {MAX_EXCERPT}")
        for f in self.faq:
            if set(f) != {"question", "answer"}:
                raise BuildError(f"{where}: each faq entry needs exactly `question:` and `answer:`")
            for k in ("question", "answer"):
                if '"' in str(f[k]):
                    raise BuildError(
                        f"{where}: faq {k} contains a straight double-quote (\") — "
                        f"use single quotes 'like this' or curly quotes for any quoted "
                        f"phrase, so the rendered FAQ and its schema stay clean")

        self.body_html, self.images = markdown_to_html(body_md, where)
        self.word_count = len(re.findall(r"\b[\w'’-]+\b", re.sub(r"<[^>]+>", " ", self.body_html)))
        self.reading_time = max(1, round(self.word_count / WORDS_PER_MINUTE))

    @property
    def cover(self) -> str:
        return f"/images/blog/{self.slug}.png"

    @property
    def card_image(self) -> str:
        webp = ROOT / "images" / "blog" / f"{self.slug}.webp"
        return f"/images/blog/{self.slug}.webp" if webp.exists() else self.cover

    @property
    def url(self) -> str:
        return f"{SITE}/blog/{self.slug}/"

    @property
    def date_long(self) -> str:
        return f"{self.date.day} {MONTHS[self.date.month - 1]} {self.date.year}"

    @property
    def date_short(self) -> str:
        return f"{self.date.day} {MONTHS[self.date.month - 1][:3]} {self.date.year}"

    @property
    def rfc822(self) -> str:
        d = self.date
        wd = WEEKDAYS[datetime(d.year, d.month, d.day).weekday()]
        return f"{wd}, {d.day:02d} {MONTHS[d.month - 1][:3]} {d.year} 08:00:00 +0000"


def load_posts() -> list[Post]:
    if not POSTS_DIR.is_dir():
        raise BuildError("posts/ directory not found")
    posts = [Post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    live = [p for p in posts if not p.draft]
    if not live:
        raise BuildError("no publishable posts found in posts/")
    seen: dict[str, str] = {}
    for p in live:
        key = p.title.lower()
        if key in seen:
            raise BuildError(f"{p.where}: duplicate title, already used by {seen[key]}")
        seen[key] = p.where
    live.sort(key=lambda p: (p.date, p.slug), reverse=True)
    return live


def validate_references(posts: list[Post]) -> list[str]:
    """Cross-post checks: images on disk, related slugs, internal links."""
    problems: list[str] = []
    slugs = {p.slug for p in posts}
    for p in posts:
        if not (ROOT / p.cover.lstrip("/")).exists():
            problems.append(f"{p.where}: cover image {p.cover} does not exist — generate it "
                            f"(tools/make-cover.py) and copy it there")
        for src in p.images:
            if src.startswith("/") and not (ROOT / src.lstrip("/")).exists():
                problems.append(f"{p.where}: inline image {src} does not exist")
        for slug in p.related:
            if slug not in slugs:
                problems.append(f"{p.where}: related slug {slug!r} is not a published post")
            if slug == p.slug:
                problems.append(f"{p.where}: related lists the post itself")
        internal_links = 0
        for href in re.findall(r'href="([^"]*)"', p.body_html):
            if href.startswith(("#", "mailto:", "https://", "http://")):
                continue
            if not href.startswith("/"):
                problems.append(f"{p.where}: link href {href!r} is neither an absolute in-site "
                                f"path (/…) nor a full URL — likely a typo; use /blog/<slug>/")
                continue
            m = re.fullmatch(r"/blog/([a-z0-9-]+)/", href)
            if m and m.group(1) not in slugs:
                problems.append(f"{p.where}: links to /blog/{m.group(1)}/ which does not exist")
            elif not m and href != "/" and not (ROOT / href.lstrip("/").split("#")[0]).exists():
                problems.append(f"{p.where}: links to {href} which is not a file in this site")
            if m and m.group(1) in slugs and m.group(1) != p.slug:
                internal_links += 1
        if len(posts) > 1 and internal_links < 1:
            problems.append(f"{p.where}: no inline link to another post in the body — link to at "
                            f"least one related /blog/<slug>/ where it's genuinely relevant")
        # The soft nudge has to exist: at least one natural in-body mention of the
        # app, and no more than two (the template already adds the CTA).
        mentions = len(re.findall(r"wrnty", re.sub(r"<[^>]+>", "", p.body_html), re.I))
        if mentions < 1:
            problems.append(f"{p.where}: the body never mentions wrnty — include exactly one "
                            f"natural mention where the app is the honest tool for the job")
        elif mentions > 2:
            problems.append(f"{p.where}: wrnty is mentioned {mentions}x in the body — the "
                            f"nudge budget is one (two at the very most); trim it")
        if p.word_count < MIN_WORDS:
            problems.append(f"{p.where}: only {p.word_count} words (minimum {MIN_WORDS})")
        if p.hero and not p.cover_alt:
            problems.append(f"{p.where}: hero: true needs coverAlt — the image is shown in the "
                            f"article and screen readers read that text aloud")
    return problems


# --- rendering -------------------------------------------------------------

def attr(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def indent(block: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + ln if ln.strip() else "" for ln in block.split("\n"))


def card(p: Post, heading: str, extra_class: str = "", excerpt: str | None = None,
         more: bool = False) -> str:
    cls = f"post-card {extra_class}".strip()
    body = [
        f'<article class="{cls}">',
        '  <div class="post-card-media">',
        f'    <img src="{p.card_image}" alt="" width="1200" height="630" loading="lazy">',
        '  </div>',
        '  <div class="post-card-body">',
        f'    <p class="post-meta"><span class="tag">{p.tag}</span>'
        f'<time datetime="{p.date.isoformat()}">{p.date_short}</time>'
        f'<span class="dot" aria-hidden="true"></span>{p.reading_time} min read</p>',
        f'    <{heading} class="post-card-title">'
        f'<a href="/blog/{p.slug}/">{attr(p.title)}</a></{heading}>',
        f'    <p class="post-card-excerpt">{attr(excerpt if excerpt is not None else p.excerpt)}</p>',
    ]
    if more:
        body.append('    <span class="post-card-more">Read it →</span>')
    body += ['  </div>', '</article>']
    return "\n".join(body)


def faq_html(p: Post) -> str:
    if not p.faq:
        return ""
    rows = ["", '        <section class="post-faq">',
            '          <h2>Common questions</h2>']
    for entry in p.faq:
        rows.append('          <details class="post-faq-item">')
        rows.append(f'            <summary>{attr(entry["question"])}</summary>')
        rows.append(f'            <p>{inline(entry["answer"])}</p>')
        rows.append('          </details>')
    rows.append('        </section>')
    return "\n".join(rows) + "\n"


def faq_jsonld(p: Post) -> str:
    if not p.faq:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": e["question"],
             "acceptedAnswer": {"@type": "Answer", "text": e["answer"]}}
            for e in p.faq
        ],
    }
    body = json.dumps(data, indent=2, ensure_ascii=False)
    return ('\n  <script type="application/ld+json">\n'
            + indent(body, 2) + "\n  </script>\n")


def hero_html(p: Post) -> str:
    if not p.hero:
        return ""
    return ("\n        <figure class=\"article-hero\">\n"
            f'          <img src="{p.card_image}" alt="{attr(p.cover_alt)}" '
            'width="1200" height="630" fetchpriority="high" decoding="async">\n'
            "        </figure>\n")


def render_post(p: Post, posts: list[Post], template: str) -> str:
    related = [q for q in posts if q.slug in p.related]
    if not related:                                   # default: the newest others
        related = [q for q in posts if q.slug != p.slug][:2]
    cards = "\n\n".join(indent(card(q, "h3", excerpt=q.teaser_excerpt), 12)
                        for q in related[:2])

    values = {
        "META_TITLE": attr(p.meta_title),
        "DESCRIPTION": attr(p.description),
        "URL": p.url,
        "SITE": SITE,
        "COVER": p.cover,
        "OG_TITLE": attr(p.og_title),
        "OG_DESCRIPTION": attr(p.og_description),
        "TWITTER_DESCRIPTION": attr(p.twitter_description),
        "DATE": p.date.isoformat(),
        "DATE_MODIFIED": p.modified.isoformat(),
        "DATE_LONG": p.date_long,
        "TAG": p.tag,
        "TITLE": attr(p.title),
        "LEDE": inline(p.lede),
        "READING_TIME": str(p.reading_time),
        "WORD_COUNT": str(p.word_count),
        "JSON_TITLE": json.dumps(p.title, ensure_ascii=False),
        "JSON_DESCRIPTION": json.dumps(p.description, ensure_ascii=False),
        "JSON_KEYWORDS": json.dumps(p.keywords, ensure_ascii=False),
        "BODY": indent(p.body_html, 10),
        "HERO": hero_html(p),
        "FAQ_HTML": faq_html(p),
        "FAQ_JSONLD": faq_jsonld(p),
        "RELATED": cards,
    }
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        raise BuildError(f"template placeholder(s) never filled: {sorted(set(leftover))}")
    return out


# --- marker-delimited regions ---------------------------------------------

def replace_region(path: Path, name: str, new_body: str) -> str:
    text = path.read_text(encoding="utf-8")
    start, end = f"BLOG:{name}:START", f"BLOG:{name}:END"
    pattern = re.compile(
        rf"(^[^\n]*{re.escape(start)}[^\n]*\n)(.*?)(^[^\n]*{re.escape(end)}[^\n]*$)",
        re.S | re.M)
    m = pattern.search(text)
    if not m:
        raise BuildError(f"{path.relative_to(ROOT)}: missing {start} / {end} markers")
    return text[:m.start(2)] + new_body + text[m.end(2):]


def replace_section(path: Path, heading: str, new_body: str) -> str:
    """Replace everything under a markdown heading, up to the next same-level one."""
    text = path.read_text(encoding="utf-8")
    level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(rf"(^{re.escape(heading)}[^\n]*\n)(.*?)(?=^#{{1,{level}}} |\Z)",
                         re.S | re.M)
    m = pattern.search(text)
    if not m:
        raise BuildError(f"{path.relative_to(ROOT)}: no {heading!r} section found")
    return text[:m.start(2)] + new_body + text[m.end(2):]


def write(path: Path, content: str, check: bool, changed: list[str]) -> None:
    rel = str(path.relative_to(ROOT))
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == content:
        return
    changed.append(rel)
    if not check:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


# --- the derived files -----------------------------------------------------

def build_feed(posts: list[Post]) -> str:
    items = []
    for p in posts:
        items.append(f"""    <item>
      <title>{attr(p.title)}</title>
      <link>{p.url}</link>
      <guid isPermaLink="true">{p.url}</guid>
      <pubDate>{p.rfc822}</pubDate>
      <category>{p.tag}</category>
      <description>{attr(p.description)}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>wrnty Blog</title>
    <link>{SITE}/blog/</link>
    <description>Practical advice on warranties, receipts and buying smart — from the team behind wrnty.</description>
    <language>en</language>
    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{posts[0].rfc822}</lastBuildDate>

{chr(10).join(items)}

  </channel>
</rss>
"""


def build_sitemap_region(posts: list[Post]) -> str:
    rows = []
    for p in posts:
        rows.append(f"""  <url>
    <loc>{p.url}</loc>
    <lastmod>{p.modified.isoformat()}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.7</priority>
  </url>
""")
    return "".join(rows)


LLMS_BLOG_INTRO = (
    "\nPractical advice on warranties, receipts and buying smart, published at {SITE}/blog/ "
    "(RSS: {SITE}/feed.xml).\n\n")
LLMS_FULL_BLOG_INTRO = (
    "\nThe wrnty blog publishes practical advice on tracking warranties, organising receipts "
    "and buying smart at {SITE}/blog/ (RSS feed: {SITE}/feed.xml). Posts are tagged "
    "`warranty-tips`, `organizing` or `buying-guides`.\n\n")


def build_llms_region(posts: list[Post]) -> str:
    rows = [f"- [{p.title}]({p.url}) — {p.tag}, {p.date.isoformat()}. "
            f"{p.summary.split('. ')[0].rstrip('.')}."
            for p in posts]
    return LLMS_BLOG_INTRO.format(SITE=SITE) + "\n".join(rows) + "\n\n"


def build_llms_full_region(posts: list[Post]) -> str:
    rows = [f"### {p.title} ({p.date.isoformat()}, {p.tag})\n{p.url}\n{p.summary}\n"
            for p in posts]
    return LLMS_FULL_BLOG_INTRO.format(SITE=SITE) + "\n".join(rows) + "\n"


def build_blog_index_region(posts: list[Post]) -> str:
    return "\n\n".join(indent(card(p, "h2", "fade-in", more=True), 10) for p in posts) + "\n"


def build_blog_schema_region(posts: list[Post]) -> str:
    items = ",\n".join(
        f"""      {{
        "@type": "BlogPosting",
        "headline": {json.dumps(p.title, ensure_ascii=False)},
        "url": "{p.url}",
        "datePublished": "{p.date.isoformat()}",
        "image": "{SITE}{p.cover}"
      }}""" for p in posts)
    return f"""  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Blog",
    "name": "wrnty Blog",
    "description": "Practical advice on warranties, receipts and buying smart.",
    "url": "{SITE}/blog/",
    "publisher": {{
      "@type": "Organization",
      "name": "12F ApS",
      "url": "https://12f.dk/",
      "logo": "{SITE}/images/app-icon.png"
    }},
    "blogPost": [
{items}
    ]
  }}
  </script>
"""


def build_teaser_region(posts: list[Post]) -> str:
    return "\n\n".join(indent(card(p, "h3", "fade-in", excerpt=p.teaser_excerpt, more=True), 10)
                       for p in posts[:3]) + "\n"


# --- main ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="validate and report what would change; write nothing")
    args = ap.parse_args()

    try:
        posts = load_posts()
    except BuildError as e:
        print(f"ERROR  {e}", file=sys.stderr)
        return 1

    problems = validate_references(posts)
    if problems:
        for p in problems:
            print(f"ERROR  {p}", file=sys.stderr)
        return 1

    template = TEMPLATE.read_text(encoding="utf-8")
    changed: list[str] = []
    try:
        for p in posts:
            write(BLOG_DIR / p.slug / "index.html", render_post(p, posts, template),
                  args.check, changed)
        write(ROOT / "feed.xml", build_feed(posts), args.check, changed)
        write(BLOG_DIR / "index.html",
              replace_region(BLOG_DIR / "index.html", "CARDS", build_blog_index_region(posts)),
              args.check, changed)
        write(BLOG_DIR / "index.html",
              replace_region(BLOG_DIR / "index.html", "SCHEMA", build_blog_schema_region(posts)),
              args.check, changed)
        write(ROOT / "index.html",
              replace_region(ROOT / "index.html", "TEASER", build_teaser_region(posts)),
              args.check, changed)
        write(ROOT / "sitemap.xml",
              replace_region(ROOT / "sitemap.xml", "URLS", build_sitemap_region(posts)),
              args.check, changed)
        write(ROOT / "llms.txt",
              replace_section(ROOT / "llms.txt", "## Blog", build_llms_region(posts)),
              args.check, changed)
        write(ROOT / "llms-full.txt",
              replace_section(ROOT / "llms-full.txt", "## Blog", build_llms_full_region(posts)),
              args.check, changed)
    except BuildError as e:
        print(f"ERROR  {e}", file=sys.stderr)
        return 1

    if BLOG_DIR.is_dir():
        stale = {d.name for d in BLOG_DIR.iterdir() if d.is_dir()} - {p.slug for p in posts}
        for slug in sorted(stale):
            print(f"WARN   blog/{slug}/ has no posts/{slug}.md — delete it or restore the source")

    verb = "would change" if args.check else "wrote"
    if changed:
        for rel in changed:
            print(f"  {verb}  {rel}")
    print(f"BUILD OK — {len(posts)} post(s), {len(changed)} file(s) {verb}"
          + (" (check only)" if args.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
