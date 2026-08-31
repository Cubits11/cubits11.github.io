#!/usr/bin/env python3
"""Print the qualified-outcome state and apply the stop rule.

Separates outcomes that required someone else to do work from metrics that
only say people saw something. Prints zero as zero.

Run: python scripts/outcomes.py
"""
from __future__ import annotations
import pathlib, sys, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "distribution" / "outcomes.yaml"

def main() -> int:
    if not LEDGER.exists():
        print(f"FAIL  {LEDGER.relative_to(ROOT)} is missing")
        return 1
    d = yaml.safe_load(LEDGER.read_text())
    q = d.get("qualified") or {}
    total = sum(len(v or []) for v in q.values())
    print("QUALIFIED OUTCOMES (someone who is not the author did work)")
    for k, v in q.items():
        print(f"  {k:28s} {len(v or []):3d}")
    print(f"  {'TOTAL':28s} {total:3d}")

    diag = d.get("diagnostics") or {}
    print("\nDIAGNOSTICS (not evidence)")
    for k, v in diag.items():
        print(f"  {k:28s} {'—' if v is None else v}")

    rule = d.get("stop_rule") or {}
    n = diag.get("technical_interactions") or 0
    thresh = rule.get("threshold_interactions", 12)
    print(f"\nSTOP RULE  ({n}/{thresh} technical interactions, {total} qualified)")
    if n >= thresh and total == 0:
        print("  TRIGGERED — stop replying; shift to upstream contributions and "
              "author outreach. Report the null result rather than continuing.")
    elif total > 0:
        print("  not triggered — qualified engagement exists.")
    else:
        print(f"  not triggered — {thresh - n} interactions remain before the "
              "null result is called.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
