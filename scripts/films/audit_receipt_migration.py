#!/usr/bin/env python3
"""One-off audit of the receipt migration, by the old whole-file rule.

    python3 scripts/films/audit_receipt_migration.py --old <rev> [--new <rev>]

It imports nothing from the new verifier or facts_digest.py; it reads git
objects and the worktree only. For every render receipt at --old (whole-file
rule) and the same receipt at --new (default: the worktree; subset rule):

  1. The old rule, as --old applied it: the old receipt names the sha256 of
     films/data/facts.json. Find the exact bytes with that sha256 in the file's
     git history: the facts file the old receipt certified.
  2. Every fact the film displays (facts_used; old and new must name the same
     set) has the same value in the certified file as in the facts file at
     --new.
  3. The new receipt's facts_subset sha256 equals sha256 of canonical JSON
     {fact_id: value} over those facts, computed here from the certified file.
  4. The frames_digest is unchanged, and the encoded video bytes are reported.
  5. The old rule applied to --new: is the facts file at --new byte-identical
     to the certified one?

Then every pair of consecutive facts.json revisions in history is replayed
against the receipts at --new: which receipts each rule would have made stale,
and which facts changed. That part is counterfactual: the films did not all
exist, or read the same facts, at every revision.

Exit 1 if any receipt fails 1-4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACTS = "films/data/facts.json"


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def read(rev: str | None, path: str) -> bytes:
    return (ROOT / path).read_bytes() if rev is None else git("show", f"{rev}:{path}")


def receipts(rev: str | None) -> list[str]:
    if rev is None:
        return sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("films/*/renders/*.receipt.json"))
    names = git("ls-tree", "-r", "--name-only", rev, "--", "films").decode().split("\n")
    return sorted(n for n in names if n.endswith(".receipt.json") and "/renders/" in n)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def subset_sha(facts: dict, ids: list[str]) -> str:
    # written here again on purpose, from the rule's words, not imported
    body = json.dumps({i: facts[i]["value"] for i in ids}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha(body.encode())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", default=None, help="a revision; default the worktree")
    args = ap.parse_args()
    old_rev = git("rev-parse", args.old).decode().strip()
    new_rev = git("rev-parse", args.new).decode().strip() if args.new else None

    history = git("log", "--format=%H", old_rev, "--", FACTS).decode().split()
    by_sha: dict[str, tuple[str, bytes]] = {}
    for rev in reversed(history):  # oldest first, so a repeated digest keeps its first revision
        b = git("show", f"{rev}:{FACTS}")
        by_sha.setdefault(sha(b), (rev, b))
    new_bytes = read(new_rev, FACTS)
    new_facts = json.loads(new_bytes)["facts"]

    print(f"old {old_rev[:12]} (whole-file rule) -> new {new_rev[:12] if new_rev else 'worktree'} (subset rule)")
    print(f"facts.json at new: sha256 {sha(new_bytes)[:12]}, {len(new_facts)} facts\n")
    print(f"{'receipt':<52} {'certified facts.json':<22} {'shown':>5} {'values':>6} {'subset':>6} {'frames':>6} {'video':>7} {'old rule @ new':>15}")
    failures = 0
    old_names, new_names = receipts(old_rev), receipts(new_rev)
    if old_names != new_names:
        print(f"FAIL  receipt inventory differs: only old {sorted(set(old_names) - set(new_names))}, only new {sorted(set(new_names) - set(old_names))}")
        failures += 1
    for name in old_names:
        if name not in new_names:
            continue
        old = json.loads(read(old_rev, name))
        new = json.loads(read(new_rev, name))
        problems = []
        digest = old["inputs"].get(FACTS)
        if digest not in by_sha:
            problems.append(f"old receipt certifies facts.json {digest} found nowhere in its history")
            certified_rev, certified = "-", None
        else:
            certified_rev, certified_bytes = by_sha[digest]
            certified = json.loads(certified_bytes)["facts"]
        if sorted(old["facts_used"]) != sorted(new["facts_used"]):
            problems.append(f"facts_used differs: old {old['facts_used']} new {new['facts_used']}")
        shown = sorted(new["facts_used"])
        values_equal = certified is not None and all(
            f in certified and f in new_facts and
            json.dumps(certified[f]["value"], sort_keys=True) == json.dumps(new_facts[f]["value"], sort_keys=True)
            for f in shown)
        if not values_equal:
            problems.append("a displayed fact's value differs between the certified file and the new one")
        bound = (new.get("facts_subset") or {}).get("sha256")
        subset_ok = certified is not None and bound == subset_sha(certified, shown)
        if not subset_ok:
            problems.append(f"new facts_subset {bound} is not the digest of the certified values")
        if FACTS in new.get("inputs", {}):
            problems.append("new receipt still binds the whole facts file")
        frames_ok = old["frames_digest"] == new["frames_digest"]
        if not frames_ok:
            problems.append(f"frames_digest changed: {old['frames_digest'][:12]} -> {new['frames_digest'][:12]}")
        video = "same" if old["outputs"]["master_sha256"] == new["outputs"]["master_sha256"] else "differs"
        old_rule_now = "fresh" if sha(new_bytes) == digest else "STALE"
        cut = name.split("/")[-1].removesuffix(".receipt.json")
        print(f"{cut:<52} {sha(certified_bytes)[:12] + ' @ ' + certified_rev[:7] if certified else '-':<22} {len(shown):>5} "
              f"{'equal' if values_equal else 'DIFF':>6} {'equal' if subset_ok else 'DIFF':>6} "
              f"{'same' if frames_ok else 'DIFF':>6} {video:>7} {old_rule_now:>15}")
        for p in problems:
            print(f"FAIL  {cut}: {p}")
        failures += bool(problems)

    # counterfactual replay of history against today's receipts
    print("\nfacts.json history replayed against the receipts at new (counterfactual):")
    print(f"{'revision':<10} {'date':<11} {'facts changed':>13} {'stale, whole-file rule':>23} {'stale, subset rule':>19}  changed facts")
    new_receipts = [json.loads(read(new_rev, n)) for n in new_names]
    chain = list(reversed(history))
    for prev, rev in zip(chain, chain[1:]):
        a_bytes, b_bytes = git("show", f"{prev}:{FACTS}"), git("show", f"{rev}:{FACTS}")
        a, b = json.loads(a_bytes)["facts"], json.loads(b_bytes)["facts"]
        stale_old = len(new_receipts) if sha(a_bytes) != sha(b_bytes) else 0
        changed = sorted(k for k in set(a) | set(b) if json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True))
        changed_values = {k for k in changed if json.dumps((a.get(k) or {}).get("value"), sort_keys=True)
                          != json.dumps((b.get(k) or {}).get("value"), sort_keys=True) or (k in a) != (k in b)}
        stale_new = sum(1 for r in new_receipts if changed_values & set(r["facts_used"]))
        when = git("show", "-s", "--format=%as", rev).decode().strip()
        listed = ", ".join(changed[:4]) + (f" … +{len(changed) - 4}" if len(changed) > 4 else "")
        print(f"{rev[:8]:<10} {when:<11} {len(changed):>13} {stale_old:>20}/{len(new_receipts)} {stale_new:>16}/{len(new_receipts)}  {listed}")
    print(f"\n{failures} receipt(s) failed the audit")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
