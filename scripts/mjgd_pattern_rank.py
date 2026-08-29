#!/usr/bin/env python3
"""Rank of the frozen MJGD v1 *public* linear map y = A_K c.

This is a theorem-check, not a new disclosure standard and not MJGD v2.

Frozen family (what validate_mjgd actually *reports* for complete static
evidence — schema positiveMetrics / _positive_metrics — plus N):

    N                      = 1^T c     (population.positive_denominator;
                                        also mjgd_reference denominator)
    per_system_catches[i]  = sum_{s : s_i=1} c_s
    union_detection        = sum_{s : s != 0} c_s
    all_miss               = c_0
    ordered_prefix_unions[j] = sum_{s : some bit in 0..j is 1} c_s
    leave_one_out_unions[i]  = sum_{s : some bit != i is 1} c_s

Bit convention (packet string keys, _table_from_patterns):
    pattern[i] == '1'  <=>  execution.order[i] flagged.
Kernel integer masks (mjgd_reference._reduce):
    (mask >> i) & 1    <=>  order[i] flagged.
These are the same assignment written MSB-left vs LSB-first.

NOT in the public packet, therefore NOT rows of A_K:
    residual_coverage, pairwise  (emitted by mjgd_reference._reduce;
                                  dropped by validate_mjgd._static_metrics)
    benign union                 (not a functional of the *positive* table)

N is disclosed (required field) and reconstructible as 1^T c. It is a row
of A_K so we do not hide it. Rank is unchanged if that row is dropped,
because union + all_miss = N.

stdlib only. Integer Gaussian elimination over Q.
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import mjgd_reference  # noqa: E402


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a) if a else 0


def string_patterns(k: int) -> list[str]:
    return [format(s, f"0{k}b") for s in range(1 << k)]


def string_to_kernel_mask(pattern: str) -> int:
    """MSB-left packet key -> LSB-first kernel mask. Bit i = order[i] both ways."""
    mask = 0
    for i, bit in enumerate(pattern):
        if bit == "1":
            mask |= 1 << i
    return mask


def public_from_string_counts(counts: dict[str, int], order: list[str]) -> dict:
    """The linear maps of the frozen public packet fields.

    Identical to expanding via validate_mjgd._table_from_patterns and then
    reading _static_metrics, and identical to projecting _reduce, for these
    fields. Residuals/pairwise are not returned.
    """
    width = len(order)
    per_system = {
        name: sum(c for p, c in counts.items() if p[i] == "1")
        for i, name in enumerate(order)
    }
    union = sum(c for p, c in counts.items() if "1" in p)
    prefixes = [
        sum(c for p, c in counts.items() if "1" in p[: j + 1])
        for j in range(width)
    ]
    leave_one_out = {
        name: sum(
            c for p, c in counts.items()
            if any(bit == "1" for pos, bit in enumerate(p) if pos != i)
        )
        for i, name in enumerate(order)
    }
    n = sum(counts.values())
    return {
        "N": n,
        "per_system_catches": per_system,
        "union_detection": union,
        "all_miss": counts.get("0" * width, 0),
        "ordered_prefix_unions": prefixes,
        "leave_one_out_unions": leave_one_out,
    }


def y_vector(counts: dict[str, int], k: int) -> tuple:
    order = [f"g{i}" for i in range(k)]
    m = public_from_string_counts(counts, order)
    y = [m["N"]]
    y.extend(m["per_system_catches"][n] for n in order)
    y.append(m["union_detection"])
    y.append(m["all_miss"])
    y.extend(m["ordered_prefix_unions"])
    y.extend(m["leave_one_out_unions"][n] for n in order)
    return tuple(y)


def build_A(k: int) -> list[list[int]]:
    keys = string_patterns(k)
    cols = len(keys)
    A = None
    for j, key in enumerate(keys):
        counts = {k_: 0 for k_ in keys}
        counts[key] = 1
        y = y_vector(counts, k)
        if A is None:
            A = [[] for _ in y]
        for r, val in enumerate(y):
            A[r].append(val)
    return A


def rref_rank_null(A: list[list[int]]):
    m, n = len(A), len(A[0])
    M = [[Fraction(A[i][j]) for j in range(n)] for i in range(m)]
    pivots = []
    row = 0
    for col in range(n):
        pivot = None
        for i in range(row, m):
            if M[i][col] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        M[row], M[pivot] = M[pivot], M[row]
        div = M[row][col]
        M[row] = [x / div for x in M[row]]
        for i in range(m):
            if i != row and M[i][col] != 0:
                factor = M[i][col]
                M[i] = [a - factor * b for a, b in zip(M[i], M[row])]
        pivots.append(col)
        row += 1
        if row == m:
            break
    free = [j for j in range(n) if j not in set(pivots)]
    basis = []
    for f in free:
        vec = [Fraction(0)] * n
        vec[f] = Fraction(1)
        for i, p in enumerate(pivots):
            vec[p] = -M[i][f]
        den = 1
        for x in vec:
            den = den * x.denominator // gcd(den, x.denominator)
        iv = [int(x * den) for x in vec]
        g = 0
        for v in iv:
            g = gcd(g, abs(v))
        if g > 1:
            iv = [v // g for v in iv]
        basis.append(iv)
    return len(pivots), basis


def four_cycle(k: int):
    """Nonneg integer c != c', same N, same public y. Requires K>=4.

    Interpretable: two items. Pairing {g0,g2} and {g1,g3} versus
    pairing {g0,g3} and {g1,g2}. Same singletons, same nested prefixes
    of the declared order, same leave-one-out unions. Different 2-bit
    cells, so the 2^K table is not identified.
    """
    if k < 4:
        return None
    keys = string_patterns(k)

    def pat(*idx: int) -> str:
        s = ["0"] * k
        for i in idx:
            s[i] = "1"
        return "".join(s)

    def vec(*pairs: str) -> dict[str, int]:
        counts = {key: 0 for key in keys}
        for p in pairs:
            counts[p] = 1
        return counts

    return vec(pat(0, 2), pat(1, 3)), vec(pat(0, 3), pat(1, 2))


def kernel_reduce(counts: dict[str, int], k: int) -> dict:
    order = [f"g{i}" for i in range(k)]
    patterns = {}
    for p, c in counts.items():
        if c:
            patterns[string_to_kernel_mask(p)] = c
    return mjgd_reference.joint_disclosure_from_patterns(patterns, order)


def public_from_kernel(reduced: dict, k: int) -> tuple:
    order = [f"g{i}" for i in range(k)]
    prefixes = []
    total = 0
    for row in reduced["residual_coverage"]:
        total += row["catches_among_prior_misses"]
        prefixes.append(total)
    loo = {
        row["guard"]: row["union_without"]
        for row in reduced["leave_one_out"]
    }
    y = [reduced["denominator"]]
    y.extend(reduced["per_guard"][n] for n in order)
    y.append(reduced["union_detection"])
    y.append(reduced["all_miss"])
    y.extend(prefixes)
    y.extend(loo[n] for n in order)
    return tuple(y)


def main() -> int:
    failures = []

    def check(cond: bool, msg: str) -> None:
        print(("ok    " if cond else "FAIL  ") + msg)
        if not cond:
            failures.append(msg)

    print("Frozen public map: N + packet positiveMetrics")
    print("Kernel: mjgd_reference.joint_disclosure_from_patterns")
    print()
    print(f"{'K':>3} {'2^K':>5} {'rows':>5} {'rank':>5} {'null':>5} {'id?':>4}")
    ranks = {}
    for k in range(1, 6):
        A = build_A(k)
        rank, basis = rref_rank_null(A)
        cols = 1 << k
        null = cols - rank
        ranks[k] = (rank, null, basis)
        print(f"{k:3d} {cols:5d} {len(A):5d} {rank:5d} {null:5d} "
              f"{'yes' if null == 0 else 'no':>4}")
        if k >= 3:
            check(rank == min(cols, 3 * k - 1),
                  f"K={k}: rank {rank} == min(2^K, 3K-1)={min(cols, 3*k-1)}")
        else:
            check(rank == cols, f"K={k}: full column rank {cols}")

    # Identities among rows: rank <= 3K-1 for K>=3.
    check(ranks[4][0] == 11 and ranks[4][1] == 5, "K=4: rank 11, nullity 5")
    check(ranks[5][0] == 14 and ranks[5][1] == 18, "K=5: rank 14, nullity 18")

    # Sufficiency: every kernel output is a function of c.
    for k in (2, 3, 4, 5):
        keys = string_patterns(k)
        counts = {key: (i * 3 + 7) % 5 for i, key in enumerate(keys)}
        counts["0" * k] = max(counts["0" * k], 1)
        reduced = kernel_reduce(counts, k)
        y_pub = y_vector(counts, k)
        y_ker = public_from_kernel(reduced, k)
        check(y_pub == y_ker,
              f"K={k}: public y from linear maps equals kernel projection")
        check(reduced["denominator"] == sum(counts.values()),
              f"K={k}: N = 1^T c")
        # Pairwise and residual are also functions of c (kernel computes them).
        check("pairwise" in reduced and "residual_coverage" in reduced,
              f"K={k}: kernel still emits residual and pairwise internally")

    # 2^K is sufficient for ALL kernel outputs, including residual/pairwise.
    # Non-minimality is for the *public packet* projection.
    for k in (4, 5):
        c, cp = four_cycle(k)
        check(c != cp and sum(c.values()) == sum(cp.values()),
              f"K={k}: counterexample vectors differ, same N")
        check(y_vector(c, k) == y_vector(cp, k),
              f"K={k}: public A_K c = A_K c'")
        rc, rp = kernel_reduce(c, k), kernel_reduce(cp, k)
        check(public_from_kernel(rc, k) == public_from_kernel(rp, k),
              f"K={k}: kernel-projected public fields agree")
        # Pairwise must *differ* — otherwise we would have claimed a kernel
        # vector of a larger map than the public contract.
        check(rc["pairwise"] != rp["pairwise"],
              f"K={k}: kernel pairwise distinguishes the pair (not public)")
        keys = string_patterns(k)
        nz_c = {p: c[p] for p in keys if c[p]}
        nz_p = {p: cp[p] for p in keys if cp[p]}
        print(f"      counterexample K={k}: c={nz_c}  c'={nz_p}  N={sum(c.values())}")

    # Fixture: partial-release.json string table.
    fixture = {"00": 2, "01": 2, "10": 3, "11": 3}
    got = public_from_string_counts(fixture, ["a", "b"])
    check(got["per_system_catches"] == {"a": 6, "b": 5}, "fixture catches")
    check(got["union_detection"] == 8 and got["all_miss"] == 2, "fixture union/all-miss")
    check(got["ordered_prefix_unions"] == [6, 8], "fixture prefixes")
    check(got["leave_one_out_unions"] == {"a": 5, "b": 6}, "fixture loo")

    print()
    if failures:
        print(f"{len(failures)} pattern-rank check(s) failed.")
        return 1
    print("Pattern-rank verified: 2^K is a sufficient statistic for every "
          "kernel output; the public packet map has rank min(2^K, 3K-1) for "
          "K>=3 (full for K<=3); K>=4 is not identifiable, with an explicit "
          "nonneg integer counterexample. Pairwise is kernel-internal, not "
          "in the public packet, and is what distinguishes the counterexample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
