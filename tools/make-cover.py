#!/usr/bin/env python3
"""make-cover.py — generate a branded 1200x630 cover card for a blog post.

Produces a green→teal gradient card with the post title, a tag chip and the
wrnty wordmark — no photo needed, so posts are self-contained. Run it once per
post; build.py expects the result at images/blog/<slug>.png.

    python3 tools/make-cover.py <slug> "<Title>" <tag>

Needs Pillow (pip install Pillow). Fonts are bundled in tools/fonts/.
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"
W, H = 1200, 630
GREEN = (18, 147, 79)
TEAL = (13, 120, 110)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def main():
    if len(sys.argv) != 4:
        print("usage: make-cover.py <slug> \"<Title>\" <tag>", file=sys.stderr)
        return 1
    slug, title, tag = sys.argv[1], sys.argv[2], sys.argv[3]

    bg = Image.new("RGB", (W, H))
    px = bg.load()
    for y in range(H):
        for x in range(W):
            t = (x / W * 0.55) + (y / H * 0.45)
            px[x, y] = lerp(GREEN, TEAL, min(1, t))

    # soft light glow, top-left
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-220, -280, 620, 560], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    bg = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), bg,
                         glow.point(lambda v: int(v * 0.22))).convert("RGBA")

    draw = ImageDraw.Draw(bg, "RGBA")
    bold = lambda s: ImageFont.truetype(str(FONTS / "Inter-Bold.ttf"), s)
    reg = lambda s: ImageFont.truetype(str(FONTS / "Inter-Regular.ttf"), s)

    pad = 90
    # tag chip
    f_tag = bold(26)
    chip = tag.upper()
    tw = draw.textlength(chip, font=f_tag)
    draw.rounded_rectangle([pad, 96, pad + tw + 52, 152], radius=28, fill=(255, 255, 255, 235))
    draw.text((pad + 26, 108), chip, font=f_tag, fill=(13, 120, 110))

    # title (wrapped, up to ~4 lines)
    f_title = bold(72)
    lines = wrap(draw, title, f_title, W - pad * 2)
    y = 210
    for ln in lines[:4]:
        draw.text((pad, y), ln, font=f_title, fill=(255, 255, 255))
        y += 84

    # wordmark
    icon = Image.open(ROOT / "images" / "app-icon.png").convert("RGBA").resize((60, 60), Image.LANCZOS)
    bg.alpha_composite(icon, (pad, H - 110))
    draw.text((pad + 76, H - 98), "wrnty", font=bold(44), fill=(255, 255, 255))

    out = ROOT / "images" / "blog" / f"{slug}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(out, "PNG")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
