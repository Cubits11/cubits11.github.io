# S001 — judgement points, primary reviewer (recorded before adjudication)

Every place applying protocol v1 to the sentinel required a decision the
protocol did not make for me. Written and committed before the independent
adjudicator's ambiguity log was seen.

The pre-registered stopping condition treats ambiguity in **eligibility, ladder
rung, reconstruction class, or which negative kind applies** as a protocol
defect requiring v1.1 before observation #2.

---

## J1 — With K=2, L4 and L5 are the same rung · **DEFECT**

`L4` licenses "pairwise intersection and pairwise union statements" and
explicitly `does_not_license` higher-order joints, on the ground that "pairwise
agreement does not identify the triple". `L5` is "sufficient higher-order or
full joint information".

With exactly two mechanisms there is no triple. The full joint distribution over
two binary verdicts **is** the 2x2 pairwise table, so L4 attained implies L5
attained, and L4's `does_not_license` clause is simply false for K=2.

The protocol never says how many mechanisms L4/L5 assume. I had to decide.

**Did it change this classification?** No — L4 is not attained here, so the
collapse never bites. It would bite immediately for any two-mechanism artifact
that *does* publish overlap, and such an artifact is exactly what the
adversarial selection rule is designed to find. This is a latent defect that
this sentinel surfaced without being blocked by.

**Repair for v1.1:** state that for K=2, L4 and L5 are the same rung, and record
L5 as `NOT_APPLICABLE_K_EQUALS_2` rather than as a negative finding.

## J2 — "Released harness computes the joint, then discards it" has no kind · **DEFECT**

L3 is not attained. But the reason is unusual and sharper than plain absence:
`main.py` scores every example with both detectors and builds per-example rows
carrying `predicted` and `actual`, and then `save_results()` writes **aggregate
counts only**, discarding exactly the per-item verdicts that would make the
joint exactly recoverable.

Which `negative_kinds` entry is that?

- `NOT_PUBLISHED` — "examined and does not report this". True, but it misses that
  the artifact *computed* it.
- `CANNOT_BE_RECONSTRUCTED` — "established that the published information is
  insufficient to recover the quantity". Also true of the published outputs, but
  a third party can recover the verdicts by re-running modified code, so calling
  it unreconstructible overstates the barrier.

Neither is wrong; neither is right. I recorded `NOT_PUBLISHED` and flagged it.

**Repair for v1.1:** add `COMPUTED_THEN_DISCARDED` — the artifact's own released
tooling derives the quantity and does not persist it. This is a distinct and
common failure mode, and it is the most actionable one for an author: the fix is
one `to_json` call, not new experiments.

## J3 — No preservation state for a commit-pinned repository · **DEFECT**

`preservation_states` offers ARCHIVED_VERIFIED, ARCHIVE_URL_RECORDED,
NO_ARCHIVE_RECORDED, ARCHIVE_UNDETERMINED — all framed around web archives.

This artifact is pinned to git commit `4c81a13`, which is a **stronger** content
binding than an archive URL: it is content-addressed and independently
verifiable. Recording it as `NO_ARCHIVE_RECORDED` is technically true and
materially misleading.

**Repair for v1.1:** add `SOURCE_COMMIT_PINNED`, ranked above ARCHIVE_URL_RECORDED.

## J4 — Unit of observation for an untagged repository · **UNDERSPECIFIED**

`universe.unit_of_observation` names "a paper, report, leaderboard snapshot, or
repository release". This repository has no paper, no release, and no tag — only
a default branch. `edge_cases.leaderboard_is_mutable` says a leaderboard is
observed as a dated snapshot; nothing says the same for a repository.

I pinned the commit and treated that as the artifact. The protocol did not tell
me to.

**Repair for v1.1:** extend the leaderboard snapshot rule to any mutable source,
and require a commit or content digest whenever one is obtainable.

## J5 — One unretrievable field: does the whole record become pending? · **DEFECT**

`n_items` requires the size of `deepset/prompt-injections` (HuggingFace). HTTP is
blocked here, so that single field is
`NOT_RETRIEVABLE_IN_THIS_ENVIRONMENT`.

The state machine says `VERIFICATION_PENDING` is for a record whose
"classification requires evidence not yet retrieved". Every classification-bearing
field here *was* retrieved; only a descriptive count was not. The protocol does
not say whether one pending descriptive field forces the whole record to
VERIFICATION_PENDING, or whether a record can be VERIFIED with named pending
fields.

I treated the record as classifiable with `n_items` pending, because no ladder
rung, negative kind, or reconstruction class depended on it.

**Repair for v1.1:** distinguish *classification-bearing* fields from
*descriptive* fields, and state that only a pending classification-bearing field
forces VERIFICATION_PENDING.

---

## Verdict against the pre-registered stopping condition

Four defects (J1, J2, J3, J5) and one underspecification (J4). Two of them —
J1 (a ladder rung) and J2 (which negative kind applies) — fall squarely inside
the categories the stopping condition names.

**STOP. Version to v1.1. Do not collect observation #2 until repaired.**

This is the contact test working. The protocol was coherent as a document and
ambiguous on first contact with a real artifact, which is precisely what one
observation was supposed to reveal and what twenty observations would have
baked in.
