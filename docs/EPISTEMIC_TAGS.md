# Epistemic tags: a boundary, not a schema extension

Working note, 2026-08-28. This is internal method documentation, not a
proposed standard or a second public registry.

A private working vocabulary has used `[O]` observed, `[M]` memory, `[I]`
interpretation, `[S]` reflective practice, `[H]` hypothesis, `[E]`
empirically supported, `[C]` contested, `[U]` unknown, and `[F]` falsified.
The useful question is not whether that vocabulary is elegant. It is whether
the public claim registry can represent those meanings without pretending to.
It cannot, and that is a safeguard rather than a missing enum.

## No one-to-one mapping

`claims.yaml` records a proposition, scope, evidence location, provenance,
support role, evidential status, review dates, triggers, a falsifier,
forbidden rescues, and non-claims. Those are useful controls. They are not an
epistemic-tag ontology.

| Working tag | Why the registry does not encode it directly | Safe handling |
|---|---|---|
| `[O]` observed | An executed program can be a deterministic calculation, not an observation of a world. | State the data lineage and assertion kind in the claim scope. |
| `[E]` empirically supported | `supported_within_scope` can also describe a document or artifact claim. | Preserve the evidence type; do not read the status as “empirical.” |
| `[H]` hypothesis | `untested` also appears on owner-attested facts. | Write the hypothesis and its decision rule explicitly. |
| `[F]` falsified | A declared falsifier or fired review trigger means review is due; it does not adjudicate falsity. | Record the review and its consequence in a correction/revision record. |
| `[M]` memory | `owner_attested` is a provenance statement, not a memory category. | Keep it outside technical evidence claims. |
| `[I]` interpretation | A support URL tells us where text lives, not how an inference was made. | Name the inference and competing readings. |
| `[C]` contested | `inconclusive` conflates conflict with several other reasons for non-resolution. | Describe the disagreement, evidence, and adjudication path. |
| `[U]` unknown | Some unknowns are non-identification; others are missing data or open hypotheses. | Name the object and the measurement that would distinguish it. |
| `[S]` reflective practice | A reflection is not necessarily truth-apt and should not be promoted by accumulating “evidence.” | Keep it in a separate private practice record, never in the public claim registry. |

The missing structured axis is **assertion kind**, not a new status label. A
future, separately reviewed schema could distinguish source record,
deterministic recomputation, mathematical result, statistical inference,
hypothesis, and artifact description. Until then, compound claims must scope
those roles in prose instead of using a decorative tag.

## `[S]` stays out of `claims.yaml`

Adding `[S]` would create exactly the category error the tag is meant to
avoid. Every public claim must carry a proposition, scope, support, a review
window, a falsifier, a fixed consequence, forbidden rescues, and non-claims.
That is right for a claim. It is wrong for a reflective practice such as “keep
this distinction visible while planning work.”

There is therefore no `[S]` enum, claim record, generated public page, or
evidence-ledger entry. If a reflective record is ever useful, it must live
outside the public repository and include `kind: reflective_practice`, a
practice status (`adopted`, `revised`, or `retired`), revision conditions,
related claims, and `non_empirical: true`. It must not carry a claim status,
an expected result, or an evidence chain. Turning it into a public claim must
create a new claim ID, a new scope, and new appropriate support; it can never
be an in-place promotion.

## `[U]` has a precise instance, not a universal meaning

For a fixed, full-exposure, parallel block-on-any stack with per-guard miss
rates `p_1, …, p_k`, static all-miss is identified only to

    [L, U] = [max(0, Σp_i − (k−1)), min_i p_i].

The unidentified width is

    U − L = min_i p_i − max(0, Σp_i − (k−1)).

It equals `min_i p_i` only when `L = 0`; for `p = (0.9, 0.9)`, the width is
`0.1`, not `0.9`. A same-denominator static union aggregate closes this
particular unknown because `all_miss = 1 − union_detection`. Per-item outcomes
then add overlap and leave-one-out analysis. Neither form of disclosure turns
a static result into an operational or adaptive-risk estimate.

This is the useful meaning of `[U]` here: not “we do not know,” but “this
specified object has this identified set under these conditions, and this
specified measurement would shrink it.” Other unknowns need their own
objects, units, and remedies.

## Standing rule

Working tags may guide private notes. They do not appear in `claims.yaml`,
the generated ledger, observatory, modules, public evidence pages, or social
copy. The public record must stand on its own stated proposition, scope,
lineage, and falsifier. A tag never substitutes for any of them.
