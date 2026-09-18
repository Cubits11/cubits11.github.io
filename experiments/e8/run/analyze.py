#!/usr/bin/env python3
"""E8 analysis: the bootstrap interval on the discrepancy, read against the contract.

    python3 experiments/e8/run/analyze.py

Reads results/observations.jsonl and results/result.json as the runner wrote
them, the contract for the SESOI, margin, desired half width and floor, and
freeze.json for the bootstrap seed and B. Writes results/analysis.json. It adds
no threshold and no cell: every quantity is a function of the stored per-item
score vectors, the contract and the seed.

The identification verdict is the runner's, not this file's. When the runner
reports IDENTIFICATION-LIMITED the interval is still computed and recorded,
and the verdict below says no discrepancy is claimed from it.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E8 = ROOT / "experiments/e8"
RESULTS = E8 / "results"


def delta_of(rows: list[dict], guards: list[str]) -> Fraction:
    n = len(rows)
    all_miss = sum(all(r["miss"][g] for g in guards) for r in rows)
    plug = Fraction(1)
    for g in guards:
        plug *= Fraction(sum(r["miss"][g] for r in rows), n)
    return Fraction(all_miss, n) - plug


def main() -> int:
    contract = json.loads((E8 / "contract.json").read_text())
    freeze = json.loads((E8 / "freeze" / "freeze.json").read_text())
    result = json.loads((RESULTS / "result.json").read_text())
    rows = [json.loads(l) for l in (RESULTS / "observations.jsonl").read_text().splitlines()]
    guards = result["active_guards"]
    n = len(rows)
    delta = delta_of(rows, guards)
    assert str(delta) == result["identification"]["delta_all_miss"], "analysis disagrees with the runner"

    B, seed = freeze["bootstrap"]["B"], freeze["seed"]
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16))
    deltas = sorted(float(delta_of([rows[rng.randrange(n)] for _ in range(n)], guards)) for _ in range(B))
    ci = [deltas[int(.025 * B)], deltas[int(.975 * B) - 1]]
    half = (ci[1] - ci[0]) / 2
    inf = contract["inference"]
    sesoi, margin = inf["decision"]["SESOI"], inf["decision"]["equivalence_margin"]
    desired = inf["precision"]["desired_ci_half_width"]
    ident = result["identification"]
    limited = ident["status"] != "INFORMATIVE"
    out = {
        "experiment": "E8", "contract_id": contract["id"], "n": n, "guards": guards,
        "miss_rates": {g: result["evaluation"]["miss_counts"][g] / n for g in guards},
        "q_obs": result["evaluation"]["all_miss"] / n,
        "q_ind": float(Fraction(result["evaluation"]["plug_in_all_miss_count"]) / n),
        "delta": float(delta), "delta_exact": str(delta),
        "delta_ci95": ci, "bootstrap_B": B, "seed": seed,
        "realized_ci_half_width": half, "desired_ci_half_width": desired,
        "precision_met": half <= desired,
        "ci_excludes_zero": ci[0] > 0 or ci[1] < 0,
        "ci_within_equivalence_margin": -margin <= ci[0] and ci[1] <= margin,
        "point_at_or_beyond_sesoi": abs(float(delta)) >= sesoi,
        "marginal_only_width": float(Fraction(ident["marginal_only_width"])),
        "marginal_only_width_exact": ident["marginal_only_width"],
        "declared_floor": float(Fraction(ident["floor"])) if ident["floor"] else None,
        "identification_status": ident["status"],
        "frechet": [result["evaluation"]["band_counts"][0] / n, result["evaluation"]["band_counts"][1] / n],
        "inside_frechet": result["evaluation"]["band_counts"][0] <= result["evaluation"]["all_miss"]
                          <= result["evaluation"]["band_counts"][1],
        "provenance": result["provenance"],
    }
    if limited:
        verdict = (f"{ident['status']}: the realized marginal-only width {out['marginal_only_width']:.4f} is below "
                   f"the declared floor {out['declared_floor']}; the discrepancy is recorded and not claimed")
    elif out["ci_within_equivalence_margin"]:
        verdict = (f"EQUIVALENT within ±{margin}: the marginals quote residual risk on this pool to within the "
                   f"margin; the joint measurement changes the number by less than the SESOI {sesoi}")
    elif out["ci_excludes_zero"] and out["point_at_or_beyond_sesoi"]:
        verdict = (f"DISCREPANT: the interval excludes zero and the point discrepancy reaches the SESOI {sesoi}; "
                   f"the marginals do not quote residual risk on this pool")
    else:
        verdict = (f"UNRESOLVED: the interval neither sits inside ±{margin} nor excludes zero with a point at the "
                   f"SESOI; {'precision met' if out['precision_met'] else 'precision not met'} "
                   f"(half width {half:.4f} against {desired})")
    out["verdict"] = verdict
    (RESULTS / "analysis.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"n={n} miss={ {g: round(v, 4) for g, v in out['miss_rates'].items()} } q_obs={out['q_obs']:.4f} "
          f"q_ind={out['q_ind']:.4f} delta={out['delta']:+.4f} CI95=[{ci[0]:+.4f}, {ci[1]:+.4f}] "
          f"half={half:.4f} (desired {desired})")
    print(f"marginal-only width {out['marginal_only_width']:.4f} floor {out['declared_floor']} "
          f"-> {ident['status']}; Frechet {out['frechet']} q_obs inside {out['inside_frechet']}")
    print(verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
