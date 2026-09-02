#!/usr/bin/env python3
"""TRY-C — apply the Missing Column disclosure test to an evaluation you know.

The census (census.yaml) classifies each public guardrail evaluation under
frozen criteria v1 with a handful of yes/no/unstated fields. This script asks
you those same questions about an evaluation you can read, classifies your
answers with the same predicates scripts/verify_census.py uses for the census
counts, prints a candidate row, and hands you the intake link. It never reads
the source for you: your answers are your observations; the classification is
derived from them; the candidate row is a proposal until reviewed.

    python3 scripts/try_audit.py                                   # interactive, ~15 minutes with the source open
    python3 scripts/try_audit.py --answers fixtures/try/audit-example.json   # a worked example, no prompts
    python3 scripts/try_audit.py --answers my-eval.json --yaml     # print the candidate row as YAML for an issue

Standard library only. Nothing is written to disk. Exit 0 with a final line
beginning AUDIT; exit 1 with FAIL on a malformed answer.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = "https://github.com/Cubits11/cubits11.github.io/issues/new"

TRI = ("yes", "no", "mixed", "unstated")

# (key, prompt, allowed answers) — the frozen inclusion criteria first, then the
# classification-bearing fields the census records for every examined row.
QUESTIONS: list[tuple[str, str, tuple[str, ...] | None]] = [
    ("id", "Short id for the evaluation (letters, digits, hyphens; e.g. guardbench-2024)", None),
    ("title", "Title of the artifact", None),
    ("url", "Public URL of the artifact", None),
    ("public_access", "Is it publicly accessible without payment at a stable URL?", ("yes", "no")),
    ("n_systems", "How many distinct, separately attributable guardrail mechanisms does it evaluate? (integer)", None),
    ("shared_item_universe", "Are the mechanisms evaluated on the same item set (per task)?", TRI),
    ("per_mechanism_results", "Does it report separately attributable per-mechanism quantitative results?", ("yes", "no")),
    ("domain", "Is its domain safety/harm detection, jailbreak or injection detection, moderation, policy enforcement, or PII detection around LLMs?", ("yes", "no")),
    ("same_event_definition", "Do all compared mechanisms share one ground-truth event definition (which items count as positives)?", TRI),
    ("thresholds_comparable", "Does the source document that the mechanisms are compared at matched operating thresholds?", TRI),
    ("all_systems_saw_all_items", "Did every mechanism see every item (no gating, no routing, no early stop)?", TRI),
    ("joint_printed", "Does it PRINT a joint statistic over two or more mechanisms (union, all-miss, overlap, residual coverage, measured ensemble)?", ("none", "partial_stack", "full_stack")),
    ("items_released", "Does it RELEASE aligned per-item outcomes for two or more mechanisms on shared items, so a joint statistic is directly computable?", ("yes", "no")),
    ("public_before_freeze", "Was it public on or before 2026-08-27 (the census freeze date)?", ("yes", "no", "unstated")),
]


def ask(key: str, prompt: str, allowed: tuple[str, ...] | None) -> str:
    hint = f" [{'/'.join(allowed)}]" if allowed else ""
    while True:
        raw = input(f"  {prompt}{hint}\n  > ").strip()
        if allowed is None and raw:
            return raw
        if allowed and raw.lower() in allowed:
            return raw.lower()
        print("    please answer one of: " + (", ".join(allowed) if allowed else "a non-empty value"))


def classify(a: dict) -> dict:
    """The census's own predicates (verify_census.compute_counts), applied to one candidate."""
    failed = [k for k in ("public_access", "per_mechanism_results", "domain") if a[k] != "yes"]
    try:
        n = int(a["n_systems"])
    except (TypeError, ValueError):
        raise ValueError("n_systems must be an integer")
    if n < 2:
        failed.append("multi_mechanism")
    if a["shared_item_universe"] == "no":
        failed.append("shared_item_universe")
    if failed:
        return {"eligible": False, "failed": failed, "classification": "INELIGIBLE",
                "joint_scope": "none", "rung": None}
    if a["same_event_definition"] == "no":
        cls, scope = "NOT_COMPARABLE", "none"
    elif a["joint_printed"] in ("partial_stack", "full_stack") or a["items_released"] == "yes":
        cls = "PRESENT"
        scope = ("printed_" + a["joint_printed"]) if a["joint_printed"] != "none" else "computable_via_item_release"
    else:
        cls, scope = "ABSENT", "none"
    shared = a["shared_item_universe"] == "yes" and a["same_event_definition"] == "yes"
    tnc = shared and a["thresholds_comparable"] in ("yes", "unstated")
    doc = tnc and a["thresholds_comparable"] == "yes" and a["all_systems_saw_all_items"] == "yes"
    rung = "documented_full_exposure" if doc else "threshold_not_contradicted" if tnc else "shared_basis" if shared else "below_shared_basis"
    additional = ["computable_via_item_release"] if (a["joint_printed"] != "none" and a["items_released"] == "yes") else []
    return {"eligible": True, "failed": [], "classification": cls, "joint_scope": scope,
            "joint_scope_additional": additional, "rung": rung}


def candidate_yaml(a: dict, c: dict) -> str:
    def tri(k: str) -> str:
        return f"{{value: {a[k]}, evidence: \"<quote the passage or table that shows this>\"}}"
    lines = [
        f"- id: {a['id']}",
        f"  title: \"{a['title']}\"",
        f"  primary_url: \"{a['url']}\"",
        f"  n_systems: {int(a['n_systems'])}",
        f"  same_items_for_all_systems: {tri('shared_item_universe')}",
        f"  same_event_definition: {tri('same_event_definition')}",
        f"  thresholds_comparable: {tri('thresholds_comparable')}",
        f"  all_systems_saw_all_items: {tri('all_systems_saw_all_items')}",
        f"  classification: {c['classification']}",
        f"  joint_scope: {c['joint_scope']}",
    ]
    if c.get("joint_scope_additional"):
        lines.append(f"  joint_scope_additional: [{', '.join(c['joint_scope_additional'])}]")
    lines.append("  classification_reason: \"<one sentence: what the source prints or releases, and what it does not>\"")
    lines.append(f"  public_before_freeze: {a['public_before_freeze']}   # candidate field; the reviewer dates it from the source")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--answers", type=Path, help="JSON file of answers keyed by question id (skips the prompts)")
    ap.add_argument("--yaml", action="store_true", help="print the candidate row as YAML ready to paste into an issue")
    args = ap.parse_args()

    if args.answers:
        try:
            a = json.loads(args.answers.read_text())
        except (OSError, ValueError) as exc:
            print(f"FAIL  could not read answers: {exc}")
            return 1
        missing = [k for k, _, _ in QUESTIONS if k not in a]
        if missing:
            print(f"FAIL  answers file lacks: {', '.join(missing)}")
            return 1
        for k, _, allowed in QUESTIONS:
            if allowed and str(a[k]).lower() not in allowed:
                print(f"FAIL  {k} must be one of {allowed}, got {a[k]!r}")
                return 1
            a[k] = str(a[k]).lower() if allowed else a[k]
        worked = args.answers.resolve() == (ROOT / "fixtures" / "try" / "audit-example.json").resolve()
    else:
        print("The Missing Column disclosure test — TRY-C. Open the evaluation; answer from what it prints or releases.")
        a = {k: ask(k, p, allowed) for k, p, allowed in QUESTIONS}
        worked = False
    try:
        c = classify(a)
    except ValueError as exc:
        print(f"FAIL  {exc}")
        return 1

    print()
    print(f"  artifact        {a['id']} — {a['title']}")
    if not c["eligible"]:
        print(f"  eligibility     INELIGIBLE under criteria v1 — failed: {', '.join(c['failed'])}")
        print("  meaning         not a census row; an ineligible artifact is never counted as 'does not report'")
    else:
        print("  eligibility     meets criteria v1 on your answers")
        print(f"  classification  {c['classification']}  joint_scope={c['joint_scope']}"
              + (f"  additional={c['joint_scope_additional']}" if c.get("joint_scope_additional") else ""))
        print(f"  ladder rung     {c['rung']}  (shared_basis → threshold_not_contradicted → documented_full_exposure)")
        if c["classification"] == "ABSENT":
            print("  meaning         per-system results, no joint statistic, no per-item release: the column is missing here")
        elif c["classification"] == "PRESENT":
            print("  meaning         a joint-evidence artifact exists: the census would count this row as PRESENT")
        else:
            print("  meaning         different ground-truth events: a joint statistic over these marginals is ill-defined")
    print("  status          your answers are your observations; this classification is derived; the row is a proposal")
    if args.yaml or args.answers:
        print()
        print("  candidate row (paste into the intake issue, then fill the <…> evidence fields from the source):")
        for ln in candidate_yaml(a, c).splitlines():
            print("    " + ln)
    kind = ("I found a benchmark that already reports the stack (a row the census should have as PRESENT)"
            if c.get("classification") == "PRESENT" else "I found a benchmark the census missed (a candidate row)")
    url = ISSUES + "?" + urllib.parse.urlencode({"template": "counterexample.yml",
                                                 "title": f"candidate row: {a['id']} — {c['classification']}",
                                                 "kind": kind, "experiment": "TRY-C"})
    print()
    print(f"  report          {url}")
    suffix = "  (worked example, not a census row)" if worked else ""
    print(f"AUDIT  TRY-C  {a['id']}  {c['classification']}  {c['joint_scope']}  rung={c['rung']}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
