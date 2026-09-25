# Same scores, different worlds

**What a stack-level assurance claim can establish when each guard's performance
is known and their joint behavior is not.**

Pranav Bhave · [cubits11.github.io](https://cubits11.github.io/) · the
repository's exact state is the citation (`CITATION.cff`).

Every number below is recomputed from its source by
`tests/test_research_synthesis.py`; an edited number fails the manifest. This
file synthesizes. It governs nothing: the registry (`claims.yaml`), the frozen
experiment objects and the census are the authorities, and where this text and
they disagree, they win.

## The question

A deployment runs guards as a stack. An evaluation usually reports each guard
alone. The stack's residual risk is the rate at which every guard misses the
same input: a joint quantity. I ask what the per-guard numbers entitle anyone to
say about that joint quantity, what additional evidence would entitle them to
say more, and whether public evaluations preserve that evidence.

## 1. Identification

Per-guard miss rates do not determine the joint miss rate. For two guards with
miss rates *a* and *b*, every joint miss rate in
[max(0, *a* + *b* − 1), min(*a*, *b*)] is consistent with them, and both ends
are attained by explicit distributions. For two guards that each miss 10%, the
set is [0.0, 0.10]; multiplying the rates gives 1%, one point in that set,
selected by an independence assumption the data does not supply.

The uncertainty is structural. More items do not narrow it; only joint
observations or declared assumptions do. The kernel that computes the bounds and
their endpoint witnesses is registered as CC-001 and CC-004 and re-executed from
a clean clone of `cc-framework` at its bound commit.

## 2. Does public reporting preserve the joint evidence?

The Missing Column census (MC-001) applies frozen inclusion criteria to public
guardrail evaluations and classifies what each one preserves. Of 20 evaluations
examined, 14 establish a shared item set and a common event definition, and 5
preserve one of the census's declared joint-evidence artifacts. Its stricter
ladder is 14/12/0: no evaluation documents matched thresholds with full
exposure.

The census is bounded: one reviewer, a frozen search, and a correction route
that rejects the current counts if a qualifying evaluation was missed. It
measures reporting practice. It does not rank vendors or estimate the safety of
any stack.

Where released per-item verdicts exist, they can be recounted. On BELLS's
released subset (MC-002), five supervisors all miss 9 of 82 harmful prompts; the
five published miss rates alone pin that rate only to [0.00%, 14.63%].

## 3. Measuring the joint quantity under a frozen design

From E3 onward I ran the measurements myself, all but E6 under a frozen
preregistration. The early runs failed, and every failure is kept:

| run | what happened | disposition |
|---|---|---|
| E3 | the pool put both guards at an extreme; marginal-only width 0.0175 | stands; primary prediction failed |
| E3B | a matched pool produced the opposite extreme; width 0 | stands; two predictions failed |
| E6 | the same width question on a published economic model | rejected: the permutation moved unequal-mass atoms |
| E7 | the prereg's threshold rule pointed the wrong way and selected a degenerate threshold | void |
| E7B | calibration used a pool other than the declared one | rejected as stated |
| E8 | the identification floor was declared first; no scouting pool reached it (widest 0.07 against 0.1) | stopped before any evaluation item |
| E9 | calibration moved to representative benign traffic; one pool admitted | result below |

E3 and E3B showed that a discrepancy can only be seen where the marginals leave
room for one. E8 made that a gate: a pool is measured only if its marginal-only
width reaches a declared floor. E9 changed one variable, the benign population
the operating point is calibrated on. Two of three pools cleared the floor; one
of those had a complete measurement slice and was admitted.

**E9.** On 1,000 measurement items from the admitted pool, two classifiers at a
frozen operating point both miss at a rate of 0.3220. The independence plug-in
from their miss rates is 0.2652. The discrepancy is +0.0568, with a 95%
bootstrap interval of [+0.0472, +0.0669]. The miss rates alone would have
allowed anything in [0.1240, 0.3370]. All five predictions fixed before scoring
held, and the preregistered verdict is DISCREPANT.

At its scope, this says: on this pool, for these two guards, at this operating
point, the joint miss rate differs from what independence predicts, and the
marginals alone leave a wide set. The interval's lower end is below the 0.05
smallest effect of interest, so it establishes a discrepancy from zero, not one
beyond 0.05. The interval does not include calibration uncertainty. One pool
was chosen for having intermediate marginals. Full scope and threats:
[`experiments/e9/RESULT.md`](experiments/e9/RESULT.md).

An exploratory reanalysis, run after the outcome was read and changing nothing
above ([`research/exploratory/e9_robustness.json`](research/exploratory/e9_robustness.json)),
tests two of those limits and adds one quantity. Re-selecting both thresholds on resampled
calibration sets widens the interval to [+0.0388, +0.0764]; the discrepancy
is positive in every replicate and reaches 0.05 in 1,492 of 2,000. At false-positive
budgets of 0.01, 0.02, 0.03 and 0.04 it stays positive and falls below 0.05, so the
sign is stable across operating points and the size is not. The decision-facing
number is residual coverage: of the 337 items G1 misses, G2 catches 15.

## 4. Claims as executable objects

Every public claim is a registry entry with a support binding, a falsifier and
a fixed consequence, forbidden rescues, non-claims, a review window, and a
declared transition history. Generated pages are drift-checked against their
sources; bound commits must be reachable from their repository's default
branch; figure geometry is asserted.

The founding cohort E3–E7B motivated the next step: a preregistration proves
that an analysis was declared, not that the declared analysis ran. Two of those
five runs stand. Each defect was caught by hand after outcomes were visible. From
E8, a frozen `contract.json` carries each experiment's scientific choices and
the runner reads them from it. Whether that intercepts defects before outcomes
is not yet measured: no divergence has occurred prospectively, so there is
nothing to count (`research/DIRECTION.yaml`).

These checks establish that stated artifacts regenerate stated outputs. They do
not establish that the science is right, and they are not independent of the
person who writes them (`SECURITY.md`).

## What this program does not establish

- that guard pairs in general depart from independence, or in which direction;
- anything about a deployed stack, a routing policy or a vendor's product;
- that any guard or stack is safe or unsafe;
- that the census covers every public evaluation;
- independent reproduction. Every run so far is the author's, and re-running
  committed scripts is replay.

## Open questions

- Does the E9 discrepancy survive a second guard pair, a second pool and
  calibration uncertainty carried into the interval?
- Can the verdict rule itself live in the frozen contract? For E9 it lives in
  `run/analyze.py`.
- Will a person other than the author reproduce any of this from a clone?
- Which public evaluations will release the per-item outcomes the census asks
  for?

## Reproduce, correct, cite

- Reproduce: [README → Reproduce the claims](README.md#reproduce-the-claims).
- Correct: [the correction log](https://cubits11.github.io/corrections/); a
  counterexample or a missed evaluation rejects the current counts.
- Cite: `CITATION.cff`, with the exact commit.
