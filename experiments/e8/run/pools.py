#!/usr/bin/env python3
"""Build E8's candidate harmful pools from pinned upstream files. Runs before any model loads.

Each candidate is one upstream file at one revision, verified by sha256 before
a row is read, reduced to (row_index, prompt[, extra]) and written under
experiments/e8/freeze/sources/. The candidates, their order and the reason
each is or is not eligible are declared in experiments/e8/freeze/scouting.json
before any candidate is scored; this file only materializes them.

    python3 experiments/e8/run/pools.py --from DIR     # DIR holds the downloaded upstream files

Nothing here chooses a pool. The choice is scouting.json's rule applied by
scout.py to scouting slices that are burned for evaluation once read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/e8/freeze"
SOURCES = FREEZE / "sources"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_of(candidate: dict, path: Path) -> list[dict]:
    fmt = candidate["upstream"]["format"]
    if fmt == "parquet":
        import pyarrow.parquet as pq
        raw = pq.read_table(path).to_pylist()
    elif fmt == "csv":
        with path.open(encoding="utf-8") as fh:
            raw = list(csv.DictReader(fh))
    else:
        raise SystemExit(f"unknown upstream format {fmt!r}")
    text = candidate["upstream"]["text_column"]
    keep = candidate["upstream"].get("keep_where")
    out = []
    for i, r in enumerate(raw):
        if keep and str(r.get(keep["column"], "")).strip() != str(keep["equals"]):
            continue
        prompt = r.get(text)
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        row = {"row_index": i, "prompt": prompt}
        for extra in candidate["upstream"].get("extra_columns", []):
            row[extra] = r.get(extra)
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", type=Path, required=True)
    a = ap.parse_args()
    plan = json.loads((FREEZE / "scouting.json").read_text())
    SOURCES.mkdir(parents=True, exist_ok=True)
    for cand in plan["candidates"]:
        up = cand["upstream"]
        path = a.src / up["local_name"]
        digest = sha256(path)
        if digest != up["sha256"]:
            print(f"REFUSED: {path.name} sha256 {digest[:12]}… is not the pinned {up['sha256'][:12]}…")
            return 1
        rows = rows_of(cand, path)
        out = SOURCES / f"{cand['id']}.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            fields = ["row_index", "prompt"] + up.get("extra_columns", [])
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"{cand['id']}: {len(rows)} rows from {path.name} ({digest[:12]}…) -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
