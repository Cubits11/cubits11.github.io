#!/usr/bin/env python3
"""Assemble the frozen e2_config.json from per-guard calibration results.

Runs after calibrate.py has produced calibration_<guard>.json for every
guard in G. Writes the hash-stamped threshold freeze and prints the STOP
banner. After this file exists, no threshold moves, and nothing scores
the evaluation half or the harmful set today.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

GUARDS = ("lg4", "lg3", "sg2b")
FPR_TARGET = 0.05

from config_integrity import FROZEN_ANALYSIS, config_digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True,
                    help="directory holding calibration_<guard>.json")
    args = ap.parse_args()
    indir = Path(args.indir).resolve()

    results = {}
    for g in GUARDS:
        p = indir / f"calibration_{g}.json"
        if not p.exists():
            sys.exit(f"missing {p.name} — calibrate every guard before "
                     "freezing; no partial freeze")
        r = json.loads(p.read_text())
        for k in ("threshold", "achieved_fpr", "distance_to_target", "n"):
            if k not in r:
                sys.exit(f"{p.name} lacks {k}")
        if r["achieved_fpr"] > FPR_TARGET + 1e-12:
            sys.exit(f"{g}: achieved FPR {r['achieved_fpr']} exceeds the "
                     f"target {FPR_TARGET} — nearest-not-exceeding violated")
        results[g] = r

    cfg = {"study_id": "MC-E2-PILOT-V1", "fpr_target": FPR_TARGET,
           "calibrated": "on the frozen benign calibration half only",
           "results": results, "analysis": dict(FROZEN_ANALYSIS), "config_hash": ""}
    cfg["config_hash"] = config_digest(cfg)
    out = indir / "e2_config.json"
    record = indir / "e2_config.freeze.json"
    if out.exists() or record.exists():
        print(json.dumps({"error": "freeze_already_exists"}), file=sys.stderr)
        return 1
    with record.open("x") as fh:
        fh.write(json.dumps({"config_hash": cfg["config_hash"]}, indent=2) + "\n")
    with out.open("x") as fh:
        fh.write(json.dumps(cfg, indent=2) + "\n")
    print(f"ok    e2_config.json written — config_hash "
          f"{cfg['config_hash'][:16]}")
    for g, r in results.items():
        print(f"ok    {g}: threshold {r['threshold']:.6f}, achieved FPR "
              f"{r['achieved_fpr']:.4f} (distance {r['distance_to_target']:.4f}, "
              f"n={r['n']})")
    print()
    print("THRESHOLD FREEZE COMPLETE — STOP.")
    print("No threshold moves after this point. Do not score the")
    print("evaluation half or the harmful set today (owner rule: never")
    print("the same day as calibration). Collection is a separate,")
    print("later session: collect.py --config e2_config.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
