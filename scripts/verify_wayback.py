#!/usr/bin/env python3
"""Audit Wayback coverage for the examined census sources without writing.

This is intentionally a preflight tool, not CI: the Wayback availability API
is an external, rate-limited service. It distinguishes a historical capture
from one that is fresh enough to preserve the source state reviewed in this
repository. A successful response says a snapshot exists; it never proves
that the snapshot supports this census's classification.
"""

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
API = "https://archive.org/wayback/available"
TIMEOUT = 30


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
                        help="retries after a transient API error (default: %(default)s)")
    args = parser.parse_args()
    if args.sleep_seconds < 0:
        parser.error("--sleep-seconds cannot be negative")
    if args.retries < 0:
        parser.error("--retries cannot be negative")
    return args


def request_snapshot(url: str, retries: int) -> tuple[dict | None, str | None]:
    endpoint = API + "?" + urllib.parse.urlencode({"url": url})
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                endpoint, headers={"User-Agent": "cubits11-wayback-preflight/1.0"})
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(endpoint, response.status, "", {}, None)
                payload = json.loads(response.read().decode("utf-8"))
                closest = (payload.get("archived_snapshots") or {}).get("closest")
                return (closest if isinstance(closest, dict) else None), None
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError) as exc:
            if attempt == retries:
                return None, str(exc)
            time.sleep(5 * (attempt + 1))
    return None, "unreachable"


def capture_date(snapshot: dict) -> dt.date | None:
    raw = str(snapshot.get("timestamp", ""))
    try:
        return dt.datetime.strptime(raw[:8], "%Y%m%d").date()
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
    for i, row in enumerate(rows):
        if i:
            time.sleep(args.sleep_seconds)
        row_id = row["id"]
        snapshot, error = request_snapshot(row["primary_url"], args.retries)
        if error:
            failures += 1
            print(f"FAIL  {row_id}: Wayback availability request failed: {error}")
            continue
        if (not snapshot or str(snapshot.get("status")) != "200"
                or not snapshot.get("url")):
            failures += 1
            print(f"FAIL  {row_id}: no HTTP 200 Wayback capture available")
            continue
        date = capture_date(snapshot)
        if args.freshness == "reviewed":
            reviewed = dt.date.fromisoformat(str(row["last_checked"]))
            if date is None or date < reviewed:
                failures += 1
                print(f"FAIL  {row_id}: capture {snapshot.get('timestamp')} predates "
                      f"review {reviewed.isoformat()} — {snapshot['url']}")
                continue
        print(f"ok    {row_id}: {snapshot.get('timestamp')} — {snapshot['url']}")

    if failures:
        print(f"Wayback preflight failed: {failures}/{len(rows)} selected source(s) "
              "lack the requested preservation level.")
        return 1
    print(f"Wayback preflight passed: {len(rows)} selected source(s) meet "
          f"freshness={args.freshness}. Inspect snapshots before treating them as evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
