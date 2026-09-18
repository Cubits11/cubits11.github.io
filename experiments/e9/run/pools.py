#!/usr/bin/env python3
"""Build E9's pools from pinned upstream files. Runs before any model loads.

    python3 experiments/e9/run/pools.py --from DIR     # DIR holds the downloaded upstream files

The harmful candidates are E8's three, from the same pinned files. The
target-benign population is the declared WildChat-1M shards reduced by the
filters protocol.json declares, and nothing else. Every file is verified by
sha256 before a row is read. The stress stratum is read in place from E3B's
freeze by draw.py.

Nothing here chooses a pool, a threshold or an item. protocol.json declares,
draw.py draws, admit.py applies the rule.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/e9/freeze"
SOURCES = FREEZE / "sources"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verified(path: Path, digest: str) -> Path:
    got = sha256(path)
    if got != digest:
        raise SystemExit(f"REFUSED: {path.name} sha256 {got[:12]}… is not the pinned {digest[:12]}…")
    return path


def candidate_rows(cand: dict, path: Path) -> list[dict]:
    """E8's reduction, unchanged: (row_index, prompt[, extras]) with the declared keep rule."""
    up = cand["upstream"]
    if up["format"] == "parquet":
        import pyarrow.parquet as pq
        raw = pq.read_table(path).to_pylist()
    elif up["format"] == "csv":
        with path.open(encoding="utf-8") as fh:
            raw = list(csv.DictReader(fh))
    else:
        raise SystemExit(f"unknown upstream format {up['format']!r}")
    keep = up.get("keep_where")
    out = []
    for i, r in enumerate(raw):
        if keep and str(r.get(keep["column"], "")).strip() != str(keep["equals"]):
            continue
        prompt = r.get(up["text_column"])
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        row = {"row_index": i, "prompt": prompt}
        for extra in up.get("extra_columns", []):
            row[extra] = r.get(extra)
        out.append(row)
    return out


def target_benign_rows(tb: dict, src: Path) -> tuple[list[dict], dict]:
    """First user turns, English, non-empty, free of every declared attack marker. Nothing more.

    The release's toxic flag is deliberately not read: protocol.json says why.
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    marks = tb["exclude_markers"]
    substrings = [m.lower() for m in marks["substrings_case_insensitive"]]
    words = [re.compile(r"\b" + re.escape(w) + r"\b") for w in marks["whole_words_case_sensitive"]]
    out, counts = [], collections.Counter()
    for f in tb["source"]["files"]:
        table = pq.read_table(verified(src / f["local_name"], f["sha256"]), columns=["conversation"])
        first = pc.list_element(table.column("conversation"), 0).combine_chunks()
        del table
        roles, langs = first.field("role").to_pylist(), first.field("language").to_pylist()
        texts = first.field("content").to_pylist()
        for i, (role, lang, text) in enumerate(zip(roles, langs, texts)):
            counts["conversations"] += 1
            if role != "user":
                counts["first turn not from the user"] += 1
            elif lang != "English":
                counts["first turn not English"] += 1
            elif not isinstance(text, str) or not text.strip():
                counts["empty first turn"] += 1
            elif any(m in text.lower() for m in substrings) or any(w.search(text) for w in words):
                counts["canonical attack marker"] += 1
            else:
                out.append({"row_index": f"{f['shard']}-{i}", "prompt": text})
    counts["kept"] = len(out)
    return out, dict(counts)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", type=Path, required=True)
    a = ap.parse_args()
    plan = json.loads((FREEZE / "protocol.json").read_text())
    SOURCES.mkdir(parents=True, exist_ok=True)
    for cand in plan["candidates"]:
        up = cand["upstream"]
        rows = candidate_rows(cand, verified(a.src / up["local_name"], up["sha256"]))
        write_csv(SOURCES / f"{cand['id']}.csv", rows, ["row_index", "prompt"] + up.get("extra_columns", []))
        print(f"{cand['id']}: {len(rows)} rows from {up['local_name']}")
    rows, counts = target_benign_rows(plan["target_benign"], a.src)
    write_csv(SOURCES / "target-benign.csv", rows, ["row_index", "prompt"])
    (SOURCES / "target-benign.counts.json").write_text(json.dumps(counts, indent=1) + "\n")
    print(f"target-benign: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
