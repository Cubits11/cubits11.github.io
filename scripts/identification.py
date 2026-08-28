#!/usr/bin/env python3
"""What a reader can actually compute about a stack, given what was published.

The census asks whether joint statistics are *reported*. This file asks the
prior question: for a given evaluation, what is the identified set for the
quantity an operator cares about — the rate at which every guard in the
stack misses the same item?

None of the mathematics here is new. It is Bonferroni plus monotonicity,
and the bounds are Fréchet's. What this file contributes is the
application: pricing, in probability units, what marginal-only guardrail
reporting leaves undetermined, and naming the cheapest disclosure that
determines it.

For miss events E_1..E_k (E_i = "guard i missed this item") with marginal
miss rates p_1..p_k on a common population, the all-miss rate is pinned
only to

    max(0, Σ p_i − (k−1))  ≤  P(∩ E_i)  ≤  min_i p_i

and — since couplings are closed under mixture and the functional is
affine — every point of that interval is attained by some joint law with
those marginals. The interval IS the identified set, not a conservative
envelope. Both endpoints are attained for every k: the upper by nesting
the events (comonotone), the lower by laying the complements end to end
around the circle, where they cover it exactly when Σ p_i ≤ k−1.

Three consequences, stated in the direction that survives scrutiny:

  * DIRECTION. Under block-on-any (OR) composition, P(∩E_i) ≤ min_i p_i is
    a theorem: a stack is never worse than its best member at catching.
    What marginals can never do is certify that it is BETTER, because
    min_i p_i always lies inside the identified set. Strict improvement is
    unfalsifiable from marginals; degradation is ruled out by algebra.

  * ASYMMETRY. When Σ p_i > k−1 the lower endpoint is positive, so
    marginals CAN certify an irreducible failure floor. They can certify a
    floor on failure and never a gain from stacking. The same holds on the
    benign side, where the union burden is bounded below by max_i f_i and
    is therefore always certifiably positive when any guard misfires.

  * PRICE. One scalar closes the harmful side: for a parallel stack on a
    fixed labelled population at a fixed operating point, all-miss = 1 − B
    where B is the "flagged by at least one guard" rate. This is an
    identity, not a theorem. Cheap, and it releases no items.

    But the identity that MATTERS is the leave-one-out union. Publishing
    the k unions-without-guard-g reveals each member's unique contribution
    — the thing marginals plus the union together still hide, and the
    thing nobody asks for. See ``leave_one_out``.

What this file does NOT do: estimate dependence, correct for sampling
error, model routes, or certify a stack. A bound is not an estimate, and
where a value sits inside a bound is not a score.

    python3 scripts/identification.py --test    # identities and sharpness
    python3 scripts/identification.py --bells   # the one calibrated case
"""

import itertools
import json
import sys


# --------------------------------------------------------- identified sets

def frechet_interval(miss_rates: list[float]) -> tuple[float, float]:
    """Identified set for P(all k guards miss), given only their marginals."""
    if len(miss_rates) < 2:
        raise ValueError("a stack needs at least two guards")
    for p in miss_rates:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"miss rate {p} is not a probability")
    k = len(miss_rates)
    return max(0.0, sum(miss_rates) - (k - 1)), min(miss_rates)


def integer_grid(catch_counts: list[int], n: int) -> list[int]:
    """The identified set on a finite item set is not an interval of reals
    but a set of integers, and it is smaller than the continuous bound
    suggests. With n items and catch counts c_i, an all-miss count of t
    requires every guard's catches to fit inside the remaining n − t
    items, so t ≤ n − max_i c_i. Every value from the lower bound up to
    that ceiling is realisable by relabelling which items each guard
    catches, holding every count exact."""
    if n <= 0:
        raise ValueError("empty denominator")
    lo = max(0, sum(n - c for c in catch_counts) - (len(catch_counts) - 1) * n)
    return list(range(lo, n - max(catch_counts) + 1))


def independence_plugin(miss_rates: list[float]) -> float:
    """The number a dashboard prints when it assumes the guards fail
    independently. It is one point inside the identified set, chosen by
    assumption rather than evidence. It is never outside the set, so the
    bounds alone cannot refute it — only per-item data can."""
    product = 1.0
    for p in miss_rates:
        product *= p
    return product


def burden_interval(flag_rates: list[float]) -> tuple[float, float]:
    """Identified set for the stack's benign flag rate — the union of the
    guards' false positives, since one guard flagging is enough:

        max_i f_i  ≤  P(∪ F_i)  ≤  min(1, Σ f_i)

    The lower endpoint is strictly positive whenever any guard has a
    non-zero false-positive rate. Marginals therefore always identify a
    floor under what a stack costs legitimate users."""
    if len(flag_rates) < 2:
        raise ValueError("a stack needs at least two guards")
    for f in flag_rates:
        if not 0.0 <= f <= 1.0:
            raise ValueError(f"flag rate {f} is not a probability")
    return max(flag_rates), min(1.0, sum(flag_rates))


def improvement_interval(miss_rates: list[float]) -> tuple[float, float]:
    """Identified set for min_i p_i − P(all miss): how much the stack
    improves on its own best member.

    The lower endpoint is always 0, attained when the best guard's misses
    are contained in every other guard's. Set beside ``burden_interval``,
    the asymmetry is exact — a positive identified floor under the cost, a
    floor of zero under the benefit.

    Read with care: "best member" is selected after seeing the numbers, so
    an improvement measured against it is a post-hoc comparison, not an
    estimate of what stacking buys in general."""
    lower, upper = frechet_interval(miss_rates)
    best = min(miss_rates)
    return best - upper, best - lower


def collapse_from_union(union_rate: float) -> float:
    """all-miss = 1 − (rate flagged by at least one guard). An identity for
    a parallel stack on a fixed labelled population at a fixed operating
    point — not a theorem, and not robust to changing any of those three."""
    if not 0.0 <= union_rate <= 1.0:
        raise ValueError("union rate is not a probability")
    return 1.0 - union_rate


def leave_one_out(catch_sets: dict) -> dict:
    """Each guard's unique contribution: how much the union shrinks when
    that guard is removed.

    This is the disclosure that marginals plus the union still cannot
    supply, and it costs k scalars and no items. A stack whose members'
    marginals look complementary can be, item for item, one guard doing
    all the work and k−1 riding along; only these numbers distinguish the
    two cases."""
    names = list(catch_sets)
    if len(names) < 2:
        raise ValueError("a stack needs at least two guards")
    union = set().union(*catch_sets.values())
    out = {}
    for g in names:
        without = set().union(*[catch_sets[x] for x in names if x != g]) \
            if len(names) > 1 else set()
        out[g] = {"union_without": len(without),
                  "unique_contribution": len(union) - len(without)}
    return {"union": len(union), "per_guard": out}


# --------------------------------------------------------------- self-tests

def _realise_extremes(miss_rates: list[float], grid: int = 2000) -> tuple[float, float]:
    """Attainability by explicit construction, not by restating the formula.
    Upper: nest the events on [0,1) so the intersection is [0, min p).
    Lower: lay the COMPLEMENTS end to end around the circle; they cover it
    exactly when Σ(1 − p_i) ≥ 1, i.e. Σ p_i ≤ k − 1."""
    cells = [(i + 0.5) / grid for i in range(grid)]
    upper_hat = sum(1 for c in cells if all(c < p for p in miss_rates)) / grid
    arcs, start = [], 0.0
    for p in miss_rates:
        arcs.append((start, start + (1.0 - p)))
        start += (1.0 - p)
    def missed_by_all(c: float) -> bool:
        for lo, hi in arcs:
            if lo <= c < hi or (hi > 1.0 and c < hi - 1.0):
                return False
        return True
    return sum(1 for c in cells if missed_by_all(c)) / grid, upper_hat


def _test() -> int:
    failures = []

    def check(cond, msg):
        print(("ok    " if cond else "FAIL  ") + msg)
        if not cond:
            failures.append(msg)

    lo, hi = frechet_interval([0.5, 0.5])
    check((lo, hi) == (0.0, 0.5), "k=2, p=(.5,.5): identified set [0, 0.5]")

    lo, hi = frechet_interval([0.9, 0.9])
    check(abs(lo - 0.8) < 1e-12,
          "Σp > k−1 lifts the lower endpoint: marginals CAN certify a "
          "failure floor (0.8)")

    for rates in ([0.3, 0.4, 0.5], [0.1, 0.9, 0.5, 0.2]):
        lo, hi = frechet_interval(rates)
        check(lo == 0.0 and abs((hi - lo) - min(rates)) < 1e-12,
              f"Σp ≤ k−1 for {rates}: width == best guard's rate {min(rates)}")

    for rates in ([0.3, 0.4, 0.5], [0.9, 0.9, 0.9], [0.5] * 5):
        lo, hi = frechet_interval(rates)
        check(lo - 1e-12 <= independence_plugin(rates) <= hi + 1e-12,
              f"independence lies INSIDE the identified set for {rates} — "
              "the bounds alone cannot refute it")

    for rates in ([0.3, 0.4, 0.5], [0.2, 0.6, 0.7, 0.9]):
        lo, hi = frechet_interval(rates)
        lo_hat, hi_hat = _realise_extremes(rates)
        check(abs(hi_hat - hi) < 1e-3,
              f"upper endpoint {hi:.3f} realised by nesting ({hi_hat:.3f})")
        check(abs(lo_hat - lo) < 1e-3,
              f"lower endpoint {lo:.3f} realised by arc covering ({lo_hat:.3f})")

    # Direction: a stack is never WORSE than its best member (OR composition).
    check(frechet_interval([0.3, 0.4, 0.5])[1] == 0.3,
          "upper endpoint is the best guard's rate — a stack cannot be worse")
    check(improvement_interval([0.3, 0.4, 0.5])[0] == 0.0,
          "…and the identified floor under its improvement is exactly 0")

    # The asymmetry, on both sides at once.
    b_lo, b_hi = burden_interval([0.14, 0.0, 0.16, 0.20, 0.0])
    check(b_lo > 0, f"benign burden floor is strictly positive ({b_lo:.0%})")

    # Finite-sample: the grid is smaller than the real interval implies.
    grid = integer_grid([52, 5, 25, 70, 0], 82)
    check(grid[0] == 0 and grid[-1] == 12 and len(grid) == 13,
          "on 82 items the identified set is {0/82 … 12/82}: 13 values, and "
          "13/82 is infeasible because 70 catches cannot fit in 69 items")

    check(abs(collapse_from_union(73 / 82) - 9 / 82) < 1e-12,
          "one published union rate identifies all-miss exactly (1 − 73/82)")

    check(len({frechet_interval(list(q))
               for q in itertools.permutations([0.15, 0.65, 0.4])}) == 1,
          "the identified set does not depend on stack order")

    loo = leave_one_out({"a": {1, 2, 3}, "b": {1, 2}, "c": {4}})
    check(loo["per_guard"]["b"]["unique_contribution"] == 0
          and loo["per_guard"]["c"]["unique_contribution"] == 1,
          "leave-one-out exposes a member that contributes nothing, which "
          "marginals and the union together cannot")

    # The registry envelope must match what this file computes, or MC-003
    # is decoration. Same discipline as MC-001/MC-002.
    try:
        exp = _expected_mc003()
    except Exception as exc:                       # registry absent in a bare copy
        print(f"note  MC-003 envelope not cross-checked ({exc})")
    else:
        b = _expected()
        n, catches = b["n_harmful"], b["per_guard_catches"]
        grid = integer_grid(list(catches.values()), n)
        rates = [(n - c) / n for c in catches.values()]
        fv = [c / b["n_benign"] for c in b["per_guard_benign_flags"].values()]
        zeros = sum(1 for g in catches
                    if b["union_detection"] - b["leave_one_out_union"][g] == 0)
        got = {
            "identified_set_lower": grid[0],
            "identified_set_upper": grid[-1],
            "identified_set_size": len(grid),
            "observed_all_miss": b["all_miss"],
            "denominator": n,
            "benign_burden_floor_pct": round(burden_interval(fv)[0] * 100),
            "improvement_floor_pct": round(improvement_interval(rates)[0] * 100),
            "members_contributing_nothing": zeros,
        }
        for key, want in exp.items():
            check(got.get(key) == want,
                  f"MC-003 expected {key}={want} matches the computation "
                  f"({got.get(key)})")

    if failures:
        print(f"\n{len(failures)} check(s) failed.")
        return 1
    print("\nIdentification arithmetic verified: bounds sharp and attained, "
          "independence interior,\nimprovement floor zero, burden floor "
          "positive, leave-one-out separates riders.")
    return 0


# ------------------------------------------------------------- the one case

def _expected_mc003() -> dict:
    import pathlib

    import yaml
    root = pathlib.Path(__file__).resolve().parent.parent
    registry = yaml.safe_load((root / "claims.yaml").read_text())
    return next(c for c in registry["claims"]
                if c["id"] == "MC-003")["expected"]


def _expected() -> dict:
    """Counts come from MC-002's expected block, which
    scripts/reanalyze_bells_subset.py re-asserts against the hash-verified
    upstream file on every CI run. This file keeps no copy of a number the
    registry already binds."""
    import pathlib

    import yaml
    root = pathlib.Path(__file__).resolve().parent.parent
    registry = yaml.safe_load((root / "claims.yaml").read_text())
    return next(c for c in registry["claims"] if c["id"] == "MC-002")["expected"]


def _bells() -> int:
    exp = _expected()
    n = exp["n_harmful"]
    catches = exp["per_guard_catches"]
    rates = {g: (n - c) / n for g, c in catches.items()}
    p = list(rates.values())
    lo, hi = frechet_interval(p)
    actual = exp["all_miss"] / n
    plug = independence_plugin(p)
    best = min(rates, key=lambda g: rates[g])
    union = exp["union_detection"]

    print("BELLS 2025 misuse-detection subset — the one calibrated case")
    print(f"  denominator: {n} prompts labelled harmful, of "
          f"{n + exp['n_benign'] + exp['n_borderline']} released")
    print(f"  ({exp['n_benign']} benign and {exp['n_borderline']} borderline "
          "are separate strata and are never folded in)\n")
    for g, r in sorted(rates.items(), key=lambda kv: kv[1]):
        print(f"    {g:<14} misses {n - catches[g]:>2}/{n} = {r:6.2%}")

    print("\n  --- what the marginals alone identify ---")
    print(f"  identified set for all-miss : [{lo:.2%}, {hi:.2%}]"
          f"   width {hi - lo:.2%}")
    print(f"  width == best guard ({best})  : {rates[best]:.2%}")
    print(f"  on {n} items the set is      : "
          f"{{{integer_grid(list(catches.values()), n)[0]}/{n} … "
          f"{integer_grid(list(catches.values()), n)[-1]}/{n}}}")
    print(f"  independence plug-in        : {plug:.2%}  — inside the set, so "
          "the bounds\n                                cannot refute it; only "
          "the per-item release can")
    print(f"  actually observed           : {actual:.2%} "
          f"({exp['all_miss']} of {n})")
    print(f"  collapse from the union     : 1 − {union}/{n} = "
          f"{collapse_from_union(union / n):.2%}")

    i_lo, i_hi = improvement_interval(p)
    nb = exp["n_benign"]
    fv = [c / nb for c in exp["per_guard_benign_flags"].values()]
    b_lo, b_hi = burden_interval(fv)
    b_actual = exp["benign_union_flagged"] / nb
    print("\n  --- the asymmetry ---")
    print(f"  benign burden, identified   : [{b_lo:.2%}, {b_hi:.2%}]"
          "   floor POSITIVE")
    print(f"  benign burden, actual       : {b_actual:.2%}")
    print(f"  improvement over {best},     : [{i_lo:.2%}, {i_hi:.2%}]"
          "   floor ZERO")
    print(f"  identified / actual         : "
          f"{rates[best] - actual:.2%} on this stratum")
    print(f"\n  From the marginals alone one can prove this stack flags at least")
    print(f"  {b_lo:.0%} of benign traffic, and cannot prove it catches one harmful")
    print(f"  item its best member would have missed. ({best} is chosen after")
    print(f"  seeing the results, so the comparison is post-hoc.)")

    print("\n  --- what marginals AND the union still hide ---")
    print("  leave-one-out unions — k scalars, no items released:")
    for g, c in sorted(catches.items(), key=lambda kv: -kv[1]):
        loo = exp["leave_one_out_union"][g]
        print(f"    without {g:<14} union {loo:>2}/{n}   "
              f"unique contribution {union - loo:>2}")
    zeros = [g for g in catches if union - exp["leave_one_out_union"][g] == 0]
    print(f"\n  {len(zeros)} of {len(catches)} members contribute nothing to this")
    print(f"  stratum's union: {', '.join(sorted(zeros))}.")
    print("  The published marginals and the union are exactly what such a")
    print("  stack would report, and are fully consistent with a working")
    print(f"  {len(catches)}-member ensemble. Only the leave-one-out row shows")
    print("  otherwise. Nobody asks for that row.")

    print(f"\n  Scope: exactly these {n} author-selected prompts at the vendors'")
    print("  released binary verdicts, on one stratum of one evaluation. A")
    print("  calibration point, not a population, and no ratio here is offered")
    print("  as a general law of guardrail dependence.")
    if "--json" in sys.argv:
        print(json.dumps({"interval": [lo, hi], "actual": actual,
                          "independence": plug, "burden": [b_lo, b_hi],
                          "improvement": [i_lo, i_hi]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_bells() if "--bells" in sys.argv else _test())
