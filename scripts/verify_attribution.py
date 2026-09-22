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

One exemption, and its reasoning. On a merge GitHub writes -- the synthetic
commit CI builds to test a pull request, and the commit the merge button
writes -- the author stays the person and the committer becomes
`GitHub <noreply@github.com>`. That committer slot is plumbing, not authorship,
and a rule that failed on it would fail on every merge into main forever. So on
a commit with two or more parents whose committer is exactly that identity, the
committer slot alone is exempt. The author is always checked, so a merge still
names a person; a single-parent commit made as GitHub is someone committing as
GitHub and fails; and a merge authored by a model fails on its author.

The exemption is not exempt from the trailer check, and the merge's parents are
each checked on their own, which is where content actually enters.

The residual: a merge commit can carry conflict-resolution content that exists
in no parent, and that content is attributed only by the merge's author. That is
accepted rather than hidden. Closing it would mean checking merge-diff
provenance, which is a different gate than this one.

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


# GitHub's own merge identity. See the exemption in the module docstring.
WEB_FLOW = ("github", "noreply@github.com")


def identities_to_check(parents: str, an: str, ae: str, cn: str, ce: str):
    """Which identities the rule binds on this commit.

    On a merge, GitHub commits on the owner's behalf: the author stays the
    person, the committer becomes `GitHub <noreply@github.com>`. Only that
    committer slot is exempt, and only on a merge. The author is always
    checked, so a merge still names a person, and a single-parent commit
    made as GitHub is someone committing as GitHub and fails.

    One function so the gate and its fixtures cannot disagree.
    """
    roles = [("author", an, ae)]
    committer_is_plumbing = (
        len(parents.split()) > 1
        and (cn.strip().lower(), ce.strip().lower()) == WEB_FLOW
    )
    if not committer_is_plumbing:
        roles.append(("committer", cn, ce))
    return tuple(roles)


def violations(sha: str) -> list[str]:
    record = git("show", "-s", "--format=%an%n%ae%n%cn%n%ce%n%P%n%B", sha)
    an, ae, cn, ce, parents, *body = record.split("\n")
    found: list[str] = []
    for role, name, email in identities_to_check(parents, an, ae, cn, ce):
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

    # The web-flow exemption, exercised through the function the gate uses.
    # An earlier version of these fixtures re-implemented the condition inline
    # and so agreed with a bug the gate had; they now call identities_to_check.
    OWNER = ("Cubits11", "90584946+Cubits11@users.noreply.github.com")
    GH = ("GitHub", "noreply@github.com")
    for label, parents, author, committer, expect_roles in (
        # What GitHub actually builds for a PR: owner authors, GitHub commits.
        ("pr test merge", "aaa bbb", OWNER, GH, ("author",)),
        ("merge button", "aaa bbb", OWNER, GH, ("author",)),
        # Not a merge: committing as GitHub is not exempt.
        ("single parent as github", "aaa", GH, GH, ("author", "committer")),
        # A merge does not launder the author.
        ("merge authored by a model", "aaa bbb", ("Claude", "noreply@anthropic.com"),
         GH, ("author",)),
        # An ordinary local merge is checked on both slots.
        ("local merge", "aaa bbb", OWNER, OWNER, ("author", "committer")),
    ):
        got = tuple(r for r, _, _ in identities_to_check(
            parents, author[0], author[1], committer[0], committer[1]))
        if got != expect_roles:
            failures.append(f"  web-flow {label}: expected {expect_roles}, got {got}")

    # The exemption must not let a model-authored merge through.
    bad = identities_to_check("aaa bbb", "Claude", "noreply@anthropic.com",
                              "GitHub", "noreply@github.com")
    if not any(e.lower() not in PERMITTED_EMAILS for _, _, e in bad):
        failures.append("  web-flow: a model-authored merge was not caught")
    if failures:
        print(f"attribution fixtures: {len(failures)} failed")
        print("\n".join(failures))
        return 1
    print(f"attribution fixtures: {len(FIXTURES) + 9} passed")
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
