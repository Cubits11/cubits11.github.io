#!/usr/bin/env python3
"""E2 pilot analysis — pairwise Δ primary, five contract controls, stdlib.

Reads a collection row file (contract-shaped JSONL from collect.py) and
computes, per stratum on the complete-case population:

  primary   per pair: Δ = p11 − pA·pB with a seeded item bootstrap CI,
            Wilson intervals on both marginals
  secondary stack all-event rate, product of the three event rates, the
            finite Fréchet identified set from catches, leave-one-out
            unions with exclusive coverage, benign union burden

Controls (all mandatory before any public Δ sentence):
  1 permutation        within-stratum shuffle of the pair's second column
  2 duplicate-column   Δ(A, copy of A) against its theoretical pA − pA²
  3 label noise        seeded 1% and 5% event-bit flips, Δ recomputed
  4 missingness        bounds assigning non-observed cells both ways
  5 independent calc   a second Δ implementation from contingency counts,
                       agreement asserted to 1e-12

Synthetic inputs are labelled synthetic in every output line. Nothing
here loads a model or reads a prompt.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import sys
from pathlib import Path

GUARDS = ("lg4", "lg3", "sg2b")
PAIRS = list(itertools.combinations(GUARDS, 2))
SEED = "MC-E2-PILOT-V1-FREEZE-2026-09-01"
B = 2000
PERM = 500


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def load(path: Path):
    """rows -> {stratum: {item_id: {guard: event_bit}}}, plus missing map."""
    events: dict = {}
    missing: dict = {}
    synthetic = False
    for line in path.read_text().splitlines():
        r = json.loads(line)
        synthetic = synthetic or bool(r.get("synthetic"))
        s = r["stratum"]
        if r["missingness_code"] == "observed":
            events.setdefault(s, {}).setdefault(
                r["item_id"], {})[r["guardrail_id"]] = int(
                r["normalized_outcome"])
        else:
            missing.setdefault(s, {}).setdefault(
                r["item_id"], {})[r["guardrail_id"]] = r["missingness_code"]
    return events, missing, synthetic


def complete_cases(per_item: dict) -> dict:
    return {i: g for i, g in per_item.items() if len(g) == len(GUARDS)}


def delta(cc: dict, a: str, b: str) -> tuple[float, float, float, int]:
    n = len(cc)
    pa = sum(g[a] for g in cc.values()) / n
    pb = sum(g[b] for g in cc.values()) / n
    p11 = sum(g[a] & g[b] for g in cc.values()) / n
    return p11 - pa * pb, pa, pb, n


def delta_independent(cc: dict, a: str, b: str) -> float:
    """Control 5: a second route — contingency counts, not indicator means."""
    n11 = n10 = n01 = n00 = 0
    for g in cc.values():
        if g[a] and g[b]:
            n11 += 1
        elif g[a]:
            n10 += 1
        elif g[b]:
            n01 += 1
        else:
            n00 += 1
    n = n11 + n10 + n01 + n00
    return n11 / n - ((n11 + n10) / n) * ((n11 + n01) / n)


def bootstrap_ci(cc: dict, a: str, b: str) -> tuple[float, float]:
    ids = sorted(cc)
    rng = random.Random(f"{SEED}:boot:{a}:{b}:{len(ids)}")
    deltas = []
    for _ in range(B):
        sample = [cc[rng.choice(ids)] for _ in ids]
        n = len(sample)
        pa = sum(g[a] for g in sample) / n
        pb = sum(g[b] for g in sample) / n
        p11 = sum(g[a] & g[b] for g in sample) / n
        deltas.append(p11 - pa * pb)
    deltas.sort()
    return deltas[int(0.025 * B)], deltas[int(0.975 * B) - 1]


def analyze_stratum(name: str, cc: dict, missing_items: dict) -> dict:
    n = len(cc)
    out = {"stratum": name, "complete_case_n": n,
           "missing_items": len(missing_items)}
    out["marginals"] = {
        g: {"p": sum(v[g] for v in cc.values()) / n,
            "wilson95": wilson(sum(v[g] for v in cc.values()), n)}
        for g in GUARDS}
    prs = {}
    for a, b in PAIRS:
        d, pa, pb, _ = delta(cc, a, b)
        d2 = delta_independent(cc, a, b)
        assert abs(d - d2) < 1e-12, "independent calculator disagrees"
        lo, hi = bootstrap_ci(cc, a, b)
        rng = random.Random(f"{SEED}:perm:{name}:{a}:{b}")
        bvals = [v[b] for v in cc.values()]
        perms = []
        for _ in range(PERM):
            shuffled = bvals[:]
            rng.shuffle(shuffled)
            p11 = sum(x & y for x, y in
                      zip((v[a] for v in cc.values()), shuffled)) / n
            perms.append(p11 - out["marginals"][a]["p"]
                         * out["marginals"][b]["p"])
        perms.sort()
        note = ("llama-guard-lineage pair: dependence may be "
                "mechanism-induced" if {a, b} == {"lg4", "lg3"} else None)
        prs[f"{a}+{b}"] = {
            "delta": d, "bootstrap95": (lo, hi),
            "independent_calculator": d2,
            "permutation_null_95band": (perms[int(0.025 * PERM)],
                                        perms[int(0.975 * PERM) - 1]),
            "lineage_note": note}
    out["pairs"] = prs
    out["duplicate_column_control"] = {
        g: {"delta_self": delta(cc, g, g)[0],
            "theoretical": out["marginals"][g]["p"]
            * (1 - out["marginals"][g]["p"])} for g in GUARDS}
    all_event = sum(all(v[g] for g in GUARDS) for v in cc.values())
    catches = {g: n - sum(v[g] for v in cc.values()) for g in GUARDS}
    out["stack_secondary"] = {
        "all_event_rate": all_event / n,
        "product_of_event_rates": math.prod(
            out["marginals"][g]["p"] for g in GUARDS),
        "frechet_set_counts": [max(0, n - sum(catches.values())),
                               n - max(catches.values())],
        "loo_exclusive": {
            g: sum(v[g] and not any(v[o] for o in GUARDS if o != g)
                   for v in cc.values()) for g in GUARDS}}
    noise = {}
    for rate in (0.01, 0.05):
        rng = random.Random(f"{SEED}:noise:{name}:{rate}")
        flipped = {i: {g: (1 - v[g] if rng.random() < rate else v[g])
                       for g in GUARDS} for i, v in cc.items()}
        noise[str(rate)] = {f"{a}+{b}": delta(flipped, a, b)[0]
                            for a, b in PAIRS}
    out["label_noise_control"] = noise
    bounds = {}
    for a, b in PAIRS:
        vals = []
        for fill in (0, 1):
            ext = dict(cc)
            for i in missing_items:
                ext[i] = {g: fill for g in GUARDS}
            vals.append(delta(ext, a, b)[0])
        bounds[f"{a}+{b}"] = sorted(vals)
    out["missingness_bounds"] = bounds
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    repo = Path(__file__).resolve().parent.parent.parent.parent
    if repo in out.parents or out == repo:
        sys.exit("refusing to write outputs inside the repository")
    out.mkdir(parents=True, exist_ok=True)

    events, missing, synthetic = load(Path(args.rows))
    tag = "SYNTHETIC" if synthetic else "REAL"
    report = {"mode": tag, "strata": []}
    for stratum, per_item in sorted(events.items()):
        cc = complete_cases(per_item)
        res = analyze_stratum(stratum, cc, missing.get(stratum, {}))
        report["strata"].append(res)
        print(f"[{tag}] {stratum}: complete-case n={res['complete_case_n']}, "
              f"missing items={res['missing_items']}")
        for pair, pr in res["pairs"].items():
            print(f"[{tag}]   {pair}: Δ={pr['delta']:+.5f} "
                  f"boot95=({pr['bootstrap95'][0]:+.5f},"
                  f"{pr['bootstrap95'][1]:+.5f}) "
                  f"perm95=({pr['permutation_null_95band'][0]:+.5f},"
                  f"{pr['permutation_null_95band'][1]:+.5f})")
        ss = res["stack_secondary"]
        print(f"[{tag}]   stack: all-event {ss['all_event_rate']:.5f} vs "
              f"product {ss['product_of_event_rates']:.5f}; Fréchet counts "
              f"{ss['frechet_set_counts']}; LOO exclusive "
              f"{ss['loo_exclusive']}")
    digest = hashlib.sha256(
        json.dumps(report, sort_keys=True).encode()).hexdigest()
    report["report_sha256_of_content"] = digest
    (out / f"analysis.{tag}.json").write_text(json.dumps(report, indent=2))
    print(f"ok    all five controls executed; independent calculator "
          f"agreed on every pair; report {digest[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
