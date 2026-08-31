#!/usr/bin/env python3
"""Verify census_protocol_v1.yaml, and that it agrees with the enforcer.

A protocol document that drifts from the code enforcing it is worse than no
document: it tells a reader rules the repository does not actually apply. This
gate checks the protocol's shape and then asserts that every vocabulary it
defines is exactly the vocabulary scripts/verify_census.py enforces.

Run: python scripts/verify_census_protocol.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / "census_protocol_v1.yaml"

spec = importlib.util.spec_from_file_location("vc", ROOT / "scripts" / "verify_census.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)

REQUIRED_STATES = {"DISCOVERED", "ELIGIBILITY_PENDING", "ELIGIBLE", "INELIGIBLE",
                   "VERIFICATION_PENDING", "VERIFIED", "STALE", "SUPERSEDED"}
REQUIRED_RUNGS = {"L1", "L2", "L3", "L4", "L5", "L6"}
REQUIRED_NEGATIVE_KINDS = {"NOT_PUBLISHED", "NOT_FOUND", "NOT_PRESERVED",
                           "NOT_RETRIEVABLE_IN_THIS_ENVIRONMENT",
                           "CANNOT_BE_RECONSTRUCTED", "NOT_APPLICABLE"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def main() -> int:
    if not PROTOCOL.exists():
        print(f"FAIL  {PROTOCOL.name} is missing — v1 has no prospective rules")
        return 1
    p = yaml.safe_load(PROTOCOL.read_text())

    meta = p.get("protocol") or {}
    if meta.get("status") != "prospective_frozen":
        fail("protocol.status must be prospective_frozen")
    if meta.get("written_before_first_v1_observation") is not True:
        fail("protocol.written_before_first_v1_observation must be true — the "
             "whole point is that the rules predate the observations")
    else:
        ok("protocol declares itself prospective and pre-observation")

    # A. universe
    u = p.get("universe") or {}
    for field in ("unit_of_observation", "counting_rule"):
        if not str(u.get(field) or "").strip():
            fail(f"universe.{field} must be non-empty")
    if len(u.get("inclusion") or []) < 5:
        fail("universe.inclusion must enumerate the criteria")
    if len(u.get("exclusions") or []) < 8:
        fail("universe.exclusions must enumerate the named exclusions and edge rules")
    for ex in u.get("exclusions") or []:
        if not ex.get("key") or not str(ex.get("text") or "").strip():
            fail(f"universe.exclusions entry needs key and text: {ex}")
    inacc = [e for e in (u.get("exclusions") or [])
             if e.get("key") == "inaccessible_evidence"]
    if not inacc:
        fail("universe.exclusions must name inaccessible_evidence explicitly")
    elif "never counted as" not in str(inacc[0].get("text", "")).lower():
        fail("inaccessible_evidence must state that it is never counted as a "
             "negative finding")
    else:
        ok("inaccessible evidence is explicitly barred from becoming absence")
    if len(u.get("edge_cases") or []) < 3:
        fail("universe.edge_cases must cover the known hard cases")
    falsifier = [c for c in (u.get("edge_cases") or [])
                 if c.get("case") == "artifact_publishes_complete_joint"]
    if not falsifier or not str(falsifier[0].get("headline_effect") or "").strip():
        fail("the protocol must state that enough complete-joint artifacts would "
             "falsify the headline — the falsification route may not be hidden")
    else:
        ok("the falsification route for the headline is stated in the protocol")

    # B. state machine
    sm = p.get("state_machine") or {}
    states = sm.get("states") or {}
    if set(states) != REQUIRED_STATES:
        fail(f"state_machine.states must be exactly {sorted(REQUIRED_STATES)}; "
             f"got {sorted(states)}")
    else:
        ok(f"state machine defines all {len(REQUIRED_STATES)} states")
    counted = [n for n, s in states.items() if s.get("counts_toward_totals")]
    if counted != ["VERIFIED"]:
        fail(f"only VERIFIED may count toward totals; got {counted}")
    else:
        ok("only VERIFIED records count toward totals")
    if "never converted into absence" not in str(sm.get("law") or "").lower():
        fail("state_machine.law must forbid converting inability to verify into absence")
    else:
        ok("state machine law forbids inability-to-verify becoming absence")

    # C. ladder
    ladder = p.get("disclosure_ladder") or {}
    rungs = ladder.get("rungs") or {}
    if set(rungs) != REQUIRED_RUNGS:
        fail(f"disclosure_ladder.rungs must be exactly {sorted(REQUIRED_RUNGS)}")
    else:
        ok("disclosure ladder defines L1-L6")
    for name, rung in rungs.items():
        if not str(rung.get("licenses") or "").strip():
            fail(f"rung {name} must say what it licenses")
    if not str((rungs.get("L6") or {}).get("caveat") or "").strip():
        fail("L6 must carry the caveat that an OR union is not automatically the "
             "deployed system's behaviour")
    else:
        ok("L6 records that an OR union is not automatically the deployed system")
    neg = ladder.get("negative_kinds") or {}
    if set(neg) != REQUIRED_NEGATIVE_KINDS:
        fail(f"negative_kinds must be exactly {sorted(REQUIRED_NEGATIVE_KINDS)}; "
             f"got {sorted(neg)}")
    else:
        ok(f"all {len(REQUIRED_NEGATIVE_KINDS)} kinds of negative are kept distinct")

    # D. reconstruction classes must equal what the enforcer accepts
    classes = {k for k in (p.get("reconstruction_classes") or {}) if k != "law"}
    if classes != vc.RECONSTRUCTION_CLASSES:
        fail("reconstruction_classes in the protocol do not match the classes "
             f"verify_census.py enforces: protocol={sorted(classes)} "
             f"enforcer={sorted(vc.RECONSTRUCTION_CLASSES)}")
    else:
        ok("reconstruction classes match the enforcer exactly")
    law = str((p.get("reconstruction_classes") or {}).get("law") or "").lower()
    if "never be assigned from a failed retrieval" not in law:
        fail("reconstruction_classes.law must forbid assigning a class from a "
             "failed retrieval")
    else:
        ok("a reconstruction class may not be assigned from a failed retrieval")

    # E. preservation states must equal what the enforcer accepts
    pres = set(p.get("preservation_states") or {})
    if pres != vc.PRESERVATION_STATES:
        fail("preservation_states do not match the enforcer: "
             f"protocol={sorted(pres)} enforcer={sorted(vc.PRESERVATION_STATES)}")
    else:
        ok("preservation states match the enforcer exactly")

    # F. falsification must stay quantified and pre-registered
    f = p.get("falsification") or {}
    if not str(f.get("headline_claim") or "").strip():
        fail("falsification.headline_claim must state the claim that can be false")
    qt = f.get("quantified_threshold") or {}
    if not isinstance(qt.get("artifacts_required_from_v0"), int):
        fail("falsification.quantified_threshold.artifacts_required_from_v0 must be "
             "an integer — a falsification route without a number is a gesture")
    else:
        ok(f"falsification is quantified: {qt['artifacts_required_from_v0']} further "
           "complete-joint artifacts would make the headline false")
    if len(f.get("downgrade_conditions") or []) < 3:
        fail("falsification.downgrade_conditions must pre-register when this "
             "programme stops being worth continuing")
    else:
        ok(f"{len(f['downgrade_conditions'])} downgrade conditions pre-registered")
    if not str(f.get("termination_condition") or "").strip():
        fail("falsification.termination_condition must be pre-registered")
    rs = (f.get("rule_sensitivity_measured_at_v0") or {}).get("rules") or []
    if len(rs) < 4:
        fail("falsification.rule_sensitivity_measured_at_v0.rules must record the "
             "headline under alternative defensible inclusion rules")
    else:
        ok(f"headline recomputed under {len(rs)} alternative inclusion rules")

    if failures:
        print(f"\nProtocol verification failed: {len(failures)} problem(s).")
        return 1
    print("\nProtocol v1 verified: prospective, complete, and identical to the "
          "vocabulary the census enforcer applies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
