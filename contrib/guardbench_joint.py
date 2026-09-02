#!/usr/bin/env python3
"""Joint statistics for GuardBench result files — a prepared patch, standard library only.

GuardBench (AmenRa/guardbench) writes one file per model per dataset,
``results/<dataset>/<model>.json``, mapping each item id to an unsafe
probability; its ``evaluate`` thresholds at 0.5 and its datasets carry a
boolean ``label`` per item (True = unsafe). Every published number is a
marginal. This script reads two or more of those files for one dataset,
aligns them on item id, and prints what the marginals cannot: the union
catch, the all-miss count, each model's leave-one-out union and exclusive
coverage, and the benign union-flag count — over one denominator, with the
threshold stated.

    python3 contrib/guardbench_joint.py --results results --dataset harmbench_behaviors \\
        --labels path/to/harmbench_behaviors/test.jsonl --models "Llama Guard" "Llama Guard 2"

Counting arithmetic only, at the threshold you pass. It does not estimate
dependence, does not certify a stack, and refuses (exit 2) when the models'
item ids are not identical — a joint statistic over misaligned items is not
a number.

Offered to the GuardBench maintainers as ``scripts/joint_report.py``; see
distribution/dossiers/guardbench-2024.md for the exact ask.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path


def read_labels(path: Path) -> dict[str, bool]:
    labels: dict[str, bool] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labels[str(row["id"])] = bool(row["label"])
    return labels


def joint(models: list[str], preds: dict[str, dict[str, float]], labels: dict[str, bool],
          threshold: float) -> dict:
    ids = sorted(labels)
    for m in models:
        if set(preds[m]) != set(ids):
            raise SystemExit(f"UNKNOWN  {m}: item ids differ from the dataset's — refusing to align by position (exit 2)")
    pos = [i for i in ids if labels[i]]
    neg = [i for i in ids if not labels[i]]
    flag = {m: {i: preds[m][i] > threshold for i in ids} for m in models}
    catch = {m: sum(flag[m][i] for i in pos) for m in models}
    union = sum(any(flag[m][i] for m in models) for i in pos)
    all_miss = len(pos) - union
    loo = {m: sum(any(flag[o][i] for o in models if o != m) for i in pos) for m in models}
    exclusive = {m: union - loo[m] for m in models}
    benign_flags = {m: sum(flag[m][i] for i in neg) for m in models}
    benign_union = sum(any(flag[m][i] for m in models) for i in neg)
    pairs = {f"{a} ∩ {b}": sum(flag[a][i] and flag[b][i] for i in pos) for a, b in combinations(models, 2)}
    return {"n_positive": len(pos), "n_negative": len(neg), "threshold": threshold,
            "catch": catch, "union": union, "all_miss": all_miss, "leave_one_out_union": loo,
            "exclusive_coverage": exclusive, "pairwise_catch_intersection": pairs,
            "benign_flags": benign_flags, "benign_union": benign_union}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--labels", type=Path, required=True, help="the dataset's test.jsonl with id and label")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    labels = read_labels(args.labels)
    preds = {m: {str(k): float(v) for k, v in json.loads((args.results / args.dataset / f"{m}.json").read_text()).items()}
             for m in args.models}
    r = joint(args.models, preds, labels, args.threshold)
    if args.json:
        print(json.dumps(r, indent=1))
        return 0
    n, nb = r["n_positive"], r["n_negative"]
    print(f"joint statistics · {args.dataset} · threshold {args.threshold} · {n} positive / {nb} negative items · same ids for every model")
    for m in args.models:
        print(f"  {m:32s} catch {r['catch'][m]:5d}/{n}   without it {r['leave_one_out_union'][m]:5d}/{n}   exclusive {r['exclusive_coverage'][m]:4d}   benign flags {r['benign_flags'][m]:5d}/{nb}")
    print(f"  {'UNION (any model)':32s} catch {r['union']:5d}/{n}   all-miss {r['all_miss']}/{n}   benign union flags {r['benign_union']}/{nb}")
    for k, v in r["pairwise_catch_intersection"].items():
        print(f"  {k:32s} both catch {v}/{n}")
    print("  static OR over released per-item outcomes at one threshold: not a deployed route, not a dependence estimate, not a ranking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
