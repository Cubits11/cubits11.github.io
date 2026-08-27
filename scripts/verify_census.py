#!/usr/bin/env python3
"""Verify the Missing Column Census (census.yaml) — census schema v1.

The census's public headline is an N/M/K statement. This verifier makes
that statement mechanical rather than rhetorical:

  1. Shape — the census block (frozen criteria, search protocol, revision
     history) and every benchmark row carry their required fields; enums
     are enforced; dates parse and never sit in the future.
  2. Consistency — a row classified PRESENT must point at its joint
     statistic and carry a joint_scope; a row that is not PRESENT may not
     release per-item outcomes (released outcomes make the joint statistic
     computable, which IS presence); a NOT_COMPARABLE row may not
     simultaneously assert a shared item set and a shared event.
  3. Counts — N, M, and K are recomputed from the rows. Anything the site
     prints comes from compute_counts(); there is no hand-typed headline
     number anywhere.

Rows with status under_review are excluded from every count and must say
so in their rendering. generate_missing_column.py imports this module so
the page and the verifier can never disagree about arithmetic.
"""

import datetime
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

CLASSIFICATIONS = {"PRESENT", "ABSENT", "AMBIGUOUS", "NOT_COMPARABLE"}
JOINT_SCOPES = {"printed_full_stack", "printed_partial_stack",
                "computable_via_item_release", "none"}
TRI_STATE = {"yes", "no", "unstated", "mixed"}

TRI_FIELDS = [
    "same_items_for_all_systems",
    "same_event_definition",
    "thresholds_comparable",
    "all_systems_saw_all_items",
    "item_level_outcomes_released",
    "pairwise_intersections_reported",
    "union_detection_reported",
    "all_miss_rate_reported",
    "residual_coverage_reported",
    "sequential_gating_modeled",
    "uncertainty_reported",
]

REQUIRED_EXAMINED = {
    "id", "status", "title", "authors_or_org", "publication_date",
    "primary_url", "task", "dataset_population", "n_items", "n_systems",
    "systems", "per_system_metrics", "raw_data_available", "code_available",
    "combination_prose", "joint_statistic_evidence", "joint_scope",
    "classification", "classification_reason", "source_passages",
    "contact_route", "last_checked", "correction_history",
    *TRI_FIELDS,
}

REQUIRED_UNDER_REVIEW = {"id", "status", "title", "primary_url",
                         "last_checked", "notes"}

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def parse_date(raw, where: str):
    try:
        d = datetime.date.fromisoformat(str(raw))
    except ValueError:
        fail(f"{where}: date {raw!r} is not ISO YYYY-MM-DD")
        return None
    if d > datetime.date.today():
        fail(f"{where}: date {raw!r} is in the future")
    return d


def tri_value(row: dict, field: str, rid: str) -> str:
    """A tri-state field is {value, evidence}; value from the fixed enum."""
    cell = row.get(field)
    if not isinstance(cell, dict) or "value" not in cell:
        fail(f"{rid}: {field} must be a mapping with value and evidence")
        return "unstated"
    value = str(cell["value"])
    if value not in TRI_STATE:
        fail(f"{rid}: {field}.value={value!r} not in {sorted(TRI_STATE)}")
    evidence = cell.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        fail(f"{rid}: {field}.evidence must be a non-empty string "
             f"(say where the answer comes from, or why it is unstated)")
    return value


def check_census_block(census: dict) -> None:
    required = {"id", "schema_version", "criteria_version", "frozen_as_of",
                "maintainer", "question", "proposition_template",
                "inclusion_criteria", "exclusion_rules", "non_criteria_note",
                "search_protocol", "revision_history"}
    missing = required - set(census)
    if missing:
        fail(f"census block missing fields {sorted(missing)}")
    parse_date(census.get("frozen_as_of"), "census.frozen_as_of")
    criteria = census.get("inclusion_criteria") or []
    if not isinstance(criteria, list) or len(criteria) < 3:
        fail("census.inclusion_criteria must list the frozen criteria")
    for i, c in enumerate(criteria):
        if not isinstance(c, dict) or not c.get("key") or not c.get("text"):
            fail(f"census.inclusion_criteria[{i}] needs key and text")
    history = census.get("revision_history") or []
    if not history:
        fail("census.revision_history may never be empty — the census "
             "records its own establishment")
    for i, entry in enumerate(history):
        if not isinstance(entry, dict) or not entry.get("change"):
            fail(f"census.revision_history[{i}] needs date and change")
            continue
        parse_date(entry.get("date"), f"census.revision_history[{i}].date")
    protocol = census.get("search_protocol") or {}
    for field in ("executed", "bounded", "starting_cases", "queries",
                  "snowball", "budget"):
        if field not in protocol:
            fail(f"census.search_protocol missing {field!r}")


def check_row(row: dict, seen_ids: set) -> None:
    rid = str(row.get("id", "<no id>"))
    if rid in seen_ids:
        fail(f"{rid}: duplicate id")
    seen_ids.add(rid)
    status = row.get("status")
    if status not in ("examined", "under_review"):
        fail(f"{rid}: status={status!r} must be examined|under_review")
        return
    required = REQUIRED_EXAMINED if status == "examined" else REQUIRED_UNDER_REVIEW
    missing = required - set(row)
    if missing:
        fail(f"{rid}: missing fields {sorted(missing)}")
        return
    parse_date(row["last_checked"], f"{rid}.last_checked")
    url = row.get("primary_url")
    if url is not None and not str(url).startswith(("http://", "https://")):
        fail(f"{rid}: primary_url must be http(s) or null")
    if status == "under_review":
        if url is None and not str(row.get("notes", "")).strip():
            fail(f"{rid}: under_review with no primary_url must explain "
                 f"itself in notes")
        return

    # ---- examined rows ----
    if url is None:
        fail(f"{rid}: examined rows require a primary_url")
    pub = str(row["publication_date"]).strip()
    if not pub:
        fail(f"{rid}: publication_date must be non-empty (free text allowed; "
             f"blogs rarely print ISO dates)")
    elif len(pub) == 10 and pub[4] == "-" and pub[7] == "-":
        parse_date(pub, f"{rid}.publication_date")
    values = {f: tri_value(row, f, rid) for f in TRI_FIELDS}
    classification = row["classification"]
    if classification not in CLASSIFICATIONS:
        fail(f"{rid}: classification={classification!r} not in "
             f"{sorted(CLASSIFICATIONS)}")
        return
    joint_scope = row["joint_scope"]
    if joint_scope not in JOINT_SCOPES:
        fail(f"{rid}: joint_scope={joint_scope!r} not in {sorted(JOINT_SCOPES)}")
    evidence = str(row["joint_statistic_evidence"]).strip()
    if classification == "PRESENT":
        if joint_scope == "none":
            fail(f"{rid}: PRESENT requires a joint_scope other than 'none'")
        if not evidence or evidence.lower().startswith("none"):
            fail(f"{rid}: PRESENT requires joint_statistic_evidence to name "
                 f"the table/section or the released item-level artifact")
    else:
        if joint_scope != "none":
            fail(f"{rid}: joint_scope={joint_scope!r} contradicts "
                 f"classification {classification}")
        if values["item_level_outcomes_released"] == "yes":
            fail(f"{rid}: released per-item outcomes make the joint "
                 f"statistic computable — classification must be PRESENT")
    if classification == "NOT_COMPARABLE":
        if (values["same_items_for_all_systems"] == "yes"
                and values["same_event_definition"] == "yes"
                and values["thresholds_comparable"] == "yes"):
            fail(f"{rid}: NOT_COMPARABLE but items, event, and thresholds "
                 f"all read 'yes' — one of them must record the failure")
    if not isinstance(row["systems"], list) or len(row["systems"]) < 2:
        fail(f"{rid}: systems must list the ≥2 evaluated systems")
    passages = row["source_passages"]
    if not isinstance(passages, list) or not passages:
        fail(f"{rid}: source_passages must cite at least one precise "
             f"location in the primary source")
    reason = str(row["classification_reason"]).strip()
    if not reason:
        fail(f"{rid}: classification_reason must say why, in one breath")
    if not isinstance(row["correction_history"], list):
        fail(f"{rid}: correction_history must be a list ([] when clean)")
    prose = row["combination_prose"]
    if prose is not None:
        if not isinstance(prose, dict) or not prose.get("quote") \
                or not prose.get("location"):
            fail(f"{rid}: combination_prose must be null or "
                 f"{{quote, location}}")


def check_exclusion(row: dict, seen_ids: set) -> None:
    rid = str(row.get("id", "<no id>"))
    if rid in seen_ids:
        fail(f"exclusions.{rid}: duplicate id")
    seen_ids.add(rid)
    for field in ("id", "title", "reason", "last_checked"):
        if not str(row.get(field, "")).strip():
            fail(f"exclusions.{rid}: missing {field}")
    parse_date(row.get("last_checked"), f"exclusions.{rid}.last_checked")


def compute_counts(data: dict) -> dict:
    """The one arithmetic in the census. The page renders these numbers
    and no others; hand-typing an N, M, or K anywhere is drift."""
    rows = data.get("benchmarks") or []
    examined = [r for r in rows if r.get("status") == "examined"]
    under_review = [r for r in rows if r.get("status") == "under_review"]

    def tri(row, field):
        cell = row.get(field)
        return cell.get("value") if isinstance(cell, dict) else None

    comparable = [r for r in examined
                  if tri(r, "same_items_for_all_systems") == "yes"
                  and tri(r, "same_event_definition") == "yes"]
    present = [r for r in examined if r.get("classification") == "PRESENT"]
    by_classification: dict = {}
    for r in examined:
        c = r.get("classification", "?")
        by_classification[c] = by_classification.get(c, 0) + 1
    by_scope: dict = {}
    for r in present:
        s = r.get("joint_scope", "?")
        by_scope[s] = by_scope.get(s, 0) + 1
    return {
        "N": len(examined),
        "M": len(comparable),
        "K": len(present),
        "by_classification": by_classification,
        "present_by_scope": by_scope,
        "under_review": len(under_review),
        "excluded": len(data.get("exclusions") or []),
        "unexamined": len(data.get("unexamined_candidates") or []),
    }


def load() -> dict:
    return yaml.safe_load((ROOT / "census.yaml").read_text())


def main() -> int:
    data = load()
    check_census_block(data.get("census") or {})
    seen: set = set()
    for row in data.get("benchmarks") or []:
        check_row(row, seen)
    for row in data.get("exclusions") or []:
        check_exclusion(row, seen)
    counts = compute_counts(data)

    if "--counts" in sys.argv:
        print(json.dumps(counts, indent=2, sort_keys=True))

    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    ok(f"census block: criteria v{data['census']['criteria_version']} "
       f"frozen {data['census']['frozen_as_of']}, revision history present")
    ok(f"rows: {counts['N']} examined · {counts['under_review']} under review "
       f"· {counts['excluded']} excluded · {counts['unexamined']} unexamined")
    ok(f"counts recomputed: N={counts['N']} M={counts['M']} K={counts['K']} "
       f"(scopes {counts['present_by_scope'] or '—'})")
    print("Census verified: criteria frozen, rows shaped, classifications "
          "consistent, counts mechanical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
