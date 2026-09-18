#!/usr/bin/env python3
"""E9 analysis: E8's, read against E9's contract, freeze and admission record.

    python3 experiments/e9/run/analyze.py

Reads results/observations.jsonl and results/result.json as the runner wrote
them, the contract for the SESOI, margin, desired half width and floor,
freeze.json for the bootstrap seed and B, and protocol.json's results for the
admission thresholds. Writes results/analysis.json. It adds no threshold and no
cell: every quantity is a function of the stored per-item score vectors, the
contract and the seed.

One assertion E8 did not need: the thresholds the runner recomputed from the
calibration set equal the thresholds admission used. A difference would mean
the operating point moved after a width was seen, and the analysis stops.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E9 = ROOT / "experiments/e9"
RESULTS = E9 / "results"


def delta_of(rows: list[dict], guards: list[str]) -> Fraction:
    n = len(rows)
    all_miss = sum(all(r["miss"][g] for g in guards) for r in rows)
    plug = Fraction(1)
    for g in guards:
        plug *= Fraction(sum(r["miss"][g] for r in rows), n)
    return Fraction(all_miss, n) - plug


def main() -> int:
    contract = json.loads((E9 / "contract.json").read_text())
    freeze = json.loads((E9 / "freeze" / "freeze.json").read_text())
    admission = json.loads((E9 / "freeze" / "protocol.json").read_text())["results"]
    result = json.loads((RESULTS / "result.json").read_text())
    rows = [json.loads(line) for line in (RESULTS / "observations.jsonl").read_text().splitlines()]
    if result["thresholds"] != admission["thresholds"]:
        print(f"STOP: measurement thresholds {result['thresholds']} differ from admission thresholds "
              f"{admission['thresholds']}; the operating point moved after a width was seen")
        return 1
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
    ev = result["evaluation"]
    out = {
        "experiment": "E9", "contract_id": contract["id"], "n": n, "guards": guards,
        "admitted_pool": admission["admitted"], "thresholds": result["thresholds"],
        "thresholds_equal_admission": True,
        "miss_rates": {g: ev["miss_counts"][g] / n for g in guards},
        "q_obs": ev["all_miss"] / n,
        "q_ind": float(Fraction(ev["plug_in_all_miss_count"]) / n),
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
        "frechet": [ev["band_counts"][0] / n, ev["band_counts"][1] / n],
        "inside_frechet": ev["band_counts"][0] <= ev["all_miss"] <= ev["band_counts"][1],
        "stress": admission.get("stress"),
        "hypothesis": admission["hypothesis"],
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
    print(f"n={n} pool={out['admitted_pool']} miss={ {g: round(v, 4) for g, v in out['miss_rates'].items()} } "
          f"q_obs={out['q_obs']:.4f} q_ind={out['q_ind']:.4f} delta={out['delta']:+.4f} "
          f"CI95=[{ci[0]:+.4f}, {ci[1]:+.4f}] half={half:.4f} (desired {desired})")
    print(f"marginal-only width {out['marginal_only_width']:.4f} floor {out['declared_floor']} "
          f"-> {ident['status']}; Frechet {out['frechet']} q_obs inside {out['inside_frechet']}")
    print(verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
