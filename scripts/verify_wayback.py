#!/usr/bin/env python3
"""Audit Wayback coverage for the examined census sources without writing.

This is intentionally a preflight tool, not CI: the Wayback availability API
is an external, rate-limited service. It distinguishes a historical capture
from one that is fresh enough to preserve the source state reviewed in this
repository. A successful response says a snapshot exists; it never proves
that the snapshot supports this census's classification.

The tool also distinguishes confirmed absence from an unevaluable request:
an unavailable transport or an invalid/error API response cannot establish
that a source lacks a capture. Both return a non-passing incomplete state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
API = "https://archive.org/wayback/available"
TIMEOUT = 30

CAPTURE = "capture"
NO_CAPTURE = "no_capture"
UNREACHABLE = "unreachable"
UNKNOWN_RESPONSE = "unknown_response"

# HTTPError is intentionally handled before this tuple: it is an URLError
# subclass, but proves that an HTTP response arrived. OSError covers TLS and
# socket failures; HTTPException covers interrupted HTTP response bodies.
TRANSPORT_EXCEPTIONS = (urllib.error.URLError, TimeoutError, socket.timeout,
                        socket.gaierror, ConnectionError, OSError,
                        http.client.HTTPException)


@dataclass(frozen=True)
class SnapshotResult:
    state: str
    snapshot: dict[str, object] | None = None
    detail: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Wayback availability for every examined census source.")
    parser.add_argument("--id", action="append", dest="ids",
                        help="check one census row ID (repeatable)")
    parser.add_argument(
        "--freshness", choices=("any", "reviewed"), default="any",
        help="'reviewed' requires capture date >= each row's last_checked")
    parser.add_argument("--sleep-seconds", type=float, default=2.0,
                        help="minimum delay between API calls (default: %(default)s)")
    parser.add_argument("--retries", type=int, default=2,
                        help="retries after an unevaluable API result (default: %(default)s)")
    args = parser.parse_args()
    if args.sleep_seconds < 0:
        parser.error("--sleep-seconds cannot be negative")
    if args.retries < 0:
        parser.error("--retries cannot be negative")
    return args


def response_result(response) -> SnapshotResult:
    """Parse one HTTP response without turning malformed evidence into absence."""
    status = getattr(response, "status", None)
    if status != 200:
        return SnapshotResult(UNKNOWN_RESPONSE, detail=f"HTTP status {status!r}")
    try:
        body = response.read()
    except TRANSPORT_EXCEPTIONS as exc:
        return SnapshotResult(UNREACHABLE,
                              detail=f"response body interrupted ({exc})")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        return SnapshotResult(UNKNOWN_RESPONSE, detail=f"invalid JSON ({exc})")
    if not isinstance(payload, dict):
        return SnapshotResult(UNKNOWN_RESPONSE, detail="top-level response is not an object")
    snapshots = payload.get("archived_snapshots")
    if not isinstance(snapshots, dict):
        return SnapshotResult(UNKNOWN_RESPONSE,
                              detail="archived_snapshots is missing or not an object")
    closest = snapshots.get("closest")
    if closest is None or closest == {}:
        return SnapshotResult(NO_CAPTURE)
    if not isinstance(closest, dict):
        return SnapshotResult(UNKNOWN_RESPONSE,
                              detail="archived_snapshots.closest is not an object")
    return SnapshotResult(CAPTURE, snapshot=closest)


def request_snapshot(url: str, retries: int) -> SnapshotResult:
    endpoint = API + "?" + urllib.parse.urlencode({"url": url})
    result = SnapshotResult(UNREACHABLE, detail="request was not attempted")
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                endpoint, headers={"User-Agent": "cubits11-wayback-preflight/1.0"})
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                result = response_result(response)
        except urllib.error.HTTPError as exc:
            # HTTPError is a URLError subclass, but it proves a server
            # response arrived. It is unusable evidence, not an outage.
            result = SnapshotResult(UNKNOWN_RESPONSE,
                                    detail=f"HTTP status {exc.code}: {exc.reason}")
        except TRANSPORT_EXCEPTIONS as exc:
            result = SnapshotResult(UNREACHABLE, detail=str(exc))

        if result.state in (CAPTURE, NO_CAPTURE):
            return result
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    return result


def capture_date(snapshot: dict[str, object]) -> dt.date | None:
    raw = snapshot.get("timestamp")
    if not isinstance(raw, str) or len(raw) != 14 or not raw.isdigit():
        return None
    try:
        return dt.datetime.strptime(raw, "%Y%m%d%H%M%S").date()
    except ValueError:
        return None


def main() -> int:
    args = parse_args()
    data = yaml.safe_load((ROOT / "census.yaml").read_text()) or {}
    rows = [row for row in data.get("benchmarks") or []
            if row.get("status") == "examined"]
    if args.ids:
        wanted = set(args.ids)
        rows = [row for row in rows if row.get("id") in wanted]
        missing = wanted - {row.get("id") for row in rows}
        if missing:
            print(f"FAIL  unknown or unexamined row ID(s): {', '.join(sorted(missing))}")
            return 1
    if not rows:
        print("FAIL  no examined rows selected")
        return 1

    failures = 0
    unknowns = 0
    for i, row in enumerate(rows):
        if i:
            time.sleep(args.sleep_seconds)
        row_id = row["id"]
        result = request_snapshot(row["primary_url"], args.retries)
        if result.state == UNREACHABLE:
            unknowns += 1
            print(f"UNKNOWN  {row_id}: Wayback availability API was not reached "
                  f"({result.detail}) — preservation unevaluated, not absent")
            continue
        if result.state == UNKNOWN_RESPONSE:
            unknowns += 1
            print(f"UNKNOWN  {row_id}: Wayback availability API response could not be "
                  f"evaluated ({result.detail}) — preservation unevaluated, not absent")
            continue
        if result.state == NO_CAPTURE:
            failures += 1
            print(f"FAIL  {row_id}: no Wayback capture is available")
            continue

        snapshot = result.snapshot or {}
        if (str(snapshot.get("status")) != "200"
                or not isinstance(snapshot.get("url"), str)
                or not snapshot["url"].strip()):
            failures += 1
            print(f"FAIL  {row_id}: no HTTP 200 Wayback capture available")
            continue
        date = capture_date(snapshot)
        if args.freshness == "reviewed":
            try:
                reviewed = dt.date.fromisoformat(str(row["last_checked"]))
            except (KeyError, ValueError):
                failures += 1
                print(f"FAIL  {row_id}: invalid local last_checked value "
                      f"{row.get('last_checked')!r}")
                continue
            if date is None:
                unknowns += 1
                print(f"UNKNOWN  {row_id}: capture timestamp {snapshot.get('timestamp')!r} "
                      "cannot be evaluated against the review date — preservation "
                      "freshness unevaluated, not stale")
                continue
            if date < reviewed:
                failures += 1
                print(f"FAIL  {row_id}: capture {snapshot['timestamp']} predates "
                      f"review {reviewed.isoformat()} — {snapshot['url']}")
                continue
        print(f"ok    {row_id}: {snapshot.get('timestamp')} — {snapshot['url']}")

    if failures:
        print(f"Wayback preflight found {failures} confirmed preservation failure(s) "
              f"and {unknowns} unevaluated source(s), out of {len(rows)} selected.")
        return 1
    if unknowns:
        print(f"Wayback preflight incomplete: {unknowns}/{len(rows)} selected source(s) "
              "could not be evaluated. This is non-passing, not evidence of absence.")
        return 2
    print(f"Wayback preflight passed: {len(rows)} selected source(s) meet "
          f"freshness={args.freshness}. Inspect snapshots before treating them as evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
