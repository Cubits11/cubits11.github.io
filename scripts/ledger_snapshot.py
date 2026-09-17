#!/usr/bin/env python3
"""Freeze the volatile ledger counts so a prose surface cannot quietly go stale.

The evidence ledger prints the repository's own state. Those counts move: rows
get produced, blockers clear, claims register. Any document that types one of
them by hand is correct for a day and wrong afterwards, silently — which is how
a film script came to say "observation rows: zero" three days after 4,800 rows
were committed.

This is the same drift gate the generated pages already use, pointed at the
counter instead of at the registry. ``metrics/ledger_snapshot.json`` is
GENERATED from ``.claude/skills/evidence-ledger/ledger.py`` and carries only the
facts that change when the repository changes — never a clock. Blocker *ages*
are deliberately excluded: an age moves every midnight, and a gate that fails
every midnight teaches people to ignore it.

A prose surface that speaks these numbers cites this file and its ``as_of``
date. When the repository moves, ``--check`` fails, the snapshot is
regenerated, and every surface that cites it is re-read in the same change.

    python3 scripts/ledger_snapshot.py            # regenerate
    python3 scripts/ledger_snapshot.py --check    # drift gate (exit 0 / 1)
    python3 scripts/ledger_snapshot.py --print    # show, write nothing

This is a mirror with a gate, not a target. The counts are allowed to be true
and never to be optimised; nothing in this repository may set a goal for them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / ".claude" / "skills" / "evidence-ledger" / "ledger.py"
OUT = ROOT / "metrics" / "ledger_snapshot.json"


def load_ledger():
    spec = importlib.util.spec_from_file_location("evidence_ledger", LEDGER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {LEDGER}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snapshot() -> dict:
    led = load_ledger()
    rows = led.rows_block()
    claims = led.claims_block()
    blocking = led.blocking_block()
    scaffolding = led.scaffolding_block(rows)
    outcomes = led.outcomes_block()
    return {
        "_generated_by": "scripts/ledger_snapshot.py",
        "_source": ".claude/skills/evidence-ledger/ledger.py",
        "_note": (
            "Counts only. Blocker ages are excluded on purpose: they change with "
            "the calendar and would make this gate fire on days nothing happened. "
            "Run the ledger itself for ages."
        ),
        "as_of": dt.date.today().isoformat(),
        "claims": {
            "total": claims.get("total"),
            "own_measurement": claims.get("own_measurement"),
            "executed_output": claims.get("executed_output"),
            "by_origin": dict(sorted((claims.get("by_origin") or {}).items())),
        },
        "observations": {
            "rows": rows.get("observation_rows"),
            "files": sorted(
                ({"file": d["file"], "rows": d["rows"]} for d in rows.get("files", [])),
                key=lambda d: d["file"],
            ),
        },
        "blocking": {
            "markers": blocking.get("count"),
            "open": blocking.get("open"),
            "cleared": blocking.get("cleared"),
            "named": blocking.get("named"),
        },
        "scaffolding": [
            {
                "experiment": e["experiment"],
                "governing_documents": e["governing_documents"],
                "observation_rows": e["observation_rows"],
            }
            for e in scaffolding.get("experiments", [])
        ],
        "outcomes": {
            "qualified_total": outcomes.get("qualified_total"),
            "categories": outcomes.get("categories"),
            "technical_interactions": outcomes.get("technical_interactions"),
            "stop_threshold": outcomes.get("stop_threshold"),
        },
    }


def comparable(d: dict) -> dict:
    """Everything except the date the snapshot was taken."""
    return {k: v for k, v in d.items() if not k.startswith("_") and k != "as_of"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail on drift, write nothing")
    ap.add_argument("--print", dest="show", action="store_true", help="print, write nothing")
    args = ap.parse_args()

    current = snapshot()
    if args.show:
        print(json.dumps(current, indent=2))
        return 0

    if args.check:
        if not OUT.exists():
            print(f"FAIL  {OUT.relative_to(ROOT)} does not exist — regenerate it")
            return 1
        recorded = json.loads(OUT.read_text(encoding="utf-8"))
        if comparable(recorded) != comparable(current):
            print("FAIL  ledger snapshot is stale — the repository moved and the "
                  "recorded counts did not")
            for key in sorted(set(comparable(recorded)) | set(comparable(current))):
                a, b = comparable(recorded).get(key), comparable(current).get(key)
                if a != b:
                    print(f"      {key}:\n        recorded  {json.dumps(a)}\n"
                          f"        current   {json.dumps(b)}")
            print("      Regenerate with: python3 scripts/ledger_snapshot.py")
            print("      Then re-read every surface that cites metrics/ledger_snapshot.json.")
            return 1
        print(f"ok    ledger snapshot current (as of {recorded['as_of']}): "
              f"{recorded['claims']['total']} claims, "
              f"{recorded['claims']['own_measurement']} resting on own measurement, "
              f"{recorded['observations']['rows']} observation rows, "
              f"{recorded['outcomes']['qualified_total']} qualified outcomes, "
              f"{recorded['blocking']['open']} open blockers")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} as of {current['as_of']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
