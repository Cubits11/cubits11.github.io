#!/usr/bin/env python3
"""E9 scoring: raw per-item probabilities from the two pinned guards, nothing else.

    python3 experiments/e9/run/score.py --set SET     # calibration | stress | scout_<candidate> |
                                                     # measurement_<candidate>
    python3 experiments/e9/run/score.py --assemble    # results/scores.json in the runner's shape

Every score is the guard's probability for its injection class. No threshold,
flag or miss is computed here. Thresholds are the runner's, from the contract.

Refusals, all before any model loads. E8 refused only its evaluation sets;
E9 refuses every set until:
  1. contract.json is committed at status frozen and unchanged since;
  2. freeze.json is committed, unchanged, and present byte for byte on
     origin/main, so the time GitHub received it is an out-of-repository
     witness that the freeze preceded the first score;
  3. the set's item list is committed, unchanged, and hashes to what
     freeze.json recorded;
  4. protocol.json above "results" still hashes to what freeze.json recorded;
  5. for a measurement set, the committed protocol.json names that candidate
     as admitted.

Runs only under the narrow exemption of 2026-09-06: both guards are ungated,
under 1B parameters, Apache-2.0, pinned by revision, and scored only on items
an adopted freeze lists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E9 = ROOT / "experiments/e9"
FREEZE, RESULTS = E9 / "freeze", E9 / "results"
SCORES = RESULTS / "scores"
REL = "experiments/e9"
csv.field_size_limit(2**31 - 1)


def git_bytes(ref: str, rel: str) -> bytes | None:
    r = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def declared_digest(protocol: dict) -> str:
    """Everything in protocol.json except the results admit.py appends."""
    body = {k: v for k, v in protocol.items() if k != "results"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def refusal(setname: str) -> str | None:
    for rel in ("contract.json", "freeze/freeze.json", f"freeze/items_{setname}.csv"):
        head = git_bytes("HEAD", f"{REL}/{rel}")
        if head is None:
            return f"{REL}/{rel} is not committed"
        if head != (E9 / rel).read_bytes():
            return f"{REL}/{rel} differs from its committed bytes"
    if json.loads((E9 / "contract.json").read_text()).get("status") != "frozen":
        return "contract.json is not at status frozen"
    if git_bytes("origin/main", f"{REL}/freeze/freeze.json") != (FREEZE / "freeze.json").read_bytes():
        return "freeze.json is not on origin/main byte for byte; publish the freeze before scoring"
    freeze = json.loads((FREEZE / "freeze.json").read_text())
    items = FREEZE / f"items_{setname}.csv"
    if hashlib.sha256(items.read_bytes()).hexdigest() != freeze["items"].get(items.name):
        return f"{items.name} does not hash to what freeze.json recorded"
    protocol = json.loads((FREEZE / "protocol.json").read_text())
    if declared_digest(protocol) != freeze["protocol_declared_sha256"]:
        return "protocol.json above results no longer matches the frozen declaration"
    if setname.startswith("measurement_"):
        committed = git_bytes("HEAD", f"{REL}/freeze/protocol.json")
        admitted = (json.loads(committed).get("results") or {}).get("admitted") if committed else None
        if admitted != setname.removeprefix("measurement_"):
            return f"the committed protocol.json does not record {setname.removeprefix('measurement_')!r} as admitted"
    return None


def guards() -> dict[str, tuple[str, str]]:
    src = json.loads((FREEZE / "sources.json").read_text())
    return {g["slot"]: (g["hf_id"], g["revision"]) for g in src["guards"]}


def texts(setname: str) -> list[tuple[str, str]]:
    protocol = json.loads((FREEZE / "protocol.json").read_text())
    if setname == "calibration":
        pool = FREEZE / "sources" / "target-benign.csv"
    elif setname == "stress":
        pool = ROOT / protocol["stress"]["path"]
    else:
        pool = FREEZE / "sources" / f"{setname.split('_', 1)[1]}.csv"
    with pool.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by_index = ({str(i): r["prompt"] for i, r in enumerate(rows)} if setname == "stress"
                else {r["row_index"]: r["prompt"] for r in rows})
    out = []
    with (FREEZE / f"items_{setname}.csv").open() as fh:
        for r in csv.DictReader(fh):
            t = by_index[r["row_index"]]
            if hashlib.sha256(t.encode("utf-8")).hexdigest() != r["text_sha256"]:
                raise SystemExit(f"text drift at {r['id']}")
            out.append((r["id"], t))
    return out


def probs(hf_id: str, rev: str, items: list[tuple[str, str]]) -> list[float]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(hf_id, revision=rev)
    mdl = AutoModelForSequenceClassification.from_pretrained(hf_id, revision=rev).eval()
    labels = {v.upper(): k for k, v in mdl.config.id2label.items()}
    pos = labels.get("INJECTION", labels.get("UNSAFE", labels.get("LABEL_1", 1)))
    out = []
    with torch.no_grad():
        for i in range(0, len(items), 16):
            batch = [t for _, t in items[i:i + 16]]
            enc = tok(batch, return_tensors="pt", truncation=True, max_length=512, padding=True)
            out += torch.softmax(mdl(**enc).logits, -1)[:, pos].tolist()
            print(f"    {min(i + 16, len(items))}/{len(items)}", end="\r", file=sys.stderr)
    return out


def assemble() -> int:
    contract = json.loads((E9 / "contract.json").read_text())
    admitted = (json.loads((FREEZE / "protocol.json").read_text()).get("results") or {}).get("admitted")
    if not admitted:
        print("REFUSED: no candidate is admitted, so there is no measurement pool to assemble")
        return 1
    pools = {contract["execution_plan"]["calibration"]: "calibration",
             contract["execution_plan"]["evaluation"]: f"measurement_{admitted}"}
    out = {"guards": [], "pools": {}}
    for pool_name, setname in pools.items():
        rec = json.loads((SCORES / f"{setname}.probs.json").read_text())
        out["guards"] = out["guards"] or list(rec["guards"])
        ids = list(next(iter(rec["guards"].values())))
        out["pools"][pool_name] = {i: {g: rec["guards"][g][i] for g in out["guards"]} for i in ids}
    path = RESULTS / "scores.json"
    path.write_text(json.dumps(out, sort_keys=True))
    print(f"wrote {path.relative_to(ROOT)}  pools={ {k: len(v) for k, v in out['pools'].items()} }")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set")
    ap.add_argument("--assemble", action="store_true")
    a = ap.parse_args()
    if a.assemble:
        return assemble()
    if not a.set:
        ap.error("--set or --assemble")
    why = refusal(a.set)
    if why:
        print(f"REFUSED: {why}. Scoring before the freeze is committed and published is the rescue.",
              file=sys.stderr)
        return 2
    items = texts(a.set)
    SCORES.mkdir(parents=True, exist_ok=True)
    rec = {"set": a.set, "n": len(items), "guards": {}}
    for slot, (hf_id, rev) in guards().items():
        print(f"  {slot} {hf_id}@{rev[:8]}", file=sys.stderr)
        rec["guards"][slot] = dict(zip([i for i, _ in items], probs(hf_id, rev, items)))
    out = SCORES / f"{a.set}.probs.json"
    out.write_text(json.dumps(rec))
    print(f"wrote {out.relative_to(ROOT)}  n={len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
