#!/usr/bin/env python3
"""E8 scoring: raw per-item probabilities from the two pinned guards, nothing else.

    python3 experiments/e8/run/score.py --set SET          # SET: benign_scout | scout_<candidate> |
                                                           #      benign_calibration | harmful
    python3 experiments/e8/run/score.py --assemble         # results/scores.json in the runner's shape

Every score is the guard's probability for its unsafe/injection class; no
threshold, flag or miss is computed here. Thresholds are the runner's, from the
contract. Refusals, in order: an evaluation set (benign_calibration, harmful)
will not be scored until scouting.json records a choice, contract.json is
committed at status frozen, and freeze.json is committed. The commit is the
evidence that the freeze preceded the score; a file on disk is not.

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
E8 = ROOT / "experiments/e8"
FREEZE, RESULTS = E8 / "freeze", E8 / "results"
SCORES = RESULTS / "scores"


def committed(rel: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel}"], cwd=ROOT, capture_output=True).returncode == 0


def committed_json(rel: str) -> dict | None:
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def guards() -> dict[str, tuple[str, str]]:
    src = json.loads((FREEZE / "sources.json").read_text())
    return {g["slot"]: (g["hf_id"], g["revision"]) for g in src["guards"]}


def texts(setname: str) -> list[tuple[str, str]]:
    plan = json.loads((FREEZE / "scouting.json").read_text())
    if setname.startswith("benign"):
        pool = ROOT / plan["benign"]["path"]
        col = "prompt"
    else:
        cand = setname.removeprefix("scout_") if setname.startswith("scout_") else plan["results"]["chosen"]
        pool = FREEZE / "sources" / f"{cand}.csv"
        col = "prompt"
    with pool.open(encoding="utf-8") as fh:
        rows = [r[col] for r in csv.DictReader(fh)]
    by_index = rows if setname.startswith("benign") else None
    if by_index is None:
        with pool.open(encoding="utf-8") as fh:
            by_index = {r["row_index"]: r[col] for r in csv.DictReader(fh)}
    out = []
    for r in csv.DictReader((FREEZE / f"items_{setname}.csv").open()):
        t = by_index[int(r["row_index"])] if isinstance(by_index, list) else by_index[r["row_index"]]
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


def refuse_unless_frozen(setname: str) -> str | None:
    if setname not in ("benign_calibration", "harmful"):
        return None
    plan = json.loads((FREEZE / "scouting.json").read_text())
    if not plan.get("results") or not plan["results"].get("chosen"):
        return "scouting.json records no chosen candidate"
    contract = committed_json("experiments/e8/contract.json")
    if contract is None or contract.get("status") != "frozen":
        return "experiments/e8/contract.json is not committed at status frozen"
    if not committed("experiments/e8/freeze/freeze.json"):
        return "experiments/e8/freeze/freeze.json is not committed"
    if not committed(f"experiments/e8/freeze/items_{setname}.csv"):
        return f"experiments/e8/freeze/items_{setname}.csv is not committed"
    return None


def assemble() -> int:
    contract = json.loads((E8 / "contract.json").read_text())
    pools = {contract["execution_plan"]["calibration"]: "benign_calibration",
             contract["execution_plan"]["evaluation"]: "harmful"}
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
    why = refuse_unless_frozen(a.set)
    if why:
        print(f"REFUSED: {why}. This has no recovery: scoring before the freeze is committed is the rescue.",
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
