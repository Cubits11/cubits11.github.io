# Frontier roadmap — from a reporting-gap argument to a joint-behavior result

Status: working plan, 2026-08-28. Scope: what this repository does next, and
what it refuses to do next. Every dated deliverable below is a single
artifact with a stated exit criterion, because a roadmap whose steps cannot
fail is a mood board.

## 0. Where the work actually stands

The Missing Column census is a well-instrumented argument about a **reporting
gap**. It is not yet an empirical contribution about **deployed guardrail
stacks**. The distinction is the whole roadmap.

What the census earns, stated at its true strength:

> Within a bounded, single-reviewer inventory of 19 public evaluations, the
> record documents which joint-evidence artifacts were publicly recoverable.

What it does **not** earn, and must never be written as though it does: field
prevalence, general positive dependence between guards, stack unsafety, or
operational risk. The 3.1× BELLS figure is reproducible arithmetic on a
selected 170-prompt subset. It is a demonstration of what becomes computable,
not an inferential finding about guardrails.

Three structural corrections landed before any merge:

- **M is a ladder, not a verdict.** The shared-basis rung says only that a
  row documents shared items and a common event definition. It does not mean
  matched operating thresholds. The census now computes and prints all three
  rungs (13 / 12 / 0) mechanically from fields already on every row. The
  strongest rung is **0**, and 0 is the honest headline.
- **K is a discovery count, not a stack result.** Its four records contain
  noninterchangeable evidence types: two printed full-stack composition
  results, one partial/routing result, and one released per-item file. K is
  not an all-miss rate, a deployment conclusion, or a field prevalence rate.
- **A branch push is not a release.** CI now runs on pull requests, and a
  post-deploy job waits for a coherent deployment, checks the served census
  byte-for-byte, and checks that the rendered page binds itself to that census.

## 1. The estimand ladder

Composition is a tensor, not a column. Three distinct quantities are routinely
conflated; naming them is the first contribution.

| Symbol | Estimand | Question it answers | Evidence required |
|---|---|---|---|
| `O(s)` | Static all-miss | Which eligible guards miss the same pre-intervention artifact? | Full-shadow per-item outcomes, or privacy-preserving sufficient aggregates |
| `R_π(s)` | Operational route risk | What unsafe terminal action survives *this* stack in *this* order? | Replayable execution routes, predeclared ablations |
| `R_π,a,t(s)` | Adaptive robustness | What survives an attacker optimizing against the stack over time? | Sealed holdout, declared attacker budget and access, versioned reruns |

`O` is indispensable and non-terminal. In a sequential system an early block
prevents later components from ever seeing the item; in an agent, the
intervention changes the future trace. Mutable safeguards make version and
time part of the estimand, not nuisance parameters.

**Repository commitment:** no future empirical page, claim, or post may state
a result without naming which of `O`, `R_π`, `R_π,a,t` it is about. This is a
release rule for the prospective E2 packet, not a retroactive claim that the
current reporting inventory already measures all three.

## 1b. What is already identified — and what never can be

Before collecting anything, it is worth knowing what the *existing* form of
reporting can and cannot support. The answer is sharper than "not much," and
it is derivable rather than solicited: it needs nobody's cooperation and no
new census rows.

For k guards scored on a common item set at a common operating point under
block-on-any composition, with published per-guard miss rates `p_1..p_k`, the
all-miss rate is fixed only to

    max(0, Σ p_i − (k−1))  ≤  P(∩ E_i)  ≤  min_i p_i

and every point of that interval is attained by some joint law with those
marginals. The mathematics is classical — Bonferroni below, monotonicity
above, Fréchet for sharpness. Nothing here is new. What is new is reading it
as a **price**.

Three consequences, each stated in the direction that survived adversarial
review (`scripts/identification.py`, claim MC-003):

1. **Direction.** `P(∩E_i) ≤ min_i p_i` is a theorem: a block-on-any stack is
   never *worse* at catching than its best single member. What marginals can
   never do is certify that it is *better* — `min_i p_i` always lies inside
   the identified set. Strict improvement is unfalsifiable from marginals;
   degradation is ruled out by algebra.
2. **Asymmetry.** The identified floor under the stack's benign burden is
   `max_i f_i`, strictly positive whenever any member misfires. The identified
   floor under its improvement is exactly `0`. Marginal reporting can prove a
   stack costs its legitimate users, and can never prove it protects anyone.
   When `Σ p_i > k−1` the harmful-side lower endpoint also lifts, so marginals
   can certify an irreducible failure floor too. Every certifiable statement
   marginals support is a statement about *failure*.
3. **Independence is interior.** The product plug-in a dashboard prints always
   lies inside the identified set, so the bounds alone cannot refute it. Only
   per-item data can. This is why the disclosure ask cannot be replaced by
   better inference.

### The price, and what actually closes it

One scalar closes the harmful side: for a parallel stack on a fixed labelled
population at a fixed operating point, `all-miss = 1 − B`, where `B` is the
"flagged by at least one guard" rate. That is an identity, not a theorem, and
it releases no items.

But the union is not the disclosure that matters most. **The k leave-one-out
unions are** — publish the union with guard `g` removed, for each `g`, and
each member's unique contribution becomes visible. This costs k scalars, still
releases no items, and reveals the one thing marginals *and* the union
together still hide: whether a stack is an ensemble or one guard carrying
riders.

On the one per-item release the census found (BELLS 2025, 82 prompts labelled
harmful), the identified set from the five published marginals is the 13
values {0/82 … 12/82} — 13/82 is combinatorially infeasible, since 70 catches
cannot fit in 69 items. The observed all-miss is 9/82. The five marginals
(52, 5, 25, 70, 0) together with the union (73) are exactly what such a stack
would report and are entirely consistent with a working five-member ensemble.
The leave-one-out row says otherwise:

| Removed | Union without it | Unique contribution |
|---|---:|---:|
| NeMo Guardrails | 55 / 82 | 18 |
| Lakera Guard | 70 / 82 | 3 |
| LangKit | 73 / 82 | 0 |
| Prompt Guard | 73 / 82 | 0 |
| LLM Guard | 73 / 82 | 0 |

Three of five contribute nothing on this stratum. Nobody asks for that row.

**Scope, held tightly.** One stratum of one author-selected subset; the 50
benign and 38 borderline rows are separate strata and are never folded in.
This is an existence proof that the blind spot is not hypothetical — not
evidence that guards in general fail together, which this stratum cannot
separate from prompt-difficulty heterogeneity. Where an observed value sits
inside the interval is **not** a score: the endpoints come from adversarial
couplings with no detector-behavioural content, and reporting "75% of the way
across" is reading a bound as a benchmark. The claim's forbidden rescues bar
exactly that.

### What this changes about the programme

The disclosure ask stops being a request for cooperation and becomes a
statement about what published reporting can support. MJGD v1 gains a required
field — **leave-one-out unions** — and gains a derivation rather than a
preference for the fields it already had. And §7's Arm S is no longer
justified by "more data is better": it is the arm that moves the estimand from
an interval of width `min_i p_i` to a point.

## 2. The competing explanations

The wager is a three-way test, not a thesis to confirm.

1. **Shared blind spots.** Similar guards fail together; layering barely
   reduces the dangerous residual.
2. **Conditional complementarity.** Heterogeneous guards catch meaningful
   portions of each other's misses at acceptable benign-user cost.
3. **Sequential / adaptive collapse.** Static overlap looks good; real
   routing, changed trajectories, or adaptive attackers erase the gain.

A null result is a good result and must be pre-committed as publishable. The
protocol is frozen before outcomes are inspected precisely so that a null
cannot be quietly reframed as "inconclusive, needs more data."

## 3. Ninety days, one deliverable per window

| Window | Deliverable | Exit criterion |
|---|---|---|
| Days 1–14 | Corrective census release | M ladder printed; dual-review of all 19 rows recorded; retrieval and screening ledger published; PR CI and post-deploy gate green on the live site |
| Days 15–30 | MJGD v1 schema + validator | Fixtures pass for parallel, sequential, partial-release, aggregate-only, and missing-data cases; one maintainer outside this repository tests or rejects it **on record** |
| Days 31–45 | Frozen E2 protocol | One population, one event, three named systems, versions, thresholds, routes, data rights, stopping rules, and a sealed holdout — all tagged **before** any outcome is inspected |
| Days 46–70 | Prospective collection | Predeclared high-risk-stratum precision target met, or a declared STOP/HOLD with its reason; no silent missing cells; outcome, label, and configuration provenance retained |
| Days 71–90 | Joint Evidence Packet | Deterministic replay; direct joint results shown against marginal-only bounds; uncertainty, benign burden, and route effects reported; one independent clean-environment reproduction |

### Minimum Joint Guardrail Disclosure (MJGD) v1 — required fields

Fixed population · event definition · route semantics (parallel / sequential
with order / gated) · system and API versions · operating thresholds ·
missingness codes · per-system rates **at the same operating point** ·
full-stack union and all-miss · **k leave-one-out unions** · benign-union
burden · ordered residual coverage · uncertainty · latency, cost, errors, timeouts · policy topology ·
stratification by threat regime · a repeat-after-version-change rule · raw
outcome tensors where safely releasable, otherwise sufficient aggregates plus
independently verifiable manifests.

**Raw harmful prompts are not always required.** For a declared decision, a
full-stack "block on any" rate identifies all-miss; ordered prefix rates
identify residual contribution; the k leave-one-out unions identify each
member's unique contribution. Per-item vectors can stay controlled-access.
This is what makes the disclosure ask answerable rather than merely
principled — though it presupposes the evaluator retained a per-item join
across guards at a common operating point, which many leaderboards never
construct. Where they did not, the honest answer is that the disclosure is
not available at any price until the evaluation is re-run.

## 4. Standing behaviors (enforced, not aspirational)

These are repository rules. Where a rule says *CI*, it is or becomes a check
in `.github/workflows/verify.yml`.

1. **Every count is computed, never typed.** N, M, K, and the M ladder come
   only from `verify_census.compute_counts`. *CI: generated-page drift check.*
2. **Every published stratum prints its whole ladder.** A number that has a
   stricter defensible reading must show that reading beside it. *CI: the
   `m_strata` cross-check in `verify_census.py`.*
3. **Every future empirical claim names its estimand.** `O`, `R_π`, or
   `R_π,a,t`. The current census is a reporting inventory, not an empirical
   stack result; this requirement becomes executable with the frozen E2
   protocol rather than being retroactively pretended today.
4. **Corrections weaken, rescues narrow.** A post-hoc change that makes a
   claim easier to satisfy is a forbidden rescue and is refused; a change that
   makes it harder is a correction and is logged in the revision history with
   its date and its cause.
5. **A branch push is not a release.** Nothing counts as published until CI
   is green on the PR *and* the post-deploy smoke gate confirms the live site
   serves the same numbers. *CI: `smoke_deployed.py`.*
6. **Adjudication status is never hidden.** The current 19 rows are declared
   single-primary-reviewer and therefore cannot support a systematic-review
   or prevalence claim. Dual review, disagreement records, and a retrieval
   ledger are a v1.0 archival-release gate — not work already completed.
7. **No silent truncation.** Any bound on coverage — top-N, sampling, no
   retry — is printed where the result is printed.
8. **Freshness has teeth.** A claim past its review window fails CI. That
   failure *is* the trigger firing; the fix is re-review or withdrawal, never
   an extended window.
9. **External claims trail internal evidence.** Nothing is said in public
   that the repository cannot already reproduce on a clean clone.

## 5. Explicit non-goals for the next 90 days

Named so that they can be refused quickly:

- More dashboards, visualizations, or social copy for results already stated.
- A wider "comprehensive" census. Breadth is not the missing ingredient.
- A 28-guard leaderboard. Leaderboards re-create the exact marginal-only
  reporting this project is arguing against.
- Calling MJGD a *standard*. It is a schema until someone outside this
  repository uses it, and then it is a used schema.
- Any productization, funding pitch, or naming of the work as a venture.
- **A "sovereign assurance engine."** A local-inference / graph-orchestration /
  self-healing-scraper / edge-Merkle-ledger stack is a twelve-month
  infrastructure programme with no result to carry. Every layer of it is
  downstream of evidence this repository does not yet have. Two components
  earn their place and are already here in one line each: the clean-clone
  replay (`scripts/reproduce_cc001.py`) and content-hash binding of every
  external artifact. The rest — visual audit video, taxonomy crawlers,
  anti-bot fetchers, a public Merkle root — buys attestation of numbers whose
  *identification* is the actual open problem. Build the witness when there is
  something worth witnessing; the missing piece for Days 71–90 is one
  independent reproduction by a person who is not the author, which no amount
  of local infrastructure supplies.
- **Publishing an epistemic-tag vocabulary as a public artifact.** The tags
  govern this repository's own discipline (see `docs/EPISTEMIC_TAGS.md`). A
  private notation that keeps the author honest becomes, when published as a
  framework, exactly the kind of un-adopted standard §5 already refuses.

## 6. The identity this converges on

> We did not merely find an absent reporting field. We released the smallest
> reproducible protocol that fills it — and showed exactly what becomes
> identifiable once it is filled.

## 7. The next experiment: Stack Behavior Surface / Composition Eval 1.0

The next contribution is not a larger census. It is a small prospective
experiment that makes the difference between a table and a system observable.
Call the released object a **Stack Behavior Surface**: a provenance-bound
record of how a named composition behaves across threat strata, routes, and
time.

### The unit of evidence

For each eligible pre-intervention artifact `i`, component `g`, route `π`,
threat stratum `s`, and version/time `t`, preserve three linked records:

| Record | What it observes | What it can identify |
|---|---|---|
| Shadow decision tensor `D[i,g]` | Every eligible guard's decision on the same pre-intervention artifact | Static overlap `O(s)`, union, all-miss, intersections, and residual coverage |
| Route trace `T[i,π]` | The actual ordered execution, intervention, model state, tool state, error state, and terminal outcome | Operational route risk `R_π(s)` |
| Adaptive episode `A[i,π,a,t]` | A sealed-holdout attempt under a declared attacker interface and budget | Adaptive robustness `R_π,a,t(s)` |

The distinction is non-negotiable. An early block censors later components on
the actual route. Full shadow exposure repairs that *measurement* omission,
but it does not recreate a counterfactual agent trajectory after an
intervention. The study must therefore report actual paths and shadow paths
side by side, never silently substitute one for the other.

### Three hypotheses, each allowed to lose

1. **Shared-blind-spot hypothesis.** Conditional on a declared threat
   stratum, the direct all-miss rate is materially above the independence
   plug-in and added layers catch little of the preceding residual.
2. **Conditional-complementarity hypothesis.** At the same benign-user
   burden, each added layer catches a material, predeclared fraction of the
   preceding residual on the shared population.
3. **Sequential/adaptive-collapse hypothesis.** Shadow overlap appears
   favorable, while actual route traces or sealed adaptive episodes lose the
   apparent gain by changing exposure, trajectories, or attacker behavior.

These are not a rhetorical trilemma. They can all hold in different strata.
The release must name the stratum in which a conclusion is offered, state the
decision margin before looking, and publish the null or HOLD result with the
same prominence as a positive result.

### A three-arm design that can settle something

**Arm S — static full exposure.** Freeze a legitimate, rights-cleared item
population; threat taxonomy; label process; components; thresholds; versions;
and missingness codes before outcome access. Run every eligible component on
every item in shadow mode. Retain binary decisions, scores where lawful,
errors, latency, and configuration hashes. Compute direct joint quantities
and the entire marginal-only identification interval; do not elevate an
independence product into a null result.

**Arm R — operational routes.** In a replayable sandbox, run the actual
composition plus predeclared route/order ablations. An episode—not an isolated
prompt—is the unit: input/history, retrieved context, model response, tool
state, intervention, and terminal action are all versioned. When intervention
can change a later trajectory, randomize or otherwise predeclare the route
assignment; report the route-specific denominator and every aborted, timed-out,
or ineligible episode.

**Arm A — adaptive sealed holdout.** Hold back a threat-stratified evaluation
set. State exactly what an attacker can observe, how many attempts it receives,
whether it sees scores or only terminal feedback, and when versions change.
Do not turn publicly released benchmark prompts into an optimization oracle.
Sensitive prompts or traces may remain controlled-access, while a signed
outcome tensor and aggregate release still permit an independent recomputation
of the declared estimands.

### What makes this credible rather than merely elaborate

- A versioned manifest binds the population, rights basis, hashes/configs,
  route semantics, labels, exclusions, missingness taxonomy, analysis code,
  and release date.
- Outcome labels are adjudicated before joint results are examined; a second
  reviewer records disagreements rather than collapsing them into a final
  count without provenance.
- The primary decision uses a policy-relevant upper confidence bound for
  terminal unsafe pass in the highest-risk stratum. Sample size follows that
  bound and a declared benign-burden tolerance—not a pleasing round number.
- Every public plot includes direct joint observations, marginal-only bounds,
  uncertainty, benign-union burden, route effects, and a version-drift note.
- A clean environment reproduces the packet from the released manifest. A
  failed replay, missing tensor slice, or source-rights ambiguity is a HOLD,
  not a prose exception.

The deliverable is a packet, not a paper-shaped conclusion. If the direct
measure is cheap and decisive, the packet proves it. If it is unstable,
expensive, or not sufficient for operational decisions, the packet proves
that instead. Both outcomes move the field past attractive but untestable
stack rhetoric.
