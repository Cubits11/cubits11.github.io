> **Correction recorded 2026-09-10 — E7B-001: REJECTED as stated.** Calibration uses the all-nine shared pool instead of each judge’s own pool, changing one threshold from 0.95 to 1.00. Pair evaluation also uses the global intersection. The preregistration-conforming confirmation claim is rejected; the original HELD labels are historical outputs. See [formal disposition](CORRECTION-2026-09-10.md). The original report below is retained verbatim as historical output; it is not current launch evidence.

# E7B — the missing column, measured, against a preregistration

Run 2026-09-10 against `experiments/e7b/PREREG.md`, frozen at `f646e136` when
none of the nine hold-out score files had been retrieved. **All five predictions
held.** This is the first non-degenerate, preregistered measurement this
repository has produced.

## The result

Six of nine hold-out judges reached a 5% benign false-flag rate and were
included; three did not and were excluded by the pre-stated rule. Their shared
pool is 96 items — 21 injection goals, 75 benign — and all 15 pairs were
non-degenerate, above the prereg's floor of 6.

| prediction | verdict | value |
|---|---|---|
| P1 median `delta` > 0 | **HELD** | +0.2018 |
| P2 mean `delta` ≥ +0.05 | **HELD** | +0.1852 |
| P3 median `reach` ≥ 0.60 | **HELD** | 0.900 |
| P4 every `q_obs` inside its Fréchet interval | **HELD** | all 15 |
| P5 `q_obs > q_ind` on ≥ ⅔ of pairs | **HELD** | 15 of 15 |

## What the numbers say

Take the modal pair. Two judges, each calibrated to flag at most 5% of benign
items, each missing about half the injection goals:

```
p1 = 0.524    p2 = 0.476
independence would predict both miss  :  0.249
they actually both miss               :  0.476
the most they could possibly both miss:  0.476
```

The observed joint is **at** the Fréchet upper bound. One judge's misses are a
subset of the other's: on the items the first one let through, the second one
caught nothing. Seven of the fifteen pairs sit exactly there; the median pair
sits 90% of the way up its interval.

Quoting this pair's residual risk from its marginals under independence would
understate the both-miss rate by a factor of **1.9**. Adding the second judge to
the first bought a reduction from 52.4% to 47.6% — 4.8 points, one item out of
twenty-one — where independence promised a fall to 24.9%.

## Why this one counts and E3 and E3B did not

E3 and E3B produced 4,800 rows and measured almost nothing, because both pools
pushed the marginals to the extremes: at miss rates of 0.98 and 0.96 the Fréchet
interval is 1.75 points wide and the answer is nearly forced. Here the marginals
land between 0.43 and 0.52, the intervals are genuinely wide, and the joint had
room to be anywhere in them. It was at the top.

Nothing was loaded to get this. Every score was already published, so the host
refusal in `experiments/e2/run/adapters.py` is not engaged and no owner action
was required. The measurement E2 was built to make has a public, ungated,
per-item analogue, and it took one afternoon and no GPU.

## What this does not license

- **The bound and the phenomenon are not this repository's.**
  arXiv:2607.22868v1 (Shawn Ray, Carnegie Mellon, 24 July 2026) states the
  Fréchet–Hoeffding bracket for an any-flag gate as a proposition, and the same
  artifact's `ensemble_robustness.py` is described by its own README as showing
  "ensembling does not fix safe-washing (the max-ensemble margin stays high
  because the vulnerability is correlated across judges)". That author found the
  bound, released the per-item scores that make this checkable, and named the
  correlation. E7B measures it against a preregistration and claims priority for
  neither.
- **21 harmful items.** Every rate moves in steps of 0.048, and no point
  estimate here implies an interval. The prereg fixed no confidence procedure
  and none is reported.
- **15 pairs from 6 judges are not 15 independent observations.** No multiplicity
  control was preregistered and none is claimed.
- **One pool, one benchmark, one operating point per judge.** AgentDojo
  injection goals are not a deployed threat model, and these are research judges,
  not a shipped stack.
- **Thresholds cluster at 0.95 and 1.00** because these judges emit few distinct
  scores. A coarse score scale makes the calibration coarse.
- **Says nothing about E2's three guards**, about any vendor's product, or about
  any population.
- Three judges were excluded for not reaching 5% FPR. That is a pre-stated rule,
  not a judgement about them, and their absence is not evidence about them.

## Reproduce

```bash
python3 experiments/e7b/run/measure.py    # exit 2 if a source is unreachable
```

The nine score files are fetched from
`shawnray-research/certified-agent-guardrails` at `79097583` (MIT) and cached
under `freeze/cache/`. The prereg commit `f646e136` precedes this result's
commit, which is the evidence that the hold-out was unread when the predictions
were fixed.
