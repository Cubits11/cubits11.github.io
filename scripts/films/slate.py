#!/usr/bin/env python3
"""Validate films/slate.yaml and render films/SLATE.md from it.

Gate: every live concept must score at least the declared minimum on
conceptual_clarity, epistemic_integrity and distinctiveness; anything below
belongs in `killed` with a reason. Every concept carries every axis. Every
cohort_a concept must have a film directory with a manifest. --check fails on
drift between the YAML and the committed Markdown.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "films" / "slate.yaml"
OUT = ROOT / "films" / "SLATE.md"
FIELDS = ["thesis", "epistemic_operation", "visual_mechanism", "why_motion", "opening_image", "turn",
          "final_image", "evidence_dependency", "misunderstanding_risk", "implementation", "complexity", "grammar"]


def validate(data: dict) -> list[str]:
    errors = []
    axes = data["axes"]
    gate = data["gate"]
    ids = set()
    for c in data["concepts"]:
        ids.add(c["id"])
        for f in ["id", "title", "status", "scores"] + FIELDS:
            if f not in c:
                errors.append(f"{c.get('id')}: missing {f}")
        for a in axes:
            if a not in c.get("scores", {}):
                errors.append(f"{c['id']}: missing score {a}")
        for a, mn in gate.items():
            if c.get("scores", {}).get(a, 0) < mn:
                errors.append(f"{c['id']}: {a} = {c['scores'].get(a)} < gate {mn} — kill or replace it")
        if c["status"] == "cohort_a" and not (ROOT / "films" / c["id"] / "manifest.yaml").exists():
            errors.append(f"{c['id']}: cohort_a without films/{c['id']}/manifest.yaml")
    for kc in data.get("killed", []):
        if not kc.get("reason"):
            errors.append(f"killed {kc.get('id')}: no reason")
        if kc.get("replaced_by") and kc["replaced_by"] not in ids:
            errors.append(f"killed {kc['id']}: replaced_by {kc['replaced_by']} is not a live concept")
        if all(kc["scores"].get(a, 0) >= mn for a, mn in gate.items()):
            errors.append(f"killed {kc['id']}: passes the gate — why is it killed?")
    if len(data["concepts"]) < 30:
        errors.append(f"only {len(data['concepts'])} live concepts; the slate law asks for at least 30")
    return errors


def render(data: dict) -> str:
    axes = data["axes"]
    short = {"conceptual_clarity": "clar", "novelty": "nov", "epistemic_integrity": "integ", "visual_memorability": "memo",
             "silent_comprehension": "silent", "poster_strength": "poster", "render_feasibility": "feas", "distinctiveness": "dist"}
    L = ["# The slate — 30 concepts, scored", "",
         "GENERATED from films/slate.yaml by scripts/films/slate.py. Do not edit by hand.", "",
         f"Dated {data['dated']}. Gate: " + ", ".join(f"{k} ≥ {v}" for k, v in data["gate"].items()) +
         ". Cohort A scores are pre-render predictions; films/LEDGER.md records what the pixels showed.", "",
         "| # | concept | status | grammar | " + " | ".join(short[a] for a in axes) + " | mean |",
         "|---|---|---|---|" + "|".join(["---"] * axes.__len__()) + "|---|"]
    for i, c in enumerate(data["concepts"], 1):
        s = c["scores"]
        mean = sum(s[a] for a in axes) / len(axes)
        L.append(f"| {i} | {c['title']} | {c['status']} | {c['grammar']} | " + " | ".join(str(s[a]) for a in axes) + f" | {mean:.1f} |")
    L += ["", "## Killed and replaced", "", "| concept | clar | integ | dist | reason | replaced by |", "|---|---|---|---|---|---|"]
    for kc in data.get("killed", []):
        s = kc["scores"]
        L.append(f"| {kc['title']} | {s['conceptual_clarity']} | {s['epistemic_integrity']} | {s['distinctiveness']} | {kc['reason']} | {kc.get('replaced_by', '—')} |")
    L += ["", "## Concept records", ""]
    for i, c in enumerate(data["concepts"], 1):
        L += [f"### {i}. {c['title']} (`{c['id']}`) — {c['status']}", ""]
        for f in FIELDS:
            v = c[f]
            if isinstance(v, list):
                v = ", ".join(f"`{x}`" for x in v) if v else "— (constructed or registry-text only)"
            L.append(f"- **{f.replace('_', ' ')}:** {v}")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load(SRC.read_text())
    errors = validate(data)
    for e in errors:
        print(f"FAIL  {e}")
    if errors:
        return 1
    text = render(data)
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"FAIL  {OUT.relative_to(ROOT)} is stale — run scripts/films/slate.py")
            return 1
        print(f"ok    slate: {len(data['concepts'])} live concepts pass the gate, {len(data.get('killed', []))} killed with reasons; SLATE.md current")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(data['concepts'])} concepts, {len(data.get('killed', []))} killed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
