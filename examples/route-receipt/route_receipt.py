#!/usr/bin/env python3
"""Validate a small, item-level receipt for one declared evaluation route.

This is intentionally separate from MJGD v1. MJGD v1 holds routes because it
validates static full-exposure evidence; this program checks the declared
route action in a submitted trace instead. It prints terminal-event outcomes
only when the receipt names a source-defined terminal event.

A structural pass does not authenticate citations, hashes named for remote
files, or the assertion that a trace was collected directly. Those remain
declared attestations. A post-hoc static reconstruction is deliberately held:
it is useful provenance, but not a direct-route result.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re
import sys
from collections import Counter, defaultdict
from typing import Any


SCHEMA = "route-receipt/v1"
PLACEHOLDERS = {"", "default", "unknown", "n/a", "na", "vendor_default"}
DECISIONS = {"flag", "clear", "timeout", "error", "not_exposed"}
ACTIONS = {"block", "allow", "hold"}
TERMINALS = {"occurred", "not_occurred", "not_observed"}
ORIGINS = {"direct_route_trace", "derived_static_reconstruction"}
TOPOLOGIES = {"parallel_block_on_any", "sequential_stop_on_flag"}


class ReceiptError(ValueError):
    """The input does not meet the deliberately narrow receipt contract."""


def require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReceiptError(f"{name} must be an object")
    return value


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptError(f"{name} must be a nonempty string")
    return value.strip()


def declared_string(value: Any, name: str) -> str:
    result = require_string(value, name)
    if result.lower() in PLACEHOLDERS:
        raise ReceiptError(f"{name} cannot be a placeholder")
    return result


def exact_keys(value: Any, required: set[str], name: str) -> dict[str, Any]:
    result = require_mapping(value, name)
    actual = set(result)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unknown " + ", ".join(extra))
        raise ReceiptError(f"{name} has " + "; ".join(details))
    return result


def sha256(path: pathlib.Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReceiptError(f"cannot read {path}: {exc}") from exc
    return hashlib.sha256(raw).hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def decode_json(raw: str, name: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=strict_object)
    except ReceiptError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ReceiptError(f"{name} is not JSON: {exc}") from exc


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReceiptError(f"cannot read {path}: {exc}") from exc
    value = decode_json(raw, str(path))
    return require_mapping(value, str(path))


def safe_relative_path(value: Any, manifest_path: pathlib.Path) -> pathlib.Path:
    rel = require_string(value, "outcomes.path")
    candidate = pathlib.Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ReceiptError("outcomes.path must stay below the manifest directory")
    resolved = (manifest_path.parent / candidate).resolve()
    try:
        resolved.relative_to(manifest_path.parent.resolve())
    except ValueError as exc:
        raise ReceiptError("outcomes.path escapes the manifest directory") from exc
    return resolved


def operating_point(value: Any, name: str) -> None:
    point = exact_keys(value, {"kind", "value", "source"}, name)
    kind = require_string(point["kind"], f"{name}.kind")
    source = declared_string(point["source"], f"{name}.source")
    if kind == "numeric_threshold":
        numeric = point["value"]
        if (isinstance(numeric, bool) or not isinstance(numeric, (int, float))
                or not math.isfinite(numeric)):
            raise ReceiptError(f"{name}.value must be a finite number for numeric_threshold")
    elif kind == "native_categorical":
        declared_string(point["value"], f"{name}.value")
    else:
        raise ReceiptError(f"{name}.kind must be numeric_threshold or native_categorical")
    if source.lower() in PLACEHOLDERS:
        raise ReceiptError(f"{name}.source cannot be a placeholder")


def validate_routes(value: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(value, list) or not value:
        raise ReceiptError("routes must be a nonempty array")
    by_id: dict[str, dict[str, Any]] = {}
    by_key: dict[str, dict[str, Any]] = {}
    route_fields = {
        "id", "route_key", "topology", "policy_source", "nondecision_policy", "stages"
    }
    stage_fields = {"id", "system", "version", "decision_rule", "operating_point"}
    for index, raw in enumerate(value):
        route = exact_keys(raw, route_fields, f"routes[{index}]")
        route_id = require_string(route["id"], f"routes[{index}].id")
        route_key = require_string(route["route_key"], f"routes[{index}].route_key")
        if route_id in by_id or route_key in by_key:
            raise ReceiptError("route ids and route keys must each be unique")
        topology = require_string(route["topology"], f"routes[{index}].topology")
        if topology not in TOPOLOGIES:
            raise ReceiptError(f"routes[{index}].topology is unsupported")
        declared_string(route["policy_source"], f"routes[{index}].policy_source")
        policy = exact_keys(
            route["nondecision_policy"], {"timeout", "error"},
            f"routes[{index}].nondecision_policy",
        )
        if any(require_string(policy[key], f"routes[{index}].nondecision_policy.{key}")
               not in ACTIONS for key in ("timeout", "error")):
            raise ReceiptError(f"routes[{index}].nondecision_policy has an invalid action")
        stages = route["stages"]
        if not isinstance(stages, list) or not stages:
            raise ReceiptError(f"routes[{index}].stages must be a nonempty array")
        stage_ids: set[str] = set()
        for stage_index, raw_stage in enumerate(stages):
            stage = exact_keys(raw_stage, stage_fields, f"routes[{index}].stages[{stage_index}]")
            stage_id = require_string(stage["id"], f"routes[{index}].stages[{stage_index}].id")
            if stage_id in stage_ids:
                raise ReceiptError(f"routes[{index}] has duplicate stage id {stage_id!r}")
            stage_ids.add(stage_id)
            declared_string(stage["system"], f"routes[{index}].stages[{stage_index}].system")
            declared_string(stage["version"], f"routes[{index}].stages[{stage_index}].version")
            declared_string(
                stage["decision_rule"], f"routes[{index}].stages[{stage_index}].decision_rule"
            )
            operating_point(
                stage["operating_point"], f"routes[{index}].stages[{stage_index}].operating_point"
            )
        by_id[route_id] = route
        by_key[route_key] = route
    return by_id, by_key


def validate_population(value: Any, routes_by_key: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    population = exact_keys(
        value, {"label_definition", "label_source", "id_scheme", "strata"}, "population"
    )
    for key in ("label_definition", "label_source", "id_scheme"):
        declared_string(population[key], f"population.{key}")
    strata = population["strata"]
    if not isinstance(strata, list) or not strata:
        raise ReceiptError("population.strata must be a nonempty array")
    result: dict[str, dict[str, Any]] = {}
    item_ids: set[str] = set()
    for index, raw in enumerate(strata):
        stratum = exact_keys(raw, {"id", "role", "route_key", "item_ids"},
                             f"population.strata[{index}]")
        stratum_id = require_string(stratum["id"], f"population.strata[{index}].id")
        if stratum_id in result:
            raise ReceiptError(f"duplicate stratum id {stratum_id!r}")
        role = require_string(stratum["role"], f"population.strata[{index}].role")
        if role not in {"positive", "benign"}:
            raise ReceiptError(f"population.strata[{index}].role must be positive or benign")
        route_key = require_string(
            stratum["route_key"], f"population.strata[{index}].route_key"
        )
        if route_key not in routes_by_key:
            raise ReceiptError(f"population.strata[{index}] names unknown route_key {route_key!r}")
        ids = stratum["item_ids"]
        if not isinstance(ids, list) or not ids:
            raise ReceiptError(f"population.strata[{index}].item_ids must be a nonempty array")
        local_ids: set[str] = set()
        for item_id in ids:
            normalized = require_string(item_id, f"population.strata[{index}].item_ids")
            if normalized in local_ids or normalized in item_ids:
                raise ReceiptError(f"item id {normalized!r} is not uniquely assigned to one stratum")
            local_ids.add(normalized)
            item_ids.add(normalized)
        result[stratum_id] = stratum
    return result


def validate_terminal_event(value: Any) -> dict[str, Any]:
    event = require_mapping(value, "terminal_event")
    status = event.get("status")
    if status == "not_available":
        exact_keys(event, {"status"}, "terminal_event")
    elif status == "source_defined":
        event = exact_keys(event, {"status", "name", "definition", "source"}, "terminal_event")
        for key in ("name", "definition", "source"):
            declared_string(event[key], f"terminal_event.{key}")
    else:
        raise ReceiptError("terminal_event.status must be source_defined or not_available")
    return event


def expected_action(route: dict[str, Any], decisions: dict[str, str], name: str) -> str:
    stages = route["stages"]
    ids = [stage["id"] for stage in stages]
    if set(decisions) != set(ids):
        raise ReceiptError(f"{name}.stage_decisions must name every declared stage exactly once")
    if any(value not in DECISIONS for value in decisions.values()):
        raise ReceiptError(f"{name}.stage_decisions contains an unsupported state")
    topology = route["topology"]
    nondecision_policy = route["nondecision_policy"]
    if topology == "parallel_block_on_any":
        states = [decisions[stage_id] for stage_id in ids]
        if "not_exposed" in states:
            raise ReceiptError(f"{name}: parallel route cannot contain not_exposed")
        nondecisions = [state for state in states if state in {"timeout", "error"}]
        if nondecisions:
            if len(nondecisions) != len(states):
                raise ReceiptError(f"{name}: a parallel nondecision cannot be mixed with flag/clear")
            actions = {nondecision_policy[state] for state in nondecisions}
            if len(actions) != 1:
                raise ReceiptError(f"{name}: parallel nondecisions map to incompatible actions")
            return actions.pop()
        return "block" if "flag" in states else "allow"

    stopped = False
    terminal: str | None = None
    for stage_id in ids:
        state = decisions[stage_id]
        if stopped:
            if state != "not_exposed":
                raise ReceiptError(f"{name}: sequential route exposes a stage after it terminated")
            continue
        if state == "clear":
            continue
        if state == "not_exposed":
            raise ReceiptError(f"{name}: sequential route cannot begin not_exposed")
        stopped = True
        terminal = "block" if state == "flag" else nondecision_policy[state]
    return terminal or "allow"


def load_outcomes(
    path: pathlib.Path,
    expected_hash: str,
    strata: dict[str, dict[str, Any]],
    routes_by_id: dict[str, dict[str, Any]],
    terminal_event: dict[str, Any],
) -> dict[tuple[str, str], Counter[str]]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ReceiptError("outcomes.sha256 must be a lowercase SHA-256 digest")
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise ReceiptError(
            f"outcomes hash mismatch: {actual_hash[:16]}… != {expected_hash[:16]}…"
        )
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReceiptError(f"cannot read outcome rows: {exc}") from exc
    if not lines:
        raise ReceiptError("route-outcomes JSONL is empty")
    declared_items = {
        item_id for stratum in strata.values() for item_id in stratum["item_ids"]
    }
    seen: set[str] = set()
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    fields = {"item_id", "stratum_id", "route_id", "stage_decisions",
              "terminal_action", "terminal_event"}
    for line_no, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            raise ReceiptError(f"route-outcomes line {line_no} is blank")
        row = exact_keys(decode_json(raw_line, f"route-outcomes line {line_no}"),
                         fields, f"route-outcomes line {line_no}")
        item_id = require_string(row["item_id"], f"route-outcomes line {line_no}.item_id")
        if item_id in seen:
            raise ReceiptError(f"route-outcomes duplicates item id {item_id!r}")
        seen.add(item_id)
        if item_id not in declared_items:
            raise ReceiptError(f"route-outcomes names undeclared item id {item_id!r}")
        stratum_id = require_string(row["stratum_id"], f"route-outcomes line {line_no}.stratum_id")
        if stratum_id not in strata or item_id not in strata[stratum_id]["item_ids"]:
            raise ReceiptError(f"route-outcomes item {item_id!r} does not belong to stratum {stratum_id!r}")
        route_id = require_string(row["route_id"], f"route-outcomes line {line_no}.route_id")
        if route_id not in routes_by_id:
            raise ReceiptError(f"route-outcomes names unknown route {route_id!r}")
        route = routes_by_id[route_id]
        if route["route_key"] != strata[stratum_id]["route_key"]:
            raise ReceiptError(f"route-outcomes route does not match {stratum_id!r}'s declared route key")
        decisions = require_mapping(
            row["stage_decisions"], f"route-outcomes line {line_no}.stage_decisions"
        )
        normalized = {
            require_string(stage_id, f"route-outcomes line {line_no}.stage_decisions key"):
            require_string(state, f"route-outcomes line {line_no}.stage_decisions.{stage_id}")
            for stage_id, state in decisions.items()
        }
        action = require_string(
            row["terminal_action"], f"route-outcomes line {line_no}.terminal_action"
        )
        if action not in ACTIONS:
            raise ReceiptError(f"route-outcomes line {line_no}.terminal_action is unsupported")
        expected = expected_action(route, normalized, f"route-outcomes line {line_no}")
        if action != expected:
            raise ReceiptError(
                f"route-outcomes line {line_no}.terminal_action={action!r}, "
                f"but declared route implies {expected!r}"
            )
        terminal = require_string(
            row["terminal_event"], f"route-outcomes line {line_no}.terminal_event"
        )
        if terminal not in TERMINALS:
            raise ReceiptError(f"route-outcomes line {line_no}.terminal_event is unsupported")
        role = strata[stratum_id]["role"]
        if terminal_event["status"] == "not_available":
            if terminal != "not_observed":
                raise ReceiptError("terminal_event is not_available, so every row must say not_observed")
        elif role == "benign":
            if terminal != "not_observed":
                raise ReceiptError("benign rows must not be relabelled as terminal-event outcomes")
        elif action in {"block", "hold"}:
            if terminal != "not_observed":
                raise ReceiptError(
                    "a blocked or held route action cannot claim an observed terminal event"
                )
        elif terminal not in {"occurred", "not_occurred"}:
            raise ReceiptError("positive direct route rows require an observed terminal event")
        key = (route_id, stratum_id)
        counts[key][action] += 1
        counts[key][terminal] += 1
    if seen != declared_items:
        missing = sorted(declared_items - seen)
        extra = sorted(seen - declared_items)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unknown " + ", ".join(extra))
        raise ReceiptError("route-outcomes item universe differs from manifest: " + "; ".join(details))
    return counts


def validate(path: pathlib.Path) -> tuple[dict[str, Any], dict[tuple[str, str], Counter[str]]]:
    packet = exact_keys(
        load_json(path),
        {"schema_version", "receipt_id", "observed_at", "execution", "population",
         "terminal_event", "routes", "outcomes"},
        "route receipt",
    )
    if packet["schema_version"] != SCHEMA:
        raise ReceiptError(f"schema_version must be {SCHEMA!r}")
    require_string(packet["receipt_id"], "receipt_id")
    require_string(packet["observed_at"], "observed_at")
    execution = exact_keys(
        packet["execution"],
        {"kind", "evidence_origin", "route_declaration_source", "trace_generation_source",
         "code_ref", "config_sha256"},
        "execution",
    )
    kind = require_string(execution["kind"], "execution.kind")
    if kind not in {"evaluation_route", "production_route"}:
        raise ReceiptError("execution.kind must be evaluation_route or production_route")
    origin = require_string(execution["evidence_origin"], "execution.evidence_origin")
    if origin not in ORIGINS:
        raise ReceiptError("execution.evidence_origin is unsupported")
    for key in ("route_declaration_source", "trace_generation_source", "code_ref"):
        declared_string(execution[key], f"execution.{key}")
    if not re.fullmatch(r"[0-9a-f]{64}", declared_string(
            execution["config_sha256"], "execution.config_sha256")):
        raise ReceiptError("execution.config_sha256 must be a lowercase SHA-256 digest")
    routes_by_id, routes_by_key = validate_routes(packet["routes"])
    strata = validate_population(packet["population"], routes_by_key)
    terminal_event = validate_terminal_event(packet["terminal_event"])
    outcomes = exact_keys(packet["outcomes"], {"path", "sha256"}, "outcomes")
    outcome_path = safe_relative_path(outcomes["path"], path)
    counts = load_outcomes(
        outcome_path,
        require_string(outcomes["sha256"], "outcomes.sha256"),
        strata,
        routes_by_id,
        terminal_event,
    )
    return {
        "packet": packet,
        "execution": execution,
        "strata": strata,
        "routes_by_id": routes_by_id,
        "terminal_event": terminal_event,
    }, counts


def print_summary(contract: dict[str, Any], counts: dict[tuple[str, str], Counter[str]]) -> int:
    execution = contract["execution"]
    if execution["evidence_origin"] != "direct_route_trace":
        print("HOLD: derived_static_reconstruction is not a declared direct route trace")
        print("No route action or terminal-event metric is emitted.")
        return 1
    print(f"STRUCTURALLY VALID {SCHEMA}: declared direct route trace")
    print("Directness and cited sources are declared attestations, not independently authenticated.")
    for stratum_id, stratum in contract["strata"].items():
        route = next(
            route for route in contract["routes_by_id"].values()
            if route["route_key"] == stratum["route_key"]
        )
        current = counts[(route["id"], stratum_id)]
        n = len(stratum["item_ids"])
        action_text = (
            f"blocked {current['block']}/{n}; allowed {current['allow']}/{n}; "
            f"held {current['hold']}/{n}"
        )
        if (contract["terminal_event"]["status"] == "source_defined"
                and stratum["role"] == "positive"):
            action_text += (
                f"; terminal event occurred {current['occurred']}/{n}; "
                f"not occurred {current['not_occurred']}/{n}; "
                f"not observed {current['not_observed']}/{n}"
            )
        elif stratum["role"] == "benign":
            action_text += "; benign blocks are route actions, not a safety outcome"
        print(f"{route['id']} / {stratum_id} ({stratum['role']}): {action_text}")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("INVALID: expected one route-receipt.json path")
        return 1
    try:
        contract, counts = validate(pathlib.Path(sys.argv[1]).resolve())
    except ReceiptError as exc:
        print(f"INVALID: {exc}")
        return 1
    return print_summary(contract, counts)


if __name__ == "__main__":
    raise SystemExit(main())
