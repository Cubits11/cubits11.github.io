#!/usr/bin/env python3
"""Re-derive frozen item TEXTS from the pinned public sources.

The freeze commits no prompt text — only ids, row indices, and
text_sha256. Real calibration and collection therefore need this module:
it fetches the pinned AdvBench csv and the pinned or-bench-80k parquet,
rebuilds row_index -> text, and HARD-FAILS unless every rebuilt text
hashes to the frozen text_sha256. A text that does not verify never
reaches a guard.

This module reads item text for verification and scoring input only; it
computes no outcome and loads no model. Both sources are ungated, so the
verification pass runs on any host (the benign side needs pyarrow).
Found and fixed 2026-09-01: before this module existed, calibrate.py and
collect.py real modes passed item IDS to the scorers — a defect caught
by adversarial self-review, not by a burned run.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE = HERE.parent / "freeze"

ADV_URL = ("https://raw.githubusercontent.com/llm-attacks/llm-attacks/"
           "098262edf85f807224e70ecd87b9d83716bf6b73/"
           "data/advbench/harmful_behaviors.csv")
ORB_PARQUET = ("https://huggingface.co/api/datasets/bench-llm/or-bench/"
               "parquet/or-bench-80k/train")

H = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mc-e2-items"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _frozen(name: str) -> dict[str, tuple[int, str]]:
    with open(FREEZE / name, newline="") as fh:
        return {r["id"]: (int(r["row_index"]), r["text_sha256"])
                for r in csv.DictReader(fh)}


def _verify(frozen: dict, texts: dict[int, str], label: str) -> dict[str, str]:
    out, bad = {}, 0
    for iid, (idx, want) in frozen.items():
        text = texts.get(idx)
        if text is None or H(text.encode()) != want:
            bad += 1
            continue
        out[iid] = text
    if bad:
        sys.exit(f"items_text: {bad} {label} item(s) failed hash "
                 f"verification against the freeze — refusing everything")
    print(f"ok    {label}: {len(out)} texts re-derived and hash-verified")
    return out


def harmful_texts() -> dict[str, str]:
    blob = _get(ADV_URL)
    src = json.loads((FREEZE / "sources.json").read_text())
    if H(blob) != src["harmful"]["file_sha256"]:
        sys.exit("items_text: AdvBench bytes do not match the frozen "
                 "file_sha256 — refusing")
    rows = list(csv.DictReader(io.StringIO(blob.decode("utf-8"))))
    return _verify(_frozen("items_harmful.csv"),
                   {i: r["goal"] for i, r in enumerate(rows)}, "harmful")


def _benign_rows() -> dict[int, str]:
    import pyarrow.parquet as pq  # deliberate: only the benign path needs it
    src = json.loads((FREEZE / "sources.json").read_text())
    texts: dict[int, str] = {}
    base = 0
    for shard in src["benign"]["parquet"]:
        blob = _get(f"{ORB_PARQUET}/{shard['filename']}")
        if H(blob) != shard["sha256"]:
            sys.exit(f"items_text: parquet shard {shard['filename']} does "
                     "not match the frozen sha256 — refusing")
        col = pq.read_table(io.BytesIO(blob)).column("prompt").to_pylist()
        for i, t in enumerate(col):
            texts[base + i] = t
        base += len(col)
    return texts


def benign_texts(which: str) -> dict[str, str]:
    name = {"calibration": "items_benign_calibration.csv",
            "evaluation": "items_benign_evaluation.csv"}[which]
    return _verify(_frozen(name), _benign_rows(), f"benign_{which}")


def main() -> int:
    harmful_texts()
    rows = _benign_rows()
    _verify(_frozen("items_benign_calibration.csv"), rows,
            "benign_calibration")
    _verify(_frozen("items_benign_evaluation.csv"), rows,
            "benign_evaluation")
    print("Item-text verification complete: every frozen text_sha256 is "
          "re-derivable from the pinned public sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
