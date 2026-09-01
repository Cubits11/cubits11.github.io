#!/usr/bin/env python3
"""Audit Wayback coverage for the examined census sources without writing.

This is intentionally a preflight tool, not CI: the Wayback availability API
is an external, rate-limited service. It distinguishes a historical capture
from one that is fresh enough to preserve the source state reviewed in this
repository. A successful response says a snapshot exists; it never proves
that the snapshot supports this census's classification.

Absence is the expensive claim, so it is the one that needs corroboration.
The availability API degrades under load by answering HTTP 200 with an empty
payload, which at the transport layer is indistinguishable from a true
negative. This tool therefore never calls a source unpreserved on that answer
alone: it asks a second, independent index (CDX) and reports absence only when
both answer and neither finds a capture.
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
CDX = "https://web.archive.org/cdx/search/cdx"
UA = "cubits11-wayback-preflight/1.0"
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
                endpoint, headers={"User-Agent": UA})
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


def cdx_has_capture(url: str, retries: int) -> tuple[bool | None, str | None]:
    """Ask the CDX index whether any HTTP 200 capture exists for this URL.

    Returns (True/False, None) when CDX actually answered, and (None, reason)
    when it did not. The bool is only ever consulted to corroborate a negative
    from the availability API; a corroborating index that cannot be reached
    leaves the question open rather than settling it.
    """
    endpoint = CDX + "?" + urllib.parse.urlencode({
        "url": url,
        "output": "json",
        "limit": "1",
        "filter": "statuscode:200",
        "fl": "timestamp,original",
    })
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(endpoint, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(endpoint, response.status, "", {}, None)
                body = response.read().decode("utf-8").strip()
            # CDX signals "no rows" with an empty body, and otherwise emits a
            # header row followed by one row per capture.
            if not body:
                return False, None
            rows = json.loads(body)
            if not isinstance(rows, list):
                return None, "CDX returned an unexpected payload shape"
            return len(rows) > 1, None
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

    # Three outcomes that a single counter would libel as one. A request that
    # never completed says nothing about whether a capture exists; reporting it
    # as missing preservation would convert absence of evidence into evidence
    # of absence, which is the exact error this repository exists to refuse.
    unknown: list[str] = []   # no corroborated determination — status undetermined
    absent: list[str] = []    # both indices answered: no usable capture
    stale: list[str] = []     # a capture exists but predates the review
    for i, row in enumerate(rows):
        if i:
            time.sleep(args.sleep_seconds)
        row_id = row["id"]
        snapshot, error = request_snapshot(row["primary_url"], args.retries)
        if error:
            unknown.append(row_id)
            print(f"UNKNOWN  {row_id}: Wayback availability request did not complete "
                  f"({error}). This is not evidence that a capture is missing.")
            continue
        if (not snapshot or str(snapshot.get("status")) != "200"
                or not snapshot.get("url")):
            # The request completing is not the same as the index answering.
            # Under load this API returns HTTP 200 with an empty payload, which
            # is byte-for-byte what a true negative looks like here. Absence is
            # claimed only when a second, independent index agrees.
            has_capture, cdx_error = cdx_has_capture(row["primary_url"], args.retries)
            if cdx_error is not None:
                unknown.append(row_id)
                print(f"UNKNOWN  {row_id}: the availability API returned no entry and "
                      f"the CDX index could not be reached ({cdx_error}). Two "
                      "non-answers do not make an absence.")
                continue
            if has_capture:
                unknown.append(row_id)
                print(f"UNKNOWN  {row_id}: the availability API returned no entry, but "
                      "the CDX index lists an HTTP 200 capture. The indices "
                      "disagree, so preservation is undetermined, not absent.")
                continue
            absent.append(row_id)
            print(f"FAIL  {row_id}: the availability API and the CDX index both "
                  "answered and neither reports an HTTP 200 capture")
            continue
        date = capture_date(snapshot)
        if args.freshness == "reviewed":
            reviewed = dt.date.fromisoformat(str(row["last_checked"]))
            if date is None or date < reviewed:
                stale.append(row_id)
                print(f"FAIL  {row_id}: capture {snapshot.get('timestamp')} predates "
                      f"review {reviewed.isoformat()} — {snapshot['url']}")
                continue
        print(f"ok    {row_id}: {snapshot.get('timestamp')} — {snapshot['url']}")

    determined = len(absent) + len(stale)
    if determined:
        print(f"Wayback preflight: {determined}/{len(rows)} selected source(s) were "
              "checked and lack the requested preservation level "
              f"({len(absent)} with no capture, {len(stale)} stale).")
    if unknown:
        print(f"Wayback preflight: {len(unknown)}/{len(rows)} source(s) UNDETERMINED "
              f"— no corroborated determination was reached ({', '.join(unknown)}). "
              "Their preservation state is unknown, not absent. Re-run before "
              "drawing any conclusion.")
    if determined:
        return 1
    if unknown:
        # Exit 2 keeps 'we could not tell' distinguishable from 'we checked and
        # it is missing'. A caller that treats every non-zero exit the same is
        # at least not being told a falsehood.
        return 2
    print(f"Wayback preflight passed: {len(rows)} selected source(s) meet "
          f"freshness={args.freshness}. Inspect snapshots before treating them as evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
