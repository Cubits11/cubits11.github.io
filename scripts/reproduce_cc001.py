#!/usr/bin/env python3
"""Continuously reproduce claims CC-001 and CC-004 from a clean clone.

Reads the bound commit and the structured `expected` blocks from claims.yaml
(single source of truth — the proposition's numbers and the executed
assertion cannot silently diverge), clones cc-framework at exactly that
revision, installs it into a disposable virtual environment created inside
the temporary clone directory (never into the invoking interpreter), executes
the kernel there, and asserts:

  CC-001 — frechet_bounds returns the registry's recorded AND/OR intervals.
  CC-004 — identify() returns the recorded interval together with endpoint
           witness distributions that sum to one, are nonnegative, satisfy
           both marginal constraints, and attain each endpoint.

If the numbers ever stop reproducing, the claims fail in CI.
"""

import json
import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

SNIPPET = r"""
import json, sys
spec = json.loads(sys.argv[1])
tol = float(spec["tolerance"])

from cc.kernel.strict import (
    AssumptionSet, LinearQuery, enumerate_atoms, frechet_bounds,
)

# --- CC-001: Frechet endpoint bounds match the registry ---
marginals = [float(p) for p in spec["marginals"]]
for event, (lo, hi) in spec["bounds"].items():
    b = frechet_bounds(marginals, event=event)
    print(f"event={event}: lower={b.lower} upper={b.upper}")
    assert abs(b.lower - lo) <= tol and abs(b.upper - hi) <= tol, (
        f"MISMATCH: expected [{lo}, {hi}] for {event}")

# --- CC-004: endpoint witnesses are feasible and attain the endpoints ---
labels = ("A_failure", "B_failure")
a = AssumptionSet.empty(labels)
for label, p in zip(labels, marginals):
    a = a.with_marginal_interval(label, p, p)
r = a.identify(LinearQuery.intersection(labels, labels, name="P(both fail)"))
w_lo, w_hi = spec["interval"]
assert abs(r.lower_bound - w_lo) <= tol and abs(r.upper_bound - w_hi) <= tol, (
    f"MISMATCH: identify() gave [{r.lower_bound}, {r.upper_bound}], "
    f"registry records [{w_lo}, {w_hi}]")
atoms = enumerate_atoms(labels)
for side, w, bound in (("lower", r.lower_solution, r.lower_bound),
                       ("upper", r.upper_solution, r.upper_bound)):
    total = float(w.sum())
    assert abs(total - 1.0) <= tol, f"{side} witness mass {total} != 1"
    assert float(w.min()) >= -tol, f"{side} witness has negative mass"
    for j, (label, p) in enumerate(zip(labels, marginals)):
        m = float(w[atoms[:, j] == 1].sum())
        assert abs(m - p) <= tol, f"{side} witness violates P({label})={p}: {m}"
    both = float(w[(atoms[:, 0] == 1) & (atoms[:, 1] == 1)].sum())
    assert abs(both - bound) <= tol, (
        f"{side} witness does not attain its endpoint: {both} vs {bound}")
    print(f"{side} witness: {[round(x, 12) for x in w.tolist()]} "
          f"attains P(both)={both:.6f}")
print("witnesses feasible and endpoint-attaining")
"""


def run(*cmd: str, cwd: str | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    by_id = {c["id"]: c for c in registry["claims"]}
    cc001, cc004 = by_id["CC-001"], by_id["CC-004"]

    commit = cc001["support"]["commit"]
    if cc004["support"]["commit"] != commit:
        print("FAIL: CC-001 and CC-004 must share one bound commit so a "
              "single clean-clone checkout reproduces both.")
        return 1
    print(f"CC-001 + CC-004 bound commit: {commit}")

    spec = {
        "marginals": cc001["expected"]["marginals"],
        "bounds": cc001["expected"]["bounds"],
        "interval": cc004["expected"]["interval"],
        "tolerance": min(float(cc001["expected"]["tolerance"]),
                         float(cc004["expected"]["tolerance"])),
    }

    with tempfile.TemporaryDirectory() as tmp:
        repo = str(pathlib.Path(tmp) / "cc")
        run("git", "clone", "--quiet", "--filter=blob:none",
            "https://github.com/Cubits11/cc-framework.git", repo)
        run("git", "checkout", "--quiet", commit, cwd=repo)
        # The kernel is installed into a disposable virtual environment inside
        # the temporary directory, never into the interpreter that invoked this
        # script. Installing into the invoking interpreter failed on any
        # externally managed Python (PEP 668 — Homebrew, Debian, Fedora), so
        # the README's local replay was red on exactly the machines an outsider
        # is likely to own. The venv is deleted with the temporary directory.
        venv = pathlib.Path(tmp) / "venv"
        run(sys.executable, "-m", "venv", str(venv))
        py = str(venv / ("Scripts" if sys.platform == "win32" else "bin") /
                 ("python.exe" if sys.platform == "win32" else "python"))
        run(py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
            "-e", repo)
        # A fresh interpreter, deliberately: editable-install path hooks only
        # take effect for processes started after the install.
        run(py, "-c", SNIPPET, json.dumps(spec))

    print("CC-001 + CC-004 REPRODUCED: clean clone at the bound commit "
          "returns the registry's recorded bounds and witness properties.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
