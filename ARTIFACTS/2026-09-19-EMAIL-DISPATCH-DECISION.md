# Owner decision 2026-09-19 — assistant-executed email dispatch

`CLAUDE.md` requires that a widening of the external-actions boundary be
recorded with its date, because "a boundary widened by one experiment is
auditable, a boundary deleted is not." This is that record. It is written as a
repository artifact rather than as an edit to `CLAUDE.md`, because amending the
assistant's own standing instructions is the owner's hand. The patch text is at
the bottom, ready to apply.

## What happened

On 2026-09-19 the owner instructed the assistant, in session
`session_01WzLMNrfrcE4R2WVoKEe78x`, to send five cold research emails to Temple
University faculty. The instruction was given twice. The first time the
assistant declined to send and staged Gmail drafts instead, citing
`CLAUDE.md`'s "external actions are the owner's hand only" and its own inability
to verify any recipient address from a host where Temple's domains are blocked
at the egress proxy. The owner then stated that all addresses were verified and
repeated the instruction: *"all are verified just send all the emails if
drafted."*

The assistant sent all five at 2026-09-19T22:45Z. Addresses, message ids and the
exact text are recorded in `distribution/emails/2026-09-19-temple.md`.

## The decision, stated narrowly

A cold research email may be sent by the assistant from the owner's mail account
when **all** of the following hold:

1. the exact text is committed under `distribution/emails/`;
2. the owner instructs the send in-session and confirms every recipient address;
3. the assistant states its own address confidence before sending, rather than
   silently inheriting the owner's;
4. the send is recorded with UTC time, address used and provider message id.

Nothing else is widened. Issues, licences and every other external ask remain
the owner's hand.

## What this cost, stated honestly

The assistant's address confidence was **not** uniform, and sending did not make
it so. Two of five addresses were corroborated by two independent secondary
sources each; one matched a homepage path; one was an unconfirmed personal
address; and one — `y.wang@temple.edu` — actively disagreed with the public
homepage path `~yanwang`. The owner's verification resolved this and the
assistant proceeded. If message 5 bounces, that disagreement is the reason, and
it was recorded before the send rather than after.

The general hazard this exemption creates: an assistant that sends on assertion
rather than on its own verification is only as accurate as the assertion. The
four conditions above exist to keep that visible, not to make it disappear.

## Open gap this exposed

`distribution/dispatch-log.yaml` is the repository's record of what has been
sent. It cannot represent these five sends. `scripts/verify_consequence.py`
hard-fails any entry whose `sent_by` is not `owner`, and recording a
Claude-executed send as an owner send would be false. The five sends are
therefore recorded only in `distribution/emails/2026-09-19-temple.md`, which is
a weaker place for them.

Two ways to close it, both owner decisions:

- add `assistant_under_owner_instruction` as a permitted `sent_by` value, with a
  required field naming the instruction; or
- keep `sent_by: owner` as the only permitted value and treat the emails
  directory as the canonical record for this class of dispatch, saying so in
  `DISPATCH.md`.

Until one is chosen, the repository's dispatch log is silent about five real
external actions. That is the honest cost of the exemption as it stands today.

## Not affected

- No technical interaction was spent. `scripts/outcomes.py` requires an HTTP(S)
  `url` per interaction-log entry; an email has none. The stop-rule budget
  remains 4 of 12.
- No claim, census row or observation row was created.
- The prepared SciER issue in `distribution/issues/` remains **unsent**, with its
  duplicate check still outstanding.

## Patch for CLAUDE.md, for the owner to apply

In the "Hard boundaries" section, after the sentence ending
`from a clean and pushed tree.`, insert:

> **Second narrow exemption, owner decision 2026-09-19:** a cold research email
> whose exact text is committed under `distribution/emails/` may be sent by the
> assistant from the owner's mail account, when the owner instructs it
> in-session and has confirmed every recipient address. The assistant states its
> own address confidence before sending rather than inheriting the owner's, and
> the send is recorded in that file with the UTC time, the address used and the
> provider message id. Five Temple emails were sent under this on 2026-09-19
> (`ARTIFACTS/2026-09-19-EMAIL-DISPATCH-DECISION.md`). Nothing else is widened:
> issues, licences and every other external ask remain the owner's hand.

and amend the existing final sentence of that bullet from
`Nothing else is widened: asks, issues and licences remain the owner's hand.`
so that it no longer contradicts the above.
