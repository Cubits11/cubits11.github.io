#!/usr/bin/env python3
"""Adversarial proof battery for the E2 instrument — every property is
proven by breaking it, in the house mutation-fixture style: a control
that cannot fail when its property is violated is decoration.

Runs anywhere (stdlib only, seeded, no network, no model, no frozen
item). Exit 0 means every property held AND every planted violation was
caught.
"""
from __future__ import annotations

import hashlib
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import delta, delta_independent, wilson  # noqa: E402
from calibrate import FPR_TARGET, sweep  # noqa: E402

GUARDS = ("lg4", "lg3", "sg2b")
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok    " if ok else "FAIL  ") + name + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def rng_for(tag: str) -> random.Random:
    return random.Random(hashlib.sha256(tag.encode()).hexdigest())


def planted(n: int, share: float, tag: str) -> dict:
    """Items with a shared latent difficulty: dependence by construction."""
    r = rng_for(tag)
    cc = {}
    for i in range(n):
        latent = r.random()
        cc[f"i{i}"] = {g: int((share * latent + (1 - share) * r.random()) > 0.6)
                       for g in GUARDS}
    return cc


def independent(n: int, p: float, tag: str) -> dict:
    r = rng_for(tag)
    return {f"i{i}": {g: int(r.random() < p) for g in GUARDS}
            for i in range(n)}


def perm_band(cc: dict, a: str, b: str, k: int = 300) -> tuple[float, float]:
    r = rng_for(f"band:{a}:{b}:{len(cc)}")
    pa = sum(v[a] for v in cc.values()) / len(cc)
    pb = sum(v[b] for v in cc.values()) / len(cc)
    bvals = [v[b] for v in cc.values()]
    out = []
    for _ in range(k):
        s = bvals[:]
        r.shuffle(s)
        p11 = sum(x & y for x, y in zip((v[a] for v in cc.values()), s)) / len(cc)
        out.append(p11 - pa * pb)
    out.sort()
    return out[int(0.025 * k)], out[int(0.975 * k) - 1]


# P1 — sweep is nearest-not-exceeding, proven across 50 seeded score sets
def p1() -> None:
    good = True
    for t in range(50):
        r = rng_for(f"p1:{t}")
        scores = {f"i{i}": r.random() for i in range(400)}
        res = sweep(scores)
        n = len(scores)
        fpr = sum(1 for s in scores.values() if s >= res["threshold"]) / n
        good &= abs(fpr - res["achieved_fpr"]) < 1e-12 and fpr <= FPR_TARGET
        lower = sorted({s for s in scores.values() if s < res["threshold"]},
                       reverse=True)
        if lower:
            fpr_next = sum(1 for s in scores.values() if s >= lower[0]) / n
            good &= fpr_next > FPR_TARGET
    check("P1 sweep: achieved FPR <= target and one step lower overshoots",
          good)


# P2 — planted dependence detected; destroying it collapses Delta into band
def p2() -> None:
    cc = planted(800, 0.85, "p2")
    d, *_ = delta(cc, "lg4", "lg3")
    lo, hi = perm_band(cc, "lg4", "lg3")
    detected = d > hi
    r = rng_for("p2:destroy")
    bvals = [v["lg3"] for v in cc.values()]
    r.shuffle(bvals)
    broken = {i: {**v, "lg3": bvals[k]}
              for k, (i, v) in enumerate(cc.items())}
    d2, *_ = delta(broken, "lg4", "lg3")
    lo2, hi2 = perm_band(broken, "lg4", "lg3")
    collapsed = lo2 <= d2 <= hi2
    check("P2 permutation: planted dependence outside band; destroyed "
          "dependence inside", detected and collapsed,
          f"planted {d:+.4f} > {hi:+.4f}; destroyed {d2:+.4f}")


# P3 — duplicate-column equals p(1-p); misalignment collapses it
def p3() -> None:
    cc = planted(800, 0.85, "p3")
    p = sum(v["lg4"] for v in cc.values()) / len(cc)
    d_self, *_ = delta(cc, "lg4", "lg4")
    exact = abs(d_self - p * (1 - p)) < 1e-12
    ids = list(cc)
    r = rng_for("p3:misalign")
    shuffled = ids[:]
    r.shuffle(shuffled)
    misaligned = {i: {**cc[i], "dup": cc[shuffled[k]]["lg4"]}
                  for k, i in enumerate(ids)}
    n = len(ids)
    p11 = sum(v["lg4"] & v["dup"] for v in misaligned.values()) / n
    d_mis = p11 - p * p
    check("P3 duplicate-column: exact p(1-p) when aligned; collapses "
          "under planted row misalignment",
          exact and d_mis < 0.5 * p * (1 - p),
          f"aligned {d_self:.4f} vs misaligned {d_mis:.4f}")


# P4 — independent calculator agrees on 100 random tables and catches a
#      corrupted primary
def p4() -> None:
    agree = all(
        abs(delta(t, "lg4", "lg3")[0] - delta_independent(t, "lg4", "lg3"))
        < 1e-12
        for t in (independent(300, rng_for(f"p4:{k}").random(), f"p4t:{k}")
                  for k in range(100)))
    t = planted(300, 0.8, "p4:corrupt")
    corrupted = delta(t, "lg4", "lg3")[0] + 0.01
    caught = abs(corrupted - delta_independent(t, "lg4", "lg3")) > 1e-6
    check("P4 independent calculator: agrees to 1e-12 on 100 tables and "
          "flags a corrupted primary", agree and caught)


# P5 — Frechet set always contains the observed all-event count, and both
#      endpoints are achieved by explicit couplings
def p5() -> None:
    contained = True
    for k in range(200):
        t = independent(150, 0.2 + 0.6 * rng_for(f"p5:{k}").random(), f"p5t:{k}")
        n = len(t)
        catches = {g: n - sum(v[g] for v in t.values()) for g in GUARDS}
        allev = sum(all(v[g] for g in GUARDS) for v in t.values())
        lo = max(0, n - sum(catches.values()))
        hi = n - max(catches.values())
        contained &= lo <= allev <= hi
    n = 100
    events = {g: 30 for g in GUARDS}
    nested = {f"i{i}": {g: int(i < events[g]) for g in GUARDS}
              for i in range(n)}   # comonotone: all-event = min events = 30
    hi_ok = sum(all(v[g] for g in GUARDS) for v in nested.values()) == 30
    spread = {f"i{i}": {"lg4": int(i < 30), "lg3": int(30 <= i < 60),
                        "sg2b": int(60 <= i < 90)} for i in range(n)}
    lo_ok = sum(all(v[g] for g in GUARDS) for v in spread.values()) == 0
    check("P5 Frechet: 200 random tables inside the set; both endpoints "
          "achieved by explicit couplings", contained and hi_ok and lo_ok)


# P6 — missingness bounds: the REAL analyze.py function must (a) bracket
#      the full-data Delta under cell-level masking, and (b) be EXACT —
#      equal to brute-force enumeration of every completion on small
#      cases. The 2026-09-01 uniform-fill version failed (a) here and was
#      replaced; this test now guards the replacement.
def p6() -> None:
    from itertools import product

    from analyze import missingness_delta_bounds

    good = True
    for k in range(100):
        full = planted(400, 0.8, f"p6:{k}")
        r = rng_for(f"p6mask:{k}")
        masked = {}
        for i, v in full.items():
            kept = {g: bit for g, bit in v.items() if r.random() >= 0.05}
            masked[i] = kept
        d_true = delta(full, "lg4", "lg3")[0]
        lo, hi = missingness_delta_bounds(masked, "lg4", "lg3")
        good &= lo - 1e-12 <= d_true <= hi + 1e-12
    exact = True
    for k in range(20):
        r = rng_for(f"p6exact:{k}")
        items = {}
        free = []
        for i in range(10):
            v = {}
            for g in ("lg4", "lg3"):
                if r.random() < 0.25:
                    free.append((f"i{i}", g))
                else:
                    v[g] = int(r.random() < 0.5)
            items[f"i{i}"] = v
        lo, hi = missingness_delta_bounds(items, "lg4", "lg3")
        vals = []
        for fill in product((0, 1), repeat=len(free)):
            ext = {i: dict(v) for i, v in items.items()}
            for (iid, g), bit in zip(free, fill):
                ext[iid][g] = bit
            vals.append(delta(ext, "lg4", "lg3")[0])
        exact &= (abs(min(vals) - lo) < 1e-12 and abs(max(vals) - hi) < 1e-12)
    check("P6 missingness bounds: bracket full-data Delta in 100 "
          "cell-masked trials AND match brute-force enumeration exactly "
          "on 20 small cases", good and exact)


# P7 — Wilson interval: ~95% coverage at p=0.1, n=800; sane edges
def p7() -> None:
    hits = 0
    trials = 1000
    for k in range(trials):
        r = rng_for(f"p7:{k}")
        c = sum(1 for _ in range(800) if r.random() < 0.1)
        lo, hi = wilson(c, 800)
        hits += lo <= 0.1 <= hi
    cov = hits / trials
    lo0, _ = wilson(0, 800)
    check("P7 Wilson: coverage in [0.93, 0.97] at p=0.1 n=800; zero-count "
          "lower bound is 0", 0.93 <= cov <= 0.97 and lo0 == 0.0,
          f"coverage {cov:.3f}")


# P8 — h.miss.v1 stratum semantics: harmful miss vs benign flag
def p8() -> None:
    import json
    from io import StringIO

    from collect import emit_row
    buf = StringIO()
    emit_row(buf, run_id="t", item={"id": "a", "stratum": "harmful"},
             guard="lg3", replicate=1, score=0.99, threshold=0.5,
             status="observed", code="observed", synthetic=True)
    emit_row(buf, run_id="t", item={"id": "b", "stratum": "benign_eval"},
             guard="lg3", replicate=1, score=0.99, threshold=0.5,
             status="observed", code="observed", synthetic=True)
    r1, r2 = (json.loads(x) for x in buf.getvalue().strip().splitlines())
    check("P8 h.miss.v1: flagged harmful item is NOT a miss (0); flagged "
          "benign item IS a flag (1)",
          r1["normalized_outcome"] == 0 and r2["normalized_outcome"] == 1)


# P9 — the planted-zero world: near-independent data yields Delta inside
#      the band on every pair (no hallucinated dependence)
def p9() -> None:
    cc = independent(800, 0.3, "p9")
    ok = True
    for a, b in (("lg4", "lg3"), ("lg4", "sg2b"), ("lg3", "sg2b")):
        d, *_ = delta(cc, a, b)
        lo, hi = perm_band(cc, a, b)
        ok &= lo <= d <= hi
    check("P9 null world: independent generator yields Delta inside the "
          "permutation band on all three pairs", ok)


def main() -> int:
    for f in (p1, p2, p3, p4, p5, p6, p7, p8, p9):
        f()
    if failures:
        print(f"{len(failures)} property/properties failed.")
        return 1
    print("Instrument proven: every property held and every planted "
          "violation was caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
