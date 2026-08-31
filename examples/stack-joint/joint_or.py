#!/usr/bin/env python3
"""Print a static-OR receipt only for a complete declared tuple.

A passing run establishes structural completeness of declarations and rows; it
does not independently validate the source quotations behind those declarations.
"""
import csv
import pathlib
import sys

FIELDS = ("item_id", "system_id", "decision", "item_set", "threshold", "exposure")
REQUIRED = ("event", "event_source", "event_translation", "event_translation_source",
            "item_set", "item_ids", "item_count", "systems", "operator",
            "composition", "exposure", "threshold_rule", "threshold_source",
            "missingness", "label_source", "adaptive")
EXACT = {"operator": "static_or", "composition": "counterfactual_static",
         "exposure": "declared_full", "threshold_rule": "fixed_per_system",
         "missingness": "none", "adaptive": "untested"}
EVENT_TRANSLATIONS = {"shared_source_defined", "translation_declared"}
PLACEHOLDERS = {"", "default", "vendor_default", "matched", "unknown", "na", "n/a"}


def unknown(reason):
    print(f"UNKNOWN: {reason}")
    raise SystemExit(1)


def manifest(value, name):
    values = [x.strip() for x in value.split(",")]
    if not values or any(not x for x in values) or len(set(values)) != len(values):
        unknown(f"invalid {name} manifest")
    return values


if len(sys.argv) != 2:
    unknown("input CSV")
try:
    lines = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
except OSError:
    unknown("unreadable input CSV")

meta = {}
for line in lines:
    if line.startswith("#") and ":" in line:
        key, value = line[1:].split(":", 1)
        key, value = key.strip(), value.strip()
        if key in meta:
            unknown(f"duplicate header {key}")
        meta[key] = value
if any(not meta.get(key) for key in REQUIRED):
    unknown("missing header field")
if any(meta[key] != value for key, value in EXACT.items()):
    unknown("unsupported tuple declaration")
if meta["event_translation"] not in EVENT_TRANSLATIONS:
    unknown("event is not a declared shared contract")
items, systems = manifest(meta["item_ids"], "item"), manifest(meta["systems"], "system")
try:
    if int(meta["item_count"]) != len(items) or int(meta["item_count"]) < 1:
        unknown("item_count disagrees with item manifest")
except ValueError:
    unknown("invalid item_count")
try:
    reader = csv.DictReader(line for line in lines if not line.startswith("#"))
    rows = list(reader)
except (csv.Error, UnicodeError):
    unknown("invalid CSV")
if reader.fieldnames != list(FIELDS) or not rows:
    unknown("CSV header or rows")
if any(None in row or any(not (row.get(key) or "").strip() for key in FIELDS) for row in rows):
    unknown("missing or extra CSV field")
for row in rows:
    for key in FIELDS:
        row[key] = row[key].strip()
if any(row["decision"] not in {"0", "1"} for row in rows):
    unknown("nonbinary decision")
if any(row["item_set"] != meta["item_set"] or row["exposure"] != meta["exposure"] for row in rows):
    unknown("row disagrees with declared tuple")
if {row["item_id"] for row in rows} != set(items) or {row["system_id"] for row in rows} != set(systems):
    unknown("row universe disagrees with manifest")
if any(len({row["threshold"] for row in rows if row["system_id"] == system}) != 1
       or next(iter({row["threshold"] for row in rows if row["system_id"] == system})).lower() in PLACEHOLDERS
       for system in systems):
    unknown("invalid or varying threshold")
D = {(row["item_id"], row["system_id"]): int(row["decision"]) for row in rows}
if len(D) != len(rows) or len(D) != len(items) * len(systems):
    unknown("incomplete or duplicate item×system matrix")
union = sum(max(D[item, system] for system in systems) for item in items)
all_miss = sum(min(1 - D[item, system] for system in systems) for item in items)
print(f"n={len(items)}\nunion={union}/{len(items)} = {union/len(items):.12g}\nall_miss={all_miss}/{len(items)} = {all_miss/len(items):.12g}")
