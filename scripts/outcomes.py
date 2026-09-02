#!/usr/bin/env python3
"""Validate and print the qualified-outcome state and stop rule.

Separates outcomes that required someone else to do work from metrics that
only say people saw something. Prints zero as zero.

Run: python scripts/outcomes.py
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml


ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "distribution" / "outcomes.yaml"
QUALIFIED_BUCKETS = (
    "independent_reproductions",
    "source_corrections",
    "paired_outcome_releases",
    "upstream_prs",
    "human_cold_runs",
)
INTERACTION_FIELDS = ("date", "kind", "url", "summary")
ENTRY_FIELDS = ("date", "kind", "actor", "artifact", "agreed", "consequence", "claim")
TRIAL_FIELDS = ("date", "film", "viewer", "answers", "scores", "source")
TRIAL_QUESTIONS = ("fixed_changed", "real_guardrails", "one_percent")
# WORLDSPACE's frozen protocol (worldspace/manifest.yaml → cold_test) records two
# further answers verbatim; they are never scored, so they may appear only in
# `answers`, never in `scores`.
TRIAL_OPTIONAL_ANSWERS = ("prediction", "agency")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(data: object) -> dict:
    """Reject a malformed zero as eagerly as a malformed positive outcome."""
    if not isinstance(data, dict):
        raise ValueError("outcome ledger must be a mapping")
    qualified = data.get("qualified")
    if not isinstance(qualified, dict):
        raise ValueError("outcome ledger requires a qualified mapping")
    unknown = sorted(set(qualified) - set(QUALIFIED_BUCKETS))
    if unknown:
        raise ValueError("unknown qualified outcome bucket(s): " + ", ".join(unknown))
    for bucket in QUALIFIED_BUCKETS:
        if bucket not in qualified:
            raise ValueError(f"qualified outcome bucket is missing: {bucket}")
        if not isinstance(qualified[bucket], list):
            raise ValueError(f"qualified outcome bucket must be a list: {bucket}")
        for index, entry in enumerate(qualified[bucket]):
            where = f"qualified.{bucket}[{index}]"
            if not isinstance(entry, dict) or set(entry) != set(ENTRY_FIELDS):
                raise ValueError(f"{where} must contain exactly " + ", ".join(ENTRY_FIELDS))
            if not DATE.match(str(entry["date"])):
                raise ValueError(f"{where}.date must be YYYY-MM-DD")
            if not isinstance(entry["agreed"], bool):
                raise ValueError(f"{where}.agreed must be true or false — a disagreement is a first-class entry")
            if not str(entry["artifact"]).startswith(("https://", "http://")):
                raise ValueError(f"{where}.artifact must be an HTTP(S) URL a reader can open")
            for field in ("kind", "actor", "consequence", "claim"):
                if not isinstance(entry[field], str) or not entry[field].strip():
                    raise ValueError(f"{where}.{field} must be a non-empty string")

    diagnostics = data.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError("outcome ledger requires a diagnostics mapping")
    interactions = diagnostics.get("technical_interactions")
    if (isinstance(interactions, bool) or not isinstance(interactions, int)
            or interactions < 0):
        raise ValueError("technical_interactions must be a non-negative integer")
    log = diagnostics.get("technical_interaction_log")
    if not isinstance(log, list):
        raise ValueError("technical_interaction_log must be a list")
    if len(log) != interactions:
        raise ValueError("technical_interactions must equal the interaction-log length")
    for index, item in enumerate(log):
        if not isinstance(item, dict) or set(item) != set(INTERACTION_FIELDS):
            raise ValueError(
                f"technical_interaction_log[{index}] must contain exactly "
                + ", ".join(INTERACTION_FIELDS)
            )
        for field in INTERACTION_FIELDS:
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(
                    f"technical_interaction_log[{index}].{field} must be a non-empty string"
                )
        if not item["url"].startswith(("https://", "http://")):
            raise ValueError(f"technical_interaction_log[{index}].url must be an HTTP(S) URL")

    trials = diagnostics.get("cold_comprehension_trials", [])
    if not isinstance(trials, list):
        raise ValueError("cold_comprehension_trials must be a list")
    for index, trial in enumerate(trials):
        where = f"diagnostics.cold_comprehension_trials[{index}]"
        if not isinstance(trial, dict) or set(trial) != set(TRIAL_FIELDS):
            raise ValueError(f"{where} must contain exactly " + ", ".join(TRIAL_FIELDS))
        for key in ("answers", "scores"):
            allowed = set(TRIAL_QUESTIONS) | (set(TRIAL_OPTIONAL_ANSWERS) if key == "answers" else set())
            if (not isinstance(trial[key], dict) or not set(TRIAL_QUESTIONS) <= set(trial[key])
                    or not set(trial[key]) <= allowed):
                raise ValueError(f"{where}.{key} must carry exactly the frozen questions {TRIAL_QUESTIONS}"
                                 + (f" (plus, verbatim and unscored, any of {TRIAL_OPTIONAL_ANSWERS})" if key == "answers" else ""))
        for q, v in trial["scores"].items():
            if v not in ("pass", "fail"):
                raise ValueError(f"{where}.scores.{q} must be pass or fail, scored by the pre-registered rule")
        for q, v in trial["answers"].items():
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"{where}.answers.{q} must be the viewer's verbatim answer")
        if not DATE.match(str(trial["date"])):
            raise ValueError(f"{where}.date must be YYYY-MM-DD")

    rule = data.get("stop_rule")
    if not isinstance(rule, dict):
        raise ValueError("outcome ledger requires a stop_rule mapping")
    threshold = rule.get("threshold_interactions")
    if (isinstance(threshold, bool) or not isinstance(threshold, int)
            or threshold <= 0):
        raise ValueError("stop-rule threshold_interactions must be a positive integer")
    return data


def load(path: pathlib.Path = LEDGER) -> dict:
    if not path.exists():
        raise ValueError(f"{path.relative_to(ROOT)} is missing")
    return validate(yaml.safe_load(path.read_text()))


def qualified_total(data: dict) -> int:
    qualified = data["qualified"]
    return sum(len(qualified[bucket]) for bucket in QUALIFIED_BUCKETS)


def technical_interactions(data: dict) -> int:
    return data["diagnostics"]["technical_interactions"]


def main() -> int:
    try:
        data = load()
    except ValueError as exc:
        print(f"FAIL  {exc}")
        return 1
    qualified = data["qualified"]
    total = qualified_total(data)
    print("QUALIFIED OUTCOMES (someone who is not the author did work)")
    for bucket in QUALIFIED_BUCKETS:
        print(f"  {bucket:28s} {len(qualified[bucket]):3d}")
    print(f"  {'TOTAL':28s} {total:3d}")

    diagnostics = data["diagnostics"]
    print("\nDIAGNOSTICS (not evidence)")
    for key, value in diagnostics.items():
        if key == "technical_interaction_log":
            continue
        print(f"  {key:28s} {'—' if value is None else value}")
    for item in diagnostics["technical_interaction_log"]:
        print(f"  interaction {item['date']} {item['kind']}: {item['url']}")
    trials = diagnostics.get("cold_comprehension_trials", [])
    print(f"  {'cold_comprehension_trials':28s} {len(trials):3d}  — diagnostic, never an outcome")
    if trials:
        for q in TRIAL_QUESTIONS:
            fails = sum(1 for t in trials if t["scores"][q] == "fail")
            print(f"    {q:26s} pass {len(trials) - fails:2d}  fail {fails:2d}")
        repeated = [q for q in TRIAL_QUESTIONS if sum(1 for t in trials if t["scores"][q] == "fail") >= 2]
        enough = len(trials) >= 5
        print("  cold test gate: " + ("HOLD — repeated semantic failure on " + ", ".join(repeated) if repeated
              else ("PASS — no repeated semantic failure" if enough else f"PENDING — {5 - len(trials)} more viewers needed")))

    rule = data["stop_rule"]
    interactions = technical_interactions(data)
    threshold = rule["threshold_interactions"]
    print(f"\nSTOP RULE  ({interactions}/{threshold} technical interactions, {total} qualified)")
    if interactions >= threshold and total == 0:
        print("  TRIGGERED — stop replying; shift to upstream contributions and "
              "author outreach. Report the null result rather than continuing.")
    elif total > 0:
        print("  not triggered — qualified engagement exists.")
    else:
        print(f"  not triggered — {threshold - interactions} interactions remain before the "
              "null result is called.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
