#!/usr/bin/env python3
"""Apply scouting.json's declared rule to the scouting scores and record the choice.

    python3 experiments/e8/run/scout.py

Thresholds come from the contract's operating point applied to the scouting
benign calibration set through the runner's own select_threshold, so the
scouting operating point is the run's rule and not a second implementation of
it. The output is appended under scouting.json["results"]; nothing above it
changes. Every item read here is burned for evaluation.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E8 = ROOT / "experiments/e8"
FREEZE, SCORES = E8 / "freeze", E8 / "results" / "scores"

_spec = importlib.util.spec_from_file_location("runner", E8 / "run" / "runner.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)


def main() -> int:
    plan = json.loads((FREEZE / "scouting.json").read_text())
    if plan.get("results"):
        print("REFUSED: scouting.json already records results; a second scouting pass is a second look")
        return 1
    contract = runner.load_contract(E8 / "contract.json", require_frozen=False)
    op = contract["operating_point"]
    flags = runner.COMPARATORS[op["comparator"]]
    benign = json.loads((SCORES / "benign_scout.probs.json").read_text())["guards"]
    thresholds = {g: runner.select_threshold(list(v.values()), op) for g, v in benign.items()}
    if any(t is None for t in thresholds.values()):
        print(f"STOP: no feasible threshold within budget on the scouting calibration set: {thresholds}")
        return 1
    lo_band, hi_band = (Fraction(str(x)) for x in plan["middle_band"])
    n_needed = plan["sizes"]["scout_harmful_per_candidate"] + plan["sizes"]["evaluation_harmful"]
    rows = []
    for cand in plan["candidates"]:
        rec = json.loads((SCORES / f"scout_{cand['id']}.probs.json").read_text())
        n = rec["n"]
        miss = {g: Fraction(sum(1 for p in rec["guards"][g].values() if not flags(p, thresholds[g])), n)
                for g in thresholds}
        ps = list(miss.values())
        lo = max(Fraction(0), sum(ps) - (len(ps) - 1))
        hi = min(ps)
        width = hi - lo
        available = cand.get("available_after_removal")
        in_band = all(lo_band <= p <= hi_band for p in ps)
        by_size = available is not None and available >= n_needed
        rows.append({"id": cand["id"], "n": n, "miss": {g: str(p) for g, p in miss.items()},
                     "miss_float": {g: float(p) for g, p in miss.items()},
                     "frechet": [str(lo), str(hi)], "width": str(width), "width_float": float(width),
                     "in_middle_band": in_band, "enough_rows": by_size, "available_after_removal": available,
                     "eligible": in_band and by_size})
    eligible = [r for r in rows if r["eligible"]]
    chosen = max(eligible, key=lambda r: (Fraction(r["width"]), -[r["id"] for r in rows].index(r["id"]))) if eligible else None
    plan["results"] = {
        "scouting_thresholds": thresholds,
        "scouting_calibration_n": next(iter(benign.values())).__len__(),
        "candidates": rows,
        "chosen": chosen["id"] if chosen else None,
        "verdict": (f"{chosen['id']} chosen: widest scouting Frechet width among eligible candidates"
                    if chosen else "NO-ELIGIBLE-POOL: E8 stops before any evaluation item is scored"),
        "burned": "every item in items_scout_*.csv and items_benign_scout.csv; excluded from evaluation by hash",
    }
    (FREEZE / "scouting.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    for r in rows:
        print(f"{r['id']:<16} miss {r['miss_float']}  width {r['width_float']:.4f}  "
              f"band {r['in_middle_band']}  rows {r['enough_rows']}  -> {'ELIGIBLE' if r['eligible'] else 'no'}")
    print(plan["results"]["verdict"])
    return 0 if chosen else 1


if __name__ == "__main__":
    sys.exit(main())
