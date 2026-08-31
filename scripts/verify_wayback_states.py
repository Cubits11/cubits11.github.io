#!/usr/bin/env python3
"""Regression coverage for remote-evidence failure states.

verify_wayback.py talks to an external service. The property that matters is
not that it can reach that service, but that it never reports a request which
did not complete as though the service had answered "no capture". This test
pins that distinction without touching the network.

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


def run(stub, argv):
    """Run main() with request_snapshot stubbed and argv fixed."""
    vw.request_snapshot = stub
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


CASES = [
    # (name, stub, argv, expected_exit, must_contain, must_not_contain)
    ("service unreachable -> UNDETERMINED, never 'lacks preservation'",
     lambda url, retries: (None, "URLError(timed out)"), ["--freshness", "any"],
     2, ["UNKNOWN", "not evidence that a capture is missing", "UNDETERMINED"],
     ["lack the requested preservation level"]),
    ("service answers 'no capture' -> a real, reportable absence",
     lambda url, retries: (None, None), ["--freshness", "any"],
     1, ["the availability API answered and reported no", "lack the requested preservation level"],
     ["UNDETERMINED"]),
    ("fresh capture -> pass",
     lambda url, retries: ({"status": "200", "url": "https://web.archive.org/x",
                            "timestamp": "20990101000000"}, None), ["--freshness", "any"],
     0, ["Wayback preflight passed"], ["FAIL", "UNKNOWN"]),
    ("capture predates review -> stale, and named as stale",
     lambda url, retries: ({"status": "200", "url": "https://web.archive.org/x",
                            "timestamp": "19990101000000"}, None), ["--freshness", "reviewed"],
     1, ["predates review", "stale"], ["UNDETERMINED"]),
]


def main() -> int:
    failures = 0
    for name, stub, argv, want_code, must, must_not in CASES:
        code, out = run(stub, argv)
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
          "undetermined is never reported as absent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
