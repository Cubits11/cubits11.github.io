#!/usr/bin/env python3
"""E8 draws and the disjointness gate. Runs before any model loads.

Two modes, in the order the scouting protocol fixes:

    python3 experiments/e8/run/draw.py scout                 # scouting slices + both benign sets
    python3 experiments/e8/run/draw.py evaluation CANDIDATE  # ranks 201..1200 of the chosen candidate

Ranks are sha256(seed:candidate:row_index), so a draw is a function of the
seed in scouting.json and nothing else. The gate: no drawn hash may appear in
E2, E3 or E3B's frozen items, and no evaluation hash may appear in any scouting
slice. It exits nonzero rather than warning.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/e8/freeze"
SOURCES = FREEZE / "sources"


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def plan() -> dict:
    return json.loads((FREEZE / "scouting.json").read_text())


def prior_hashes(p: dict) -> set[str]:
    out = set()
    for d in p["prior_frozen"]:
        for f in (ROOT / d).glob("items_*.csv"):
            for r in csv.DictReader(f.open()):
                if r.get("text_sha256"):
                    out.add(r["text_sha256"])
    return out


def ranked(p: dict, cand_id: str, rows: list[tuple[str, str]], prior: set[str]) -> list[tuple[str, str, str]]:
    """(id, row_index, text_sha256) deduplicated by text, prior removed, ranked by the seed."""
    seen, out = set(), []
    for row_index, text in rows:
        h = sha(text)
        if h in seen or h in prior:
            continue
        seen.add(h)
        out.append((row_index, h))
    out.sort(key=lambda t: sha(f"{p['seed']}:{cand_id}:{t[0]}"))
    scheme = "orbench80k-{}" if cand_id == "benign" else next(
        c["id_scheme"] for c in p["candidates"] if c["id"] == cand_id).replace("<row_index>", "{}")
    return [(scheme.format(i), i, h) for i, h in out]


def write(name: str, items: list[tuple[str, str, str]]) -> None:
    with (FREEZE / f"{name}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "row_index", "text_sha256"])
        w.writerows(items)


def candidate_rows(cand: dict) -> list[tuple[str, str]]:
    with (SOURCES / f"{cand['id']}.csv").open(encoding="utf-8") as fh:
        return [(r["row_index"], r["prompt"]) for r in csv.DictReader(fh)]


def benign_rows(p: dict) -> list[tuple[str, str]]:
    path = ROOT / p["benign"]["path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != p["benign"]["sha256"]:
        raise SystemExit(f"GATE FAIL — benign source sha256 {digest[:12]}… is not the pinned {p['benign']['sha256'][:12]}…")
    with path.open(encoding="utf-8") as fh:
        return [(str(i), r["prompt"]) for i, r in enumerate(csv.DictReader(fh))]


def scout(p: dict) -> int:
    prior = prior_hashes(p)
    n_s, n_bs, n_e, n_bc = (p["sizes"][k] for k in ("scout_harmful_per_candidate", "scout_benign_calibration",
                                                    "evaluation_harmful", "evaluation_benign_calibration"))
    print(f"prior frozen hashes (E2+E3+E3B)  {len(prior)}")
    for cand in p["candidates"]:
        items = ranked(p, cand["id"], candidate_rows(cand), prior)
        eligible = len(items) >= n_s + n_e
        print(f"{cand['id']}: available after dedup and removal {len(items)}  "
              f"{'ok' if eligible else 'INELIGIBLE by size'}")
        write(f"items_scout_{cand['id']}", items[:n_s])
        cand["available_after_removal"] = len(items)
    ben = ranked(p, "benign", benign_rows(p), prior)
    if len(ben) < n_bs + n_bc:
        print("GATE FAIL — benign pool exhausted")
        return 1
    write("items_benign_scout", ben[:n_bs])
    write("items_benign_calibration", ben[n_bs:n_bs + n_bc])
    print(f"benign: available {len(ben)}; scouting calibration {n_bs}, evaluation calibration {n_bc}")
    p["benign"]["available_after_removal"] = len(ben)
    (FREEZE / "scouting.json").write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print("GATE PASS — prior frozen hashes removed before ranking; scouting slices written; counts recorded")
    return 0


def evaluation(p: dict, cand_id: str) -> int:
    if not p.get("results") or p["results"].get("chosen") != cand_id:
        print(f"REFUSED: scouting.json does not record {cand_id!r} as the chosen candidate")
        return 1
    cand = next(c for c in p["candidates"] if c["id"] == cand_id)
    prior = prior_hashes(p)
    burned = set()
    for f in FREEZE.glob("items_scout_*.csv"):
        burned |= {r["text_sha256"] for r in csv.DictReader(f.open())}
    burned |= {r["text_sha256"] for r in csv.DictReader((FREEZE / "items_benign_scout.csv").open())}
    n_s, n_e = p["sizes"]["scout_harmful_per_candidate"], p["sizes"]["evaluation_harmful"]
    items = ranked(p, cand_id, candidate_rows(cand), prior)[n_s:n_s + n_e]
    hashes = {h for _, _, h in items}
    if len(items) < n_e:
        print(f"GATE FAIL — {cand_id} yields {len(items)} < {n_e} evaluation items")
        return 1
    if hashes & burned:
        print(f"GATE FAIL — {len(hashes & burned)} evaluation items intersect a scouting slice")
        return 1
    if hashes & prior:
        print(f"GATE FAIL — {len(hashes & prior)} evaluation items intersect E2/E3/E3B")
        return 1
    write("items_harmful", items)
    print(f"GATE PASS — {n_e} evaluation items from {cand_id}, ranks {n_s + 1}..{n_s + n_e}; "
          f"zero intersection with {len(burned)} burned and {len(prior)} prior hashes")
    return 0


def main() -> int:
    p = plan()
    if len(sys.argv) >= 2 and sys.argv[1] == "scout":
        return scout(p)
    if len(sys.argv) == 3 and sys.argv[1] == "evaluation":
        return evaluation(p, sys.argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
