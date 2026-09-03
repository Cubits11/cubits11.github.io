#!/usr/bin/env python3
"""Re-verify the E2 pilot config-freeze from its committed artifacts.

Stdlib only. Checks structure, counts, split determinism, the sizing bar,
source-identity disjointness against the MSBench pin, and the config hash.
It does NOT fetch anything, run any guard, or read any prompt text: item
files carry only ids, row indices, and text hashes. Re-verifying the
upstream bytes against sources.json (parquet shards, AdvBench csv,
LICENSE files) requires network and, for the parquet, pyarrow; that
deeper pass is documented in FREEZE.md and is not this script.

From the W2 freeze on it also asserts the sha256 of PREREG_SELECTION.md and
of the near-duplicate cluster map, and the map's internal consistency.
Re-deriving the clusters from item text needs the pinned upstream csv and
lives in `experiments/e2/run/dedup.py --check`, not here.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BAR = 1097

# W2 freeze, 2026-09-02. Editing either file after an E2 outcome exists is a
# forbidden rescue (12-WEEK-PROGRAM.md §14); editing it at all fails here.
PREREG_SHA = "75c4b7953c6b0d1cfe8436379bcf0d4062acaf47068b264803e8a2892c07035a"
DEDUP_SHA = "b8f75976fc94b7519476b4541e8ab865f49f14b009e5e430b3c0eaf6e954ae17"
DEDUP_THETAS = ("c50", "c60", "c70")
DEDUP_PRIMARY = "c60"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = "ok   " if ok else "FAIL "
    print(f"{tag} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def read_items(name: str) -> list[dict]:
    with open(HERE / name, newline="") as fh:
        return list(csv.DictReader(fh))


def sha256_of(name: str) -> str:
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def check_prereg(harmful: list[dict], n_benign_eval: int) -> None:
    """W2: the preregistration and the near-duplicate map are frozen."""
    for name, want in (("PREREG_SELECTION.md", PREREG_SHA),
                       ("dedup_clusters.csv", DEDUP_SHA)):
        present = (HERE / name).exists()
        check(f"{name} present", present)
        if present:
            check(f"{name} sha256 unchanged since the W2 freeze",
                  sha256_of(name) == want, sha256_of(name)[:16])

    if not (HERE / "dedup_clusters.csv").exists():
        return
    clusters = read_items("dedup_clusters.csv")
    h_ids = [r["id"] for r in harmful]
    check("dedup map covers the harmful list exactly, in order",
          [r["id"] for r in clusters] == h_ids, f"{len(clusters)} rows")

    ids = set(h_ids)
    for tag in DEDUP_THETAS:
        labels = {r[tag] for r in clusters}
        reps = {r["id"] for r in clusters if r[tag + "_rep"] == "1"}
        ok = (labels <= ids and labels == reps
              and all(r[tag] in ids for r in clusters))
        check(f"dedup {tag}: one representative per cluster, labels are member ids",
              ok, f"{len(labels)} clusters")

    n_primary = len({r[DEDUP_PRIMARY] for r in clusters})
    check(f"dedup at the primary threshold keeps n >= {BAR}",
          n_primary + n_benign_eval >= BAR,
          f"{n_primary} + {n_benign_eval} = {n_primary + n_benign_eval}")
    counts = [len({r[t] for r in clusters}) for t in DEDUP_THETAS]
    check("dedup cluster counts increase with the threshold",
          counts == sorted(counts) and len(set(counts)) == len(counts),
          " < ".join(str(c) for c in counts))


def main() -> int:
    sources = json.loads((HERE / "sources.json").read_text())

    stated = sources["config_hash"]
    probe = dict(sources, config_hash="")
    canon = json.dumps(probe, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False)
    check("config_hash matches canonical content",
          hashlib.sha256(canon.encode()).hexdigest() == stated, stated[:16])

    harmful = read_items("items_harmful.csv")
    cal = read_items("items_benign_calibration.csv")
    ev = read_items("items_benign_evaluation.csv")
    check("harmful count", len(harmful) == sources["harmful"]["n"],
          f"{len(harmful)}")
    check("calibration count", len(cal) == sources["benign"]["calibration_n"],
          f"{len(cal)}")
    check("evaluation count", len(ev) == sources["benign"]["evaluation_n"],
          f"{len(ev)}")

    cal_ids = {r["id"] for r in cal}
    ev_ids = {r["id"] for r in ev}
    check("calibration and evaluation are disjoint", not (cal_ids & ev_ids))

    seed = sources["seed"]
    pool = sorted(cal_ids | ev_ids,
                  key=lambda i: hashlib.sha256(
                      f"{seed}:split:{i}".encode()).hexdigest())
    check("split reproduces from the seed",
          set(pool[:len(cal_ids)]) == cal_ids and set(pool[len(cal_ids):]) == ev_ids)

    n_shared = len(harmful) + len(ev)
    check(f"sizing bar: n_harmful + n_benign_eval >= {BAR}",
          n_shared >= BAR, f"{len(harmful)} + {len(ev)} = {n_shared}")

    ms_ids = set(json.loads((HERE / "msbench_item_ids.json").read_text()))
    ours = {r["id"] for r in harmful} | cal_ids | ev_ids
    check("id lists disjoint from the MSBench pin",
          not (ours & ms_ids), f"msbench ids: {len(ms_ids)}")
    check("sources are not HarmBench or XSTest",
          all(s not in json.dumps(
              [sources["harmful"]["source"], sources["benign"]["source"]])
              for s in ("HarmBench", "XSTest")))

    dup = len(ours) != len(harmful) + len(cal) + len(ev)
    check("no duplicate ids across lists", not dup)

    check_prereg(harmful, len(ev))

    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Config-freeze verified: counts, split determinism, sizing bar, "
          "disjointness, config hash, the W2 preregistration sha and the "
          "near-duplicate map all hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
