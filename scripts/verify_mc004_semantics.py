#!/usr/bin/env python3
"""Keep MC-004's adapter-bit arithmetic separate from a catch event.

The data and arithmetic have always been checkable. The failure this guards is
semantic promotion: a harness-normalized `blocked` bit must not quietly become
a source-defined common safety event just because its rows are aligned.
"""
import pathlib
import sys

import yaml

import generate_missing_column as generator
import verify_census

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES = []


def check(name, condition):
    if condition:
        print(f"ok    {name}")
    else:
        FAILURES.append(name)
        print(f"FAIL  {name}")


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    mc = next(c for c in registry["claims"] if c["id"] == "MC-004")
    data = verify_census.load()
    row = next(r for r in data["benchmarks"]
               if r["id"] == "multimodal-safeguard-bench-2026")

    check("MC-004 names native unsafe labels", "native `unsafe`" in mc["proposition"])
    check("MC-004 names the missing translation", "shared catch event" in mc["scope"])
    check("MC-004 proposition does not call bits catches", "catches" not in mc["proposition"].lower())
    check("MC-004 carries the semantic non-claim",
          any("not a shared-event catch statistic" in x for x in mc["non_claims"]))
    check("ground-truth event remains distinct from native action",
          row["same_event_definition"]["value"] == "yes"
          and "ground-truth" in row["same_event_definition"]["evidence"])
    translation = row.get("native_action_translation") or {}
    check("native action translation is explicitly not established",
          translation.get("status") == "not_established"
          and "no examined source" in str(translation.get("evidence", "")).lower())

    repro = generator.render_reproduce(data)
    check("reproduction page names its released-bit aggregate",
          "released-bit aggregate" in repro and "No shared-event catch statistic" in repro)
    readme = (ROOT / "README.md").read_text()
    check("README carries the shared-event boundary", "shared-event catch\nclaim" in readme)
    receipt = (ROOT / "distribution" / "RECEIPT_PROTOCOL.md").read_text()
    check("unsafe social draft is rejected", "Rejected post — MC-004" in receipt
          and "not a publishable\nsafety-performance caption" in receipt)

    if FAILURES:
        print(f"{len(FAILURES)} semantic check(s) failed.")
        return 1
    print("MC-004 semantic scope verified: aligned bits are not a shared event.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
