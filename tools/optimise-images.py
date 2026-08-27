#!/usr/bin/env python3
"""optimise-images.py — turn the blog's source PNGs into web-ready derivatives.

The cover generator (ComfyUI or make-cover.py) writes photographic PNGs, which
is the worst possible format for them: a 1200x624 photo lands at 650-950KB as
PNG and under 40KB as WebP. Since every post marks its cover fetchpriority=high,
that PNG was the LCP element on every article page.

For each images/blog/<name>.png this writes:

    <name>.webp     on-page use (hero, cards, in-body figures)
    <name>-og.jpg   only for <slug>.png — the og:image and schema image, where
                    WebP support across social scrapers is still unreliable

and then removes the source PNG, which nothing references any more.

    python3 tools/optimise-images.py            # convert, then delete the PNGs
    python3 tools/optimise-images.py --check    # report only, exit 1 if work is due
    python3 tools/optimise-images.py --keep-png # convert but keep the sources

Needs Pillow (pip install Pillow), same as make-cover.py. build.py stays
stdlib-only and merely validates that the derivatives exist.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BLOG_IMAGES = ROOT / "images" / "blog"

WEBP_QUALITY = 82      # PSNR ~42dB against the source — visually indistinguishable
JPEG_QUALITY = 84
OG_MAX_WIDTH = 1200


def is_cover(png: Path) -> bool:
    """A cover is <slug>.png; in-body figures are <slug>-1.png, <slug>-2.png…"""
    return not png.stem.rsplit("-", 1)[-1].isdigit()


def derivatives(png: Path) -> list[Path]:
    out = [png.with_suffix(".webp")]
    if is_cover(png):
        out.append(png.with_name(f"{png.stem}-og.jpg"))
    return out


def convert(png: Path, keep_png: bool) -> list[str]:
    written = []
    src = Image.open(png)

    webp = png.with_suffix(".webp")
    src.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
    written.append(f"{webp.name} ({webp.stat().st_size // 1024}KB)")

    if is_cover(png):
        og = png.with_name(f"{png.stem}-og.jpg")
        flat = src.convert("RGB")
        if flat.width > OG_MAX_WIDTH:
            h = round(flat.height * OG_MAX_WIDTH / flat.width)
            flat = flat.resize((OG_MAX_WIDTH, h), Image.LANCZOS)
        flat.save(og, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        written.append(f"{og.name} ({og.stat().st_size // 1024}KB)")

    if not keep_png:
        png.unlink()
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report what would be converted, write nothing")
    ap.add_argument("--keep-png", action="store_true",
                    help="write the derivatives but keep the source PNG")
    args = ap.parse_args()

    if not BLOG_IMAGES.is_dir():
        print(f"no {BLOG_IMAGES.relative_to(ROOT)} directory — nothing to do")
        return 0

    pngs = sorted(BLOG_IMAGES.glob("*.png"))
    if args.check:
        pending = [p for p in pngs if not all(d.exists() for d in derivatives(p))]
        stale = [p for p in pngs if all(d.exists() for d in derivatives(p))]
        for p in pending:
            print(f"needs conversion: images/blog/{p.name}")
        for p in stale:
            print(f"source PNG still present (derivatives exist): images/blog/{p.name}")
        if pending or stale:
            print(f"\n{len(pending) + len(stale)} file(s) pending — "
                  f"run: python3 tools/optimise-images.py")
            return 1
        print("all blog images optimised")
        return 0

    if not pngs:
        print("no source PNGs in images/blog — nothing to do")
        return 0

    before = after = 0
    for png in pngs:
        size = png.stat().st_size
        before += size
        written = convert(png, args.keep_png)
        after += sum((BLOG_IMAGES / w.split(" ")[0]).stat().st_size for w in written)
        print(f"  {png.name:48} {size // 1024:4}KB -> {', '.join(written)}")

    saved = 100 - (after * 100 // before) if before else 0
    print(f"\n{len(pngs)} image(s): {before // 1024:,}KB -> {after // 1024:,}KB ({saved}% smaller)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
