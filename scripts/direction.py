#!/usr/bin/env python3
"""Where this repository is steering, read from research/DIRECTION.yaml.

The evidence ledger answers "has anything been measured?" for one instant.
The cadence series answers "is the answer moving?" over days. Neither answers
the question a session that has run out of context cannot reconstruct:
**which way is this pointed, and is the next thing I am about to write the
thing it needs?**

A mirror, not a gate — like the ledger, and for the same reason: a number that
can fail CI becomes a number people manage. ``--check`` validates the file's
shape only, which is safe to run in the manifest because shape is not a target.

    python3 scripts/direction.py           # the heading
    python3 scripts/direction.py --check   # schema only (manifest-safe)
    python3 scripts/direction.py --json    # for the record generator
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date, timedelta

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECTION = ROOT / "research" / "DIRECTION.yaml"
SERIES = ROOT / "metrics" / "repo_state.jsonl"

EVIDENCE = ("own_measurement", "observation_rows", "qualified_outcomes",
            "technical_interactions", "blockers_cleared")
SCAFFOLD = ("claims_total", "governing_documents", "checks", "verifiers", "generators")

REQUIRED = ("identity", "ontology", "plane", "corrections", "steps", "budget",
            "kill_conditions", "prior_art", "session_protocol")
STATUSES = {"done", "next", "blocked", "standing"}


def load() -> dict:
    return yaml.safe_load(DIRECTION.read_text(encoding="utf-8"))


def schema(d: dict) -> list[str]:
    bad = [f"missing top-level key {k!r}" for k in REQUIRED if k not in d]
    ids = set()
    for s in d.get("steps", []):
        sid = s.get("id")
        if not sid:
            bad.append("a step has no id")
            continue
        if sid in ids:
            bad.append(f"{sid}: duplicate step id")
        ids.add(sid)
        if s.get("status") not in STATUSES:
            bad.append(f"{sid}: status {s.get('status')!r} not in {sorted(STATUSES)}")
        if "infra" not in s:
            bad.append(f"{sid}: does not declare whether it is infrastructure")
        if not s.get("done_when"):
            bad.append(f"{sid}: no done_when — a step with no completion test is a wish")
    for s in d.get("steps", []):
        for dep in s.get("depends_on") or []:
            if dep not in ids:
                bad.append(f"{s.get('id')}: depends on unknown step {dep}")
    for c in d.get("corrections", []):
        for k in ("id", "replaces", "with", "because"):
            if not c.get(k):
                bad.append(f"correction {c.get('id', '?')}: no {k!r} — an unaudited amendment")
    for u in (d.get("prior_art") or {}).get("unverified", []):
        if u.get("verified") is not False:
            bad.append(f"prior_art {u.get('name')!r}: listed as unverified but flagged verified")
    return bad


def outstanding(d: dict) -> tuple[list[dict], list[dict]]:
    open_steps = [s for s in d["steps"] if s.get("status") in ("next", "blocked")]
    return ([s for s in open_steps if s.get("infra")],
            [s for s in open_steps if not s.get("infra")])


def actionable(d: dict) -> list[dict]:
    done = {s["id"] for s in d["steps"] if s.get("status") == "done"}
    out = []
    for s in d["steps"]:
        if s.get("status") not in ("next", "blocked"):
            continue
        if all(dep in done for dep in (s.get("depends_on") or [])):
            out.append(s)
    return out


def k_infra(weeks: int = 2) -> dict:
    """K-INFRA over calendar weeks, not row counts.

    A week is seven elapsed days. Each boundary is the latest snapshot on or
    before its target date, so a missed day shifts a window back rather than
    shortening it — the series has real gaps and a kill condition that silently
    stops being computable is worse than one that waits. A window shorter than
    seven days, or a pair spanning less than 7 * weeks, cannot fire: that is the
    defect this replaced, where seven *rows* back could be seven days of daily
    snapshots or one day of backfill.
    """
    if weeks < 1:
        raise ValueError("weeks must be positive")
    if not SERIES.exists():
        return {"computable": False, "why": "no cadence series"}
    rows = [json.loads(x) for x in SERIES.read_text().splitlines() if x.strip()]
    if not rows:
        return {"computable": False, "why": "empty cadence series"}
    try:
        dated = [(date.fromisoformat(r["date"]), r) for r in rows]
    except (KeyError, TypeError, ValueError):
        return {"computable": False, "why": "invalid snapshot date"}
    if any(a >= b for (a, _), (b, _) in zip(dated, dated[1:])):
        return {"computable": False, "why": "snapshot dates must strictly increase"}

    last = dated[-1][0]
    if (last - dated[0][0]).days < 7 * weeks:
        return {"computable": False,
                "why": f"series spans {(last - dated[0][0]).days} days; need {7 * weeks}"}

    def on_or_before(target):  # latest snapshot not after target
        found = None
        for d, r in dated:
            if d <= target:
                found = (d, r)
            else:
                break
        return found

    # Walk back one week at a time from the newest snapshot. Each boundary is
    # measured from the boundary before it, not from `last`, so a gap pushes the
    # whole chain back and every window stays at least seven days wide.
    marks = [dated[-1]]
    for _ in range(weeks):
        prev = on_or_before(marks[-1][0] - timedelta(days=7))
        if prev is None:
            return {"computable": False,
                    "why": f"no snapshot on or before {(marks[-1][0] - timedelta(days=7)).isoformat()}"}
        marks.append(prev)
    required = EVIDENCE + SCAFFOLD
    if any(f not in r for _, r in marks for f in required):
        return {"computable": False, "why": "week boundary snapshot lacks required counters"}

    spans = [(marks[i + 1], marks[i]) for i in range(weeks)]

    fired = []
    for (_, base), (_, now) in spans:
        ev = any(now[f] != base[f] for f in EVIDENCE)
        sc = any(now[f] != base[f] for f in SCAFFOLD)
        fired.append(sc and not ev)
    return {"computable": True, "windows": len(spans), "scaffold_only": fired,
            "fired": all(fired),
            "span": f"{marks[-1][0].isoformat()} to {marks[0][0].isoformat()}"}


def report(d: dict) -> int:
    o = d["ontology"]
    infra, work = outstanding(d)
    acts = actionable(d)
    kill = k_infra()

    L = [f"DIRECTION · research/DIRECTION.yaml v{d['version']} · opened {d['opened']}", ""]
    L += ["  " + line for line in d["identity"]]
    L += ["", "ONTOLOGY  the sentence the ten steps are consequences of",
          f"    from  {o['from'].strip()}",
          f"    to    {o['to'].strip()}",
          f"    order {' -> '.join(o['hierarchy'])}", ""]

    L.append("PLANE     admissibility " + d["plane"]["admissibility"])
    for name, e in d["plane"]["edges"].items():
        mark = {"enforced": "✓", "partial": "~", "absent": "·"}[e["status"]]
        L.append(f"  {mark} {name}  {e['asks']:<52} {e['status']}")
    L.append("")

    L.append("NEXT      steps whose dependencies are done")
    if not acts:
        L.append("  none actionable — every open step is waiting on another")
    for s in acts:
        tag = "infra" if s.get("infra") else "WORK"
        L.append(f"  [{tag}] {s['id']}  {s['done_when'].strip()[:96]}")
        if s.get("artifact"):
            L.append(f"         -> {s['artifact']}")
    L.append("")

    L.append("BUDGET    infrastructure outstanding must not exceed work outstanding")
    L.append(f"  infrastructure {len(infra):>2}   {' '.join(s['id'] for s in infra) or '—'}")
    L.append(f"  work           {len(work):>2}   {' '.join(s['id'] for s in work) or '—'}")
    if len(infra) > len(work):
        L.append("  VIOLATED — the next action is a work step or a human blocker, "
                 "not another verifier.")
    else:
        L.append("  ok — within budget.")
    L.append("")

    L.append("KILL      K-INFRA: two consecutive weeks of scaffold-only movement")
    if not kill["computable"]:
        L.append(f"  not computable ({kill['why']})")
    else:
        marks = ", ".join("scaffold-only" if f else "evidence moved"
                          for f in kill["scaffold_only"])
        L.append(f"  {kill['windows']} window(s) over {kill['span']}: {marks}")
        L.append("  FIRED — stop building." if kill["fired"] else "  not fired.")
    L.append("")

    n_unver = len((d.get("prior_art") or {}).get("unverified", []))
    L.append(f"DEBT      {n_unver} citation(s) unverified from this host; "
             f"no novelty claim leaves without a recorded search")
    L.append("")
    L.append("STANDING  " + d["session_protocol"]["standing_prompt"].strip())
    print("\n".join(L))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="validate shape only")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    args = ap.parse_args()

    if not DIRECTION.exists():
        print(f"FAIL  {DIRECTION.relative_to(ROOT)} is absent — the repository has no "
              f"recorded heading")
        return 1
    d = load()
    bad = schema(d)
    if args.check:
        for b in bad:
            print(f"FAIL  direction: {b}")
        if bad:
            return 1
        infra, work = outstanding(d)
        print(f"ok    direction well-formed: {len(d['steps'])} steps, "
              f"{len(d['corrections'])} audited corrections, "
              f"{len(d['plane']['edges'])} plane edges, "
              f"budget {len(infra)} infra / {len(work)} work")
        return 0
    if bad:
        for b in bad:
            print(f"FAIL  direction: {b}")
        return 1
    if args.json:
        infra, work = outstanding(d)
        print(json.dumps({"direction": d, "actionable": actionable(d),
                          "budget": {"infrastructure": [s["id"] for s in infra],
                                     "work": [s["id"] for s in work],
                                     "violated": len(infra) > len(work)},
                          "k_infra": k_infra()}, indent=2))
        return 0
    return report(d)


if __name__ == "__main__":
    raise SystemExit(main())
