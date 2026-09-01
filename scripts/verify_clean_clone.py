#!/usr/bin/env python3
"""Re-run the deterministic site gates from a fresh clone of one commit.

This is deliberately separate from ``reproduce_cc001.py``: that script
reproduces a bound CC-Framework kernel. A release also needs proof that the
Cubits11 source revision itself is cloneable, begins from a clean invoking
worktree, and regenerates its published artifacts without help from the
checkout that invoked it.
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from verification_manifest import CHECKS, validate_manifest

ROOT = Path(__file__).resolve().parent.parent
BASELINE = "eb5423a0b9f5808dea57acfcc865074208a83085"
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"


def check_workflow_entrypoint() -> None:
    """The workflow must call the same manifest this replay imports."""
    import yaml
    spec = yaml.safe_load(WORKFLOW.read_text())
    steps = (spec.get("jobs", {}).get("claims", {}) or {}).get("steps", [])
    commands = [str(step.get("run", "")).strip() for step in steps]
    expected = "python scripts/verification_manifest.py"
    if expected not in commands:
        raise ValueError("the workflow's claims job no longer runs the canonical "
                         "verification manifest")
    direct = [cmd for cmd in commands if cmd.startswith("python scripts/")
              and cmd != expected]
    if direct:
        raise ValueError("the workflow's claims job bypasses the canonical "
                         "manifest: " + "; ".join(direct))
    print(f"ok    canonical manifest: {len(CHECKS)} checks drive CI and the clean-clone replay")


README = ROOT / "README.md"
ENTRY_SECTION = "## Reproduce the claim"


def check_readme_entry_point() -> None:
    """The documented way in must be a way in that still works.

    Rigour and legibility fail independently, and this repository had them
    at opposite extremes: fifteen gates, a clean-clone replay, and a rank
    theorem, against a README whose first runnable lane described a different
    claim from the public front door. The census headline was reproducible,
    but a stranger was sent first to a later worked reconstruction instead.
    The distance between "has a result" and "has an external reproducer" was
    documentation, not evidence.

    A front door rots faster than a proof. This asserts that the first lane is
    MC-001's census verifier, its headline and ladder agree with the registry,
    every documented script exists, and MC-002's quoted figures still agree
    with the registry.
    """
    text = README.read_text()
    if ENTRY_SECTION not in text:
        raise SystemExit(f"README lost its {ENTRY_SECTION!r} section — the "
                         f"documented reproduction path is the only thing "
                         f"standing between a reader and a 0.9s result")
    section = text.split(ENTRY_SECTION, 1)[1].split("\n## ", 1)[0]

    named = re.findall(r"python3 (scripts/[\w./-]+\.py)", section)
    if not named:
        raise SystemExit("README entry section names no runnable script")
    for rel in sorted(set(named)):
        if not (ROOT / rel).exists():
            raise SystemExit(f"README entry section points at {rel}, which "
                             f"does not exist")

    import yaml
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    first_lane = re.search(r"^### First: MC-001.*?(?=^### |\Z)", section,
                           flags=re.MULTILINE | re.DOTALL)
    if first_lane is None:
        raise SystemExit("README first lane is not MC-001, the homepage "
                         "front-door claim")
    if not named or named[0] != "scripts/verify_census.py":
        raise SystemExit("README first command must run "
                         "scripts/verify_census.py")
    mc001 = next(c for c in registry["claims"] if c["id"] == "MC-001")
    e001 = mc001["expected"]
    census_literal = (f'{e001["n_examined"]}/{e001["m_shared_basis"]}/'
                      f'{e001["k_present"]}')
    if census_literal not in first_lane.group(0):
        raise SystemExit("README first lane no longer quotes the registered "
                         f"MC-001 headline ({census_literal})")
    strata = e001["m_strata"]
    ladder_literal = (f'{strata["shared_basis"]}/'
                      f'{strata["threshold_not_contradicted"]}/'
                      f'{strata["threshold_documented_full_exposure"]}')
    if ladder_literal not in first_lane.group(0):
        raise SystemExit("README first lane no longer quotes the registered "
                         f"MC-001 ladder ({ladder_literal})")
    mc = next(c for c in registry["claims"] if c["id"] == "MC-002")
    e = mc["expected"]
    n = e["n_harmful"]
    quoted = {
        f'{e["all_miss"]}/{n}': "registered all-miss fraction",
        f'{e["all_miss"] / n:.1%}': "registered all-miss rate",
        f'{e["benign_union_flagged"] / e["n_benign"]:.2%}': "benign union",
    }
    for literal, what in quoted.items():
        if literal not in section:
            raise SystemExit(f"README entry section no longer quotes the "
                             f"{what} ({literal}) the registry holds")
    print(f"ok    README entry point: MC-001 first; {len(set(named))} "
          f"scripts reachable; quoted numbers match the registry")


def run(args: list[str], cwd: Path, undetermined_on_2: bool = False) -> str:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if completed.returncode:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        # Opt-in, because exit 2 only carries this meaning for the manifest's
        # own checks — it means nothing of the kind coming back from git.
        if undetermined_on_2 and completed.returncode == 2:
            raise RuntimeError(
                "command could not be evaluated (exit 2 — its source was "
                "never reached; this is not a finding): " + " ".join(args))
        raise RuntimeError("command failed: " + " ".join(args))
    return completed.stdout


def resolve_commit(ref: str) -> str:
    return run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], ROOT).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone one committed Cubits11 revision and replay its deterministic gates.")
    parser.add_argument("--commit", default="HEAD",
                        help="commit or ref to clone and replay (default: HEAD)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_manifest()
        check_workflow_entrypoint()
    except ValueError as exc:
        print(f"FAIL  {exc}")
        return 1
    check_readme_entry_point()
    dirty = run(["git", "status", "--porcelain"], ROOT).strip()
    if dirty:
        print("FAIL  invoking worktree is dirty; commit or otherwise resolve "
              "the candidate before clean-clone replay")
        return 1
    commit = resolve_commit(args.commit)
    try:
        run(["git", "merge-base", "--is-ancestor", BASELINE, commit], ROOT)
    except RuntimeError:
        print(f"FAIL  {commit} does not descend from the declared corrective baseline "
              f"{BASELINE[:12]}")
        return 1

    with tempfile.TemporaryDirectory(prefix="cubits11-clean-clone-") as tmp:
        target = Path(tmp) / "repo"
        run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(target)], ROOT)
        run(["git", "checkout", "--quiet", "--detach", commit], target)
        if run(["git", "status", "--porcelain"], target).strip():
            print("FAIL  fresh clone is not clean after checkout")
            return 1
        checked = run(["git", "rev-parse", "HEAD"], target).strip()
        if checked != commit:
            print(f"FAIL  clean clone checked out {checked}, expected {commit}")
            return 1
        for label, *script in CHECKS:
            print(f"check {label}")
            run([sys.executable, *script], target, undetermined_on_2=True)

    print(f"Clean-clone replay passed for {commit} (descends from {BASELINE[:12]}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        raise SystemExit(1)
