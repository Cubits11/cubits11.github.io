#!/usr/bin/env python3
"""E9 runner: E8's runner, unchanged in logic, carrying E9's identity.

Every claim-critical choice comes from a validated contract.

This is step S3 of research/DIRECTION.yaml. Correction C1 says no claim-critical
choice may appear as an independently implemented literal inside the runner when
the frozen contract can supply it. So this file holds no comparator, no
threshold direction, no false-positive budget and no exclusion policy. It reads
them from a contract that research/contracts/validate_contract.py has accepted,
and it refuses a contract that validation rejects or that is not frozen.

What the runner takes and gives:

    python3 experiments/e9/run/runner.py --contract CONTRACT.json --scores SCORES.json --out DIR

SCORES.json is the atomic per-item score vector of correction C3, one number per
guard per item, keyed by the pool names the contract declares:

    {"guards": ["G1", "G2"],
     "pools": {"per_judge_benign":     {"item-1": {"G1": 0.01, "G2": 0.20}, ...},
               "pair_shared_harmful": {"item-9": {"G1": 0.70, "G2": 0.04}, ...}}}

The runner writes observations.jsonl, one row per evaluation item carrying the
full score vector and the flag per guard, and result.json, which derives the
joint cells from those rows and records the sha256 of the contract, the scores
and this file. Cells are derived at analysis, never stored as a separate table.
result.json also carries the realized marginal-only identified width against
the informativeness floor the contract declared, and applies the contract's
consequence when the width falls below it: IDENTIFICATION-LIMITED, delta not
claimed. The floor comes from the contract; this file holds no number for it.

What this does not establish. The runner consumes the contract; nothing here
proves the scores were produced by the guards the contract names, that the
items are the items a freeze pinned, or that the freeze preceded scoring. Those
are edges U and V of the plane and remain open; score.py's refusals are the
nearest this experiment gets to them. E8 never froze its contract and produced no
observation row. E9 froze its contract before any score. tests/test_e8_runner.py
exercises this file on synthetic scores under a constructed contract and shows
that a changed contract changes what it selects. Frozen experiments are not
replayed through it: reuse of frozen rows is not reuse of confirmatory status.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "research" / "contracts"

_spec = importlib.util.spec_from_file_location("validate_contract", CONTRACTS / "validate_contract.py")
validate_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_contract)


class Refusal(Exception):
    """The runner will not proceed. The message says which declared condition failed."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path, require_frozen: bool = True) -> dict:
    contract = validate_contract.load(path)
    errors = validate_contract.validate(contract)
    if errors:
        raise Refusal("contract rejected by validate_contract.py: " + "; ".join(errors))
    if contract["kind"] != "guard_selection":
        raise Refusal(f"contract kind {contract['kind']!r} is not one this runner executes")
    if require_frozen and contract["status"] != "frozen":
        raise Refusal(f"contract status is {contract['status']!r}; only a frozen contract may produce rows")
    return contract


# Comparators the schema admits, spelled once, as functions of (score, threshold).
COMPARATORS = {"ge": lambda s, t: s >= t, "le": lambda s, t: s <= t}
# Candidate orderings the schema admits. The contract chooses; the runner never defaults.
ORDERINGS = {"lowest": lambda xs: sorted(xs), "highest": lambda xs: sorted(xs, reverse=True)}


def select_threshold(scores: list[float], operating_point: dict) -> float | None:
    """First candidate, in the contract's order, whose false-positive rate is within budget.

    Returns None when no candidate satisfies the budget; the caller applies the
    contract's no_feasible_candidate policy. Budget arithmetic is exact.
    """
    if operating_point["objective"] != "maximum_sensitivity_under_fpr_budget":
        raise Refusal(f"objective {operating_point['objective']!r} has no implementation here")
    if operating_point["candidates"] != "observed_benign_scores":
        raise Refusal(f"candidate rule {operating_point['candidates']!r} has no implementation here")
    flags = COMPARATORS[operating_point["comparator"]]
    order = ORDERINGS[operating_point["direction"]]
    budget = Fraction(str(operating_point["fpr_budget"]))
    n = len(scores)
    for t in order(set(scores)):
        fp = sum(1 for s in scores if flags(s, t))
        if Fraction(fp, n) <= budget:
            return t
    return None


def pool(scores: dict, name: str, guards: list[str]) -> dict[str, dict[str, float]]:
    if name not in scores["pools"]:
        raise Refusal(f"scores carry no pool named {name!r}; declared pools are the executed universe")
    items = scores["pools"][name]
    for item_id, vector in items.items():
        missing = [g for g in guards if g not in vector]
        if missing:
            raise Refusal(f"item {item_id!r} in pool {name!r} lacks a score for {missing}")
    return items


def execute(contract: dict, scores: dict) -> tuple[list[dict], dict]:
    guards = list(scores["guards"])
    if len(guards) < 2:
        raise Refusal("a joint cell needs at least two guards")
    op = contract["operating_point"]
    calibration = pool(scores, contract["execution_plan"]["calibration"], guards)
    evaluation = pool(scores, contract["execution_plan"]["evaluation"], guards)
    thresholds: dict[str, float] = {}
    excluded: list[str] = []
    for g in guards:
        t = select_threshold([v[g] for v in calibration.values()], op)
        if t is None:
            if op["no_feasible_candidate"] != "exclude_judge":
                raise Refusal(f"policy {op['no_feasible_candidate']!r} has no implementation here")
            excluded.append(g)
        else:
            thresholds[g] = t
    active = [g for g in guards if g in thresholds]
    if len(active) < 2:
        raise Refusal(f"fewer than two guards remain after exclusion: excluded {excluded}")
    flags = COMPARATORS[op["comparator"]]
    rows = []
    for item_id in sorted(evaluation):
        vector = {g: evaluation[item_id][g] for g in guards}
        row_flags = {g: int(flags(vector[g], thresholds[g])) for g in active}
        rows.append({"experiment": "E9", "contract_id": contract["id"], "pool": contract["execution_plan"]["evaluation"],
                     "item_id": item_id, "scores": vector, "flag": row_flags,
                     "miss": {g: 1 - f for g, f in row_flags.items()}})
    n = len(rows)
    miss_counts = {g: sum(r["miss"][g] for r in rows) for g in active}
    patterns = {"".join(bits): 0 for bits in itertools.product("01", repeat=len(active))}
    for r in rows:
        patterns["".join(str(r["miss"][g]) for g in active)] += 1
    all_miss = patterns["1" * len(active)]
    lo = max(0, sum(miss_counts.values()) - (len(active) - 1) * n)
    hi = min(miss_counts.values())
    plug_in = Fraction(1)
    for g in active:
        plug_in *= Fraction(miss_counts[g], n)
    result = {"experiment": "E9", "contract_id": contract["id"], "estimand": contract["estimand"],
              "guards": guards, "active_guards": active, "excluded_guards": excluded,
              "thresholds": thresholds, "operating_point": op,
              "evaluation": {"pool": contract["execution_plan"]["evaluation"], "n": n,
                             "miss_counts": miss_counts, "all_miss": all_miss,
                             "band_counts": [lo, hi], "plug_in_all_miss_count": str(plug_in * n),
                             "cells_derived_from_rows": patterns},
              "identification": identification(contract, n, lo, hi, all_miss, plug_in)}
    return rows, result


def identification(contract: dict, n: int, lo: int, hi: int, all_miss: int, plug_in: Fraction) -> dict:
    """The realized marginal-only width against the floor the contract declared, if it declared one.

    The width is what a reader holding only the marginals could say about the
    all-miss rate: (hi - lo) / n. The discrepancy delta = q_obs - q_ind can never
    exceed it. A contract that declares an informativeness floor has promised the
    consequence of falling below it; the runner applies that consequence and
    claims nothing about delta in that case. A contract without the group gets
    the width and the discrepancy, and no verdict.
    """
    width = Fraction(hi - lo, n)
    delta = Fraction(all_miss, n) - plug_in
    out = {"marginal_only_width": str(width), "delta_all_miss": str(delta)}
    group = (contract.get("inference") or {}).get("informativeness")
    if group is None:
        out.update({"floor": None, "status": "NOT-DECLARED", "delta_claimable": False,
                    "note": "the contract declares no marginal-only width floor; no verdict is issued"})
        return out
    floor = Fraction(str(group["marginal_only_width_min"]))
    below = width < floor
    out.update({"floor": str(floor),
                "status": group["consequence_when_below"] if below else "INFORMATIVE",
                "delta_claimable": not below})
    if below:
        out["note"] = ("the marginals identify the joint to within less than the declared floor, so no "
                       "discrepancy this contract would act on can exist on this pool; delta is recorded "
                       "and not claimed")
    return out


def run(contract_path: Path, scores_path: Path, out: Path, require_frozen: bool = True) -> dict:
    contract = load_contract(contract_path, require_frozen=require_frozen)
    scores = json.loads(scores_path.read_text())
    rows, result = execute(contract, scores)
    result["provenance"] = {"contract": {"path": str(contract_path), "sha256": sha256(contract_path)},
                            "scores": {"path": str(scores_path), "sha256": sha256(scores_path)},
                            "runner": {"path": "experiments/e9/run/runner.py", "sha256": sha256(Path(__file__))},
                            "contract_status": contract["status"]}
    result["non_claims"] = [
        "the contract was consumed, not merely referenced; nothing here proves the scores came from the "
        "guards the contract names, that the items are a freeze's items, or that the freeze preceded scoring",
        "cells are derived from the stored per-item score vectors at analysis time; no cell is an input",
        "a threshold, comparator or budget changed after these rows exist makes any re-run exploratory on them"]
    out.mkdir(parents=True, exist_ok=True)
    with (out / "observations.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    (out / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = run(args.contract, args.scores, args.out)
    except Refusal as exc:
        print(f"REFUSED: {exc}")
        return 1
    ev, ident = result["evaluation"], result["identification"]
    print(f"E9 under contract {result['contract_id']}: n={ev['n']} thresholds={result['thresholds']} "
          f"miss={ev['miss_counts']} all-miss={ev['all_miss']} band={ev['band_counts']}")
    print(f"identification: marginal-only width {ident['marginal_only_width']} against floor {ident['floor']} "
          f"-> {ident['status']}; delta {ident['delta_all_miss']} "
          f"{'claimable' if ident['delta_claimable'] else 'not claimed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
