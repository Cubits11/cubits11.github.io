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


# The largest stack this file will reduce without being told to stop. 2**20 is
# a million-cell table; past that the caller is almost certainly not describing
# a guardrail stack, and silently allocating is worse than refusing. Local
# operating limit, not part of any disclosure contract.
_MAX_GUARDS = 20


def _reduce(patterns: dict, names: list) -> dict:
    """The one joint calculator. Everything downstream is a subset sum.

    ``patterns`` maps a K-bit mask to a count of positives exhibiting exactly
    that flag pattern; bit i of the mask belongs to ``names[i]``. This is the
    whole disclosure: union, all-miss, ordered residual, leave-one-out, and
    every pairwise cell are sums over subsets of the same table.

    The consequence is the point. The pattern-count vector is a **sufficient
    statistic** for the entire minimum joint disclosure, its size is 2**K
    regardless of how many items were scored, and it retains nothing about any
    individual item. A five-guard stack discloses at most 32 integers whether
    it evaluated eighty prompts or a billion, and those integers are an
    aggregate, not a record. Cost and disclosure-risk were the two standing
    objections to publishing the joint column; both are answered here, by
    arithmetic rather than by argument.
    """
    k = len(names)
    if k < 2:
        raise ValueError("a joint disclosure needs at least two guards")
    if k > _MAX_GUARDS:
        raise ValueError(f"{k} guards exceeds this reducer's local limit of "
                         f"{_MAX_GUARDS}; refusing rather than allocating "
                         f"2**{k} cells")
    if len(set(names)) != k:
        raise ValueError("guard names must be distinct — they index the mask")
    full = 1 << k
    for mask, count in patterns.items():
        if not isinstance(mask, int) or not 0 <= mask < full:
            raise ValueError(f"mask {mask!r} is not a {k}-bit pattern")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"count for mask {mask} must be a non-negative "
                             f"integer, got {count!r}")

    n_pos = sum(patterns.values())
    if n_pos == 0:
        raise ValueError("no positives — the denominator is empty")

    def total(predicate) -> int:
        return sum(c for m, c in patterns.items() if predicate(m))

    per_guard = {names[i]: total(lambda m, i=i: m >> i & 1) for i in range(k)}
    union = total(lambda m: m != 0)
    all_miss = patterns.get(0, 0)

    residual, prior = [], 0
    for i, name in enumerate(names):
        earlier = (1 << i) - 1
        residual.append({
            "guard": name,
            "catches_among_prior_misses":
                total(lambda m, i=i, e=earlier: (m >> i & 1) and not (m & e)),
            "prior_misses": n_pos - prior,
        })
        prior += residual[-1]["catches_among_prior_misses"]

    # Leave-one-out: the union with guard i removed. An item leaves the union
    # only when i was its sole catcher, so LOO_i = U - (items caught only by i).
    leave_one_out = []
    for i, name in enumerate(names):
        only_i = patterns.get(1 << i, 0)
        leave_one_out.append({
            "guard": name,
            "union_without": union - only_i,
            "unique_contribution": only_i,
        })

    pairwise = []
    for a, b in itertools.combinations(range(k), 2):
        pairwise.append({
            "guards": [names[a], names[b]],
            "both_catch": total(lambda m, a=a, b=b: (m >> a & 1) and (m >> b & 1)),
            "both_miss": total(lambda m, a=a, b=b: not (m >> a & 1)
                               and not (m >> b & 1)),
        })

    return {
        "denominator": n_pos,
        "per_guard": per_guard,
        "union_detection": union,
        "all_miss": all_miss,
        "residual_coverage": residual,
        "leave_one_out": leave_one_out,
        "pairwise": pairwise,
        "note": ("counts over the stated positive set; rates are each count "
                 "over the denominator; the declared guard order defines "
                 "residual attribution and nothing else"),
    }


def joint_disclosure_from_patterns(patterns: dict, order: list) -> dict:
    """Reduce a compact (mask, count) table. Bit i is pinned to ``order[i]``.

    For an evaluation that scored a billion items, this is the entry point:
    the table is 2**K cells whatever N was, so nothing here is proportional to
    the number of items. It is the same kernel `joint_disclosure` uses, so the
    two paths cannot drift apart.
    """
    return _reduce(dict(patterns), list(order))


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

    patterns: dict = {}
    for i, is_pos in enumerate(positive):
        if not is_pos:
            continue
        mask = 0
        for bit, name in enumerate(names):
            if decisions[name][i]:
                mask |= 1 << bit
        patterns[mask] = patterns.get(mask, 0) + 1
    if not patterns:
        raise ValueError("no positives — the denominator is empty")
    return _reduce(patterns, names)


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

    # The two entry points are one kernel. If a compact table and a per-item
    # scoring of the same evaluation ever disagreed, the disclosure would have
    # two meanings and the contract would be worthless.
    for seed in (11, 12, 13):
        decisions, positive = _fixture(seed, n=500, guards=4)
        names = list(decisions)
        per_item = joint_disclosure(decisions, positive)
        patterns: dict = {}
        for i, is_pos in enumerate(positive):
            if not is_pos:
                continue
            mask = sum(1 << b for b, nm in enumerate(names) if decisions[nm][i])
            patterns[mask] = patterns.get(mask, 0) + 1
        compact = joint_disclosure_from_patterns(patterns, names)
        check(compact == per_item,
              f"seed {seed}: compact (mask, count) table reduces identically "
              f"to per-item scoring")
        check(len(patterns) <= 2 ** len(names),
              f"seed {seed}: table is at most 2**{len(names)} cells for "
              f"{per_item['denominator']} positives — size does not follow N")

    # Leave-one-out is the union without that guard, and the quantity that
    # moves is its unique contribution. This is NOT residual coverage: A={0,1},
    # B={1,2} gives B a residual of 1 and a unique contribution of 1, but with
    # A={0,1}, B={1} the residual is 0 while the union is unchanged.
    d = joint_disclosure_from_patterns({0b01: 5, 0b10: 3, 0b11: 7, 0b00: 2},
                                       ["A", "B"])
    check(d["union_detection"] == 15 and d["all_miss"] == 2,
          "compact table: union 15, all-miss 2 over denominator 17")
    for row in d["leave_one_out"]:
        check(row["union_without"] == d["union_detection"]
              - row["unique_contribution"],
              f"leave-one-out identity holds for {row['guard']}")
    check([r["unique_contribution"] for r in d["leave_one_out"]] == [5, 3],
          "unique contribution is the count caught by that guard alone")

    for bad, why in (({0b100: 1}, "a mask wider than the declared order"),
                     ({0b01: -1}, "a negative count"),
                     ({0b01: True}, "a boolean masquerading as a count")):
        try:
            joint_disclosure_from_patterns(bad, ["A", "B"])
            check(False, f"refuses {why}")
        except ValueError:
            check(True, f"refuses {why}")
    try:
        joint_disclosure_from_patterns({0: 1}, [f"g{i}" for i in range(21)])
        check(False, "refuses a stack past the local guard limit")
    except ValueError:
        check(True, "refuses a stack past the local guard limit")

    print()
    if failures:
        print(f"{failures} disclosure check(s) failed.")
        return 1
    print("Disclosure arithmetic verified: identities hold, refusals refuse, "
          "and one kernel serves both entry points.")
    return 0


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(_test())
    decisions, positive = _fixture(0)
    print(json.dumps(joint_disclosure(decisions, positive), indent=2))
