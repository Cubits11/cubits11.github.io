#!/usr/bin/env python3
"""Adversarial checks for the portable route-receipt stub."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile


HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "route_receipt.py"
FIXTURE = HERE / "fixture-receipt.json"
ROWS = HERE / "fixture-outcomes.jsonl"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(receipt: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(receipt)],
        text=True,
        capture_output=True,
        check=False,
    )


def write_packet(directory: pathlib.Path, packet: dict, rows: list[dict]) -> pathlib.Path:
    row_path = directory / "fixture-outcomes.jsonl"
    row_path.write_text("".join(
        json.dumps(row, separators=(",", ":")) + "\n" for row in rows
    ))
    packet["outcomes"]["path"] = row_path.name
    packet["outcomes"]["sha256"] = digest(row_path)
    receipt = directory / "fixture-receipt.json"
    receipt.write_text(json.dumps(packet, indent=2) + "\n")
    return receipt


def expect(label: str, receipt: pathlib.Path, code: int, phrase: str) -> None:
    got = run(receipt)
    if got.returncode != code or phrase not in got.stdout:
        raise SystemExit(
            f"{label}: expected code {code} and {phrase!r}; got {got.returncode}\n"
            f"stdout:\n{got.stdout}\nstderr:\n{got.stderr}"
        )
    print(f"ok    {label}")


packet = json.loads(FIXTURE.read_text())
rows = [json.loads(line) for line in ROWS.read_text().splitlines()]

expect("illustrative static reconstruction is held", FIXTURE, 1,
       "HOLD: derived_static_reconstruction")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["execution"]["evidence_origin"] = "direct_route_trace"
    expect("declared direct parallel trace", write_packet(work, altered, rows), 0,
           "STRUCTURALLY VALID route-receipt/v1: declared direct route trace")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["execution"]["evidence_origin"] = "derived_static_reconstruction"
    expect("derived static reconstruction is held",
           write_packet(work, altered, rows), 1, "HOLD: derived_static_reconstruction")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["outcomes"]["sha256"] = "f" * 64
    receipt = work / "fixture-receipt.json"
    receipt.write_text(json.dumps(altered, indent=2) + "\n")
    (work / "fixture-outcomes.jsonl").write_bytes(ROWS.read_bytes())
    expect("row hash mismatch", receipt, 1, "outcomes hash mismatch")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    raw_rows = ROWS.read_text().replace(
        '{"item_id":', '{"item_id":"shadow","item_id":', 1
    )
    row_path = work / "fixture-outcomes.jsonl"
    row_path.write_text(raw_rows)
    altered["outcomes"]["path"] = row_path.name
    altered["outcomes"]["sha256"] = digest(row_path)
    receipt = work / "fixture-receipt.json"
    receipt.write_text(json.dumps(altered, indent=2) + "\n")
    expect("duplicate JSON field", receipt, 1, "duplicate JSON key")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["routes"][0]["stages"][0]["operating_point"]["value"] = "default"
    expect("default operating point", write_packet(work, altered, rows), 1,
           "cannot be a placeholder")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["routes"][1]["stages"][1]["operating_point"]["value"] = float("nan")
    expect("nonfinite threshold", write_packet(work, altered, rows), 1,
           "must be a finite number")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered_rows = [dict(row) for row in rows]
    altered_rows[0]["terminal_action"] = "allow"
    expect("route action mismatch", write_packet(work, json.loads(json.dumps(packet)), altered_rows),
           1, "declared route implies")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["execution"]["evidence_origin"] = "direct_route_trace"
    altered_rows = [dict(row) for row in rows]
    altered_rows[0]["terminal_event"] = "not_occurred"
    expect("blocked row cannot pretend observed prevention",
           write_packet(work, altered, altered_rows), 1, "blocked or held route action")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["execution"]["evidence_origin"] = "direct_route_trace"
    altered_rows = [json.loads(json.dumps(row)) for row in rows]
    altered["routes"][1]["topology"] = "sequential_stop_on_flag"
    altered_rows[2]["stage_decisions"] = {"lg4": "flag", "sg2": "not_exposed"}
    expect("direct sequential route", write_packet(work, altered, altered_rows), 0,
           "STRUCTURALLY VALID route-receipt/v1: declared direct route trace")

with tempfile.TemporaryDirectory() as temporary:
    work = pathlib.Path(temporary)
    altered = json.loads(json.dumps(packet))
    altered["execution"]["evidence_origin"] = "direct_route_trace"
    altered_rows = [json.loads(json.dumps(row)) for row in rows]
    altered["routes"][1]["topology"] = "sequential_stop_on_flag"
    altered_rows[2]["stage_decisions"] = {"lg4": "flag", "sg2": "clear"}
    expect("sequential post-termination exposure",
           write_packet(work, altered, altered_rows), 1, "exposes a stage after it terminated")

print("route-receipt regressions passed")
