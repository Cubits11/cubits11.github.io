#!/usr/bin/env python3
"""E9's draws and the disjointness gate. Runs before any model loads and before the freeze.

    python3 experiments/e9/run/draw.py

Every partition is drawn here, at once: calibration, stress, and for each
candidate a scouting slice followed by a measurement slice. Ranks are
sha256(seed:source:row_index), so a draw is a function of protocol.json's seed
and nothing else. The gate: no drawn hash may appear in a prior freeze, and no
hash may appear in two E9 partitions. It exits nonzero rather than warning.

The counts go into protocol.json["draw"] before the freeze commit. After it,
nothing in protocol.json above "results" changes: freeze.json records the
digest, and admit.py and score.py refuse a protocol that no longer matches.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE = ROOT / "experiments/e9/freeze"
SOURCES = FREEZE / "sources"
# Real first turns run past the csv module's 128 KiB default; the population keeps them.
csv.field_size_limit(2**31 - 1)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def plan() -> dict:
    return json.loads((FREEZE / "protocol.json").read_text())


def prior_hashes(p: dict) -> set[str]:
    out = set()
    for d in p["prior_frozen"]:
        for f in sorted((ROOT / d).glob("items_*.csv")):
            with f.open() as fh:
                out |= {r["text_sha256"] for r in csv.DictReader(fh) if r.get("text_sha256")}
    return out


def ranked(seed: str, source: str, scheme: str, rows: list[tuple[str, str]], taken: set[str]) -> list[tuple[str, str, str]]:
    """(id, row_index, text_sha256): deduplicated by text, taken hashes removed, ranked by the seed."""
    seen, out = set(), []
    for row_index, text in rows:
        h = sha(text)
        if h in seen or h in taken:
            continue
        seen.add(h)
        out.append((row_index, h))
    out.sort(key=lambda t: sha(f"{seed}:{source}:{t[0]}"))
    return [(scheme.replace("<row_index>", str(i)), str(i), h) for i, h in out]


def write(name: str, items: list[tuple[str, str, str]]) -> None:
    with (FREEZE / f"{name}.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "row_index", "text_sha256"])
        w.writerows(items)


def read_items(name: str) -> set[str]:
    with (FREEZE / f"{name}.csv").open() as fh:
        return {r["text_sha256"] for r in csv.DictReader(fh)}


def source_rows(name: str) -> list[tuple[str, str]]:
    with (SOURCES / f"{name}.csv").open(encoding="utf-8") as fh:
        return [(r["row_index"], r["prompt"]) for r in csv.DictReader(fh)]


def stress_rows(p: dict) -> list[tuple[str, str]]:
    path = ROOT / p["stress"]["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != p["stress"]["sha256"]:
        raise SystemExit("GATE FAIL — the stress source is not the pinned file")
    with path.open(encoding="utf-8") as fh:
        return [(str(i), r["prompt"]) for i, r in enumerate(csv.DictReader(fh))]


def main() -> int:
    p = plan()
    if p.get("results"):
        print("REFUSED: protocol.json records results; a draw after admission is a second look")
        return 1
    if (FREEZE / "freeze.json").exists():
        print("REFUSED: freeze.json exists; the draw is frozen and is not redrawn")
        return 1
    seed, sizes = p["seed"], p["sizes"]
    prior = prior_hashes(p)
    taken = set(prior)
    draw = {"prior_frozen_hashes": len(prior), "partitions": {}}

    def take(name: str, items: list[tuple[str, str, str]]) -> None:
        write(name, items)
        taken.update(h for _, _, h in items)
        draw["partitions"][name] = len(items)

    tb = ranked(seed, "target-benign", p["target_benign"]["id_scheme"], source_rows("target-benign"), taken)
    if len(tb) < sizes["calibration"]:
        print(f"GATE FAIL — {len(tb)} target-benign items after removal, {sizes['calibration']} needed")
        return 1
    draw["target_benign"] = {"filter_counts": json.loads((SOURCES / "target-benign.counts.json").read_text()),
                             "available_after_removal": len(tb)}
    take("items_calibration", tb[:sizes["calibration"]])

    st = ranked(seed, "stress", p["stress"]["id_scheme"], stress_rows(p), taken)
    if len(st) < sizes["stress"]:
        print(f"GATE FAIL — {len(st)} stress items after removal, {sizes['stress']} needed")
        return 1
    draw["stress_available_after_removal"] = len(st)
    take("items_stress", st[:sizes["stress"]])

    ns, nm = sizes["scout_harmful_per_candidate"], sizes["measurement_harmful_per_candidate"]
    draw["candidates"] = {}
    for cand in p["candidates"]:
        items = ranked(seed, cand["id"], cand["id_scheme"], source_rows(cand["id"]), taken)
        if len(items) < ns:
            print(f"GATE FAIL — {cand['id']} yields {len(items)} scouting items, {ns} needed")
            return 1
        take(f"items_scout_{cand['id']}", items[:ns])
        take(f"items_measurement_{cand['id']}", items[ns:ns + nm])
        draw["candidates"][cand["id"]] = {"available_after_removal": len(items),
                                          "measurement_n": len(items[ns:ns + nm]),
                                          "measurement_complete": len(items[ns:ns + nm]) == nm}
        print(f"{cand['id']}: {len(items)} available; scouting {ns}, measurement {len(items[ns:ns + nm])}"
              f"{'' if len(items) >= ns + nm else '  (INCOMPLETE: cannot be admitted by size)'}")

    names = sorted(draw["partitions"])
    sets = {n: read_items(n) for n in names}
    for i, a in enumerate(names):
        if sets[a] & prior:
            print(f"GATE FAIL — {a} intersects a prior freeze")
            return 1
        for b in names[i + 1:]:
            if sets[a] & sets[b]:
                print(f"GATE FAIL — {a} and {b} share {len(sets[a] & sets[b])} items")
                return 1
    p["draw"] = draw
    (FREEZE / "protocol.json").write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print(f"GATE PASS — {len(names)} partitions, pairwise disjoint, none in the {len(prior)} prior frozen hashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
