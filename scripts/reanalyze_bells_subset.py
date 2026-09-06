#!/usr/bin/env python3
"""Reproduce MC-002 — the missing column, computed on public data.

BELLS's 2025 misuse-detection evaluation ("The bitter lesson of misuse
detection", arXiv 2507.06282) released a per-item subset: 170 prompts,
each carrying eleven systems' binary verdicts as columns. This is a
BELLS-specific public per-item outcome substrate from which joint stack
statistics are directly computable. The census later recorded a distinct
full-cohort outcome release; this script does not make an exclusivity claim.
It computes the BELLS facts, and claim MC-002 binds the result.

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
  * the complete 2**5 exclusive miss partition is asserted too. It carries
    counts only — never the upstream item identities — and retains both
    observed-zero and structurally impossible cells;
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

import identification
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


def exclusive_miss_cells(decisions: dict[str, list[bool]],
                         positive: list[bool]) -> dict[str, int]:
    """Return every exclusive miss cell in SPECIALIZED order.

    A key's left-to-right characters align with SPECIALIZED; ``1`` means the
    corresponding guard missed the positive item. Keeping all 2**K keys is
    intentional: an omitted zero would make structural absence
    indistinguishable from an observed zero in the public grid.

    This only preserves the raw partition. Union, all-miss, and every other
    joint statistic still come from mjgd_reference's one canonical reducer.
    """
    width = len(SPECIALIZED)
    cells = {format(mask, f"0{width}b"): 0 for mask in range(1 << width)}
    for index, is_positive in enumerate(positive):
        if not is_positive:
            continue
        pattern = "".join(
            "0" if decisions[guard][index] else "1"
            for guard in SPECIALIZED
        )
        cells[pattern] += 1
    return cells


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
    miss_cells = exclusive_miss_cells(decisions, harmful)

    # The benign stratum goes through the same kernel as the harmful one.
    # It previously carried its own any()-sum for the union and its own
    # per-guard sums below: a second joint calculator inside the file that
    # produces the published numbers. Two calculators agreeing today is not
    # a property anything checks, and the burden side is where the strictly
    # positive floor lives.
    benign_rows = [r for r in rows if r["harm_level"] == "benign"]
    benign_patterns: dict[int, int] = {}
    for row in benign_rows:
        mask = 0
        for bit, system in enumerate(SPECIALIZED):
            if row[system].strip() == "1":
                mask |= 1 << bit
        benign_patterns[mask] = benign_patterns.get(mask, 0) + 1
    benign = mjgd_reference.joint_disclosure_from_patterns(
        benign_patterns, SPECIALIZED) if benign_patterns else None
    benign_union = benign["union_detection"] if benign else 0

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
    borderline = sum(1 for row in rows if row["harm_level"] == "borderline")
    if "n_borderline" in expected:
        if borderline == expected["n_borderline"]:
            ok(f"borderline stratum: {borderline} (as claimed — named, not "
               f"folded into either denominator)")
        else:
            fail(f"borderline stratum: computed {borderline}, claim says "
                 f"{expected['n_borderline']}")
    # Leave-one-out is emitted by the same joint kernel as the harmful union.
    loo = {row["guard"]: row for row in d["leave_one_out"]}
    for guard, want in expected.get("leave_one_out_union", {}).items():
        got = loo[guard]["union_without"]
        if got == want:
            ok(f"leave-one-out without {guard}: {got}/{d['denominator']} "
               f"(unique contribution "
               f"{loo[guard]['unique_contribution']}, "
               f"removal-relative — not a residual)")
        else:
            fail(f"leave-one-out without {guard}: computed {got}, claim says "
                 f"{want}")
    for guard, want in expected.get("per_guard_benign_flags", {}).items():
        got = benign["per_guard"][guard] if benign else 0
        if got == want:
            ok(f"benign flags {guard}: {got}/{len(benign_rows)} (as claimed)")
        else:
            fail(f"benign flags {guard}: computed {got}, claim says {want}")
    for guard, want in expected["per_guard_catches"].items():
        got = d["per_guard"].get(guard)
        if got == want:
            ok(f"per-guard {guard}: {got}/{d['denominator']} (as claimed)")
        else:
            fail(f"per-guard {guard}: computed {got}, claim says {want}")

    # The exclusive miss table uses a deliberately named representation
    # (1 = miss, characters follow SPECIALIZED), while mjgd_reference uses
    # a compact catch-mask internally. Assert their common facts explicitly
    # so a reversed or reinterpreted cell order cannot look plausible.
    registered_cells = expected.get("exclusive_cells")
    expected_keys = set(miss_cells)
    if not isinstance(registered_cells, dict):
        fail("exclusive miss cells: MC-002 expected.exclusive_cells is missing")
    elif set(registered_cells) != expected_keys:
        missing = sorted(expected_keys - set(registered_cells))
        extra = sorted(set(registered_cells) - expected_keys)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unknown " + ", ".join(extra))
        fail("exclusive miss cells: expected every 5-bit cell (" + "; ".join(detail) + ")")
    else:
        for pattern in sorted(expected_keys):
            got, want = miss_cells[pattern], registered_cells[pattern]
            if got != want:
                fail(f"exclusive miss cell {pattern}: computed {got}, claim says {want}")
        if not failures:
            ok("exclusive miss cells: all 32 cells match the registered partition")

    if sum(miss_cells.values()) != d["denominator"]:
        fail("exclusive miss cells: cells do not sum to the MJGD denominator")
    if miss_cells["1" * len(SPECIALIZED)] != d["all_miss"]:
        fail("exclusive miss cells: all-miss cell disagrees with the MJGD reducer")
    for position, guard in enumerate(SPECIALIZED):
        catches_from_cells = sum(
            count for pattern, count in miss_cells.items() if pattern[position] == "0")
        if catches_from_cells != d["per_guard"][guard]:
            fail(f"exclusive miss cells: {guard} catch marginal disagrees with the MJGD reducer")
    always_miss = [
        (position, guard) for position, guard in enumerate(SPECIALIZED)
        if d["per_guard"][guard] == 0
    ]
    for position, guard in always_miss:
        structural = [pattern for pattern in miss_cells if pattern[position] == "0"]
        if any(miss_cells[pattern] for pattern in structural):
            fail(f"exclusive miss cells: {guard} catches zero but a structural cell is nonzero")
        else:
            ok(f"exclusive miss cells: {guard} catches 0/{d['denominator']}; "
               f"{len(structural)} cells are structurally empty")

    n = d["denominator"]
    # Same single implementation the page and the validator use.
    product = identification.independence_plugin(
        [(n - d["per_guard"][guard]) / n for guard in SPECIALIZED])
    observed = d["all_miss"] / n
    print("\nderived from the hash-verified source file; compared with the")
    print("registered expected counts above:")
    print(f"  recomputed static all-miss: {d['all_miss']}/{n} = {observed:.1%}")
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
