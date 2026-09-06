#!/usr/bin/env python3
"""E3B draw and disjointness gate. Runs before any model loads."""
from __future__ import annotations
import csv, hashlib, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "experiments/e3b/freeze"
SEED = "MC-E3B-PILOT-V1-FREEZE-2026-09-06"
N = 400

def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def rank(i): return sha(f"{SEED}:{i}")

def prior_hashes() -> set[str]:
    """Every text hash already frozen by E2 or E3. Removed before ranking."""
    out = set()
    for exp in ("e2", "e3"):
        d = ROOT / f"experiments/{exp}/freeze"
        for f in d.glob("items_*.csv"):
            for r in csv.DictReader(f.open()):
                if r.get("text_sha256"): out.add(r["text_sha256"])
    return out

def write(name, items):
    with (F / f"{name}.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["id", "row_index", "text_sha256"])
        for i, t in items: w.writerow([i, i.rsplit("-", 1)[1], sha(t)])

def main() -> int:
    prior = prior_hashes()
    inj = [(f"gandalf-{i}", r["prompt"]) for i, r in
           enumerate(csv.DictReader((F / "gandalf.csv").open(encoding="utf-8")))]
    ben = [(f"orbench80k-{i}", r["prompt"]) for i, r in
           enumerate(csv.DictReader((F / "or-bench-80k.csv").open(encoding="utf-8")))]
    inj_a = [(i, t) for i, t in inj if sha(t) not in prior]
    ben_a = [(i, t) for i, t in ben if sha(t) not in prior]
    print(f"prior frozen hashes (E2+E3)   {len(prior)}")
    print(f"injection pool {len(inj)} -> available {len(inj_a)}")
    print(f"benign pool    {len(ben)} -> available {len(ben_a)}")
    if len(inj_a) < N or len(ben_a) < 2 * N:
        print("GATE FAIL — pool exhausted. E3B stops."); return 1
    injd = sorted(inj_a, key=lambda t: rank(t[0]))[:N]
    bend = sorted(ben_a, key=lambda t: rank(t[0]))[:2 * N]
    cal, ev = bend[:N], bend[N:]
    drawn = {sha(t) for _, t in injd + cal + ev}
    if drawn & prior:
        print(f"GATE FAIL — {len(drawn & prior)} drawn items intersect E2/E3."); return 1
    write("items_harmful", injd); write("items_benign_calibration", cal); write("items_benign_evaluation", ev)
    print(f"GATE PASS — zero intersection. injection {len(injd)}, benign {len(cal)}+{len(ev)}")
    return 0

if __name__ == "__main__": sys.exit(main())
