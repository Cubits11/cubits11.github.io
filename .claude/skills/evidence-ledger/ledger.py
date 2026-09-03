#!/usr/bin/env python3
"""The evidence ledger: what this repository has paid for, and what it owes.

Every other verifier here asks "is this claim well-formed?" This one asks the
question none of them ask: **has anything been measured?** It counts, from the
committed artifacts alone:

  1. claims, split by whose artifact supports them (this owner's, or someone
     else's) and whether any rests on a measurement made here;
  2. per-item observation rows this repository produced;
  3. blocking markers — the work only a human can do — with their age;
  4. governing documents per experiment against rows produced;
  5. qualified external outcomes.

It is a mirror, not a gate. It is deliberately NOT in verification_manifest.py:
a number that can fail CI becomes a number people manage. This one is only
allowed to be true.

    python3 .claude/skills/evidence-ledger/ledger.py
    python3 .claude/skills/evidence-ledger/ledger.py --json

Stdlib + PyYAML (already required by scripts/verify_census.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Declared rule, not a guess: a support locator on this owner's GitHub account
# is self-referential evidence; anything else is a third party's artifact. The
# owner's account name is the only input, so the rule is checkable by eye.
SELF_ACCOUNTS = ("github.com/Cubits11/",)

# A claim counts as resting on an OWN MEASUREMENT only if its support locator
# points at a per-item result this repository produced by running an instrument
# against a system it selected — i.e. a path under experiments/<e>/results/.
OWN_MEASUREMENT_PATH = re.compile(r"experiments/[^/]+/results/")

# Work only a human can do, and its state. OPEN markers are the ones that
# matter: nothing in this repository can clear them. CLEARED records a human
# action already taken. NAMED is a gate mentioned in prose — counted, not listed,
# because a document naming a gate is not the gate being open.
BLOCK_MARKERS = {
    "OWNER-PENDING": "open",
    "not evaluable": "open",
    "owner's hand": "open",
    "OWNER-ACTION": "open",
    "OWNER-SUPPLIED": "cleared",
    "AUTHORIZE COMPUTE": "named",
}

TODAY = dt.date.today()


def git(*args: str) -> str:
    try:
        return subprocess.run(("git", *args), cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout
    except OSError:
        return ""


def tracked(*globs: str) -> list[str]:
    out = git("ls-files", "--", *globs)
    return [ln for ln in out.splitlines() if ln]


# ---------------------------------------------------------------- claims

def claims_block() -> dict:
    path = ROOT / "claims.yaml"
    if not path.exists():
        return {"total": 0, "note": "no claims.yaml"}
    try:
        import yaml
    except ImportError:
        return {"total": 0, "note": "PyYAML not installed"}
    doc = yaml.safe_load(path.read_text())
    claims = doc["claims"] if isinstance(doc, dict) and "claims" in doc else doc

    rows = []
    for c in claims:
        sup = c.get("support") or {}
        url = sup.get("url") if isinstance(sup, dict) else None
        if not url:
            origin = "unsupported"
        elif any(a in url for a in SELF_ACCOUNTS):
            origin = ("own-measurement" if OWN_MEASUREMENT_PATH.search(url)
                      else "own-artifact")
        else:
            origin = "third-party-artifact"
        rows.append({
            "id": c.get("id"),
            "origin": origin,
            "support_role": (c.get("dimensions") or {}).get("support_role"),
            "url": url,
        })
    tally: dict[str, int] = {}
    for r in rows:
        tally[r["origin"]] = tally.get(r["origin"], 0) + 1
    executed = sum(1 for r in rows if r["support_role"] == "executed_output")
    return {"total": len(rows), "by_origin": tally,
            "executed_output": executed,
            "own_measurement": tally.get("own-measurement", 0),
            "rows": rows}


# ---------------------------------------------------------- observations

def rows_block() -> dict:
    """Per-item observation rows this repository produced."""
    files = [f for f in tracked("*.jsonl")
             if "/results/" in f or "observations" in Path(f).name]
    total = 0
    detail = []
    for f in files:
        n = sum(1 for _ in (ROOT / f).open())
        detail.append({"file": f, "rows": n})
        total += n
    return {"observation_rows": total, "files": detail}


# ------------------------------------------------------------- blocking

def blame_date(path: str, line: int) -> str | None:
    out = git("blame", "--line-porcelain", "-L", f"{line},{line}", "--", path)
    for ln in out.splitlines():
        if ln.startswith("author-time "):
            ts = int(ln.split()[1])
            return dt.datetime.fromtimestamp(ts).date().isoformat()
    return None


def blocking_block() -> dict:
    hits = []
    seen = set()
    for marker, state in BLOCK_MARKERS.items():
        # Operating instructions are not experiment records: a document that
        # explains a marker is not that marker being open. Without this the
        # ledger inflates every time someone documents it.
        out = git("grep", "-n", "-I", "--", marker,
                  "*.md", "*.yaml", "*.json", "*.py", "*.sh",
                  ":(exclude).claude/", ":(exclude)CLAUDE.md")
        for ln in out.splitlines():
            parts = ln.split(":", 2)
            if len(parts) != 3:
                continue
            path, num, text = parts[0], parts[1], parts[2].strip()
            key = (path, num)
            if key in seen:
                continue
            seen.add(key)
            when = blame_date(path, int(num))
            age = ((TODAY - dt.date.fromisoformat(when)).days
                   if when else None)
            hits.append({"marker": marker, "state": state, "file": path,
                         "line": int(num), "since": when, "age_days": age,
                         "text": text[:110]})
    hits.sort(key=lambda h: (-(h["age_days"] or 0), h["file"]))
    openh = [h for h in hits if h["state"] == "open"]
    return {"count": len(hits), "open": len(openh),
            "cleared": sum(1 for h in hits if h["state"] == "cleared"),
            "named": sum(1 for h in hits if h["state"] == "named"),
            "hits": openh, "all": hits}


# ---------------------------------------------------------- scaffolding

def scaffolding_block(rows: dict) -> dict:
    exps = sorted(p.name for p in (ROOT / "experiments").iterdir()
                  if p.is_dir()) if (ROOT / "experiments").is_dir() else []
    out = []
    for e in exps:
        docs = [f for f in tracked(f"experiments/{e}") if f.endswith(".md")]
        # governing documents outside the experiment dir that name it
        for f in tracked("docs/*.md", "ARTIFACTS/*.md"):
            if e.upper() in Path(f).name.upper():
                docs.append(f)
        n_rows = sum(d["rows"] for d in rows["files"]
                     if d["file"].startswith(f"experiments/{e}/"))
        out.append({"experiment": e, "governing_documents": len(docs),
                    "observation_rows": n_rows, "documents": sorted(docs)})
    return {"experiments": out}


# ------------------------------------------------------------- outcomes

def outcomes_block() -> dict:
    path = ROOT / "distribution" / "outcomes.yaml"
    if not path.exists():
        return {"note": "no outcomes.yaml"}
    try:
        import yaml
    except ImportError:
        return {"note": "PyYAML not installed"}
    d = yaml.safe_load(path.read_text()) or {}
    q = d.get("qualified") or {}
    filled = {k: len(v or []) for k, v in q.items()}
    diag = d.get("diagnostics") or {}
    return {"qualified": filled,
            "qualified_total": sum(filled.values()),
            "categories": len(filled),
            "technical_interactions": diag.get("technical_interactions"),
            "stop_threshold": (d.get("stop_rule") or {}).get(
                "threshold_interactions")}


# ---------------------------------------------------------------- render

def render(data: dict) -> str:
    c, r, b, s, o = (data["claims"], data["rows"], data["blocking"],
                     data["scaffolding"], data["outcomes"])
    L = [f"EVIDENCE LEDGER · {TODAY.isoformat()} · counted from committed artifacts"]

    L.append("")
    L.append("CLAIMS — whose artifact supports them")
    for origin in ("own-measurement", "own-artifact", "third-party-artifact",
                   "unsupported"):
        n = c.get("by_origin", {}).get(origin, 0)
        L.append(f"  {origin:<22} {n:>3}")
    L.append(f"  {'total':<22} {c.get('total', 0):>3}"
             f"   (executed_output: {c.get('executed_output', 0)})")
    L.append("  rule: support URL on this owner's account = own; a path under"
             " experiments/<e>/results/ = own-measurement.")

    L.append("")
    L.append("MEASUREMENTS — per-item rows this repository produced")
    L.append(f"  observation rows: {r['observation_rows']}")
    for d in r["files"]:
        L.append(f"    {d['rows']:>7}  {d['file']}")

    L.append("")
    L.append("BLOCKING — work no amount of Claude time can do")
    L.append(f"  open {b['open']} · cleared {b['cleared']} ·"
             f" gates named in prose {b['named']}")
    if not b["hits"]:
        L.append("  nothing open")
    for h in b["hits"]:
        age = f"{h['age_days']}d" if h["age_days"] is not None else "  ?"
        L.append(f"  [{age:>4} open] {h['file']}:{h['line']}  {h['marker']}")
        L.append(f"               {h['text']}")

    L.append("")
    L.append("SCAFFOLDING — governing documents against rows produced")
    for e in s["experiments"]:
        ratio = ("∞" if e["observation_rows"] == 0
                 else f"{e['governing_documents'] / e['observation_rows']:.3f}")
        L.append(f"  {e['experiment']}: {e['governing_documents']} documents ·"
                 f" {e['observation_rows']} rows · docs/row {ratio}")

    L.append("")
    L.append("EXTERNAL — qualified outcomes")
    if "qualified" in o:
        L.append(f"  qualified {o['qualified_total']} across"
                 f" {o['categories']} categories ·"
                 f" technical interactions {o.get('technical_interactions')}"
                 f" of {o.get('stop_threshold')} before the stop rule")
    else:
        L.append(f"  {o.get('note')}")

    L.append("")
    oldest = b["hits"][0] if b["hits"] else None
    L.append(f"VERDICT: own-measurement claims {c.get('own_measurement', 0)}"
             f"/{c.get('total', 0)} · observation rows {r['observation_rows']}"
             f" · qualified outcomes {o.get('qualified_total', 0)}"
             f" · open blockers {b['open']}"
             + (f" · oldest {oldest['age_days']}d ({oldest['file']})"
                if oldest and oldest["age_days"] is not None else ""))
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable")
    args = ap.parse_args()

    rows = rows_block()
    data = {"date": TODAY.isoformat(), "claims": claims_block(), "rows": rows,
            "blocking": blocking_block(), "scaffolding": scaffolding_block(rows),
            "outcomes": outcomes_block()}
    print(json.dumps(data, indent=2) if args.json else render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
