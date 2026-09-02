#!/usr/bin/env python3
"""Generate /worldspace/ — the public observatory of compatible worlds — from
worldspace/manifest.yaml and films/data/facts.json.

The page never retypes a research number. Every world it can show is derived
here from the registered marginals (CC-001) in the same atom form the
registered endpoint witnesses use (CC-004), asserted against those witnesses,
and embedded as data the runtime indexes by the joint count. The visitor's
sheet is the master film's arrangement (same seed, same shuffle); the field of
specimen worlds is constructed here, every specimen asserted to carry the
declared scores before it is written. The count of compatible arrangements is
exact integer combinatorics. Strings come from the manifest, once.

--check fails on drift, so a registry edit that changes a number the
instrument shows fails the build until the page is regenerated and the QA
receipt re-captured.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from math import comb
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from generate_missing_column import PAGE_FOOT, SITE, breadcrumbs, esc, jsonld_script, page_head  # noqa: E402

MANIFEST = ROOT / "worldspace" / "manifest.yaml"
FACTS = ROOT / "films" / "data" / "facts.json"
EXPERIMENTS = ROOT / "distribution" / "experiments.yaml"
OUT = ROOT / "worldspace" / "index.html"
ISSUES = "https://github.com/Cubits11/cubits11.github.io/issues/new"
POSTER = "/worldspace/qa/poster-1200x630.png"
POSTER_ALT = ("Eleven columns of tiny population sheets on a black field above a cyan axis from 0 to 10; "
              "two readouts hold at 10 of 100 while a single amber point at 1 is labelled independence")
TOL = 1e-9
M32 = 0xFFFFFFFF


# ---------------------------------------------------------------- PRNG (the film's)
def mulberry32(seed: int):
    a = seed & M32

    def r() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & M32
        t = ((a ^ (a >> 15)) * (1 | a)) & M32
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & M32)) ^ t) & M32
        return ((t ^ (t >> 14)) & M32) / 4294967296
    return r


def shuffled_by(r, arr) -> list:
    a = list(arr)
    for i in range(len(a) - 1, 0, -1):
        j = int(r() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


def shuffled(arr, seed: int) -> list:
    return shuffled_by(mulberry32(seed), arr)


def close(a: float, b: float) -> bool:
    return abs(a - b) <= TOL


def sci(count: int) -> str:
    s = str(count)
    exp = len(s) - 1
    mant = round(int(s[:6]) / 10 ** 5, 4)
    if mant >= 10:
        mant, exp = round(mant / 10, 4), exp + 1
    return f"{mant:.4f} × 10^{exp}"


# ------------------------------------------------------------------ data
def build_data(m: dict, facts: dict, exp: dict) -> dict:
    pop = m["constructed"]["population"]
    n, side = int(pop["n"]), int(pop["side"])
    assert side * side == n
    p1, p2 = facts["CC-001.marginals"]["value"]
    lo, hi = facts["CC-001.and_bounds"]["value"]
    grid = facts["CC-004.feasible_q_grid"]["value"]
    ind = facts["CC-001.independence_and"]["value"]
    w_lo = facts["CC-004.witness_lower"]["value"]
    w_hi = facts["CC-004.witness_upper"]["value"]
    assert close(ind, p1 * p2), "independence must be the product of the marginals"
    assert close(lo, max(0.0, p1 + p2 - 1)) and close(hi, min(p1, p2)), "registered bounds are not Fréchet's"
    miss_a, miss_b = round(p1 * n), round(p2 * n)
    assert close(miss_a / n, p1) and close(miss_b / n, p2), "the population cannot realise the marginals exactly"

    worlds = []
    for i, qv in enumerate(grid):
        atoms = [1 - p1 - p2 + qv, p1 - qv, p2 - qv, qv]
        assert all(a >= -TOL for a in atoms) and close(sum(atoms), 1.0)
        assert close(atoms[1] + atoms[3], p1) and close(atoms[2] + atoms[3], p2)
        q = round(qv * n)
        assert close(q / n, qv), f"grid value {qv} is not an integer count of {n}"
        witness = "lower" if i == 0 else ("upper" if i == len(grid) - 1 else None)
        worlds.append({"q": q, "both": round(qv, 10), "either": round(p1 + p2 - qv, 10),
                       "atoms": [round(max(a, 0.0), 10) for a in atoms], "witness": witness})
    assert [w["q"] for w in worlds] == list(range(len(worlds))), "the grid must be every integer count"
    assert all(close(a, b) for a, b in zip(worlds[0]["atoms"], w_lo)), "lower world is not the registered witness"
    assert all(close(a, b) for a, b in zip(worlds[-1]["atoms"], w_hi)), "upper world is not the registered witness"
    assert close(worlds[0]["both"], lo) and close(worlds[-1]["both"], hi)
    ind_q = round(ind * n)
    assert close(ind_q / n, ind)

    cells = shuffled(range(n), int(pop["seed"]))
    a_cells = cells[:miss_a]
    b_home = cells[miss_a:miss_a + miss_b]
    assert len(set(a_cells) | set(b_home)) == miss_a + miss_b, "A cells and B homes must be disjoint"

    spec = m["constructed"]["specimens"]
    per = int(spec["per_column"])
    r = mulberry32(int(spec["seed"]))
    seen: set = set()
    columns = []
    for q in range(len(worlds)):
        col = []
        while len(col) < per:
            a_set = sorted(shuffled_by(r, range(n))[:miss_a])
            rest = [c for c in range(n) if c not in a_set]
            b_set = sorted(shuffled_by(r, a_set)[:q] + shuffled_by(r, rest)[:miss_b - q])
            key = (tuple(a_set), tuple(b_set))
            if key in seen:
                continue
            seen.add(key)
            assert len(a_set) == miss_a and len(b_set) == miss_b and len(set(a_set) & set(b_set)) == q
            col.append({"a": a_set, "b": b_set})
        columns.append(col)

    count = comb(n, miss_a) * comb(n, miss_b)
    cnt = m["constructed"]["count"]
    assert str(count) == str(cnt["value"]), f"manifest count {cnt['value']} != C({n},{miss_a})·C({n},{miss_b}) = {count}"
    assert sci(count) == cnt["display"], f"manifest display {cnt['display']!r} != {sci(count)!r}"
    # the counting-measure note: the expected overlap under a uniform prior is exactly miss_a·miss_b/n
    mean_num = sum(q * comb(miss_a, q) * comb(n - miss_a, miss_b - q) for q in range(miss_b + 1))
    assert mean_num * n == miss_a * miss_b * comb(n, miss_b), "uniform-prior mean must equal the independence count"

    try_a = next(e for e in exp["experiments"] if e["id"] == "TRY-A")
    try_b = next(e for e in exp["experiments"] if e["id"] == "TRY-B")
    return {
        "n": n, "side": side, "missA": miss_a, "missB": miss_b,
        "marginals": [p1, p2], "interval": [lo, hi], "independence": ind, "independenceQ": ind_q,
        "worlds": worlds,
        "arrangement": {"a": a_cells, "b": b_home},
        "specimens": {"perColumn": per, "phonePerColumn": int(spec["phone_per_column"]), "columns": columns},
        "count": {"value": str(count), "display": cnt["display"]},
        "strings": m["strings"], "ledger": m["ledger_tags"],
        "routes": {"primary": m["routes"]["primary"], "experiment_b": m["routes"]["experiment_b"]},
        "tryA": {"command": try_a["command"], "final": try_a["expected_final_line"]},
        "tryB": {"command": try_b["command"]},
    }


# ------------------------------------------------------------------ SVG (no-JS proof)
def sheet_svg(data: dict, q: int, title: str) -> str:
    side = data["side"]
    a = data["arrangement"]["a"]
    b = data["arrangement"]["b"]
    rings = [a[i] if i < q else b[i] for i in range(data["missB"])]
    u = 10
    out = [f'<svg viewBox="0 0 {side * u} {side * u}" width="100%" role="img" aria-label="{esc(title)}">',
           f'<rect width="{side * u}" height="{side * u}" fill="#EDE8DA"/>']
    for i in range(side + 1):
        out.append(f'<line x1="{i * u}" y1="0" x2="{i * u}" y2="{side * u}" stroke="#C2BAA2" stroke-width=".25"/>')
        out.append(f'<line x1="0" y1="{i * u}" x2="{side * u}" y2="{i * u}" stroke="#C2BAA2" stroke-width=".25"/>')
    for c in a:
        out.append(f'<circle cx="{(c % side) * u + u / 2}" cy="{(c // side) * u + u / 2}" r="2.4" fill="#14170F"/>')
    for c in rings:
        out.append(f'<circle cx="{(c % side) * u + u / 2}" cy="{(c // side) * u + u / 2}" r="3.6" fill="none" stroke="#14170F" stroke-width="1"/>')
    out.append("</svg>")
    return "".join(out)


def axis_svg(data: dict, s: dict) -> str:
    lo, hi = data["interval"]
    ind = data["independence"]
    x0, x1, y = 20, 380, 24
    px = lambda v: x0 + (x1 - x0) * (v - lo) / (hi - lo)  # noqa: E731
    out = [f'<svg viewBox="0 0 400 64" width="100%" role="img" aria-label="{esc(s["static_axis"])}">',
           f'<rect x="{px(lo)}" y="{y - 5}" width="{px(hi) - px(lo)}" height="10" fill="#7FC4CF" opacity=".25"/>',
           f'<line x1="{px(lo)}" y1="{y}" x2="{px(hi)}" y2="{y}" stroke="#7FC4CF" stroke-width="2.5"/>']
    for w in data["worlds"]:
        out.append(f'<line x1="{px(w["both"])}" y1="{y - 6}" x2="{px(w["both"])}" y2="{y + 6}" stroke="#7FC4CF" stroke-width="1"/>')
    out.append(f'<line x1="{px(ind)}" y1="{y - 12}" x2="{px(ind)}" y2="{y + 12}" stroke="#E9A23B" stroke-width="2" stroke-dasharray="3 2"/>')
    out.append(f'<text x="{px(lo)}" y="{y + 26}" font-family="Fragment Mono,monospace" font-size="10" fill="#9AA391" text-anchor="middle">{round(lo * 100)}%</text>')
    out.append(f'<text x="{px(hi)}" y="{y + 26}" font-family="Fragment Mono,monospace" font-size="10" fill="#9AA391" text-anchor="middle">{round(hi * 100)}%</text>')
    out.append(f'<text x="{px(ind)}" y="{y - 16}" font-family="Fragment Mono,monospace" font-size="10" fill="#E9A23B" text-anchor="middle">{round(ind * 100)}% · independence</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ CSS
CSS = r"""
/* WORLDSPACE — the stage is a black field in both themes; every colour on it
   is the film runtime's token (assets/site.css dark values), so the semantic
   law holds: cyan = proved/evidence, amber = assumption, gold = locator only,
   graphite = unknown/context. No state is carried by colour alone. */
[hidden]{display:none!important}
.ws-stage{--wsbg:#0B0F0A;--wss:#11150F;--wsi:#EDE8DA;--wsm:#9AA391;--wsg:#C9A15E;--wse:#7FC4CF;--wsr:#E9A23B;--wsx:#E4796F;--wsl:#232A20;--wsls:#39422F;--paper:#EDE8DA;--pink:#14170F;--pline:#C2BAA2;
  background:var(--wsbg);color:var(--wsi);padding:4.6rem 0 1.4rem;min-height:calc(100vh - 3.4rem);display:flex;flex-direction:column}
.ws-stage .in{width:min(1180px,100% - 2*clamp(1rem,4vw,3rem));margin-inline:auto;display:flex;flex-direction:column;flex:1}
.ws-stage .mono{color:var(--wsm)}
.ws-top{display:flex;justify-content:space-between;align-items:baseline;gap:1rem}
.ws-h1{font:400 .72rem/1.2 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--wsg);margin:0}
.ws-h1 span{color:var(--wsm);letter-spacing:.06em;text-transform:none;margin-left:.6rem}
.ws-sound{appearance:none;background:transparent;border:1px solid var(--wsls);color:var(--wsm);border-radius:999px;padding:.45rem .8rem;font:400 .62rem/1 var(--mono);letter-spacing:.1em;cursor:pointer;min-height:2rem}
.ws-sound[aria-pressed="true"]{color:var(--wsi);border-color:var(--wsi)}
.ws-band{position:sticky;top:3.4rem;z-index:5;background:var(--wsbg);padding:.7rem 0 .55rem;margin-top:.6rem;box-shadow:0 .6rem .6rem -.6rem rgba(0,0,0,.6)}
.ws-readouts{display:grid;grid-template-columns:repeat(3,max-content);justify-content:center;gap:clamp(1.4rem,5vw,4.5rem);margin:0;text-align:left}
.ws-stamp-row{margin:.15rem 0 0;text-align:center;min-height:0}
.ws-readout .ws-lbl{display:block;font:400 .66rem/1.2 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--wsm)}
.ws-num{display:flex;align-items:baseline;gap:.35rem;margin-top:.25rem;font-variant-numeric:tabular-nums}
.ws-num b{font:500 clamp(2.2rem,5vw,3.6rem)/1 var(--serif);letter-spacing:-.02em;color:var(--wsi);min-width:1.2em}
.ws-num i{font:400 .78rem/1 var(--mono);color:var(--wsm);font-style:normal}
.ws-fixed{display:inline-block;margin-top:.45rem;font:400 .6rem/1 var(--mono);letter-spacing:.14em;color:var(--wse);border:1px solid var(--wse);padding:.28rem .45rem;border-radius:2px}
.ws-stamp{display:inline-block;font:400 .6rem/1 var(--mono);letter-spacing:.12em;color:var(--wse);border:1px solid var(--wse);padding:.28rem .45rem;border-radius:2px;transform:rotate(-2deg)}
.ws-invariant{text-align:center;margin:.35rem 0 0;font:400 .74rem/1.3 var(--mono);letter-spacing:.14em;color:var(--wse)}
.ws-act{display:flex;flex-direction:column;align-items:center;margin-top:clamp(.8rem,2.5vh,1.6rem);padding:0;flex:1;scroll-margin-top:0}
.ws-q{font:500 clamp(1.5rem,3.6vw,2.4rem)/1.15 var(--serif);letter-spacing:-.01em;text-align:center;margin:clamp(1.2rem,5vh,3rem) 0 1.2rem;color:var(--wsi)}
.ws-predict{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;justify-content:center}
.ws-predict input{width:6.2rem;background:var(--wss);color:var(--wsi);border:1px solid var(--wsls);border-radius:4px;padding:.55rem .7rem;font:500 2rem/1 var(--serif);text-align:center;-moz-appearance:textfield}
.ws-predict input::-webkit-outer-spin-button,.ws-predict input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.ws-predict .ws-den{font:400 .78rem/1 var(--mono);color:var(--wsm)}
.ws-btn{appearance:none;display:inline-flex;align-items:center;gap:.5rem;cursor:pointer;text-decoration:none;font:400 .72rem/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;border:1px solid var(--wsi);border-radius:999px;padding:.9rem 1.4rem;color:var(--wsi);background:transparent;min-height:2.75rem}
.ws-btn:hover,.ws-btn:focus-visible{background:var(--wsi);color:var(--wsbg)}
.ws-btn-solid{background:var(--wsg);border-color:var(--wsg);color:var(--wsbg)}
.ws-btn-solid:hover,.ws-btn-solid:focus-visible{background:var(--wsi);border-color:var(--wsi)}
.ws-small{margin:1.1rem 0 0;font:400 .72rem/1.6 var(--mono);color:var(--wsm);text-align:center}
.ws-link{appearance:none;background:none;border:0;padding:0;color:var(--wsm);font:inherit;cursor:pointer;text-decoration:underline;text-underline-offset:3px}
.ws-link:hover,.ws-link:focus-visible{color:var(--wsi)}
.ws-stage :focus-visible{outline:2px solid var(--wsg);outline-offset:3px}
/* the sheet */
.ws-sheet-wrap{width:min(500px,86vw,44vh);aspect-ratio:1;margin:0 auto}
.ws-sheet{position:relative;width:100%;height:100%;background:var(--paper);border:1px solid var(--pline);
  background-image:linear-gradient(var(--pline) 1px,transparent 1px),linear-gradient(90deg,var(--pline) 1px,transparent 1px);background-size:10% 10%;
  touch-action:none;user-select:none;-webkit-user-select:none;overflow:visible}
.ws-disc{position:absolute;width:10%;height:10%;left:0;top:0;pointer-events:none}
.ws-disc::after{content:"";position:absolute;inset:26%;border-radius:50%;background:var(--pink)}
.ws-ring{position:absolute;width:10%;height:10%;left:0;top:0;appearance:none;background:transparent;border:0;padding:0;margin:0;cursor:grab;border-radius:50%;
  transition:transform .32s cubic-bezier(.2,.7,.2,1)}
.ws-ring::after{content:"";position:absolute;inset:14%;border-radius:50%;border:3px solid var(--pink);box-sizing:border-box}
.ws-ring.on::after{inset:10%;border-width:3px}
.ws-ring.dragging{transition:none;cursor:grabbing;z-index:3}
.ws-ring.dragging::after{transform:scale(1.15)}
.ws-ring:focus-visible{outline:2px solid var(--wsg);outline-offset:2px}
.ws-sheet-small{width:min(260px,70vw);aspect-ratio:1;margin:0 auto}
.ws-sheet-small .ws-ring{cursor:default;transition:none}
.ws-hint{margin:.9rem 0 0;font-size:.68rem;letter-spacing:.1em;text-align:center}
.ws-ctl{width:min(500px,86vw);margin:.7rem auto 0;display:flex;flex-direction:column;gap:.4rem}
.ws-ctl label{font-size:.62rem}
.ws-ctl-row{display:flex;align-items:center;gap:.7rem}
.ws-ctl input[type=range]{flex:1;min-width:0;accent-color:var(--wse);height:2.2rem;cursor:pointer}
.ws-step{appearance:none;background:transparent;border:1px solid var(--wsls);color:var(--wsi);border-radius:50%;width:2.75rem;height:2.75rem;font:500 1.3rem/1 var(--serif);cursor:pointer;flex:none}
.ws-step:hover,.ws-step:focus-visible{border-color:var(--wsi)}
.ws-name{display:flex;gap:.7rem;flex-wrap:wrap;justify-content:center;margin:1.2rem 0 0;font:600 clamp(1.4rem,3.4vw,2.2rem)/1.1 var(--serif);letter-spacing:-.01em}
.ws-name .gold{color:var(--wsg)}
.ws-next{display:flex;gap:.7rem;flex-wrap:wrap;justify-content:center;margin:1.1rem 0 0}
/* the field */
.ws-field-title{font:500 clamp(1.3rem,3vw,2rem)/1.15 var(--serif);letter-spacing:-.01em;text-align:center;margin:.4rem 0 0}
.ws-fieldwrap{position:relative;width:min(1100px,100%);margin:.9rem auto 0}
.ws-fieldwrap canvas{display:block;width:100%;height:auto;opacity:1}
.ws-axis{position:relative;height:6.6rem;margin-top:1.9rem}
.ws-axis .seg{position:absolute;top:.9rem;height:4px;background:var(--wse);transition:left .45s cubic-bezier(.2,.7,.2,1),width .45s cubic-bezier(.2,.7,.2,1)}
.ws-axis .tail{position:absolute;top:.9rem;height:0;border-top:2px dashed var(--wsls)}
.ws-axis .tick{position:absolute;top:1.5rem;transform:translateX(-50%);font:400 .6rem/1 var(--mono);color:var(--wsm)}
.ws-axis .tick.end{color:var(--wsi)}
.ws-axis .unit{position:absolute;top:2.5rem;left:0;font:400 .58rem/1.2 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--wse)}
.ws-axis .tailtxt{position:absolute;top:2.5rem;right:0;font:400 .58rem/1.2 var(--mono);letter-spacing:.06em;color:var(--wsm);text-align:right;max-width:34%}
.ws-mark{position:absolute;left:0;top:0;pointer-events:none}
.ws-mark .pt{position:absolute;width:.7rem;height:.7rem;border-radius:50%;transform:translate(-50%,-50%)}
.ws-mark .txt{position:absolute;font:400 .58rem/1.2 var(--mono);letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;transform:translateX(-50%)}
.ws-mark.ind .pt{background:var(--wsr);top:1.05rem;transition:transform .5s cubic-bezier(.2,.7,.2,1)}
.ws-mark.ind .txt{color:var(--wsr);top:-1.1rem}
.ws-mark.world .pt{background:var(--wsg);width:.55rem;height:.55rem;border-radius:1px;transform:translate(-50%,-50%) rotate(45deg);top:3.95rem}
.ws-mark.world .txt{color:var(--wsg);top:4.4rem}
.ws-mark.pred .pt{background:transparent;border:2px solid var(--wsi);box-sizing:border-box;top:5.35rem}
.ws-mark.pred .txt{color:var(--wsi);top:5.8rem}
.ws-count{margin:.2rem 0 0;font-size:.62rem;letter-spacing:.06em;text-align:center;max-width:56em;margin-inline:auto}
.ws-indep{display:flex;flex-direction:column;align-items:center;gap:.5rem;margin:1rem 0 0;text-align:center}
.ws-indep .lbl{font:400 .66rem/1.2 var(--mono);letter-spacing:.14em;color:var(--wsr)}
.ws-indep .prod{font:400 .72rem/1.2 var(--mono);color:var(--wsm)}
.ws-indep .two{font:600 clamp(1.1rem,2.6vw,1.6rem)/1.15 var(--serif);color:var(--wsi)}
.ws-indep .two b{color:var(--wsr);font-weight:600}
.ws-switch{appearance:none;display:inline-flex;align-items:center;gap:.7rem;background:transparent;border:1px solid var(--wsr);color:var(--wsr);border-radius:999px;padding:.8rem 1.3rem;font:400 .7rem/1 var(--mono);letter-spacing:.1em;cursor:pointer;min-height:2.75rem;margin-top:.3rem}
.ws-switch::before{content:"";width:1.6rem;height:.9rem;border:1px solid currentColor;border-radius:999px;position:relative;background:linear-gradient(currentColor,currentColor) no-repeat .1rem 50%/.6rem .6rem;flex:none;transition:background-position .25s}
.ws-switch[aria-checked="true"]{background:var(--wsr);color:var(--wsbg)}
.ws-switch[aria-checked="true"]::before{background-position:.85rem 50%}
.ws-assume-text{margin:.5rem 0 0;font:400 .92rem/1.5 var(--sans);color:var(--wsi);max-width:30em}
.ws-inspector{margin:1rem auto 0;text-align:center;display:flex;flex-direction:column;align-items:center;gap:.6rem}
.ws-inspector p{margin:0;font:400 .66rem/1.4 var(--mono);letter-spacing:.08em;color:var(--wsm)}
.ws-ledger{margin:auto 0 0;padding-top:1.1rem;font-size:.6rem;letter-spacing:.1em;color:var(--wsm);text-align:left}
.ws-halt{margin:1rem 0 0;padding:.8rem 1rem;border:1px solid var(--wsx);color:var(--wsx);font:400 .7rem/1.4 var(--mono)}
/* the static proof — shown with JavaScript off or halted */
.ws-static{padding:2.4rem 0 1rem;background:var(--wsbg);color:var(--wsi)}
.ws-static .in{width:min(1180px,100% - 2*clamp(1rem,4vw,3rem));margin-inline:auto}
.ws-static h2{font:500 clamp(1.5rem,3vw,2.1rem)/1.1 var(--serif);margin:0 0 .5rem}
.ws-static .lead{color:#9AA391;max-width:40em;margin:0 0 1.4rem}
.ws-two{display:grid;grid-template-columns:1fr 1fr;gap:clamp(1rem,4vw,3rem);max-width:820px}
.ws-two figure{margin:0}
.ws-two figcaption{margin-top:.6rem;font:400 .66rem/1.5 var(--mono);letter-spacing:.06em;color:#9AA391}
.ws-two figcaption b{color:#EDE8DA;font-weight:400}
.ws-static-axis{max-width:520px;margin:1.6rem 0 0}
html.ws-js .ws-static{display:none}
/* the exit */
.ws-exit{padding:3rem 0 1rem}
.ws-exit .in{width:min(1060px,100% - 2*clamp(1.25rem,5vw,3rem));margin-inline:auto}
html.ws-js .ws-exit.ws-staged{display:none}
.ws-status{color:var(--muted);font-size:.66rem;letter-spacing:.08em;margin:0 0 1.6rem;border-left:2px solid var(--review);padding-left:.8rem}
.ws-exit-h{font:520 clamp(2rem,5vw,3.4rem)/1.06 var(--serif);letter-spacing:-.018em;margin:0 0 1rem}
.ws-exit-h b{color:var(--gold);font-weight:520}
.ws-exit .lead{color:var(--muted);max-width:44em}
.ws-exit pre{margin:1.2rem 0 0;padding:.8rem 1rem;background:var(--surface);border:1px solid var(--line);overflow-x:auto;font-size:.86rem;line-height:1.5}
.ws-exit .final{margin:.6rem 0 0;font-size:.66rem;color:var(--muted);letter-spacing:.04em;overflow-wrap:anywhere}
.ws-exit .final code{color:var(--ink);font-size:.74rem;text-transform:none;letter-spacing:0;white-space:pre-wrap}
.ws-routes{display:flex;flex-wrap:wrap;gap:.7rem;margin:1.4rem 0 0}
.ws-thirteen{margin:1.8rem 0 0;color:var(--muted);max-width:48em}
.ws-thirteen b{color:var(--ink);font-weight:520}
.ws-bound{margin:1.8rem 0 0;border:1px solid var(--line-strong);background:var(--surface);padding:.9rem 1.2rem}
.ws-bound summary{cursor:pointer;font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--gold)}
.ws-bound ul{margin:.8rem 0 0;padding-left:1.2rem;color:var(--muted);font-size:.94rem}
.ws-bound li{margin:.4rem 0}
.ws-bound .note{margin:.9rem 0 0;font-size:.9rem;color:var(--ink);border-left:2px solid var(--line-strong);padding-left:.8rem}
.ws-prov{margin:1.6rem 0 0;color:var(--muted);font-size:.62rem;letter-spacing:.06em;overflow-wrap:anywhere}
@media (max-width:700px){.ws-stage{padding-top:5.2rem}}
@media (max-width:560px){
  .ws-band{top:4rem}
  .ws-readouts{grid-template-columns:repeat(3,max-content);gap:.6rem;justify-content:space-between}
  .ws-readout .ws-lbl{font-size:.55rem;letter-spacing:.06em}
  .ws-num b{font-size:2.1rem}
  .ws-num i{font-size:.62rem}
  .ws-fixed{font-size:.52rem;padding:.2rem .35rem;margin-top:.3rem}
  .ws-axis .unit{max-width:46%}
  .ws-two{grid-template-columns:1fr}
  .ws-axis .tailtxt{max-width:44%}
  .ws-h1 span{display:none}
}
.ws-stage.ws-poster .ws-top,.ws-stage.ws-poster .ws-count,.ws-stage.ws-poster .ws-ctl,.ws-stage.ws-poster .ws-indep,.ws-stage.ws-poster .ws-next,.ws-stage.ws-poster .ws-ledger{display:none!important}
.ws-stage.ws-poster{padding-top:1rem;min-height:0}
.ws-stage.ws-poster .ws-band{position:static;box-shadow:none}
@media (prefers-reduced-motion: reduce){
  .ws-ring,.ws-axis .seg,.ws-switch::before,.ws-mark.ind .pt{transition:none!important}
}
"""


# ------------------------------------------------------------------ page
def issue_url(template: str, prefill: dict) -> str:
    return ISSUES + "?" + urllib.parse.urlencode({"template": template, **{k: str(v) for k, v in prefill.items()}})


def render(m: dict, data: dict, facts: dict) -> str:
    s = m["strings"]
    r = m["routes"]
    title, desc = m["page_title"], " ".join(m["page_description"].split())
    assert len(title) <= 72, f"page title is {len(title)} chars"
    assert 70 <= len(desc) <= 200, f"page description is {len(desc)} chars"
    path = m["route"]
    head = page_head(title, desc, path, CSS, jsonld=jsonld_script({
        "@context": "https://schema.org", "@type": "WebPage", "name": title, "description": desc,
        "url": f"{SITE}{path}", "inLanguage": "en", "isAccessibleForFree": True}))
    src_line = "Source: census.yaml · renderer: scripts/generate_missing_column.py"
    assert src_line in head, "shared page_head changed shape; re-derive the generated-file comment"
    head = head.replace(src_line, "Source: worldspace/manifest.yaml + films/data/facts.json · renderer: scripts/generate_worldspace.py")
    head = head.replace(f"{SITE}/assets/img/og-missing-column.png", f"{SITE}{POSTER}")
    head = re.sub(r'(og:image:alt" content=")[^"]*"', lambda mt: mt.group(1) + esc(POSTER_ALT) + '"', head)
    head = re.sub(r'(twitter:image:alt" content=")[^"]*"', lambda mt: mt.group(1) + esc(POSTER_ALT) + '"', head)
    crumbs = breadcrumbs(("The record", "/"), ("Try it", "/try/"), ("Worldspace", None))

    a10, b10, n = data["missA"], data["missB"], data["n"]
    lo, hi = data["interval"]
    count_line = s["field_count"].format(count=data["count"]["display"], shown=data["specimens"]["perColumn"] * len(data["worlds"]))
    thirteen = s["thirteen"].format(thirteen=facts["MC-003.identified_set_size"]["value"], nine=facts["MC-002.all_miss"]["value"],
                                    eighty_two=facts["MC-002.n_harmful"]["value"])
    disagree = issue_url(r["disagree_template"], r["disagree_prefill"])
    non_claims = "".join(f"<li>{esc(x)}</li>" for x in m["non_claims"])
    sheet_lo = sheet_svg(data, 0, f"World L: guard A misses {a10} of {n}, guard B misses {b10} of {n}, both miss 0 — the lower endpoint witness")
    sheet_hi = sheet_svg(data, data["missB"], f"World U: guard A misses {a10} of {n}, guard B misses {b10} of {n}, both miss {min(a10, b10)} — the upper endpoint witness")
    w_lo, w_hi = data["worlds"][0], data["worlds"][-1]
    fmt = lambda w: "(" + ", ".join(f"{v:.2f}" for v in w["atoms"]) + ")"  # noqa: E731
    canvas_label = (f"A field of specimen sheets in eleven columns, one column for each number of items both guards miss, "
                    f"0 to {min(a10, b10)}. Every sheet has guard A missing {a10} of {n} and guard B missing {b10} of {n}. "
                    f"Your own sheet is outlined in gold at its column.")

    body = f'''
<main id="main">
  <div class="ws-stage" id="ws" data-act="predict" data-both="0" data-a="{a10}" data-b="{b10}">
    <div class="in">
      <div class="ws-top">
        <h1 class="ws-h1">{esc(s["h1"])}<span>{esc(s["h1_sub"])}</span></h1>
        <button type="button" class="ws-sound" id="ws-sound" aria-pressed="false" hidden>{esc(s["sound_off"])}</button>
      </div>
      <div class="ws-band" id="ws-band">
        <div class="ws-readouts" role="group" aria-label="The two scores and the joint count">
          <div class="ws-readout" id="ro-a"><span class="ws-lbl">{esc(s["readout_a"])}</span><span class="ws-num"><b data-readout="a">{a10}</b><i>{esc(s["denominator"])}</i></span><span class="ws-fixed" data-fixed hidden>{esc(s["fixed"])}</span></div>
          <div class="ws-readout" id="ro-b"><span class="ws-lbl">{esc(s["readout_b"])}</span><span class="ws-num"><b data-readout="b">{b10}</b><i>{esc(s["denominator"])}</i></span><span class="ws-fixed" data-fixed hidden>{esc(s["fixed"])}</span></div>
          <div class="ws-readout ws-both" id="ro-both" hidden><span class="ws-lbl">{esc(s["readout_both"])}</span><span class="ws-num"><b data-readout="both">0</b><i>{esc(s["denominator"])}</i></span></div>
        </div>
        <p class="ws-stamp-row"><span class="ws-stamp" id="ws-stamp" hidden></span></p>
        <p class="ws-invariant" id="ws-invariant" hidden>{esc(s["invariant"])}</p>
      </div>
      <div class="sr-only" aria-live="polite" id="ws-live"></div>

      <section class="ws-act" id="act-predict" aria-labelledby="q-h">
        <h2 id="q-h" class="ws-q">{esc(s["question"])}</h2>
        <form id="ws-predict" class="ws-predict" novalidate>
          <label for="ws-guess" class="sr-only">{esc(s["predict_label"])}</label>
          <input id="ws-guess" type="number" inputmode="numeric" pattern="[0-9]*" min="0" max="{n}" step="1" autocomplete="off">
          <span class="ws-den">{esc(s["denominator"])}</span>
          <button type="submit" class="ws-btn ws-btn-solid" id="ws-commit">{esc(s["commit"])}</button>
        </form>
        <p class="ws-small"><button type="button" class="ws-link" id="ws-noguess">{esc(s["no_guess"])}</button> · <a class="ws-link" href="#exit" id="ws-skip">{esc(s["skip"])}</a></p>
      </section>

      <section class="ws-act" id="act-touch" hidden aria-labelledby="touch-h">
        <h2 id="touch-h" class="sr-only">Touch the world</h2>
        <div class="ws-sheet-wrap"><div class="ws-sheet" id="ws-sheet" role="group" aria-label="One hundred items. A disc marks an item guard A misses; a ring marks an item guard B misses; a ring resting on a disc marks an item both miss. Each ring is a button: activate it to move it onto a disc, or back off one."></div></div>
        <p class="ws-hint mono" id="ws-hint">{esc(s["touch_hint"])}</p>
        <div class="ws-ctl">
          <label for="ws-range" class="mono">{esc(s["set_label"])}</label>
          <div class="ws-ctl-row">
            <button type="button" class="ws-step" id="ws-minus" aria-label="One fewer item both miss">&minus;</button>
            <input type="range" id="ws-range" min="0" max="{min(a10, b10)}" step="1" value="0" aria-valuetext="0 of {n} both miss">
            <button type="button" class="ws-step" id="ws-plus" aria-label="One more item both miss">+</button>
          </div>
        </div>
        <div class="ws-name" id="ws-name" hidden><span>{esc(s["name_1"])}</span><span class="gold">{esc(s["name_2"])}</span></div>
        <p class="ws-next" id="ws-open-row" hidden><button type="button" class="ws-btn ws-btn-solid" id="ws-open">{esc(s["open"])}</button></p>
      </section>

      <section class="ws-act" id="act-field" hidden aria-labelledby="field-h">
        <h2 id="field-h" class="ws-field-title" hidden>{esc(s["field_title"])}</h2>
        <div class="ws-fieldwrap" id="ws-fieldwrap">
          <canvas id="ws-canvas" role="img" aria-label="{esc(canvas_label)}"></canvas>
          <div class="ws-axis" id="ws-axis" aria-hidden="true">
            <div class="seg" id="ws-seg"></div><div class="tail" id="ws-tail"></div>
            <span class="unit">0 … {min(a10, b10)} {esc(s["axis_unit"])}</span><span class="tailtxt">{esc(s["axis_tail"])}</span>
            <div class="ws-mark world" id="ws-mark-world" hidden><span class="pt"></span><span class="txt">{esc(s["your_world"])}</span></div>
            <div class="ws-mark pred" id="ws-mark-pred" hidden><span class="pt"></span><span class="txt" id="ws-pred-txt"></span></div>
            <div class="ws-mark ind" id="ws-mark-ind" hidden><span class="pt"></span><span class="txt">{esc(s["independence"])}</span></div>
          </div>
        </div>
        <p class="ws-count mono" id="ws-count">{esc(count_line)}</p>
        <div class="ws-ctl">
          <label for="ws-range2" class="mono">{esc(s["move_label"])}</label>
          <div class="ws-ctl-row">
            <button type="button" class="ws-step" id="ws-minus2" aria-label="Move your world one position left">&minus;</button>
            <input type="range" id="ws-range2" min="0" max="{min(a10, b10)}" step="1" value="0" aria-valuetext="0 of {n} both miss">
            <button type="button" class="ws-step" id="ws-plus2" aria-label="Move your world one position right">+</button>
          </div>
        </div>
        <div class="ws-indep" id="ws-indep" hidden>
          <span class="lbl">{esc(s["independence"])}</span>
          <span class="prod">{esc(s["independence_product"])}</span>
          <p class="two"><b>{esc(s["one_assumption"])}</b> {esc(s["one_point"])}</p>
          <button type="button" class="ws-switch" id="ws-assume" role="switch" aria-checked="false">{esc(s["assume"])}</button>
          <p class="ws-assume-text" id="ws-assume-text" hidden>{esc(s["assume_on"])}</p>
        </div>
        <p class="ws-next" id="ws-continue-row" hidden><button type="button" class="ws-btn ws-btn-solid" id="ws-continue">{esc(s["continue"])}</button><button type="button" class="ws-btn" id="ws-inspect">{esc(s["inspect_specimen"])}</button></p>
        <div class="ws-inspector" id="ws-inspector" hidden>
          <div class="ws-sheet ws-sheet-small" id="ws-spec-sheet" role="img" aria-label="One specimen arrangement"></div>
          <p id="ws-spec-cap"></p>
          <button type="button" class="ws-btn" id="ws-back">{esc(s["back"])}</button>
        </div>
      </section>

      <p class="ws-ledger mono" id="ws-ledger">{esc(m["ledger_tags"]["predict"])}</p>
    </div>
  </div>

  <section class="ws-static" id="ws-static" aria-labelledby="static-h">
    <div class="in">
      <h2 id="static-h">Two worlds, same scores</h2>
      <p class="lead">{esc(s["static_lead"])}</p>
      <div class="ws-two">
        <figure>{sheet_lo}<figcaption><b>WORLD L</b> · A {a10} / {n} · B {b10} / {n} · <b>both 0 / {n}</b> · π = {fmt(w_lo)} · lower endpoint witness</figcaption></figure>
        <figure>{sheet_hi}<figcaption><b>WORLD U</b> · A {a10} / {n} · B {b10} / {n} · <b>both {w_hi["q"]} / {n}</b> · π = {fmt(w_hi)} · upper endpoint witness</figcaption></figure>
      </div>
      <div class="ws-static-axis">{axis_svg(data, s)}</div>
      <p class="lead" style="margin-top:1rem">{esc(s["invariant"])} Both-miss runs from {round(lo * 100)}% to {round(hi * 100)}% while each guard misses {a10} of {n} in every world; independence would select {round(data["independence"] * 100)}%, one point inside.</p>
    </div>
  </section>

  <section class="ws-exit" id="exit" aria-labelledby="exit-h">
    <div class="in">
      <p class="ws-status mono">{esc(s["status_strip"])}</p>
      <h2 id="exit-h" class="ws-exit-h">{esc(s["exit_1"])}<br><b>{esc(s["exit_2"])}</b></h2>
      <p class="lead">{esc(s["exit_lead"])}</p>
      <pre><code>git clone https://github.com/Cubits11/cubits11.github.io.git &amp;&amp; cd cubits11.github.io
{esc(data["tryA"]["command"])}</code></pre>
      <p class="final mono">expected final line: <code>{esc(data["tryA"]["final"])}</code></p>
      <div class="ws-routes">
        <a class="btn btn-solid" href="{esc(r["primary"])}">{esc(s["run_a"])}</a>
        <a class="btn" href="{esc(r["claim"])}">{esc(s["inspect_claim"])}</a>
        <a class="btn" href="{esc(r["code"])}">{esc(s["inspect_code"])}</a>
        <a class="btn" href="{esc(disagree)}">{esc(s["report"])}</a>
      </div>
      <p class="ws-thirteen">{esc(thirteen)} <a class="u" href="{esc(r["experiment_b"])}">{esc(s["run_b"])}</a> · <code>{esc(data["tryB"]["command"])}</code></p>
      <details class="ws-bound">
        <summary>{esc(s["boundaries_summary"])}</summary>
        <ul>{non_claims}</ul>
        <p class="note"><span class="mono" style="color:var(--gold)">DERIVED · </span>{esc(m["constructed"]["counting_measure_note"]["text"])}</p>
      </details>
      <p class="ws-prov mono">CC-001 · CC-004 · cc-framework kernel @ {esc(facts["CC-001.support_commit"]["value"][:8])} · numbers from films/data/facts.json (bound to claims.yaml) · every string and object from worldspace/manifest.yaml · <a class="u" href="{esc(r["witnesses"])}">endpoint witnesses</a> · <a class="u" href="/corrections/">corrections</a></p>
    </div>
  </section>
</main>
<script type="application/json" id="ws-data">{json.dumps(data, separators=(",", ":"), ensure_ascii=False)}</script>
<script src="/worldspace/worldspace.js" defer></script>'''
    return head.replace("</style>\n</head>", "</style>\n" + crumbs.strip() + "\n</head>") + body + PAGE_FOOT


def main() -> int:
    m = yaml.safe_load(MANIFEST.read_text())
    facts = json.loads(FACTS.read_text())["facts"]
    exp = yaml.safe_load(EXPERIMENTS.read_text())
    data = build_data(m, facts, exp)
    html = render(m, data, facts)
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != html:
            print("DRIFT: worldspace/index.html does not match its generator. Run: python3 scripts/generate_worldspace.py")
            return 1
        print("ok    /worldspace/ matches the manifest, the bound facts and experiments.yaml")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote worldspace/index.html ({len(html)} bytes; {len(data['worlds'])} worlds, "
          f"{data['specimens']['perColumn'] * len(data['worlds'])} specimens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
