#!/usr/bin/env python3
"""Joint statistics for Adversarial-Prompt-Evaluation result pickles — a prepared patch.

IBM/Adversarial-Prompt-Evaluation's ``scripts/main_evaluate.py`` derives
``data_name = args.data_location.removesuffix(".json")`` and writes one
``result_<model>_<data_name>.pickle`` per defence with ``x_test`` (prompts),
``y_test`` (1 = malicious), ``y_pred`` (1 = detected) and ``source`` (the
dataset each prompt came from), in prompt order over one shared pool. Every
published number is a marginal. This script reads two or more of those
pickles, REFUSES unless they describe the same prompts in the same order with
the same labels and sources, and prints per source: union detection,
all-miss, leave-one-out unions and exclusive coverage over the malicious
prompts, and the union flag count over the benign prompts.

    python3 contrib/ape_joint.py --data sub_sample_filtered_data.json \\
        --models protectAI_v2 lamaguard2 langkit --dir scripts

``--data`` accepts the same value you passed as ``--data_location`` (with or
without ``.json``); the ``.json`` suffix is removed exactly as the harness
removes it, so ``result_<model>_sub_sample_filtered_data.pickle`` is found.

Exit status: 0 printed; 2 REFUSED (a diagnostic names the first
misalignment or malformed field — nothing is counted); 1 usage or I/O error.

TRUST BOUNDARY: result files are Python pickles, and unpickling can execute
code embedded in the file. Run this only on result pickles the benchmark
harness wrote on a machine you trust — never on files received from an
untrusted source. (This is a property of the pickle format, not a statement
about the harness's own artifacts.)

Counting arithmetic at each defence's own decision rule as saved; not a
dependence estimate, not a ranking, not a deployed route. Offered to the
maintainers as ``scripts/main_joint_report.py``; see
distribution/dossiers/ibm-adversarial-prompt-2025.md for the exact ask.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

REQUIRED = ("x_test", "y_test", "y_pred", "source")
EXIT_REFUSED = 2


class Refused(Exception):
    """Alignment or contract failure: the only honest output is no number."""


def data_name(data: str) -> str:
    """The harness strips a trailing .json from --data_location; so do we."""
    return data.removesuffix(".json")


def result_path(directory: Path, model: str, data: str) -> Path:
    return directory / f"result_{model}_{data_name(data)}.pickle"


def load(path: Path) -> dict:
    with path.open("rb") as fh:
        return pickle.load(fh)  # trusted, harness-written files only — see the module docstring


def _binary(values, what: str, model: str) -> list[int]:
    out = []
    for v in values:
        if isinstance(v, bool):
            out.append(int(v))
        elif isinstance(v, int) and v in (0, 1):
            out.append(v)
        else:
            raise Refused(f"{model}: {what} contains a non-binary value {v!r}")
    return out


def validate(models: list[str], results: dict[str, dict]) -> tuple[list[str], list[int], list[str], dict[str, list[int]]]:
    """Enforce the input contract; return the shared prompts, labels, sources and per-model predictions."""
    if len(models) < 2:
        raise Refused("a joint statistic needs at least two models")
    if len(set(models)) != len(models):
        raise Refused("model names must be unique — the same file counted twice is not two defences")
    ref = models[0]
    for m in models:
        r = results[m]
        if not isinstance(r, dict):
            raise Refused(f"{m}: result file is not a mapping")
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            raise Refused(f"{m}: result lacks {', '.join(missing)}")
        n = len(r["x_test"])
        if len(r["y_test"]) != n or len(r["source"]) != n:
            raise Refused(f"{m}: x_test ({n}), y_test ({len(r['y_test'])}) and source ({len(r['source'])}) lengths differ")
        if len(r["y_pred"]) != n:
            raise Refused(f"{m}: y_pred has {len(r['y_pred'])} entries for {n} prompts")
    x_ref, src_ref = list(results[ref]["x_test"]), list(results[ref]["source"])
    y_ref = _binary(results[ref]["y_test"], "y_test", ref)
    preds: dict[str, list[int]] = {}
    for m in models:
        r = results[m]
        if list(r["x_test"]) != x_ref:
            raise Refused(f"{m}: prompts differ from {ref} (order or content) — refusing to align")
        if _binary(r["y_test"], "y_test", m) != y_ref:
            raise Refused(f"{m}: labels differ from {ref} — refusing to align")
        if list(r["source"]) != src_ref:
            raise Refused(f"{m}: sources differ from {ref} — refusing to align")
        preds[m] = _binary(r["y_pred"], "y_pred", m)
    return x_ref, y_ref, src_ref, preds


def joint(models: list[str], results: dict[str, dict]) -> dict:
    _, y, src, pred = validate(models, results)
    out: dict[str, dict] = {}
    for source in sorted(set(src)):
        idx = [i for i, s in enumerate(src) if s == source]
        pos = [i for i in idx if y[i] == 1]
        neg = [i for i in idx if y[i] == 0]
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="the --data_location value used when evaluating (with or without .json)")
    ap.add_argument("--models", nargs="+", required=True, help="model names as used in result_<model>_<data>.pickle")
    ap.add_argument("--dir", type=Path, default=Path("."), help="directory holding the result pickles (harness-written, trusted)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        results = {}
        for m in args.models:
            p = result_path(args.dir, m, args.data)
            if not p.exists():
                print(f"ERROR  {p} not found (expected result_<model>_{data_name(args.data)}.pickle)", file=sys.stderr)
                return 1
            results[m] = load(p)
        out = joint(args.models, results)
    except Refused as exc:
        print(f"REFUSED  {exc} — no joint statistic is printed (exit {EXIT_REFUSED})", file=sys.stderr)
        return EXIT_REFUSED
    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    print(f"joint statistics · {data_name(args.data)} · {len(args.models)} defences on identical prompts · at each defence's saved decision rule")
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
