#!/usr/bin/env python3
"""What a published subgroup difference leaves undetermined.

A report states an overall prevalence r for some behaviour, and a
difference d between two subgroups — but not the subgroups' relative
sizes. The subgroup rates are then not identified. Writing s for the
unknown share of the first subgroup,

    r = s·a + (1−s)·b  and  d = a − b   ⟹   a = r + (1−s)·d,  b = r − s·d

so a and b each sweep an interval as s ranges over the feasible shares,
and so does the ratio a/b — the quantity a reader actually wants, because
a difference of 3.7 percentage points means something very different on a
base of 8.7% than on a base of 51%.

This is the same discipline as scripts/identification.py in a much
smaller setting: publish what the numbers pin down, publish the width of
what they do not, and never quote a point where an interval is what the
evidence supports.

Applied here to Anthropic's AI Fluency Index summary, which reports
overall prevalences for eleven observable behaviours and percentage-point
differences for conversations that produced an artifact. The summary does
not state the artifact share — and does not state whether the differences
are against non-artifact conversations or against the overall rate, so
this file computes BOTH readings and reports what holds under either.

    python3 scripts/mixture_bounds.py --test
    python3 scripts/mixture_bounds.py --fluency
"""

import math
import sys


def subgroup_intervals(overall: float, diff: float) -> dict:
    """Identified sets for the two subgroup rates and their ratio, given
    an overall rate and a between-subgroup difference but no share.

    Reading A: ``diff`` is (first subgroup − second subgroup) and
    ``overall`` is the pooled rate. The share s is unknown, so each
    quantity sweeps an interval.
    """
    if not 0.0 <= overall <= 1.0:
        raise ValueError("overall rate is not a probability")
    if not -1.0 <= diff <= 1.0:
        raise ValueError("difference is not on the probability scale")
    lo_s, hi_s = _feasible_shares(overall, diff)
    if lo_s is None:
        raise ValueError("no share makes both subgroup rates probabilities")
    ends = []
    for s in (lo_s, hi_s):
        a, b = overall + (1 - s) * diff, overall - s * diff
        ends.append((a, b, (a / b) if b > 0 else None))
    a_lo, a_hi = sorted(e[0] for e in ends)
    b_lo, b_hi = sorted(e[1] for e in ends)
    ratios = [e[2] for e in ends if e[2] is not None]
    return {"a": (a_lo, a_hi), "b": (b_lo, b_hi),
            "ratio": (min(ratios), max(ratios)) if len(ratios) == 2 else None,
            "shares": (lo_s, hi_s)}


def _feasible_shares(overall: float, diff: float) -> tuple:
    """Shares s for which both a = r+(1−s)d and b = r−s·d are probabilities.
    Both are affine in s, so the feasible set is an interval and its
    endpoints suffice."""
    lo, hi = 0.0, 1.0
    for coef, const in ((-diff, overall + diff), (diff, overall)):
        # value(s) = const + coef*s must lie in [0, 1]
        if abs(coef) < 1e-15:
            if not -1e-12 <= const <= 1 + 1e-12:
                return None, None
            continue
        b1, b2 = (0 - const) / coef, (1 - const) / coef
        lo, hi = max(lo, min(b1, b2)), min(hi, max(b1, b2))
    return (lo, hi) if lo <= hi + 1e-12 else (None, None)


def point_reading(overall: float, diff: float) -> dict:
    """Reading B: ``diff`` is stated against the overall rate itself, so
    the subgroup rate is a point and no share is needed."""
    a = overall + diff
    return {"a": a, "b": overall, "ratio": (a / overall) if overall else None}


def robust_ratio(overall: float, diff: float) -> tuple:
    """What holds under BOTH readings: the union of the two identified
    sets. A statement true here needs no assumption about which
    comparison the report meant, and none about the share."""
    iv = subgroup_intervals(overall, diff)["ratio"]
    pt = point_reading(overall, diff)["ratio"]
    if iv is None or pt is None:
        return None
    return min(iv[0], pt), max(iv[1], pt)


# --------------------------------------------------------------- self-tests

def _test() -> int:
    failures = []

    def check(cond, msg):
        print(("ok    " if cond else "FAIL  ") + msg)
        if not cond:
            failures.append(msg)

    # Closed form must agree with a brute-force sweep over feasible shares.
    for r, d in ((0.087, -0.037), (0.511, 0.147), (0.203, -0.052),
                 (0.300, 0.145), (0.158, -0.031), (0.411, 0.134)):
        iv = subgroup_intervals(r, d)
        aa, bb, rr = [], [], []
        for i in range(20001):
            s = i / 20000
            a, b = r + (1 - s) * d, r - s * d
            if -1e-12 <= a <= 1 + 1e-12 and -1e-12 <= b <= 1 + 1e-12:
                aa.append(a); bb.append(b)
                if b > 0:
                    rr.append(a / b)
        check(abs(min(aa) - iv["a"][0]) < 1e-6 and abs(max(aa) - iv["a"][1]) < 1e-6,
              f"r={r}, d={d}: subgroup interval matches a sweep "
              f"[{iv['a'][0]:.4f}, {iv['a'][1]:.4f}]")
        check(abs(min(rr) - iv["ratio"][0]) < 1e-6
              and abs(max(rr) - iv["ratio"][1]) < 1e-6,
              f"r={r}, d={d}: ratio interval matches a sweep "
              f"[{iv['ratio'][0]:.4f}, {iv['ratio'][1]:.4f}]")

    # A zero difference identifies both subgroups at the overall rate.
    iv = subgroup_intervals(0.4, 0.0)
    check(iv["a"] == (0.4, 0.4) and iv["ratio"] == (1.0, 1.0),
          "a zero difference leaves nothing undetermined")

    # The overall rate always lies between the two subgroup rates.
    for r, d in ((0.087, -0.037), (0.511, 0.147)):
        iv = subgroup_intervals(r, d)
        check(iv["a"][0] <= r <= iv["a"][1] and iv["b"][0] <= r <= iv["b"][1],
              f"r={r} lies inside both subgroup intervals — a pooled rate is "
              "a mixture, never outside its parts")

    # The point reading is one endpoint of the interval reading, so the
    # robust set is the interval reading. This is why the union is cheap.
    for r, d in ((0.087, -0.037), (0.203, -0.052)):
        iv = subgroup_intervals(r, d)["ratio"]
        pt = point_reading(r, d)["ratio"]
        check(abs(pt - iv[0]) < 1e-9,
              f"r={r}: the against-overall reading sits at the interval's "
              f"low end ({pt:.4f}), so the robust claim is the interval")

    # Infeasible input must raise, not silently return a nonsense interval.
    try:
        subgroup_intervals(0.02, -0.30)
        check(False, "an impossible (rate, difference) pair must raise")
    except ValueError:
        check(True, "an impossible (rate, difference) pair raises")

    # AF-001's envelope must match what this file computes, or the claim is
    # decoration. Same discipline as MC-001/MC-002/MC-003.
    try:
        import pathlib

        import yaml
        root = pathlib.Path(__file__).resolve().parent.parent
        registry = yaml.safe_load((root / "claims.yaml").read_text())
        exp = next(c for c in registry["claims"]
                   if c["id"] == "AF-001")["expected"]
    except Exception as exc:
        print(f"note  AF-001 envelope not cross-checked ({exc})")
    else:
        r = exp["checks_facts_overall_pct"] / 100
        d = exp["checks_facts_artifact_diff_pp"] / 100
        lo, hi = robust_ratio(r, d)
        # A bound is never rounded in the direction that strengthens it:
        # the floor rounds DOWN, the ceiling rounds UP. The exact values
        # here are 29.84% and 42.53%; reporting "30%" would claim slightly
        # more than the arithmetic supports.
        got = {
            "checks_facts_reduction_min_pct": math.floor((1 - hi) * 100),
            "checks_facts_reduction_max_pct": math.ceil((1 - lo) * 100),
            "behaviours_rising": sum(1 for _, _, dd in FLUENCY if dd > 0),
            "behaviours_falling": sum(1 for _, _, dd in FLUENCY if dd < 0),
        }
        for key, want in got.items():
            check(exp[key] == want,
                  f"AF-001 expected {key}={exp[key]} matches the computation "
                  f"({want})")
        check(any(abs(row[1] - r) < 1e-9 and abs(row[2] - d) < 1e-9
                  for row in FLUENCY),
              "AF-001's transcribed figures are the ones this file computes on")

    if failures:
        print(f"\n{len(failures)} check(s) failed.")
        return 1
    print("\nMixture bounds verified: closed form matches the sweep, pooled "
          "rate interior,\nthe against-overall reading is an endpoint, "
          "infeasible inputs refused.")
    return 0


# ------------------------------------------------------------ the one table

FLUENCY = [
    ("clarifies goal", 0.511, 0.147),
    ("provides examples", 0.411, 0.134),
    ("specifies format", 0.300, 0.145),
    ("identifies missing context", 0.203, -0.052),
    ("questions reasoning", 0.158, -0.031),
    ("checks facts", 0.087, -0.037),
]


def _fluency() -> int:
    print("AI Fluency Index — what the published summary leaves undetermined")
    print("  source: academy.claude.com/tutorials/the-ai-fluency-index")
    print("  9,830 multi-turn Claude.ai conversations, 7-day window, "
          "January 2026")
    print("  11 of the framework's 24 behaviours are directly observable\n")
    print(f"  {'behaviour':<28}{'overall':>9}{'diff':>8}"
          f"{'artifact rate':>18}{'relative':>16}")
    for name, r, d in FLUENCY:
        iv = subgroup_intervals(r, d)
        rr = robust_ratio(r, d)
        print(f"  {name:<28}{r:>8.1%}{d:>+8.1%}"
              f"   [{iv['a'][0]:5.1%}, {iv['a'][1]:5.1%}]"
              f"   [{rr[0]:5.2f}, {rr[1]:5.2f}]")

    r, d = 0.087, -0.037
    rr = robust_ratio(r, d)
    lo_pct, hi_pct = math.floor((1 - rr[1]) * 100), math.ceil((1 - rr[0]) * 100)
    print(f"\n  The headline the summary does not print. A 3.7-point drop on a "
          f"base of\n  8.7% is not a small effect: fact-checking is between "
          f"{lo_pct}% and {hi_pct}% less\n  prevalent in artifact "
          f"conversations — under either reading of the\n  comparison group, "
          f"and for every possible artifact share.\n  (Exact: "
          f"{(1 - rr[1]):.2%} to {(1 - rr[0]):.2%}; a bound is never rounded "
          f"in the\n  direction that strengthens it.)")

    ups = [n for n, _, dd in FLUENCY if dd > 0]
    downs = [n for n, _, dd in FLUENCY if dd < 0]
    print(f"\n  Direction: the three behaviours that rise ({', '.join(ups)})\n"
          f"  are Description. The three that fall ({', '.join(downs)})\n"
          f"  are Discernment. Artifacts shift effort from evaluating to "
          f"directing.")

    print("\n  What this does NOT establish. The report states the findings "
          "are\n  correlational, and states that users may perform fluency "
          "behaviours\n  mentally without expressing them conversationally. So "
          "a fall in\n  transcript-visible checking cannot be distinguished "
          "from checking that\n  moved off-platform — which is exactly where "
          "checking an artifact goes:\n  into an editor, a test run, a "
          "browser. The measured evaluation gap is\n  confounded with a "
          "measurement gap, and the published marginals cannot\n  separate "
          "them.")
    return 0


if __name__ == "__main__":
    sys.exit(_fluency() if "--fluency" in sys.argv else _test())
