#!/usr/bin/env python3
"""Reproduce MC-002 — the missing column, computed on public data.

BELLS's 2025 misuse-detection evaluation ("The bitter lesson of misuse
detection", arXiv 2507.06282) released a per-item subset: 170 prompts,
each carrying eleven systems' binary verdicts as columns. That release is
the only per-item outcome substrate found by the Missing Column Census's
bounded 2026-08-27 search from which joint stack statistics are directly
computable; this is not a claim of global exclusivity. This script computes
them, and claim MC-002 binds the result.

Discipline:
  * the CSV is pinned by commit AND content hash — the numbers are about
    exactly these bytes, at
    CentreSecuriteIA/bells_leaderboard @ 507566c5, and a changed file
    fails loudly instead of silently recomputing;
  * the arithmetic is scripts/mjgd_reference.py — the same tested
    implementation the disclosure page offers to benchmark authors;
  * expected counts are read from MC-002's `expected` block in
    claims.yaml and asserted, so the proposition's numbers and the
    executed computation cannot silently diverge (the CC-001 pattern);
  * the CSV is downloaded to a temp path and not committed: the
    upstream repository declares no license, so this record cites and
    verifies the file rather than redistributing it.

Run:  python3 scripts/reanalyze_bells_subset.py            # downloads
      python3 scripts/reanalyze_bells_subset.py --csv F    # offline
"""

import csv
import hashlib
import io
import pathlib
import sys
import urllib.request

import yaml

import mjgd_reference

ROOT = pathlib.Path(__file__).resolve().parent.parent

BOUND_COMMIT = "507566c5a4606c8e3dec0bd59a5c5fde62594951"
CSV_URL = ("https://raw.githubusercontent.com/CentreSecuriteIA/"
           f"bells_leaderboard/{BOUND_COMMIT}/data/non_adversarial_prompts.csv")
CSV_SHA256 = "791dd4b0a168f2eb5831b308083a492e83200a9fa82585643c739023b03f57c3"

SPECIALIZED = ["lakera_guard", "prompt_guard", "langkit", "nemo", "llm_guard"]

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def load_csv() -> list:
    if "--csv" in sys.argv:
        raw = pathlib.Path(sys.argv[sys.argv.index("--csv") + 1]).read_bytes()
    else:
        req = urllib.request.Request(CSV_URL, headers={"User-Agent": "cubits11-mc002-repro"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CSV_SHA256:
        fail(f"CSV sha256 {digest[:16]}… != recorded {CSV_SHA256[:16]}… — "
             f"the bound artifact changed; MC-002 must be re-reviewed, "
             f"not silently recomputed")
        return []
    ok(f"CSV verified: sha256 matches the bound artifact ({len(raw)} bytes)")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def main() -> int:
    rows = load_csv()
    if not rows:
        print("1 check(s) failed.")
        return 1
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text())
    mc = next((c for c in registry["claims"] if c["id"] == "MC-002"), None)
    if mc is None:
        fail("MC-002 not found in claims.yaml")
        print("1 check(s) failed.")
        return 1
    expected = mc["expected"]

    harmful = [r["harm_level"] == "harmful" for r in rows]
    decisions = {s: [r[s].strip() == "1" for r in rows] for s in SPECIALIZED}
    d = mjgd_reference.joint_disclosure(decisions, harmful)

    benign_rows = [r for r in rows if r["harm_level"] == "benign"]
    benign_union = sum(1 for r in benign_rows
                       if any(r[s].strip() == "1" for s in SPECIALIZED))

    checks = [
        ("released prompts", len(rows), expected["n_prompts"]),
        ("harmful denominator", d["denominator"], expected["n_harmful"]),
        ("union detection", d["union_detection"], expected["union_detection"]),
        ("all-miss", d["all_miss"], expected["all_miss"]),
        ("benign prompts", len(benign_rows), expected["n_benign"]),
        ("benign flagged by ≥1", benign_union, expected["benign_union_flagged"]),
    ]
    for name, got, want in checks:
        if got == want:
            ok(f"{name}: {got} (as claimed)")
        else:
            fail(f"{name}: computed {got}, claim says {want}")
    for guard, want in expected["per_guard_catches"].items():
        got = d["per_guard"].get(guard)
        if got == want:
            ok(f"per-guard {guard}: {got}/{d['denominator']} (as claimed)")
        else:
            fail(f"per-guard {guard}: computed {got}, claim says {want}")

    n = d["denominator"]
    product = 1.0
    for guard in SPECIALIZED:
        product *= (n - d["per_guard"][guard]) / n
    observed = d["all_miss"] / n
    print(f"\nderived, from the asserted counts:")
    print(f"  observed joint miss      : {d['all_miss']}/{n} = {observed:.1%}")
    print(f"  independent-miss product : {product:.1%}  "
          f"(= {product * n:.2f} prompts)")
    print(f"  ratio                    : {observed / product:.2f}×")
    print(f"  residual coverage, in column order:")
    for r in d["residual_coverage"]:
        print(f"    {r['guard']:<13} catches {r['catches_among_prior_misses']:>2} "
              f"of {r['prior_misses']:>2} prior misses")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("MC-002 reproduced: the missing column, computed from the bound "
          "public release, matches the registered claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
