#!/usr/bin/env python3
"""Render the Missing Column social image (1200×630 PNG).

The image is the campaign mark: four filled per-guard cells and a fifth,
dashed, empty cell labelled THE STACK — comprehensible without the post
text around it. Colors are the site's own dark tokens (assets/site.css)
and the type is the site's own vendored faces, so the image carries the
same provenance as the pages.

Fonts: Pillow's bundled FreeType cannot read woff2, so this script takes
--fonts-dir pointing at TTF conversions of assets/fonts/*.woff2 (made
with `fonttools ttLib`, flavor=None). The image is a committed artifact;
CI never needs to run this script.

Output: assets/img/og-missing-column.png
"""

import argparse
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent

# assets/site.css dark tokens
BG = "#0B0F0A"
SURFACE = "#11150F"
INK = "#EDE8DA"
MUTED = "#9AA391"
GOLD = "#C9A15E"
REVIEW = "#E9A23B"
LINE = "#39422F"

W, H = 1200, 630


def load_font(fonts_dir: pathlib.Path, name: str, size: int,
              weight: float | None = None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(fonts_dir / f"{name}.ttf"), size)
    if weight is not None:
        try:
            axes = font.get_variation_axes()
            values = []
            for axis in axes:
                tag = axis["name"] if isinstance(axis, dict) else axis.name
                tag = bytes(tag).decode() if isinstance(tag, (bytes, bytearray)) else str(tag)
                if "wght" in tag.lower() or "weight" in tag.lower():
                    values.append(weight)
                else:
                    values.append(axis["default"] if isinstance(axis, dict) else axis.default)
            font.set_variation_by_axes(values)
        except OSError:
            pass  # static face — the default instance is fine
    return font


def dashed_rect(draw: ImageDraw.ImageDraw, box: tuple, color: str,
                dash: int = 12, gap: int = 8, width: int = 3) -> None:
    x0, y0, x1, y1 = box
    def dashed_line(a, b, vertical=False):
        pos = a
        while pos < b:
            end = min(pos + dash, b)
            if vertical:
                draw.line([(a2, pos), (a2, end)], fill=color, width=width)
            else:
                draw.line([(pos, a2), (end, a2)], fill=color, width=width)
            pos = end + gap
    a2 = y0; dashed_line(x0, x1)
    a2 = y1; dashed_line(x0, x1)
    a2 = x0; dashed_line(y0, y1, vertical=True)
    a2 = x1; dashed_line(y0, y1, vertical=True)


def centered(draw, cx, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def render(fonts_dir: pathlib.Path, out: pathlib.Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    mono_s = load_font(fonts_dir, "fragment-mono", 22)
    mono_xs = load_font(fonts_dir, "fragment-mono", 19)
    serif_num = load_font(fonts_dir, "fraunces-roman", 54, weight=520)
    sans = load_font(fonts_dir, "instrument-sans-roman", 30, weight=450)

    # kicker with gold rule, matching the site's .kicker idiom
    draw.line([(64, 84), (100, 84)], fill=GOLD, width=2)
    draw.text((116, 71), "THE MISSING COLUMN — A SOURCE-BOUND CENSUS",
              font=mono_s, fill=GOLD)

    # the table
    cols = ["GUARD A", "GUARD B", "GUARD C", "GUARD D", "THE STACK"]
    vals = ["91%", "88%", "94%", "86%", None]
    tx0, tx1 = 64, W - 64
    ty0, head_h, cell_h = 150, 64, 130
    col_w = (tx1 - tx0) / 5
    ty1 = ty0 + head_h + cell_h

    draw.rectangle([tx0, ty0, tx1, ty1], fill=SURFACE, outline=LINE, width=2)
    draw.line([(tx0, ty0 + head_h), (tx1, ty0 + head_h)], fill=LINE, width=2)
    for i in range(1, 5):
        x = tx0 + i * col_w
        draw.line([(x, ty0), (x, ty1)], fill=LINE, width=2)

    for i, (name, val) in enumerate(zip(cols, vals)):
        cx = tx0 + i * col_w + col_w / 2
        head_fill = GOLD if val is None else MUTED
        centered(draw, cx, ty0 + head_h / 2 - 11, name, mono_xs, head_fill)
        cy = ty0 + head_h + cell_h / 2
        if val is None:
            pad = 12
            dashed_rect(draw, (tx0 + 4 * col_w + pad, ty0 + head_h + pad,
                               tx1 - pad, ty1 - pad), REVIEW)
            centered(draw, cx, cy - 12, "not reported", mono_xs, REVIEW)
        else:
            centered(draw, cx, cy - 34, val, serif_num, INK)

    # the sentence, set in the site's prose face
    draw.text((64, 420), "Teams deploy guardrails in stacks.",
              font=sans, fill=INK)
    draw.text((64, 462), "Public evaluations report them one at a time.",
              font=sans, fill=INK)
    draw.text((64, 528),
              "The individual columns do not determine the last one.",
              font=load_font(fonts_dir, "instrument-sans-roman", 24,
                             weight=430), fill=MUTED)

    draw.text((64, 576), "cubits11.github.io/missing-column",
              font=mono_s, fill=GOLD)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size} bytes, "
          f"{img.size[0]}x{img.size[1]})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts-dir", required=True,
                    help="directory of TTF conversions of assets/fonts/*.woff2")
    args = ap.parse_args()
    fonts_dir = pathlib.Path(args.fonts_dir)
    for needed in ("fraunces-roman", "instrument-sans-roman", "fragment-mono"):
        if not (fonts_dir / f"{needed}.ttf").exists():
            print(f"missing {needed}.ttf in {fonts_dir} — convert the site's "
                  f"woff2 faces with fonttools (TTFont(...); flavor=None; save)")
            return 1
    render(fonts_dir, ROOT / "assets" / "img" / "og-missing-column.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
