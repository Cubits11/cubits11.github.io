#!/usr/bin/env python3
"""Contributions in this repository are attributed to Cubits11. No agent names itself.

An agent that signs a commit is making a claim about who did the work, on the
one surface a reader trusts without checking: the commit log. This repository
prosecutes its claims, so it cannot leave that one unprosecuted. The rule is
that every commit bound by it carries a Cubits11 author, a Cubits11 committer,
and no machine-attribution trailer.

The rule binds forward, from a recorded baseline commit, and not backward.
That asymmetry is deliberate and is the substance of this file:

    Rewriting the 43 pre-baseline commits that carry a model trailer would
    change every SHA on the default branch. Sixty-odd published permalinks
    pin those SHAs -- the traction ledger, the dispatch log, the BELLS
    dossier, the missing-column page. Every one of them would 404. A
    binding that no longer resolves is a worse failure than a trailer that
    records, accurately, that a model drafted the text. So the history
    stands, the baseline records where the rule starts, and the count of
    pre-baseline trailers is reported rather than hidden.

    python3 scripts/verify_attribution.py           # the gate (exit 0 / 1)
    python3 scripts/verify_attribution.py --history # the pre-baseline count
    python3 scripts/verify_attribution.py --test    # the fixtures, in memory

What this does NOT do: verify that a human wrote any particular line. It
verifies attribution hygiene -- that no machine signs this log -- which is a
statement about the record, not about the labour.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "metrics" / "attribution_baseline.json"

# Identities permitted to author or commit. Matched case-insensitively and in
# full, so a look-alike address does not pass.
PERMITTED_EMAILS = frozenset({
    "90584946+cubits11@users.noreply.github.com",
})
PERMITTED_NAMES = frozenset({"cubits11", "pranav bhave"})

# A trailer or footer by which a tool names its own contribution.
MACHINE_ATTRIBUTION = re.compile(
    r"^\s*(?:"
    r"co-authored-by:.*(?:anthropic|openai|claude|gpt-|copilot|codex|gemini|cursor|devin)"
    r"|claude-session:"
    r"|assisted-by:.*(?:anthropic|openai|claude)"
    r"|(?:\U0001F916\s*)?(?:co-)?generated (?:with|by) \[?(?:claude|cursor|copilot|codex)"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def baseline_commit() -> str:
    if not BASELINE.exists():
        raise SystemExit(
            "metrics/attribution_baseline.json is absent; the rule has no start point."
        )
    return json.loads(BASELINE.read_text())["commit"]


def bound_commits() -> list[str]:
    """Commits reachable from HEAD that the rule binds: baseline exclusive."""
    base = baseline_commit()
    try:
        out = git("rev-list", f"{base}..HEAD")
    except subprocess.CalledProcessError:
        raise SystemExit(
            f"baseline commit {base[:12]} is not reachable from HEAD; "
            "re-pin metrics/attribution_baseline.json."
        )
    return [line for line in out.splitlines() if line]


def violations(sha: str) -> list[str]:
    record = git("show", "-s", "--format=%an%n%ae%n%cn%n%ce%n%B", sha)
    an, ae, cn, ce, *body = record.split("\n")
    found: list[str] = []
    for role, name, email in (("author", an, ae), ("committer", cn, ce)):
        if email.strip().lower() not in PERMITTED_EMAILS:
            found.append(f"{role} email {email!r} is not a Cubits11 identity")
        if name.strip().lower() not in PERMITTED_NAMES:
            found.append(f"{role} name {name!r} is not a Cubits11 identity")
    for line in MACHINE_ATTRIBUTION.findall("\n".join(body)):
        found.append(f"machine-attribution trailer: {line.strip()!r}")
    if MACHINE_ATTRIBUTION.search("\n".join(body)) and not any(
        f.startswith("machine-attribution") for f in found
    ):  # pragma: no cover - findall/search disagree only on a regex bug
        found.append("machine-attribution trailer present")
    return found


def gate() -> int:
    failures: list[str] = []
    for sha in bound_commits():
        for reason in violations(sha):
            subject = git("show", "-s", "--format=%s", sha).strip()
            failures.append(f"  {sha[:12]}  {subject[:58]}\n      {reason}")
    if failures:
        print(f"attribution: {len(failures)} violation(s) after the baseline\n")
        print("\n".join(failures))
        print(
            "\nInstall the hook that prevents this:\n"
            "  git config core.hooksPath .githooks"
        )
        return 1
    print(f"attribution: {len(bound_commits())} bound commit(s), all Cubits11, no machine trailers")
    return 0


def history() -> int:
    """Report, without editing, what the pre-baseline record contains."""
    base = baseline_commit()
    pre = [s for s in git("rev-list", base).splitlines() if s]
    tagged = [s for s in pre if MACHINE_ATTRIBUTION.search(git("show", "-s", "--format=%B", s))]
    print(f"pre-baseline commits: {len(pre)}")
    print(f"  carrying a machine-attribution trailer: {len(tagged)}")
    print(
        "\nThese are not rewritten. Their SHAs are pinned by published permalinks\n"
        "in distribution/traction/events.json, distribution/dispatch-log.yaml,\n"
        "distribution/dossiers/ and missing-column/index.html. Rewriting them\n"
        "would break every one of those bindings."
    )
    return 0


FIXTURES = (
    ("bare subject", "a subject line", False),
    ("body only", "subject\n\nsome body text\n", False),
    ("human co-author", "subject\n\nCo-Authored-By: A Person <a@example.org>\n", False),
    ("model co-author", "subject\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n", True),
    ("vendor address", "subject\n\nCo-Authored-By: X <someone@anthropic.com>\n", True),
    ("session backlink", "subject\n\nClaude-Session: https://claude.ai/code/session_x\n", True),
    ("generated footer", "subject\n\n\U0001F916 Generated with [Claude Code](https://x)\n", True),
    ("copilot", "subject\n\nCo-authored-by: GitHub Copilot <copilot@github.com>\n", True),
    ("assisted-by", "subject\n\nAssisted-By: OpenAI Codex\n", True),
    ("word in prose", "subject\n\nI discuss claude's output in this paragraph.\n", False),
)


def test() -> int:
    failures = []
    for label, message, expected in FIXTURES:
        got = bool(MACHINE_ATTRIBUTION.search(message))
        if got != expected:
            failures.append(f"  {label}: expected {expected}, got {got}")
    for label, email, expected in (
        ("canonical", "90584946+cubits11@users.noreply.github.com", True),
        ("model", "noreply@anthropic.com", False),
        ("look-alike", "90584946+cubits11@users.noreply.github.com.evil.test", False),
    ):
        got = email.lower() in PERMITTED_EMAILS
        if got != expected:
            failures.append(f"  identity {label}: expected {expected}, got {got}")
    if failures:
        print(f"attribution fixtures: {len(failures)} failed")
        print("\n".join(failures))
        return 1
    print(f"attribution fixtures: {len(FIXTURES) + 3} passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true", help="count pre-baseline trailers")
    parser.add_argument("--test", action="store_true", help="run the fixtures in memory")
    args = parser.parse_args()
    if args.test:
        return test()
    if args.history:
        return history()
    return gate()


if __name__ == "__main__":
    sys.exit(main())
