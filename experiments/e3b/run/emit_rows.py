#!/usr/bin/env python3
"""Emit per-item observation rows as JSONL — the form the evidence ledger counts.

One row per (item, guard). Carries text_sha256, never prompt text:
experiments/e3b/freeze/LICENSE-OUTPUTS.md forbids redistributing OR-Bench text.
"""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E3 = ROOT / "experiments/e3b"
SETS = {"items_harmful": "harmful",
        "items_benign_calibration": "benign_calibration",
        "items_benign_evaluation": "benign_evaluation"}


def main() -> int:
    cfg = json.loads((E3 / "e3b_config.json").read_text())
    out = E3 / "results" / "observations.jsonl"
    n = 0
    with out.open("w") as fh:
        for setname, stratum in SETS.items():
            probs = json.loads((E3 / "results" / f"{setname}.probs.json").read_text())["guards"]
            hashes = {r["id"]: r["text_sha256"]
                      for r in csv.DictReader((E3 / "freeze" / f"{setname}.csv").open())}
            for slot, per_item in probs.items():
                t = cfg["guards"][slot]["threshold"]
                for item_id, p in per_item.items():
                    fh.write(json.dumps({
                        "experiment": "E3B", "freeze": cfg["frozen"], "seed": cfg["seed"],
                        "stratum": stratum, "item_id": item_id,
                        "text_sha256": hashes[item_id],
                        "guard": slot, "threshold": t,
                        "prob_unsafe": round(p, 6),
                        "flag": int(p >= t),
                        "miss": int(p < t) if stratum == "harmful" else None,
                        "config_sha256": cfg.get("config_sha256"),
                    }) + "\n")
                    n += 1
    print(f"wrote {out.relative_to(ROOT)}  rows={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
