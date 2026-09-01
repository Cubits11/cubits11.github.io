#!/usr/bin/env python3
"""Re-verify the E2 pilot config-freeze from its committed artifacts.

Stdlib only. Checks structure, counts, split determinism, the sizing bar,
source-identity disjointness against the MSBench pin, and the config hash.
It does NOT fetch anything, run any guard, or read any prompt text: item
files carry only ids, row indices, and text hashes. Re-verifying the
upstream bytes against sources.json (parquet shards, AdvBench csv,
LICENSE files) requires network and, for the parquet, pyarrow; that
deeper pass is documented in FREEZE.md and is not this script.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BAR = 1097
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = "ok   " if ok else "FAIL "
    print(f"{tag} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def read_items(name: str) -> list[dict]:
    with open(HERE / name, newline="") as fh:
        return list(csv.DictReader(fh))


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

    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("Config-freeze verified: counts, split determinism, sizing bar, "
          "disjointness, and config hash all hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
