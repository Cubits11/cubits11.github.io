#!/usr/bin/env python3
"""The fourteen blocker markers, resolved into the six human actions behind them.

The evidence ledger counts markers. Markers are not decisions: five of them are
one license acceptance, three are one message. This groups them, orders them by
what unblocks the most, and prints each as clicks and commands rather than
prose. It reads live state, so an action disappears from the list when the
thing it was waiting for is actually true.

    python3 scripts/owner_actions.py          # all open actions, ordered
    python3 scripts/owner_actions.py --one    # only the next one

It sends nothing and clears nothing. Every step below is the owner's hand.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / ".claude" / "skills" / "evidence-ledger" / "ledger.py"


def hits() -> list[dict]:
    spec = importlib.util.spec_from_file_location("_ledger", LEDGER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [h for h in mod.blocking_block()["hits"] if h.get("state") == "open"]


def e2_licenses_pending() -> int:
    p = ROOT / "experiments" / "e2" / "freeze" / "sources.json"
    s = json.loads(p.read_text(encoding="utf-8"))
    return sum(1 for g in s["guards"]
               if str(g.get("license_bytes_sha256", "")).startswith("OWNER-PENDING"))


def enrolment_rows() -> int:
    p = ROOT / "trials" / "necromancer" / "pilot" / "responses" / "enrolment.csv"
    if not p.exists():
        return 0
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines()
               if ln.strip() and not ln.lstrip().startswith("#"))


def remote_branches() -> set[str]:
    try:
        out = subprocess.run(["git", "ls-remote", "--heads", "--tags", "origin"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        return {ln.split("refs/")[-1] for ln in out.stdout.splitlines() if "refs/" in ln}
    except Exception:
        return set()


def qualified_zero() -> bool:
    spec = importlib.util.spec_from_file_location("_ledger", LEDGER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return int(mod.outcomes_block().get("qualified_total", 0)) == 0


def build() -> list[dict]:
    """Open actions, most-unblocking first. Each is one sitting."""
    open_hits = hits()
    by_file = {}
    for h in open_hits:
        by_file.setdefault(h["file"], []).append(h)
    age = max((h["age_days"] for h in open_hits), default=0)

    A: list[dict] = []

    n = e2_licenses_pending()
    if n:
        A.append({
            "id": "A1",
            "title": f"Accept three Hugging Face licenses, then seal their hashes",
            "clears": 6,
            "why": "Six markers are this one action. Until it is done E2 has no "
                   "collection path and K1 is not evaluable, which is why "
                   "PREREG_SELECTION.md:397 reads `not evaluable`.",
            "minutes": 10,
            "steps": [
                "Open each, signed in, and click the accept/agree button:",
                "    https://huggingface.co/meta-llama/Llama-Guard-4-12B",
                "    https://huggingface.co/meta-llama/Llama-Guard-3-8B",
                "    https://huggingface.co/google/shieldgemma-2b",
                "Make a READ token at https://huggingface.co/settings/tokens",
                "Then, on any machine with this repo (not necessarily the authorized box —",
                "this hashes license text, it does not load a guard):",
                "    export HF_TOKEN=hf_...",
                "    python3 experiments/e2/freeze/seal_licenses.py --check   # see it first",
                "    python3 experiments/e2/freeze/seal_licenses.py",
                "    python3 scripts/verification_manifest.py",
                "    git commit -am 'e2: seal three gated license hashes on authenticated pull'",
            ],
            "note": "config_hash WILL change. Three fields declared pending became "
                    "known; that is the freeze completing, not a frozen file moving "
                    "after outcomes. No outcome has been observed.",
        })

    if enrolment_rows() == 0 and any("necromancer" in f for f in by_file):
        A.append({
            "id": "A2",
            "title": "Send Message 1 of the Trial IV invitation to ten people",
            "clears": 3,
            "why": "Three markers, one action, open since 2026-09-02 with zero "
                   "receipts. This is the only thing between this repository and "
                   "its first human observation.",
            "minutes": 20,
            "steps": [
                "Text is frozen in trials/necromancer/pilot/INVITATION.md (Message 1).",
                "Send it as-is. Do not explain the trial, the arms, or the rule.",
                "Ten separate messages, not one thread: they must not see each other.",
                "Write the date sent and the 14-day deadline on line 1 of",
                "    trials/necromancer/pilot/responses/enrolment.csv",
                "As each IN arrives: append slot,timestamp,contact in ARRIVAL order,",
                "then send Message 2 with that slot.",
                "On the deadline:  python3 scripts/trial_score.py",
            ],
            "note": "Ten invitations to people who already know you is not a "
                    "qualified outcome and the trial does not claim it is. It is a "
                    "cold-comprehension diagnostic. That is still the first row.",
        })

    if by_file.get("ARTIFACTS/2026-09-07-RECONCILIATION.md"):
        present = remote_branches()
        stale = [b for b in ("heads/claude/foundations-push-cleanup",
                             "heads/claude/mc-005-selection-regret") if b in present]
        tags = [t for t in ("tags/archive/claude-spine-b454285",
                            "tags/archive/codex-production-audit-fb754db") if t in present]
        if not stale and len(tags) == 2:
            A.append({
                "id": "A3", "clears": 1, "minutes": 1,
                "title": "Close a stale marker: this reconciliation work is already done",
                "why": "Checked against origin just now: both archive tags are "
                       "pushed and both merged branches are already deleted. The "
                       "marker has been aging for 15 days over completed work.",
                "steps": [
                    "Verify for yourself:",
                    "    git ls-remote --tags origin | grep archive",
                    "    git ls-remote --heads origin | grep -E 'foundations-push-cleanup|mc-005'",
                    "Then edit ARTIFACTS/2026-09-07-RECONCILIATION.md:36 to record the",
                    "date the pushes and deletions actually happened, so the marker stops",
                    "being counted as open.",
                    "",
                    "Still genuinely open, and not markers — two judgement calls:",
                    "  origin/claude/success-upgrade-i8gfz8 — UNCERTAIN, left for you.",
                    "    Its withdrawn-vs-unreachable distinction in verify_claims.py looks new.",
                    "  PR 18 codex/external-queue-reconciliation — recommend CLOSE without merge;",
                    "    merging reverts DISPATCH.md C to NOT SENT and deletes the X record.",
                ],
                "note": "A marker that outlives its action teaches you to ignore markers.",
            })
        else:
            A.append({
                "id": "A3",
                "title": "Push the two archive tags and delete the two merged remote branches",
                "clears": 1,
                "why": "Bookkeeping from the 2026-09-07 reconciliation. Cheapest marker "
                       "on the board and it has been open 15 days.",
                "minutes": 2,
                "steps": [
                    "git push origin archive/claude-spine-b454285 archive/codex-production-audit-fb754db",
                    "git push origin --delete claude/foundations-push-cleanup claude/mc-005-selection-regret",
                    ("  (checked: both branches still exist on origin)" if len(stale) == 2
                     else f"  (checked: {len(stale)} of 2 still exist on origin — skip the gone ones)"),
                    "",
                    "Separately, two judgement calls the reconciliation left open:",
                    "  origin/claude/success-upgrade-i8gfz8 — UNCERTAIN, left for you.",
                    "    Its withdrawn-vs-unreachable distinction in verify_claims.py looks new.",
                    "  PR 18 codex/external-queue-reconciliation — recommend CLOSE without merge;",
                    "    merging reverts DISPATCH.md §C to NOT SENT and deletes the X record.",
                ],
                "note": None,
            })

    if by_file.get("distribution/CAMPAIGN-2026-09-10.md"):
        A.append({
            "id": "A4",
            "title": "Write the LessWrong post, in your own hand",
            "clears": 1,
            "why": "The packet is prepared; the prose deliberately is not. A post "
                   "about epistemic honesty that was not written by its byline is "
                   "self-refuting, and that audience detects assembled prose.",
            "minutes": 180,
            "steps": [
                "Packet and five-beat spine: distribution/CAMPAIGN-2026-09-10.md, LessWrong section.",
                "Beat 3 is the void beat (E7). Do not soften it, do not bury it.",
                "State n=21 in the same breath as the E7B result.",
                "Credit arXiv:2607.22868 in the paragraph, not a footnote.",
                "I can review a draft against the packet, the registry and the",
                "non-claims. I will not draft it and you should not let me.",
            ],
            "note": "This is the single highest-leverage open item for T2 and it is "
                    "the one I am least able to help with. That is not a coincidence.",
        })

    if qualified_zero() and by_file.get("ARTIFACTS/12-WEEK-PROGRAM.md"):
        A.append({
            "id": "A5",
            "title": "Chase the two sent asks; dispatch the third",
            "clears": 1,
            "why": "W9's artifact is outcomes.yaml entries, qualified or zero. Two "
                   "asks were sent 2026-09-02 and 2026-09-05 and have been pending "
                   "since. A silence recorded is a result; a silence unrecorded is not.",
            "minutes": 25,
            "steps": [
                "IBM/Adversarial-Prompt-Evaluation issue 7 — sent 2026-09-02, no reply.",
                "    One short follow-up, or record the silence as zero and stop.",
                "BELLS selection question — issue 1, sent 2026-09-16, open, no comments.",
                "GuardBench reporter patch (contrib/guardbench_joint.py) — PREPARED, NOT SENT.",
                "    Draft is in distribution/DISPATCH.md. This is the next dispatch.",
                "Record every outcome, including refusal and silence, in",
                "    distribution/outcomes.yaml (technical_interaction_log)",
                "Stop rule: 12 technical interactions with 0 qualified. You are at 4.",
            ],
            "note": "One dispatch, not twenty. Your own campaign file says a "
                    "broadcast is not an engagement, and the stop rule counts "
                    "interactions rather than recipients for that reason.",
        })

    A.append({
        "id": "A6",
        "title": "Close what will never be cleared",
        "clears": 0,
        "why": "A blocker nobody will ever act on is not a blocker, it is a "
               "declared limit being stored in the wrong shape, and it ages the "
               "oldest-blocker counter forever.",
        "minutes": 15,
        "steps": [
            "For each marker still open after A1-A5, answer one question:",
            "  will I actually do this, ever?",
            "If no: replace the marker with the sentence this repository publishes",
            "about its own ceiling, and record the date it was closed as a limit.",
            "A closed limit is auditable. An immortal OWNER-PENDING is not.",
        ],
        "note": f"Oldest open marker is {age} days.",
    })
    return A


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--one", action="store_true", help="only the next action")
    a = ap.parse_args()
    A = build()
    if a.one:
        A = A[:1]
    total = sum(x["clears"] for x in A)
    print(f"OWNER ACTIONS · {len(A)} action(s) · {total} marker(s) clear on completion\n")
    for x in A:
        print(f"  {x['id']}  {x['title']}")
        print(f"      clears {x['clears']} marker(s) · about {x['minutes']} min")
        for line in x["why"].split(". "):
            if line.strip():
                print(f"      {line.strip().rstrip('.')}.")
        print()
        for s in x["steps"]:
            print(f"        {s}")
        if x["note"]:
            print()
            print(f"      NOTE  {x['note']}")
        print()
    print("  Nothing here is sent, accepted, pushed or deleted by this repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
