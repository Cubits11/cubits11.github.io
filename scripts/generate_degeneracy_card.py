#!/usr/bin/env python3
"""Render the MC-004 degeneracy card (1200×630 PNG).

Two numbers, deliberately identical in weight and colour, because the finding
is that the same adapter-bit OR is 1 on every harmful-labelled and every
benign-labelled image in the pinned release. This is a label-separation
diagnostic on harness-normalized native predicates, not a safety claim.

Not a chart — a stat-tile pair. There is nothing to plot: the whole content is
two rates that are both exactly 1.0. Colouring one "good" and one "bad" would
argue beyond the source, so both wear the same ink token and only the
non-separation line carries a status colour, with a label beside it rather than
colour alone.

Colours are the site's own dark tokens and the type is the site's own vendored
faces, so the card carries the same provenance as the pages.

Fonts: Pillow cannot read woff2, so pass --fonts-dir pointing at TTF
conversions of assets/fonts/*.woff2. Committed artifact; CI never runs this.

Output: assets/img/og-mc004-degeneracy.png
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
REVIEW = "#E9A23B"      # status: warning — always paired with a label
LINE = "#39422F"

W, H = 1200, 630
OUT = ROOT / "assets" / "img" / "og-mc004-degeneracy.png"


def font(d: pathlib.Path, name: str, size: int, weight: float | None = None):
    f = ImageFont.truetype(str(d / f"{name}.ttf"), size)
    if weight is not None:
        try:
            axes = f.get_variation_axes()
            f.set_variation_by_axes([weight if a["name"] in (b"wght", "wght") else
                                     a["default"] for a in axes])
        except Exception:
            pass
    return f


def centered(draw, cx, y, text, fnt, fill):
    draw.text((cx - draw.textlength(text, font=fnt) / 2, y), text, font=fnt, fill=fill)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fonts-dir", required=True)
    args = ap.parse_args()
    fd = pathlib.Path(args.fonts_dir)
    if not fd.is_dir():
        print(f"FAIL  --fonts-dir {fd} is not a directory")
        return 1

    mono_s = font(fd, "fragment-mono", 17)
    mono_xs = font(fd, "fragment-mono", 15)
    sans = font(fd, "instrument-sans-roman", 26)
    sans_s = font(fd, "instrument-sans-roman", 20)
    mid = font(fd, "fragment-mono", 30)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # kicker — scope before anything else
    d.line([(64, 68), (100, 68)], fill=REVIEW, width=2)
    d.text((116, 56), "MULTIMODAL SAFEGUARD BENCH · results/full_run @ fb6f32e6 · IMAGE MODALITY",
           font=mono_xs, fill=MUTED)

    # the two numbers — identical treatment on purpose
    panel_y0, panel_y1 = 118, 366
    d.rectangle([64, panel_y0, W - 64, panel_y1], fill=SURFACE, outline=LINE, width=2)
    d.line([(W // 2, panel_y0), (W // 2, panel_y1)], fill=LINE, width=2)

    left_cx, right_cx = 64 + (W // 2 - 64) // 2, W // 2 + (W - 64 - W // 2) // 2

    # Fit the hero numbers to the half-panel by measurement, not by guess: a
    # number that overflows its own cell is the wrong way to argue for honest
    # reporting. Both get the SAME size, chosen so the wider one fits.
    half = (W // 2) - 64
    avail = half - 72                      # padding each side
    hero_texts = ("200/200", "250/250")
    size = 120
    while size > 24:
        f = font(fd, "fragment-mono", size)
        if max(d.textlength(t, font=f) for t in hero_texts) <= avail:
            break
        size -= 2
    huge = font(fd, "fragment-mono", size)
    widest = max(d.textlength(t, font=huge) for t in hero_texts)
    assert widest <= avail, f"hero number {widest:.0f}px exceeds cell {avail}px"
    centered(d, left_cx, 168, hero_texts[0], huge, INK)
    centered(d, right_cx, 168, hero_texts[1], huge, INK)
    centered(d, left_cx, 286, "harmful-labelled images · bit = 1", sans_s, MUTED)
    centered(d, right_cx, 286, "benign-labelled images · bit = 1", sans_s, MUTED)
    centered(d, left_cx, 318, "100%", mid, REVIEW)
    centered(d, right_cx, 318, "100%", mid, REVIEW)

    # the finding
    d.text((64, 404), "Same static adapter-bit OR. One guard is 1 on every image,",
           font=sans, fill=INK)
    d.text((64, 440), "so the OR is 1 on every image.", font=sans, fill=INK)

    # status carries a label, never colour alone
    d.rectangle([64, 486, 70, 508], fill=REVIEW)
    d.text((84, 486), "NON-SEPARATING ON RELEASE LABELS · Δ_L = 0.000",
           font=mono_s, fill=REVIEW)

    # scope boundary and route back to the receipt
    d.line([(64, 534), (W - 64, 534)], fill=LINE, width=2)
    d.text((64, 552), "Static OR of harness-normalized native unsafe labels. "
                      "No shared-event translation; not deployed-route safety.", font=mono_xs, fill=MUTED)
    d.text((64, 576), "8 pinned files, one command: cubits11.github.io/missing-column/reproduce/",
           font=mono_xs, fill=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {W}×{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
