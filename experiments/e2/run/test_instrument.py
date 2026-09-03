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


# P10 — planted inversion: the marginal-best candidate overlaps the incumbent
#       almost entirely while a weaker candidate is disjoint; the selection
#       code must pick the weaker one on the joint, report the flip and the
#       exact known regret, and the independent calculator must agree — and
#       must refuse a corrupted primary.
def p10() -> None:
    from analyze import selection_independent, selection_stats
    n = 200
    catch = {f"i{k}": {"A": int(k < 120), "X": int(k < 130),
                       "Y": int(k >= 100), "Z": int(k < 50)} for k in range(n)}
    benign = {f"b{k}": {"A": 0, "X": 0, "Y": 0, "Z": 0} for k in range(20)}

    def table(guards: list) -> dict:
        return {"source": "synthetic", "label": "planted_inversion",
                "guards": guards,
                "catch": {i: {g: v[g] for g in guards} for i, v in catch.items()},
                "benign": {i: {g: v[g] for g in guards} for i, v in benign.items()},
                "operating_point": "synthetic", "event": "synthetic",
                "item_id_scheme": "synthetic", "locator": "synthetic",
                "prediction_pairs": None}
    t = table(["A", "X", "Y", "Z"])
    st = selection_stats(t)
    selection_independent(t, st)
    a = {r["incumbent"]: r for r in st["incumbents"]}["A"]
    caught = (a["marginal_choice"] == "X" and a["joint_choice"] == "Y"
              and a["flip"] and a["regret_items"] == 70
              and a["U_marg"] == 130 and a["U_joint"] == 200
              and a["ci95_items"][0] > 0)
    t2 = table(["A", "X", "Z"])            # remove the disjoint candidate
    st2 = selection_stats(t2)
    selection_independent(t2, st2)
    a2 = {r["incumbent"]: r for r in st2["incumbents"]}["A"]
    quiet = (not a2["flip"]) and a2["regret_items"] == 0
    st["incumbents"][0]["regret_items"] += 1        # corrupt the primary
    try:
        selection_independent(t, st)
        refused = False
    except AssertionError:
        refused = True
    if caught:
        print("planted inversion caught")
    check("P10 planted inversion caught (X marginal-best, Y joint-best, "
          "regret exactly 70/200, CI>0); no inversion reported without Y; "
          "independent calculator refuses a corrupted primary",
          caught and quiet and refused)


# P11 — Mantel–Haenszel stratified odds ratio is exact on a hand-built
#       two-stratum table (MH = 4.6), with the stratifier read from the
#       third guard's misses.
def p11() -> None:
    from analyze import mh_odds_ratio
    items: dict = {}

    def add(prefix: str, a11: int, a10: int, a01: int, a00: int, cmiss: int) -> None:
        for lbl, (ma, mb), cnt in (("11", (1, 1), a11), ("10", (1, 0), a10),
                                   ("01", (0, 1), a01), ("00", (0, 0), a00)):
            for k in range(cnt):
                items[f"{prefix}{lbl}{k}"] = {"a": 1 - ma, "b": 1 - mb, "c": 1 - cmiss}
    add("s1", 3, 1, 1, 5, 0)      # (3·5/10)/(1·1/10)
    add("s2", 2, 2, 2, 4, 1)      # (2·4/10)/(2·2/10)  →  (1.5+0.8)/(0.1+0.4) = 4.6
    crude, mh, k = mh_odds_ratio(items, sorted(items), "a", "b", ["c"])
    pooled = ((5 + 0.5) * (9 + 0.5)) / ((3 + 0.5) * (3 + 0.5))
    check("P11 MH stratified OR exact (4.6) on a hand-built two-stratum "
          "table; crude Haldane OR matches the pooled table",
          abs(mh - 4.6) < 1e-12 and k == 2 and abs(crude - pooled) < 1e-12,
          f"mh {mh:.6f} crude {crude:.6f}")


def main() -> int:
    for f in (p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11):
        f()
    if failures:
        print(f"{len(failures)} property/properties failed.")
        return 1
    print("Instrument proven: every property held and every planted "
          "violation was caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
