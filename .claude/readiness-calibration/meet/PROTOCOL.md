# Prospective test of the meet

Declared 2026-09-27, before any prospective case was scored. The definitions below are
fixed. A change to them after any outcome in this series is visible voids every case
already scored under them. Those cases are then reported as void, never re-read.

## Fixed definitions

- **Obligations** are A, I, T, Q, V and X as in `MEET.md`, and nothing else.
- **I, strict.** The change set is committed with explicit paths, *and* the acceptance
  runs on the committed tree: a fresh worktree of the commit, or CI on the pushed commit.
  Explicit paths alone do not establish I. For a dispatch that writes nothing, I is the
  dispatch identity alone: the executor compares the digest of the bytes it received
  with the admitted digest before acting.
- **Evidence** is a pointer the owner can open: a file and line, a commit, a Drive file id,
  or a command with its output. "The prompt says so" is evidence only for properties of the
  prompt.
- **Compiler-dischargeable** obligations are those a fixed clause establishes by
  construction. There are two, and no others:
  - I: `Commit with explicit paths. Run the acceptance in a fresh worktree of your commit and report its output.`
  - X: `Your harness is <named>. If a tool this task needs is absent there, stop and name it.`
  Anything else that fails is a HOLD, and it goes to the owner.

## Per dispatch

1. Before dispatch, write the case (the `readiness_meet.py` format) and freeze it: commit
   it, or record its sha256 in the 13.05 Freeze Ledger. Record the 13.04 decision beside
   it. Neither may change after the run starts.
2. Record the sha256 of the exact dispatched bytes. The executor compares it before acting
   (the I obligation above).
3. For a REVIEW, record which observation was taken, what it returned, and the decision
   that followed.
4. After the run, grade the outcome with 13.04's labels (TRUE/FALSE READY, TRUE/FALSE HOLD,
   UNKNOWN). Grade from the acceptance run in a clean worktree of the run's commit, never
   from the executor's report.

## What is compared, and when

Nothing is stated until **10** dispatches are graded. Then, for each instrument, the
counts of each label are compared. For the meet, two further counts are reported:

- **resolved**: REVIEWs whose named observation decided the case (READY or HOLD after it);
- **operative**: resolved REVIEWs whose post-observation decision matched the graded
  outcome.

With N = 10, no difference between the instruments is reported as an effect. The counts
are reported as they are, with the cases listed.

## Kill conditions

- **K-M1.** The meet says READY where 13.04 says HOLD, and the case grades FALSE READY. One
  such case ends the meet's use for admission.
- **K-M2.** Of the first 10 REVIEWs, fewer than 5 are resolved. The named variables are then
  not the ones that decide cases: REVIEW becomes HOLD, and the variable naming is retired.
- **K-M3.** With the compiled I-clause present, an identity failure (a missing dependency,
  swept-in work, acceptance run on a tree other than the commit) occurs in 2 or more of the
  first 10 runs. The strict definition of I is then wrong, not merely unenforced.
- **K-M4.** The owner records twice that the meet delayed a task that needed no gate. This is
  13.04's own self-audit condition, "the engine delays trivial work".

## Not claimed

- That 10 dispatches can separate the instruments. They can surface a disqualifying case
  (K-M1 to K-M4), and they cannot show superiority.
- That a graded outcome measures prompt readiness alone. Executor, harness and task
  difficulty are uncontrolled. The executor's identity is recorded, not randomized.
