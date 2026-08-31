# S001 — independent adjudication and comparison

A second reviewer was given **only** `census_protocol_v1.yaml` and the artifact
checkout, with the sealed primary classification, `census.yaml`, the census
pages and the scripts directory explicitly off limits. It had not seen the
protocol before.

**What this tests, and what it does not.** It tests whether the protocol is
*self-sufficient* — whether someone can apply it without asking what we meant.
That is the question the contact test poses. It is **not** inter-rater
reliability between independent humans: the adjudicator is the same model as the
primary reviewer and shares its priors. A human reviewer remains the real
version of this step, and this result does not substitute for one.

Primary classification sealed at `31415f0`; primary ambiguity log sealed at
`58e96f8`; both committed before the adjudicator ran.

---

## 1. Classification agreement — 9 of 9

| field | primary | adjudicator | agree |
|---|---|---|---|
| eligibility (6 inclusion criteria) | all met, no exclusion | all met, no exclusion | ✅ |
| L1 marginals | attained | attained | ✅ |
| L2 shared item universe | attained | attained | ✅ |
| L3 item-level verdicts | not attained · NOT_PUBLISHED | not attained · NOT_PUBLISHED | ✅ |
| L4 pairwise | not attained · NOT_PUBLISHED | not attained · NOT_PUBLISHED | ✅ |
| L5 higher-order | not attained · NOT_PUBLISHED | not attained · NOT_PUBLISHED | ✅ |
| L6 stack/union | not attained · NOT_PUBLISHED | not attained · NOT_PUBLISHED | ✅ |
| reconstruction class | PARTIALLY_IDENTIFIED | PARTIALLY_IDENTIFIED | ✅ |
| preservation | NO_ARCHIVE_RECORDED | NO_ARCHIVE_RECORDED | ✅ |

No disagreement on eligibility, on any rung, on the reconstruction class, or on
absence-versus-unverified — the four categories the stopping condition names.

**One state-assignment difference.** The primary recorded
`eligibility.state: ELIGIBLE` and stopped; the adjudicator carried the record
through to `VERIFIED`, and flagged a competing literal reading of
`VERIFICATION_PENDING`. The primary conflated an eligibility verdict with a
record state. That is a reviewer error revealed by the adjudication, and it is
also a protocol gap (defect D1 below).

## 2. The result that matters: agreement was not mechanical

The adjudicator reached the same nine answers **by making twelve undetermined
judgement calls**. The primary made five. Reaching the same place by
independently guessing at the same dozen forks is not reproducibility; it is two
readers with the same priors.

Answer to the question the contact test asked — *can a competent stranger apply
the frozen protocol without asking what we meant?* — **No.**

## 3. Independently confirmed defects (found by both, separately)

| primary | adjudicator | defect |
|---|---|---|
| J1 | #6 | L5 is undefined for two mechanisms; L4 and L5 are the same object |
| J2 | #5 | `NOT_PUBLISHED` and `CANNOT_BE_RECONSTRUCTED` are both true, with no precedence |
| J3 | #8 | no preservation state fits a commit-pinned source |
| J4 | #2 | "artifact" undefined for a mutable, untagged repository |
| J5 | #1 | an unretrievable field's effect on record state is unspecified |

Two of these the adjudicator found **worse** than the primary did:

- **#2** — if commits are artifacts, `duplicate_publication` (earliest wins) and
  `superseded_version` (latest wins) fire in *direct contradiction* on identical
  facts, with no tiebreak.
- **#1** — `INELIGIBLE` is defined as matching "a named exclusion", and
  `inaccessible_evidence` **is** a named entry in `universe.exclusions`, while
  that entry's own text says it is "NOT an exclusion". The protocol contradicts
  itself.

## 4. Defects the primary reviewer missed

These are the return on adjudication.

- **#3 — `method_detail` is circular.** It requires "enough detail to place the
  artifact on the ladder and assign a reconstruction class". But every artifact
  admits a placement (all rungs `NOT_PUBLISHED`) and every artifact admits
  `UNVERIFIED`. The criterion excludes nothing, and can only be evaluated after
  the classification it is supposed to gate.
- **#4 — key/text mismatch.** `incomparable_thresholds` is keyed on thresholds
  but its text is about event definitions and label sets. A reviewer scanning
  keys and one reading text screen different artifacts.
- **#7 — the artifact contradicts itself, and it is load-bearing.** README
  reports LLM Guard recall 46.31% (TP 94); the committed PR-curve PNG at the
  same threshold shows recall ≈ 40.2% (TP 82) — stale output from a superseded
  commit. The protocol says nothing about which figure is *the* marginal, and
  the choice moves the identification bounds. See the correction below.
- **#9 — "distinct" mechanisms has no test.** Both compared systems are
  DeBERTa-based. If they wrapped the same checkpoint, "two mechanisms" is one
  mechanism behind two wrappers. Checking requires network access.
- **#10 — fail-open folded into the marginal.** `main.py:73-76, 88-91` catch
  every exception and record `is_injection = False`. Each published marginal is
  really the marginal of "detector OR (crash → allow)", and the crash rate is
  never reported.
- **#11 — no denominator is published.** The artifact states neither N nor class
  balance. The adjudicator recovered N=546 / P=203 from a baseline annotation
  inside the PNGs plus integrality against four-significant-figure ratios.
  Without that recovery, `PARTIALLY_IDENTIFIED` would be assignable but empty —
  a class with no computable bounds.
- **#12 — the class table is not total.** The ladder declares rungs
  independent, but `EXACTLY_RECONSTRUCTIBLE` requires [L2,L3] and
  `PARTIALLY_IDENTIFIED` requires [L1,L2]; combinations the independence clause
  permits have no class, and `UNVERIFIED` would wrongly absorb them.

## 5. Verdict against the pre-registered stopping condition

Twelve undetermined judgement points, two internal contradictions, one circular
criterion. **STOP. Version the protocol to v1.1. Do not collect observation #2
until the ambiguity is repaired.**

The instrument produced the same answer twice and could not say why
mechanically. That is exactly the failure one observation was meant to expose
and twenty would have baked in.
