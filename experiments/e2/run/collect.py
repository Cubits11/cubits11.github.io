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
from datetime import datetime, timezone
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE = HERE.parent / "freeze"
from config_integrity import (ConfigError, FROZEN_ANALYSIS, load_config,
                              synthetic_config)

SEED = FROZEN_ANALYSIS["SEED"]
GUARDS = ("lg4", "lg3", "sg2b")
NORMALIZER = "h.miss.v1"
MISS_CODES = ("timeout", "execution_error", "unparseable_output")
from row_schema import RowValidationError, validate_row


def h01(*parts: str) -> float:
    d = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return int(d[:12], 16) / float(16 ** 12)


def read_items(name: str, stratum: str) -> list[dict]:
    with open(FREEZE / name, newline="") as fh:
        return [{"id": r["id"], "stratum": stratum,
                 "item_hash": r["text_sha256"]}
                for r in csv.DictReader(fh)]


def emit_row(fh, *, run_id, item, guard, replicate, score, threshold,
             status, code, synthetic, configuration_hash=None):
    if configuration_hash is None:
        if not synthetic:
            raise RowValidationError(json.dumps({"error": "row_conformance",
                "violations": ["configuration_hash_required"]}))
        configuration_hash = synthetic_config()["config_hash"]
    item_hash = item.get("item_hash")
    raw_input_hash = item.get("raw_input_hash")
    if synthetic:
        item_hash = item_hash or hashlib.sha256(item["id"].encode()).hexdigest()
        raw_input_hash = raw_input_hash or item_hash
    if (not item_hash or not raw_input_hash or
            (not synthetic and score is not None and not item.get("raw_output_hash"))):
        raise RowValidationError(json.dumps({"error": "row_conformance",
            "violations": ["real observation requires item_hash, raw_input_hash and observed raw_output_hash"]}))
    if score is not None and (type(score) not in (int, float) or not math.isfinite(score)):
        raise RowValidationError(json.dumps({"error": "row_conformance",
            "violations": ["score must be a finite number or null"]}))
    flagged = None if score is None else bool(score >= threshold)
    if item["stratum"].startswith("harmful"):
        normalized = None if flagged is None else int(not flagged)  # miss
    else:
        normalized = None if flagged is None else int(flagged)      # flag
    row = {
        "schema_version": "cc.e2_observation_row.v1",
        "study_id": "MC-E2-PILOT-V1", "run_id": run_id,
        "item_id": item["id"],
        "item_source": "SYNTHETIC" if synthetic else (
            "AdvBench" if item["stratum"].startswith("harmful") else "OR-Bench"),
        "item_source_version": "SYNTHETIC" if synthetic else (
            "098262ed" if item["stratum"].startswith("harmful") else "e36d8b80"),
        "item_hash": item_hash,
        "raw_input_hash": raw_input_hash,
        "policy_version": "SYNTHETIC" if synthetic else "unknown",
        "shared_dependency_group": ("llama-guard-lineage" if guard in ("lg4", "lg3") else None),
        "guardrail_id": guard,
        "guardrail_version": "SYNTHETIC" if synthetic
        else {"lg4": "87acb4b9", "lg3": "7327bd9f", "sg2b": "d1dffc9c"}.get(guard, "unknown"),
        "configuration_hash": configuration_hash,
        "raw_outcome": None if score is None else ("hard_block" if flagged else "allow"),
        "raw_output_hash": None if score is None else item.get("raw_output_hash",
            hashlib.sha256(json.dumps(score, allow_nan=False).encode()).hexdigest()),
        "raw_outcome_detail": {"score": score, "threshold": threshold,
                               "synthetic": synthetic},
        "normalized_outcome": normalized,
        "normalizer_version": NORMALIZER,
        "stratum": item["stratum"],
        "execution_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "execution_status": ("success" if status == "observed" else
                             ("timeout" if code == "timeout" else "error")
                             if status == "failed" else status),
        "missingness_code": code,
        "predeclared_exclusion": False,
        "replicate_id": replicate,
        "reference_label": int(item["stratum"].startswith("harmful")),
        "reference_label_uncertainty": None,
    }
    validate_row(row)
    fh.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--config", help="e2_config json (real mode)")
    ap.add_argument("--freeze-record", help="independently retained threshold-freeze record")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cfg = None
    if args.config:
        try:
            cfg = load_config(args.config, args.freeze_record)
        except ConfigError as exc:
            print(json.dumps({"error": "configuration_integrity", "reason": str(exc)}),
                  file=sys.stderr)
            return 1
    elif not args.synthetic:
        print(json.dumps({"error": "configuration_integrity",
                          "reason": "config_required"}), file=sys.stderr)
        return 1

    if args.synthetic and cfg is None:
        cfg = synthetic_config()

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
        thresholds = {g: cfg["results"][g]["threshold"] for g in GUARDS}
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
                                 status="failed", code=code, synthetic=True,
                                 configuration_hash=cfg["config_hash"])
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
                             synthetic=True, configuration_hash=cfg["config_hash"])
        print(f"ok    synthetic collection: {len(items)} items x "
              f"{len(GUARDS)} guards -> {path.name} (shared-difficulty "
              f"generator, seeded 1% coded missingness)")
        return 0

    if not args.config:
        sys.exit("real mode needs --config from a frozen calibration")
    sys.path.insert(0, str(HERE))
    from adapters import SCORERS, OBSERVATIONS  # gated: refuses off the authorized box
    from items_text import benign_texts, harmful_texts
    assert cfg is not None
    texts = {**benign_texts("evaluation"), **harmful_texts()}
    items = (read_items("items_benign_evaluation.csv", "benign_eval") +
             read_items("items_harmful.csv", "harmful"))
    if {i["id"] for i in items} != set(texts):
        sys.exit("frozen ids and verified texts disagree; refusing")
    print(f"real collection: {len(items)} frozen, hash-verified items")
    run_id = "E2-PILOT-V1-RUN-1"
    with open(out / "rows.jsonl", "w") as fh:
        for item in items:
            for g in GUARDS:
                OBSERVATIONS.pop(g, None)
                score = SCORERS[g](texts[item["id"]])  # box-gated
                observation = OBSERVATIONS.get(g)
                if not observation:
                    raise RowValidationError(json.dumps({"error": "row_conformance",
                        "violations": [f"{g}: scorer did not preserve raw observation hashes"]}))
                emit_item = dict(item, **observation)
                emit_row(fh, run_id=run_id, item=emit_item, guard=g, replicate=1,
                         score=score, threshold=cfg["results"][g]["threshold"],
                         status="observed", code="observed", synthetic=False,
                         configuration_hash=cfg["config_hash"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RowValidationError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
