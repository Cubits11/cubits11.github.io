# Epistemic tags, and what this repository already enforces

Working note, 2026-08-28. Internal discipline, not a proposed standard —
see the non-goals in [FRONTIER_ROADMAP.md](FRONTIER_ROADMAP.md).

A nine-tag vocabulary has been in private use for bounding the validity domain
of a statement: `[O]` observed, `[M]` memory, `[I]` interpretation, `[S]`
reflective, `[H]` hypothesis, `[E]` empirically supported, `[C]` contested,
`[U]` unknown, `[F]` falsified. The question worth answering is not whether the
vocabulary is good. It is **which tags this repository can already prosecute,
and which it cannot** — because a tag that nothing checks is a mood, and the
repository's whole thesis is that its claims are mechanically prosecutable.

## The mapping

| Tag | Nearest registry state | Enforced by |
|---|---|---|
| `[O]` observed | `provenance: machine_generated_owner_executed` + `support_role: executed_output` | the bound artifact's content hash, re-asserted in CI |
| `[E]` empirically supported | `evidential_status: supported_within_scope` | `expected` block cross-checked against a recomputation |
| `[H]` hypothesis | `evidential_status: untested` | freshness window; a hypothesis that never resolves expires |
| `[F]` falsified | `falsifier.consequence: REJECT`, fired | executable review triggers |
| `[M]` memory | `provenance: owner_attested` | nothing executable — attestation is the weakest support role |
| `[I]` interpretation | `support_role: site_document` | ledger coverage only |
| `[C]` contested | — collapsed into `inconclusive` | nothing |
| `[U]` unknown | — collapsed into `inconclusive` | nothing |
| `[S]` reflective | — **inexpressible** | nothing |

Three findings fall out of building the table.

## 1. `[S]` has no home, and that is a real gap

The registry cannot say *"this is a practice I keep because it is useful, and
it makes no empirical claim."* Every claim must declare an `evidential_status`
drawn from a scale that runs from `untested` to `contradicted` — a scale that
presupposes the thing is the kind of statement evidence bears on. A reflective
practice forced onto that scale gets recorded as `untested`, which reads as
"not yet supported," which is a promise the practice never made.

The consequence is worse than untidiness: it creates pressure to promote. A
practice logged as `untested` looks like an unfinished claim, and unfinished
claims invite completion. **The silent promotion of `[S]` to `[E]` is the
failure mode the tag vocabulary exists to prevent, and the registry's schema
currently supplies the incentive for it.**

Not fixed here. Adding an enum value touches every claim and deserves its own
reviewed change. Recorded so it is not rediscovered.

## 2. `[C]` and `[U]` are different states, and the difference is now computable

`inconclusive` currently absorbs both *"the evidence conflicts"* (`[C]`) and
*"the parameter is not identified"* (`[U]`). These are not the same problem and
do not have the same remedy. Conflicting evidence is resolved by more or better
evidence. **Non-identification is not resolved by more evidence of the same
kind at all** — it is resolved only by measuring a different thing.

This distinction stopped being philosophical when `scripts/identification.py`
landed. `[U]` now has units: for a stacked guardrail claim, the unknown is an
interval, its width is `min_i p_i` in probability, and the one scalar that
collapses it is nameable. A tag that meant "we don't know" now means "the
identified set has width W, and here is what closes it."

That is the only defensible reason to keep the vocabulary at all: a tag earns
its place when it forces a question that changes what you do next. `[U]` now
does. Before the identification work, it did not — it was a shrug with a
bracket around it.

## 3. The axiom the repository already implements

> A reflectively tagged assertion can never be silently upgraded without
> deterministic, reproducible evidence.

This is `forbidden_rescues`, which every claim must declare and which CI
requires to be explicit (`[]` is allowed; absent is not). It is also the rule
that killed a drafted clause in MC-001 rather than reinterpreting "commercial"
after a counterexample appeared, and the rule that will not let MC-003 quote
where an observed value sits inside its identified interval as though that were
a score.

The mechanism was already here under a different name. The vocabulary did not
add it; the vocabulary named it, which is worth something and is not worth
publishing.

## Standing rule

Tags are used in working notes and journal entries. They do not enter
`claims.yaml`, the generated pages, or anything public, because the registry
already carries a prosecutable version of the same distinctions and a second
vocabulary would drift from the first. **Where the two disagree, the registry
wins** — it is the one that fails a build.

One correction on record: a draft journal entry (Lesson Nº 2) carried invented
measurements under an `[O]` tag. It was rewritten against the BELLS release,
where the real numbers turned out to be stronger than the invented ones. That
is the whole argument for the discipline, and it is the reason the discipline
stays private until it has survived longer than one correction.
