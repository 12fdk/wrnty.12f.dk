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

Images are *not* generated here — build.py has no Pillow. It validates that
tools/optimise-images.py has produced the WebP and og.jpg derivatives, and
fails the build if it hasn't.

A post whose source markdown is deleted leaves blog/<slug>/ behind. That stale
directory stays live and indexable while vanishing from the sitemap, feed and
index — an orphan. main() now deletes those directories, or serves a redirect
stub if the slug is listed in REDIRECTS.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
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
MAX_META_TITLE = 62     # the <title>; Google truncates a SERP title around here
MAX_DESCRIPTION = 160
MAX_EXCERPT = 220
MIN_WORDS = 700
ANSWER_MIN_WORDS = 40      # the direct-answer block is sized for a paragraph snippet
ANSWER_MAX_WORDS = 70

# Who the site says it is. Posts are drafted by the weekly job in prompt.md and
# reviewed before they ship, so the organisation is the author and the human is
# the editor — Person schema on `editor`, not on `author`.
ORG = {"name": "12F ApS", "url": "https://12f.dk/"}
EDITOR = {"name": "Robert Jensen", "url": f"{SITE}/about.html"}
CONTACT_EMAIL = "wrnty@12f.dk"

# Anchors the brand in the entity graph — without these, an AI engine has no way
# to connect wrnty the site to wrnty the App Store listing.
SAMEAS = [
    "https://apps.apple.com/us/app/wrnty-warranty-receipts/id6747742961",
    "https://12f.dk/",
]

# Slugs whose post was deleted but whose URL may already be indexed or linked.
# main() writes a noindex meta-refresh stub pointing at the successor instead of
# leaving an orphan live. Drop an entry once the URL has aged out of the index.
REDIRECTS = {
    "how-to-keep-track-of-warranties": "/blog/how-to-organise-receipts/",
    "is-an-extended-warranty-worth-it": "/blog/is-applecare-worth-it/",
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class BuildError(Exception):
    pass


# --- image dimensions ------------------------------------------------------
#
# The markup used to hardcode height="630" on covers and height="675" on figures
# while the real files were 624 and 696 — enough of a mismatch to shift the page
# as each image lands. Read the real numbers out of the file header instead;
# stdlib only, so no Pillow here.

_IMAGE_SIZES: dict[Path, tuple[int, int]] = {}


def _read_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:64]
    if data[:8] == b"\x89PNG\r\n\x1a\n":                       # IHDR is always first
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return (int.from_bytes(data[24:27], "little") + 1,
                    int.from_bytes(data[27:30], "little") + 1)
        if chunk == b"VP8 ":
            return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                    int.from_bytes(data[28:30], "little") & 0x3FFF)
        if chunk == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if data[:2] == b"\xff\xd8":                                # JPEG: walk to a SOF
        blob = path.read_bytes()
        i = 2
        while i < len(blob) - 9:
            if blob[i] != 0xFF:
                i += 1
                continue
            marker = blob[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                return (int.from_bytes(blob[i + 7:i + 9], "big"),
                        int.from_bytes(blob[i + 5:i + 7], "big"))
            i += 2 + int.from_bytes(blob[i + 2:i + 4], "big")
    raise BuildError(f"{path.relative_to(ROOT)}: cannot read image dimensions")


def image_size(src: str) -> tuple[int, int]:
    """(width, height) for a site-absolute image path such as /images/blog/x.webp."""
    path = ROOT / src.lstrip("/")
    if path not in _IMAGE_SIZES:
        if not path.exists():
            raise BuildError(f"image {src} does not exist")
        _IMAGE_SIZES[path] = _read_size(path)
    return _IMAGE_SIZES[path]


def prefer_webp(src: str) -> str:
    """Swap a .png reference for its .webp derivative when one has been built."""
    if src.endswith(".png"):
        webp = src[:-4] + ".webp"
        if (ROOT / webp.lstrip("/")).exists():
            return webp
    return src


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
TABLE_ROW = re.compile(r"^\|.*\|$")
TABLE_RULE = re.compile(r"^\|(?:\s*:?-{2,}:?\s*\|)+$")


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
            served = prefer_webp(src)
            try:
                w, h = image_size(served)
            except BuildError as e:
                raise BuildError(f"{where}: {e}")
            fig = [f'<figure class="post-figure">',
                   f'  <img src="{served}" alt="{html.escape(alt, quote=True)}" '
                   f'width="{w}" height="{h}" loading="lazy" decoding="async">']
            if caption:
                fig.append(f"  <figcaption>{inline(caption)}</figcaption>")
            fig.append("</figure>")
            parts.append("\n".join(fig))
        elif TABLE_ROW.match(first) and len(lines) >= 2 and TABLE_RULE.match(lines[1].strip()):
            parts.append(_table(lines, where))
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


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _table(lines: list[str], where: str) -> str:
    """A pipe table. Comparison tables are the format search engines lift wholesale
    for table snippets, and several of these posts are reference material that
    reads far better as a grid than as prose."""
    header = _cells(lines[0])
    aligns = []
    for spec in _cells(lines[1]):
        left, right = spec.startswith(":"), spec.endswith(":")
        aligns.append("center" if left and right else "right" if right else "left")
    if len(aligns) != len(header):
        raise BuildError(f"{where}: table header has {len(header)} column(s) but the "
                         f"separator row has {len(aligns)}")

    def style(i: int) -> str:
        return f' style="text-align:{aligns[i]}"' if aligns[i] != "left" else ""

    out = ['<div class="table-wrap">', "<table>", "  <thead>", "    <tr>"]
    out += [f"      <th{style(i)}>{inline(c)}</th>" for i, c in enumerate(header)]
    out += ["    </tr>", "  </thead>", "  <tbody>"]
    for n, row in enumerate(lines[2:], start=3):
        if not row.strip():
            continue
        if not TABLE_ROW.match(row.strip()):
            raise BuildError(f"{where}: table row {n} is not pipe-delimited: {row.strip()[:60]!r}")
        cells = _cells(row)
        if len(cells) != len(header):
            raise BuildError(f"{where}: table row {n} has {len(cells)} cell(s), "
                             f"header has {len(header)}")
        out.append("    <tr>")
        out += [f"      <td{style(i)}>{inline(c)}</td>" for i, c in enumerate(cells)]
        out.append("    </tr>")
    out += ["  </tbody>", "</table>", "</div>"]
    return "\n".join(out)


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
        # The 40–70 word standalone answer that sits directly under the H1. Search
        # engines lift this verbatim as a paragraph snippet, so it has to resolve
        # the title's question on its own, without the article around it.
        self.answer = str(meta.get("answer", "")).strip()
        # Outbound corroboration. Generative engines weight claims that point at a
        # primary source, and consumer-law posts without one read as assertion.
        self.sources = [s for s in (meta.get("sources") or []) if isinstance(s, dict)]
        self.howto = [s for s in (meta.get("howto") or []) if isinstance(s, dict)]
        self.howto_name = str(meta.get("howtoName", "")).strip()

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
        if len(self.meta_title) > MAX_META_TITLE:
            raise BuildError(f"{where}: the <title> is {len(self.meta_title)} chars, max "
                             f"{MAX_META_TITLE} — it will truncate in search results. Add a "
                             f"shorter `metaTitle:` (the on-page H1 keeps the full `title:`).")
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

        if not self.answer:
            raise BuildError(f"{where}: missing `answer:` — a standalone {ANSWER_MIN_WORDS}–"
                             f"{ANSWER_MAX_WORDS} word paragraph that answers the title on its "
                             f"own. It renders under the H1 and is what a featured snippet lifts.")
        answer_words = len(self.answer.split())
        if not ANSWER_MIN_WORDS <= answer_words <= ANSWER_MAX_WORDS:
            raise BuildError(f"{where}: `answer:` is {answer_words} words — it must be "
                             f"{ANSWER_MIN_WORDS}–{ANSWER_MAX_WORDS}, the length search "
                             f"engines actually extract as a paragraph snippet")
        if '"' in self.answer:
            raise BuildError(f"{where}: `answer:` contains a straight double-quote (\") — "
                             f"use single or curly quotes so the schema stays clean")

        for s in self.sources:
            if set(s) != {"title", "url"}:
                raise BuildError(f"{where}: each sources entry needs exactly `title:` and `url:`")
            if not str(s["url"]).startswith("https://"):
                raise BuildError(f"{where}: source url {s['url']!r} must be an https:// URL — "
                                 f"cite the primary source, not a summary of it")
        for s in self.howto:
            if set(s) != {"name", "text"}:
                raise BuildError(f"{where}: each howto entry needs exactly `name:` and `text:`")
        if self.howto and not self.howto_name:
            raise BuildError(f"{where}: `howto:` needs a `howtoName:` — the name of the "
                             f"procedure, e.g. 'How to make a warranty claim'")

        self.body_html, self.images = markdown_to_html(body_md, where)
        self.word_count = len(re.findall(r"\b[\w'’-]+\b", re.sub(r"<[^>]+>", " ", self.body_html)))
        self.reading_time = max(1, round(self.word_count / WORDS_PER_MINUTE))

    @property
    def cover(self) -> str:
        """og:image and schema image. Stays JPEG: WebP support across social and
        chat scrapers is still patchy, and this one is never render-blocking."""
        return f"/images/blog/{self.slug}-og.jpg"

    @property
    def card_image(self) -> str:
        """On-page use — hero, index cards, teasers. WebP, ~25KB instead of ~700KB."""
        return f"/images/blog/{self.slug}.webp"

    @property
    def url(self) -> str:
        return f"{SITE}/blog/{self.slug}/"

    @property
    def date_long(self) -> str:
        return f"{self.date.day} {MONTHS[self.date.month - 1]} {self.date.year}"

    # One date format everywhere. Cards used to read "30 Jul 2026" while the
    # article above them read "30 July 2026", which looked like two sites.
    @property
    def date_short(self) -> str:
        return self.date_long

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
        for derived, why in ((p.card_image, "on-page hero and cards"),
                             (p.cover, "og:image and schema image")):
            if not (ROOT / derived.lstrip("/")).exists():
                problems.append(
                    f"{p.where}: {derived} does not exist ({why}) — generate the cover "
                    f"(tools/make-cover.py) then run tools/optimise-images.py")
        for src in p.images:
            if not src.startswith("/"):
                continue
            served = prefer_webp(src)
            if not (ROOT / served.lstrip("/")).exists():
                problems.append(f"{p.where}: inline image {src} does not exist")
            elif served.endswith(".png"):
                problems.append(f"{p.where}: inline image {src} is still a PNG — run "
                                f"tools/optimise-images.py so it ships as WebP")
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
        if not p.cover_alt:
            problems.append(f"{p.where}: missing coverAlt — the cover is also the index card "
                            f"image, and an empty alt there leaves the whole blog grid unlabelled")
        # Corroboration. A post asserting what consumer law says, citing nothing,
        # is exactly what a generative engine declines to quote.
        if not p.sources:
            problems.append(f"{p.where}: no `sources:` — cite at least one primary source "
                            f"(a regulator, a statute, a manufacturer's own warranty page) "
                            f"for the claims this post makes")
        seen_urls: set[str] = set()
        for s in p.sources:
            url = str(s["url"])
            if url in seen_urls:
                problems.append(f"{p.where}: source {url} is listed twice")
            seen_urls.add(url)
            if "wrnty.12f.dk" in url or "12f.dk" in url:
                problems.append(f"{p.where}: source {url} points back at our own site — "
                                f"sources are for outside corroboration")
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
    w, h = image_size(p.card_image)
    body = [
        f'<article class="{cls}">',
        '  <div class="post-card-media">',
        f'    <img src="{p.card_image}" alt="{attr(p.cover_alt)}" '
        f'width="{w}" height="{h}" loading="lazy" decoding="async">',
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
    w, h = image_size(p.card_image)
    return ("\n        <figure class=\"article-hero\">\n"
            f'          <img src="{p.card_image}" alt="{attr(p.cover_alt)}" '
            f'width="{w}" height="{h}" fetchpriority="high" decoding="async">\n'
            "        </figure>\n")


def answer_html(p: Post) -> str:
    """The direct answer, directly under the H1 — the block a featured snippet lifts."""
    return ('\n        <div class="post-answer">\n'
            f'          <p>{inline(p.answer)}</p>\n'
            "        </div>\n")


def sources_html(p: Post) -> str:
    if not p.sources:
        return ""
    rows = ["", '        <section class="post-sources">',
            "          <h2>Where this comes from</h2>",
            "          <ul>"]
    for s in p.sources:
        rows.append(f'            <li><a href="{attr(str(s["url"]))}" '
                    f'rel="noopener nofollow" target="_blank">{attr(str(s["title"]))}</a></li>')
    rows += ["          </ul>", "        </section>"]
    return "\n".join(rows) + "\n"


def howto_jsonld(p: Post) -> str:
    if not p.howto:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": p.howto_name,
        "description": p.description,
        "step": [
            {"@type": "HowToStep", "position": n, "name": s["name"], "text": s["text"],
             "url": f"{p.url}#step-{n}"}
            for n, s in enumerate(p.howto, start=1)
        ],
    }
    body = json.dumps(data, indent=2, ensure_ascii=False)
    return ('\n  <script type="application/ld+json">\n'
            + indent(body, 2) + "\n  </script>\n")


def render_post(p: Post, posts: list[Post], template: str) -> str:
    related = [q for q in posts if q.slug in p.related]
    if not related:                                   # default: the newest others
        related = [q for q in posts if q.slug != p.slug][:2]
    cards = "\n\n".join(indent(card(q, "h3", excerpt=q.teaser_excerpt), 12)
                        for q in related[:2])
    cover_w, cover_h = image_size(p.cover)

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
        "ANSWER": answer_html(p),
        "SOURCES_HTML": sources_html(p),
        "FAQ_HTML": faq_html(p),
        "FAQ_JSONLD": faq_jsonld(p),
        "HOWTO_JSONLD": howto_jsonld(p),
        "RELATED": cards,
        "EDITOR_NAME": attr(EDITOR["name"]),
        "EDITOR_URL": EDITOR["url"],
        "ORG_NAME": attr(ORG["name"]),
        "ORG_URL": ORG["url"],
        "CONTACT_EMAIL": CONTACT_EMAIL,
        "COVER_ALT": attr(p.cover_alt),
        "COVER_WIDTH": str(cover_w),
        "COVER_HEIGHT": str(cover_h),
        "JSON_EDITOR": indent(json.dumps(
            {"@type": "Person", "name": EDITOR["name"], "url": EDITOR["url"]},
            indent=2, ensure_ascii=False), 6).lstrip(),
        "JSON_SAMEAS": indent(json.dumps(SAMEAS, indent=2, ensure_ascii=False), 6).lstrip(),
        "JSON_CITATIONS": indent(json.dumps(
            [{"@type": "CreativeWork", "name": s["title"], "url": s["url"]}
             for s in p.sources], indent=2, ensure_ascii=False), 6).lstrip(),
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
        "dateModified": "{p.modified.isoformat()}",
        "image": "{SITE}{p.cover}"
      }}""" for p in posts)
    sameas = indent(json.dumps(SAMEAS, indent=2, ensure_ascii=False), 6).lstrip()
    return f"""  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Blog",
    "name": "wrnty Blog",
    "description": "Practical advice on warranties, receipts and buying smart.",
    "url": "{SITE}/blog/",
    "publisher": {{
      "@type": "Organization",
      "name": "{ORG['name']}",
      "url": "{ORG['url']}",
      "email": "{CONTACT_EMAIL}",
      "logo": "{SITE}/images/app-icon.png",
      "sameAs": {sameas}
    }},
    "blogPost": [
{items}
    ]
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{SITE}/"}},
      {{"@type": "ListItem", "position": 2, "name": "Blog", "item": "{SITE}/blog/"}}
    ]
  }}
  </script>
"""


def redirect_stub(slug: str, target: str) -> str:
    """A retired post URL. GitHub Pages can't issue a 301, so this is the next best
    thing: noindex so it leaves the index, canonical so any equity consolidates on
    the successor, meta-refresh plus a real link so a visitor still lands somewhere."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Moved — wrnty</title>
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{SITE}{target}">
  <meta http-equiv="refresh" content="0; url={target}">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  <main class="section" style="text-align:center">
    <h1>This post has moved</h1>
    <p>It has been replaced by a more complete one.</p>
    <p><a class="btn btn-primary" href="{target}">Read it here →</a></p>
    <p><a href="/blog/">← All posts</a></p>
  </main>
</body>
</html>
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

    # A directory whose source post is gone is an orphan: still live, still
    # indexable, but absent from the sitemap, the feed, llms.txt and the index,
    # and reachable from nothing. Warning about it was not enough — one sat live
    # for a month carrying the site's only broken internal link. Remove it, or
    # serve a redirect stub when the URL is worth preserving.
    if BLOG_DIR.is_dir():
        live = {p.slug for p in posts}
        on_disk = {d.name for d in BLOG_DIR.iterdir() if d.is_dir()}
        for slug in sorted(REDIRECTS):
            if slug in live:
                print(f"WARN   blog/{slug}/ is in REDIRECTS but posts/{slug}.md exists — "
                      f"drop the REDIRECTS entry, the post is live again")
                continue
            if REDIRECTS[slug].startswith("/blog/") and \
                    REDIRECTS[slug].strip("/").split("/")[-1] not in live:
                print(f"ERROR  REDIRECTS[{slug!r}] points at {REDIRECTS[slug]}, "
                      f"which is not a published post", file=sys.stderr)
                return 1
            write(BLOG_DIR / slug / "index.html", redirect_stub(slug, REDIRECTS[slug]),
                  args.check, changed)
        for slug in sorted(on_disk - live - set(REDIRECTS)):
            changed.append(f"blog/{slug}/ (removed)")
            if not args.check:
                shutil.rmtree(BLOG_DIR / slug)
            print(f"  {'would remove' if args.check else 'removed'}  blog/{slug}/ "
                  f"— no posts/{slug}.md (add it to REDIRECTS to keep the URL alive)")

    verb = "would change" if args.check else "wrote"
    if changed:
        for rel in changed:
            print(f"  {verb}  {rel}")
    print(f"BUILD OK — {len(posts)} post(s), {len(changed)} file(s) {verb}"
          + (" (check only)" if args.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
