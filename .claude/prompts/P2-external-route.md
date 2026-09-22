# P2 · The zero

Run first:

```bash
python3 .claude/skills/evidence-ledger/ledger.py
python3 scripts/horizon.py
```

`qualified_outcomes` is 0 across five buckets. A qualified outcome requires
someone who is not the author to do work. This is the single number that makes
all three trajectories in `research/HORIZON.yaml` unfalsifiable, and it is the
number the active trajectory is defined to move.

## The honest framing

Zero is not evidence the work is wrong. It is evidence the work has not been
touched. Those are different failures. Do not let this prompt become a
persuasion exercise: the goal is to make touching the work cheap, not to make
the work sound better.

## Do this — under the active trajectory

Read `selection.active` in `HORIZON.yaml`. The route depends on it.

**If T2 (THE STANDARD).** The unit is a change inside a repository this one does
not own.
1. Pick one target from `census.yaml`. One. A broadcast is not an engagement and
   the stop rule counts interactions, not recipients.
2. Write the change as a diff against their code, not as a request in prose. The
   ask is "here is the patch", never "have you considered".
3. Answer the objection you would raise if you were the maintainer — cost of
   emitting the field, schema churn, what breaks — inside the patch, before
   sending.
4. Stage it for the owner's hand. Record the dispatch in
   `distribution/outcomes.yaml` as a technical interaction, never as a qualified
   outcome; an invitation is diagnostic only.

**If T1 (THE INSTRUMENT).** The unit is rows from an instrument this repository
ran, and the external route is a cold run: someone reproducing from source. Make
the reproduction command work on a machine that is not this one, then invite
exactly one person to run it. A cold run that needs a clarifying question is a
documentation defect — record it as one.

**If T3 (THE DISCIPLINE).** The unit is classified mutation detection, and the
external route is defects this repository did not author. Find a corpus of real
analysis errors someone else recorded. Sourcing them is the work; constructing
them here is the thing the trajectory is forbidden to do.

## Record it honestly

An outcome is qualified when it is verified, not when it is seen. A
disagreement is recorded with at least the prominence of the claim it disagrees
with. A refusal is a result and goes in the log verbatim.

## Test

An artifact exists that a named external person could act on today, and the only
thing standing between it and them is the owner's hand.
