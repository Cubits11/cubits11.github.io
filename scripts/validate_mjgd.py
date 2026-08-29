#!/usr/bin/env python3
"""Validate a Minimum Joint Guardrail Disclosure (MJGD) v1 packet.

MJGD v1 is a machine-readable disclosure schema, not a safety standard and
not another calculator. It makes the boundary of the existing reference
arithmetic executable:

* complete static full-exposure outcomes are recomputed;
* complete aggregate pattern tables are recomputed without item identities;
* marginals alone produce their exact finite identified set;
* routes, gates, partial exposure, and missing decision cells HOLD rather
  than being silently reduced to a static stack result.

The validator is standard-library-only. It imports the existing arithmetic
sources rather than recreating their mathematics.
"""

from __future__ import annotations

import argparse
import copy
import datetime as datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

import identification
import mjgd_reference


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT / "fixtures" / "mjgd-v1"
SCHEMA_PATH = ROOT / "schemas" / "mjgd-v1.schema.json"

SCHEMA_VERSION = "mjgd/v1"
STATIC_MODE = "parallel_full_exposure"
ROUTE_MODES = {"sequential_route", "gated_route"}
STATUS_RECOMPUTABLE = "RECOMPUTABLE_STATIC"
STATUS_AGGREGATE_PATTERNS = "RECOMPUTED_FROM_AGGREGATE_PATTERNS"
STATUS_NOT_IDENTIFIED = "NOT_IDENTIFIED_FROM_MARGINALS"
STATUS_HOLD_ROUTE = "HOLD_ROUTE_TRACE_REQUIRED"
STATUS_HOLD_MISSING = "HOLD_MISSING_DATA"

SYSTEM_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    """A packet is malformed or makes a claim its evidence cannot support."""


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_packet(path: Path) -> dict[str, Any]:
    """Load one packet and reject duplicate JSON object keys."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"),
                             object_pairs_hook=_no_duplicate_keys)
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{path}: packet root must be an object")
    return payload


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _keys(value: Any, required: set[str], optional: set[str], label: str) -> dict[str, Any]:
    result = _mapping(value, label)
    missing = required - set(result)
    extra = set(result) - required - optional
    if missing:
        raise ValidationError(f"{label} missing required field(s): {', '.join(sorted(missing))}")
    if extra:
        raise ValidationError(f"{label} has unknown field(s): {', '.join(sorted(extra))}")
    return result


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _integer(value: Any, label: str, lower: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < lower:
        raise ValidationError(f"{label} must be an integer >= {lower}")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{label} must be boolean")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{label} must be a non-empty list")
    result = [_string(item, f"{label} entry") for item in value]
    if len(set(result)) != len(result):
        raise ValidationError(f"{label} must not contain duplicates")
    return result


def _check_date(value: Any, label: str) -> str:
    date = _string(value, label)
    try:
        datetime.date.fromisoformat(date)
    except ValueError as exc:
        raise ValidationError(f"{label} must be YYYY-MM-DD") from exc
    return date


def _check_system_id(value: Any, label: str) -> str:
    system_id = _string(value, label)
    if not SYSTEM_ID.fullmatch(system_id):
        raise ValidationError(
            f"{label} must match {SYSTEM_ID.pattern!r}; got {system_id!r}")
    return system_id


def _check_exact_map(value: Any, expected: list[str], label: str,
                     validator) -> dict[str, Any]:
    result = _mapping(value, label)
    actual = set(result)
    needed = set(expected)
    if actual != needed:
        missing = needed - actual
        extra = actual - needed
        parts = []
        if missing:
            parts.append("missing " + ", ".join(sorted(missing)))
        if extra:
            parts.append("unknown " + ", ".join(sorted(extra)))
        raise ValidationError(
            f"{label} must have exactly the declared systems ({'; '.join(parts)})")
    for key in expected:
        validator(result[key], f"{label}.{key}")
    return result


def _manifest(value: Any, label: str) -> dict[str, Any]:
    result = _keys(value, {"kind", "location", "sha256"}, set(), label)
    _string(result["kind"], f"{label}.kind")
    _string(result["location"], f"{label}.location")
    digest = _string(result["sha256"], f"{label}.sha256")
    if not SHA256.fullmatch(digest):
        raise ValidationError(f"{label}.sha256 must be a lowercase SHA-256 digest")
    return result


def _unavailable(value: Any, label: str) -> dict[str, Any]:
    result = _keys(value, {"status", "reason"}, set(), label)
    if result["status"] != "not_available":
        raise ValidationError(f"{label}.status must be 'not_available'")
    _string(result["reason"], f"{label}.reason")
    return result


def _validate_scope(value: Any) -> dict[str, Any]:
    result = _keys(value, {"stratum_id", "threat_regime"}, set(), "scope")
    _check_system_id(result["stratum_id"], "scope.stratum_id")
    _string(result["threat_regime"], "scope.threat_regime")
    return result


def _validate_population(value: Any) -> dict[str, int]:
    result = _keys(value, {"id", "positive_denominator", "benign_denominator"},
                   set(), "population")
    _check_system_id(result["id"], "population.id")
    return {
        "positive_denominator": _integer(result["positive_denominator"],
                                         "population.positive_denominator", 1),
        "benign_denominator": _integer(result["benign_denominator"],
                                       "population.benign_denominator", 0),
    }


def _validate_event(value: Any, route: bool) -> dict[str, Any]:
    optional = {"terminal_event_definition"}
    result = _keys(value, {"positive_definition", "flag_definition"}, optional, "event")
    _string(result["positive_definition"], "event.positive_definition")
    _string(result["flag_definition"], "event.flag_definition")
    if route:
        if "terminal_event_definition" not in result:
            raise ValidationError("event.terminal_event_definition is required for route evidence")
        _string(result["terminal_event_definition"], "event.terminal_event_definition")
    return result


def _validate_systems(value: Any) -> tuple[list[str], list[dict[str, str]]]:
    if not isinstance(value, list) or len(value) < 2:
        raise ValidationError("systems must be a list of at least two systems")
    systems = []
    ids = []
    for index, raw in enumerate(value):
        item = _keys(raw, {"id", "name", "version", "operating_point"}, set(),
                     f"systems[{index}]")
        system_id = _check_system_id(item["id"], f"systems[{index}].id")
        ids.append(system_id)
        systems.append({
            "id": system_id,
            "name": _string(item["name"], f"systems[{index}].name"),
            "version": _string(item["version"], f"systems[{index}].version"),
            "operating_point": _string(item["operating_point"],
                                        f"systems[{index}].operating_point"),
        })
    if len(set(ids)) != len(ids):
        raise ValidationError("systems contains duplicate system ids")
    return ids, systems


def _validate_execution(value: Any, system_ids: list[str]) -> dict[str, Any]:
    result = _keys(value, {"mode", "topology", "same_items", "full_exposure", "order"},
                   set(), "execution")
    mode = _string(result["mode"], "execution.mode")
    if mode not in {STATIC_MODE, *ROUTE_MODES}:
        raise ValidationError("execution.mode must be parallel_full_exposure, "
                              "sequential_route, or gated_route")
    topology = _string(result["topology"], "execution.topology")
    same_items = _boolean(result["same_items"], "execution.same_items")
    full_exposure = _boolean(result["full_exposure"], "execution.full_exposure")
    order = _string_list(result["order"], "execution.order")
    if set(order) != set(system_ids) or len(order) != len(system_ids):
        raise ValidationError("execution.order must contain every declared system exactly once")
    if mode == STATIC_MODE:
        if topology != "parallel_or" or not same_items or not full_exposure:
            raise ValidationError(
                "parallel_full_exposure requires parallel_or, same_items=true, "
                "and full_exposure=true")
    elif mode == "sequential_route":
        if topology != "sequential":
            raise ValidationError("sequential_route requires execution.topology='sequential'")
    elif topology != "gated":
        raise ValidationError("gated_route requires execution.topology='gated'")
    return {
        "mode": mode,
        "topology": topology,
        "same_items": same_items,
        "full_exposure": full_exposure,
        "order": order,
    }


def _validate_missingness(value: Any) -> set[str]:
    result = _keys(value, {"policy", "allowed_codes"}, set(), "missingness")
    if result["policy"] != "hold":
        raise ValidationError("MJGD v1 accepts only missingness.policy='hold'")
    codes = _string_list(result["allowed_codes"], "missingness.allowed_codes")
    if not {"flag", "clear"}.issubset(codes):
        raise ValidationError("missingness.allowed_codes must include 'flag' and 'clear'")
    allowed = {"flag", "clear", "timeout", "error", "not_exposed"}
    unknown = set(codes) - allowed
    if unknown:
        raise ValidationError("missingness.allowed_codes has unsupported code(s): "
                              + ", ".join(sorted(unknown)))
    return set(codes)


def _validate_packet_contract(packet: dict[str, Any]) -> dict[str, Any]:
    root = _keys(
        packet,
        {
            "schema_version", "disclosure_id", "observed_at", "scope", "population",
            "event", "systems", "execution", "missingness", "evidence", "reported",
            "uncertainty", "repeat_after", "non_claims",
        },
        set(),
        "packet",
    )
    if root["schema_version"] != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION!r}")
    disclosure_id = _string(root["disclosure_id"], "disclosure_id")
    if not disclosure_id.startswith("mjgd-v1:"):
        raise ValidationError("disclosure_id must start with 'mjgd-v1:'")
    _check_date(root["observed_at"], "observed_at")
    _validate_scope(root["scope"])
    population = _validate_population(root["population"])
    system_ids, _ = _validate_systems(root["systems"])
    execution = _validate_execution(root["execution"], system_ids)
    _validate_event(root["event"], execution["mode"] in ROUTE_MODES)
    allowed_codes = _validate_missingness(root["missingness"])
    uncertainty = _keys(root["uncertainty"], {"kind", "reason"}, set(), "uncertainty")
    _string(uncertainty["kind"], "uncertainty.kind")
    _string(uncertainty["reason"], "uncertainty.reason")
    repeat_after = set(_string_list(root["repeat_after"], "repeat_after"))
    required_repeat = {
        "system_version_change",
        "operating_point_change",
        "topology_or_route_change",
    }
    if not required_repeat.issubset(repeat_after):
        raise ValidationError("repeat_after is missing required trigger(s): "
                              + ", ".join(sorted(required_repeat - repeat_after)))
    non_claims = set(_string_list(root["non_claims"], "non_claims"))
    required_non_claims = {
        "static_all_miss_is_not_route_risk",
        "static_all_miss_is_not_adaptive_robustness",
    }
    if not required_non_claims.issubset(non_claims):
        raise ValidationError("non_claims is missing required boundary statement(s): "
                              + ", ".join(sorted(required_non_claims - non_claims)))
    reported = _keys(root["reported"], {"positive", "benign"}, set(), "reported")
    return {
        "disclosure_id": disclosure_id,
        "population": population,
        "system_ids": system_ids,
        "execution": execution,
        "allowed_codes": allowed_codes,
        "evidence": _mapping(root["evidence"], "evidence"),
        "reported": reported,
    }


def _positive_metrics(value: Any, system_ids: list[str], label: str) -> dict[str, Any]:
    result = _keys(
        value,
        {
            "per_system_catches", "union_detection", "all_miss",
            "ordered_prefix_unions", "leave_one_out_unions",
        },
        set(),
        label,
    )
    catches = _check_exact_map(result["per_system_catches"], system_ids,
                               f"{label}.per_system_catches",
                               lambda x, name: _integer(x, name))
    union = _integer(result["union_detection"], f"{label}.union_detection")
    all_miss = _integer(result["all_miss"], f"{label}.all_miss")
    prefix = result["ordered_prefix_unions"]
    if not isinstance(prefix, list) or len(prefix) != len(system_ids):
        raise ValidationError(f"{label}.ordered_prefix_unions must have one value per system")
    prefix_values = [_integer(item, f"{label}.ordered_prefix_unions[{index}]")
                     for index, item in enumerate(prefix)]
    leave_one_out = _check_exact_map(result["leave_one_out_unions"], system_ids,
                                     f"{label}.leave_one_out_unions",
                                     lambda x, name: _integer(x, name))
    return {
        "per_system_catches": catches,
        "union_detection": union,
        "all_miss": all_miss,
        "ordered_prefix_unions": prefix_values,
        "leave_one_out_unions": leave_one_out,
    }


def _benign_metrics(value: Any, denominator: int, label: str,
                    require_metric: bool = False) -> dict[str, Any]:
    result = _mapping(value, label)
    if set(result) == {"status", "reason"}:
        if require_metric:
            raise ValidationError(f"{label} must report benign union burden for complete evidence")
        _unavailable(result, label)
        return {"available": False}
    result = _keys(result, {"union_flags"}, set(), label)
    count = _integer(result["union_flags"], f"{label}.union_flags")
    if count > denominator:
        raise ValidationError(f"{label}.union_flags exceeds benign denominator {denominator}")
    return {"available": True, "union_flags": count}


def _unavailable_metrics(value: Any, label: str) -> None:
    _unavailable(value, label)


def _validate_decision(value: Any, label: str, allowed_codes: set[str]) -> str:
    code = _string(value, label)
    if code not in allowed_codes:
        raise ValidationError(f"{label} uses code {code!r}, which is absent from "
                              "missingness.allowed_codes")
    return code


def _validate_items(value: Any, system_ids: list[str],
                    allowed_codes: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValidationError("evidence.items must be a non-empty list")
    item_ids = set()
    items = []
    for index, raw in enumerate(value):
        item = _keys(raw, {"id", "positive", "decisions"}, set(),
                     f"evidence.items[{index}]")
        item_id = _string(item["id"], f"evidence.items[{index}].id")
        if item_id in item_ids:
            raise ValidationError(f"evidence.items has duplicate id {item_id!r}")
        item_ids.add(item_id)
        positive = _boolean(item["positive"], f"evidence.items[{index}].positive")
        decisions = _check_exact_map(
            item["decisions"], system_ids, f"evidence.items[{index}].decisions",
            lambda code, name: _validate_decision(code, name, allowed_codes),
        )
        items.append({"id": item_id, "positive": positive, "decisions": decisions})
    return items


def _prefix_unions(reference: dict[str, Any]) -> list[int]:
    total = 0
    result = []
    for entry in reference["residual_coverage"]:
        total += entry["catches_among_prior_misses"]
        result.append(total)
    return result


def _check_reported_matches(expected: dict[str, Any], reported: dict[str, Any],
                            label: str) -> None:
    for field in ("per_system_catches", "union_detection", "all_miss",
                  "ordered_prefix_unions", "leave_one_out_unions"):
        if reported[field] != expected[field]:
            raise ValidationError(
                f"{label}.{field} does not match recomputed complete evidence: "
                f"reported {reported[field]!r}, expected {expected[field]!r}")


def _recompute_raw_static(contract: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    system_ids = contract["execution"]["order"]
    population = contract["population"]
    positives = [item["positive"] for item in items]
    if len(items) != population["positive_denominator"] + population["benign_denominator"]:
        raise ValidationError("evidence.items length does not equal positive_denominator + "
                              "benign_denominator")
    if sum(positives) != population["positive_denominator"]:
        raise ValidationError("evidence.items positive labels do not match positive_denominator")
    if len(items) - sum(positives) != population["benign_denominator"]:
        raise ValidationError("evidence.items benign labels do not match benign_denominator")
    decisions = {
        system_id: [item["decisions"][system_id] == "flag" for item in items]
        for system_id in system_ids
    }
    reference = mjgd_reference.joint_disclosure(decisions, positives)
    catch_sets = {
        system_id: {
            index for index, item in enumerate(items)
            if item["positive"] and item["decisions"][system_id] == "flag"
        }
        for system_id in system_ids
    }
    leave_one_out = identification.leave_one_out(catch_sets)
    expected = {
        "per_system_catches": reference["per_guard"],
        "union_detection": reference["union_detection"],
        "all_miss": reference["all_miss"],
        "ordered_prefix_unions": _prefix_unions(reference),
        "leave_one_out_unions": {
            system_id: leave_one_out["per_guard"][system_id]["union_without"]
            for system_id in system_ids
        },
    }
    benign_union = sum(
        any(item["decisions"][system_id] == "flag" for system_id in system_ids)
        for item in items if not item["positive"]
    )
    return {"positive": expected, "benign_union": benign_union}


def _validate_raw(contract: dict[str, Any]) -> dict[str, Any]:
    evidence = _keys(contract["evidence"], {"kind", "items"}, {"manifest"}, "evidence")
    if evidence["kind"] != "per_item_outcomes":
        raise ValidationError("internal error: raw validator called for non-raw evidence")
    if "manifest" in evidence:
        _manifest(evidence["manifest"], "evidence.manifest")
    items = _validate_items(evidence["items"], contract["system_ids"],
                            contract["allowed_codes"])
    non_binary = [
        (item["id"], system_id, item["decisions"][system_id])
        for item in items
        for system_id in contract["system_ids"]
        if item["decisions"][system_id] not in {"flag", "clear"}
    ]
    if non_binary:
        _unavailable_metrics(contract["reported"]["positive"], "reported.positive")
        _unavailable_metrics(contract["reported"]["benign"], "reported.benign")
        return {
            "disclosure_id": contract["disclosure_id"],
            "status": STATUS_HOLD_MISSING,
            "hold_reason": "explicit non-binary decision cell(s) under missingness.policy=hold",
            "missing_cells": [
                {"item_id": item_id, "system_id": system_id, "code": code}
                for item_id, system_id, code in non_binary
            ],
        }
    expected = _recompute_raw_static(contract, items)
    reported = _positive_metrics(contract["reported"]["positive"],
                                 contract["system_ids"], "reported.positive")
    _check_reported_matches(expected["positive"], reported, "reported.positive")
    benign = _benign_metrics(contract["reported"]["benign"],
                             contract["population"]["benign_denominator"],
                             "reported.benign", require_metric=True)
    if benign["union_flags"] != expected["benign_union"]:
        raise ValidationError("reported.benign.union_flags does not match recomputed "
                              f"complete evidence: reported {benign['union_flags']}, "
                              f"expected {expected['benign_union']}")
    return {
        "disclosure_id": contract["disclosure_id"],
        "status": STATUS_RECOMPUTABLE,
        "positive": expected["positive"],
        "benign": {
            "denominator": contract["population"]["benign_denominator"],
            "union_flags": expected["benign_union"],
        },
    }


def _aggregate_pattern_counts(value: Any, order: list[str], denominator: int) -> dict[str, int]:
    """Validate a complete item-membership count table in declared route order.

    Pattern key 010 means only the second system in execution.order flagged
    those items. The zero pattern is mandatory, so no omitted key can quietly
    become an all-miss count.
    """
    result = _mapping(value, "evidence.joint_pattern_counts")
    width = len(order)
    expected = {format(number, f"0{width}b") for number in range(2 ** width)}
    if set(result) != expected:
        missing = expected - set(result)
        extra = set(result) - expected
        parts = []
        if missing:
            parts.append("missing " + ", ".join(sorted(missing)))
        if extra:
            parts.append("unknown " + ", ".join(sorted(extra)))
        raise ValidationError("evidence.joint_pattern_counts must include every "
                              f"{width}-bit membership pattern ({'; '.join(parts)})")
    counts = {
        pattern: _integer(result[pattern], f"evidence.joint_pattern_counts.{pattern}")
        for pattern in sorted(expected)
    }
    if sum(counts.values()) != denominator:
        raise ValidationError("evidence.joint_pattern_counts must sum to "
                              "population.positive_denominator")
    return counts


def _metrics_from_patterns(patterns: dict[str, int], order: list[str]) -> dict[str, Any]:
    width = len(order)
    per_system = {
        system_id: sum(count for pattern, count in patterns.items() if pattern[index] == "1")
        for index, system_id in enumerate(order)
    }
    union = sum(count for pattern, count in patterns.items() if "1" in pattern)
    prefixes = [
        sum(count for pattern, count in patterns.items() if "1" in pattern[:index + 1])
        for index in range(width)
    ]
    leave_one_out = {
        system_id: sum(
            count for pattern, count in patterns.items()
            if any(bit == "1" for position, bit in enumerate(pattern) if position != index)
        )
        for index, system_id in enumerate(order)
    }
    return {
        "per_system_catches": per_system,
        "union_detection": union,
        "all_miss": patterns["0" * width],
        "ordered_prefix_unions": prefixes,
        "leave_one_out_unions": leave_one_out,
    }


def _validate_aggregate_static(contract: dict[str, Any]) -> dict[str, Any]:
    evidence = _keys(
        contract["evidence"],
        {"kind", "manifest", "per_system_catches", "joint_pattern_counts"},
        set(),
        "evidence",
    )
    if evidence["kind"] != "sufficient_aggregates":
        raise ValidationError("internal error: aggregate validator called for other evidence")
    _manifest(evidence["manifest"], "evidence.manifest")
    order = contract["execution"]["order"]
    patterns = _aggregate_pattern_counts(
        evidence["joint_pattern_counts"], order,
        contract["population"]["positive_denominator"],
    )
    expected = _metrics_from_patterns(patterns, order)
    evidence_counts = _check_exact_map(
        evidence["per_system_catches"], contract["system_ids"],
        "evidence.per_system_catches", lambda x, name: _integer(x, name),
    )
    if evidence_counts != expected["per_system_catches"]:
        raise ValidationError("evidence.per_system_catches does not match the "
                              "complete aggregate pattern table")
    reported = _positive_metrics(contract["reported"]["positive"],
                                 contract["system_ids"], "reported.positive")
    _check_reported_matches(expected, reported, "reported.positive")
    _unavailable_metrics(contract["reported"]["benign"], "reported.benign")
    result = {
        "disclosure_id": contract["disclosure_id"],
        "status": STATUS_AGGREGATE_PATTERNS,
        "positive": expected,
    }
    return result


def _validate_marginals(contract: dict[str, Any]) -> dict[str, Any]:
    evidence = _keys(contract["evidence"], {"kind", "manifest", "per_system_catches"},
                     set(), "evidence")
    if evidence["kind"] != "marginals_only":
        raise ValidationError("internal error: marginal validator called for other evidence")
    _manifest(evidence["manifest"], "evidence.manifest")
    counts = _check_exact_map(evidence["per_system_catches"], contract["system_ids"],
                              "evidence.per_system_catches",
                              lambda x, name: _integer(x, name))
    n = contract["population"]["positive_denominator"]
    ordered_counts = []
    for system_id in contract["system_ids"]:
        if counts[system_id] > n:
            raise ValidationError(f"evidence.per_system_catches.{system_id} exceeds denominator")
        ordered_counts.append(counts[system_id])
    _unavailable_metrics(contract["reported"]["positive"], "reported.positive")
    _unavailable_metrics(contract["reported"]["benign"], "reported.benign")
    identified = identification.integer_grid(ordered_counts, n)
    return {
        "disclosure_id": contract["disclosure_id"],
        "status": STATUS_NOT_IDENTIFIED,
        "positive_all_miss_identified_set": identified,
        "positive_all_miss_interval": [identified[0], identified[-1]],
    }


def _validate_route(contract: dict[str, Any]) -> dict[str, Any]:
    evidence = _keys(contract["evidence"], {"kind", "manifest"}, set(), "evidence")
    if evidence["kind"] != "route_trace":
        raise ValidationError("route or gate evidence must use evidence.kind='route_trace'")
    _manifest(evidence["manifest"], "evidence.manifest")
    _unavailable_metrics(contract["reported"]["positive"], "reported.positive")
    _unavailable_metrics(contract["reported"]["benign"], "reported.benign")
    return {
        "disclosure_id": contract["disclosure_id"],
        "status": STATUS_HOLD_ROUTE,
        "hold_reason": "route or gate trace is not reduced to static full-exposure arithmetic",
    }


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Return the evidence status or raise ValidationError on an invalid packet."""
    contract = _validate_packet_contract(packet)
    mode = contract["execution"]["mode"]
    kind = contract["evidence"].get("kind")
    if not isinstance(kind, str):
        raise ValidationError("evidence.kind must be a string")
    if mode in ROUTE_MODES:
        return _validate_route(contract)
    if mode != STATIC_MODE:
        raise ValidationError("unsupported execution mode")
    if kind == "per_item_outcomes":
        return _validate_raw(contract)
    if kind == "sufficient_aggregates":
        return _validate_aggregate_static(contract)
    if kind == "marginals_only":
        return _validate_marginals(contract)
    if kind == "route_trace":
        raise ValidationError("route_trace evidence requires a route or gate execution mode")
    raise ValidationError("evidence.kind must be per_item_outcomes, sufficient_aggregates, "
                          "marginals_only, or route_trace")


def validate_path(path: Path) -> dict[str, Any]:
    """Public entry point used by the generated disclosure page."""
    return validate_packet(load_packet(path))


FIXTURE_EXPECTATIONS = {
    "parallel-full-exposure.json": STATUS_RECOMPUTABLE,
    "sequential-route.json": STATUS_HOLD_ROUTE,
    "partial-release.json": STATUS_AGGREGATE_PATTERNS,
    "aggregate-only.json": STATUS_NOT_IDENTIFIED,
    "missing-data.json": STATUS_HOLD_MISSING,
}


def validate_fixtures() -> list[tuple[Path, dict[str, Any]]]:
    results = []
    for filename, expected_status in FIXTURE_EXPECTATIONS.items():
        path = FIXTURE_DIR / filename
        result = validate_path(path)
        if result["status"] != expected_status:
            raise ValidationError(f"{path}: got status {result['status']}, "
                                  f"expected {expected_status}")
        results.append((path, result))
    return results


def _expect_refusal(packet: dict[str, Any], label: str) -> None:
    try:
        validate_packet(packet)
    except ValidationError:
        print(f"ok    refuses {label}")
    else:
        raise ValidationError(f"self-test expected refusal: {label}")


def run_self_test() -> int:
    failures = 0

    def check(action, label: str) -> None:
        nonlocal failures
        try:
            action()
        except (ValidationError, OSError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"FAIL  {label}: {exc}")
        else:
            print(f"ok    {label}")

    check(lambda: json.load(SCHEMA_PATH.open(encoding="utf-8")),
          "schema is valid JSON")
    check(lambda: validate_fixtures(), "five conformance fixtures validate with expected states")

    try:
        json.loads('{"same": 1, "same": 2}', object_pairs_hook=_no_duplicate_keys)
    except ValidationError:
        print("ok    refuses duplicate JSON keys")
    else:
        failures += 1
        print("FAIL  refuses duplicate JSON keys")

    raw = load_packet(FIXTURE_DIR / "parallel-full-exposure.json")
    bad_schema = copy.deepcopy(raw)
    bad_schema["schema_version"] = "mjgd/v0"
    _expect_refusal(bad_schema, "an unsupported schema version")

    unknown_root = copy.deepcopy(raw)
    unknown_root["unreviewed_extra"] = "must not be silently ignored"
    _expect_refusal(unknown_root, "an unknown packet field")

    tampered_union = copy.deepcopy(raw)
    tampered_union["reported"]["positive"]["union_detection"] = 4
    _expect_refusal(tampered_union, "a tampered complete-evidence union")

    ordered = copy.deepcopy(raw)
    ordered["execution"]["order"] = ["b", "a"]
    ordered["evidence"]["items"][1]["decisions"]["a"] = "clear"
    ordered["reported"]["positive"] = {
        "per_system_catches": {"a": 1, "b": 2},
        "union_detection": 2,
        "all_miss": 2,
        "ordered_prefix_unions": [2, 2],
        "leave_one_out_unions": {"a": 2, "b": 1},
    }

    def check_declared_order() -> None:
        result = validate_packet(ordered)
        if result["positive"]["ordered_prefix_unions"] != [2, 2]:
            raise ValidationError("declared execution order did not define prefix attribution")

    check(check_declared_order, "declared execution order controls raw prefix unions")
    wrong_ordered_prefix = copy.deepcopy(ordered)
    wrong_ordered_prefix["reported"]["positive"]["ordered_prefix_unions"] = [1, 2]
    _expect_refusal(wrong_ordered_prefix, "a raw prefix reported in systems-list order")

    aggregate = load_packet(FIXTURE_DIR / "partial-release.json")
    aggregate_wrong_leave_one_out = copy.deepcopy(aggregate)
    aggregate_wrong_leave_one_out["reported"]["positive"]["leave_one_out_unions"]["a"] = 1
    _expect_refusal(aggregate_wrong_leave_one_out,
                    "an aggregate leave-one-out inconsistent with pattern counts")
    aggregate_missing_pattern = copy.deepcopy(aggregate)
    del aggregate_missing_pattern["evidence"]["joint_pattern_counts"]["00"]
    _expect_refusal(aggregate_missing_pattern,
                    "an aggregate pattern table with an omitted zero pattern")
    aggregate_with_unrecomputed_benign = copy.deepcopy(aggregate)
    aggregate_with_unrecomputed_benign["population"]["benign_denominator"] = 7
    aggregate_with_unrecomputed_benign["reported"]["benign"] = {"union_flags": 6}
    _expect_refusal(aggregate_with_unrecomputed_benign,
                    "an unrecomputed benign union in an aggregate-pattern packet")

    marginal = load_packet(FIXTURE_DIR / "aggregate-only.json")
    marginal_with_observed = copy.deepcopy(marginal)
    marginal_with_observed["reported"]["positive"] = copy.deepcopy(raw["reported"]["positive"])
    _expect_refusal(marginal_with_observed, "an observed static result from marginals only")

    route = load_packet(FIXTURE_DIR / "sequential-route.json")
    route_with_static = copy.deepcopy(route)
    route_with_static["reported"]["positive"] = copy.deepcopy(raw["reported"]["positive"])
    _expect_refusal(route_with_static, "a static result inserted into route evidence")
    route_with_benign = copy.deepcopy(route)
    route_with_benign["reported"]["benign"] = {"union_flags": 0}
    _expect_refusal(route_with_benign, "a benign result inserted into held route evidence")

    missing_cell = copy.deepcopy(raw)
    del missing_cell["evidence"]["items"][0]["decisions"]["b"]
    _expect_refusal(missing_cell, "an omitted item-system decision cell")

    missing = load_packet(FIXTURE_DIR / "missing-data.json")
    missing_with_benign = copy.deepcopy(missing)
    missing_with_benign["reported"]["benign"] = {"union_flags": 0}
    _expect_refusal(missing_with_benign, "a benign result inserted into held missing data")

    duplicate_system = copy.deepcopy(raw)
    duplicate_system["systems"][1]["id"] = "a"
    _expect_refusal(duplicate_system, "a duplicate system id")

    print()
    if failures:
        print(f"{failures} MJGD v1 self-test(s) failed.")
        return 1
    print("MJGD v1 validator verified: complete, aggregate, marginal, route, and hold states.")
    return 0


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"{result['status']}  {result['disclosure_id']}")
    if "positive_all_miss_interval" in result:
        lo, hi = result["positive_all_miss_interval"]
        print(f"  static all-miss identified set: {lo}..{hi}")
    if "hold_reason" in result:
        print(f"  hold: {result['hold_reason']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate one MJGD v1 disclosure packet without reimplementing its arithmetic.")
    parser.add_argument("path", nargs="?", type=Path,
                        help="MJGD v1 JSON packet to validate")
    parser.add_argument("--fixtures", action="store_true",
                        help="validate and print every committed conformance fixture")
    parser.add_argument("--json", action="store_true",
                        help="emit the validation result as JSON (requires one path)")
    parser.add_argument("--test", action="store_true",
                        help="run fixture conformance and refusal tests")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.test:
        if args.path or args.fixtures or args.json:
            raise ValidationError("--test cannot be combined with a path, --fixtures, or --json")
        return run_self_test()
    if args.fixtures:
        if args.path or args.json:
            raise ValidationError("--fixtures cannot be combined with a path or --json")
        for path, result in validate_fixtures():
            print(f"ok    {path.relative_to(ROOT)}: {result['status']}")
        return 0
    if args.path is None:
        raise ValidationError("supply a packet path, --fixtures, or --test")
    result = validate_path(args.path)
    _print_result(result, args.json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        raise SystemExit(1)
