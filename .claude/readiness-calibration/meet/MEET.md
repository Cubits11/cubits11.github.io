# Readiness as a meet

A candidate dispatch rule. It is not wired into CI, and nothing here governs a dispatch
until the test in `PROTOCOL.md` has run. `readiness_meet.py` evaluates it.
`python3 readiness_meet.py --selftest` exits 0 when every property and control below holds.

## What it decides

A dispatch is admissible in a world when six obligations hold together:

| | obligation | holds when |
|---|---|---|
| A | authorization | a grant covers every action, and whoever issued the grant was entitled to issue it |
| I | identity | execution acts on the subject that was admitted: the dispatched bytes, the change set, and the tree the acceptance runs on |
| T | truth roots | the prompt's premises are the live roots' current state, and the executor can read those roots |
| Q | requirements | every required check passes now, evaluated per check |
| V | verification | completion is observable by a check that the builder does not grade alone |
| X | environment | the tools, runtime and access the task needs exist where it runs |

Every unresolved fact is a declared variable: a question with an enumerated answer set.
The compatible worlds Ω(K) are the assignments that no evidence rules out.

| decision | condition | what resolves it |
|---|---|---|
| INCONSISTENT | Ω(K) is empty | finding the contradiction in the evidence |
| READY | every compatible world admits | nothing; dispatch |
| REVIEW | some compatible worlds admit and some do not | an observation; the evaluator names the cheapest decisive one |
| HOLD | no compatible world admits | an intervention: change the prompt, the grant or the environment |

## Four corrections to the definition pasted on 2026-09-27

1. **An empty Ω(K) is not READY.** The pasted definition, READY iff every ω in Ω(K)
   satisfies C, is vacuously true when the evidence contradicts itself. 13.12 had that
   shape: its README said the key was sealed, and an unauthenticated fetch returned the
   key (d49480e). Control `C-INCONSISTENT`.
2. **REVIEW and HOLD differ in what resolves them.** REVIEW is resolved by looking;
   HOLD only by changing something. A HOLD whose change is a mechanical prompt clause can be
   discharged by the compiler without reaching the owner.
3. **The Kleene projection is sound but incomplete for HOLD.** If each obligation is
   scored 1, 0 or U, the meet is READY exactly when the world semantics is READY. The meet
   is never READY when the world semantics is not. It can say REVIEW when no world admits,
   because obligations that are each satisfiable can conflict through a shared variable.
   Control `C-GAP` has that shape: Blender exists only on the owner's Mac, and acceptance
   from the committed tree needs a clean clone. The evaluator decides on the worlds and
   reports the conflicting sets. Over 4,000 generated cases, 404 had that gap, and every
   one was of that form (Kleene REVIEW, world HOLD).
4. **Obligations are default-deny; 13.04's vetoes are default-allow.** A veto that nobody
   notices counts as absent, so `Hard Veto Count = 0` passes. Here an obligation with no
   evidence is rejected (`C-NO-EVIDENCE`), and a missing one is rejected
   (`C-MISSING-I`). In 13.10, V08 fired on none of six ASTRA rows. The batch then swept
   unrelated work into 14ca608 and broke T4 and T6 from a clean checkout. Both of those
   are identity failures.

Each rule is disabled in turn by `--selftest` and flips at least one named control.

## Mapping from 13.04

`MAPPING_1304` in the evaluator is the full table. Its splits:

- **V06** has two cases that 13.04 scores alike. *Unavailable* is X=0 (HOLD).
  *Unspecified* is X=U with the harness as the variable (REVIEW, one question). All four
  V06 firings in 13.10 were the unspecified case, and all four were immaterial. The brief's
  own macOS paths (`/Applications/Blender.app`, `~/Documents/...`) were evidence for the
  local harness.
- **Freshness** belongs to the controller, not the prompt (13.11 REVIEW F5). Stale
  doctrine disables the compiler; it does not lower a prompt's readiness.
- **Context economy, effort, subagents and harness simplicity** are routing. They change
  cost and model choice, not admissibility.
- **A01** splits into routing (bloat) and T (stale or conflicting instructions).
- **V09** splits into A (disclosure the executor is not entitled to) and routing
  (irrelevance).

## Findings in the prompt text, readable before any run

Each is a fact about a brief's text. I found them while re-reading rows whose outcomes I
already knew.

- **The ASTRA §A contract cannot be satisfied on the owner's working tree.** Rule 7 says
  `verification_manifest.py must exit 0 before any commit`. Known-open says
  `claims_history.yaml entry 38 fails the append-only check in the working tree. Do not commit around it.`
  FORBIDDEN lists `touching ... claims_history.yaml`. No task can meet rule 7 on that tree
  without the forbidden edit. A clean clone has no Blender. That is the `C-GAP` shape,
  and 13.04's V04 fired for none of the six rows on it. The record does not show whether
  the executor ran the manifest. The working tree had deleted the registration entry
  (index 38) of MC-005, since retracted; 26ce503 recorded that retraction as an appended
  RETRACT instead, three hours after the ASTRA commits, which still carry 39 entries.
- **No ASTRA row binds identity.** §A says `OUTPUT one commit per task`. It has no
  explicit-path commit, and its acceptance runs in the working tree. The FABLE brief added
  `Commit with explicit paths`, which guards against sweeping in unrelated work. It still
  does not run acceptance on the committed tree, which is the check that would have caught
  T4's and T6's missing dependency.

## Retrospective reading: post hoc, not evidence

`cases/retro_blind_rows.json` encodes the seven BLIND rows of 13.10 with the rules in its
header, and `retro_reading.txt` is the evaluator's output. The meet was proposed after
these outcomes were known, by a reader of the retrospective workbook. The encoding was
written by the session that audited the outcomes. Agreement with the outcomes is built in
by construction and is not reported as support.

| row | 13.04 (frozen) | meet, strict I | smallest change that leaves HOLD | outcome (13.10, provisional) |
|---|---|---|---|---|
| T1 | HOLD V04 | HOLD (I) | compiler I-clause → REVIEW on harness + K7 | acceptance PASS; K7 for the owner |
| T2 | HOLD V06 | HOLD (I) | compiler I-clause + owner fixes entry 38 → REVIEW on harness | UNVERIFIED |
| T3 | HOLD V06, core 81 | HOLD (I) | the same | PASS reproduced; FALSE HOLD |
| T4 | HOLD V06, verif 7 | HOLD (I, V) | + owner adjudicates the mappings | PARTIAL; broke on a missing dependency (I) |
| T5 | HOLD V06, goal 12 | HOLD (I, V) | + a named load check | PARTIAL; browser load never verified (V) |
| T6 | HOLD core 77 | HOLD (I, V) | + an independent grader | FAIL at run commit on a missing dependency (I) |
| SPINE | READY | HOLD (I) | compiler I-clause → REVIEW on the room label | PASS; the one deviation was the room label |

Under the lenient reading of I (explicit paths alone), the spine is REVIEW rather than
HOLD, and every ASTRA row stays HOLD. Under the strict reading the spine is a FALSE HOLD
whose fix is one compiled clause. `PROTOCOL.md` fixes the strict reading before any
prospective case is scored.

## What this does not establish

- That the meet predicts outcomes better than 13.04. No prospective case has been scored.
- That the obligation list is complete. Six is the list pasted on 2026-09-27. Nothing
  here tests whether a seventh is needed.
- That the variables and evidence in any case are right. The evaluator checks structure:
  every obligation is present, every unknown is named, and every assertion cites evidence.
  Whether the evidence is true is outside it.
- That a REVIEW's named observation is the cause of any later failure.
