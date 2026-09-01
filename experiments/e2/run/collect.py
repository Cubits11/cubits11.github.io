#!/usr/bin/env python3
"""E2 pilot collection runner — freeze-bound, synthetic-testable.

Emits one JSONL row per (item, guard, replicate) in the shape of the
E2 measurement contract's Layer F. Real mode scores the frozen benign
EVALUATION half and the harmful set at the thresholds frozen in
e2_config.json — only on the authorized box (the adapters refuse
elsewhere), only after calibration. Synthetic mode exercises the same
row machinery end to end with seeded fake scores and seeded missing
cells, on synthetic item ids, writing outside the repository.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE = HERE.parent / "freeze"
SEED = "MC-E2-PILOT-V1-FREEZE-2026-09-01"
GUARDS = ("lg4", "lg3", "sg2b")
NORMALIZER = "h.miss.v1"
MISS_CODES = ("timeout", "execution_error", "unparseable_output")


def h01(*parts: str) -> float:
    d = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return int(d[:12], 16) / float(16 ** 12)


def read_items(name: str, stratum: str) -> list[dict]:
    with open(FREEZE / name, newline="") as fh:
        return [{"id": r["id"], "stratum": stratum}
                for r in csv.DictReader(fh)]


def emit_row(fh, *, run_id, item, guard, replicate, score, threshold,
             status, code, synthetic):
    flagged = None if score is None else bool(score >= threshold)
    if item["stratum"].startswith("harmful"):
        normalized = None if flagged is None else int(not flagged)  # miss
    else:
        normalized = None if flagged is None else int(flagged)      # flag
    row = {
        "schema_version": "cc.e2_observation_row.v1",
        "study_id": "MC-E2-PILOT-V1", "run_id": run_id,
        "item_id": item["id"],
        "item_source": "SYNTHETIC" if synthetic else "per freeze sources.json",
        "guardrail_id": guard,
        "guardrail_version": "SYNTHETIC" if synthetic
        else "pinned; see freeze sources.json + LG4_CONFIG.md",
        "configuration_hash": "SYNTHETIC" if synthetic else "e2_config.json",
        "raw_outcome": None if score is None else round(score, 10),
        "raw_outcome_detail": "score" if score is not None else None,
        "normalized_outcome": normalized,
        "normalizer_version": NORMALIZER,
        "stratum": item["stratum"],
        "execution_status": status, "missingness_code": code,
        "predeclared_exclusion": False,
        "replicate_id": replicate,
        "reference_label": ("harmful" if item["stratum"].startswith("harmful")
                            else "benign"),
        "reference_label_uncertainty": "none-recorded (declared limitation)",
        "synthetic": synthetic,
    }
    fh.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--config", help="e2_config json (real mode)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out).resolve()
    repo = HERE.parent.parent.parent
    if repo in out.parents or out == repo:
        sys.exit("refusing to write outputs inside the repository")
    out.mkdir(parents=True, exist_ok=True)

    if args.synthetic:
        items = ([{"id": f"synb-{i:04d}", "stratum": "benign_eval"}
                  for i in range(800)] +
                 [{"id": f"synh-{i:04d}", "stratum": "harmful"}
                  for i in range(520)])
        thresholds = {g: 0.95 for g in GUARDS}
        run_id, path = "SYNTHETIC-SHAKEOUT", out / "rows.SYNTHETIC.jsonl"
        with open(path, "w") as fh:
            for item in items:
                for g in GUARDS:
                    u = h01(SEED, "collect", g, item["id"])
                    if u < 0.01:  # seeded 1% missingness, coded
                        code = MISS_CODES[int(u * 1000) % len(MISS_CODES)]
                        emit_row(fh, run_id=run_id, item=item, guard=g,
                                 replicate=1, score=None,
                                 threshold=thresholds[g],
                                 status="failed", code=code, synthetic=True)
                        continue
                    base = h01(SEED, "difficulty", item["id"])
                    score = min(1.0, max(0.0, 0.55 * base + 0.45 * h01(
                        SEED, "noise", g, item["id"])))
                    if item["stratum"] == "harmful":
                        score = min(1.0, score + 0.35)
                    emit_row(fh, run_id=run_id, item=item, guard=g,
                             replicate=1, score=score,
                             threshold=thresholds[g],
                             status="observed", code="observed",
                             synthetic=True)
        print(f"ok    synthetic collection: {len(items)} items x "
              f"{len(GUARDS)} guards -> {path.name} (shared-difficulty "
              f"generator, seeded 1% coded missingness)")
        return 0

    if not args.config:
        sys.exit("real mode needs --config from a frozen calibration")
    sys.path.insert(0, str(HERE))
    from adapters import SCORERS  # gated: refuses off the authorized box
    cfg = json.loads(Path(args.config).read_text())
    items = (read_items("items_benign_evaluation.csv", "benign_eval") +
             read_items("items_harmful.csv", "harmful"))
    print(f"real collection: {len(items)} frozen items; adapters gated")
    run_id = "E2-PILOT-V1-RUN-1"
    with open(out / "rows.jsonl", "w") as fh:
        for item in items:
            for g in GUARDS:
                score = SCORERS[g](item["id"])  # raises until on-box
                emit_row(fh, run_id=run_id, item=item, guard=g, replicate=1,
                         score=score, threshold=cfg["results"][g]["threshold"],
                         status="observed", code="observed", synthetic=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
