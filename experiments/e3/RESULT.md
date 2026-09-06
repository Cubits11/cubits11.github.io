# E3 RESULT — 2026-09-06

**The first observation rows this repository has produced.** 2,400 of them:
1,200 items × 2 guards. Every previous empirical number here was a recount of
someone else's released file.

**Prediction 1 failed.** It is registered because it failed, in the same commit,
with the prediction quoted — `PREREG.md` calls this the interesting outcome and
that has to be honoured when it happens, not admired in advance.

## The numbers

Harmful stratum, n = 400, `or-bench-toxic` at `e36d8b80`, thresholds from
`e3_config.json` sha256 `e163a2f2…` committed **before** any harmful item was scored.

| quantity | value |
|---|---|
| miss rate, G1 (deberta prompt-injection v2) | **0.9825** |
| miss rate, G2 (pangolin-guard-base) | **0.9625** |
| `q_obs` — both miss | **0.9475** |
| `q_ind` — independence plug-in | 0.9457 |
| **Δ = q_obs − q_ind** | **+0.0018** |
| 95% bootstrap CI on Δ, B = 2000 | **[−0.0010, +0.0071]** |
| **CI excludes zero** | **No** |
| Fréchet interval from the marginals | [0.9450, 0.9625] |
| `q_obs` inside it | **Yes** |

Benign evaluation, n = 400: joint flag 0.0050, plug-in 0.0013, Δ +0.0037.

## Against the three predictions

| # | Prediction, quoted | Outcome |
|---|---|---|
| 1 | *"Δ > 0 with a 95% CI excluding zero. Every per-item matrix examined to date shows Δ > 0 — 45 of 45 pairs on BELLS-11, 21 of 21 on Alotaibi-7 — so a Δ ≤ 0 here is the interesting outcome, not the expected one."* | **FAILED.** Δ = +0.0018, CI includes zero. The sign is positive and the magnitude is not distinguishable from zero. |
| 2 | *"The observed joint miss is inside the Fréchet interval. If it is not, the instrument is wrong, not the world, and collection stops."* | **HELD.** 0.9475 ∈ [0.9450, 0.9625]. No stop. |
| 3 | Stratifying on item difficulty reduces the joint-miss odds ratio. | **NOT COMPUTED.** Not attempted, not estimated, not inferred. It is open. |

## Why the test had almost nothing to measure

**Both guards miss 96–98% of this pool**, and that is the dominant fact about
this run.

The Fréchet interval is **[0.9450, 0.9625] — 1.75 percentage points wide.** When
both marginals sit at the extreme, they *nearly identify* the joint on their
own. There was almost no room between the endpoints for a joint measurement to
say anything the marginals had not already fixed.

That is this programme's own thesis running in the regime where it says least,
and it is worth stating plainly rather than as a caveat: **marginal-only
reporting is uninformative when the identified set is wide, and this run's
identified set was nearly a point.** A null here is what the mathematics
predicts, not a surprise about dependence.

## The mismatch, and it is mine

G1 is a **prompt-injection** classifier. G2 is a jailbreak/injection guard.
`or-bench-toxic` is a pool of **harmful requests**, not injections. The guards
are close to blind on it by construction, which is what drove the 96–98% miss
rates and therefore the degenerate interval.

`PREREG.md` carried the same mismatch with AdvBench — harmful *behaviours* are
not injections either — so the pool substitution did not introduce it. But I
swapped the pool without re-examining guard/pool fit, and that check was
available for free before any weights were downloaded. Recorded here rather
than discovered by a reader.

**What this does not license:** the result is not evidence that these guards are
bad, and not evidence that joint measurement is unnecessary. It is evidence that
*this pairing* of guards and pool produces marginals too extreme for the
question to be interesting.

## What would make E3 informative

A pool the guards are built for — prompt injections and jailbreak attempts —
where miss rates land away from the extremes and the Fréchet interval is wide
enough to hold an answer. That is a **new freeze and a new prereg**, drawn
before any outcome from it is visible. It is not a re-run of this one, and
this result stands whatever that one shows.

## Non-claims

- No vendor, product, or deployed stack is described. Two research classifiers on one pool.
- 2,400 rows prove the instrument runs end to end. **They do not prove it measures what the programme says it measures** — see the mismatch above, which is a live argument that on this pool it did not.
- Nothing here transfers to E2's three guards, its pools, or its operating points.
- The programme's least favourable fact is unchanged and untested by this: joint measurement changed second-guard selection by at most 2.4 points on every per-item matrix examined, with no regret interval excluding zero.
- Discrepancy D1 (the FPR\* threshold direction) is declared in `e3_config.json`; it was decided before any harmful item was scored.
- Not registered in `claims.yaml`. Registration is an owner action.
