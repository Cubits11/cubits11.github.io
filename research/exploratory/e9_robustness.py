#!/usr/bin/env python3
"""EXPLORATORY. Attacks on E9's frozen result, run after its outcome was seen.

    python3 research/exploratory/e9_robustness.py           # writes e9_robustness.json
    python3 research/exploratory/e9_robustness.py --check   # recompute; exit 1 on drift

Status, stated before the numbers: every row here was scored and every outcome
read before this file existed. Correction C3 in research/DIRECTION.yaml: a
choice made after looking at rows is exploratory on those rows. Nothing here
replaces, re-labels or rescues E9's preregistered verdict; experiments/e9/
RESULT.md stays the result. What this file can do is show whether a reasonable
alternative analysis would change the scoped conclusion, and which of E9's
unmodelled uncertainties matter. A reanalysis that fails to move the result is
evidence about the analysis, not new evidence about the world.

Inputs are the atomic per-item score vectors E9 committed (results/scores.json,
correction C3). Thresholds come from E9's own runner.select_threshold under the
frozen contract's operating point. Before writing anything, the script
recomputes the frozen thresholds, the 2x2 table and the discrepancy and refuses
if any differs from results/analysis.json.

  A. The 2x2 table and residual coverage: P(G2 catches | G1 missed) and the
     reverse. A stack decision turns on these, not on the discrepancy.
  B. Conditional association: Fisher's exact test and the odds ratio.
  C. Nested recalibration bootstrap: resample the calibration set, re-select
     both thresholds, resample the measurement set. E9's interval held the
     thresholds fixed; this one carries calibration uncertainty.
  D. Operating-point surface: the same quantities at other false-positive
     budgets. Post-hoc by construction; it says how local E9's point is.
  E. Not computable here, named so the gap is not mistaken for a pass.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E9 = ROOT / "experiments/e9"
OUT = Path(__file__).with_suffix(".json")

sys.path.insert(0, str(E9 / "run"))
_spec = importlib.util.spec_from_file_location("e9_runner", E9 / "run/runner.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)

SEED = "EXPLORATORY-E9-ROBUSTNESS-2026-09-25"
B = 2000
BUDGETS = ["0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.075", "0.10"]
GUARDS = ("G1", "G2")


def load(rel: str) -> dict:
    return json.loads((E9 / rel).read_text())


def table(meas: list[dict], t: dict) -> dict:
    """Cells keyed by (G1 missed, G2 missed). A miss is score below threshold (comparator ge)."""
    c = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    for v in meas:
        c[(int(not v["G1"] >= t["G1"]), int(not v["G2"] >= t["G2"]))] += 1
    return c


def summarize(c: dict) -> dict:
    n = sum(c.values())
    m1, m2, both = c[(1, 0)] + c[(1, 1)], c[(0, 1)] + c[(1, 1)], c[(1, 1)]
    q, p1, p2 = Fraction(both, n), Fraction(m1, n), Fraction(m2, n)
    delta = q - p1 * p2
    return {
        "n": n, "g1_miss": m1, "g2_miss": m2, "both_miss": both,
        "delta": delta,
        "r_g2_after_g1_miss": Fraction(c[(1, 0)], m1) if m1 else None,
        "r_g1_after_g2_miss": Fraction(c[(0, 1)], m2) if m2 else None,
        "width": min(p1, p2) - max(Fraction(0), p1 + p2 - 1),
    }


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 6), round(centre + half, 6)]


def fisher(c: dict) -> dict:
    a, b, cc, d = c[(0, 0)], c[(0, 1)], c[(1, 0)], c[(1, 1)]
    n, r1, c1 = a + b + cc + d, a + b, a + cc
    lf = lambda k: math.lgamma(k + 1)
    pmf = lambda x: math.exp(lf(r1) + lf(n - r1) + lf(c1) + lf(n - c1) - lf(n)
                             - lf(x) - lf(r1 - x) - lf(c1 - x) - lf(n - r1 - c1 + x))
    p0 = pmf(a)
    p = sum(pmf(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if pmf(x) <= p0 * (1 + 1e-7))
    return {"odds_ratio": round(a * d / (b * cc), 4) if b and cc else None,
            "p_two_sided": float(f"{p:.3e}")}


def fast_threshold(desc: list[float], budget: Fraction) -> float | None:
    """select_threshold for ge/lowest on scores sorted descending; asserted equal to the runner's."""
    allowed = int(budget * len(desc))
    if allowed >= len(desc):
        return desc[-1]
    above = [s for s in desc[:allowed] if s > desc[allowed]]
    return min(above) if above else None


def pct(xs: list[float]) -> list[float]:
    xs = sorted(xs)
    return [round(xs[int(.025 * len(xs))], 6), round(xs[min(len(xs) - 1, int(.975 * len(xs)))], 6)]


def compute() -> dict:
    contract, analysis = load("contract.json"), load("results/analysis.json")
    scores = load("results/scores.json")
    plan = contract["execution_plan"]
    cal = [scores["pools"][plan["calibration"]][i] for i in sorted(scores["pools"][plan["calibration"]])]
    meas = [scores["pools"][plan["evaluation"]][i] for i in sorted(scores["pools"][plan["evaluation"]])]
    op = contract["operating_point"]
    frozen_budget = Fraction(str(op["fpr_budget"]))

    # ---- self-check: the frozen result, recomputed, or nothing is written
    t = {g: runner.select_threshold([v[g] for v in cal], op) for g in GUARDS}
    if t != analysis["thresholds"]:
        raise SystemExit(f"REFUSED: thresholds {t} != recorded {analysis['thresholds']}")
    for g in GUARDS:
        if fast_threshold(sorted((v[g] for v in cal), reverse=True), frozen_budget) != t[g]:
            raise SystemExit(f"REFUSED: fast threshold disagrees with runner.select_threshold for {g}")
    c = table(meas, t)
    s = summarize(c)
    if str(s["delta"]) != analysis["delta_exact"] or s["both_miss"] / s["n"] != analysis["q_obs"]:
        raise SystemExit(f"REFUSED: recomputed delta {s['delta']} != recorded {analysis['delta_exact']}")

    # ---- A, B
    part_a = {
        "cells": {"g1_catch_g2_catch": c[(0, 0)], "g1_catch_g2_miss": c[(0, 1)],
                  "g1_miss_g2_catch": c[(1, 0)], "both_miss": c[(1, 1)]},
        "residual_coverage": {
            "g2_catches_after_g1_misses": {"k": c[(1, 0)], "n": s["g1_miss"],
                                           "rate": round(float(s["r_g2_after_g1_miss"]), 6),
                                           "wilson95": wilson(c[(1, 0)], s["g1_miss"])},
            "g1_catches_after_g2_misses": {"k": c[(0, 1)], "n": s["g2_miss"],
                                           "rate": round(float(s["r_g1_after_g2_miss"]), 6),
                                           "wilson95": wilson(c[(0, 1)], s["g2_miss"])},
        },
        "reads": "a stack that adds G2 behind G1 catches this share of what G1 missed, and the reverse",
    }
    part_b = fisher(c)

    # ---- C: nested recalibration bootstrap
    rng = random.Random(int(hashlib.sha256(SEED.encode()).hexdigest(), 16))
    reps = {"delta": [], "r21": [], "width": []}
    moved = 0
    for _ in range(B):
        cb = [cal[rng.randrange(len(cal))] for _ in cal]
        tb = {g: fast_threshold(sorted((v[g] for v in cb), reverse=True), frozen_budget) for g in GUARDS}
        if None in tb.values():
            continue
        moved += tb != t
        mb = [meas[rng.randrange(len(meas))] for _ in meas]
        sb = summarize(table(mb, tb))
        reps["delta"].append(float(sb["delta"]))
        reps["width"].append(float(sb["width"]))
        if sb["r_g2_after_g1_miss"] is not None:
            reps["r21"].append(float(sb["r_g2_after_g1_miss"]))
    sesoi = contract["inference"]["decision"]["SESOI"]
    floor = contract["inference"]["informativeness"]["marginal_only_width_min"]
    part_c = {
        "B": B, "replicates": len(reps["delta"]), "thresholds_moved_in": moved,
        "delta_95": pct(reps["delta"]),
        "frozen_delta_95_thresholds_fixed": analysis["delta_ci95"],
        "share_delta_positive": round(sum(d > 0 for d in reps["delta"]) / len(reps["delta"]), 4),
        "share_delta_at_or_above_sesoi": round(sum(d >= sesoi for d in reps["delta"]) / len(reps["delta"]), 4),
        "width_95": pct(reps["width"]),
        "share_width_at_or_above_floor": round(sum(w >= floor for w in reps["width"]) / len(reps["width"]), 4),
        "g2_after_g1_miss_95": pct(reps["r21"]),
    }

    # ---- D: operating-point surface (post-hoc)
    surface = []
    for b in BUDGETS:
        opb = copy.deepcopy(op)
        opb["fpr_budget"] = float(b)
        tb = {g: runner.select_threshold([v[g] for v in cal], opb) for g in GUARDS}
        if None in tb.values():
            surface.append({"fpr_budget": b, "thresholds": None})
            continue
        sb = summarize(table(meas, tb))
        rr = random.Random(int(hashlib.sha256(f"{SEED}:{b}".encode()).hexdigest(), 16))
        ds = [float(summarize(table([meas[rr.randrange(len(meas))] for _ in meas], tb))["delta"])
              for _ in range(500)]
        surface.append({
            "fpr_budget": b, "frozen": b == str(op["fpr_budget"]) or Fraction(b) == frozen_budget,
            "miss": {"G1": sb["g1_miss"] / sb["n"], "G2": sb["g2_miss"] / sb["n"]},
            "both_miss": sb["both_miss"] / sb["n"],
            "delta": round(float(sb["delta"]), 6), "delta_95_thresholds_fixed_B500": pct(ds),
            "g2_after_g1_miss": round(float(sb["r_g2_after_g1_miss"]), 6) if sb["r_g2_after_g1_miss"] is not None else None,
            "width": round(float(sb["width"]), 6),
        })

    return {
        "status": "EXPLORATORY — run after E9's outcome was read; see the module docstring. "
                  "E9's preregistered verdict is in experiments/e9/RESULT.md and is not changed here.",
        "seed": SEED,
        "self_check": "frozen thresholds, table and exact discrepancy recomputed from results/scores.json "
                      "and equal to results/analysis.json",
        "A_table_and_residual_coverage": part_a,
        "B_conditional_association": {**part_b, "question": "given the observed margins, are the two miss "
                                      "indicators associated? Exploratory; not the preregistered analysis."},
        "C_nested_recalibration_bootstrap": part_c,
        "D_operating_point_surface": surface,
        "E_not_computable_here": [
            "cluster sensitivity by Mosscap level: the level column is in freeze/sources/, which is rebuilt "
            "from the pinned upstream file and not committed",
            "near-duplicate sensitivity: prompt texts are not committed; only their sha256 is",
            "any population beyond the admitted pool, guard pair or benign calibration population",
        ],
        "non_claims": [
            "not a result of E9 and not a replacement for its verdict",
            "an operating point read off section D is chosen after the rows were seen and is exploratory",
            "agreement between these analyses and E9 is not independent replication: same rows, same analyst",
        ],
        "inputs_sha256": {rel: hashlib.sha256((E9 / rel).read_bytes()).hexdigest()
                          for rel in ("contract.json", "results/scores.json", "results/analysis.json")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    text = json.dumps(compute(), indent=1, default=str) + "\n"
    if ap.parse_args().check:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"DRIFT  {OUT.relative_to(ROOT)} differs from a fresh recomputation")
            return 1
        print(f"ok    {OUT.relative_to(ROOT)} recomputes byte for byte")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
