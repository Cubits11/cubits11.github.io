#!/usr/bin/env python3
"""Regression coverage for the claim registry's remote-evidence failure states.

verify_claims.py reaches four external things: the raw content behind a review
trigger, a bare clone used as an ancestry probe, that probe's verdict, and each
public support URL. For every one of them the property that matters is not that
the network worked, but that a request which never completed can never be
reported as a substantive finding — a fired trigger, a dangling binding, or a
dead support URL.

That distinction is load-bearing. "TRIGGER FIRED" means bound evidence changed
upstream and a claim is due for re-review; "NOT reachable" means a binding is
dangling. Both are claims about the world. A timeout is a claim about the
network, and the weekly scheduled run must not be able to manufacture the
former out of the latter.

This is the companion to verify_wayback_states.py, and it holds the same line
for the registry. It touches no network.

Run: python scripts/verify_claims_states.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import socket
import subprocess
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "vc", ROOT / "scripts" / "verify_claims.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)


TIMEOUT = urllib.error.URLError(socket.timeout("timed out"))
NOT_FOUND = urllib.error.HTTPError(
    "https://example.invalid/x", 404, "Not Found", {}, None)


def raiser(exc):
    def _f(*_a, **_k):
        raise exc
    return _f


def run(fn):
    """Run one probe with the module's buckets reset; return (out, fails, unknowns)."""
    vc.failures.clear()
    vc.unknowns.clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue(), list(vc.failures), list(vc.unknowns)


class FakeCompleted:
    def __init__(self, returncode, stderr=b""):
        self.returncode = returncode
        self.stderr = stderr


def liveness_transport():
    vc.fetch = raiser(TIMEOUT)
    vc.check_url_liveness("CC-001", "https://example.invalid/a")


def liveness_http_error():
    vc.fetch = raiser(NOT_FOUND)
    vc.check_url_liveness("CC-001", "https://example.invalid/a")


TRIG = {"enforcement": "executable", "type": "remote_content_change",
        "repo": "o/r", "path": "p.py", "bound_ref": "abcdef1234567890"}


def trigger_transport():
    vc.fetch = raiser(TIMEOUT)
    vc.check_trigger("CC-002", dict(TRIG))


def trigger_really_fired():
    seen = []

    def _fetch(url):
        seen.append(url)
        return b"bound" if len(seen) == 1 else b"drifted"
    vc.fetch = _fetch
    vc.check_trigger("CC-002", dict(TRIG))


def trigger_http_error():
    vc.fetch = raiser(NOT_FOUND)
    vc.check_trigger("CC-002", dict(TRIG))


BINDINGS = {"o/r": [("CC-003", "0123456789abcdef0123456789abcdef01234567")]}


def _with_subprocess(clone_exc, ancestor_rc, stderr=b""):
    def _run(cmd, *a, **k):
        if cmd[0] == "git" and cmd[1] == "clone":
            if clone_exc:
                raise clone_exc
            return FakeCompleted(0)
        return FakeCompleted(ancestor_rc, stderr)
    return _run


def clone_unreachable():
    vc.subprocess.run = _with_subprocess(
        subprocess.TimeoutExpired("git clone", 120), 0)
    vc.check_reachability(dict(BINDINGS))


def ancestry_refuted():
    vc.subprocess.run = _with_subprocess(None, 1)
    vc.check_reachability(dict(BINDINGS))


def ancestry_probe_broken():
    vc.subprocess.run = _with_subprocess(None, 128, b"fatal: bad object")
    vc.check_reachability(dict(BINDINGS))


def ancestry_ok():
    vc.subprocess.run = _with_subprocess(None, 0)
    vc.check_reachability(dict(BINDINGS))


# (name, probe, want_fails, want_unknowns, must_contain, must_not_contain)
CASES = [
    ("support URL not reached -> UNDETERMINED, never a dead binding",
     liveness_transport, 0, 1,
     ["UNKNOWN", "was not reached", "not disproved"],
     ["FAIL", "returned an error"]),

    ("support URL answers 404 -> a real, reportable finding",
     liveness_http_error, 1, 0,
     ["FAIL", "returned an error"],
     ["UNKNOWN", "not disproved"]),

    ("trigger fetch not reached -> UNDETERMINED, never TRIGGER FIRED",
     trigger_transport, 0, 1,
     ["UNKNOWN", "did not complete", "unevaluated, not observed"],
     ["TRIGGER FIRED", "FAIL"]),

    ("bound content really diverged -> TRIGGER FIRED, and said so",
     trigger_really_fired, 1, 0,
     ["FAIL", "TRIGGER FIRED", "due for re-review"],
     ["UNKNOWN"]),

    ("trigger URL answers 404 -> a finding about the binding, not the network",
     trigger_http_error, 1, 0,
     ["FAIL", "did not complete"],
     ["UNKNOWN", "TRIGGER FIRED"]),

    ("ancestry clone did not complete -> UNDETERMINED, never 'NOT reachable'",
     clone_unreachable, 0, 1,
     ["UNKNOWN", "unevaluated, not refuted"],
     ["FAIL", "NOT reachable"]),

    ("git answered 'not an ancestor' -> a real dangling binding",
     ancestry_refuted, 1, 0,
     ["FAIL", "NOT reachable", "dangling binding"],
     ["UNKNOWN"]),

    ("git could not answer -> UNDETERMINED, not a dangling binding",
     ancestry_probe_broken, 0, 1,
     ["UNKNOWN", "could not be evaluated", "bad object"],
     ["FAIL", "NOT reachable"]),

    ("commit is an ancestor -> pass",
     ancestry_ok, 0, 0,
     ["ok", "reachable from"],
     ["FAIL", "UNKNOWN", "NOT reachable"]),
]


def exit_contract() -> list[str]:
    """The three exit codes must stay distinguishable to a caller."""
    problems = []
    for label, fails, unknowns, want in (
            ("clean", [], [], 0),
            ("undetermined only", [], ["u"], 2),
            ("a real failure", ["f"], [], 1),
            ("failure alongside undetermined", ["f"], ["u"], 1)):
        vc.failures[:] = fails
        vc.unknowns[:] = unknowns
        # Execute the real branch, never a copy of it.
        with contextlib.redirect_stdout(io.StringIO()):
            code = vc.exit_code()
        if code != want:
            problems.append(f"{label}: exit {code}, expected {want}")
    return problems


def classification() -> list[str]:
    """HTTPError subclasses URLError; order of the isinstance tests matters."""
    problems = []
    if vc.transport_failure(NOT_FOUND):
        problems.append("a 404 was classified as a transport failure — "
                        "HTTPError must be excluded before URLError is tested")
    if not vc.transport_failure(TIMEOUT):
        problems.append("a timeout was not classified as a transport failure")
    return problems


def main() -> int:
    failures = 0
    for name, probe, want_f, want_u, must, must_not in CASES:
        out, fails, unknowns = run(probe)
        problems = []
        if len(fails) != want_f:
            problems.append(f"{len(fails)} failure(s), expected {want_f}")
        if len(unknowns) != want_u:
            problems.append(f"{len(unknowns)} unknown(s), expected {want_u}")
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

    for label, problems in (("transport classification", classification()),
                            ("exit-code contract", exit_contract())):
        if problems:
            failures += 1
            print(f"FAIL  {label}\n      " + "\n      ".join(problems))
        else:
            print(f"ok    {label}")

    if failures:
        print(f"claim-registry failure states: {failures} regression(s)")
        return 1
    print(f"ok    claim-registry remote failure states hold ({len(CASES) + 2} "
          "cases; unreached is never reported as refuted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
