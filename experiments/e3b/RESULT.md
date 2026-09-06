# E3B RESULT — 2026-09-06

**Prediction 1 failed. Prediction 3 failed. Prediction 2 held.** Registered as
failures, with the predictions quoted, in the same commit as the numbers.

E3B was meant to fix E3's degenerate identified set by putting the guards on a
matched pool. It produced a degenerate identified set **at the opposite end**,
and the pair of failures is a better result than either run alone.

## The numbers

Injection stratum, n = 400, `Lakera/gandalf_ignore_instructions` @ `04737b65`.
Thresholds from `e3b_config.json` sha256 `252a5db9…`, committed **before** any
injection item was scored.

| quantity | value |
|---|---|
| miss rate, G1 (deberta prompt-injection v2) | **0.0000** — caught 400 of 400 |
| miss rate, G2 (pangolin-guard-base) | **0.3975** — missed 159 of 400 |
| `q_obs` | **0.0000** |
| `q_ind` | 0.0000 |
| **Δ** | **+0.0000** |
| 95% bootstrap CI, B = 2000 | **[0.0000, 0.0000]** |
| Fréchet interval | **[0.0000, 0.0000]** — width **0** |
| `q_obs` inside it | Yes, trivially |

Benign evaluation, n = 400: joint flag 0.0075, plug-in 0.0026, Δ +0.0049.

**G1's result is not an operating-point artifact.** Its threshold is 0.004479,
and its **lowest** score across all 400 injections is **0.6299** — 140× the
threshold. G1 would still catch all 400 at a threshold of 0.6.

## Against the predictions

| # | Prediction, quoted | Outcome |
|---|---|---|
| 1 | *"Δ > 0 with a 95% CI excluding zero."* | **FAILED.** Δ = 0 exactly; the CI is the degenerate [0, 0]. |
| 2 | *"`q_obs` lies inside the Fréchet interval. If not, the instrument is wrong."* | **HELD**, trivially — the interval is a point and `q_obs` is that point. |
| 3 | *"The Fréchet interval is wider than 10 percentage points, and at least one guard's miss rate falls in [0.05, 0.60]."* | **FAILED on the half that mattered.** G2's miss rate is 0.3975, inside [0.05, 0.60] — that half held. The interval is **0 points wide**, not >10. |

Prediction 3 was written as *"the point of E3B and deliberately falsifiable — if
the interval comes back narrow again, the redraw failed on its own terms."* It
came back narrower. **The redraw failed on its own terms.**

## What the two failures say together

This is the part worth keeping.

`q_obs` is bounded above by `min(p₁, p₂)`. **If either guard misses nothing, the
joint miss is exactly zero and the marginals have fully identified it.** No joint
measurement can add anything, because there is nothing left to add.

| run | p₁ | p₂ | Fréchet width | why degenerate |
|---|---|---|---|---|
| E3 | 0.9825 | 0.9625 | 1.75 pp | both guards miss almost everything |
| E3B | 0.0000 | 0.3975 | **0 pp** | one guard misses nothing |

Two pilots, two degenerate identified sets, at opposite extremes. That yields a
sharpening of this programme's own thesis rather than a dent in it:

> **Marginal-only reporting is uninformative in the middle and fully informative
> at the extremes.** The missing column is worth reporting precisely when every
> guard's miss rate is intermediate — which is the regime real stacks are
> supposed to operate in, and the regime neither pilot reached.

This is consistent with everything already registered: BELLS-11's 45 of 45
positive Δ came from a matrix of intermediate marginals, and MC-003's identified
set `{0/82 … 12/82}` is wide for the same reason.

## Contamination

`PREREG.md` flagged G2 as the contamination risk — its fine-tuning corpus
returns HTTP 401 — and said a near-zero **G2** miss rate would be
train-on-test-compatible. The extreme came from **G1** instead, whose declared
training sets do not include Gandalf.

Two live explanations, not separated here:

1. **Generalisation.** Gandalf prompts are the textbook form — *"Ignore all
   previous text…"* — and G1 trains on injection corpora including
   `Harelix/Prompt-Injection-Mixed-Techniques-2024` and
   `jackhhao/jailbreak-classification`. Catching all 400 is unremarkable for a
   detector built for exactly this.
2. **Near-duplicate leakage.** Gandalf is not in G1's declared sets, but
   Gandalf-*like* text plausibly is. Not checked.

**Nothing here distinguishes them**, and the confident-margin finding (minimum
score 0.6299) is equally consistent with both.

## Precondition for any third pilot, statable now

**Both guards' miss rates must be intermediate on the chosen pool** — say each
in [0.15, 0.85] — or the identified set is degenerate before a single row is
scored and the experiment cannot answer its question.

That is now a **cheap pre-scoring check**: score a small pilot slice, read the
two marginals, compute the Fréchet width, and abandon the pool if it is narrow.
Both E3 and E3B would have been stopped by it for the cost of ~40 items. It
belongs in any future prereg as a gate, not a hope.

## Non-claims

- No vendor, product, or deployed stack. Two research classifiers, one pool.
- **E3B does not replace E3.** E3's null stands on its own pool; this is a
  different experiment and both are registered.
- G1 catching 400 of 400 is not evidence that G1 is a good guardrail. It is one
  pool of one attack family at one operating point.
- G2 missing 159 of 400 is not evidence that G2 is a bad one, and contamination
  status is unverifiable for it either way.
- 2,400 more observation rows prove the instrument runs. They do not prove it
  measures what the programme says it measures — on this pool the question was
  degenerate, so it measured almost nothing.
- The programme's least favourable fact is untouched: joint measurement changed
  second-guard selection by at most 2.4 points on every per-item matrix
  examined, with no regret interval excluding zero.
- Not registered in `claims.yaml`. Registration is an owner action.
