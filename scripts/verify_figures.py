#!/usr/bin/env python3
"""Assert the geometry of the site's probability figures.

A figure that lies about probability must fail the build instead of looking
fine. This checker parses the committed SVG markup (no browser, no render)
and asserts, to within 1e-9:

Fig. 02 — the feasible-worlds instrument (index.html), eleven frames q=0..10:
  * both marginal strips are exactly 10% of the population width in every
    frame (marginals pinned);
  * the overlap rectangle's width over the population width equals q/100;
  * the frame's stated atom vector is (0.80+q̃, 0.10−q̃, 0.10−q̃, q̃) and sums
    to 1;
  * the stated readouts equal P(both)=q% and P(either)=(20−q)%;
  * the axis dot sits at the linear position for q on the 0–10% scale, and
    its label reads q%;
  * the independence tick sits exactly at 1%.

Essay number line (essays/when-marginals-are-not-enough/): the AND band spans
[0%,10%], the OR band spans [10%,20%], and the independence dots sit at 1%
and 19% on the same linear scale.

Exit code 0 = all geometry asserted; 1 = at least one assertion failed.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOL = 1e-9

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def close(a: float, b: float) -> bool:
    return abs(a - b) <= TOL


def check_fig02() -> None:
    html = (ROOT / "index.html").read_text()
    pop_x, pop_w = 40.0, 560.0
    axis_y0, axis_y10 = 190.0, 58.0  # 0% at the bottom, 10% at the top
    per_pct = (axis_y0 - axis_y10) / 10.0

    frames = re.findall(r'<g class="hf hf(\d+)">(.*?)</g>', html, re.S)
    if len(frames) != 11 or sorted(int(q) for q, _ in frames) != list(range(11)):
        fail(f"Fig. 02: expected frames hf0..hf10, found {[q for q, _ in frames]}")
        return
    ok("Fig. 02: 11 frames present (q = 0..10)")

    for qs, body in frames:
        q = int(qs)
        qf = q / 100.0
        rects = {cls: (float(x), float(w)) for x, w, cls in re.findall(
            r'<rect x="([\d.]+)" y="58" width="([\d.]+)" height="132" class="(hs[ABX])"/>', body)}

        for cls in ("hsA", "hsB"):
            if cls not in rects:
                fail(f"Fig. 02 q={q}: strip {cls} missing")
                continue
            _, w = rects[cls]
            if not close(w / pop_w, 0.10):
                fail(f"Fig. 02 q={q}: {cls} marginal is {w / pop_w}, not 0.10")
        if "hsA" in rects and not close(rects["hsA"][0], pop_x):
            fail(f"Fig. 02 q={q}: strip A does not start at the population edge")

        if q == 0:
            if "hsX" in rects:
                fail("Fig. 02 q=0: overlap rectangle present in the zero-overlap world")
        elif "hsX" not in rects:
            fail(f"Fig. 02 q={q}: overlap rectangle missing")
        else:
            x, w = rects["hsX"]
            if not close(w / pop_w, qf):
                fail(f"Fig. 02 q={q}: overlap area {w / pop_w} != q {qf}")
            if "hsB" in rects and not close(x, rects["hsB"][0]):
                fail(f"Fig. 02 q={q}: overlap does not align with strip B")
        if "hsA" in rects and "hsB" in rects:
            expected_xb = pop_x + (0.10 - qf) * pop_w
            if not close(rects["hsB"][0], expected_xb):
                fail(f"Fig. 02 q={q}: strip B at {rects['hsB'][0]}, expected {expected_xb}")

        atoms = re.search(r'π\(q\) = \(([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)\)', body)
        if not atoms:
            fail(f"Fig. 02 q={q}: atom vector label missing")
        else:
            a = [float(v) for v in atoms.groups()]
            expect = [0.80 + qf, 0.10 - qf, 0.10 - qf, qf]
            if not all(close(x, e) for x, e in zip(a, expect)):
                fail(f"Fig. 02 q={q}: atoms {a} != expected {expect}")
            if not close(sum(a), 1.0):
                fail(f"Fig. 02 q={q}: atoms sum to {sum(a)}, not 1")

        readout = re.search(
            r'P\(both fail\) = (\d+)%\s+·\s+P\(at least one fails\) = (\d+)%', body)
        if not readout:
            fail(f"Fig. 02 q={q}: readout line missing")
        elif (int(readout.group(1)), int(readout.group(2))) != (q, 20 - q):
            fail(f"Fig. 02 q={q}: readout says {readout.groups()}, expected ({q}, {20 - q})")

        dot = re.search(r'<circle cx="651" cy="([\d.]+)" r="5" class="hdot"/>', body)
        lbl = re.search(r'text-anchor="end">(\d+)%</text>', body)
        if not dot or not lbl:
            fail(f"Fig. 02 q={q}: axis dot or label missing")
        else:
            if not close(float(dot.group(1)), axis_y0 - per_pct * q):
                fail(f"Fig. 02 q={q}: dot at y={dot.group(1)}, "
                     f"expected {axis_y0 - per_pct * q}")
            if int(lbl.group(1)) != q:
                fail(f"Fig. 02 q={q}: axis label says {lbl.group(1)}%, expected {q}%")

    indep = re.search(r'<line x1="638" y1="([\d.]+)" x2="662" y2="([\d.]+)" class="hindep"/>',
                      html)
    if not indep:
        fail("Fig. 02: independence tick missing")
    elif not (close(float(indep.group(1)), axis_y0 - per_pct * 1)
              and close(float(indep.group(2)), axis_y0 - per_pct * 1)):
        fail(f"Fig. 02: independence tick at y={indep.group(1)}, "
             f"expected {axis_y0 - per_pct * 1} (exactly 1%)")

    if not failures:
        ok("Fig. 02: marginals pinned, overlap area equals q, atoms coherent, "
           "axis linear, independence tick at exactly 1% — in all eleven frames")


def check_essay_numberline() -> None:
    html = (ROOT / "essays" / "when-marginals-are-not-enough" / "index.html").read_text()
    x0, per_pct = 40.0, 28.0  # 0% at x=40; 20% at x=600

    before = len(failures)
    bands = re.findall(r'<rect class="band" x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', html)
    if len(bands) != 2:
        fail(f"essay: expected 2 bound bands, found {len(bands)}")
    else:
        (ax, aw), (ox, ow) = ((float(x), float(w)) for x, w in bands)
        if not (close((ax - x0) / per_pct, 0) and close((ax + aw - x0) / per_pct, 10)):
            fail(f"essay: AND band spans [{(ax - x0) / per_pct}, "
                 f"{(ax + aw - x0) / per_pct}]%, expected [0, 10]%")
        if not (close((ox - x0) / per_pct, 10) and close((ox + ow - x0) / per_pct, 20)):
            fail(f"essay: OR band spans [{(ox - x0) / per_pct}, "
                 f"{(ox + ow - x0) / per_pct}]%, expected [10, 20]%")
    dots = [float(cx) for cx in re.findall(r'<circle class="pt" cx="([\d.]+)"', html)]
    if len(dots) != 2:
        fail(f"essay: expected 2 independence dots, found {len(dots)}")
    else:
        for cx, expected_pct in zip(dots, (1.0, 19.0)):
            if not close((cx - x0) / per_pct, expected_pct):
                fail(f"essay: independence dot at {(cx - x0) / per_pct}%, "
                     f"expected {expected_pct}%")
    if len(failures) == before:
        ok("essay number line: AND [0,10]%, OR [10,20]%, independence dots at "
           "1% and 19% on a linear scale")


def check_missing_column() -> None:
    """The campaign figures state illustrative numbers; assert the drawn
    geometry matches them, the printed readouts match them, and the motif's
    missing cell actually stays missing."""
    path = ROOT / "missing-column" / "index.html"
    if not path.exists():
        fail("missing-column: page not generated")
        return
    html = path.read_text()
    x0, w = 40.0, 560.0
    total, a_catch = 1000, 900
    a_miss = total - a_catch
    worlds = {"i": (90, 10), "ii": (20, 80)}

    before = len(failures)
    panels = re.findall(r'<g class="rc-panel" data-world="(i{1,2})">(.*?)</g>',
                        html, re.S)
    if sorted(p for p, _ in panels) != ["i", "ii"]:
        fail(f"missing-column: expected residual panels i and ii, "
             f"found {[p for p, _ in panels]}")
        return
    for wid, body in panels:
        b_catch, all_miss = worlds[wid]
        rects = {cls: (float(x), float(width)) for x, width, cls in re.findall(
            r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="26" '
            r'class="(rc[AMBX])"/>', body)}
        for cls in ("rcA", "rcM", "rcB", "rcX"):
            if cls not in rects:
                fail(f"missing-column world {wid}: segment {cls} missing")
        if len(rects) < 4:
            continue
        if not close(rects["rcA"][1] / w, a_catch / total):
            fail(f"missing-column world {wid}: A-caught width "
                 f"{rects['rcA'][1] / w} != {a_catch / total}")
        if not close(rects["rcM"][0], x0 + rects["rcA"][1]) or \
                not close(rects["rcM"][1] / w, a_miss / total):
            fail(f"missing-column world {wid}: A-missed segment misplaced")
        if not close(rects["rcB"][1] / w, b_catch / a_miss):
            fail(f"missing-column world {wid}: B-residual width "
                 f"{rects['rcB'][1] / w} != {b_catch / a_miss}")
        if not close(rects["rcX"][0], x0 + rects["rcB"][1]) or \
                not close(rects["rcX"][1] / w, all_miss / a_miss):
            fail(f"missing-column world {wid}: all-miss segment misplaced")
        if f"A catches {a_catch:,} of {total:,} · misses {a_miss}" not in body:
            fail(f"missing-column world {wid}: marginal readout wrong or missing")
        if f"B catches {b_catch} of the {a_miss} A missed · {all_miss} reach production" not in body:
            fail(f"missing-column world {wid}: residual readout wrong or missing")
    ratio = worlds["ii"][1] / worlds["i"][1]
    if ratio != int(ratio) or f"factor of {int(ratio)}" not in html:
        fail(f"missing-column: caption factor does not match "
             f"{worlds['ii'][1]}/{worlds['i'][1]}")

    cell = re.search(r'<td class="motif-missing">(.*?)</td>', html, re.S)
    if not cell:
        fail("missing-column: the motif's missing cell is missing")
    elif re.search(r"\d", cell.group(1)):
        fail("missing-column: the motif's missing cell contains a number — "
             "the whole point is that it must not")
    if len(failures) == before:
        ok("missing column: residual panels match their stated counts in "
           "both worlds, and the missing cell holds no number")


def check_disclosure_ladder() -> None:
    path = ROOT / "missing-column" / "disclosure" / "index.html"
    if not path.exists():
        fail("disclosure: page not generated")
        return
    html = path.read_text()
    before = len(failures)
    expected = ["1 · Per-guard marginals", "2 · Pairwise intersections",
                "3 · Union and all-miss", "4 · Per-item release"]
    rungs = re.findall(
        r'<rect x="([\d.]+)" y="([\d.]+)" width="[\d.]+" height="[\d.]+" '
        r'class="rung"/><text[^>]*class="rung-name">([^<]+)</text>', html)
    if [name for _, _, name in rungs] != expected:
        fail(f"disclosure: ladder rungs {[n for _, _, n in rungs]} != "
             f"{expected}")
    else:
        xs = [float(x) for x, _, _ in rungs]
        ys = [float(y) for _, y, _ in rungs]
        if not all(b > a for a, b in zip(xs, xs[1:])):
            fail("disclosure: ladder does not step rightward")
        if not all(b < a for a, b in zip(ys, ys[1:])):
            fail("disclosure: ladder does not step upward — stronger "
                 "disclosure must sit higher")
    if len(failures) == before:
        ok("disclosure ladder: four rungs, correct order, ascending")


def main() -> int:
    check_fig02()
    check_essay_numberline()
    check_missing_column()
    check_disclosure_ladder()
    print()
    if failures:
        print(f"{len(failures)} geometry assertion(s) failed.")
        return 1
    print("Figures verified: the committed markup cannot state a probability "
          "its geometry does not draw.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
