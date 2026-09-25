#!/usr/bin/env python3
"""EXPLORATORY. How wide can the marginal-only identified set get on the pools
this repository has already scored, as the false-positive budget moves?

    python3 research/exploratory/width_curve.py           # writes width_curve.json
    python3 research/exploratory/width_curve.py --check   # recompute; exit 1 on drift

Status, stated before the numbers: every row read here was already scored and
already seen. E3 and E3B are reported experiments; E8's scouting slices are
burned. Correction C3 in research/DIRECTION.yaml: a budget chosen after looking
at these rows is exploratory on these rows. Nothing here is confirmatory,
nothing here may be quoted as a result of E3, E3B or E8, and nothing here can
move E9, whose budget, rule and calibration population were frozen on
2026-09-18 before this file existed.

What it computes, per pool and per budget b:
  1. each guard's threshold from its benign calibration scores, by the E8
     runner's own select_threshold under the E8 contract's operating point with
     only fpr_budget replaced by b — one implementation, not a copy;
  2. each guard's miss rate m1, m2 on the pool's harmful items;
  3. the Frechet width a marginal-only reader faces:
         min(m1, m2) - max(0, m1 + m2 - 1) = min(m1, m2, 1 - m1, 1 - m2)
  4. a 95% percentile bootstrap interval for that width, resampling benign
     calibration items and harmful items independently and re-selecting the
     thresholds in every replicate, so calibration noise is inside the interval.

What it deliberately does not compute: the observed joint miss, the
independence plug-in, or their discrepancy. That is E9's confirmatory
estimand. An informal version of it on burned rows at a budget picked from a
sweep is the forking path the freeze exists to close.

Self-check: at b = 0.05, the operating point every pool was actually run at,
the recomputed thresholds and miss rates must equal the recorded ones exactly
(E3, E3B: results/e3_result.json; E8: freeze/scouting.json). If they do not,
the script refuses to write anything.
"""
from __future__ import annotations

import argparse
import bisect
import copy
import hashlib
import importlib.util
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_suffix(".json")

spec = importlib.util.spec_from_file_location("e8_runner", ROOT / "experiments/e8/run/runner.py")
runner = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(ROOT / "experiments/e8/run"))
spec.loader.exec_module(runner)

SEED = "EXPLORATORY-WIDTH-CURVE-2026-09-25"
B = 1000
BUDGETS = ["0.005", "0.01", "0.02", "0.03", "0.05", "0.075", "0.10", "0.15", "0.20", "0.25", "0.30"]
RECORDED_BUDGET = "0.05"
FLOOR_SOURCE = "experiments/e8/contract.json"

POOLS = [
    # id, harmful scores, benign calibration scores, where the recorded b=0.05 numbers live
    ("e3/orbench-toxic", "experiments/e3/results/items_harmful.probs.json",
     "experiments/e3/results/items_benign_calibration.probs.json",
     ("e3", "experiments/e3/results/e3_result.json", "experiments/e3/e3_config.json")),
    ("e3b/gandalf", "experiments/e3b/results/items_harmful.probs.json",
     "experiments/e3b/results/items_benign_calibration.probs.json",
     ("e3", "experiments/e3b/results/e3_result.json", "experiments/e3b/e3b_config.json")),
    ("e8-scout/mosscap-test", "experiments/e8/results/scores/scout_mosscap-test.probs.json",
     "experiments/e8/results/scores/benign_scout.probs.json", ("e8", "mosscap-test")),
    ("e8-scout/spml-injection", "experiments/e8/results/scores/scout_spml-injection.probs.json",
     "experiments/e8/results/scores/benign_scout.probs.json", ("e8", "spml-injection")),
    ("e8-scout/itw-jailbreak", "experiments/e8/results/scores/scout_itw-jailbreak.probs.json",
     "experiments/e8/results/scores/benign_scout.probs.json", ("e8", "itw-jailbreak")),
]
GUARDS = ("G1", "G2")


def load(rel: str) -> dict[str, list[float]]:
    guards = json.loads((ROOT / rel).read_text())["guards"]
    ids = sorted(guards[GUARDS[0]])
    for g in GUARDS:
        if sorted(guards[g]) != ids:
            raise SystemExit(f"{rel}: {g} does not score the same items as {GUARDS[0]}")
    return {g: [guards[g][i] for i in ids] for g in GUARDS}


def operating_point(budget: str) -> dict:
    op = copy.deepcopy(json.loads((ROOT / "experiments/e8/contract.json").read_text())["operating_point"])
    op["fpr_budget"] = float(budget)
    return op


def fast_threshold(desc: list[float], budget: Fraction) -> float | None:
    """select_threshold for comparator ge, direction lowest, on scores sorted descending.

    Used only inside the bootstrap. Its agreement with the runner's own function
    is asserted on every point estimate before any interval is reported.
    """
    n = len(desc)
    allowed = int(budget * n)            # largest fp count within budget
    if allowed >= n:
        return desc[-1]
    # lowest t in the observed scores with #{s >= t} <= allowed: every score
    # strictly above desc[allowed] is admissible, and the lowest such is the
    # smallest distinct value above it.
    cut = desc[allowed]
    above = [s for s in desc[:allowed] if s > cut]
    return min(above) if above else None


def miss(harm: list[float], t: float | None) -> Fraction | None:
    if t is None:
        return None
    return Fraction(sum(1 for s in harm if not s >= t), len(harm))


def width(m1: Fraction, m2: Fraction) -> Fraction:
    return min(m1, m2) - max(Fraction(0), m1 + m2 - 1)


def recorded(ref: tuple) -> tuple[dict[str, float], dict[str, Fraction]]:
    """(thresholds, miss rates) as the experiment recorded them at b = 0.05."""
    if ref[0] == "e3":
        h = json.loads((ROOT / ref[1]).read_text())["harmful"]
        cfg = json.loads((ROOT / ref[2]).read_text())["guards"]
        return ({g: cfg[g]["threshold"] for g in GUARDS},
                {g: Fraction(str(h[f"p_miss_{g}"])).limit_denominator(10_000) for g in GUARDS})
    res = json.loads((ROOT / "experiments/e8/freeze/scouting.json").read_text())["results"]
    c = next(c for c in res["candidates"] if c["id"] == ref[1])
    return dict(res["scouting_thresholds"]), {g: Fraction(c["miss"][g]) for g in GUARDS}


def compute() -> dict:
    floor = json.loads((ROOT / FLOOR_SOURCE).read_text())["inference"]["informativeness"]["marginal_only_width_min"]
    floor_f = Fraction(str(floor))
    rng = random.Random(int(hashlib.sha256(SEED.encode()).hexdigest(), 16))
    pools = []
    for pid, harm_rel, ben_rel, ref in POOLS:
        harm, ben = load(harm_rel), load(ben_rel)
        rows = []
        for b in BUDGETS:
            op, bf = operating_point(b), Fraction(b)
            t = {g: runner.select_threshold(ben[g], op) for g in GUARDS}
            for g in GUARDS:
                if fast_threshold(sorted(ben[g], reverse=True), bf) != t[g]:
                    raise SystemExit(f"{pid} b={b} {g}: bootstrap threshold disagrees with runner.select_threshold")
            m = {g: miss(harm[g], t[g]) for g in GUARDS}
            if b == RECORDED_BUDGET and (t, m) != recorded(ref):
                raise SystemExit(f"{pid}: recomputed (thresholds, miss rates) at b=0.05 {(t, m)} "
                                 f"!= recorded {recorded(ref)}")
            w = width(m["G1"], m["G2"]) if None not in m.values() else None
            reps = []
            nh, nb = len(harm["G1"]), len(ben["G1"])
            for _ in range(B):
                hi = [rng.randrange(nh) for _ in range(nh)]
                bi = [rng.randrange(nb) for _ in range(nb)]
                mm = []
                for g in GUARDS:
                    tt = fast_threshold(sorted((ben[g][i] for i in bi), reverse=True), bf)
                    mm.append(miss([harm[g][i] for i in hi], tt))
                if None not in mm:
                    reps.append(width(*mm))
            reps.sort()
            lo = reps[int(0.025 * len(reps))] if reps else None
            hi_ = reps[min(len(reps) - 1, int(0.975 * len(reps)))] if reps else None
            rows.append({
                "fpr_budget": b,
                "threshold": t,
                "miss": {g: (str(m[g]) if m[g] is not None else None) for g in GUARDS},
                "width": str(w) if w is not None else None,
                "width_float": round(float(w), 6) if w is not None else None,
                "width_ci95": [round(float(lo), 6), round(float(hi_), 6)] if reps else None,
                "replicates_defined": len(reps),
                "point_at_or_above_floor": w is not None and w >= floor_f,
                "ci_lower_at_or_above_floor": lo is not None and lo >= floor_f,
            })
        best = max((r for r in rows if r["width"] is not None), key=lambda r: Fraction(r["width"]))
        pools.append({
            "pool": pid, "harmful": harm_rel, "benign_calibration": ben_rel,
            "n_harmful": len(harm["G1"]), "n_benign_calibration": len(ben["G1"]),
            "reproduces_recorded_at_0.05": True,
            "curve": rows,
            "widest_on_grid": {"fpr_budget": best["fpr_budget"], "width": best["width_float"],
                               "width_ci95": best["width_ci95"]},
            "first_budget_point_clears_floor": next((r["fpr_budget"] for r in rows if r["point_at_or_above_floor"]), None),
            "first_budget_ci_clears_floor": next((r["fpr_budget"] for r in rows if r["ci_lower_at_or_above_floor"]), None),
        })
    return {
        "status": "EXPLORATORY — every row was already scored and seen; see the module docstring",
        "seed": SEED, "bootstrap_B": B, "interval": "percentile 95%, benign and harmful resampled independently, thresholds re-selected per replicate",
        "operating_point": "experiments/e8/contract.json#operating_point with fpr_budget replaced by each grid value; runner.select_threshold",
        "floor": {"value": floor, "source": FLOOR_SOURCE + "#inference.informativeness.marginal_only_width_min"},
        "budgets": BUDGETS,
        "not_computed": "observed joint miss, independence plug-in, discrepancy — E9's confirmatory estimand",
        "non_claims": [
            "not a result of E3, E3B or E8; those stand as recorded",
            "a budget read off this curve is chosen after the rows were seen and is exploratory on them",
            "says nothing about E9, whose calibration population differs and whose rule was frozen first",
            "a wide marginal-only set is a precondition for a discrepancy to be visible, not evidence one exists",
            "calibration sets differ by experiment; curves are comparable within a pool, not across calibration sets",
        ],
        "inputs_sha256": {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
                          for rel in sorted({p[1] for p in POOLS} | {p[2] for p in POOLS})},
        "pools": pools,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = json.dumps(compute(), indent=1) + "\n"
    if args.check:
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
