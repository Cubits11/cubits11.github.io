# External events — how a qualified outcome enters the record

A qualified outcome is work done by someone who is not the author:
an independent reproduction, a source or benchmark correction, a paired or
joint outcome release, an accepted upstream contribution, a human cold run of
the protocol. Everything else — impressions, views, likes, follows, clicks,
bookmarks, issues opened, compliments, invitations, technical conversation
without an external result — is a diagnostic. The two are never combined
into one score. `scripts/outcomes.py` validates both ledgers; `/try/` renders
the qualified counts from `distribution/outcomes.yaml`, and zero is rendered
as zero.

## The procedure, every time

1. **Observe.** An issue, PR, release, or message arrives. Record nothing yet.
2. **Verify.** Open the artifact. Re-run what was run, or read what was
   released, against the pinned sources. A claimed reproduction that cannot
   be re-run is a diagnostic, not an outcome.
3. **Update the ledger.** Append one entry to the matching bucket in
   `distribution/outcomes.yaml` with `date` (of verification), `kind`,
   `actor` (public name or `anonymous`, per the reporter's credit choice),
   `artifact` (the URL a reader can open), `agreed` (true or false),
   `consequence`, and `claim`. `scripts/outcomes.py` rejects a malformed entry.
4. **Decide whether a claim changes.** A disagreement runs the claim's own
   falsifier: NARROW, REJECT, or HOLD as registered in `claims.yaml`, never a
   new consequence chosen after the fact. Forbidden rescues stay forbidden.
5. **Update the public surface.** Run the relevant generators (for an outcome-ledger update,
   `python3 scripts/generate_try.py` and
   `python3 scripts/generate_missing_column.py`, and
   `python3 scripts/generate_research_index.py`, followed by
   `python3 scripts/generate_sitemap.py`), then run
   `python3 scripts/verification_manifest.py`. The manifest checks; it does
   not regenerate stale pages. A correction is placed beside the claim it
   corrects — in `/corrections/`, the census revision history, or the claim's
   correction history — with at least the prominence of the original.
6. **Credit.** Name the contributor as they chose. A falsification is credited
   at least as prominently as a confirmation.
7. **Communicate.** Say what changed, in the same channel the claim was made
   in, with the artifact linked. The event generates the publication; the
   publication is never manufactured to feed the event.

## The two-result rule

- First independent result: investigate. One confirmation does not canonize;
  one disagreement is not noise because it is inconvenient.
- Second genuinely independent result (different person, different
  environment): update confidence, in the direction the results point.

## What counts where

| Event | Bucket | Not this |
|---|---|---|
| A stranger runs TRY-A/B or a reproduction script and files the result, match or mismatch, and it re-runs | `independent_reproductions` | an issue that only says "works for me" with no output |
| A benchmark author or reader corrects a census row or a claim's source reading | `source_corrections` | a reply that disagrees without a checkable source |
| An evaluation publishes joint, paired, union, all-miss, or per-item outcomes it did not publish before | `paired_outcome_releases` | a promise to release |
| A patch of ours is merged in someone else's repository | `upstream_prs` | an open PR |
| A human applies `census_protocol_v1.yaml` or TRY-C to an artifact without asking us what the questions mean, and files the result | `human_cold_runs` | a comprehension-trial answer (diagnostic) |

## Stop and kill rules (unchanged)

The stop rule in `distribution/outcomes.yaml` stands: at 12 technical
interactions with 0 qualified outcomes, stop optimising replies and content,
diagnose the funnel mechanically (`campaigns.yaml → funnel.interpretation`),
and move effort to upstream contributions and direct one-integer asks. The
kill rule stands: if widened evidence shows the reporting gap is common, the
decision problem is usually identified from marginals, and qualified outcomes
remain absent, downgrade the programme to a portfolio artifact and say so
with the prominence of the original claim.
