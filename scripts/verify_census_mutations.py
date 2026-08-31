#!/usr/bin/env python3
"""Mutation tests for the census invariants.

A gate that has never been observed to fail is not evidence that the property
holds; it is evidence that nobody checked. Each case below breaks one property
in memory and asserts that verify_census.py rejects it, then asserts the
unmutated census still passes. Nothing on disk is modified.

Run: python scripts/verify_census_mutations.py
"""
from __future__ import annotations

import copy
import importlib.util
import io
import contextlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("vc", ROOT / "scripts" / "verify_census.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)

BASE = yaml.safe_load((ROOT / "census.yaml").read_text())


def run_checks(data: dict) -> list[str]:
    """Run the row/lock invariants over `data`, returning failures."""
    vc.failures = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            vc.check_snapshot_and_lock(data)
            for row in data.get("benchmarks") or []:
                if row.get("status") == "examined":
                    vc.check_protocol_annotations(row, row.get("id", "?"))
        except SystemExit:
            pass
    return list(vc.failures)


def mutate_silent_history_edit(d):
    """The headline defect this lock exists for: quietly change a past row."""
    d["benchmarks"][0]["classification_reason"] = "quietly rewritten"
    return d


def mutate_unverified_to_absent(d):
    """Promote an unestablished row to a negative finding."""
    for r in d["benchmarks"]:
        if r.get("reconstruction", {}).get("class") == "UNVERIFIED":
            r["reconstruction"]["class"] = "NOT_IDENTIFIABLE"
            break
    return d


def mutate_overclaim_reconstructible(d):
    """Claim exact reconstruction without an item-level release."""
    for r in d["benchmarks"]:
        if r.get("joint_scope") == "none":
            r["reconstruction"]["class"] = "EXACTLY_RECONSTRUCTIBLE"
            break
    return d


def mutate_overclaim_directly_reported(d):
    """Claim a printed composition where none is recorded."""
    for r in d["benchmarks"]:
        if r.get("joint_scope") == "none":
            r["reconstruction"]["class"] = "DIRECTLY_REPORTED"
            break
    return d


def mutate_class_without_evidence(d):
    d["benchmarks"][0]["reconstruction"]["evidence"] = "   "
    return d


def mutate_drop_snapshot(d):
    d["census"].pop("snapshot", None)
    return d


def mutate_weaken_public_statement(d):
    d["census"]["snapshot"]["public_statement"] = "The census is up to date."
    return d


def mutate_bad_preservation_state(d):
    """'No archive recorded' must not be spelled as a fact about the world."""
    d["benchmarks"][0]["preservation"]["state"] = "NOT_ARCHIVED"
    return d


CASES = [
    ("a past row is silently edited", mutate_silent_history_edit, "v0_row_lock"),
    ("UNVERIFIED promoted to NOT_IDENTIFIABLE", mutate_unverified_to_absent, "positive finding"),
    ("EXACTLY_RECONSTRUCTIBLE without item release", mutate_overclaim_reconstructible, "per-item"),
    ("DIRECTLY_REPORTED without a printed composition", mutate_overclaim_directly_reported, "printed composition"),
    ("a class asserted with no evidence", mutate_class_without_evidence, "evidence"),
    ("the snapshot declaration is removed", mutate_drop_snapshot, "snapshot"),
    ("the currency caveat is weakened", mutate_weaken_public_statement, "not asserted to remain current"),
    ("preservation stated as a fact about the world", mutate_bad_preservation_state, "preservation.state"),
]


def main() -> int:
    clean = run_checks(copy.deepcopy(BASE))
    if clean:
        print("FAIL  the unmutated census does not pass its own invariants:")
        for f in clean:
            print(f"        {f}")
        return 1
    print("ok    unmutated census passes the invariants")

    bad = 0
    for name, mutate, expect in CASES:
        got = run_checks(mutate(copy.deepcopy(BASE)))
        if not got:
            bad += 1
            print(f"FAIL  {name}: the gate did NOT fail — it does not protect this property")
        elif not any(expect.lower() in f.lower() for f in got):
            bad += 1
            print(f"FAIL  {name}: failed, but for the wrong reason ({got[0][:90]})")
        else:
            print(f"ok    {name}: rejected")

    if bad:
        print(f"\n{bad} mutation(s) escaped the gates")
        return 1
    print(f"\nok    all {len(CASES)} mutations rejected; every gate demonstrably fails "
          "when its property is broken")
    return 0


if __name__ == "__main__":
    sys.exit(main())
