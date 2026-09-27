#!/usr/bin/env python3
"""Owner step D4: append the two falsifier-assessment transcriptions, then close the exemption.

Run by the owner from the repository root, on a branch that contains c1b71f9
(claude/falsifier-assessment-kernel) and REL-001's review, because Drive 10 D4
condition 1 requires the kernel change to pass scripts/verification_manifest.py
first. This script refuses otherwise. It does not commit; it prints the command.

Steps, each stopping on failure:
  1. preflight: the branch contains c1b71f9, the tree is clean, the kernel verifies,
     neither subject is assessed yet, and each quote is on its cited line verbatim;
  2. the manifest exits 0 (D4 condition 1);
  3. `claims_history.py assess` twice (each appends only if the candidate chain verifies);
  4. delete LEGACY_UNASSESSED, LEGACY_END and the exemption from
     tests/test_correction_dispositions.py, as its own failing check demands;
  5. re-run the kernel, the dispositions test and the manifest.

Usage:  python3 .claude/glassroot/owner/d4_transcribe.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
KERNEL_COMMIT = "c1b71f9"
DRIVE_D4 = "drive:1VlYFw2z5_glEEk45NaBnKdb_C9vlCWlo33VLV8H7C-E#D4"
DECLARED_IN = "git:48e98e44be87497bcd0c4c650e8123efde98c625"
REASON = ("Transcribes the declaration dated 2026-09-10, first present in git at 48e98e4 (2026-09-15): "
          "'{quote}' Not a new judgment. Authorized by Drive 10 decision D4 (delegated, 2026-09-25).")

ENTRIES = [
    {"claim": "E6-001", "subject": "3405d1d9d4f086cf17ebc7a1217fc9e563448a65d50293641ca170b61fa59c23",
     "value": "NOT_FIRED", "source": ("experiments/e6/CORRECTION-2026-09-10.md", 9),
     "quote": ("The old falsifier did not explicitly test preservation of marginal masses. Rejection is "
               "recorded on the stronger direct evidence; it is not misrepresented as an old "
               "numerical-tolerance test firing."),
     "evidence": ["experiments/e6/CORRECTION-2026-09-10.md:9",
                  "corrections/records/2026-09-10.json#records[0].basis",
                  "claims_history.yaml#entries[48].reason"]},
    {"claim": "E7B-001", "subject": "4a8f7a510eff285e97aa79495fe51982ce1c96074550723d8d9f2093375aeea5",
     "value": "FIRED", "source": ("experiments/e7b/CORRECTION-2026-09-10.md", 9),
     "quote": ("The preregistration-conformance falsifier in E7B-001 explicitly covers an applied "
               "operating-point rule differing from `PREREG.md`. Its fixed consequence is REJECT. "
               "That condition is met."),
     "evidence": ["experiments/e7b/CORRECTION-2026-09-10.md:9",
                  "corrections/records/2026-09-10.json#records[1].basis",
                  "claims_history.yaml#entries[49].reason"]},
]

TEST = "tests/test_correction_dispositions.py"
TEST_EDITS = [
    ("""# Drive 09 requires a falsifier assessment for every governed correction. These two predate the assessment kind,
# and their transcription is the owner's decision (Drive 10, D4). The exemption can only shrink: its members are
# transition digests, each a transition recorded before the kind existed (entries[:50], which the kernel's
# append-only rule keeps fixed); it must equal exactly the governed legacy corrections still unassessed, so an
# appended assessment fails until its digest is deleted here, and a member cannot be deleted without one; an
# empty set fails, so the exemption is removed with its last member.
LEGACY_UNASSESSED=frozenset({
    '3405d1d9d4f086cf17ebc7a1217fc9e563448a65d50293641ca170b61fa59c23',  # E6-001 entries[48]
    '4a8f7a510eff285e97aa79495fe51982ce1c96074550723d8d9f2093375aeea5',  # E7B-001 entries[49]
})
LEGACY_END=50
""", ""),
    ("""        # falsifier FIRED; NOT_FIRED asserts no relation. A governed correction with no assessment fails, except
        # for the members of LEGACY_UNASSESSED.
        hist=yaml.safe_load((ROOT/'claims_history.yaml').read_text())
        legacy={e['digest'] for e in hist['entries'][:LEGACY_END] if e.get('kind')=='transition'}
        known=history.commitments_by_digest(hist)
        unassessed=set()
""", """        # falsifier FIRED; NOT_FIRED asserts no relation. A governed correction with no assessment fails.
        hist=yaml.safe_load((ROOT/'claims_history.yaml').read_text())
        known=history.commitments_by_digest(hist)
"""),
    ("""            rel=history.falsifier_relation(hist,t,pred)
            if rel=='FIRED':self.assertEqual(row['disposition'],pred['falsifier']['consequence'],row['claim_id'])
            elif rel=='UNASSESSED':
                self.assertIn(t['digest'],legacy,f"{row['claim_id']}: a governed correction needs a falsifier assessment")
                unassessed.add(t['digest'])
        self.assertEqual(set(LEGACY_UNASSESSED),unassessed,'the exemption lists exactly the legacy corrections still unassessed')
        self.assertTrue(LEGACY_UNASSESSED,'the exemption is empty: delete LEGACY_UNASSESSED, LEGACY_END and this check')
""", """            rel=history.falsifier_relation(hist,t,pred)
            self.assertNotEqual(rel,'UNASSESSED',f"{row['claim_id']}: a governed correction needs a falsifier assessment")
            if rel=='FIRED':self.assertEqual(row['disposition'],pred['falsifier']['consequence'],row['claim_id'])
"""),
]


def run(*cmd: str, quiet: bool = False) -> int:
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=quiet, text=True)
    if quiet and r.returncode:
        print((r.stdout + r.stderr)[-3000:])
    return r.returncode


def stop(msg: str) -> None:
    print(f"STOP  {msg}")
    sys.exit(1)


def preflight() -> None:
    if subprocess.run(["git", "merge-base", "--is-ancestor", KERNEL_COMMIT, "HEAD"], cwd=ROOT).returncode:
        stop(f"this branch does not contain {KERNEL_COMMIT} (the kernel with assess and resolve)")
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        stop("the working tree is not clean")
    if run(sys.executable, "scripts/claims_history.py", "verify", quiet=True):
        stop("the claim-history kernel does not verify before the appends")
    import yaml
    assessed = {x.get("subject_transition_digest") for x in
                yaml.safe_load((ROOT / "claims_history.yaml").read_text())["entries"]
                if x.get("kind") == "falsifier_assessment"}
    for e in ENTRIES:
        path, line = e["source"]
        text = (ROOT / path).read_text().splitlines()[line - 1]
        if e["quote"] not in text:
            stop(f"{e['claim']}: the quote is not verbatim on {path}:{line}")
        if e["subject"] in assessed:
            stop(f"{e['claim']}: an assessment of this subject already exists")
    print("ok    preflight: branch, clean tree, kernel verifies, quotes verbatim, subjects unassessed")


def gate_manifest(when: str) -> None:
    if run(sys.executable, "scripts/verification_manifest.py", quiet=True):
        stop(f"verification_manifest.py does not exit 0 {when} (Drive 10 D4 condition 1). "
             "If only REL-001 and unreachable URLs fail, the owner's REL-001 review comes first.")
    print(f"ok    manifest exits 0 {when}")


def append() -> None:
    for e in ENTRIES:
        args = [sys.executable, "scripts/claims_history.py", "assess", "--subject", e["subject"],
                "--value", e["value"], "--reason", REASON.format(quote=e["quote"])]
        for ref in e["evidence"] + [DECLARED_IN, DRIVE_D4]:
            args += ["--evidence", ref]
        if run(*args):
            stop(f"{e['claim']}: assess refused; nothing further is appended")


def close_exemption() -> None:
    p = ROOT / TEST
    s = p.read_text()
    for old, new in TEST_EDITS:
        if s.count(old) != 1:
            stop(f"{TEST} is not the file this script was written against; edit it by hand")
        s = s.replace(old, new)
    p.write_text(s)
    print(f"ok    {TEST}: exemption removed")


def after() -> None:
    import yaml
    before = yaml.safe_load(subprocess.run(["git", "show", "HEAD:claims_history.yaml"], cwd=ROOT,
                                           capture_output=True, text=True, check=True).stdout)
    now = yaml.safe_load((ROOT / "claims_history.yaml").read_text())
    added = now["entries"][len(before["entries"]):]
    now["entries"] = now["entries"][:len(before["entries"])]
    if now != before or [e.get("kind") for e in added] != ["falsifier_assessment"] * 2:
        stop("claims_history.yaml changed beyond the two appended assessments")
    print("ok    parsed, the file equals HEAD plus exactly two assessments "
          "(line re-wrapping by yaml.safe_dump is formatting only)")
    if run(sys.executable, "scripts/claims_history.py", "verify", quiet=True):
        stop("the kernel does not verify after the appends")
    if run(sys.executable, "-m", "unittest", "tests.test_correction_dispositions", quiet=True):
        stop("the dispositions test fails after the appends")


def main() -> int:
    preflight()
    gate_manifest("before the appends")
    append()
    close_exemption()
    after()
    gate_manifest("after the appends")
    print("\nReview `git diff`, then commit with explicit paths:\n")
    print("  git add claims_history.yaml tests/test_correction_dispositions.py")
    print("  git commit -m 'claims history: transcribe the two 2026-09-10 falsifier declarations (Drive 10 D4)'")
    print("\nThe entries become permanent when merged to main (D4 condition 5). The merge is the owner's.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
