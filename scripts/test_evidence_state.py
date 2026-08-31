#!/usr/bin/env python3
"""Regression tests for evidence retrieval states that must not be conflated.

These are mocked deliberately: the point is to verify the policy around an
outage, a server error, malformed data, an actual empty preservation record,
and their exit codes without asking a network service to misbehave on demand.
"""

from __future__ import annotations

import json
import contextlib
import datetime as dt
import http.client
import io
import socket
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import verify_claims as claims
import verify_wayback as wayback


class FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


class ClaimRetrievalStates(unittest.TestCase):
    def setUp(self) -> None:
        claims.failures.clear()
        claims.unknowns.clear()

    @staticmethod
    def http_error(code: int, reason: str) -> urllib.error.HTTPError:
        return urllib.error.HTTPError("https://example.test", code, reason, {}, io.BytesIO())

    def test_only_transport_failures_are_unevaluated(self) -> None:
        self.assertTrue(claims.transport_failure(urllib.error.URLError("offline")))
        self.assertTrue(claims.transport_failure(socket.timeout("late")))
        self.assertTrue(claims.transport_failure(
            http.client.IncompleteRead(b"partial response", 100)))
        self.assertTrue(claims.transport_failure(OSError("TLS socket reset")))
        error = self.http_error(503, "unavailable")
        self.assertFalse(claims.transport_failure(error))
        error.close()
        self.assertFalse(claims.transport_failure(RuntimeError("bad response parser")))

    def test_liveness_outage_is_unknown_not_failure(self) -> None:
        with mock.patch.object(claims, "fetch",
                               side_effect=urllib.error.URLError("offline")):
            with contextlib.redirect_stdout(io.StringIO()):
                claims.check_url_liveness("TEST-001", "https://example.test/source")
        self.assertFalse(claims.failures)
        self.assertEqual(len(claims.unknowns), 1)

    def test_liveness_http_error_is_failure_not_unknown(self) -> None:
        error = self.http_error(429, "rate limited")
        with mock.patch.object(claims, "fetch", side_effect=error):
            with contextlib.redirect_stdout(io.StringIO()):
                claims.check_url_liveness("TEST-002", "https://example.test/source")
        self.assertEqual(len(claims.failures), 1)
        self.assertFalse(claims.unknowns)
        error.close()


class WaybackRetrievalStates(unittest.TestCase):
    def response(self, payload: object, status: int = 200) -> wayback.SnapshotResult:
        with mock.patch.object(wayback.urllib.request, "urlopen",
                               return_value=FakeResponse(status, payload)):
            return wayback.request_snapshot("https://example.test/source", retries=0)

    def test_capture_and_empty_record_are_distinct(self) -> None:
        capture = self.response({"archived_snapshots": {"closest": {
            "status": "200", "timestamp": "20260831010203",
            "url": "https://web.archive.org/example"}}})
        self.assertEqual(capture.state, wayback.CAPTURE)
        self.assertEqual(wayback.capture_date(capture.snapshot or {}), dt.date(2026, 8, 31))
        empty = self.response({"archived_snapshots": {}})
        self.assertEqual(empty.state, wayback.NO_CAPTURE)

    def test_response_errors_and_malformed_json_are_not_absence(self) -> None:
        error = urllib.error.HTTPError("https://archive.org", 429, "rate limited", {}, io.BytesIO())
        with mock.patch.object(wayback.urllib.request, "urlopen", side_effect=error):
            self.assertEqual(wayback.request_snapshot("https://example.test", 0).state,
                             wayback.UNKNOWN_RESPONSE)
        error.close()
        with mock.patch.object(wayback.urllib.request, "urlopen",
                               return_value=FakeResponse(200, b"not json")):
            self.assertEqual(wayback.request_snapshot("https://example.test", 0).state,
                             wayback.UNKNOWN_RESPONSE)
        malformed = self.response({"archived_snapshots": {"closest": []}})
        self.assertEqual(malformed.state, wayback.UNKNOWN_RESPONSE)

    def test_transport_outage_and_bad_timestamp_are_unevaluated(self) -> None:
        with mock.patch.object(wayback.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("offline")):
            self.assertEqual(wayback.request_snapshot("https://example.test", 0).state,
                             wayback.UNREACHABLE)
        self.assertIsNone(wayback.capture_date({"timestamp": "20260831"}))
        self.assertIsNone(wayback.capture_date({"timestamp": "20261301010203"}))

    def test_interrupted_or_tls_responses_are_unevaluated(self) -> None:
        class InterruptedResponse(FakeResponse):
            def read(self) -> bytes:
                raise http.client.IncompleteRead(b"partial response", 100)

        with mock.patch.object(wayback.urllib.request, "urlopen",
                               return_value=InterruptedResponse(200, {})):
            self.assertEqual(wayback.request_snapshot("https://example.test", 0).state,
                             wayback.UNREACHABLE)
        with mock.patch.object(wayback.urllib.request, "urlopen",
                               side_effect=OSError("TLS socket reset")):
            self.assertEqual(wayback.request_snapshot("https://example.test", 0).state,
                             wayback.UNREACHABLE)

    def test_main_uses_success_failure_and_incomplete_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "census.yaml").write_text(
                "benchmarks:\n  - id: test-row\n    status: examined\n"
                "    primary_url: https://example.test/source\n"
                "    last_checked: '2026-08-30'\n",
                encoding="utf-8")
            args = SimpleNamespace(ids=None, freshness="any", sleep_seconds=0, retries=0)
            successful = wayback.SnapshotResult(wayback.CAPTURE, {
                "status": "200", "timestamp": "20260831010203",
                "url": "https://web.archive.org/example"})
            cases = (
                (successful, 0),
                (wayback.SnapshotResult(wayback.NO_CAPTURE), 1),
                (wayback.SnapshotResult(wayback.UNREACHABLE, detail="offline"), 2),
                (wayback.SnapshotResult(wayback.UNKNOWN_RESPONSE, detail="HTTP 429"), 2),
            )
            for result, expected in cases:
                with self.subTest(state=result.state), \
                     mock.patch.object(wayback, "ROOT", root), \
                     mock.patch.object(wayback, "parse_args", return_value=args), \
                     mock.patch.object(wayback, "request_snapshot", return_value=result):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(wayback.main(), expected)


if __name__ == "__main__":
    unittest.main()
