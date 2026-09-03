#!/usr/bin/env python3
"""Score the Trial IV pilot and apply the frozen decision rule.

    python3 scripts/trial_score.py [responses_dir] [--keys path]

Reads every *.json receipt under trials/necromancer/pilot/responses/, refuses
any receipt whose instrument_hash is not the frozen one, scores the pre-task
and the cold case against the withheld key file, and prints per-arm medians
and the decision. Exit codes:

    0   a decision was reached — CONTINUE, NARROW or KILL — under the frozen rule
    1   a receipt or the key file is malformed or off-freeze
    2   UNDETERMINED: n < 8, or an arm outside 4…5 — nothing is concluded

Exit 2 is not a pass and not a KILL. Concluding from n below eight is a
forbidden rescue; this script makes it impossible to do by accident.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "trials" / "necromancer" / "pilot"
RESPONSES = PILOT / "responses"
FREEZE = PILOT / "freeze.json"
KEY_LOCATIONS = (ROOT / "_private" / "necromancer" / "keys.json", PILOT / "keys.json")

N_MIN = 8
PER_ARM = (4, 5)
CONTINUE_AT = 2
NARROW_AT = 1


def score(sort: dict, key: dict) -> int:
    return sum(1 for mid, k in key.items() if sort.get(mid) == k["key"])


def decide(arms: dict) -> tuple[str, int, str]:
    """arms: {"A": [(pre, cold), ...], "B": [...]} → (decision, exit, reason)."""
    n = sum(len(v) for v in arms.values())
    if n < N_MIN or any(not (PER_ARM[0] <= len(arms.get(a, [])) <= PER_ARM[1]) for a in ("A", "B")):
        return "UNDETERMINED", 2, f"n = {n} (A {len(arms.get('A', []))}, B {len(arms.get('B', []))}); the rule needs {N_MIN} with {PER_ARM[0]}…{PER_ARM[1]} per arm"
    med = {a: statistics.median([c for _, c in arms[a]]) for a in ("A", "B")}
    pre = {a: statistics.median([p for p, _ in arms[a]]) for a in ("A", "B")}
    for a in ("A", "B"):
        if not med[a] > pre[a]:
            return "KILL", 0, f"arm {a} cold median {med[a]} does not beat its own pre-task median {pre[a]}"
    d = med["A"] - med["B"]
    if d >= CONTINUE_AT:
        return "CONTINUE", 0, f"median A {med['A']} − median B {med['B']} = {d} ≥ {CONTINUE_AT}"
    if d >= NARROW_AT:
        return "NARROW", 0, f"median A {med['A']} − median B {med['B']} = {d} in [{NARROW_AT}, {CONTINUE_AT}): narrow to the two-way sort (rescue vs not-rescue)"
    return "KILL", 0, f"median A {med['A']} − median B {med['B']} = {d} < {NARROW_AT}"


def selftest() -> str | None:
    cases = [
        ({"A": [(3, 7)] * 4, "B": [(3, 5)] * 4}, "CONTINUE"),
        ({"A": [(3, 6)] * 5, "B": [(3, 5)] * 4}, "NARROW"),
        ({"A": [(3, 5)] * 4, "B": [(3, 5)] * 4}, "KILL"),
        ({"A": [(3, 6), (3, 7)] * 2, "B": [(3, 5)] * 4}, "NARROW"),   # medians 6.5 − 5 = 1.5 → narrow
        ({"A": [(3, 5), (3, 6)] * 2, "B": [(3, 5)] * 4}, "KILL"),     # 5.5 − 5 = 0.5 → kill
        ({"A": [(6, 6)] * 4, "B": [(3, 4)] * 4}, "KILL"),      # arm A fails to beat its own pre-task
        ({"A": [(3, 8)] * 4, "B": [(3, 5)] * 3}, "UNDETERMINED"),
        ({"A": [(3, 8)] * 6, "B": [(3, 5)] * 4}, "UNDETERMINED"),
    ]
    for arms, want in cases:
        got = decide(arms)[0]
        if got != want:
            return f"{arms} → {got}, expected {want}"
    return None


def load_keys(explicit: str | None) -> dict:
    paths = [Path(explicit)] if explicit else list(KEY_LOCATIONS)
    for p in paths:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))["cases"]
    raise SystemExit("FAIL  no key file found (looked in " + ", ".join(str(p) for p in paths) + ")")


def main(argv: list[str]) -> int:
    if "--test" in argv:
        r = selftest()
        print("FAIL  " + r if r else "ok    trial_score self-test")
        return 1 if r else 0
    keys_path = argv[argv.index("--keys") + 1] if "--keys" in argv else None
    args = [a for a in argv[1:] if not a.startswith("--") and a != keys_path]
    rdir = Path(args[0]) if args else RESPONSES
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    keys = load_keys(keys_path)
    arms: dict = {"A": [], "B": []}
    rows = []
    ORDER = {"A": ["enrol", "pre", "claim", "seal", "evidence", "sort", "debrief", "update", "cold", "receipt"],
             "B": ["enrol", "pre", "claim", "evidence", "seal", "sort", "debrief", "update", "cold", "receipt"]}
    for p in sorted(rdir.glob("*.json")):
        if not re.fullmatch(r"slot-\d+\.json", p.name):
            print(f"note  {p.name}: not the first receipt for a slot (only slot-<N>.json is scored); kept, not scored")
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        if int(p.stem.split("-")[1]) != r.get("slot"):
            print(f"FAIL  {p.name}: file name and receipt slot disagree")
            return 1
        if [x.get("id") for x in r.get("phases", [])] != ORDER.get(r.get("arm")):
            print(f"FAIL  {p.name}: phase list is not arm {r.get('arm')}'s full order; refused by the frozen exclusions")
            return 1
        if r.get("instrument_hash") != freeze["instrument_hash"]:
            print(f"FAIL  {p.name}: instrument_hash is not the frozen one; excluded_pre by rule, not by outcome")
            return 1
        if freeze["arms"].get(str(r.get("slot"))) != r.get("arm"):
            print(f"FAIL  {p.name}: slot {r.get('slot')} is frozen as arm {freeze['arms'].get(str(r.get('slot')))}, receipt says {r.get('arm')}")
            return 1
        pre, cold = score(r["pre"], keys["pre"]), score(r["cold"], keys["cold"])
        arms[r["arm"]].append((pre, cold))
        rows.append((p.name, r["arm"], r["slot"], pre, cold, r.get("confidence"), r.get("helped"), r.get("total_seconds")))
    print("receipt                          arm slot  pre cold  conf help  seconds")
    for row in rows:
        print(f"{row[0]:32s} {row[1]}   {row[2]:>3}   {row[3]}    {row[4]}    {row[5]}    {row[6]}   {row[7]}")
    decision, code, reason = decide(arms)
    print(f"\n{decision}  {reason}")
    print("secondary outcomes (reactions, confidence, time, self-report, trained case) are reported above and decide nothing")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
