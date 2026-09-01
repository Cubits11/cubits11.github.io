#!/usr/bin/env python3
"""Regression coverage for remote-evidence failure states.

verify_wayback.py talks to an external service. The property that matters is
not that it can reach that service, but that it never reports a non-answer as
though the service had answered "no capture". Two distinct non-answers exist:
a request that fails at the transport layer, and a request that succeeds while
the index returns an empty payload — which is what this API does under load and
is byte-for-byte identical to a true negative. Absence is therefore only ever
claimed when a second, independent index corroborates it. This test pins those
distinctions without touching the network.

Run: python scripts/verify_wayback_states.py
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("vw", ROOT / "scripts" / "verify_wayback.py")
vw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vw)


def run(stub, argv, cdx_stub=None):
    """Run main() with the network entry points stubbed and argv fixed."""
    vw.request_snapshot = stub
    # Default corroborator: unreachable. A case that reaches CDX without saying
    # what CDX answered should land in UNDETERMINED, not silently in absence.
    vw.cdx_has_capture = cdx_stub or (lambda url, retries: (None, "not stubbed"))
    vw.time.sleep = lambda *_: None
    old = sys.argv
    sys.argv = ["verify_wayback.py", *argv]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = vw.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


EMPTY = lambda url, retries: (None, None)          # HTTP 200, empty payload
FRESH = {"status": "200", "url": "https://web.archive.org/x",
         "timestamp": "20990101000000"}

CASES = [
    # (name, stub, argv, expected_exit, must_contain, must_not_contain, cdx_stub)
    ("service unreachable -> UNDETERMINED, never 'lacks preservation'",
     lambda url, retries: (None, "URLError(timed out)"), ["--freshness", "any"],
     2, ["UNKNOWN", "not evidence that a capture is missing", "UNDETERMINED"],
     ["lack the requested preservation level"], None),
    # The regression this battery previously certified as correct: an empty
    # payload from a throttled index was reported as a real absence.
    ("empty payload + CDX unreachable -> UNDETERMINED, never absence",
     EMPTY, ["--freshness", "any"],
     2, ["UNKNOWN", "Two non-answers do not make an absence", "UNDETERMINED"],
     ["lack the requested preservation level"],
     lambda url, retries: (None, "HTTPError 429")),
    ("empty payload + CDX finds a capture -> UNDETERMINED, indices disagree",
     EMPTY, ["--freshness", "any"],
     2, ["UNKNOWN", "indices", "disagree", "UNDETERMINED"],
     ["lack the requested preservation level"],
     lambda url, retries: (True, None)),
    ("both indices answer 'no capture' -> a real, reportable absence",
     EMPTY, ["--freshness", "any"],
     1, ["both", "neither reports an HTTP 200 capture",
         "lack the requested preservation level"],
     ["UNDETERMINED"],
     lambda url, retries: (False, None)),
    ("fresh capture -> pass",
     lambda url, retries: (FRESH, None), ["--freshness", "any"],
     0, ["Wayback preflight passed"], ["FAIL", "UNKNOWN"], None),
    ("capture predates review -> stale, and named as stale",
     lambda url, retries: ({"status": "200", "url": "https://web.archive.org/x",
                            "timestamp": "19990101000000"}, None), ["--freshness", "reviewed"],
     1, ["predates review", "stale"], ["UNDETERMINED"], None),
]


def main() -> int:
    failures = 0
    for name, stub, argv, want_code, must, must_not, cdx_stub in CASES:
        code, out = run(stub, argv, cdx_stub)
        problems = []
        if code != want_code:
            problems.append(f"exit {code}, expected {want_code}")
        for needle in must:
            if needle not in out:
                problems.append(f"missing {needle!r}")
        for needle in must_not:
            if needle in out:
                problems.append(f"must not say {needle!r}")
        if problems:
            failures += 1
            print(f"FAIL  {name}\n      " + "\n      ".join(problems))
        else:
            print(f"ok    {name}")
    if failures:
        print(f"remote-evidence failure states: {failures} regression(s)")
        return 1
    print(f"ok    remote-evidence failure states hold ({len(CASES)} cases; "
          "absence requires two agreeing indices, and undetermined is never "
          "reported as absent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
