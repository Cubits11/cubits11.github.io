# PC-001 · Trial IV pilot — frozen protocol

Dated 2026-09-02. Frozen before any human has answered. The sha256 of every
input named below is in `freeze.json`, written by
`python3 scripts/verify_trial.py --freeze` and re-asserted by
`python3 scripts/verify_trial.py` on every push. **After the first receipt
is in, an edit to any frozen input is a forbidden rescue and voids the
affected result.** The instrument is `/trials/necromancer/`; the manifest
`trials/necromancer/manifest.yaml` wins any conflict with this prose.

## Proposition

A 20-minute experience built from this repository's enforced conventions
causes a person to sort post-result moves correctly into forbidden rescue,
legitimate correction, and unwarranted surrender — on a claim they have
never seen, in a field they do not work in, with the mythology stripped out.

Status: HYPOTHESIS. No human has answered. Nothing here asserts the method
works, is novel, is a standard, or is certifiable.

## Design

- **Two arms.** Identical claim, result, moves and clock. Arm A commits the
  seal — falsifier, fixed consequence, forbidden moves — before the decisive
  evidence. Arm B commits the same seal after the evidence, before the moves.
- **Assignment.** Ten enrolment slots. Within each consecutive pair (1,2),
  (3,4), … the slot with the lower
  `sha256("PC-001-NECROMANCER-2026-09-02:" + slot)` is arm A and the other arm
  B, so any even number of acceptances is balanced. The table is in
  `freeze.json` and embedded in the page; the runtime only looks it up. **A person's slot is the order in which their acceptance
  reply arrives**, recorded with the reply's timestamp in
  `responses/enrolment.csv` before the slot is sent. The owner invites; the
  owner does not choose who gets which slot.
- **Pre-task.** Both arms sort the same unseen bare case (`pre`, a bakery)
  before any instruction. No feedback.
- **Trained case.** The stack (two content filters, 100 items, 9 joint
  misses). Publish → seal → evidence → eight moves → debrief with the rule and
  its repository source for each move → update the claim → recall the rule.
- **Cold transfer case.** A bare case in another field (`cold`, a bus
  depot). Eight moves, same eight templates, no mythology, no feedback.
- **Receipt.** The page stores and sends nothing. The learner copies a JSON
  receipt and returns it by replying to the invitation. Each receipt carries
  the instrument hash and the slot; the scorer refuses any receipt whose hash
  or slot→arm mapping is not the frozen one.

## Outcomes

**Primary, one:** correct sorts out of eight on the cold transfer case,
scored against the withheld key file (`keys_sha256` in `freeze.json`; the
file is committed to this directory only after every response is in).

Secondary, reported in full, deciding nothing: the pre-task score, the
trained-case score, the seal (consequence and forbidden candidates), the
updated claim verbatim, the rule recalled verbatim, confidence (1–5),
self-reported help from the trained case (1–5), per-phase and total time,
free comment.

## Decision rule

Let `medA`, `medB` be the arms' medians on the primary outcome and `preA`,
`preB` their medians on the pre-task.

| condition | decision |
| --- | --- |
| `medA − medB ≥ 2` | CONTINUE |
| `1 ≤ medA − medB < 2` | NARROW to the two-way sort (rescue vs not-rescue) |
| `medA − medB < 1` | KILL |
| `medA ≤ preA` or `medB ≤ preB` (either arm fails to strictly beat its own pre-task) | KILL, checked first |
| `n < 8`, or either arm outside 4…5 | UNDETERMINED — `scripts/trial_score.py` exits 2; nothing is concluded |

Medians are the standard median (middle value, or the mean of the two middle
values); with four per arm a median can be a half-integer, and the bands are
stated so every value falls in exactly one: `1.5` narrows, `0.5` kills.

**When it is scored.** Once, at the return deadline: 14 days after the
first invitation is sent, the date written in `responses/enrolment.csv`.
Every receipt in by then is scored; none after. The owner does not score
early and does not wait for a number to move.

## Exclusions, fixed now

- The first receipt returned per slot counts; any later receipt for the same
  slot is kept in `responses/` and not scored.
- A receipt whose `instrument_hash` is not the frozen one, or whose `slot`
  maps to a different arm than `freeze.json`, is refused by the scorer.
- A receipt whose phase list is not its arm's full order is refused.
- A seal hash of `unavailable` (no Web Crypto in the browser) is scored; the
  hash is tamper-evidence, not an outcome.
- Time is never an exclusion; a slow receipt is scored and its time reported.
- A learner who says in their reply that they re-enrolled after losing the
  page is scored on the receipt they returned and flagged in the report.

## Forbidden rescues for this pilot

Writing more curriculum. A second trial. A certificate. A landing page.
Renaming a failure a "pilot design finding". Relaxing the decision rule
after seeing a number. Recruiting until the number moves. Substituting an
easier transfer case. Concluding from reactions, confidence, time,
self-report, or the trained case. Concluding from n below eight. Concluding
anything before humans answer.

## What counts against the lesson, beyond the rule

- Either arm's cold median at or below its pre-task median (the KILL above).
- The trained-case debrief score not exceeding the pre-task score in most
  learners — the lesson did not even teach its own case.
- Rule recall that does not contain both halves (fixed before; nothing
  frozen moves / nothing untouched falls) in most learners.
- Total time over 30 minutes in most learners — the 20-minute claim fails.
- Any receipt whose instrument hash is not the frozen one.

## Limitations stated now

- n of eight to ten decides CONTINUE / NARROW / KILL for this lesson; it
  does not estimate an effect size and is not a study of the method.
- The two bare cases were authored by a fresh-context model from a fixed
  eight-template brief; their difficulty match is asserted by structure, not
  measured. The pre-task is `pre`; the cold case is `cold`; they are not
  swapped after outcomes.
- Keys are withheld from the page and the case file but the moves are
  public; a learner who reads the repository before answering contaminates
  their own receipt, and the invitation asks them not to.
- Receipts are self-reported and assumed in good faith.
- The seed and the slot table are public; assignment is deterministic by
  design, not concealed.

## Files

`freeze.json` hashes · `INVITATION.md` the text the owner sends ·
`NEXT_ACTION.md` the owner's single next action · `responses/` where
receipts go, one `slot-<n>.json` each · `qa/` the browser QA receipt and
screenshots · `keys.json` (absent until every response is in; digest frozen).
