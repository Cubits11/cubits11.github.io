# The owner's single next action

OWNER-ACTION · open since 2026-09-02 · zero receipts · the pilot cannot produce a row until this is done.

**Send Message 1 of `INVITATION.md` to ten people, today, and write the
date sent and the 14-day deadline on the first line of
`trials/necromancer/pilot/responses/enrolment.csv`.**

`/trials/necromancer/` went live on 2026-09-03 (merge c71125b, CI run
33710923297 green, deployed page carries the frozen instrument hash
`be77f883…`). Sending the message is the owner's hand; nothing here does it.

That message is the only thing between this repository and its first human
observation. Nothing else on this page moves the count.

Then, mechanically:

1. As each IN arrives, append `slot,timestamp,contact` to `enrolment.csv`
   in arrival order, and send Message 2 with that slot.
2. As each receipt arrives, save it verbatim as
   `trials/necromancer/pilot/responses/slot-<N>.json`.
3. On the deadline, run

```bash
python3 scripts/trial_score.py
```

It exits 2 and concludes nothing below eight receipts with four to five per
arm. When it exits 0 it prints CONTINUE, NARROW or KILL under the rule
frozen in `PILOT.md`; that word is the result, and the secondary outcomes it
prints beside it decide nothing. Then, and only then, copy
`_private/necromancer/keys.json` to `trials/necromancer/pilot/keys.json`
and commit it — the verifier checks it against the digest frozen on
2026-09-02.
