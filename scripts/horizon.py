#!/usr/bin/env python3
"""The ten-year horizon, and the next problem selected from it.

`research/DIRECTION.yaml` holds the next step. `research/HORIZON.yaml` holds the
bet that step is a step toward. This reads both, plus the measured state from
the evidence ledger, and answers one question:

    given what is actually true in this repository right now, what is the next
    problem, and is it even a problem this trajectory is allowed to work on?

The selector is deliberately hostile to its own file. A human blocker and an
absent external outcome outrank every step HORIZON.yaml proposes, because a
horizon that cannot lose to a blocker is a daydream. This is a mirror, not a
gate: it is absent from verification_manifest.py on purpose.

    python3 scripts/horizon.py            # the bet, the arcs, the selection
    python3 scripts/horizon.py --next     # the next problem, and the prompt for it
    python3 scripts/horizon.py --year 1   # year one of the active trajectory
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HORIZON = ROOT / "research" / "HORIZON.yaml"
DIRECTION = ROOT / "research" / "DIRECTION.yaml"
LEDGER = ROOT / ".claude" / "skills" / "evidence-ledger" / "ledger.py"
PROMPTS = ROOT / ".claude" / "prompts"

# How old an open blocker may get before it outranks everything else here.
BLOCKER_ESCALATION_DAYS = 14


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def ledger_state() -> dict:
    """Measured state, imported from the ledger rather than re-counted here.

    Two counters of the same thing drift apart. Returns {} if the ledger cannot
    be loaded, and the caller reports that rather than guessing a number.
    """
    try:
        spec = importlib.util.spec_from_file_location("_ledger", LEDGER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return {
            "blocking": mod.blocking_block(),
            "outcomes": mod.outcomes_block(),
            "claims": mod.claims_block(),
        }
    except Exception as exc:  # the absence is reported, never interpolated
        return {"error": f"{type(exc).__name__}: {exc}"}


def oldest_blocker(state: dict) -> tuple[int, str]:
    """(age_days, description) of the oldest open blocker, or (0, '')."""
    block = state.get("blocking") or {}
    best = (0, "")
    for it in block.get("hits", []):
        if it.get("state") != "open":
            continue
        age = it.get("age_days") or 0
        if age > best[0]:
            best = (age, f"{it.get('file','?')}:{it.get('line','?')}  {it.get('marker','')}")
    return best


def qualified_total(state: dict) -> int:
    out = state.get("outcomes") or {}
    return int(out.get("qualified_total", 0))


def direction_next() -> list[dict]:
    """Steps whose status is `next`, non-infrastructure first."""
    d = load(DIRECTION)
    steps = [s for s in d.get("steps", []) if s.get("status") == "next"]
    return sorted(steps, key=lambda s: bool(s.get("infra")))


def select(h: dict, state: dict) -> dict:
    """The priority ladder. First rung that fires is the answer.

    The order encodes the one judgement in this file: things only a human can
    do, and things only a stranger can do, come before anything Claude can
    write. Every rung below rung 3 is work that feels like progress.
    """
    active = h["selection"]["active"]
    traj = next(t for t in h["trajectories"] if t["id"] == active)

    if "error" in state:
        return {
            "rung": 0,
            "kind": "SENSOR",
            "what": "The evidence ledger did not load; every count below would be a guess.",
            "detail": state["error"],
            "prompt": None,
        }

    age, where = oldest_blocker(state)
    if age >= BLOCKER_ESCALATION_DAYS:
        return {
            "rung": 1,
            "kind": "BLOCKER",
            "what": f"Clear or formally close the oldest open blocker ({age}d).",
            "detail": f"{where} — no amount of writing here clears one. "
                      "If it will never be cleared, close it as a declared limit.",
            "prompt": "P1-clear-blocker.md",
        }

    if qualified_total(state) == 0:
        return {
            "rung": 2,
            "kind": "EXTERNAL",
            "what": f"Move qualified_outcomes off zero on {active}'s route.",
            "detail": f"{traj['name']}: progress is counted in {traj['unit_of_progress']}. "
                      "Zero across five buckets makes all three trajectories unfalsifiable.",
            "prompt": "P2-external-route.md",
        }

    steps = direction_next()
    if steps:
        s = steps[0]
        return {
            "rung": 3,
            "kind": "STEP",
            "what": f"{s['id']}: {s.get('done_when','')}",
            "detail": f"artifact: {s.get('artifact','—')} · infra={bool(s.get('infra'))}",
            "prompt": "P3-direction-step.md",
        }

    return {
        "rung": 4,
        "kind": "HORIZON",
        "what": f"No DIRECTION step is ready. Take the next unmet year-one state for {active}.",
        "detail": str(h["year_one"][active]),
        "prompt": "P4-year-one.md",
    }


def report(h: dict) -> int:
    sel = h["selection"]
    active = sel["active"]
    W = []
    W.append(f"HORIZON · research/HORIZON.yaml v{h['version']} · opened {h['opened']}")
    W.append("")
    W.append("TRAJECTORIES  three bets on why external uptake is zero")
    for t in h["trajectories"]:
        mark = "»" if t["id"] == active else " "
        W.append(f"  {mark} {t['id']}  {t['name']}")
        W.append(f"       {t['one_line'].strip()}")
        W.append(f"       counts: {t['unit_of_progress']}")
        W.append(f"       {t['kill_condition']['id']}: {t['kill_condition']['condition']}")
    W.append("")
    W.append(f"ACTIVE        {active} since {sel['active_since']} · review {sel['review']}")
    for line in sel["rationale"].strip().splitlines():
        W.append(f"       {line.strip()}")
    W.append("  DISSENT")
    for line in sel["dissent"].strip().splitlines():
        W.append(f"       {line.strip()}")
    W.append("")
    W.append(f"YEAR ONE      {active} · test: {h['year_one'][active]['year_end_test']}")
    for q in ("Q1", "Q2", "Q3", "Q4"):
        for item in h["year_one"][active][q]:
            W.append(f"  {q}   {item}")
    W.append("")
    W.append("FLOOR         true regardless of trajectory; outranks every step above")
    for f in h["year_one"]["common_floor"]:
        hand = "OWNER" if f["owner_hand"] else "here"
        W.append(f"  {f['id']}  [{hand}] {f['what']}")
    W.append("")
    W.append("  python3 scripts/horizon.py --next   # the next problem, selected")
    print("\n".join(W))
    return 0


def report_next(h: dict) -> int:
    state = ledger_state()
    sel = select(h, state)
    active = h["selection"]["active"]
    W = [f"NEXT · rung {sel['rung']} · {sel['kind']} · trajectory {active}", ""]
    W.append(f"  {sel['what']}")
    W.append("")
    for line in sel["detail"].strip().splitlines():
        W.append(f"  {line.strip()}")
    W.append("")
    if sel["prompt"]:
        p = PROMPTS / sel["prompt"]
        W.append(f"  PROMPT  {p.relative_to(ROOT)}" + ("" if p.exists() else "  [MISSING]"))
    W.append("")
    W.append("  Rungs 1 and 2 outrank every step this horizon proposes. If one of them")
    W.append("  is showing, writing the step below it is the failure mode, not the work.")
    print("\n".join(W))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--next", action="store_true", help="select the next problem")
    ap.add_argument("--year", type=int, help="print year N of every arc")
    a = ap.parse_args()
    h = load(HORIZON)
    if a.next:
        return report_next(h)
    if a.year:
        key = f"Y{a.year}"
        for tid, arc in h["arcs"].items():
            print(f"{tid} {key}  {arc.get(key, '—')}")
        return 0
    return report(h)


if __name__ == "__main__":
    sys.exit(main())
