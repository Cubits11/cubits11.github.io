#!/usr/bin/env python3
"""Verify the Missing Column Census (census.yaml) — census schema v2.

The census's public headline is an N/M/K statement. This verifier makes
that statement mechanical rather than rhetorical:

  1. Shape — the census block (criteria lock, search protocol, revision
     history, adjudication status) and every benchmark row carry their required fields; enums
     are enforced; dates parse and never sit in the future.
  2. Consistency — a row classified PRESENT must point at its joint
     statistic and carry a joint_scope; a row that is not PRESENT may not
     release per-item outcomes (released outcomes make the joint statistic
     computable, which IS presence); a NOT_COMPARABLE row may not
     simultaneously assert a shared item set and a shared event.
  3. Counts — N, M, and K are recomputed from the rows. Anything the site
     prints comes from compute_counts(); there is no hand-typed headline
     number anywhere.
  4. Interpretation sensitivities — any stricter defensible reading that
     changes the census is declared as named row exclusions whose alternate
     N/M/K values this verifier independently recomputes.

Rows with status under_review are excluded from every count and must say
so in their rendering. generate_missing_column.py imports this module so
the page and the verifier can never disagree about arithmetic.
"""

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

CLASSIFICATIONS = {"PRESENT", "ABSENT", "AMBIGUOUS", "NOT_COMPARABLE"}
JOINT_SCOPES = {"printed_full_stack", "printed_partial_stack",
                "computable_via_item_release", "none"}
ADJUDICATION_MODES = {"single_primary_reviewer", "dual_reviewed"}
TRI_STATE = {"yes", "no", "unstated", "mixed"}
CENSUS_SCHEMA_VERSION = 3
CRITERIA_CANONICALIZATION = (
    "JSON UTF-8; sort_keys=true; separators=(',', ':'); ensure_ascii=false; "
    "inclusion_criteria only"
)

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
                "maintainer", "adjudication_status", "question", "proposition_template",
                "inclusion_criteria", "exclusion_rules", "non_criteria_note",
                "frozen_criteria_lock", "interpretation_sensitivities",
                "search_protocol", "revision_history"}
    missing = required - set(census)
    if missing:
        fail(f"census block missing fields {sorted(missing)}")
    if census.get("schema_version") != CENSUS_SCHEMA_VERSION:
        fail(f"census.schema_version must be {CENSUS_SCHEMA_VERSION} for "
             "the current verifier")
    parse_date(census.get("frozen_as_of"), "census.frozen_as_of")
    adjudication = census.get("adjudication_status")
    if not isinstance(adjudication, dict):
        fail("census.adjudication_status must be a mapping")
    else:
        if adjudication.get("mode") not in ADJUDICATION_MODES:
            fail("census.adjudication_status.mode must be one of "
                 f"{sorted(ADJUDICATION_MODES)}")
        covered = adjudication.get("covered_examined_rows")
        if not isinstance(covered, int) or isinstance(covered, bool) or covered < 0:
            fail("census.adjudication_status.covered_examined_rows must be a "
                 "non-negative integer")
        for field in ("limit", "release_gate"):
            if not isinstance(adjudication.get(field), str) \
                    or not adjudication[field].strip():
                fail(f"census.adjudication_status.{field} must be non-empty")
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
    for name in ("exclusion_rules", "queries"):
        seq = (census.get(name) if name == "exclusion_rules"
               else protocol.get(name)) or []
        for i, item in enumerate(seq):
            if not isinstance(item, str) or not item.strip():
                fail(f"census.{name}[{i}] must be a non-empty string — an "
                     f"unquoted 'key: value' scalar parses as a mapping and "
                     f"renders as a dict on the public page")
    if not isinstance(census.get("interpretation_sensitivities"), list):
        fail("census.interpretation_sensitivities must be a list — use [] "
             "when no alternate reading changes a count")


def criteria_digest(criteria: list) -> str:
    """Hash literal criterion values independently of YAML formatting."""
    canonical = json.dumps(criteria, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def check_frozen_criteria_lock(census: dict) -> None:
    """Prove the literal v1 criteria still match the pre-search commit.

    The lock protects wording, not interpretation: later sensitivities are
    deliberately recorded elsewhere and cannot be smuggled into the frozen
    criterion text. Both the current digest and the historical file at the
    declared immutable commit must agree.
    """
    lock = census.get("frozen_criteria_lock")
    if not isinstance(lock, dict):
        fail("census.frozen_criteria_lock must be a mapping")
        return
    source_commit = lock.get("source_commit")
    declared = lock.get("sha256")
    if not isinstance(source_commit, str) or len(source_commit) != 40 \
            or any(ch not in "0123456789abcdef" for ch in source_commit):
        fail("census.frozen_criteria_lock.source_commit must be a full lowercase "
             "Git SHA-1")
        return
    if lock.get("canonicalization") != CRITERIA_CANONICALIZATION:
        fail("census.frozen_criteria_lock.canonicalization does not name the "
             "verifier's fixed canonical form")
        return
    if not isinstance(declared, str) or len(declared) != 64 \
            or any(ch not in "0123456789abcdef" for ch in declared):
        fail("census.frozen_criteria_lock.sha256 must be a lowercase SHA-256")
        return
    criteria = census.get("inclusion_criteria")
    if not isinstance(criteria, list):
        return  # shape failure already reported above
    current = criteria_digest(criteria)
    if current != declared:
        fail("census.frozen_criteria_lock: current inclusion_criteria hash "
             f"{current[:12]} does not match declared {declared[:12]}")
    try:
        result = subprocess.run(
            ["git", "show", f"{source_commit}:census.yaml"], cwd=ROOT,
            capture_output=True, text=True, check=False)
    except OSError as exc:
        fail(f"census.frozen_criteria_lock: cannot invoke git show ({exc})")
        return
    if result.returncode != 0:
        fail("census.frozen_criteria_lock: source commit is unavailable — "
             "full git history is required to verify a frozen criterion")
        return
    try:
        snapshot = yaml.safe_load(result.stdout) or {}
        frozen = snapshot["census"]["inclusion_criteria"]
    except (KeyError, TypeError, yaml.YAMLError) as exc:
        fail(f"census.frozen_criteria_lock: cannot read criteria at "
             f"{source_commit[:12]} ({exc})")
        return
    if not isinstance(frozen, list):
        fail("census.frozen_criteria_lock: source commit has no criteria list")
        return
    historical = criteria_digest(frozen)
    if historical != declared:
        fail("census.frozen_criteria_lock: source commit criteria hash "
             f"{historical[:12]} does not match declared {declared[:12]}")
    elif current == declared:
        ok(f"frozen criteria lock: v1 wording matches {source_commit[:12]} "
           f"(sha256 {declared[:12]})")


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
    # A row may carry a second kind of joint evidence. Declaring it is
    # optional; declaring it loosely is not, because scope-mode counts are
    # derived from this field and a count nobody can recompute is the
    # defect this field exists to prevent.
    additional = row.get("joint_scope_additional") or []
    if not isinstance(additional, list):
        fail(f"{rid}: joint_scope_additional must be a list of scopes")
        additional = []
    for extra in additional:
        if extra not in JOINT_SCOPES or extra == "none":
            fail(f"{rid}: joint_scope_additional={extra!r} not in "
                 f"{sorted(JOINT_SCOPES - {'none'})}")
        elif extra == joint_scope:
            fail(f"{rid}: joint_scope_additional repeats the primary "
                 f"joint_scope {joint_scope!r}")
    if additional and classification != "PRESENT":
        fail(f"{rid}: joint_scope_additional requires classification PRESENT")
    if len(set(additional)) != len(additional):
        fail(f"{rid}: joint_scope_additional contains duplicates")
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
    history = row["correction_history"]
    if not isinstance(history, list):
        fail(f"{rid}: correction_history must be a list ([] when clean)")
    else:
        for i, correction in enumerate(history):
            where = f"{rid}.correction_history[{i}]"
            if not isinstance(correction, dict):
                fail(f"{where} must be a mapping with date and change")
                continue
            parse_date(correction.get("date"), f"{where}.date")
            if not isinstance(correction.get("change"), str) \
                    or not correction["change"].strip():
                fail(f"{where}.change must be a non-empty string")
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


def compute_counts(data: dict, excluded_ids: set[str] | None = None) -> dict:
    """The one arithmetic in the census. The page renders these numbers
    and no others; hand-typing an N, M, or K anywhere is drift.

    ``excluded_ids`` exists only for declared interpretation sensitivities:
    it lets the verifier re-run the exact same arithmetic under a visible,
    named stricter reading instead of leaving a competing count in prose.
    """
    excluded_ids = excluded_ids or set()
    rows = data.get("benchmarks") or []
    examined = [r for r in rows if r.get("status") == "examined"
                and r.get("id") not in excluded_ids]
    under_review = [r for r in rows if r.get("status") == "under_review"]

    def tri(row, field):
        cell = row.get(field)
        return cell.get("value") if isinstance(cell, dict) else None

    comparable = [r for r in examined
                  if tri(r, "same_items_for_all_systems") == "yes"
                  and tri(r, "same_event_definition") == "yes"]
    # M is a stratum, not a verdict. Its shared-basis rung means only shared
    # items and a shared event definition; it says nothing about
    # whether the systems were compared at documented, matched operating
    # thresholds, or whether every system saw every item. Reporting M as a
    # single number lets a reader assume the stronger reading, so the census
    # publishes the whole ladder and the page renders all three rungs.
    # "No stated threshold mismatch" permits an explicit match or a source
    # that simply does not report threshold comparability. A "mixed" record
    # has stated a partial mismatch and must not enter this rung by accident.
    threshold_not_contradicted = [r for r in comparable
                                  if tri(r, "thresholds_comparable")
                                  in {"yes", "unstated"}]
    threshold_documented = [r for r in threshold_not_contradicted
                            if tri(r, "thresholds_comparable") == "yes"
                            and tri(r, "all_systems_saw_all_items") == "yes"]
    present = [r for r in examined if r.get("classification") == "PRESENT"]
    by_classification: dict = {}
    for r in examined:
        c = r.get("classification", "?")
        by_classification[c] = by_classification.get(c, 0) + 1
    by_scope: dict = {}
    for r in present:
        s = r.get("joint_scope", "?")
        by_scope[s] = by_scope.get(s, 0) + 1
    # Evidence modes are not the primary-scope split: a row can print a
    # composition result *and* release the items. Prose used to state that
    # overlap as a hand-typed number; it is derived here instead, so the
    # sentence and the file cannot disagree.
    printed_scopes = {"printed_full_stack", "printed_partial_stack"}
    prints_any = 0
    releases_items = 0
    both = 0
    for r in present:
        scopes = {r.get("joint_scope")} | set(r.get("joint_scope_additional") or [])
        p_hit = bool(scopes & printed_scopes)
        c_hit = "computable_via_item_release" in scopes
        prints_any += p_hit
        releases_items += c_hit
        both += p_hit and c_hit
    return {
        "N": len(examined),
        "M": len(comparable),
        "M_strata": {
            "shared_basis": len(comparable),
            "threshold_not_contradicted": len(threshold_not_contradicted),
            "threshold_documented_full_exposure": len(threshold_documented),
        },
        "K": len(present),
        "K_evidence_modes": {
            "prints_composition_result": prints_any,
            "releases_computable_items": releases_items,
            "does_both": both,
        },
        "by_classification": by_classification,
        "present_by_scope": by_scope,
        "under_review": len(under_review),
        "excluded": len(data.get("exclusions") or []),
        "unexamined": len(data.get("unexamined_candidates") or []),
    }


def check_interpretation_sensitivities(data: dict) -> None:
    """Verify disclosed alternate readings rather than trusting their prose.

    A sensitivity may only remove named, examined rows. It cannot alter a
    row's evidence or classification behind the reader's back; if a different
    interpretation needs different field values, it deserves a separately
    reviewed census revision instead.
    """
    census = data.get("census") or {}
    sensitivities = census.get("interpretation_sensitivities")
    if not isinstance(sensitivities, list):
        return  # check_census_block already reports the shape failure
    examined_ids = {str(r.get("id")) for r in data.get("benchmarks") or []
                    if r.get("status") == "examined"}
    seen: set[str] = set()
    keys = ("n_examined", "m_shared_basis", "k_present")
    for i, item in enumerate(sensitivities):
        where = f"census.interpretation_sensitivities[{i}]"
        if not isinstance(item, dict):
            fail(f"{where} must be a mapping")
            continue
        sid = item.get("id")
        if not isinstance(sid, str) or not sid.strip():
            fail(f"{where}.id must be a non-empty string")
            sid = f"<invalid-{i}>"
        elif sid in seen:
            fail(f"{where}.id={sid!r} duplicates an earlier sensitivity")
        seen.add(sid)
        for field in ("label", "premise"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                fail(f"{where}.{field} must be a non-empty string")
        excluded = item.get("exclude_benchmark_ids")
        if not isinstance(excluded, list) or not excluded:
            fail(f"{where}.exclude_benchmark_ids must name at least one "
                 "examined row")
            continue
        if any(not isinstance(rid, str) or not rid.strip() for rid in excluded):
            fail(f"{where}.exclude_benchmark_ids must contain non-empty strings")
            continue
        if len(set(excluded)) != len(excluded):
            fail(f"{where}.exclude_benchmark_ids repeats a row id")
            continue
        unknown = sorted(set(excluded) - examined_ids)
        if unknown:
            fail(f"{where}.exclude_benchmark_ids names non-examined row(s) "
                 f"{unknown}")
            continue
        expected = item.get("expected")
        if not isinstance(expected, dict):
            fail(f"{where}.expected must state N/M/K")
            continue
        if any(not isinstance(expected.get(k), int) or isinstance(expected.get(k), bool)
               for k in keys):
            fail(f"{where}.expected must give integer n_examined, "
                 "m_shared_basis, and k_present")
            continue
        counts = compute_counts(data, set(excluded))
        actual = (counts["N"], counts["M"], counts["K"])
        stated = tuple(expected[k] for k in keys)
        if stated != actual:
            fail(f"{where} expected N/M/K {stated} but named exclusions "
                 f"compute {actual}")
        else:
            ok(f"sensitivity {sid}: named exclusions reproduce N/M/K "
               f"{actual[0]}/{actual[1]}/{actual[2]}")


def load() -> dict:
    return yaml.safe_load((ROOT / "census.yaml").read_text())


def main() -> int:
    data = load()
    check_census_block(data.get("census") or {})
    check_frozen_criteria_lock(data.get("census") or {})
    seen: set = set()
    for row in data.get("benchmarks") or []:
        check_row(row, seen)
    for row in data.get("exclusions") or []:
        check_exclusion(row, seen)
    check_interpretation_sensitivities(data)
    counts = compute_counts(data)
    adjudication = (data.get("census") or {}).get("adjudication_status") or {}
    if adjudication.get("covered_examined_rows") != counts["N"]:
        fail("census.adjudication_status.covered_examined_rows must equal "
             f"the current examined-row count ({counts['N']})")
    else:
        ok(f"adjudication status declared: {adjudication.get('mode')} for "
           f"{counts['N']} examined row(s)")

    # Claim coherence: if the registry carries the census claim, its
    # expected counts must equal what this file actually computes — the
    # public envelope can never drift from the census arithmetic.
    claims_path = ROOT / "claims.yaml"
    if claims_path.exists():
        registry = yaml.safe_load(claims_path.read_text())
        mc = next((c for c in registry.get("claims", [])
                   if c.get("id") == "MC-001"), None)
        if mc is not None:
            expected = mc.get("expected") or {}
            stated = (expected.get("n_examined"), expected.get("m_shared_basis"),
                      expected.get("k_present"))
            actual = (counts["N"], counts["M"], counts["K"])
            if stated != actual:
                fail(f"MC-001 expected N/M/K {stated} but census computes "
                     f"{actual} — re-review the claim or fix the census")
            else:
                ok(f"MC-001 expected counts match the census (N/M/K "
                   f"{actual[0]}/{actual[1]}/{actual[2]})")
            # The M ladder is part of the envelope: a claim that prints one
            # M must also state what stricter policy/exposure readings yield,
            # or the strongest reading is silently implied.
            stated_strata = expected.get("m_strata")
            if not isinstance(stated_strata, dict):
                fail("MC-001 expected must carry an m_strata block "
                     "(shared_basis, threshold_not_contradicted, "
                     "threshold_documented_full_exposure)")
            elif stated_strata != counts["M_strata"]:
                fail(f"MC-001 expected m_strata {stated_strata} but census "
                     f"computes {counts['M_strata']}")
            else:
                fail_free = counts["M_strata"]
                ok(f"MC-001 M ladder matches the census "
                   f"({fail_free['shared_basis']}/"
                   f"{fail_free['threshold_not_contradicted']}/"
                   f"{fail_free['threshold_documented_full_exposure']})")

    if "--counts" in sys.argv:
        print(json.dumps(counts, indent=2, sort_keys=True))

    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    ok(f"census block: criteria v{data['census']['criteria_version']} wording "
       f"locked {data['census']['frozen_as_of']}, revision history present")
    ok(f"rows: {counts['N']} examined · {counts['under_review']} under review "
       f"· {counts['excluded']} excluded · {counts['unexamined']} unexamined")
    ok(f"counts recomputed: N={counts['N']} M={counts['M']} K={counts['K']} "
       f"(scopes {counts['present_by_scope'] or '—'})")
    strata = counts["M_strata"]
    ok(f"M ladder: {strata['shared_basis']} shared basis · "
       f"{strata['threshold_not_contradicted']} no stated threshold mismatch · "
       f"{strata['threshold_documented_full_exposure']} documented matched "
       f"thresholds with full exposure")
    print("Census verified: criteria lock, adjudication status, row shape, "
          "classification consistency, and mechanical counts all hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
