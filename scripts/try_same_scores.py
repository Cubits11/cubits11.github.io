#!/usr/bin/env python3
"""TRY-A — Same Scores, Different Worlds: a 60-second proof, standard library only.

Two guards each miss some fraction of items. Those two published rates do not
determine how often both miss the same item: every value between
max(0, p+q-1) and min(p, q) is attained by some joint distribution with exactly
those marginals. This script constructs the two endpoint worlds and nine
worlds in between, checks each one's marginals to 1e-12, and compares the
interval with what the claim registry records for the declared input
(CC-001, CC-004), read from films/data/facts.json — the file that
scripts/films/bind_facts.py derives from claims.yaml and keeps current in CI.

    python3 scripts/try_same_scores.py                       # the registered input
    python3 scripts/try_same_scores.py --marginals 0.05 0.02  # any two rates

Exit 0 and a final line beginning MATCH (registered input) or CONSTRUCTED
(your own input). Exit 1 with a FAIL line if any world violates its marginals
or the registry disagrees. No packages, no network, nothing written to disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "films" / "data" / "facts.json"
TOL = 1e-12


def world(p: float, q: float, both: float) -> list[float]:
    """Atoms in the order (neither, A only, B only, both)."""
    return [1 - p - q + both, p - both, q - both, both]


def check_world(atoms: list[float], p: float, q: float) -> str | None:
    if any(a < -TOL for a in atoms):
        return "negative mass"
    if abs(sum(atoms) - 1) > TOL:
        return f"mass {sum(atoms)} != 1"
    if abs(atoms[1] + atoms[3] - p) > TOL:
        return f"P(A) {atoms[1] + atoms[3]} != {p}"
    if abs(atoms[2] + atoms[3] - q) > TOL:
        return f"P(B) {atoms[2] + atoms[3]} != {q}"
    return None


def fmt(atoms: list[float]) -> str:
    return "(" + ", ".join(f"{max(a, 0.0):.2f}" for a in atoms) + ")"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marginals", nargs=2, type=float, metavar=("P_A", "P_B"),
                    help="two miss rates in [0, 1]; without this flag the registered input is used")
    args = ap.parse_args()

    registered = None
    if FACTS.exists():
        registered = json.loads(FACTS.read_text())["facts"]
    if args.marginals is None:
        if registered is None:
            print(f"FAIL  {FACTS.relative_to(ROOT)} is missing — run from a clone of the repository, "
                  "or pass --marginals to construct worlds for your own rates")
            return 1
        p, q = registered["CC-001.marginals"]["value"]
        mode = "registered input (claims.yaml CC-001)"
    else:
        p, q = args.marginals
        if not (0 <= p <= 1 and 0 <= q <= 1):
            print("FAIL  marginals must lie in [0, 1]")
            return 1
        mode = "your input — CONSTRUCTED, not the registry's declared case"

    lo, hi = max(0.0, p + q - 1), min(p, q)
    print("Same Scores, Different Worlds — TRY-A (standard library, offline)")
    print(f"  marginals   guard A misses {p:.2%}   guard B misses {q:.2%}   [{mode}]")
    print("  atoms are (neither, A only, B only, both); every world below keeps both marginals fixed")
    steps = 10
    for i in range(steps + 1):
        both = lo + (hi - lo) * i / steps
        atoms = world(p, q, both)
        err = check_world(atoms, p, q)
        if err:
            print(f"FAIL  world both={both:.4f}: {err}")
            return 1
        tag = "  ← lower endpoint witness" if i == 0 else ("  ← upper endpoint witness" if i == steps else "")
        print(f"  world {i:2d}  π={fmt(atoms)}  P(A)={atoms[1] + atoms[3]:.2f}  P(B)={atoms[2] + atoms[3]:.2f}  both={both:.2f}{tag}")
    print(f"  interval    both-miss ∈ [{lo:.2f}, {hi:.2f}] — every value attained, marginals held to {TOL:g}")
    print(f"  assumption  independence would choose {p * q:.2%} — one point inside, chosen by one assumption")

    if args.marginals is None:
        exp_lo, exp_hi = registered["CC-001.and_bounds"]["value"]
        w_lo = registered["CC-004.witness_lower"]["value"]
        w_hi = registered["CC-004.witness_upper"]["value"]
        ind = registered["CC-001.independence_and"]["value"]
        ok = (abs(exp_lo - lo) < 1e-9 and abs(exp_hi - hi) < 1e-9
              and all(abs(a - b) < 1e-9 for a, b in zip(world(p, q, lo), w_lo))
              and all(abs(a - b) < 1e-9 for a, b in zip(world(p, q, hi), w_hi))
              and abs(ind - p * q) < 1e-9)
        print(f"  registry    CC-001 and_bounds [{exp_lo:.2f}, {exp_hi:.2f}] · CC-004 witnesses {fmt(w_lo)} and {fmt(w_hi)}"
              f" → {'agree' if ok else 'DISAGREE'}")
        if not ok:
            print("FAIL  TRY-A  this script and the registry disagree — file it: the disagreement is the result")
            return 1
        print(f"MATCH  TRY-A  marginals {p:.2f}/{q:.2f}  both-miss interval [{lo:.2f}, {hi:.2f}]  endpoints attained  independence {p * q:.2f} is one point")
        return 0
    print(f"CONSTRUCTED  TRY-A  marginals {p:.2f}/{q:.2f}  both-miss interval [{lo:.2f}, {hi:.2f}]  endpoints attained  independence {p * q:.4f} is one point")
    return 0


if __name__ == "__main__":
    sys.exit(main())
