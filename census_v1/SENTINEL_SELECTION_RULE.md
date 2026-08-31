# v1 sentinel — selection rule (pre-registered)

Written and committed **before** any discovery was run for this observation, and
before any candidate's disclosure outcome was inspected. The commit containing
this file is the pre-registration; anything selected afterwards is bound by it.

Purpose: one artifact, chosen adversarially, run end-to-end through
`census_protocol_v1.yaml`. The question under test is **not** whether the result
supports the Missing Column. It is:

> Can a competent stranger apply the frozen protocol to a new artifact without
> asking what we meant?

---

## 0. Environment constraint, declared up front

Outbound HTTP is blocked in this build environment. `WebSearch` returns a search
index; `git` reaches GitHub. Therefore:

- **Discovery** may use the search index. A search result is a pointer, never
  evidence, and never a classification input.
- **Primary-source retrieval** is possible only for artifacts whose evidence is
  reachable over `git` (a repository), or whose full text is already committed
  in this repository.
- An artifact selected under this rule whose primary evidence cannot be
  retrieved here resolves to `VERIFICATION_PENDING` with
  `blocking_reason: NOT_RETRIEVABLE_IN_THIS_ENVIRONMENT`. It is **not**
  classified, and its absence of a finding is **not** a finding.

This constraint biases the reachable pool toward repository-hosted artifacts.
That is a coverage limitation of this run and is recorded as one. It is not a
claim about the population.

## 1. Adversarial intent

The sentinel is chosen to have a **reasonable chance of defeating the narrative**.
Concretely, among eligible candidates, preference goes to the artifact most
likely to expose unusually rich joint information — an ensemble/stacked result,
or a per-item release from which joint quantities are exactly computable.

If the sentinel turns out to sit at L6 or `EXACTLY_RECONSTRUCTIBLE`, that is a
**successful** run of this rule, not a failure of it.

## 2. Discovery procedure (fixed before execution)

- **Window:** searches executed 2026-08-31 (America/New_York).
- **Queries** (exact strings, run in this order):
  1. `guardrail ensemble benchmark union detection rate multiple safety filters`
  2. `LLM guard model comparison released per-item predictions github`
  3. `prompt injection detection benchmark ensemble combined detector results`
  4. `content moderation API benchmark released raw per-sample outputs`
- **Snowball:** none. One pass only.
- **Every candidate surfaced is recorded**, including those rejected, with the
  reason. The denominator is auditable or the exercise is worthless.

## 3. Eligibility

Applied exactly as written in `census_protocol_v1.yaml` (`universe.inclusion`,
`universe.exclusions`, `universe.edge_cases`). No criterion is added, relaxed, or
reinterpreted for this run.

Additionally, the candidate must **not already be a v0 examined row**. A v0
`unexamined_candidate` is allowed, and its provenance is recorded as such rather
than presented as fresh discovery.

## 4. Ranking, mechanical

Among candidates passing eligibility and retrievable per §0, rank by:

1. **Adversarial value** — descending:
   `3` public signal of an ensemble/stacked/union result **and** a per-item release
   `2` public signal of one of those
   `1` neither signalled
2. **Retrievability** — repository-hosted primary evidence ranks above all else.
3. **Recency** — later publication date first.
4. **Tie-break** — lexicographically smallest candidate identifier.

Take rank 1. Exactly one artifact. No substitution after inspection: if the
selected artifact turns out to be inconvenient, it is still the sentinel.

## 5. Stopping condition

If applying the protocol requires any judgement the protocol does not determine
— eligibility, ladder rung, reconstruction class, or which kind of negative
applies — that ambiguity is a **protocol defect**. Record it, version the
protocol to v1.1, and **do not collect observation #2** until it is repaired.

Every point at which a human judgement was necessary is logged, whether or not
the protocol resolved it.
