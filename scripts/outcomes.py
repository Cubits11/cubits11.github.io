#!/usr/bin/env python3
"""Validate and print the qualified-outcome state and stop rule.

Separates outcomes that required someone else to do work from metrics that
only say people saw something. Prints zero as zero.

Run: python scripts/outcomes.py
"""

from __future__ import annotations

import pathlib
import sys

import yaml


ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "distribution" / "outcomes.yaml"
QUALIFIED_BUCKETS = (
    "independent_reproductions",
    "source_corrections",
    "paired_outcome_releases",
    "upstream_prs",
    "human_cold_runs",
)


def validate(data: object) -> dict:
    """Reject a malformed zero as eagerly as a malformed positive outcome."""
    if not isinstance(data, dict):
        raise ValueError("outcome ledger must be a mapping")
    qualified = data.get("qualified")
    if not isinstance(qualified, dict):
        raise ValueError("outcome ledger requires a qualified mapping")
    unknown = sorted(set(qualified) - set(QUALIFIED_BUCKETS))
    if unknown:
        raise ValueError("unknown qualified outcome bucket(s): " + ", ".join(unknown))
    for bucket in QUALIFIED_BUCKETS:
        if bucket not in qualified:
            raise ValueError(f"qualified outcome bucket is missing: {bucket}")
        if not isinstance(qualified[bucket], list):
            raise ValueError(f"qualified outcome bucket must be a list: {bucket}")

    diagnostics = data.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError("outcome ledger requires a diagnostics mapping")
    interactions = diagnostics.get("technical_interactions")
    if (isinstance(interactions, bool) or not isinstance(interactions, int)
            or interactions < 0):
        raise ValueError("technical_interactions must be a non-negative integer")

    rule = data.get("stop_rule")
    if not isinstance(rule, dict):
        raise ValueError("outcome ledger requires a stop_rule mapping")
    threshold = rule.get("threshold_interactions")
    if (isinstance(threshold, bool) or not isinstance(threshold, int)
            or threshold <= 0):
        raise ValueError("stop-rule threshold_interactions must be a positive integer")
    return data


def load(path: pathlib.Path = LEDGER) -> dict:
    if not path.exists():
        raise ValueError(f"{path.relative_to(ROOT)} is missing")
    return validate(yaml.safe_load(path.read_text()))


def qualified_total(data: dict) -> int:
    qualified = data["qualified"]
    return sum(len(qualified[bucket]) for bucket in QUALIFIED_BUCKETS)


def technical_interactions(data: dict) -> int:
    return data["diagnostics"]["technical_interactions"]


def main() -> int:
    try:
        data = load()
    except ValueError as exc:
        print(f"FAIL  {exc}")
        return 1
    qualified = data["qualified"]
    total = qualified_total(data)
    print("QUALIFIED OUTCOMES (someone who is not the author did work)")
    for bucket in QUALIFIED_BUCKETS:
        print(f"  {bucket:28s} {len(qualified[bucket]):3d}")
    print(f"  {'TOTAL':28s} {total:3d}")

    diagnostics = data["diagnostics"]
    print("\nDIAGNOSTICS (not evidence)")
    for key, value in diagnostics.items():
        print(f"  {key:28s} {'—' if value is None else value}")

    rule = data["stop_rule"]
    interactions = technical_interactions(data)
    threshold = rule["threshold_interactions"]
    print(f"\nSTOP RULE  ({interactions}/{threshold} technical interactions, {total} qualified)")
    if interactions >= threshold and total == 0:
        print("  TRIGGERED — stop replying; shift to upstream contributions and "
              "author outreach. Report the null result rather than continuing.")
    elif total > 0:
        print("  not triggered — qualified engagement exists.")
    else:
        print(f"  not triggered — {threshold - interactions} interactions remain before the "
              "null result is called.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
