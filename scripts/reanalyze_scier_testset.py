#!/usr/bin/env python3
"""Count the SciER test splits, and name the column they do not contain.

SciER (EMNLP 2024; Zhang, Chen, Pan, Caragea, Latecki, Dragut) releases an
entity and relation extraction dataset for scientific documents and reports
three supervised extractors on it — PURE, PL-Marker and HGERE — plus LLM
baselines. The dataset is released. The extractors' per-item predictions are
not.

That is the same shape this repository studies in guardrail stacks: several
detectors are scored on one shared item pool, each detector's marginal is
published, and the joint outcome — how many items *every* extractor missed —
is left unidentified. From three F1 scores alone the all-miss count is
bounded, not determined. With three id-keyed prediction files it is an
integer.

This script establishes the denominator of that missing integer. It is not a
claim about SciER's quality, not an estimate of any extractor's performance,
and not a measurement of composition: no prediction file exists to measure.
It counts released bytes so that an ask can carry a number instead of an
adjective.

Discipline, following scripts/reanalyze_bells_subset.py:
  * both splits are pinned by commit AND content hash — the counts are about
    exactly these bytes, at TUDMLab/SciER @ db347813, and a changed file
    fails loudly instead of silently recomputing;
  * the files are downloaded to a temp path and not committed — this record
    cites and verifies them rather than redistributing them;
  * expected counts are asserted inline, so a silent upstream change cannot
    pass as agreement;
  * nothing here is registered as a claim. Adding a non-guardrail row to a
    guardrail census is an owner decision, not a side effect of a script.

Run:  python3 scripts/reanalyze_scier_testset.py                # downloads
      python3 scripts/reanalyze_scier_testset.py --dir DIR      # offline
"""

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import urllib.request

BOUND_COMMIT = "db347813de379eb200e0813bbfee350d67e7c701"
BASE = ("https://raw.githubusercontent.com/TUDMLab/SciER/"
        f"{BOUND_COMMIT}/SciER/LLM")

# split -> (sha256 of the released bytes, expected counts)
SPLITS = {
    "test.jsonl": {
        "sha256": "a90aba6c52c43ff4f5762d79121ac35379bd220c6172ae2b04ca8b27043f4115",
        "sentences": 854,
        "documents": 10,
        "mentions": 2948,
        "relations": 1626,
        "entity_types": {"Method": 1890, "Task": 688, "Dataset": 370},
    },
    "test_ood.jsonl": {
        "sha256": "1db0d82a47271504af83abd5a0d5eced9735be3eca69a3a614b27625ce3ec345",
        "sentences": 580,
        "documents": 6,
        "mentions": 1295,
        "relations": 582,
        "entity_types": {"Method": 1018, "Task": 194, "Dataset": 83},
    },
}

# Reported in the SciER paper on these splits. Recorded here as the names of
# the marginals, not as values: this script does not read or reproduce any
# score, and asserts nothing about them.
REPORTED_EXTRACTORS = ("PURE", "PL-Marker", "HGERE")

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def load(name: str, local_dir: pathlib.Path | None) -> bytes:
    if local_dir is not None:
        return (local_dir / name).read_bytes()
    with urllib.request.urlopen(f"{BASE}/{name}", timeout=60) as response:
        return response.read()


def count(raw: bytes) -> dict:
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    documents = {row["doc_id"] for row in rows}
    entity_types: collections.Counter = collections.Counter()
    relation_types: collections.Counter = collections.Counter()
    mentions = 0
    for row in rows:
        for mention in row.get("ner") or []:
            mentions += 1
            entity_types[mention[1]] += 1
        for triple in row.get("rel") or []:
            relation_types[triple[1]] += 1
    return {
        "sentences": len(rows),
        "documents": len(documents),
        "mentions": mentions,
        "relations": sum(relation_types.values()),
        "entity_types": dict(entity_types),
        "relation_types": dict(relation_types),
    }


def check_split(name: str, expected: dict, local_dir: pathlib.Path | None) -> None:
    try:
        raw = load(name, local_dir)
    except Exception as exc:  # noqa: BLE001 — reported, never swallowed
        fail(f"{name}: could not be read ({type(exc).__name__}: {exc})")
        return

    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected["sha256"]:
        fail(f"{name}: sha256 {digest} != pinned {expected['sha256']} — "
             "the released bytes changed; every count below is void")
        return
    ok(f"{name}: sha256 matches the pinned bytes at {BOUND_COMMIT[:8]}")

    observed = count(raw)
    for field in ("sentences", "documents", "mentions", "relations", "entity_types"):
        if observed[field] != expected[field]:
            fail(f"{name}.{field}: {observed[field]} != expected {expected[field]}")
        else:
            ok(f"{name}.{field}: {observed[field]}")
    print(f"      relation types: {observed['relation_types']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=pathlib.Path, default=None,
                        help="read the splits from this directory instead of downloading")
    args = parser.parse_args()

    print(f"SciER test splits — TUDMLab/SciER @ {BOUND_COMMIT}")
    print()
    for name, expected in SPLITS.items():
        check_split(name, expected, args.dir)
        print()

    total = sum(split["mentions"] for split in SPLITS.values())
    print("WHAT IS IDENTIFIED")
    print(f"  {SPLITS['test.jsonl']['mentions']} entity mentions in the in-distribution test split,")
    print(f"  {SPLITS['test_ood.jsonl']['mentions']} in the out-of-distribution split, {total} together.")
    print()
    print("WHAT IS NOT IDENTIFIED")
    print(f"  Of those {total} mentions, how many were missed by all of "
          f"{', '.join(REPORTED_EXTRACTORS)} simultaneously.")
    print("  Per-extractor F1 bounds that count; it does not determine it.")
    print("  No prediction file is released, so this script cannot compute it")
    print("  and does not estimate it. The bound is not reported here either:")
    print("  reconstructing it needs the per-extractor marginals, which this")
    print("  script deliberately does not read.")
    print()
    print("  The smallest artifact that would determine it: three id-keyed")
    print("  prediction files over the released test split.")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
