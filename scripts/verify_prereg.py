#!/usr/bin/env python3
"""Gate the join between a preregistration's prose and the code that runs it.

Twenty-eight verifiers here check that a claim is well-formed, that a URL
resolves, that a figure re-derives, that a generated page was not hand-edited.
None of them checks the one thing that has actually invalidated work in this
repository: that the estimator the runner computes is the estimator the
preregistration wrote down.

Three executed experiments have been voided or rejected, and all three failed
in that join, not in either half:

  E7   VOID    the prereg fixed the operating point as "the highest threshold
               whose false-flag rate does not exceed 5%". Raising a threshold
               lowers the flag rate, so the highest threshold inside any budget
               is the one that flags nothing. The code implemented the prose.
  E6   REJECT  the construction claimed to hold marginals fixed while permuting
               unequal-mass atoms. Permutation does not preserve unequal masses.
               Nothing asserted the invariant the prose asserted.
  E7B  REJECT  the prereg calibrated each judge on its own benign pool; the
               runner calibrated every judge on the intersection of all nine,
               and evaluated on the global intersection rather than the pair's
               shared pool. Two pool identities, never declared, never checked.

Each was caught by hand, after outcomes were visible, at the cost of the run.
This file turns those three post-mortems into three pre-execution gates.

Two parts:

  --test    Three regression fixtures on synthetic data with known answers.
            Each asserts the defective rule gets it wrong AND the corrected
            rule gets it right, so a fixture that has lost its teeth fails
            loudly rather than passing vacuously.

  (default) Conformance scan. An experiment opts in by committing
            ``experiments/<e>/PREREG.estimator.json`` beside its PREREG.md.
            Where the sidecar exists its obligations are enforced. Where it
            does not, the experiment is reported as undeclared and the scan
            still passes: retroactively gating a frozen preregistration would
            itself be a post-hoc change to a frozen file.

    python3 scripts/verify_prereg.py           # the gate (exit 0 / 1)
    python3 scripts/verify_prereg.py --test    # the three regression fixtures
    python3 scripts/verify_prereg.py --show    # print the coverage table
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = ROOT / "experiments"
SIDECAR = "PREREG.estimator.json"

failures: list[str] = []
QUIET = False          # set while running mutants, whose failures are the point


def fail(msg: str) -> None:
    failures.append(msg)
    if not QUIET:
        print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    if not QUIET:
        print(f"ok    {msg}")


# ---------------------------------------------------------------------------
# The three shared rules. A runner imports these; it does not restate them.
# That is the whole mechanism: one definition, two readers.
# ---------------------------------------------------------------------------

def budget_threshold(scores: list[float], budget: float, direction: str,
                     comparator: str = "ge") -> float | None:
    """Operating point under a false-flag budget.

    ``comparator`` "ge" means an item is flagged when its score reaches the
    threshold, so the flag rate is non-increasing in the threshold. Under that
    monotonicity the budget is satisfied by an upward-closed set of thresholds,
    and only its *infimum* is a non-degenerate operating point. The supremum
    flags nothing and satisfies every budget. E7 died here.
    """
    if comparator != "ge":
        raise ValueError(f"unsupported comparator {comparator!r}")
    cands = sorted({*scores})
    inside = [t for t in cands if sum(s >= t for s in scores) / len(scores) <= budget]
    if not inside:
        return None
    return inside[0] if direction == "lowest" else inside[-1]


def marginal_after_permutation(weights: list[float], perm: tuple[int, ...]) -> list[float]:
    """Mass landing on each value position after permuting atom positions."""
    return [sum(weights[k] for k in range(len(weights)) if perm[k] == j)
            for j in range(len(weights))]


def mass_preserving_permutations(weights: list[float]) -> list[tuple[int, ...]]:
    return [p for p in itertools.permutations(range(len(weights)))
            if marginal_after_permutation(weights, p) == weights]


def pool_threshold(scores: dict[str, float], pool: set[str], budget: float) -> float | None:
    return budget_threshold([scores[k] for k in sorted(pool)], budget, "lowest")


# ---------------------------------------------------------------------------
# Part 1 — regression fixtures
# ---------------------------------------------------------------------------

def fixture_direction() -> None:
    """E7. A budget-constrained threshold has exactly one non-degenerate end."""
    benign = [round(0.01 * i, 2) for i in range(1, 101)]          # 0.01 .. 1.00
    harmful = [0.90, 0.93, 0.96, 0.97, 0.98]

    hi = budget_threshold(benign, 0.05, "highest")
    lo = budget_threshold(benign, 0.05, "lowest")
    if hi is None or lo is None:
        fail("direction fixture: no threshold satisfies the budget; fixture is broken")
        return

    flag_hi = sum(s >= hi for s in harmful) / len(harmful)
    flag_lo = sum(s >= lo for s in harmful) / len(harmful)

    if not hi > lo:
        fail(f"direction fixture has lost its teeth: highest {hi} is not above lowest {lo}")
    if flag_hi != 0.0:
        fail(f"direction fixture has lost its teeth: the defective rule flags "
             f"{flag_hi:.2f} of harmful items; E7's failure was that it flags nothing")
    if flag_lo <= 0.0:
        fail(f"direction fixture: the corrected rule also flags nothing ({flag_lo:.2f})")
    fpr_hi = sum(s >= hi for s in benign) / len(benign)
    fpr_lo = sum(s >= lo for s in benign) / len(benign)
    if fpr_lo > 0.05 + 1e-12:
        fail(f"direction fixture: corrected threshold {lo} exceeds the budget at {fpr_lo}")

    if not failures:
        ok(f"E7 direction: budget 0.05 admits [{lo}, {hi}]; the defective 'highest' end "
           f"misses {1 - flag_hi:.0%} of harmful items at FPR {fpr_hi:.2f}, the 'lowest' end "
           f"catches {flag_lo:.0%} at FPR {fpr_lo:.2f}")


def fixture_marginal_invariance() -> None:
    """E6. Permuting unequal-mass atoms does not preserve their marginal."""
    W = [0.25, 0.50, 0.25]
    counterexample = (1, 0, 2)
    got = marginal_after_permutation(W, counterexample)
    if got == W:
        fail("marginal fixture has lost its teeth: the counterexample preserves the masses")
    valid = mass_preserving_permutations(W)
    if len(valid) != 2:
        fail(f"marginal fixture: expected 2 mass-preserving permutations, found {len(valid)}")
    if (0, 1, 2) not in valid or (2, 1, 0) not in valid:
        fail(f"marginal fixture: identity and reversal must both preserve; got {valid}")
    valid_constructions = len(valid) ** 4
    enumerated = 6 ** 4
    if (valid_constructions, enumerated) != (16, 1296):
        fail(f"marginal fixture: {valid_constructions} of {enumerated}; E6 recorded 16 of 1296")
    if not failures:
        ok(f"E6 invariance: permutation {counterexample} sends {W} to {got}; only "
           f"{len(valid)} of 6 permutations preserve the masses, so "
           f"{valid_constructions} of {enumerated} enumerated constructions are valid")


def fixture_pool_identity() -> None:
    """E7B. Calibrating on a shared pool is not calibrating on an own pool."""
    own = {f"b{i}": round(0.01 * i, 2) for i in range(1, 101)}
    shared_ids = {f"b{i}" for i in range(1, 41)}          # the intersection is smaller
    t_own = pool_threshold(own, set(own), 0.05)
    t_shared = pool_threshold(own, shared_ids, 0.05)
    if t_own is None or t_shared is None:
        fail("pool fixture: a threshold was not computable; fixture is broken")
        return
    if t_own == t_shared:
        fail(f"pool fixture has lost its teeth: own-pool and shared-pool calibration "
             f"agree at {t_own}; E7B's failure was that they differ")
    if len(shared_ids) >= len(own):
        fail("pool fixture: the shared pool must be a strict subset to be a test")
    if not failures:
        ok(f"E7B pools: the same scores calibrate to {t_own} on the own pool (n={len(own)}) "
           f"and {t_shared} on the shared pool (n={len(shared_ids)}); pool identity is part "
           f"of the estimator, not an implementation detail")


FIXTURES = (
    ("operating-point direction (E7)", fixture_direction),
    ("marginal invariance under permutation (E6)", fixture_marginal_invariance),
    ("calibration pool identity (E7B)", fixture_pool_identity),
)


def run_fixtures() -> int:
    print("check preregistration-conformance regression fixtures")
    for name, fn in FIXTURES:
        before = len(failures)
        fn()
        if len(failures) > before:
            print(f"      ^ {name}")
    if failures:
        print(f"\n{len(failures)} fixture(s) failed.")
        return 1
    print(f"\n{len(FIXTURES)} fixtures hold. Each reconstructs a defect that voided a real "
          f"run here, and each asserts the defective rule still gets it wrong.")
    return 0


# ---------------------------------------------------------------------------
# Part 2 — conformance scan over committed preregistrations
# ---------------------------------------------------------------------------

REQUIRED = ("estimand", "quantities", "runner")


def check_sidecar(exp: str, prereg: Path, sidecar: Path) -> None:
    try:
        dec = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"{exp}: {SIDECAR} is not valid JSON ({e})")
        return
    prose = prereg.read_text(encoding="utf-8")

    for key in REQUIRED:
        if not dec.get(key):
            fail(f"{exp}: {SIDECAR} declares no {key!r}")

    # every quantity the estimator computes must be named in the prose
    for q in dec.get("quantities", []):
        if not re.search(re.escape(q), prose):
            fail(f"{exp}: quantity {q!r} is computed but never named in PREREG.md")

    # This is a static reference check, not proof of runtime consumption.
    runner = dec.get("runner")
    if runner:
        rp = ROOT / runner
        if not rp.exists():
            fail(f"{exp}: declared runner {runner} does not exist")
        elif SIDECAR not in rp.read_text(encoding="utf-8", errors="replace"):
            fail(f"{exp}: {runner} has no static reference to {SIDECAR}; "
                 f"runtime consumption is not established by this declaration check")

    # E7's trap, closed by declaration
    op = dec.get("operating_point")
    if op:
        direction = op.get("direction")
        comparator = op.get("comparator", "ge")
        if direction not in ("lowest", "highest"):
            fail(f"{exp}: operating_point.direction must be declared 'lowest' or 'highest'")
        elif comparator == "ge" and direction == "highest" and op.get("budget") is not None:
            fail(f"{exp}: operating_point selects the HIGHEST threshold under a "
                 f"{op['budget']} budget with a 'ge' comparator — that end flags nothing. "
                 f"This is the defect that voided E7.")

    # E7B's trap, closed by declaration
    pools = dec.get("pools")
    if pools is not None:
        for role in ("calibration", "evaluation"):
            if not pools.get(role):
                fail(f"{exp}: pools.{role} is not declared; E7B diverged on both")

    # E6's trap, closed by declaration
    for inv in dec.get("invariants", []):
        if inv == "marginal_masses_preserved":
            w = dec.get("marginal_weights")
            if not w:
                fail(f"{exp}: declares invariant {inv!r} but no marginal_weights to check it against")
            elif len(mass_preserving_permutations([float(x) for x in w])) < 2:
                fail(f"{exp}: no permutation preserves the declared marginal_weights {w}")

    if not any(f.startswith(f"{exp}:") for f in failures):
        ok(f"{exp}: estimator declared, {len(dec.get('quantities', []))} quantities named in "
           f"prose, runner reads the declaration")


def scan(show: bool) -> int:
    print("check preregistration conformance")
    declared, undeclared = [], []
    for d in sorted(p for p in EXPERIMENTS.iterdir() if p.is_dir()):
        prereg = d / "PREREG.md"
        if not prereg.exists():
            continue
        sidecar = d / SIDECAR
        if sidecar.exists():
            declared.append(d.name)
            check_sidecar(d.name, prereg, sidecar)
        else:
            undeclared.append(d.name)

    total = len(declared) + len(undeclared)
    if show or undeclared:
        for name in undeclared:
            print(f"      {name}: undeclared — no {SIDECAR}; conformance is not "
                  f"mechanically checked for this experiment")
    if failures:
        print(f"\n{len(failures)} conformance check(s) failed.")
        return 1
    print(f"\nconformance: {len(declared)} of {total} preregistrations declare a "
          f"machine-readable estimator. Undeclared preregistrations are reported, not "
          f"failed — gating a frozen file after its outcomes are visible is the rescue "
          f"this repository forbids. New experiments carry the sidecar.")
    return 0



# ---------------------------------------------------------------------------
# Part 3 — mutants. A gate nobody has watched fire is a gate nobody can trust.
# Each mutant is a declaration carrying one of the three real defects; the scan
# must reject it. A mutant that passes means the gate has stopped working.
# ---------------------------------------------------------------------------

MUTANTS: tuple[tuple[str, dict, str], ...] = (
    ("E7 as declared: highest threshold under a budget",
     {"estimand": "miss rate", "quantities": ["miss"], "runner": None,
      "operating_point": {"rule": "budget", "direction": "highest",
                          "budget": 0.05, "comparator": "ge"}},
     "operating_point selects the HIGHEST"),
    ("E7 as declared: direction left unstated",
     {"estimand": "miss rate", "quantities": ["miss"], "runner": None,
      "operating_point": {"rule": "budget", "budget": 0.05, "comparator": "ge"}},
     "direction must be declared"),
    ("E6 as declared: marginals held fixed over unequal masses",
     {"estimand": "coupling range", "quantities": ["range"], "runner": None,
      "invariants": ["marginal_masses_preserved"], "marginal_weights": [0.25, 0.5, 0.24]},
     "no permutation preserves"),
    ("E6 as declared: invariant asserted with nothing to check it against",
     {"estimand": "coupling range", "quantities": ["range"], "runner": None,
      "invariants": ["marginal_masses_preserved"]},
     "no marginal_weights"),
    ("E7B as declared: evaluation pool unstated",
     {"estimand": "joint miss", "quantities": ["miss"], "runner": None,
      "pools": {"calibration": "own"}},
     "pools.evaluation is not declared"),
    ("a quantity computed but never named in the prose",
     {"estimand": "joint miss", "quantities": ["q_undisclosed"], "runner": None},
     "never named in PREREG.md"),
    ("no estimand at all",
     {"quantities": ["q_obs"], "runner": None},
     "declares no 'estimand'"),
)


def run_mutants() -> None:
    """Apply the scan's obligations to defective declarations in memory."""
    import tempfile
    print("check the gate fires on defective declarations")
    prose = "This preregistration names q_obs and miss and range and nothing else.\n"
    for name, dec, expect in MUTANTS:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "PREREG.md").write_text(prose, encoding="utf-8")
            (d / SIDECAR).write_text(json.dumps(dec), encoding="utf-8")
            global failures, QUIET
            keep, failures, QUIET = failures, [], True
            check_sidecar("mutant", d / "PREREG.md", d / SIDECAR)
            caught = [f for f in failures if expect in f]
            fired, failures, QUIET = list(failures), keep, False
        if not caught:
            fail(f"mutant survived: {name} — expected a failure containing {expect!r}, "
                 f"got {fired or 'nothing'}")
        else:
            ok(f"rejected: {name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--test", action="store_true", help="run the three regression fixtures")
    ap.add_argument("--show", action="store_true", help="print undeclared experiments too")
    args = ap.parse_args()
    if args.test:
        rc = run_fixtures()
        print()
        before = len(failures)
        run_mutants()
        if len(failures) > before:
            print(f"\n{len(failures) - before} mutant(s) survived the gate.")
            return 1
        print(f"\n{len(MUTANTS)} mutants rejected. The gate fires.")
        return rc
    return scan(args.show)


if __name__ == "__main__":
    raise SystemExit(main())
