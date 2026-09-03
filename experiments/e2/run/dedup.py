#!/usr/bin/env python3
"""Freeze and re-derive the AdvBench near-duplicate clustering (W2 rule).

The rule is declared in `experiments/e2/freeze/PREREG_SELECTION.md` §6 and
executed here. It reads item TEXT from the pinned upstream CSV — never from
this repository, which commits ids and text hashes only — and writes the
cluster map to `experiments/e2/freeze/dedup_clusters.csv`.

No guard, no score, no outcome is involved: the clustering is a function of
the frozen item text alone. It is committed now so that W7 recomputes on a
map that was fixed before any guard ran.

    python3 experiments/e2/run/dedup.py --check      # re-derive, compare
    python3 experiments/e2/run/dedup.py --write      # regenerate the map
    python3 experiments/e2/run/dedup.py --check --cache DIR   # offline

Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE = HERE.parent / "freeze"
OUT = FREEZE / "dedup_clusters.csv"

SEED = "MC-E2-PILOT-V1-FREEZE-2026-09-01"
SHINGLE_K = 3
PRIMARY = 0.6
BAND = (0.5, 0.6, 0.7)
COLUMN = "goal"


def fetch_bytes(url: str, cache: Path | None, name: str) -> bytes:
    if cache is not None and (cache / name).exists():
        return (cache / name).read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "cubits11-e2-w2-dedup"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / name).write_bytes(raw)
    return raw


def normalize(s: str) -> str:
    """NFKC, casefold, every non-[a-z0-9] run to one space, strip."""
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def shingles(s: str, k: int = SHINGLE_K) -> frozenset:
    t = normalize(s).split()
    if len(t) < k:
        return frozenset([tuple(t)])
    return frozenset(tuple(t[i:i + k]) for i in range(len(t) - k + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def components(sets: list, threshold: float) -> list:
    """Single-linkage connected components at Jaccard >= threshold."""
    parent = list(range(len(sets)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            if jaccard(sets[i], sets[j]) >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    return [find(i) for i in range(len(sets))]


def rank_key(item_id: str) -> str:
    return hashlib.sha256(f"{SEED}:dedup:{item_id}".encode()).hexdigest()


def build(cache: Path | None) -> list[dict]:
    sources = json.loads((FREEZE / "sources.json").read_text())
    h = sources["harmful"]
    url = (f"https://raw.githubusercontent.com/llm-attacks/llm-attacks/"
           f"{h['commit']}/{h['path']}")
    raw = fetch_bytes(url, cache, "harmful_behaviors.csv")
    got = hashlib.sha256(raw).hexdigest()
    if got != h["file_sha256"]:
        sys.exit(f"AdvBench csv sha256 {got[:16]}… != pinned "
                 f"{h['file_sha256'][:16]}… — refusing to cluster on it")
    upstream = list(csv.DictReader(io.StringIO(raw.decode())))

    frozen = list(csv.DictReader((FREEZE / "items_harmful.csv").open(newline="")))
    texts = []
    for r in frozen:
        t = upstream[int(r["row_index"])][COLUMN]
        if hashlib.sha256(t.encode()).hexdigest() != r["text_sha256"]:
            sys.exit(f"{r['id']}: frozen text hash does not reproduce upstream")
        texts.append(t)

    sets = [shingles(t) for t in texts]
    ids = [r["id"] for r in frozen]
    out = [{"id": i, "row_index": r["row_index"]}
           for i, r in zip(ids, frozen)]

    for th in BAND:
        roots = components(sets, th)
        # cluster id = the seeded-rank-first member's id; representative =
        # the same member. Both are order-free functions of the id set.
        members: dict[int, list[int]] = {}
        for idx, root in enumerate(roots):
            members.setdefault(root, []).append(idx)
        label = {}
        for root, idxs in members.items():
            rep = min(idxs, key=lambda k: rank_key(ids[k]))
            for k in idxs:
                label[k] = ids[rep]
        tag = f"c{int(round(th * 100))}"
        for k, row in enumerate(out):
            row[tag] = label[k]
            row[tag + "_rep"] = "1" if label[k] == ids[k] else "0"
    return out


FIELDS = ["id", "row_index"] + [f"c{int(round(t * 100))}{s}"
                                for t in BAND for s in ("", "_rep")]


def render(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def summarize(rows: list[dict]) -> None:
    for t in BAND:
        tag = f"c{int(round(t * 100))}"
        cl = {r[tag] for r in rows}
        sizes: dict[str, int] = {}
        for r in rows:
            sizes[r[tag]] = sizes.get(r[tag], 0) + 1
        big = sorted(sizes.values(), reverse=True)[:5]
        mark = " (primary)" if t == PRIMARY else ""
        print(f"  J>={t}: {len(cl)} clusters of {len(rows)} items · "
              f"singletons {sum(1 for v in sizes.values() if v == 1)} · "
              f"largest {big}{mark}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="regenerate the map")
    ap.add_argument("--check", action="store_true",
                    help="re-derive and compare against the committed map")
    ap.add_argument("--cache", help="directory of previously fetched files")
    args = ap.parse_args()
    if not (args.write or args.check):
        ap.error("one of --write / --check is required")

    rows = build(Path(args.cache) if args.cache else None)
    text = render(rows)
    print(f"AdvBench near-duplicate clustering — word-{SHINGLE_K}-gram Jaccard, "
          f"single linkage, seed {SEED}")
    summarize(rows)

    if args.write:
        OUT.write_text(text)
        print(f"wrote {OUT.relative_to(FREEZE.parent.parent.parent)} "
              f"sha256 {hashlib.sha256(text.encode()).hexdigest()}")
        return 0

    if not OUT.exists():
        sys.exit(f"{OUT} missing")
    have = OUT.read_text()
    if have != text:
        sys.exit("committed dedup_clusters.csv does not reproduce from the "
                 "pinned text under the frozen rule")
    print(f"committed map reproduces exactly · sha256 "
          f"{hashlib.sha256(have.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
