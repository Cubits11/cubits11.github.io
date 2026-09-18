#!/usr/bin/env python3
"""Apply protocol.json's admission rule at E9's fixed operating point, and record it.

    python3 experiments/e9/run/admit.py

Thresholds come from the frozen contract's operating point applied to the
calibration set through the runner's own select_threshold. That is one rule,
one implementation, and the same numbers the runner recomputes at measurement.
The stress stratum is read against those thresholds and reported; it decides
nothing. Each candidate's scouting slice gives its miss rates and Frechet width
at those thresholds, and the width is compared with the contract's floor.

The output is appended under protocol.json["results"]. Nothing above it
changes, and a second pass is refused: a second look is not a second chance.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E9 = ROOT / "experiments/e9"
FREEZE, SCORES = E9 / "freeze", E9 / "results" / "scores"


def module(name: str):
    spec = importlib.util.spec_from_file_location(name, E9 / "run" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner, score = module("runner"), module("score")


def scores(setname: str) -> dict:
    return json.loads((SCORES / f"{setname}.probs.json").read_text())


def main() -> int:
    plan = json.loads((FREEZE / "protocol.json").read_text())
    if plan.get("results"):
        print("REFUSED: protocol.json already records results; a second admission pass is a second look")
        return 1
    freeze = json.loads((FREEZE / "freeze.json").read_text())
    if score.declared_digest(plan) != freeze["protocol_declared_sha256"]:
        print("REFUSED: protocol.json above results no longer matches the frozen declaration")
        return 1
    contract = runner.load_contract(E9 / "contract.json", require_frozen=True)
    op = contract["operating_point"]
    flags = runner.COMPARATORS[op["comparator"]]
    floor = Fraction(str(contract["inference"]["informativeness"]["marginal_only_width_min"]))

    calibration = scores("calibration")["guards"]
    thresholds, excluded = {}, []
    for g, by_item in calibration.items():
        t = runner.select_threshold(list(by_item.values()), op)
        if t is None:
            if op["no_feasible_candidate"] != "exclude_judge":
                raise runner.Refusal(f"policy {op['no_feasible_candidate']!r} has no implementation here")
            excluded.append(g)
        else:
            thresholds[g] = t
    results = {"calibration_n": len(next(iter(calibration.values()))), "thresholds": thresholds,
               "excluded_guards": excluded, "floor": str(floor)}
    e8 = json.loads((ROOT / "experiments/e8/freeze/scouting.json").read_text())["results"]
    if len(thresholds) < 2:
        results.update({"admitted": None, "hypothesis": "H1",
                        "verdict": (f"NO-FEASIBLE-OPERATING-POINT: {excluded} admit no threshold within the budget on "
                                    f"representative benign traffic. E9 stops before any scouting or measurement item "
                                    f"is read; the local-path stop is recorded.")})
    else:
        stress = scores("stress")
        ids = list(next(iter(stress["guards"].values())))
        n = len(ids)
        flagged = {g: sum(1 for i in ids if flags(stress["guards"][g][i], thresholds[g])) for g in thresholds}
        both = sum(1 for i in ids if all(flags(stress["guards"][g][i], thresholds[g]) for g in thresholds))
        results["stress"] = {"n": n, "flagged": flagged,
                             "false_positive_rate": {g: str(Fraction(c, n)) for g, c in flagged.items()},
                             "false_positive_rate_float": {g: c / n for g, c in flagged.items()},
                             "both_flagged": both, "both_flagged_rate": both / n}
        order = [c["id"] for c in plan["candidates"]]
        rows = []
        for cand in plan["candidates"]:
            rec = scores(f"scout_{cand['id']}")
            m = rec["n"]
            miss = {g: Fraction(sum(1 for p in rec["guards"][g].values() if not flags(p, thresholds[g])), m)
                    for g in thresholds}
            ps = list(miss.values())
            lo, hi = max(Fraction(0), sum(ps) - (len(ps) - 1)), min(ps)
            complete = plan["draw"]["candidates"][cand["id"]]["measurement_complete"]
            rows.append({"id": cand["id"], "n": m, "miss": {g: str(p) for g, p in miss.items()},
                         "miss_float": {g: float(p) for g, p in miss.items()},
                         "frechet": [str(lo), str(hi)], "width": str(hi - lo), "width_float": float(hi - lo),
                         "width_clears_floor": hi - lo >= floor, "measurement_complete": complete,
                         "admitted": hi - lo >= floor and complete})
        admitted = [r for r in rows if r["admitted"]]
        chosen = (max(admitted, key=lambda r: (Fraction(r["width"]), -order.index(r["id"]))) if admitted else None)
        e8_rows = {c["id"]: c for c in e8["candidates"]}
        results.update({
            "candidates": rows,
            "admitted": chosen["id"] if chosen else None,
            "hypothesis": "H2" if chosen else "H1",
            "verdict": (f"{chosen['id']} admitted: at E9's operating point its scouting width {chosen['width_float']:.4f} "
                        f"clears the floor {float(floor)}, the widest among admitted candidates. H2's prediction held for "
                        f"these pools." if chosen else
                        f"NO-ADMISSIBLE-POOL: at E9's operating point no candidate's scouting width clears the floor "
                        f"{float(floor)} with a complete measurement slice. H1's prediction held for these pools. E9 "
                        f"stops before any measurement item is scored; the local-path stop is recorded, and a "
                        f"new-guard experiment (E10) is the justified next step."),
            "e8_comparison": {"thresholds": {"E8": e8["scouting_thresholds"], "E9": thresholds},
                              "scouting": {r["id"]: {"E8_miss": e8_rows[r["id"]]["miss_float"], "E9_miss": r["miss_float"],
                                                     "E8_width": e8_rows[r["id"]]["width_float"],
                                                     "E9_width": r["width_float"]} for r in rows}},
        })
    results["burned"] = ("every calibration, stress and scouting item; none enters measurement, and the "
                         "measurement slices were drawn before any score")
    plan["results"] = results
    (FREEZE / "protocol.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    print(f"thresholds {thresholds}  excluded {excluded}")
    for r in results.get("candidates", []):
        print(f"{r['id']:<16} miss {r['miss_float']}  width {r['width_float']:.4f}  "
              f"clears {r['width_clears_floor']}  complete {r['measurement_complete']}  -> "
              f"{'ADMITTED' if r['admitted'] else 'no'}")
    if "stress" in results:
        print(f"stress: false-positive rate {results['stress']['false_positive_rate_float']} "
              f"both {results['stress']['both_flagged_rate']:.4f}")
    print(results["verdict"])
    return 0 if results["admitted"] else 1


if __name__ == "__main__":
    sys.exit(main())
