#!/usr/bin/env python3
"""Joint statistics for Adversarial-Prompt-Evaluation result pickles — a prepared patch.

IBM/Adversarial-Prompt-Evaluation's ``scripts/main_evaluate.py`` writes one
``result_<model>_<data>.pickle`` per defence with ``y_test`` (1 = malicious),
``y_pred`` (1 = detected) and ``source`` (the dataset each prompt came from),
in prompt order over one shared pool. Every published number is a marginal.
This script reads two or more of those pickles for one data file, checks that
they describe the same prompts in the same order, and prints per source:
union detection, all-miss, leave-one-out unions and exclusive coverage over
the malicious prompts, and the union flag count over the benign prompts.

    python3 contrib/ape_joint.py --data sub_sample_filtered_data.json \\
        --models protectAI_v2 lamaguard2 langkit --dir scripts

Standard library only (pickle, json). Counting arithmetic at each defence's
own decision rule as saved; not a dependence estimate, not a ranking, not a
deployed route. Refuses (exit 2) when the prompt lists differ.

Offered to the maintainers as ``scripts/main_joint_report.py``; see
distribution/dossiers/ibm-adversarial-prompt-2025.md for the exact ask.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path


def load(path: Path) -> dict:
    with path.open("rb") as fh:
        return pickle.load(fh)


def joint(models: list[str], results: dict[str, dict]) -> dict:
    ref = results[models[0]]
    x_ref, y_ref, src_ref = list(ref["x_test"]), list(ref["y_test"]), list(ref["source"])
    for m in models[1:]:
        r = results[m]
        if list(r["x_test"]) != x_ref or list(r["y_test"]) != y_ref or list(r["source"]) != src_ref:
            raise SystemExit(f"UNKNOWN  {m}: prompts, labels, or sources differ from {models[0]} — refusing to align (exit 2)")
    out: dict[str, dict] = {}
    for source in sorted(set(src_ref)):
        idx = [i for i, s in enumerate(src_ref) if s == source]
        pos = [i for i in idx if int(y_ref[i]) == 1]
        neg = [i for i in idx if int(y_ref[i]) == 0]
        pred = {m: [int(v) for v in results[m]["y_pred"]] for m in models}
        catch = {m: sum(pred[m][i] for i in pos) for m in models}
        union = sum(any(pred[m][i] for m in models) for i in pos)
        loo = {m: sum(any(pred[o][i] for o in models if o != m) for i in pos) for m in models}
        out[source] = {
            "n_positive": len(pos), "n_negative": len(neg), "catch": catch, "union": union,
            "all_miss": len(pos) - union, "leave_one_out_union": loo,
            "exclusive_coverage": {m: union - loo[m] for m in models},
            "benign_flags": {m: sum(pred[m][i] for i in neg) for m in models},
            "benign_union": sum(any(pred[m][i] for m in models) for i in neg),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="the data_location name used when evaluating, e.g. sub_sample_filtered_data.json")
    ap.add_argument("--models", nargs="+", required=True, help="model names as used in result_<model>_<data>.pickle")
    ap.add_argument("--dir", type=Path, default=Path("."), help="directory holding the result pickles")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = {m: load(args.dir / f"result_{m}_{args.data}.pickle") for m in args.models}
    out = joint(args.models, results)
    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    print(f"joint statistics · {args.data} · {len(args.models)} defences on identical prompts · at each defence's saved decision rule")
    for source, r in out.items():
        n, nb = r["n_positive"], r["n_negative"]
        print(f"[{source}]  {n} malicious / {nb} benign")
        for m in args.models:
            print(f"  {m:24s} catch {r['catch'][m]:5d}/{n}   without it {r['leave_one_out_union'][m]:5d}/{n}   exclusive {r['exclusive_coverage'][m]:4d}   benign flags {r['benign_flags'][m]:5d}/{nb}")
        print(f"  {'UNION (any defence)':24s} catch {r['union']:5d}/{n}   all-miss {r['all_miss']}/{n}   benign union flags {r['benign_union']}/{nb}")
    print("  static OR over saved per-prompt predictions: not a deployed route, not a dependence estimate, not a ranking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
