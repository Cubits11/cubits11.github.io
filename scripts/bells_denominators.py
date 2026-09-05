#!/usr/bin/env python3
"""BELLS denominator / provenance table — regenerated from pinned upstream bytes.

Answers one question a stranger should be able to ask of every published BELLS
number: what exact `n` sits underneath it, from which artifact, under which
selection rule. It downloads nothing it does not hash-assert, redistributes
nothing (the upstream repository declares no licence), and computes only
counts. Companion to `scripts/reanalyze_bells_subset.py` (MC-002), which
owns the joint arithmetic on the 170-row file; this script owns the lineage
of the denominators around that file.

Every upstream artifact is pinned by (commit, path, sha256). A changed byte
fails loudly. Nothing here is a claim; the packet that cites this output is
`ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md`.

Run:  python3 scripts/bells_denominators.py                 # downloads (~2 MB)
      python3 scripts/bells_denominators.py --cache DIR     # reads DIR/<sha7>_<file>
      python3 scripts/bells_denominators.py --json          # machine-readable

Exit 0 only if every pinned file hashes as recorded.
"""

import argparse
import collections
import csv
import hashlib
import io
import json
import pathlib
import sys
import urllib.request

REPO = "CentreSecuriteIA/bells_leaderboard"
RAW = f"https://raw.githubusercontent.com/{REPO}"

# (commit, path, sha256, upstream commit date, upstream commit subject)
PINS = [
    ("0fc3d6d3", "data/non_adversarial_prompts.csv",
     "b3d5553510f0" , "2025-02-18", "[WIP] v0"),
    ("d6ebd0e5", "data/non_adversarial_prompts.csv",
     "a8d2e4ea69b3", "2025-02-18", "Add frontier models to playground"),
    ("077555d9", "data/non_adversarial_prompts.csv",
     "7fa0fbf5885e", "2025-02-19", "smaller dataset for playground"),
    ("00b42bfd", "data/non_adversarial_prompts.csv",
     "52ca9ab8eb62", "2025-02-21", "New data, new results interpretation"),
    ("ffe88ccb", "data/non_adversarial_prompts.csv",
     "d93f9fe1d1a1", "2025-02-23", "new playground data"),
    ("b20aeed5", "data/non_adversarial_prompts.csv",
     "791dd4b0a168", "2025-03-22", "new results"),
    ("507566c5", "data/non_adversarial_prompts.csv",
     "791dd4b0a168", "2025-07-08", "css for faq (default-branch head)"),
    ("507566c5", "data/adversarial_prompts.csv",
     "32fe8663621a", "2025-07-08", "css for faq (default-branch head)"),
    ("0fc3d6d3", "data/safeguard_evaluation_results.csv",
     "06eeb0251e5b", "2025-02-18", "[WIP] v0"),
    ("00b42bfd", "data/safeguard_evaluation_results.csv",
     "d906e69c1fd8", "2025-02-21", "New data, new results interpretation"),
    ("dde32a3d", "data/safeguard_evaluation_results.csv",
     "6c133bea489b", "2025-02-23", "final results and associated interpretation points"),
    ("507566c5", "data/safeguard_evaluation_results.csv",
     "6935166c5663", "2025-07-08", "css for faq (default-branch head)"),
    ("507566c5", "data/safeguard_evaluation_results_llama.csv",
     "db321a9d4eee", "2025-07-08", "css for faq (default-branch head)"),
    ("507566c5", "data/metacognitive_results.csv",
     "66a9f09c60d3", "2025-07-08", "css for faq (default-branch head)"),
]
# Full 64-hex digests for the two files other repository artifacts already pin.
FULL_SHA = {
    "791dd4b0a168": "791dd4b0a168f2eb5831b308083a492e83200a9fa82585643c739023b03f57c3",
    "6935166c5663": "6935166c5663204fc23feb9385d1801cd69436d7bb95df5e92cbb77bdfdab84c",
}

SPECIALIZED = ["lakera_guard", "prompt_guard", "langkit", "nemo", "llm_guard"]
STRATA = ("harmful", "benign", "borderline")
AGG_COLS = ["benign_non-adversarial", "borderline_non-adversarial",
            "harmful_non-adversarial", "benign_jailbreaks",
            "borderline_jailbreaks", "harmful_jailbreaks"]

failures: list[str] = []


def fetch(commit: str, path: str, cache: pathlib.Path | None) -> bytes:
    name = f"{commit}_{pathlib.Path(path).name}"
    if cache is not None and (cache / name).exists():
        return (cache / name).read_bytes()
    req = urllib.request.Request(f"{RAW}/{commit}/{path}",
                                 headers={"User-Agent": "cubits11-bells-denominators"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / name).write_bytes(raw)
    return raw


def rows_of(raw: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def profile_items(rows: list[dict]) -> dict:
    cols = list(rows[0].keys())
    const = {c: rows[0][c].strip() for c in cols
             if len({r[c].strip() for r in rows}) == 1}
    by = collections.Counter(r["harm_level"] for r in rows)
    harm_cats = collections.Counter(r["category"] for r in rows if r["harm_level"] == "harmful")
    verdict_cols = [c for c in cols if c not in ("question", "harm_level", "source", "category",
                                                 "jailbreak_prompt", "jailbreak_type", "jailbreak_source")]
    return {"n": len(rows), "by_harm_level": {s: by.get(s, 0) for s in STRATA},
            "harmful_categories": len(harm_cats), "verdict_columns": verdict_cols,
            "constant_columns": const}


def smallest_common_denominator(values: list[str], maxd: int = 6000) -> int | None:
    """Smallest d such that every non-zero value times d is an integer (1e-7).

    A divisor-consistent set of fractions across eleven independent rows is
    strong evidence for a common denominator, but the true denominator could
    be any integer multiple; the packet says so.
    """
    for d in range(1, maxd + 1):
        if all(abs(float(v) * d - round(float(v) * d)) < 1e-7 for v in values if float(v) != 0):
            return d
    return None


def profile_aggregate(rows: list[dict]) -> dict:
    out = {"n_safeguards": len(rows), "safeguards": [r["safeguard"] for r in rows], "denominators": {}}
    for c in AGG_COLS:
        if c not in rows[0]:
            continue
        out["denominators"][c] = smallest_common_denominator([r[c] for r in rows])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cache = pathlib.Path(args.cache) if args.cache else None

    data: dict[tuple[str, str], list[dict]] = {}
    report = {"pins": [], "items": {}, "aggregates": {}}
    for commit, path, sha12, date, subject in PINS:
        raw = fetch(commit, path, cache)
        digest = hashlib.sha256(raw).hexdigest()
        pinned_ok = digest.startswith(sha12) and (
            sha12 not in FULL_SHA or digest == FULL_SHA[sha12])
        report["pins"].append({"commit": commit, "path": path, "sha256": digest,
                               "pinned": pinned_ok, "date": date, "subject": subject})
        if not pinned_ok:
            failures.append(f"{commit} {path}: sha256 {digest[:12]} != pinned {sha12}")
            continue
        rows = rows_of(raw)
        data[(commit, path)] = rows
        key = f"{commit}:{pathlib.Path(path).name}"
        if path.endswith("prompts.csv"):
            report["items"][key] = profile_items(rows)
        elif "safeguard_evaluation" in path:
            report["aggregates"][key] = profile_aggregate(rows)
        else:  # metacognitive
            prompts = {r["prompt"] for r in rows}
            report["items"][key] = {
                "n_rows": len(rows), "unique_prompts": len(prompts),
                "models": sorted({r["model"] for r in rows}),
                "non_adversarial_unique_prompts": len({r["prompt"] for r in rows
                                                       if r["dataset"] == "non_adversarial_prompts"})}

    # Containment and verdict agreement of the head 170-row file against its ancestors.
    head = data.get(("507566c5", "data/non_adversarial_prompts.csv"))
    if head:
        H = {r["question"]: r for r in head}
        lineage = {}
        for commit in ("0fc3d6d3", "d6ebd0e5", "077555d9", "00b42bfd", "ffe88ccb"):
            anc = data.get((commit, "data/non_adversarial_prompts.csv"))
            if not anc:
                continue
            A = {r["question"]: r for r in anc}
            shared = [q for q in H if q in A]
            harmful = [q for q in shared if H[q]["harm_level"] == "harmful"]
            agree = {g: sum(H[q][g].strip() == A[q][g].strip() for q in harmful)
                     for g in SPECIALIZED}
            lineage[commit] = {"head_questions_present": len(shared),
                               "shared_harmful": len(harmful),
                               "harmful_verdict_agreement": agree}
        report["head_lineage"] = lineage

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("BELLS denominators — pinned upstream artifacts (counts only)\n")
        print("| commit | file | sha256[:12] | pinned | n | harmful | benign | borderline | harmful cats | constant columns |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for p in report["pins"]:
            key = f"{p['commit']}:{pathlib.Path(p['path']).name}"
            it = report["items"].get(key)
            if it and "by_harm_level" in it:
                b = it["by_harm_level"]
                const = ", ".join(f"{k}={v}" for k, v in it["constant_columns"].items()) or "none"
                print(f"| {p['commit']} ({p['date']}) | {pathlib.Path(p['path']).name} | {p['sha256'][:12]} | "
                      f"{'yes' if p['pinned'] else 'NO'} | {it['n']} | {b['harmful']} | {b['benign']} | "
                      f"{b['borderline']} | {it['harmful_categories']} | {const} |")
        print("\nAggregate files — smallest common denominator across all safeguard rows (1e-7):\n")
        print("| commit | file | safeguards | " + " | ".join(AGG_COLS) + " |")
        print("|---|---|---|" + "---|" * len(AGG_COLS))
        for key, ag in report["aggregates"].items():
            commit, name = key.split(":")
            cells = [str(ag["denominators"].get(c, "—")) for c in AGG_COLS]
            print(f"| {commit} | {name} | {ag['n_safeguards']} | " + " | ".join(cells) + " |")
        meta = report["items"].get("507566c5:metacognitive_results.csv")
        if meta:
            print(f"\nmetacognitive_results.csv @ 507566c5: {meta['n_rows']} rows, "
                  f"{meta['unique_prompts']} unique prompts, {meta['non_adversarial_unique_prompts']} "
                  f"non-adversarial; models {meta['models']}")
        if head:
            print("\nHead 170-row file against its ancestors (harmful stratum verdict agreement, "
                  "per specialized column, over shared questions):")
            for commit, ln in report["head_lineage"].items():
                ag = ln["harmful_verdict_agreement"]
                print(f"  {commit}: {ln['head_questions_present']}/170 head questions present; "
                      f"shared harmful {ln['shared_harmful']}; agreement " +
                      ", ".join(f"{g}={ag[g]}" for g in SPECIALIZED))
    # In --json mode the only stdout is the JSON document; status goes to stderr
    # so the output stays parseable.
    out = sys.stderr if args.json else sys.stdout
    if not args.json:
        print()
    if failures:
        for f in failures:
            print("FAIL ", f, file=out)
        print(f"{len(failures)} pin(s) failed.", file=out)
        return 1
    print("ok    every pinned upstream artifact hashes as recorded", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
