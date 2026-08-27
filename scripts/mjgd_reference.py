#!/usr/bin/env python3
"""Minimum Joint Guardrail Disclosure — reference implementation.

Input: one boolean decision per item per guard (True = the guard flagged
the item), plus which items are positives (items a guard should catch).
Output: every joint statistic the disclosure asks for — per-guard counts,
union detection, all-miss, residual coverage in stack order, and pairwise
intersections of catches and of misses — with the denominator attached to
each number.

This file is the entire marginal cost of the disclosure for an evaluation
that retained per-item decisions. It has no dependencies beyond the
standard library. `--test` runs the synthetic fixtures and asserts the
identities that make the arithmetic trustworthy:

  * union + all-miss = number of positives
  * residual coverage telescopes: marginal of guard 1 + residuals of the
    later guards = union
  * every pairwise intersection respects its feasibility bounds
    max(0, a + b - n) <= |A ∩ B| <= min(a, b)
  * permuting stack order never changes union or all-miss (only the
    residual attribution)

Nothing here estimates dependence, corrects for sampling error, or
certifies a stack. It counts. Uncertainty intervals and missingness policy
are the evaluator's obligations, stated alongside the counts.
"""

import itertools
import json
import random
import sys


def joint_disclosure(decisions: dict, positive: list) -> dict:
    """decisions[name][i] = True if guard `name` flagged item i.
    positive[i] = True if item i is a positive (should be caught).
    Guards are read in dict order; that order defines residual attribution.
    """
    names = list(decisions)
    if len(names) < 2:
        raise ValueError("a joint disclosure needs at least two guards")
    n_items = len(positive)
    for name in names:
        if len(decisions[name]) != n_items:
            raise ValueError(f"guard {name!r} has {len(decisions[name])} "
                             f"decisions for {n_items} items — every guard "
                             f"must score every item")

    pos_idx = [i for i, p in enumerate(positive) if p]
    n_pos = len(pos_idx)
    if n_pos == 0:
        raise ValueError("no positives — the denominator is empty")

    catches = {name: {i for i in pos_idx if decisions[name][i]}
               for name in names}
    union = set().union(*catches.values())
    all_miss = [i for i in pos_idx if i not in union]

    residual = []
    caught_so_far: set = set()
    for name in names:
        new = catches[name] - caught_so_far
        residual.append({
            "guard": name,
            "catches_among_prior_misses": len(new),
            "prior_misses": n_pos - len(caught_so_far),
        })
        caught_so_far |= catches[name]

    pairwise = []
    for a, b in itertools.combinations(names, 2):
        pairwise.append({
            "guards": [a, b],
            "both_catch": len(catches[a] & catches[b]),
            "both_miss": len({i for i in pos_idx
                              if i not in catches[a] and i not in catches[b]}),
        })

    return {
        "denominator": n_pos,
        "per_guard": {name: len(catches[name]) for name in names},
        "union_detection": len(union),
        "all_miss": len(all_miss),
        "residual_coverage": residual,
        "pairwise": pairwise,
        "note": ("counts over the stated positive set; rates are each count "
                 "over the denominator; order of `decisions` defines "
                 "residual attribution"),
    }


def _fixture(seed: int, n: int = 400, guards: int = 3) -> tuple:
    rng = random.Random(seed)
    positive = [rng.random() < 0.5 for _ in range(n)]
    decisions = {}
    for g in range(guards):
        skill = 0.55 + 0.15 * g
        decisions[f"guard_{g}"] = [
            (rng.random() < skill) if positive[i] else (rng.random() < 0.05)
            for i in range(n)]
    return decisions, positive


def _test() -> int:
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if cond:
            print(f"ok    {msg}")
        else:
            failures += 1
            print(f"FAIL  {msg}")

    # Hand-computable fixture: 4 positives, 2 guards.
    #   item:      0     1      2      3      4(neg)
    #   positive:  T     T      T      T      F
    #   A:         T     T      F      F      T
    #   B:         T     F      T      F      F
    decisions = {"A": [True, True, False, False, True],
                 "B": [True, False, True, False, False]}
    positive = [True, True, True, True, False]
    d = joint_disclosure(decisions, positive)
    check(d["denominator"] == 4, "fixture: denominator 4")
    check(d["per_guard"] == {"A": 2, "B": 2}, "fixture: per-guard counts")
    check(d["union_detection"] == 3, "fixture: union 3 (items 0,1,2)")
    check(d["all_miss"] == 1, "fixture: all-miss 1 (item 3)")
    check(d["residual_coverage"][1]["catches_among_prior_misses"] == 1,
          "fixture: B catches 1 among the 2 A missed")
    check(d["residual_coverage"][1]["prior_misses"] == 2,
          "fixture: 2 prior misses when B is added")
    check(d["pairwise"][0] == {"guards": ["A", "B"], "both_catch": 1,
                               "both_miss": 1},
          "fixture: pairwise both-catch 1, both-miss 1")

    # Identities on random fixtures.
    for seed in range(5):
        decisions, positive = _fixture(seed)
        d = joint_disclosure(decisions, positive)
        n_pos = d["denominator"]
        check(d["union_detection"] + d["all_miss"] == n_pos,
              f"seed {seed}: union + all-miss = denominator")
        telescoped = sum(r["catches_among_prior_misses"]
                         for r in d["residual_coverage"])
        check(telescoped == d["union_detection"],
              f"seed {seed}: residual coverage telescopes to the union")
        for pair in d["pairwise"]:
            a, b = (d["per_guard"][g] for g in pair["guards"])
            lo, hi = max(0, a + b - n_pos), min(a, b)
            check(lo <= pair["both_catch"] <= hi,
                  f"seed {seed}: {pair['guards']} intersection within "
                  f"[{lo}, {hi}]")
        # Order independence of the joint statistics.
        reordered = dict(reversed(list(decisions.items())))
        d2 = joint_disclosure(reordered, positive)
        check((d2["union_detection"], d2["all_miss"])
              == (d["union_detection"], d["all_miss"]),
              f"seed {seed}: union and all-miss invariant under stack order")

    # Refusals.
    try:
        joint_disclosure({"A": [True]}, [True])
        check(False, "refuses a single guard")
    except ValueError:
        check(True, "refuses a single guard")
    try:
        joint_disclosure({"A": [True], "B": [True, False]}, [True, True])
        check(False, "refuses ragged decision vectors")
    except ValueError:
        check(True, "refuses ragged decision vectors")
    try:
        joint_disclosure({"A": [False], "B": [False]}, [False])
        check(False, "refuses an empty denominator")
    except ValueError:
        check(True, "refuses an empty denominator")

    print()
    if failures:
        print(f"{failures} disclosure check(s) failed.")
        return 1
    print("Disclosure arithmetic verified: identities hold, refusals refuse.")
    return 0


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(_test())
    decisions, positive = _fixture(0)
    print(json.dumps(joint_disclosure(decisions, positive), indent=2))
