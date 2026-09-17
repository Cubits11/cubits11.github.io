#!/usr/bin/env python3
"""A retracted claim id may not be cited as if it were registered.

When a claim is withdrawn, the registry entry disappears and the history keeps
a RETRACT. What does not disappear is every sentence elsewhere in the
repository that said "bound to MC-005" or "MC-005 proposition" — and those
sentences keep pointing at an id a reader will look up and not find. That is
the half-state this gate exists to prevent: a number circulating with the
authority of a registration that no longer exists.

The rule is deliberately crude and lexical, in the same family as the spine's
scope-widener check. Every line of an active surface that names a retracted
claim id must, on the same line, also carry one of the words that says what
happened to it. A line that names the id and nothing else fails.

Retracted ids are derived, never listed by hand: a claim whose history ends in
a RETRACT and which is absent from claims.yaml.

    python3 scripts/verify_retracted.py          # the gate (exit 0 / 1)
    python3 scripts/verify_retracted.py --list   # show the retracted ids
    python3 scripts/verify_retracted.py --test   # the fixtures, in memory

What this does NOT do: decide whether the underlying computation was any good.
A retracted claim's numbers may be perfectly sound — MC-005's are, and the
retraction says so. The gate is about attribution, not about arithmetic.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# A line naming a retracted id must also say, on that line, what became of it.
ACQUITTING = (
    "retract", "retracted", "unregistered", "not registered", "no registered",
    "never registered", "withdrawn", "de-registered", "deregistered",
)

# Surfaces a reader can reach or an agent will quote. The history file is the
# record of the retraction and is exempt; so is anything private or vendored.
INCLUDE_GLOBS = (
    "*.html", "*.md", "*.yaml", "*.yml", "*.json", "*.py", "*.txt",
)
# Frozen experiment artifacts are excluded, and the reason matters: a freeze is
# immutable by contract, and this repository treats a post-hoc edit to one as a
# forbidden rescue. A gate that demanded an annotation inside a freeze would be
# a gate demanding the one edit the programme forbids. A retracted id inside a
# freeze is a true statement about what was frozen, on the date it was frozen.
EXCLUDE_PARTS = (
    ".git", "_private", "node_modules", "__pycache__", ".tmp.drivedownload",
    ".tmp.driveupload", "renders", "freeze",
)
EXEMPT_FILES = {
    "claims_history.yaml",          # the record of the retraction itself
    "scripts/verify_retracted.py",  # this gate
}

ID = re.compile(r"\b([A-Z]{2,4}-\d{3})\b")


def retracted_ids() -> list[str]:
    hist = yaml.safe_load((ROOT / "claims_history.yaml").read_text(encoding="utf-8"))
    live = {
        c["id"]
        for c in yaml.safe_load((ROOT / "claims.yaml").read_text(encoding="utf-8"))["claims"]
    }
    last: dict[str, str] = {}
    for e in hist.get("entries", []):
        cid = e.get("claim_id")
        if not cid:
            continue
        last[cid] = e.get("transition_type") or ("registration" if e.get("kind") == "registration" else "")
    return sorted(cid for cid, t in last.items() if t == "RETRACT" and cid not in live)


def surfaces() -> list[Path]:
    out = []
    for pattern in INCLUDE_GLOBS:
        for p in ROOT.rglob(pattern):
            rel = p.relative_to(ROOT)
            if any(part in EXCLUDE_PARTS for part in rel.parts):
                continue
            if str(rel) in EXEMPT_FILES:
                continue
            out.append(p)
    return sorted(set(out))


def offending_lines(text: str, ids: list[str]) -> list[tuple[int, str, str]]:
    """(line number, the id, the line) for every unacquitted mention."""
    bad = []
    patterns = {cid: re.compile(rf"(?<![A-Za-z0-9-]){re.escape(cid)}(?![0-9A-Za-z])")
                for cid in ids}
    for n, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        for cid, pat in patterns.items():
            if pat.search(line) and not any(w in low for w in ACQUITTING):
                bad.append((n, cid, line.strip()[:140]))
    return bad


def run() -> int:
    ids = retracted_ids()
    if not ids:
        print("ok    no retracted claim ids — nothing to police")
        return 0
    failures = 0
    for path in surfaces():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, cid, line in offending_lines(text, ids):
            rel = path.relative_to(ROOT)
            print(f"FAIL  {rel}:{n}: names {cid}, which is retracted, without saying so "
                  f"on the same line\n      {line}")
            failures += 1
    if failures:
        print(f"\n{failures} unacquitted mention(s). Add the word that says what happened "
              f"to the id — retracted, unregistered, withdrawn — or remove the reference. "
              f"Retracted ids: {', '.join(ids)}")
        return 1
    print(f"ok    every mention of {', '.join(ids)} says on its own line that it is retracted")
    return 0


def test() -> int:
    """A gate nobody has watched fail is not a gate."""
    ids = ["ZZ-999"]
    cases = [
        ("bound to ZZ-999", True, "a bare attribution must fail"),
        ("ZZ-999 proposition", True, "a bare proposition reference must fail"),
        ("ZZ-999 (retracted 2026-09-06)", False, "an acquitted mention must pass"),
        ("computed, unregistered — formerly ZZ-999", False, "unregistered acquits"),
        ("nothing here names a claim", False, "an unrelated line must pass"),
        ("ZZ-9999 is a different token", False, "the id must match whole"),
    ]
    bad = 0
    for text, should_fail, why in cases:
        got = bool(offending_lines(text, ids))
        mark = "ok  " if got == should_fail else "FAIL"
        if got != should_fail:
            bad += 1
        print(f"{mark}  {why}: {text!r} -> {'flagged' if got else 'clean'}")
    if bad:
        print(f"\n{bad} fixture(s) behaved wrongly.")
        return 1
    print("\nfixtures pass: the gate flags bare attribution and clears acquitted mentions")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="print the retracted ids and exit")
    ap.add_argument("--test", action="store_true", help="run the fixtures in memory")
    args = ap.parse_args()
    if args.test:
        return test()
    if args.list:
        ids = retracted_ids()
        print("\n".join(ids) if ids else "(none)")
        return 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
