#!/usr/bin/env python3
"""Run the deterministic release gates from one canonical manifest.

The deployed workflow and the clean-clone replay are two witnesses for the
same candidate revision. They must execute the same commands in the same
order, rather than carrying two hand-maintained lists that can quietly drift.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# The single deterministic verification surface. The workflow runs this
# module directly; verify_clean_clone imports this tuple for its fresh clone.
CHECKS: tuple[tuple[str, ...], ...] = (
    # Offline first: the liveness classifier decides whether a red registry
    # run is evidence about the bound evidence or about this runner's network.
    # That branch never executes on an unrestricted box, so it is asserted
    # against synthetic responses rather than trusted because CI went green.
    ("claim registry liveness classification", "scripts/verify_claims.py", "--test"),
    ("claim registry", "scripts/verify_claims.py"),
    ("census", "scripts/verify_census.py"),
    ("census protocol v1", "scripts/verify_census_protocol.py"),
    ("census invariant mutations", "scripts/verify_census_mutations.py"),
    ("ledger drift", "scripts/generate_ledger.py", "--check"),
    ("figure assertions", "scripts/verify_figures.py"),
    ("module drift", "scripts/generate_modules.py", "--check"),
    ("observatory drift", "scripts/generate_observatory.py", "--check"),
    ("missing-column drift", "scripts/generate_missing_column.py", "--check"),
    ("fact-binding fixtures", "scripts/verify_facts.py", "--test"),
    ("current fact surfaces", "scripts/verify_facts.py"),
    ("growth page drift", "scripts/generate_growth.py", "--check"),
    ("acquisition surfaces", "scripts/verify_growth.py"),
    ("sitemap drift", "scripts/generate_sitemap.py", "--check"),
    ("MJGD identities", "scripts/mjgd_reference.py", "--test"),
    ("MJGD v1 fixtures", "scripts/validate_mjgd.py", "--test"),
    ("identification bounds", "scripts/identification.py"),
    ("pattern-count rank", "scripts/mjgd_pattern_rank.py"),
    ("mixture bounds", "scripts/mixture_bounds.py"),
    ("BELLS reproduction", "scripts/reanalyze_bells_subset.py"),
    ("MSBench reproduction", "scripts/reanalyze_msbench.py"),
    ("MC-004 semantic scope", "scripts/verify_mc004_semantics.py"),
    ("degeneracy diagnostic", "scripts/degeneracy.py"),
    ("portable static-OR receipt", "examples/stack-joint/test_joint_or.py"),
    ("portable route receipt", "examples/route-receipt/test_route_receipt.py"),
    ("qualified outcome ledger", "scripts/outcomes.py"),
    ("internal links", "scripts/check_links.py"),
    ("frontend structure and scroll regions", "scripts/verify_frontend.py"),
    ("remote-evidence failure states", "scripts/verify_wayback_states.py"),
    ("resume PDF receipt", "scripts/verify_resume_receipt.py"),
)


def validate_manifest(checks: tuple[tuple[str, ...], ...] = CHECKS) -> None:
    """Reject duplicate command entries before a green run can hide one."""
    seen: dict[tuple[str, ...], str] = {}
    duplicates: list[tuple[str, str, tuple[str, ...]]] = []
    for label, *command in checks:
        key = tuple(command)
        if key in seen:
            duplicates.append((seen[key], label, key))
        else:
            seen[key] = label
    if duplicates:
        details = "; ".join(
            f"{first!r} and {second!r}: {' '.join(command)}"
            for first, second, command in duplicates
        )
        raise ValueError("verification manifest contains duplicate commands: " + details)


def run_manifest(cwd: Path = ROOT) -> int:
    try:
        validate_manifest()
    except ValueError as exc:
        print(f"FAIL  {exc}")
        return 1
    for label, *command in CHECKS:
        print(f"check {label}", flush=True)
        completed = subprocess.run([sys.executable, *command], cwd=cwd)
        if completed.returncode:
            print(f"FAIL  {label}: {' '.join(command)}")
            return completed.returncode
    print(f"ok    deterministic verification manifest: {len(CHECKS)} unique checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_manifest())
