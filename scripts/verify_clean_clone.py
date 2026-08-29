#!/usr/bin/env python3
"""Re-run the deterministic site gates from a fresh clone of one commit.

This is deliberately separate from ``reproduce_cc001.py``: that script
reproduces a bound CC-Framework kernel. A release also needs proof that the
Cubits11 source revision itself is cloneable, begins from a clean invoking
worktree, and regenerates its published artifacts without help from the
checkout that invoked it.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = "eb5423a0b9f5808dea57acfcc865074208a83085"
CHECKS = (
    ("claim registry", "scripts/verify_claims.py"),
    ("census", "scripts/verify_census.py"),
    ("ledger drift", "scripts/generate_ledger.py", "--check"),
    ("figure assertions", "scripts/verify_figures.py"),
    ("module drift", "scripts/generate_modules.py", "--check"),
    ("observatory drift", "scripts/generate_observatory.py", "--check"),
    ("missing-column drift", "scripts/generate_missing_column.py", "--check"),
    ("sitemap drift", "scripts/generate_sitemap.py", "--check"),
    ("MJGD identities", "scripts/mjgd_reference.py", "--test"),
    ("MJGD v1 fixtures", "scripts/validate_mjgd.py", "--test"),
    ("identification bounds", "scripts/identification.py"),
    ("pattern-count rank", "scripts/mjgd_pattern_rank.py"),
    ("mixture bounds", "scripts/mixture_bounds.py"),
    ("BELLS reproduction", "scripts/reanalyze_bells_subset.py"),
    ("internal links", "scripts/check_links.py"),
    ("frontend structural gates", "scripts/verify_frontend.py"),
)


WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"
MANIFEST_JOB = "claims"


def check_manifest_parity() -> None:
    """One manifest, two consumers — or the two consumers verify different
    things and both report success.

    This repository verifies itself through two surfaces: the workflow job
    that runs on every push, and this clean-clone replay. Each printed a
    green result while covering a different set of scripts, and neither
    printed what the other covered. `identification.py` and
    `mixture_bounds.py` ran in CI and not in the replay, so a reader
    reproducing from a clean clone got a passing run that never executed the
    identification arithmetic the central claim rests on.

    That is the census's own finding, committed by the census: two marginals,
    each reported, and a joint nobody published. The repair is structural
    rather than a one-time reconciliation — the workflow's list and CHECKS
    must be the same set, asserted here, so the divergence cannot come back
    quietly.
    """
    import yaml
    spec = yaml.safe_load(WORKFLOW.read_text())
    steps = (spec.get("jobs", {}).get(MANIFEST_JOB, {}) or {}).get("steps", [])
    in_ci = set()
    for step in steps:
        cmd = str(step.get("run", "")).strip()
        parts = cmd.split()
        if len(parts) >= 2 and parts[0] == "python" \
                and parts[1].startswith("scripts/"):
            in_ci.add(" ".join(parts[1:]))
    in_manifest = {" ".join(entry[1:]) for entry in CHECKS}
    only_ci = sorted(in_ci - in_manifest)
    only_manifest = sorted(in_manifest - in_ci)
    if only_ci or only_manifest:
        lines = ["CHECKS and the workflow's '%s' job have diverged — one "
                 "surface would verify what the other does not, and both "
                 "would report success:" % MANIFEST_JOB]
        for entry in only_ci:
            lines.append(f"  in CI, absent from the clean-clone replay: {entry}")
        for entry in only_manifest:
            lines.append(f"  in the replay, absent from CI: {entry}")
        raise SystemExit("\n".join(lines))
    print(f"ok    manifest parity: {len(in_manifest)} checks drive both CI "
          f"and the clean-clone replay")


def run(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if completed.returncode:
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
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
    check_manifest_parity()
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
            run([sys.executable, *script], target)

    print(f"Clean-clone replay passed for {commit} (descends from {BASELINE[:12]}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        raise SystemExit(1)
