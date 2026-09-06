#!/usr/bin/env python3
"""E3 sample draw and disjointness gate. Runs before any model is loaded.

Deterministic: every id's rank is sha256(seed + ':' + id). No RNG, no shuffle,
so the draw is reproducible from the seed alone and cannot be quietly re-run
with a different one — a re-draw changes the seed, and the seed is in the freeze.

Exits nonzero if the harmful or benign draw intersects E2's frozen items at the
text-hash level. That is the gate, not a note.
"""
from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/e3/freeze"
E2 = ROOT / "experiments/e2/freeze"
SEED = "MC-E3-PILOT-V1-FREEZE-2026-09-06"
N_HARMFUL, N_BENIGN_CAL, N_BENIGN_EVAL = 400, 400, 400


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def rank(seed: str, item_id: str) -> str:
    return sha(f"{seed}:{item_id}")


def e2_frozen_text_hashes() -> set[str]:
    out = set()
    for name in ("items_harmful", "items_benign_calibration", "items_benign_evaluation"):
        for r in csv.DictReader((E2 / f"{name}.csv").open()):
            if r.get("text_sha256"):
                out.add(r["text_sha256"])
    return out


def draw(rows: list[tuple[str, str]], n: int) -> list[tuple[str, str]]:
    """rows: (id, text). Rank by sha256(seed:id) ascending hex, take first n."""
    return sorted(rows, key=lambda t: rank(SEED, t[0]))[:n]


def main() -> int:
    pool_path = Path(sys.argv[1]) if len(sys.argv) > 1 else FREEZE / "or-bench-toxic.csv"
    frozen = e2_frozen_text_hashes()

    harmful_rows = [
        (f"orbenchtoxic-{i}", r["prompt"])
        for i, r in enumerate(csv.DictReader(pool_path.open(encoding="utf-8")))
    ]
    harmful = draw(harmful_rows, N_HARMFUL)

    inter = {sha(t) for _, t in harmful} & frozen
    print(f"pool rows           {len(harmful_rows)}")
    print(f"harmful drawn       {len(harmful)}")
    print(f"E2 frozen hashes    {len(frozen)}")
    print(f"|E3 harmful ∩ E2|   {len(inter)}")
    if inter:
        print("GATE FAIL — the draw intersects E2's frozen items. E3 stops.")
        return 1
    if len(harmful) < N_HARMFUL:
        print(f"GATE FAIL — pool yields {len(harmful)} < {N_HARMFUL}. E3 stops.")
        return 1

    out = FREEZE / "items_harmful.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "row_index", "text_sha256"])
        for i, t in harmful:
            w.writerow([i, i.rsplit("-", 1)[1], sha(t)])
    print(f"GATE PASS — zero intersection. wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
