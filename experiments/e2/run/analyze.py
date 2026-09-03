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


def missingness_delta_bounds(per_item: dict, a: str, b: str) -> tuple[float, float]:
    """Exact extremal Δ_ab over every completion of the missing cells.

    Fixed part: items with both a and b observed. Free parts, per the
    TRUE completion space (observed cells of partially missing items stay
    fixed; only missing cells vary):
      k1/k0 items with a missing and b observed 1/0 — choose j1/j0 set to 1
      l1/l0 items with b missing and a observed 1/0 — choose i1/i0 set to 1
      mb items with both missing — choose c11/c10/c01 pattern counts
    Δ is linear in j0, i0 and bilinear in (c10, c01) given the rest, so
    those sit at corners; j1, i1, c11 are scanned exhaustively. Proven
    exact against brute-force enumeration in test_instrument.py.
    """
    n11 = na = nb = 0
    k1 = k0 = l1 = l0 = mb = 0
    n = len(per_item)
    for v in per_item.values():
        ha, hb = a in v, b in v
        if ha and hb:
            n11 += v[a] & v[b]
            na += v[a]
            nb += v[b]
        elif hb:
            k1 += v[b]
            k0 += 1 - v[b]
            nb += v[b]   # the observed b counts toward pB under EVERY fill
        elif ha:
            l1 += v[a]
            l0 += 1 - v[a]
            na += v[a]   # the observed a counts toward pA under EVERY fill
        else:
            mb += 1

    def d(j1, j0, i1, i0, c11, c10, c01) -> float:
        p11 = (n11 + j1 + i1 + c11) / n
        pa = (na + j1 + j0 + c11 + c10) / n
        pb = (nb + i1 + i0 + c11 + c01) / n
        return p11 - pa * pb

    lo, hi = math.inf, -math.inf
    for j1 in range(k1 + 1):
        for i1 in range(l1 + 1):
            for c11 in range(mb + 1):
                rest = mb - c11
                for j0 in (0, k0):
                    for i0 in (0, l0):
                        # (c10, c01) on the simplex c10+c01 <= rest: Δ is
                        # bilinear, linear along the axes, but QUADRATIC
                        # along the hypotenuse — the product (A+c10)(B+c01)
                        # with a fixed sum peaks at the balanced split, so
                        # Δ's minimum can sit interior. Evaluate the three
                        # corners AND the integer neighbourhood of that
                        # interior optimum.
                        cands = {(0, 0), (rest, 0), (0, rest)}
                        A = na + j1 + j0 + c11
                        Bv = nb + i1 + i0 + c11
                        t = (Bv + rest - A) / 2
                        for ti in (math.floor(t), math.ceil(t)):
                            ti = max(0, min(rest, ti))
                            cands.add((ti, rest - ti))
                        for c10, c01 in cands:
                            v = d(j1, j0, i1, i0, c11, c10, c01)
                            lo, hi = min(lo, v), max(hi, v)
    return lo, hi


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


def analyze_stratum(name: str, cc: dict, per_item_all: dict) -> dict:
    n = len(cc)
    out = {"stratum": name, "complete_case_n": n,
           "items_with_missing_cells": len(per_item_all) - n}
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
    # Exact extremal bounds over the true completion space: every item
    # enters; observed cells stay fixed; only missing cells vary. The
    # 2026-09-01 uniform-fill version was proven unsound by the battery
    # (P6) and replaced — Δ is not monotone in the fill.
    everything = dict(per_item_all)
    out["missingness_bounds"] = {
        f"{a}+{b}": missingness_delta_bounds(everything, a, b)
        for a, b in PAIRS}
    return out



# ---------------------------------------------------------------------------
# --selection — retrospective regret and difficulty-stratified dependence on
# the existing per-item matrices (ARTIFACTS/12-WEEK-PROGRAM.md §15 / W1).
# Native points, unmatched, retrospective. Reads only pinned, hash-checked
# public releases; refuses to compute on a changed byte. Nothing here loads a
# model or touches a frozen E2 item.
#
# Contract-silent choices, recorded here rather than adapted silently:
#   * bootstrap on R holds the full-data picks M(A), J(A) fixed and resamples
#     harmful items (B, SEED as the primary Δ bootstrap);
#   * crude OR uses Haldane +0.5 (the convention of the Alotaibi artifact);
#   * MH stratifier = miss count among the OTHER guards of the table, as §7
#     states; an MH numerator with zero denominator is +inf, 0/0 is None;
#   * a pair is "measurable" when neither marginal is 0 or n; the Alotaibi
#     prediction denominator is that artifact's own 15 live pairs.
# ---------------------------------------------------------------------------
import csv
import io
import urllib.request

SCRIPTS = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ALOTAIBI_COMMIT = "f517218b5eb3cf4d2896b37b83316e56ec87d6ce"
ALOTAIBI_BASE = ("https://raw.githubusercontent.com/AbrarAlotaibi/"
                 f"defense-correlation/{ALOTAIBI_COMMIT}/results/hpc_vicuna_autodan/")
ALOTAIBI_DEFENSES = ("llamaguard", "ppl_filter", "probe", "probe_b",
                     "refusal_prime", "smoothllm", "token_anomaly")
ALOTAIBI_LIVE = ("ppl_filter", "probe", "probe_b", "refusal_prime",
                 "smoothllm", "token_anomaly")
BELLS_META = ("question", "harm_level", "source", "category")


def fetch_bytes(url: str, cache: Path | None, name: str) -> bytes:
    if cache is not None and (cache / name).exists():
        return (cache / name).read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "cubits11-e2-w1-selection"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / name).write_bytes(raw)
    return raw


def require_sha(raw: bytes, want: str, name: str) -> str:
    got = hashlib.sha256(raw).hexdigest()
    if got != want:
        sys.exit(f"{name}: sha256 {got[:16]}… != pinned {want[:16]}… — the "
                 f"bound artifact changed; refusing to compute on it")
    return got


def source_bells11(cache: Path | None, pin_path: Path) -> list:
    import reanalyze_bells_subset as rb
    raw = fetch_bytes(rb.CSV_URL, cache, "non_adversarial_prompts.csv")
    sha = require_sha(raw, rb.CSV_SHA256, "bells non_adversarial_prompts.csv")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    systems = [c for c in rows[0] if c not in BELLS_META]
    if len(systems) != 11:
        sys.exit(f"bells: expected 11 verdict columns, found {len(systems)}")

    def bits(level: str) -> dict:
        return {f"row{k}": {s: int(r[s].strip() == "1") for s in systems}
                for k, r in enumerate(rows) if r["harm_level"] == level}
    harm, ben = bits("harmful"), bits("benign")
    loc = f"{rb.CSV_URL} sha256:{sha}"
    tables = []
    for label, guards in (("harmful[all11]", systems),
                          ("harmful[specialized5]", list(rb.SPECIALIZED))):
        tables.append({
            "source": "bells11", "label": label, "guards": guards,
            "catch": {i: {g: v[g] for g in guards} for i, v in harm.items()},
            "benign": {i: {g: v[g] for g in guards} for i, v in ben.items()},
            "operating_point": "native (vendor-default binary verdicts as released)",
            "event": "catch = released verdict 1 on a harmful-labelled prompt; "
                     "benign flag = verdict 1 on a benign-labelled prompt",
            "item_id_scheme": "row index in the released file, harm_level stratum",
            "locator": loc, "prediction_pairs": None})
    return tables


def source_msbench(cache: Path | None, pin_path: Path) -> list:
    import reanalyze_msbench as rm
    verdicts: dict = {}
    locs = []
    for kind in ("harmful", "benign"):
        verdicts[kind] = {}
        for guard in rm.GUARDS:
            name = f"guard_{guard}_{kind}.jsonl"
            raw = fetch_bytes(rm.BASE_URL + name, cache, name)
            sha = require_sha(raw, rm.SHA256[name], name)
            locs.append(f"{rm.BASE_URL}{name} sha256:{sha}")
            table = {}
            for line in raw.decode("utf-8").splitlines():
                r = json.loads(line)
                table[r["item_id"]] = (int(bool(r["blocked"])), r["modality"])
            verdicts[kind][guard] = table
    tables = []
    for modality in ("text", "image"):
        def stratum(kind: str) -> dict:
            base = verdicts[kind][rm.GUARDS[0]]
            return {i: {g: verdicts[kind][g][i][0] for g in rm.GUARDS}
                    for i in sorted(base) if base[i][1] == modality}
        tables.append({
            "source": "msbench", "label": f"harmful_{modality}",
            "guards": list(rm.GUARDS), "catch": stratum("harmful"),
            "benign": stratum("benign"),
            "operating_point": "native (harness-normalized `blocked` bit at the "
                               "release's fixed action layer)",
            "event": "catch = blocked on a harmful item; benign flag = blocked "
                     "on a benign item; not a shared-event catch statistic (MC-004)",
            "item_id_scheme": "release item_id",
            "locator": " | ".join(locs), "prediction_pairs": None})
    return tables


def source_alotaibi7(cache: Path | None, pin_path: Path) -> list:
    names = (["gold.jsonl", "confound_check.json"]
             + [f"stage04_{d}_benign.jsonl" for d in ALOTAIBI_DEFENSES])
    raws = {n: fetch_bytes(ALOTAIBI_BASE + n, cache, n) for n in names}
    hashes = {n: hashlib.sha256(raws[n]).hexdigest() for n in names}
    if pin_path.exists():
        pin = json.loads(pin_path.read_text())
        if pin["commit"] != ALOTAIBI_COMMIT:
            sys.exit("alotaibi: pin file commit differs from the code pin")
        for n in names:
            if pin["files"].get(n) != hashes[n]:
                sys.exit(f"alotaibi {n}: sha256 differs from the recorded pin "
                         f"— refusing to compute on a changed artifact")
        pinned = "asserted against recorded pin"
    else:
        pin_path.parent.mkdir(parents=True, exist_ok=True)
        pin_path.write_text(json.dumps(
            {"repository": "AbrarAlotaibi/defense-correlation",
             "commit": ALOTAIBI_COMMIT, "license": "MIT",
             "recorded": "at first fetch by analyze.py --selection --source alotaibi7",
             "files": hashes}, indent=2) + "\n")
        pinned = f"recorded at fetch into {pin_path.name}"
    gold = [json.loads(l) for l in raws["gold.jsonl"].decode("utf-8").splitlines()]
    catch: dict = {}
    for r in gold:
        if r["attack"] != "adaptive" or r["defense"] not in ALOTAIBI_DEFENSES:
            continue
        catch.setdefault(r["behaviour_id"], {})[r["defense"]] = int(not r["breach"])
    if any(len(v) != len(ALOTAIBI_DEFENSES) for v in catch.values()) or len(catch) != 100:
        sys.exit("alotaibi: adaptive breach matrix is not 100 × 7 complete")
    benign: dict = {}
    for d in ALOTAIBI_DEFENSES:
        for line in raws[f"stage04_{d}_benign.jsonl"].decode("utf-8").splitlines():
            r = json.loads(line)
            benign.setdefault(r["benign_id"], {})[d] = int(bool(r["blocked"]))
    if any(len(v) != len(ALOTAIBI_DEFENSES) for v in benign.values()):
        sys.exit("alotaibi: benign refusal matrix incomplete")
    live_pairs = {tuple(sorted(p)) for p in itertools.combinations(ALOTAIBI_LIVE, 2)}
    return [{
        "source": "alotaibi7", "label": "adaptive_breach[7 defenses]",
        "guards": list(ALOTAIBI_DEFENSES), "catch": catch, "benign": benign,
        "operating_point": "native (each defense at the artifact's calibrated "
                           "threshold; breach judged post hoc by StrongREJECT)",
        "event": "catch = no breach under the adaptive attacker; benign flag = "
                 "refused on the matched benign set (stage04)",
        "item_id_scheme": "behaviour_id (JailbreakBench)",
        "locator": f"{ALOTAIBI_BASE}gold.jsonl sha256:{hashes['gold.jsonl']} "
                   f"({pinned})",
        "prediction_pairs": sorted(live_pairs),
        "_confound_check": json.loads(raws["confound_check.json"].decode("utf-8")),
        "_file_hashes": hashes}]


SOURCES = {"bells11": source_bells11, "msbench": source_msbench,
           "alotaibi7": source_alotaibi7}


def regret_ci(catch: dict, ids: list, a: str, m: str, j: str, tag: str) -> tuple:
    """Percentile bootstrap on U(A,J) − U(A,M) in items; picks held fixed."""
    rng = random.Random(f"{SEED}:regret:{tag}:{a}:{len(ids)}")
    vals = []
    for _ in range(B):
        s = [catch[rng.choice(ids)] for _ in ids]
        vals.append(sum(v[a] | v[j] for v in s) - sum(v[a] | v[m] for v in s))
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def mh_odds_ratio(catch: dict, ids: list, a: str, b: str, others: list) -> tuple:
    """(crude Haldane OR, Mantel–Haenszel OR, strata) of joint MISS for the
    pair, stratified by the miss count among `others` on each item."""
    strata: dict = {}
    for i in ids:
        strata.setdefault(sum(1 - catch[i][o] for o in others), []).append(i)
    n11 = n10 = n01 = n00 = 0
    num = den = 0.0
    for its in strata.values():
        a11 = a10 = a01 = a00 = 0
        for i in its:
            x, y = 1 - catch[i][a], 1 - catch[i][b]
            if x and y:
                a11 += 1
            elif x:
                a10 += 1
            elif y:
                a01 += 1
            else:
                a00 += 1
        nk = len(its)
        num += a11 * a00 / nk
        den += a10 * a01 / nk
        n11, n10, n01, n00 = n11 + a11, n10 + a10, n01 + a01, n00 + a00
    crude = ((n11 + 0.5) * (n00 + 0.5)) / ((n10 + 0.5) * (n01 + 0.5))
    if den == 0 and num == 0:
        mh = None
    elif den == 0:
        mh = math.inf
    else:
        mh = num / den
    return crude, mh, len(strata)


def selection_stats(table: dict) -> dict:
    guards, catch, ben = table["guards"], table["catch"], table["benign"]
    ids = sorted(catch)
    n = len(ids)
    tag = f"{table['source']}:{table['label']}"
    cc = {g: sum(catch[i][g] for i in ids) for g in guards}
    fc = {g: sum(v[g] for v in ben.values()) for g in guards}

    def U(a: str, b: str) -> int:
        return sum(catch[i][a] | catch[i][b] for i in ids)

    def F(a: str, b: str) -> int:
        return sum(v[a] | v[b] for v in ben.values())

    incumbents = []
    for a in guards:
        cands = [b for b in guards if b != a]
        mkey = {b: (cc[b], -fc[b]) for b in cands}
        jkey = {b: (U(a, b), -F(a, b)) for b in cands}
        m = max(cands, key=lambda b: (mkey[b], -cands.index(b)))
        j = max(cands, key=lambda b: (jkey[b], -cands.index(b)))
        um, uj = U(a, m), U(a, j)
        lo, hi = regret_ci(catch, ids, a, m, j, tag)
        incumbents.append({
            "incumbent": a, "incumbent_catch": cc[a],
            "marginal_choice": m, "joint_choice": j, "flip": m != j,
            "regret_items": uj - um, "regret_points": (uj - um) / n,
            "U_marg": um, "U_joint": uj,
            "benign_union_marg": F(a, m), "benign_union_joint": F(a, j),
            "ci95_items": [lo, hi], "ci_excludes_zero": lo > 0,
            "marginal_tie": sum(mkey[b] == mkey[m] for b in cands) > 1,
            "joint_tie": sum(jkey[b] == jkey[j] for b in cands) > 1,
            "n": n, "operating_point": table["operating_point"],
            "stratum": table["label"], "locator": table["locator"]})

    miss = {i: {g: 1 - catch[i][g] for g in guards} for i in ids}
    pred = table.get("prediction_pairs")
    pairs = []
    for a, b in itertools.combinations(guards, 2):
        d, pa, pb, _ = delta(miss, a, b)
        d2 = delta_independent(miss, a, b)
        assert abs(d - d2) < 1e-12, "independent Δ calculator disagrees"
        crude, mh, k = mh_odds_ratio(catch, ids, a, b, [g for g in guards if g not in (a, b)])
        measurable = 0 < pa < 1 and 0 < pb < 1
        in_pred = measurable if pred is None else (tuple(sorted((a, b))) in {tuple(p) for p in pred})
        pairs.append({"a": a, "b": b, "p_miss_a": pa, "p_miss_b": pb,
                      "delta": d, "crude_or_haldane": crude,
                      "mh_or": mh, "mh_strata": k, "measurable": measurable,
                      "in_prediction_set": in_pred})
    import identification
    grid = identification.integer_grid([cc[g] for g in guards], n)
    pred_pairs = [p for p in pairs if p["in_prediction_set"]]
    defined = [p for p in pred_pairs if p["mh_or"] is not None]
    ge = sum(p["mh_or"] >= 1.5 for p in defined)
    regmax = max(r["regret_items"] for r in incumbents)
    summary = (f"regret max {regmax} items ({100 * regmax / n:.1f}%) · "
               f"incumbents with CI>0: {sum(r['ci_excludes_zero'] for r in incumbents)}"
               f"/{len(incumbents)} · pairs with stratified OR ≥ 1.5: "
               f"{ge}/{len(defined)}")
    return {"source": table["source"], "stratum": table["label"], "n": n,
            "guards": guards, "operating_point": table["operating_point"],
            "event": table["event"], "item_id_scheme": table["item_id_scheme"],
            "locator": table["locator"],
            "catch_counts": cc, "benign_flag_counts": fc,
            "benign_n": len(ben), "incumbents": incumbents, "pairs": pairs,
            "frechet_all_miss_count_set": [grid[0], grid[-1]],
            "incumbents_with_flip": sum(r["flip"] for r in incumbents),
            "incumbents_with_regret_gt0": sum(r["regret_items"] > 0 for r in incumbents),
            "pairs_undefined_mh": sum(p["mh_or"] is None for p in pred_pairs),
            "summary_line": summary}


def selection_independent(table: dict, primary: dict) -> None:
    """Second route: unions from the MJGD reference kernel, picks by explicit
    sorting; asserts every published pick, union and regret."""
    import mjgd_reference
    guards, catch, ben = table["guards"], table["catch"], table["benign"]
    ids = sorted(catch)
    bids = sorted(ben)
    n = len(ids)
    dec = {g: [bool(catch[i][g]) for i in ids] for g in guards}
    bdec = {g: [bool(ben[i][g]) for i in bids] for g in guards}

    def union(a: str, b: str) -> int:
        return mjgd_reference.joint_disclosure({a: dec[a], b: dec[b]},
                                               [True] * n)["union_detection"]

    def bunion(a: str, b: str) -> int:
        if not bids:
            return 0
        return mjgd_reference.joint_disclosure({a: bdec[a], b: bdec[b]},
                                               [True] * len(bids))["union_detection"]
    for row in primary["incumbents"]:
        a = row["incumbent"]
        cands = [b for b in guards if b != a]
        m = sorted(cands, key=lambda b: (-sum(dec[b]), sum(bdec[b]), cands.index(b)))[0]
        j = sorted(cands, key=lambda b: (-union(a, b), bunion(a, b), cands.index(b)))[0]
        assert m == row["marginal_choice"], f"{a}: marginal pick disagrees"
        assert j == row["joint_choice"], f"{a}: joint pick disagrees"
        r = union(a, j) - union(a, m)
        assert r == row["regret_items"], f"{a}: regret disagrees"
        assert abs(r / n - row["regret_points"]) < 1e-12
        assert union(a, m) == row["U_marg"] and union(a, j) == row["U_joint"]


def implementation_check_alotaibi(table: dict, primary: dict) -> dict:
    """§15 decision rule: check the CMH implementation against the artifact's
    own confound_check.json — its convention stratifies on the OTHER LIVE
    defenses (Llama Guard excluded). Reported beside, never in place of,
    the frozen statistic."""
    ref = table["_confound_check"]
    ids = sorted(table["catch"])
    live = list(ref["live_defenses"])
    rows, worst = [], 0.0
    for p in ref["pairs"]:
        a, b = p["d1"], p["d2"]
        crude, mh, _ = mh_odds_ratio(table["catch"], ids, a, b,
                                     [g for g in live if g not in (a, b)])
        dm = abs(mh - p["cmh_or"]) if mh not in (None, math.inf) else math.inf
        dc = abs(crude - p["raw_or"])
        worst = max(worst, dm, dc)
        rows.append({"a": a, "b": b, "artifact_raw_or": p["raw_or"],
                     "ours_crude": crude, "artifact_cmh_or": p["cmh_or"],
                     "ours_mh_live_stratifier": mh, "artifact_survives_p": p["survives"]})
    return {"convention": "stratifier = other LIVE defenses (artifact); crude Haldane +0.5",
            "max_abs_difference": worst, "artifact_n_survives_by_p": ref["n_survives"],
            "pairs": rows}


TABLE_HEADER = ("incumbent | marginal_choice | joint_choice | flip | regret | n | "
                "operating_point | stratum | locator")


def selection_main(args) -> int:
    print("native points, unmatched, retrospective")
    out = Path(args.out).resolve()
    cache = Path(args.cache).resolve() if args.cache else None
    pin_path = out.parent / "alotaibi_pin.json"
    tables = SOURCES[args.source](cache, pin_path)
    report = {"mode": "RETROSPECTIVE", "first_line": "native points, unmatched, retrospective",
              "source": args.source, "seed": SEED, "bootstrap_B": B,
              "regret_definition": "R(A) = U(A,J(A)) − U(A,M(A)) in items of the harmful "
                                   "stratum; M = argmax marginal catch (tie: fewer benign "
                                   "flags), J = argmax measured union (tie: lower benign "
                                   "union); remaining ties: earlier column",
              "tables": []}
    for t in tables:
        st = selection_stats(t)
        selection_independent(t, st)
        report["tables"].append(st)
        print(f"\n[{args.source}] {st['stratum']}: n={st['n']} guards={len(st['guards'])}")
        print(TABLE_HEADER)
        for r in st["incumbents"]:
            print(f"{r['incumbent']} | {r['marginal_choice']} | {r['joint_choice']} | "
                  f"{r['flip']} | {r['regret_items']} items ({100 * r['regret_points']:.1f}%) "
                  f"CI[{r['ci95_items'][0]},{r['ci95_items'][1]}] | {r['n']} | "
                  f"{r['operating_point']} | {r['stratum']} | {r['locator'][:72]}…")
        print(f"[{args.source}] {st['stratum']}: {st['summary_line']}")
        print(f"[{args.source}] {st['stratum']}: Fréchet all-miss count set "
              f"{st['frechet_all_miss_count_set']}; flips {st['incumbents_with_flip']}"
              f"/{len(st['incumbents'])}; regret>0 {st['incumbents_with_regret_gt0']}"
              f"/{len(st['incumbents'])}")
        if args.source == "alotaibi7":
            chk = implementation_check_alotaibi(t, st)
            report["implementation_check"] = chk
            report["file_hashes"] = t["_file_hashes"]
            print(f"[alotaibi7] implementation check vs confound_check.json "
                  f"(artifact convention): max |diff| = {chk['max_abs_difference']:.3e}")
    print("ok    independent calculator agrees (1e-12)")
    digest = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    report["report_sha256_of_content"] = digest
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"ok    wrote {out} ({digest[:16]})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows")
    ap.add_argument("--out", required=True)
    ap.add_argument("--selection", action="store_true",
                    help="retrospective regret mode (§15/W1) on a pinned public matrix")
    ap.add_argument("--source", choices=sorted(SOURCES))
    ap.add_argument("--cache", help="directory of previously fetched source files (offline)")
    args = ap.parse_args()
    if args.selection:
        if not args.source:
            sys.exit("--selection requires --source")
        return selection_main(args)
    if not args.rows:
        sys.exit("--rows is required outside --selection mode")
    out = Path(args.out).resolve()
    repo = Path(__file__).resolve().parent.parent.parent.parent
    if repo in out.parents or out == repo:
        sys.exit("refusing to write outputs inside the repository")
    out.mkdir(parents=True, exist_ok=True)

    events, missing, synthetic = load(Path(args.rows))
    tag = "SYNTHETIC" if synthetic else "REAL"
    report = {"mode": tag, "strata": []}
    for stratum, per_item in sorted(events.items()):
        only_missing = set(missing.get(stratum, {})) - set(per_item)
        per_item_all = {**{i: {} for i in only_missing}, **per_item}
        cc = complete_cases(per_item)
        res = analyze_stratum(stratum, cc, per_item_all)
        report["strata"].append(res)
        print(f"[{tag}] {stratum}: complete-case n={res['complete_case_n']}, "
              f"items with missing cells={res['items_with_missing_cells']}")
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
