#!/usr/bin/env python3
"""Continuously reproduce claim CC-001 from a clean clone.

Reads the bound commit from claims.yaml (single source of truth), clones
cc-framework at exactly that revision, installs it into the current
environment, executes the kernel, and asserts the registry's recorded
values. If the numbers ever stop reproducing, the claim fails in CI.
"""

import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPECTED = {"and": (0.0, 0.1), "or": (0.1, 0.2)}


def run(*cmd: str, cwd: str | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    cc001 = next(c for c in registry["claims"] if c["id"] == "CC-001")
    commit = cc001["support"]["commit"]
    print(f"CC-001 bound commit: {commit}")

    snippet = (
        "from cc.kernel.strict import frechet_bounds\n"
        f"expected = {EXPECTED!r}\n"
        "for event, (lo, hi) in expected.items():\n"
        "    b = frechet_bounds([0.10, 0.10], event=event)\n"
        "    print(f'event={event}: lower={b.lower} upper={b.upper}')\n"
        "    assert (b.lower, b.upper) == (lo, hi), f'MISMATCH: expected ({lo}, {hi})'\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        repo = str(pathlib.Path(tmp) / "cc")
        run("git", "clone", "--quiet", "--filter=blob:none",
            "https://github.com/Cubits11/cc-framework.git", repo)
        run("git", "checkout", "--quiet", commit, cwd=repo)
        run(sys.executable, "-m", "pip", "install", "--quiet", "-e", repo)
        # A fresh interpreter, deliberately: editable-install path hooks only
        # take effect for processes started after the install.
        run(sys.executable, "-c", snippet)

    print("CC-001 REPRODUCED: clean clone at the bound commit returns the "
          "registry's recorded bounds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
