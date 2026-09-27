#!/usr/bin/env python3
"""Readiness as a meet: a candidate dispatch decision over the worlds still compatible with what is known.

A candidate, not a rule. Nothing here is wired into scripts/verification_manifest.py
or counted by scripts/cadence.py. PROTOCOL.md states the test that can kill it.

Model
  A case declares:
    variables     each unresolved fact, as a question with an enumerated answer set.
                  This is the only source of uncertainty. An obligation cannot be unknown
                  except through a named variable (13.04: a band "must correspond to a named
                  unresolved fact", never to the assessor's discomfort).
    constraints   formulas every compatible world satisfies (what the evidence rules out).
    obligations   A I T Q V X, each {"holds": formula, "evidence": text}. All six are
                  required. An obligation asserted true without evidence is rejected, so an
                  obligation nobody established cannot pass by being left out (default-deny).
    observations  what could be looked at next: the variables it settles and a cost.
    interventions optional: what could be changed, and the obligation formulas it replaces.

  Omega(K) = assignments of the variables satisfying every constraint.
  C(w) = A & I & T & Q & V & X at world w.

Decisions
  INCONSISTENT  Omega(K) is empty: the evidence contradicts itself. Under the plain
                definition READY := forall w in Omega(K). C(w), an empty Omega(K) is READY
                vacuously; here it never is.
  READY         C holds in every compatible world.
  HOLD          C holds in no compatible world. No observation can admit the dispatch;
                only an intervention can (change the prompt, the grant or the environment).
  REVIEW        C holds in some compatible worlds and not in others. An observation can
                decide it; the case names which.

Kleene projection
  Each obligation's status is 1 if it holds in every world, 0 if in none, U otherwise;
  the Kleene meet is min under 0 < U < 1. Because forall distributes over & and exists
  does not:
    meet = 1  <=>  READY
    meet = 0   =>  HOLD
    REVIEW     =>  meet = U
  The one disagreement is meet = U with HOLD: obligations that are each satisfiable but not
  jointly, because they depend on a shared variable. The evaluator reports it as a gap,
  with the minimal conflicting sets, rather than returning the projection's REVIEW.

Formulas (JSON)
  true | false | {"var": NAME, "in": [VALUE, ...]} | {"all": [F, ...]} | {"any": [F, ...]} | {"not": F}

Exit codes: 0 every case evaluated; 1 a case is malformed or a self-test failed.

Usage
  python3 readiness_meet.py CASE.json [CASE.json ...] [--json]
  python3 readiness_meet.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from pathlib import Path

OBLIGATIONS = ("A", "I", "T", "Q", "V", "X")
NAMES = {
    "A": "authorization: a covering grant, issued by a principal entitled to issue it",
    "I": "identity: execution is bound to the subject admitted (bytes, change set, target)",
    "T": "truth roots: the premises are the live roots' state and the executor can read them",
    "Q": "requirements: every required check currently passes, evaluated now, per check",
    "V": "verification: completion is observable by a check the builder does not grade alone",
    "X": "environment: the tools, runtime and access the task needs exist where it runs",
}
ONE, ZERO, UNK = "1", "0", "U"
ORDER = {ZERO: 0, UNK: 1, ONE: 2}

# 13.04 v1.0 codes -> the obligation each one is evidence about, or the layer it belongs to
# when it is not an admission obligation. ROUTING: efficiency and model choice; it can make a
# run slower or costlier, not inadmissible. CONTROLLER: a property of the controller, not of
# the prompt (13.11 REVIEW F5). A code naming two parts is split, never averaged.
MAPPING_1304 = {
    "V01": ("T",), "V02": ("A",), "V03": ("A",), "V04": ("A",), "V05": ("V",),
    "V06": ("X",), "V07": ("Q",), "V08": ("I",), "V09": ("A", "ROUTING"), "V10": ("T",),
    "A01": ("ROUTING", "T"), "A02": ("V",), "A03": ("ROUTING",), "A04": ("V",),
    "C01": ("V",), "C02": ("ROUTING",), "C03": ("T",), "C04": ("ROUTING",),
    "core.goal": ("V",), "core.evidence": ("T",), "core.boundary": ("A",),
    "core.verification": ("V",), "core.truth_state": ("T",), "core.scope": ("A",),
    "astra.context_economy": ("ROUTING",), "astra.completion": ("V",),
    "astra.decision_boundaries": ("A",), "astra.tool_runtime": ("X",),
    "astra.validation": ("V",), "astra.freshness": ("CONTROLLER",), "astra.effort": ("ROUTING",),
    "claude.task_decomposition": ("ROUTING",), "claude.truth_root_relevance": ("T",),
    "claude.evaluator_need": ("V",), "claude.harness_simplicity": ("ROUTING",),
    "claude.subagent": ("ROUTING",), "claude.permission_sandbox": ("A", "X"),
    "claude.handoff_receipt": ("I",), "claude.long_run_context": ("ROUTING",),
    "source_freshness": ("CONTROLLER",),
}


class CaseError(ValueError):
    pass


# ---------------------------------------------------------------- formulas

def holds(f, world: dict) -> bool:
    if f is True or f is False:
        return f
    if not isinstance(f, dict) or len(f) == 0:
        raise CaseError(f"not a formula: {f!r}")
    if "var" in f:
        return world[f["var"]] in f["in"]
    if "all" in f:
        return all(holds(g, world) for g in f["all"])
    if "any" in f:
        return any(holds(g, world) for g in f["any"])
    if "not" in f:
        return not holds(f["not"], world)
    raise CaseError(f"unknown formula operator in {f!r}")


def variables_of(f) -> set[str]:
    if f is True or f is False:
        return set()
    if "var" in f:
        return {f["var"]}
    for op in ("all", "any"):
        if op in f:
            return set().union(*(variables_of(g) for g in f[op])) if f[op] else set()
    if "not" in f:
        return variables_of(f["not"])
    raise CaseError(f"unknown formula operator in {f!r}")


def _check_formula(f, variables: dict, where: str) -> None:
    if f is True or f is False:
        return
    if not isinstance(f, dict) or len(f) != (2 if "var" in f else 1):
        raise CaseError(f"{where}: malformed formula {f!r}")
    if "var" in f:
        name, vals = f["var"], f.get("in")
        if name not in variables:
            raise CaseError(f"{where}: undeclared variable {name!r}")
        if not isinstance(vals, list) or not vals:
            raise CaseError(f"{where}: {name!r} needs a non-empty 'in' list")
        bad = [v for v in vals if v not in variables[name]]
        if bad:
            raise CaseError(f"{where}: {bad} not in the domain of {name!r}")
        return
    op = next(iter(f))
    if op in ("all", "any"):
        if not isinstance(f[op], list):
            raise CaseError(f"{where}: {op!r} takes a list")
        for i, g in enumerate(f[op]):
            _check_formula(g, variables, f"{where}.{op}[{i}]")
    elif op == "not":
        _check_formula(f["not"], variables, f"{where}.not")
    else:
        raise CaseError(f"{where}: unknown operator {op!r}")


# ---------------------------------------------------------------- cases

def validate(case: dict, *, default_deny: bool = True) -> None:
    cid = case.get("id", "?")
    variables = case.get("variables", {})
    if not isinstance(variables, dict):
        raise CaseError(f"{cid}: variables must be a mapping")
    for name, spec in variables.items():
        dom = spec.get("domain") if isinstance(spec, dict) else None
        if not isinstance(dom, list) or len(dom) < 1 or len(set(map(str, dom))) != len(dom):
            raise CaseError(f"{cid}: variable {name!r} needs a non-empty domain of distinct values")
        if not (isinstance(spec.get("question"), str) and spec["question"].strip()):
            raise CaseError(f"{cid}: variable {name!r} must state the question it stands for")
    doms = {n: s["domain"] for n, s in variables.items()}
    for i, c in enumerate(case.get("constraints", [])):
        _check_formula(c.get("holds") if isinstance(c, dict) else c, doms, f"{cid}.constraints[{i}]")
    obls = case.get("obligations", {})
    extra = set(obls) - set(OBLIGATIONS)
    if extra:
        raise CaseError(f"{cid}: unknown obligations {sorted(extra)}")
    for o in OBLIGATIONS:
        if o not in obls:
            if default_deny:
                raise CaseError(f"{cid}: obligation {o} is missing; an obligation nobody "
                                f"established cannot pass by being left out")
            continue
        spec = obls[o]
        if not isinstance(spec, dict) or "holds" not in spec:
            raise CaseError(f"{cid}: obligation {o} needs a 'holds' formula")
        _check_formula(spec["holds"], doms, f"{cid}.obligations.{o}")
        if default_deny and not (isinstance(spec.get("evidence"), str) and spec["evidence"].strip()):
            raise CaseError(f"{cid}: obligation {o} states no evidence; an unsupported "
                            f"assertion is not an establishment")
    for name, ob in case.get("observations", {}).items():
        rv = ob.get("reveals")
        if not isinstance(rv, list) or not rv or any(v not in doms for v in rv):
            raise CaseError(f"{cid}: observation {name!r} must reveal declared variables")
        if not isinstance(ob.get("cost", 1), (int, float)) or ob.get("cost", 1) < 0:
            raise CaseError(f"{cid}: observation {name!r} has a bad cost")
    for name, iv in case.get("interventions", {}).items():
        repl = iv.get("replaces", {})
        if not isinstance(repl, dict) or not repl or set(repl) - set(OBLIGATIONS):
            raise CaseError(f"{cid}: intervention {name!r} must replace named obligations")
        for o, spec in repl.items():
            _check_formula(spec["holds"], doms, f"{cid}.interventions.{name}.{o}")


def worlds(case: dict) -> list[dict]:
    variables = case.get("variables", {})
    names = sorted(variables)
    out = []
    for combo in itertools.product(*(variables[n]["domain"] for n in names)):
        w = dict(zip(names, combo))
        if all(holds(c.get("holds") if isinstance(c, dict) else c, w)
               for c in case.get("constraints", [])):
            out.append(w)
    return out


def _formula(case: dict, o: str):
    spec = case.get("obligations", {}).get(o)
    return True if spec is None else spec["holds"]   # reachable only with default_deny off


def _status(values: list[bool]) -> str:
    if all(values):
        return ONE          # also the vacuous value on an empty set; handled by the caller
    if not any(values):
        return ZERO
    return UNK


def decide(case: dict, omega: list[dict]) -> str:
    if not omega:
        return "INCONSISTENT"
    c = [all(holds(_formula(case, o), w) for o in OBLIGATIONS) for w in omega]
    if all(c):
        return "READY"
    if not any(c):
        return "HOLD"
    return "REVIEW"


def kleene(case: dict, omega: list[dict]) -> tuple[dict, str]:
    st = {o: _status([holds(_formula(case, o), w) for w in omega]) for o in OBLIGATIONS}
    meet = min(st.values(), key=ORDER.__getitem__)
    return st, {ONE: "READY", ZERO: "HOLD", UNK: "REVIEW"}[meet]


def conflict_sets(case: dict, omega: list[dict], candidates: list[str]) -> list[list[str]]:
    """Minimal sets of obligations that no compatible world satisfies together."""
    found: list[set] = []
    for r in range(2, len(candidates) + 1):
        for s in itertools.combinations(candidates, r):
            if any(set(s) >= f for f in found):
                continue
            if not any(all(holds(_formula(case, o), w) for o in s) for w in omega):
                found.append(set(s))
    return [sorted(f, key=OBLIGATIONS.index) for f in found]


def rank_observations(case: dict, omega: list[dict]) -> list[dict]:
    """Minimax: fewest worlds left in REVIEW after the observation, then cost, then name."""
    ranked = []
    for name, ob in sorted(case.get("observations", {}).items()):
        keyvars = ob["reveals"]
        cells: dict[tuple, list[dict]] = {}
        for w in omega:
            cells.setdefault(tuple(w[v] for v in keyvars), []).append(w)
        outcome = {}
        left = 0
        for key, cell in sorted(cells.items(), key=lambda kv: tuple(map(str, kv[0]))):
            d = decide(case, cell)
            outcome[" & ".join(f"{v}={k}" for v, k in zip(keyvars, key))] = d
            if d == "REVIEW":
                left += len(cell)
        ranked.append({"observation": name, "reveals": keyvars, "cost": ob.get("cost", 1),
                       "decisive": left == 0, "worlds_left_in_review": left,
                       "outcomes": outcome, "how": ob.get("how", "")})
    ranked.sort(key=lambda r: (r["worlds_left_in_review"], r["cost"], r["observation"]))
    return ranked


def evaluate(case: dict, *, default_deny: bool = True) -> dict:
    validate(case, default_deny=default_deny)
    omega = worlds(case)
    decision = decide(case, omega)
    status, k_decision = kleene(case, omega)
    deps = {o: sorted(variables_of(_formula(case, o))) for o in OBLIGATIONS}
    out = {
        "id": case.get("id"),
        "decision": decision,
        "worlds": {"compatible": len(omega),
                   "admissible": sum(all(holds(_formula(case, o), w) for o in OBLIGATIONS)
                                     for w in omega)},
        "obligations": {o: {"status": status[o] if omega else "EMPTY",
                            "depends_on": deps[o]} for o in OBLIGATIONS},
        "kleene_projection": k_decision,
        "gap": None,
    }
    if decision == "INCONSISTENT":
        out["gap"] = ("the evidence admits no world; forall over an empty set is true, so "
                      "the plain definition and the Kleene meet both return READY here")
        out["next"] = "find the contradiction among the constraints; no dispatch decision exists yet"
        return out
    if decision != k_decision:
        out["gap"] = (f"the Kleene meet says {k_decision}; the world semantics says {decision}: "
                      f"obligations that are each satisfiable are not jointly satisfiable")
    if decision == "HOLD":
        forced = [o for o in OBLIGATIONS if status[o] == ZERO]
        loose = [o for o in OBLIGATIONS if status[o] != ONE]
        out["hold"] = {
            "fails_in_every_world": forced,
            "conflict_sets": [] if forced else conflict_sets(case, omega, loose),
            "resolved_by": "intervention only; no observation of the declared variables admits it",
        }
        out["interventions"] = _interventions(case, omega)
    elif decision == "REVIEW":
        ranked = rank_observations(case, omega)
        out["next_observation"] = ranked[0] if ranked else None
        out["observations_ranked"] = ranked
        if not ranked:
            out["next"] = "REVIEW with no declared observation: declare one, or this is a HOLD in practice"
    return out


def _apply(case: dict, names: tuple) -> dict:
    changed = json.loads(json.dumps(case))
    for name in names:
        for o, spec in case["interventions"][name]["replaces"].items():
            changed["obligations"][o] = spec
    return changed


def _interventions(case: dict, omega: list[dict]) -> list[dict]:
    """Minimal sets of declared interventions that leave HOLD, and where each set lands.

    A set is reported only if no proper subset already leaves HOLD. Its decision is
    READY or REVIEW; a REVIEW names the observation still owed after the change.
    """
    names = sorted(case.get("interventions", {}))
    res, admitted = [], []
    for r in range(1, len(names) + 1):
        for s in itertools.combinations(names, r):
            if any(set(s) >= a for a in admitted):
                continue
            changed = _apply(case, s)
            d = decide(changed, omega)
            if d == "HOLD":
                continue
            admitted.append(set(s))
            entry = {"interventions": list(s), "decision_after": d,
                     "what": [case["interventions"][n].get("what", "") for n in s]}
            if d == "REVIEW":
                ranked = rank_observations(changed, omega)
                entry["then_observe"] = ranked[0]["observation"] if ranked else None
            res.append(entry)
    return res


# ---------------------------------------------------------------- rendering

def certificate(result: dict, case: dict) -> str:
    lines = [f"{result['id']}: {result['decision']}  "
             f"(worlds compatible {result['worlds']['compatible']}, "
             f"admissible {result['worlds']['admissible']}; "
             f"Kleene projection {result['kleene_projection']})"]
    for o in OBLIGATIONS:
        ob = result["obligations"][o]
        dep = f"  depends on {', '.join(ob['depends_on'])}" if ob["depends_on"] else ""
        ev = case["obligations"][o].get("evidence", "") if o in case.get("obligations", {}) else ""
        lines.append(f"  {o} {ob['status']:>5}{dep}")
        if ev:
            lines.append(f"        {ev}")
    if result.get("gap"):
        lines.append(f"  GAP  {result['gap']}")
    if result["decision"] == "HOLD":
        h = result["hold"]
        if h["fails_in_every_world"]:
            lines.append(f"  HOLD fails in every world: {', '.join(h['fails_in_every_world'])}")
        for cs in h["conflict_sets"]:
            lines.append(f"  HOLD jointly unsatisfiable: {' & '.join(cs)}")
        ivs = result.get("interventions", [])
        if case.get("interventions") and not ivs:
            lines.append("  no declared intervention, alone or combined, leaves HOLD")
        for iv in ivs:
            then = f", then observe {iv['then_observe']}" if iv.get("then_observe") else ""
            lines.append(f"  change {' + '.join(iv['interventions'])} -> {iv['decision_after']}{then}")
    if result["decision"] == "REVIEW" and result.get("next_observation"):
        n = result["next_observation"]
        tag = "decisive" if n["decisive"] else f"{n['worlds_left_in_review']} world(s) still in REVIEW"
        lines.append(f"  NEXT OBSERVATION {n['observation']} (cost {n['cost']}, {tag})")
        if n.get("how"):
            lines.append(f"        {n['how']}")
        for k, d in n["outcomes"].items():
            lines.append(f"        if {k}: {d}")
    return "\n".join(lines)


def load_cases(path: Path) -> list[dict]:
    doc = json.loads(path.read_text())
    return doc["cases"] if isinstance(doc, dict) and "cases" in doc else (
        doc if isinstance(doc, list) else [doc])


# ---------------------------------------------------------------- self-test

def _random_formula(rng: random.Random, doms: dict, depth: int = 0):
    r = rng.random()
    if depth > 1 or r < 0.15:
        return rng.random() < 0.6
    if r < 0.7:
        v = rng.choice(sorted(doms))
        k = rng.randint(1, len(doms[v]))
        return {"var": v, "in": rng.sample(doms[v], k)}
    op = rng.choice(["all", "any", "not"])
    if op == "not":
        return {"not": _random_formula(rng, doms, depth + 1)}
    return {op: [_random_formula(rng, doms, depth + 1) for _ in range(rng.randint(1, 3))]}


def _random_case(rng: random.Random, i: int) -> dict:
    doms = {f"v{j}": [f"a{k}" for k in range(rng.randint(2, 3))] for j in range(rng.randint(1, 3))}
    return {
        "id": f"random-{i}",
        "variables": {v: {"question": f"what is {v}?", "domain": d} for v, d in doms.items()},
        "constraints": [{"holds": _random_formula(rng, doms)} for _ in range(rng.randint(0, 2))],
        "obligations": {o: {"holds": _random_formula(rng, doms), "evidence": "generated"}
                        for o in OBLIGATIONS},
        "observations": {f"see-{v}": {"reveals": [v], "cost": 1} for v in doms}
                        | {"see-all": {"reveals": sorted(doms), "cost": 3}},
    }


def selftest(cases_dir: Path | None = None, n: int = 4000, seed: int = 20260927) -> int:
    rng = random.Random(seed)
    tally = {"READY": 0, "HOLD": 0, "REVIEW": 0, "INCONSISTENT": 0, "gap": 0}
    problems = []
    for i in range(n):
        case = _random_case(rng, i)
        omega = worlds(case)
        d = decide(case, omega)
        _, k = kleene(case, omega)
        tally[d] += 1
        if omega:
            if (k == "READY") != (d == "READY"):
                problems.append(f"{case['id']}: Kleene READY and world READY disagree")
            if k == "HOLD" and d != "HOLD":
                problems.append(f"{case['id']}: Kleene HOLD without world HOLD")
            if d == "REVIEW" and k != "REVIEW":
                problems.append(f"{case['id']}: world REVIEW but Kleene {k}")
            if d != k:
                tally["gap"] += 1
                if not (k == "REVIEW" and d == "HOLD"):
                    problems.append(f"{case['id']}: a gap other than Kleene REVIEW / world HOLD")
            if d == "REVIEW":
                r = evaluate(case)
                if not any(x["decisive"] for x in r["observations_ranked"]):
                    problems.append(f"{case['id']}: observing every variable was not decisive")
            # learning never reverses a decided case: add one more constraint
            extra = {"holds": _random_formula(rng, {v: s["domain"] for v, s in case["variables"].items()})}
            narrower = dict(case, constraints=case["constraints"] + [extra])
            d2 = decide(narrower, worlds(narrower))
            if d in ("READY", "HOLD") and d2 not in (d, "INCONSISTENT"):
                problems.append(f"{case['id']}: {d} became {d2} after the evidence narrowed")
        else:
            if d != "INCONSISTENT":
                problems.append(f"{case['id']}: empty Omega not reported INCONSISTENT")
            if k != "READY":
                problems.append(f"{case['id']}: the vacuous Kleene READY was expected on empty Omega")
    print(f"properties over {n} generated cases (seed {seed}): {tally}")
    for p in problems[:20]:
        print("FAIL ", p)

    codes = ([f"V{i:02d}" for i in range(1, 11)] + [f"A{i:02d}" for i in range(1, 5)]
             + [f"C{i:02d}" for i in range(1, 5)])
    unmapped = [c for c in codes if c not in MAPPING_1304]
    layers = set(OBLIGATIONS) | {"ROUTING", "CONTROLLER"}
    stray = sorted(k for k, v in MAPPING_1304.items() if set(v) - layers)
    if unmapped or stray:
        problems.append(f"13.04 mapping: unmapped {unmapped}, unknown layers in {stray}")
    print(f"13.04 codes mapped: {len(codes) - len(unmapped)}/{len(codes)}; "
          f"dimensions mapped: {len(MAPPING_1304) - len(codes)}")

    named = run_named_controls(cases_dir)
    for line in named["lines"]:
        print(line)
    ok = not problems and named["ok"]
    print("selftest:", "ok" if ok else "FAILED")
    return 0 if ok else 1


def run_named_controls(cases_dir: Path | None) -> dict:
    """Each rule of the evaluator, disabled in turn, must flip at least one named control.

    A rule that no control can see is dead weight; it is reported, not kept silently.
    """
    base = Path(__file__).resolve().parent / "cases" if cases_dir is None else cases_dir
    controls = json.loads((base / "controls.json").read_text())["cases"]
    expected = {c["id"]: c["expect"] for c in controls}

    def run_all(variant: str) -> dict:
        got = {}
        for c in controls:
            try:
                got[c["id"]] = _decide_variant(c, variant)
            except CaseError:
                got[c["id"]] = "REJECTED"
        return got

    lines = []
    ok = True
    baseline = run_all("baseline")
    for cid, want in expected.items():
        if baseline[cid] != want:
            ok = False
            lines.append(f"FAIL  control {cid}: {baseline[cid]}, expected {want}")
    lines.append(f"named controls: {sum(baseline[c] == expected[c] for c in expected)}/{len(expected)} as expected")
    for variant, rule in VARIANTS.items():
        got = run_all(variant)
        flipped = sorted(c for c in expected if got[c] != baseline[c])
        if not flipped:
            ok = False
        lines.append(f"  disable {rule:<58} flips {', '.join(flipped) or 'NOTHING (rule unearned)'}")
    return {"ok": ok, "lines": lines}


VARIANTS = {
    "no_empty_check": "an empty Omega is INCONSISTENT, never READY",
    "unknown_is_one": "an unknown obligation is not a satisfied one",
    "unknown_is_zero": "an unknown obligation is not a failed one (a veto)",
    "missing_is_true": "a missing obligation is rejected, not assumed",
    "no_evidence_ok": "an obligation asserted without evidence is rejected",
    "kleene_decides": "the world semantics decides, not the Kleene projection",
}


def _decide_variant(case: dict, variant: str) -> str:
    if variant == "missing_is_true":
        validate(case, default_deny=False)
        if any(o not in case.get("obligations", {}) for o in OBLIGATIONS):
            return decide(case, worlds(case))
        # fall through to the evidence rule, which this variant keeps
    if variant == "no_evidence_ok":
        validate(case, default_deny=False)
        if any(o not in case.get("obligations", {}) for o in OBLIGATIONS):
            raise CaseError("missing obligation")
        return decide(case, worlds(case))
    validate(case)
    omega = worlds(case)
    if variant == "no_empty_check" and not omega:
        return "READY"
    if variant == "kleene_decides":
        return kleene(case, omega)[1] if omega else "INCONSISTENT"
    if variant in ("unknown_is_one", "unknown_is_zero") and omega:
        st, _ = kleene(case, omega)
        if any(v == UNK for v in st.values()):
            sub = ONE if variant == "unknown_is_one" else ZERO
            meet = min((sub if v == UNK else v for v in st.values()), key=ORDER.__getitem__)
            return {ONE: "READY", ZERO: "HOLD"}[meet]
    return decide(case, omega)


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="*", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cases:
        ap.error("name a case file, or --selftest")
    results, rc = [], 0
    for path in a.cases:
        for case in load_cases(path):
            try:
                r = evaluate(case)
            except CaseError as e:
                print(f"MALFORMED {e}", file=sys.stderr)
                rc = 1
                continue
            results.append(r)
            if not a.json:
                print(certificate(r, case))
                print()
    if a.json:
        print(json.dumps(results, indent=1, sort_keys=True))
    return rc


if __name__ == "__main__":
    sys.exit(main())
