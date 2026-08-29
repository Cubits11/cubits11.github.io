#!/usr/bin/env python3
"""What static stack behavior is identified by the columns a report keeps.

The census asks whether joint statistics are reported. This file asks the
prior question: on one fixed evaluation, what can a reader recover about the
rate at which every eligible guard misses the same item when the report keeps
only per-guard marginals?

The scope is deliberately narrow: a common, fixed population; full exposure
of every eligible guard to every item; per-item decisions that are functions
of that item; one declared operating point; and a parallel block-on-any (OR)
rule. It is not a model of a sequential route, a changed agent trajectory,
adaptive attack, sampling uncertainty, or deployment risk.

For miss events E_1..E_k with marginal miss rates p_1..p_k, the continuous
identified set for static all-miss is the sharp Fréchet interval

    max(0, sum(p_i) - (k-1)) <= P(intersection E_i) <= min(p_i).

Every point is attainable by a joint law with those marginals. On a finite
population of n labelled items with exact per-guard catch counts c_i, the
identified set is the integer grid

    {max(0, n - sum(c_i)), ..., n - max(c_i)}.

One same-denominator union aggregate identifies static all-miss exactly:
all_miss = n - union_detection. It does not disclose overlap. Publishing the
k leave-one-out unions adds a compact, privacy-preserving view of each guard's
*exclusive full-stack coverage*: union_all - union_without_guard. That still
does not identify pairwise or higher-order overlap, Shapley values, route
semantics, or an ensemble's causal structure.

The mathematics is classical. The contribution here is a checked translation
from the mathematics to the disclosure boundary — what a marginal table can
support, what a union closes, and what a small additional aggregate exposes.

    python3 scripts/identification.py --test    # formulas and finite checks
    python3 scripts/identification.py --bells   # registered BELLS envelope
"""

import itertools
import json
import sys


# --------------------------------------------------------- identified sets

def _check_probabilities(values: list[float], label: str) -> None:
    if len(values) < 2:
        raise ValueError("a stack needs at least two guards")
    for value in values:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{label} {value} is not a probability")


def _check_counts(values: list[int], n: int) -> None:
    if len(values) < 2:
        raise ValueError("a stack needs at least two guards")
    if n <= 0:
        raise ValueError("empty denominator")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= n:
            raise ValueError(f"catch count {value!r} is not an integer in [0, {n}]")


def frechet_interval(miss_rates: list[float]) -> tuple[float, float]:
    """Sharp continuous identified set for P(all k guards miss)."""
    _check_probabilities(miss_rates, "miss rate")
    k = len(miss_rates)
    return max(0.0, sum(miss_rates) - (k - 1)), min(miss_rates)


def identified_width(miss_rates: list[float]) -> float:
    """Width of the continuous all-miss identified set.

    It equals min(p_i) only when the lower Fréchet endpoint is zero.
    """
    lower, upper = frechet_interval(miss_rates)
    return upper - lower


def integer_grid(catch_counts: list[int], n: int) -> list[int]:
    """Exact finite-population all-miss counts compatible with catch counts.

    With n labelled items and exact catches c_i, the all-miss count t is
    feasible exactly for max(0, n - sum(c_i)) <= t <= n - max(c_i). Every
    integer in that range is attained by choosing catch sets on n labels.
    """
    _check_counts(catch_counts, n)
    lower = max(0, n - sum(catch_counts))
    upper = n - max(catch_counts)
    return list(range(lower, upper + 1))


def unique_contribution_intervals(
        catch_counts: dict[str, int], union_count: int) -> dict[str, tuple[int, int]]:
    """Bounds on each guard's exclusive full-stack coverage from aggregates.

    Let c_i be a guard's catch count and U the full-stack union. Its exclusive
    count q_i is identified only to

        max(0, U - sum_{j != i} c_j) <= q_i
            <= min(c_i, U - max_{j != i} c_j).

    Each integer in the interval is attainable. Thus marginals plus a union
    can sometimes prove an exclusive count is zero (as a zero marginal does),
    but they generally cannot recover every guard's realized exclusive
    coverage. Leave-one-out unions do so under the static assumptions above.
    """
    names = list(catch_counts)
    counts = list(catch_counts.values())
    if len(names) < 2:
        raise ValueError("a stack needs at least two guards")
    if isinstance(union_count, bool) or not isinstance(union_count, int) or union_count < 0:
        raise ValueError("union count must be a non-negative integer")
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0
           for count in counts):
        raise ValueError("catch counts must be non-negative integers")
    if union_count < max(counts) or union_count > sum(counts):
        raise ValueError("union count is incompatible with the catch counts")

    bounds = {}
    for guard, count in catch_counts.items():
        others = [other for name, other in catch_counts.items() if name != guard]
        lower = max(0, union_count - sum(others))
        upper = min(count, union_count - max(others))
        bounds[guard] = (lower, upper)
    return bounds


def independence_plugin(miss_rates: list[float]) -> float:
    """The all-miss expectation under an independence model.

    The product lies in the continuous Fréchet set. Marginals alone therefore
    do not identify a realized all-miss rate or distinguish the independence
    model from another compatible coupling; a same-denominator union or
    per-item outcome data can. On a finite file the product can be a
    non-integer expected count, not a realizable deterministic cell count.
    """
    _check_probabilities(miss_rates, "miss rate")
    product = 1.0
    for rate in miss_rates:
        product *= rate
    return product


def burden_interval(flag_rates: list[float]) -> tuple[float, float]:
    """Sharp identified set for a static OR stack's benign union-flag rate.

        max_i f_i <= P(union F_i) <= min(1, sum(f_i)).

    A positive marginal benign flag rate therefore yields a positive lower
    bound on the static union-flag burden. Whether that is an acceptable user
    cost requires a separate utility, calibration, and route analysis.
    """
    _check_probabilities(flag_rates, "flag rate")
    return max(flag_rates), min(1.0, sum(flag_rates))


def improvement_interval(miss_rates: list[float]) -> tuple[float, float]:
    """Identified set for improvement over the best static member.

    The quantity is min_i p_i - P(all miss). Its lower endpoint is zero;
    marginal rates certify non-degradation under OR composition. They do not
    generally certify strict incremental benefit: when the set is
    non-degenerate, zero remains compatible. In a singleton case, however,
    marginals can rule strict improvement out.
    """
    lower, upper = frechet_interval(miss_rates)
    best = min(miss_rates)
    return best - upper, best - lower


def collapse_from_union(union_rate: float) -> float:
    """Static all-miss = 1 - static union detection on one fixed population."""
    if not 0.0 <= union_rate <= 1.0:
        raise ValueError("union rate is not a probability")
    return 1.0 - union_rate


# --------------------------------------------------------------- self-tests

def _realise_extremes(miss_rates: list[float], grid: int = 10_000) -> tuple[float, float]:
    """Numerical smoke check for explicit endpoint constructions.

    Upper endpoint: nest all miss events from zero. Lower endpoint: lay their
    complements consecutively around a unit circle. The formulas above give
    the exact endpoint; this routine checks the constructions on a fine grid.
    """
    _check_probabilities(miss_rates, "miss rate")
    if grid <= 0:
        raise ValueError("grid must be positive")
    cells = [(index + 0.5) / grid for index in range(grid)]
    upper_hat = sum(
        1 for cell in cells if all(cell < rate for rate in miss_rates)
    ) / grid

    arcs, start = [], 0.0
    for rate in miss_rates:
        length = 1.0 - rate
        arcs.append((start % 1.0, length))
        start += length

    def in_arc(cell: float, origin: float, length: float) -> bool:
        return length >= 1.0 or ((cell - origin) % 1.0) < length

    lower_hat = sum(
        1 for cell in cells if not any(in_arc(cell, origin, length)
                                       for origin, length in arcs)
    ) / grid
    return lower_hat, upper_hat


def _exhaust_small_finite_cases() -> tuple[bool, str]:
    """Exhaustively check finite formulas for n <= 4 and k <= 3."""
    for n in range(1, 5):
        masks = range(1 << n)
        full_mask = (1 << n) - 1
        for k in (2, 3):
            all_miss_sets: dict[tuple[int, ...], set[int]] = {}
            unique_sets: dict[tuple[tuple[int, ...], int], list[set[int]]] = {}
            for outcome in itertools.product(masks, repeat=k):
                counts = tuple(mask.bit_count() for mask in outcome)
                union_mask = 0
                for mask in outcome:
                    union_mask |= mask
                union_count = union_mask.bit_count()
                all_miss_sets.setdefault(counts, set()).add(n - union_count)
                key = (counts, union_count)
                if key not in unique_sets:
                    unique_sets[key] = [set() for _ in range(k)]
                for index, mask in enumerate(outcome):
                    others = 0
                    for other_index, other in enumerate(outcome):
                        if index != other_index:
                            others |= other
                    unique_sets[key][index].add((mask & ~others & full_mask).bit_count())

            for counts, seen in all_miss_sets.items():
                expected = set(integer_grid(list(counts), n))
                if seen != expected:
                    return False, f"all-miss grid mismatch n={n}, k={k}, counts={counts}"
            for (counts, union_count), per_guard in unique_sets.items():
                named = {f"g{index}": count for index, count in enumerate(counts)}
                bounds = unique_contribution_intervals(named, union_count)
                for index, seen in enumerate(per_guard):
                    lower, upper = bounds[f"g{index}"]
                    if seen != set(range(lower, upper + 1)):
                        return False, ("exclusive-coverage interval mismatch "
                                       f"n={n}, k={k}, counts={counts}, U={union_count}, "
                                       f"guard={index}")
    return True, "finite all-miss and exclusive-coverage formulas exhaustive for n<=4, k<=3"


def _test() -> int:
    failures = []

    def check(condition: bool, message: str) -> None:
        print(("ok    " if condition else "FAIL  ") + message)
        if not condition:
            failures.append(message)

    lower, upper = frechet_interval([0.5, 0.5])
    check((lower, upper) == (0.0, 0.5), "k=2, p=(.5,.5): identified set [0, .5]")

    lower, upper = frechet_interval([0.9, 0.9])
    check(abs(lower - 0.8) < 1e-12 and abs(identified_width([0.9, 0.9]) - 0.1) < 1e-12,
          "positive lower endpoint: p=(.9,.9) has [0.8, .9], width .1 (not min p)")

    for rates in ([0.3, 0.4, 0.5], [0.1, 0.9, 0.5, 0.2]):
        lower, upper = frechet_interval(rates)
        check(lower == 0.0 and abs(identified_width(rates) - min(rates)) < 1e-12,
              f"zero lower endpoint for {rates}: width equals min p only in this case")

    for rates in ([0.3, 0.4, 0.5], [0.9, 0.9, 0.9], [0.0, 0.4], [0.3, 1.0]):
        lower, upper = frechet_interval(rates)
        product = independence_plugin(rates)
        check(lower - 1e-12 <= product <= upper + 1e-12,
              f"independence product lies in the continuous set for {rates}")

    for rates in ([0.3, 0.4, 0.5], [0.9, 0.9], [0.9, 0.8, 0.75]):
        lower, upper = frechet_interval(rates)
        lower_hat, upper_hat = _realise_extremes(rates)
        check(abs(upper_hat - upper) < 1e-3,
              f"nested-event construction reaches upper endpoint {upper:.3f}")
        check(abs(lower_hat - lower) < 1e-3,
              f"circle-complement construction reaches lower endpoint {lower:.3f}")

    check(improvement_interval([0.3, 0.4, 0.5])[0] == 0.0,
          "non-degenerate marginals leave zero strict improvement compatible")
    check(improvement_interval([0.0, 0.4]) == (0.0, 0.0),
          "a singleton marginal set can rule strict improvement out")

    burden_lower, _ = burden_interval([0.14, 0.0, 0.16, 0.20, 0.0])
    check(burden_lower > 0,
          f"positive benign union-flag floor follows from marginals ({burden_lower:.0%})")

    finite_ok, finite_message = _exhaust_small_finite_cases()
    check(finite_ok, finite_message)

    grid = integer_grid([52, 5, 25, 70, 0], 82)
    check(grid[0] == 0 and grid[-1] == 12 and len(grid) == 13,
          "BELLS harmful stratum: exact finite all-miss set is {0/82 ... 12/82}")

    check(abs(collapse_from_union(73 / 82) - 9 / 82) < 1e-12,
          "one same-denominator union identifies static all-miss (1 - 73/82)")

    # The registry envelope must match the transformations computed here.
    try:
        expected = _expected_mc003()
    except Exception as exc:  # registry absent in a bare script copy
        print(f"note  MC-003 envelope not cross-checked ({exc})")
    else:
        bells = _expected()
        n, catches = bells["n_harmful"], bells["per_guard_catches"]
        finite_grid = integer_grid(list(catches.values()), n)
        rates = [(n - count) / n for count in catches.values()]
        flag_rates = [count / bells["n_benign"]
                      for count in bells["per_guard_benign_flags"].values()]
        exclusive_bounds = unique_contribution_intervals(catches, bells["union_detection"])
        zero_exclusive = sum(
            1 for guard in catches
            if bells["union_detection"] - bells["leave_one_out_union"][guard] == 0
        )
        got = {
            "identified_set_lower": finite_grid[0],
            "identified_set_upper": finite_grid[-1],
            "identified_set_size": len(finite_grid),
            "release_recomputed_all_miss": bells["all_miss"],
            "denominator": n,
            "benign_burden_floor_pct": round(burden_interval(flag_rates)[0] * 100),
            "improvement_floor_pct": round(improvement_interval(rates)[0] * 100),
            "members_zero_exclusive_full_stack_coverage": zero_exclusive,
            "aggregate_unique_contribution_bounds": {
                guard: list(bounds) for guard, bounds in exclusive_bounds.items()
            },
        }
        for key, want in expected.items():
            check(got.get(key) == want,
                  f"MC-003 expected {key}={want} matches ({got.get(key)})")

    if failures:
        print(f"\n{len(failures)} check(s) failed.")
        return 1
    print("\nIdentification arithmetic verified: sharp continuous and finite bounds, "
          "aggregate exclusive-coverage limits, and registered BELLS transforms.")
    return 0


# ------------------------------------------------------------- the one case

def _expected_mc003() -> dict:
    import pathlib

    import yaml
    root = pathlib.Path(__file__).resolve().parent.parent
    registry = yaml.safe_load((root / "claims.yaml").read_text())
    return next(claim for claim in registry["claims"]
                if claim["id"] == "MC-003")["expected"]


def _expected() -> dict:
    """Read MC-002's registered values.

    ``reanalyze_bells_subset.py`` separately downloads and hash-verifies the
    bound upstream file in CI, then re-computes these values. This script
    checks the identification transformations applied to that registered
    release-recomputed envelope; it does not fetch source data itself.
    """
    import pathlib

    import yaml
    root = pathlib.Path(__file__).resolve().parent.parent
    registry = yaml.safe_load((root / "claims.yaml").read_text())
    return next(claim for claim in registry["claims"]
                if claim["id"] == "MC-002")["expected"]


def _bells() -> int:
    expected = _expected()
    n = expected["n_harmful"]
    catches = expected["per_guard_catches"]
    miss_rates = {guard: (n - count) / n for guard, count in catches.items()}
    continuous_lower, continuous_upper = frechet_interval(list(miss_rates.values()))
    finite = integer_grid(list(catches.values()), n)
    release_recomputed = expected["all_miss"] / n
    product = independence_plugin(list(miss_rates.values()))
    best = min(miss_rates, key=miss_rates.get)
    union = expected["union_detection"]
    aggregate_bounds = unique_contribution_intervals(catches, union)

    print("BELLS 2025 misuse-detection subset — registered identification envelope")
    print("  Lineage: this view reads MC-002's registered release-recomputed counts.")
    print("  scripts/reanalyze_bells_subset.py is the separate hash-verified source")
    print("  reanalysis; this command does not download the vendor-verdict file.\n")
    print(f"  denominator: {n} prompts labelled harmful, of "
          f"{n + expected['n_benign'] + expected['n_borderline']} released")
    print(f"  ({expected['n_benign']} benign and {expected['n_borderline']} borderline "
          "are separate strata and are never folded in)\n")
    for guard, rate in sorted(miss_rates.items(), key=lambda pair: pair[1]):
        print(f"    {guard:<14} misses {n - catches[guard]:>2}/{n} = {rate:6.2%}")

    print("\n  --- what the harmful-stratum marginals alone identify ---")
    print(f"  continuous all-miss set     : [{continuous_lower:.2%}, {continuous_upper:.2%}]"
          f"   width {identified_width(list(miss_rates.values())):.2%}")
    if continuous_lower == 0:
        print(f"  in this case width == best  : {miss_rates[best]:.2%} ({best})")
    print(f"  finite all-miss count set   : {{{finite[0]}/{n} ... {finite[-1]}/{n}}}")
    print(f"  independence plug-in        : {product:.2%} "
          f"({product * n:.2f} expected prompts) under a model")
    print("  Marginals alone do not identify the realized static all-miss or test")
    print("  that model. A same-denominator union does identify static all-miss.")
    print(f"  registered release-recomputed: {expected['all_miss']}/{n} = {release_recomputed:.2%}")
    print(f"  from the registered union   : 1 - {union}/{n} = "
          f"{collapse_from_union(union / n):.2%}")

    improvement_lower, improvement_upper = improvement_interval(list(miss_rates.values()))
    benign_n = expected["n_benign"]
    flag_rates = [count / benign_n for count in expected["per_guard_benign_flags"].values()]
    burden_lower, burden_upper = burden_interval(flag_rates)
    release_benign_union = expected["benign_union_flagged"] / benign_n
    print("\n  --- static direction and benign burden ---")
    print(f"  benign union-flag set       : [{burden_lower:.2%}, {burden_upper:.2%}]")
    print(f"  registered benign union     : {release_benign_union:.2%}")
    print(f"  improvement over {best:<10}: [{improvement_lower:.2%}, {improvement_upper:.2%}]")
    print("  OR composition certifies non-degradation versus the best member; in")
    print("  this non-degenerate case, marginals do not identify strict benefit.")

    print("\n  --- what catch marginals plus the union still leave open ---")
    print("  aggregate-only bounds on exclusive full-stack coverage:")
    for guard, count in sorted(catches.items(), key=lambda pair: -pair[1]):
        lower, upper = aggregate_bounds[guard]
        print(f"    {guard:<14} {lower:>2} ... {upper:<2} of {n}")
    print("  These aggregates force LLM Guard's exclusive count to zero, but they")
    print("  do not identify the other guards' realized exclusive coverage.")
    print("\n  registered leave-one-out unions (exact under the static file semantics):")
    for guard, count in sorted(catches.items(), key=lambda pair: -pair[1]):
        without = expected["leave_one_out_union"][guard]
        print(f"    without {guard:<14} union {without:>2}/{n}   "
              f"exclusive full-stack coverage {union - without:>2}")
    zeros = [guard for guard in catches
             if union - expected["leave_one_out_union"][guard] == 0]
    print(f"\n  {len(zeros)} of {len(catches)} guards have zero exclusive full-stack")
    print(f"  coverage on this stratum: {', '.join(sorted(zeros))}.")

    print(f"\n  Scope: exactly these {n} author-selected prompts at vendors' released")
    print("  binary verdicts, in one stratum of one evaluation. This is a static")
    print("  counting result, not a population estimate, deployment-risk estimate,")
    print("  vendor ranking, or general law of guardrail dependence.")
    if "--json" in sys.argv:
        print(json.dumps({
            "continuous_interval": [continuous_lower, continuous_upper],
            "finite_all_miss_counts": finite,
            "release_recomputed_all_miss": release_recomputed,
            "independence_plugin": product,
            "benign_union_interval": [burden_lower, burden_upper],
            "improvement_interval": [improvement_lower, improvement_upper],
            "aggregate_unique_contribution_bounds": {
                guard: list(bounds) for guard, bounds in aggregate_bounds.items()
            },
        }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_bells() if "--bells" in sys.argv else _test())
