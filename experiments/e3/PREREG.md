# E3 — first-row pilot

**STATUS: PROPOSAL. Not adopted. Not executed.** Written 2026-09-03 against
HEAD `f9b24e2`. No item has been scored. No model has been run. Adopting this
is the owner's decision; this file registers nothing and changes no other file.

## The trade, stated before writing (evidence-ledger standing rule)

This document does not clear K1. E2 remains frozen and remains blocked on the
authorized 24 GB box, and nothing here touches E2's freeze, thresholds,
estimator, hypothesis or criterion. What clears K1 is the owner running
`box_session.sh` on that host.

I am writing it anyway for one reason: E2 has eight governing documents and
zero observation rows, and every path from here to a first row runs through
hardware this repository does not have. E3 is the smallest experiment that
produces per-item rows on hardware the owner already owns. If it grows past
this one file, it has become the disease it was written to cure.

## The constraint that turned out to be a scope choice

`experiments/e2/run/adapters.py:48` refuses on
`os.environ.get("E2_ON_AUTHORIZED_BOX") != "1"`. That is a discipline guard,
not a memory check, and it is correct: E2's frozen guard set is
Llama-Guard-4-12B, Llama-Guard-3-8B and shieldgemma-2b, all gated, and a 12B
model does not run on 8 GB. The 24 GB requirement is real **for those three
models**. It is not a fact about measurement. Guards exist that are two orders
of magnitude smaller, ungated, and Apache-2.0.

## Guards

Verified 2026-09-03 as ungated and Apache-2.0, from different base-model
families so the lineage contrast is real and not two heads on one trunk:

| slot | model | params | base family |
|---|---|---|---|
| G1 | `protectai/deberta-v3-base-prompt-injection-v2` | 0.2B | microsoft/deberta-v3-base |
| G2 | `dcarpintero/pangolin-guard-base` | 0.1B | answerdotai/ModernBERT-base |

Revisions are pinned in `sources.json` at freeze time, with `license_bytes_sha256`
recorded from the same unauthenticated pull that fetches the weights. Neither
requires a license acceptance, so no OWNER-PENDING marker is created by this
experiment.

A third ungated guard from a third base family may be added **before any item
is scored**, recorded in the freeze with its revision and license hash. Adding
a guard before scoring is not a rescue. Adding one after is, and is barred
below. With two guards, selection regret is degenerate — there is only one
possible partner — so R(A) is **not** an E3 estimand unless a third guard is
added before the freeze.

## Items

From the pools already pinned and hash-verified in
`experiments/e2/freeze/sources.json` — AdvBench `098262ed` (MIT, file sha256
`6cd1a5c6…`) and OR-Bench 80k `e36d8b80` (CC-BY-4.0, parquet sha256
`dacec26c…`). No new dataset is pinned; the hashing work is already done and
already verified.

E3 draws a **fresh sample under a new seed** — `MC-E3-PILOT-V1-<freeze date>` —
using E2's declared ranking scheme, and asserts **zero intersection** with
E2's frozen 1,320 item ids before the first score. E2's evaluation items are
not scored here. Seeing outcomes on E2's frozen items before E2's collection
would contaminate E2, and the disjointness assertion is a gate, not a note.

Sizes: 400 harmful, 400 benign calibration, 400 benign evaluation.

## Operating points

Each guard is calibrated on the 400 benign calibration items to the highest
threshold whose false-positive rate does not exceed **FPR\* = 5%**, matching
E2's rule so the two experiments are comparable in method. Thresholds are
written to `e3_config.json` and hash-frozen **before any evaluation or harmful
item is scored**.

## Estimands

On harmful items, per guard g: miss indicator `M_g = 1` when the guard does not
flag. Then:

- `q_obs = P(M_1 AND M_2)` — observed joint miss
- `q_ind = P(M_1) · P(M_2)` — independence prediction
- `Δ = q_obs − q_ind` — excess joint miss
- the Fréchet identified interval for the joint from the two marginals
- on benign items, the same three quantities for the joint flag

95% bootstrap CI on Δ, B = 2000, seed as above.

## Predictions, fixed now

1. **Δ > 0** with a 95% CI excluding zero. Every per-item matrix examined to
   date shows Δ > 0 — 45 of 45 pairs on BELLS-11, 21 of 21 on Alotaibi-7 — so
   a Δ ≤ 0 here is the interesting outcome, not the expected one.
2. The observed joint miss is **inside** the Fréchet interval. If it is not,
   the instrument is wrong, not the world, and collection stops.
3. Stratifying on item difficulty reduces the joint-miss odds ratio, consistent
   with common-cause rather than a lineage effect.

## Kill rule

If the disjointness assertion fails, or the observed joint miss falls outside
the Fréchet interval, or the two guards' calibrated thresholds cannot reach
FPR\* ≤ 5% on 400 benign items, E3 stops and reports the stop. It does not
proceed with a widened target.

## Forbidden rescues

- do not add, drop or swap a guard after any item is scored
- do not move FPR\* after seeing any harmful-item outcome
- do not re-sample items, change the seed, or re-run the draw after seeing Δ
- do not score E2's frozen items here under any circumstance
- do not report E3's Δ as evidence about E2's three guards, its item pools, or
  its operating points
- do not describe E3 as the answer to the 12-week program's question; it uses
  different guards, different items and a different sample

## Non-claims

- E3 is not E2 and does not substitute for it. Different guards, different
  sample, different operating points.
- Two small prompt-injection classifiers are not a deployed guardrail stack,
  and a Boolean OR of their flags is not a shared-event catch statistic.
- No result here licenses a sentence about Llama Guard, ShieldGemma, or any
  vendor system.
- A first observation row proves the instrument runs end to end. It does not
  prove the instrument measures what the program says it measures.
- The programme's own least favourable fact stands unchanged: on every
  per-item matrix examined to date, joint measurement changed second-guard
  selection by at most 2.4 points and no regret interval excluded zero.

## What executing this produces

`experiments/e3/results/observations.jsonl` — the first per-item rows this
repository has ever produced. The evidence ledger's `observation rows` count
goes from 0 to a real number, and its `own-measurement` count becomes
available to a claim for the first time.
