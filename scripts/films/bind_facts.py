#!/usr/bin/env python3
"""Bind every number a film may display to the registry that owns it.

Films never retype a research number. They read ``films/data/facts.json``,
which this script DERIVES from claims.yaml (the ``expected`` blocks that the
reproduction scripts also read), from ``verify_census.compute_counts`` (the
census's one arithmetic), and from a handful of constructions whose every
constraint is asserted here before the file is written.

Each fact carries an epistemic kind, so a film can label what it shows:

  OBSERVED     a count taken from a bound, hash-verified upstream release
               (the reproduction script re-asserts it in CI)
  DERIVED      arithmetic on OBSERVED or REGISTRY values, done here
  PROVED       a mathematical result the registry binds to a clean-clone
               reproduction (CC-001, CC-004) or a checked construction (CC-003)
  CONSTRUCTED  an arrangement built here to satisfy stated constraints; it
               is one feasible world, never the released rows
  REGISTRY     a fact about the public record itself (dates, windows, ids)
  DOCUMENT     text quoted verbatim from a bound document or the registry

``--check`` regenerates in memory and fails when the committed file differs,
so a registry edit that changes a number a film shows fails the build until
the facts file (and therefore the film) is regenerated and re-inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, timedelta
from itertools import product
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import facts as fact_registry  # noqa: E402
import verify_census  # noqa: E402

OUT = ROOT / "films" / "data" / "facts.json"
TOL = 1e-9


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a: float, b: float) -> bool:
    return abs(a - b) <= TOL


class Facts:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, fid: str, value, kind: str, source: str, claim: str | None = None,
            note: str | None = None) -> None:
        if fid in self.items:
            raise ValueError(f"duplicate fact id {fid}")
        entry = {"value": value, "kind": kind, "source": source}
        if claim:
            entry["claim"] = claim
        if note:
            entry["note"] = note
        self.items[fid] = entry


def claims_by_id() -> tuple[dict, dict]:
    data = yaml.safe_load((ROOT / "claims.yaml").read_text())
    return data, {c["id"]: c for c in data["claims"]}


# --------------------------------------------------------------------------
# CC-001 / CC-004: the two-guard interval and its endpoint witnesses
# --------------------------------------------------------------------------
def bind_cc(F: Facts, C: dict) -> None:
    c1 = C["CC-001"]
    m = c1["expected"]["marginals"]
    F.add("CC-001.marginals", m, "REGISTRY", "claims.yaml:CC-001.expected.marginals", "CC-001",
          "declared illustrative input to the kernel; not a measured system")
    F.add("CC-001.and_bounds", c1["expected"]["bounds"]["and"], "PROVED",
          "claims.yaml:CC-001.expected.bounds.and (reproduced in CI by scripts/reproduce_cc001.py)",
          "CC-001")
    F.add("CC-001.or_bounds", c1["expected"]["bounds"]["or"], "PROVED",
          "claims.yaml:CC-001.expected.bounds.or", "CC-001")
    p1, p2 = m
    lo, hi = max(0.0, p1 + p2 - 1), min(p1, p2)
    assert close(lo, c1["expected"]["bounds"]["and"][0]) and close(hi, c1["expected"]["bounds"]["and"][1])
    F.add("CC-001.independence_and", p1 * p2, "DERIVED",
          "product of CC-001.marginals — the value ONE assumption (independence) selects",
          "CC-001", "an assumption-world, not an estimate")
    F.add("CC-001.support_commit", c1["support"]["commit"], "REGISTRY", "claims.yaml:CC-001.support.commit", "CC-001")

    c4 = C["CC-004"]
    F.add("CC-004.interval", c4["expected"]["interval"], "PROVED",
          "claims.yaml:CC-004.expected.interval (witness stage of scripts/reproduce_cc001.py)", "CC-004")
    # Endpoint witnesses in the same atom order as index.html Fig. 02
    # (asserted there by scripts/verify_figures.py): (neither, A only, B only, both).
    witnesses = {}
    for name, q in (("lower", lo), ("upper", hi)):
        atoms = [1 - p1 - p2 + q, p1 - q, p2 - q, q]
        assert all(a >= -TOL for a in atoms) and close(sum(atoms), 1.0)
        assert close(atoms[1] + atoms[3], p1) and close(atoms[2] + atoms[3], p2)
        witnesses[name] = [round(a, 10) for a in atoms]
    F.add("CC-004.witness_lower", witnesses["lower"], "PROVED",
          "constructed from CC-001.marginals; sums to 1, nonnegative, satisfies both marginals, attains the lower endpoint (asserted here)",
          "CC-004")
    F.add("CC-004.witness_upper", witnesses["upper"], "PROVED",
          "constructed from CC-001.marginals; attains the upper endpoint (asserted here)", "CC-004")
    # every interior world q in [lo, hi] is feasible too — the film sweeps it
    F.add("CC-004.feasible_q_grid", [round(lo + i * (hi - lo) / 10, 10) for i in range(11)], "PROVED",
          "eleven feasible both-fail values from lower to upper endpoint; each has a witness of the same form",
          "CC-004")


# --------------------------------------------------------------------------
# CC-003: the parity construction (three guards, eight outcomes)
# --------------------------------------------------------------------------
def bind_parity(F: Facts, C: dict) -> None:
    c = C["CC-003"]
    prop = " ".join(c["proposition"].split())
    for needle in ("(0.5)", "(0.25)", "0 under even parity", "0.25 under odd parity"):
        if needle not in prop:
            raise SystemExit(f"CC-003 proposition no longer states {needle!r}; parity facts must be re-reviewed")
    even = {o: 0.25 for o in product((0, 1), repeat=3) if sum(o) % 2 == 0}
    odd = {o: 0.25 for o in product((0, 1), repeat=3) if sum(o) % 2 == 1}
    for world in (even, odd):
        assert close(sum(world.values()), 1.0)
        for i in range(3):
            assert close(sum(p for o, p in world.items() if o[i] == 1), 0.5)
        for i, j in ((0, 1), (0, 2), (1, 2)):
            assert close(sum(p for o, p in world.items() if o[i] == 1 and o[j] == 1), 0.25)
    assert close(even.get((1, 1, 1), 0.0), 0.0) and close(odd[(1, 1, 1)], 0.25)
    F.add("CC-003.singleton", 0.5, "PROVED", "claims.yaml:CC-003.proposition (asserted numerically here)", "CC-003")
    F.add("CC-003.pairwise", 0.25, "PROVED", "claims.yaml:CC-003.proposition (asserted numerically here)", "CC-003")
    F.add("CC-003.triple_even", 0.0, "PROVED", "claims.yaml:CC-003.proposition", "CC-003")
    F.add("CC-003.triple_odd", 0.25, "PROVED", "claims.yaml:CC-003.proposition", "CC-003")
    F.add("CC-003.even_atoms", {"".join(map(str, o)): p for o, p in even.items()}, "CONSTRUCTED",
          "uniform mass on the four even-parity outcomes; singleton/pairwise moments asserted here", "CC-003",
          "E1 is synthetic — a possibility proof, not a frequency claim about real stacks")
    F.add("CC-003.odd_atoms", {"".join(map(str, o)): p for o, p in odd.items()}, "CONSTRUCTED",
          "uniform mass on the four odd-parity outcomes; moments asserted here", "CC-003")
    F.add("CC-003.support_commit", c["support"]["commit"], "REGISTRY", "claims.yaml:CC-003.support.commit", "CC-003")


# --------------------------------------------------------------------------
# MC-001: the census
# --------------------------------------------------------------------------
def bind_census(F: Facts, C: dict) -> None:
    data = verify_census.load()
    counts = verify_census.compute_counts(data)
    reg = fact_registry.registry(counts)
    for fid, value in reg.items():
        F.add(fid, value, "DERIVED", "scripts/facts.registry ← verify_census.compute_counts(census.yaml)", "MC-001")
    census = data["census"]
    F.add("MC-001.frozen_as_of", str(census["frozen_as_of"]), "REGISTRY", "census.yaml:census.frozen_as_of", "MC-001")
    F.add("MC-001.criteria_version", census["criteria_version"], "REGISTRY", "census.yaml:census.criteria_version", "MC-001")
    F.add("MC-001.adjudication_mode", census["adjudication_status"]["mode"], "REGISTRY",
          "census.yaml:census.adjudication_status.mode", "MC-001",
          "single primary reviewer; no independent second review exists yet")
    F.add("MC-001.excluded", counts["excluded"], "DERIVED", "compute_counts: len(exclusions)", "MC-001")
    F.add("MC-001.unexamined", counts["unexamined"], "DERIVED", "compute_counts: len(unexamined_candidates)", "MC-001")
    F.add("MC-001.NOT_COMPARABLE", counts["by_classification"].get("NOT_COMPARABLE", 0), "DERIVED",
          "compute_counts.by_classification", "MC-001")

    def tri(row, field):
        cell = row.get(field)
        return cell.get("value") if isinstance(cell, dict) else None

    rows = []
    for r in data["benchmarks"]:
        if r.get("status") != "examined":
            continue
        shared = tri(r, "same_items_for_all_systems") == "yes" and tri(r, "same_event_definition") == "yes"
        tnc = shared and tri(r, "thresholds_comparable") in {"yes", "unstated"}
        doc = tnc and tri(r, "thresholds_comparable") == "yes" and tri(r, "all_systems_saw_all_items") == "yes"
        rows.append({
            "id": r["id"],
            "classification": r["classification"],
            "joint_scope": r.get("joint_scope"),
            "joint_scope_additional": r.get("joint_scope_additional") or [],
            "shared_basis": shared,
            "threshold_not_contradicted": tnc,
            "threshold_documented_full_exposure": doc,
        })
    # the per-row flags must reproduce the ladder exactly, or the film lies
    assert sum(x["shared_basis"] for x in rows) == reg["MC-001.M1"]
    assert sum(x["threshold_not_contradicted"] for x in rows) == reg["MC-001.M2"]
    assert sum(x["threshold_documented_full_exposure"] for x in rows) == reg["MC-001.M3"]
    assert sum(x["classification"] == "PRESENT" for x in rows) == reg["MC-001.K"]
    assert sum(x["classification"] == "ABSENT" for x in rows) == reg["MC-001.ABSENT"]
    assert len(rows) == reg["MC-001.N"]
    F.add("MC-001.rows", rows, "REGISTRY",
          "census.yaml examined rows; per-row ladder flags use the identical predicates as compute_counts",
          "MC-001", "classifications are one reviewer's first-pass reading of each public source")

    sens = []
    for s in census.get("interpretation_sensitivities", []):
        e = s["expected"]
        sens.append({"id": s["id"], "label": s["label"],
                     "envelope": [e["n_examined"], e["m_shared_basis"], e["k_present"]]})
    F.add("MC-001.sensitivities", sens, "REGISTRY", "census.yaml:census.interpretation_sensitivities[].expected", "MC-001",
          "declared alternative readings; never a bare replacement for the primary envelope")

    correction = None
    for entry in census.get("revision_history", []):
        change = " ".join(str(entry.get("change", "")).split())
        if str(entry.get("date")) == "2026-08-30" and "19/13/4" in change and "20/14/5" in change:
            correction = {"date": "2026-08-30", "from": [19, 13, 4], "to": [20, 14, 5],
                          "row_added": "multimodal-safeguard-bench-2026"}
            break
    if correction is None:
        raise SystemExit("census revision_history no longer carries the dated 19/13/4 -> 20/14/5 correction")
    assert correction["to"] == [reg["MC-001.N"], reg["MC-001.M"], reg["MC-001.K"]]
    F.add("MC-001.correction", correction, "REGISTRY",
          "census.yaml:census.revision_history (entry dated 2026-08-30); the rejected envelope is retained there",
          "MC-001", "the claim's own REJECT falsifier fired; the superseding envelope is a correction, not a reinterpretation")


# --------------------------------------------------------------------------
# MC-002 / MC-003: BELLS counts, identification, and one consistent arrangement
# --------------------------------------------------------------------------
GUARD_ORDER = ["lakera_guard", "prompt_guard", "langkit", "nemo", "llm_guard"]
GUARD_LABEL = {"lakera_guard": "Lakera Guard", "prompt_guard": "Prompt Guard", "langkit": "LangKit",
               "nemo": "NeMo Guardrails", "llm_guard": "LLM Guard"}


def bind_bells(F: Facts, C: dict) -> None:
    c2 = C["MC-002"]
    e = c2["expected"]
    src = "claims.yaml:MC-002.expected (re-asserted against the hash-verified release by scripts/reanalyze_bells_subset.py)"
    n = e["n_harmful"]
    F.add("MC-002.n_prompts", e["n_prompts"], "OBSERVED", src, "MC-002")
    F.add("MC-002.n_harmful", n, "OBSERVED", src, "MC-002")
    F.add("MC-002.n_benign", e["n_benign"], "OBSERVED", src, "MC-002")
    F.add("MC-002.n_borderline", e["n_borderline"], "OBSERVED", src, "MC-002",
          "a third stratum, named so it is never folded into either denominator")
    assert e["n_harmful"] + e["n_benign"] + e["n_borderline"] == e["n_prompts"]
    F.add("MC-002.guards", GUARD_ORDER, "REGISTRY", "column order of the residual chain in scripts/reanalyze_bells_subset.py", "MC-002")
    F.add("MC-002.guard_labels", GUARD_LABEL, "REGISTRY", "names as printed by the release", "MC-002")
    F.add("MC-002.per_guard_catches", e["per_guard_catches"], "OBSERVED", src, "MC-002")
    misses = {g: n - e["per_guard_catches"][g] for g in GUARD_ORDER}
    F.add("MC-002.per_guard_misses", misses, "DERIVED", "n_harmful − per_guard_catches", "MC-002")
    F.add("MC-002.union_detection", e["union_detection"], "OBSERVED", src, "MC-002")
    F.add("MC-002.all_miss", e["all_miss"], "OBSERVED", src, "MC-002")
    assert e["union_detection"] + e["all_miss"] == n
    F.add("MC-002.per_guard_benign_flags", e["per_guard_benign_flags"], "OBSERVED", src, "MC-002")
    F.add("MC-002.benign_union_flagged", e["benign_union_flagged"], "OBSERVED", src, "MC-002")
    F.add("MC-002.leave_one_out_union", e["leave_one_out_union"], "OBSERVED", src, "MC-002")
    excl = {g: e["union_detection"] - e["leave_one_out_union"][g] for g in GUARD_ORDER}
    F.add("MC-002.exclusive_full_stack_coverage", excl, "DERIVED",
          "union_detection − leave_one_out_union[g] (removal-relative; not a residual, not a ranking)", "MC-002")
    rates = {g: misses[g] / n for g in GUARD_ORDER}
    prod = 1.0
    for g in GUARD_ORDER:
        prod *= rates[g]
    F.add("MC-002.independence_plugin_rate", round(prod, 6), "DERIVED",
          "product of per-guard miss rates — the value the independence model would select", "MC-002",
          "a model's point, not a count; on an 82-item file it is not even an integer number of prompts")
    F.add("MC-002.independence_plugin_prompts", round(prod * n, 4), "DERIVED", "independence_plugin_rate × n_harmful", "MC-002")
    F.add("MC-002.all_miss_rate", round(e["all_miss"] / n, 6), "DERIVED", "all_miss / n_harmful", "MC-002")
    F.add("MC-002.ratio_recomputed_to_plugin", round((e["all_miss"] / n) / prod, 4), "DERIVED",
          "all_miss_rate / independence_plugin_rate", "MC-002",
          "describes this subset's arithmetic, not a law; cite only with the selection caveat")
    F.add("MC-002.support_commit", c2["support"]["commit"], "REGISTRY", "claims.yaml:MC-002.support.commit", "MC-002")
    F.add("MC-002.support_url", c2["support"]["url"], "REGISTRY", "claims.yaml:MC-002.support.url", "MC-002")

    c3 = C["MC-003"]
    e3 = c3["expected"]
    src3 = "claims.yaml:MC-003.expected (checked by scripts/identification.py)"
    F.add("MC-003.identified_set_lower", e3["identified_set_lower"], "PROVED", src3, "MC-003")
    F.add("MC-003.identified_set_upper", e3["identified_set_upper"], "PROVED", src3, "MC-003")
    F.add("MC-003.identified_set_size", e3["identified_set_size"], "PROVED", src3, "MC-003")
    lo = max(0.0, sum(rates.values()) - (len(GUARD_ORDER) - 1))
    hi = min(rates.values())
    assert close(lo, e3["identified_set_lower"] / n) or e3["identified_set_lower"] == 0
    assert close(hi, e3["identified_set_upper"] / n)
    F.add("MC-003.continuous_set", [round(lo, 6), round(hi, 6)], "PROVED",
          "[max(0, Σp − (k−1)), min p] on MC-002.per_guard_misses / n_harmful (asserted here)", "MC-003")
    F.add("MC-003.benign_burden_floor_pct", e3["benign_burden_floor_pct"], "PROVED", src3, "MC-003")
    F.add("MC-003.improvement_floor_pct", e3["improvement_floor_pct"], "PROVED", src3, "MC-003")
    F.add("MC-003.aggregate_unique_contribution_bounds", e3["aggregate_unique_contribution_bounds"], "PROVED", src3, "MC-003",
          "what catch marginals plus the union alone can say about each guard's exclusive coverage")
    F.add("MC-003.members_zero_exclusive_full_stack_coverage", e3["members_zero_exclusive_full_stack_coverage"], "OBSERVED", src3, "MC-003")
    benign_floor = max(e["per_guard_benign_flags"].values()) / e["n_benign"]
    assert close(benign_floor * 100, e3["benign_burden_floor_pct"])
    F.add("MC-003.benign_union_set", [round(benign_floor, 6), round(min(1.0, sum(e["per_guard_benign_flags"].values()) / e["n_benign"]), 6)],
          "PROVED", "[max f_i, min(1, Σ f_i)] on MC-002.per_guard_benign_flags / n_benign", "MC-003")
    F.add("MC-003.benign_union_rate", round(e["benign_union_flagged"] / e["n_benign"], 6), "DERIVED",
          "benign_union_flagged / n_benign", "MC-002")

    # One arrangement of 82 × 5 catch bits consistent with EVERY registered
    # aggregate: per-guard catches, the union, and all five leave-one-out
    # unions. It is a feasible world for the film's lamps to stand in. It is
    # not the released rows, which this record never redistributes.
    catches = e["per_guard_catches"]
    L, P, K, N_, G = GUARD_ORDER  # lakera, prompt_guard, langkit, nemo, llm_guard
    blocks = [
        ("none", 0, e["all_miss"]),
        ("nemo-only", {N_}, excl["nemo"]),
        ("lakera-only", {L}, excl["lakera_guard"]),
        ("nemo+langkit", {N_, K}, 3),
        ("nemo+lakera+langkit", {N_, L, K}, catches["langkit"] - 3),
        ("nemo+lakera+prompt_guard", {N_, L, P}, catches["prompt_guard"]),
        ("nemo+lakera", {N_, L}, 0),
    ]
    used = sum(b[2] for b in blocks)
    blocks[-1] = ("nemo+lakera", {N_, L}, n - used)
    masks = []
    for _, members, count in blocks:
        m = 0
        if members:
            for g in members:
                m |= 1 << GUARD_ORDER.index(g)
        masks += [m] * count
    assert len(masks) == n
    for gi, g in enumerate(GUARD_ORDER):
        assert sum(1 for m in masks if m >> gi & 1) == catches[g], g
    assert sum(1 for m in masks if m) == e["union_detection"]
    for gi, g in enumerate(GUARD_ORDER):
        others = sum(1 for m in masks if m & ~(1 << gi))
        assert others == e["leave_one_out_union"][g], (g, others)
    F.add("MC-002.constructed_arrangement", masks, "CONSTRUCTED",
          "82 five-bit catch masks (bit i = MC-002.guards[i]) satisfying per-guard catches, union, and all leave-one-out unions — asserted here",
          "MC-002", "one feasible arrangement, not the released rows; pairwise overlaps are not registered and are not identified by these aggregates")


# --------------------------------------------------------------------------
# MC-004: Multimodal Safeguard Bench strata (bound for Cohort B)
# --------------------------------------------------------------------------
def bind_msbench(F: Facts, C: dict) -> None:
    c = C["MC-004"]
    src = "claims.yaml:MC-004.expected (re-asserted against eight hash-verified files by scripts/reanalyze_msbench.py)"
    for stratum, block in c["expected"].items():
        F.add(f"MC-004.{stratum}", block, "OBSERVED", src, "MC-004",
              "harness-normalized native `unsafe` bits; an OR of them is not a shared-event catch statistic")
    F.add("MC-004.support_commit", c["support"]["commit"], "REGISTRY", "claims.yaml:MC-004.support.commit", "MC-004")


# --------------------------------------------------------------------------
# AF-001: mixture bounds (bound for Cohort B)
# --------------------------------------------------------------------------
def bind_af(F: Facts, C: dict) -> None:
    c = C["AF-001"]
    for key, value in c["expected"].items():
        F.add(f"AF-001.{key}", value, "OBSERVED" if key.startswith("n_") or key.startswith("behaviours") or key.startswith("checks_facts_overall") or key.endswith("_pp") else "PROVED",
              "claims.yaml:AF-001.expected (closed form checked by scripts/mixture_bounds.py)", "AF-001")


# --------------------------------------------------------------------------
# GA-001: receipt kernel — constructed digests + the registry's own boundary text
# --------------------------------------------------------------------------
def canonicalize(raw: str) -> str:
    """The FILM's own toy canonicalizer: parse JSON, drop float-ness of whole
    numbers, sort keys, no whitespace. It is not Ghost-Ark's canonicalizer.
    It exists to show that two different byte strings can share one digest."""
    obj = json.loads(raw)

    def norm(v):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        if isinstance(v, dict):
            return {k: norm(v[k]) for k in sorted(v)}
        if isinstance(v, list):
            return [norm(x) for x in v]
        return v
    return json.dumps(norm(obj), separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def bind_receipt(F: Facts, C: dict) -> None:
    c = C["GA-001"]
    raw_a = '{"amount": 1.0, "to": "acct-7"}'
    raw_b = '{"to": "acct-7", "amount": 1}'
    can_a, can_b = canonicalize(raw_a), canonicalize(raw_b)
    assert can_a == can_b
    d = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
    assert d(raw_a) != d(raw_b) and d(can_a) == d(can_b)
    F.add("RECEIPT.raw_a", raw_a, "CONSTRUCTED", "this script; a toy receipt payload", "GA-001")
    F.add("RECEIPT.raw_b", raw_b, "CONSTRUCTED", "this script; same fields, different bytes (key order, 1.0 vs 1)", "GA-001")
    F.add("RECEIPT.canonical", can_a, "CONSTRUCTED", "this script's toy canonicalizer (sort keys, whole floats → ints)", "GA-001",
          "the film's own pipeline, not Ghost-Ark's; nothing is built on the lab's repository")
    F.add("RECEIPT.digest_raw_a", d(raw_a), "DERIVED", "sha256 of RECEIPT.raw_a bytes", "GA-001")
    F.add("RECEIPT.digest_raw_b", d(raw_b), "DERIVED", "sha256 of RECEIPT.raw_b bytes", "GA-001")
    F.add("RECEIPT.digest_canonical", d(can_a), "DERIVED", "sha256 of RECEIPT.canonical bytes — identical for both inputs", "GA-001")
    F.add("GA-001.proposition", " ".join(c["proposition"].split()), "DOCUMENT", "claims.yaml:GA-001.proposition (bound to the S2 Lab thesis at its commit)", "GA-001")
    F.add("GA-001.non_claims", [" ".join(x.split()) for x in c["non_claims"]], "DOCUMENT", "claims.yaml:GA-001.non_claims", "GA-001")
    F.add("GA-001.support_commit", c["support"]["commit"], "REGISTRY", "claims.yaml:GA-001.support.commit", "GA-001")
    F.add("GA-001.support_url", c["support"]["url"], "REGISTRY", "claims.yaml:GA-001.support.url", "GA-001")


# --------------------------------------------------------------------------
# The registry itself: review windows (freshness), statuses
# --------------------------------------------------------------------------
def bind_registry(F: Facts, data: dict) -> None:
    rows = []
    for c in data["claims"]:
        last = date.fromisoformat(str(c["last_reviewed"]))
        window = int(c["review_window_days"])
        rows.append({
            "id": c["id"],
            "last_reviewed": last.isoformat(),
            "review_window_days": window,
            "review_due": (last + timedelta(days=window)).isoformat(),
            "evidential_status": c["dimensions"]["evidential_status"],
            "maturity": c["dimensions"]["maturity"],
            "provenance": c["dimensions"]["provenance"],
        })
    F.add("REGISTRY.claims", rows, "REGISTRY", "claims.yaml: last_reviewed + review_window_days per claim", None,
          "passing a review window means review is due and the build fails; it does not adjudicate falsity")
    F.add("REGISTRY.version", data["version"], "REGISTRY", "claims.yaml:version")
    F.add("REGISTRY.last_owner_review", str(data["last_owner_review"]), "REGISTRY", "claims.yaml:last_owner_review")


def build() -> dict:
    data, C = claims_by_id()
    F = Facts()
    bind_cc(F, C)
    bind_parity(F, C)
    bind_census(F, C)
    bind_bells(F, C)
    bind_msbench(F, C)
    bind_af(F, C)
    bind_receipt(F, C)
    bind_registry(F, data)
    return {
        "_generated_by": "scripts/films/bind_facts.py — DO NOT EDIT; regenerate and re-inspect the films",
        "_inputs": {
            "claims.yaml": sha256_file(ROOT / "claims.yaml"),
            "census.yaml": sha256_file(ROOT / "census.yaml"),
        },
        "_kinds": ["OBSERVED", "DERIVED", "PROVED", "CONSTRUCTED", "REGISTRY", "DOCUMENT"],
        "facts": F.items,
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if the committed facts file is stale")
    args = ap.parse_args()
    text = render(build())
    if args.check:
        if not OUT.exists():
            print(f"FAIL  {OUT.relative_to(ROOT)} missing — run scripts/films/bind_facts.py")
            return 1
        if OUT.read_text() != text:
            print(f"FAIL  {OUT.relative_to(ROOT)} is stale against claims.yaml/census.yaml — regenerate and re-inspect every film that reads it")
            return 1
        n = len(json.loads(text)["facts"])
        print(f"ok    film facts current: {n} bound facts derived from the registries")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(json.loads(text)['facts'])} facts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
