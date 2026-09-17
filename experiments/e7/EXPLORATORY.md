# E7 exploratory — nine judges, one global threshold, outcome seen

**Not a test.** These numbers were computed before any preregistration existed
and are recorded so that E7B's prereg cannot be mistaken for a description of
data nobody had looked at. No figure here held a prediction, because none was
made.

Source: `shawnray-research/certified-agent-guardrails` @ `79097583`, the
reproducibility artifact for arXiv:2607.22868v1. Labels from `_inj_goals.json`
(35 AgentDojo injection goals). Nine judges sharing the 132-item pool:
`bluesminds`, `cohere`, `dsv4`, `gemma2_9b`, `gpt4omini`, `gptoss120b`, `grok`,
`llama3.1_8b`, `llamaguard`. A miss is a harmful item scored below **0.5**, a
single global threshold applied to every judge — not a calibrated operating
point, and the reason E7B calibrates per judge instead.

Over the 36 pairs, all non-degenerate:

| statistic | value |
|---|---|
| mean excess joint miss, `q_obs − p₁p₂` | **+0.107** |
| median position in the Fréchet interval | **81%** of the way to the upper bound |
| pairs at or above 90% of the upper bound | **10 of 36** |
| pairs with `q_obs > p₁p₂` | **36 of 36** |

Several pairs sat exactly at the upper bound, meaning one judge's misses were a
subset of the other's: on those items the second judge added nothing.

## Why this is weak evidence even so

- **n = 35 harmful items.** Every rate moves in steps of 0.029. No interval is
  implied by any point estimate above.
- **One global threshold across judges whose score scales differ.**
  `llamaguard` emits two distinct values, `cohere` ten, `grok` fifteen. A 0.5
  cut means something different for each.
- **36 pairs from 9 judges, no multiplicity control**, and the pairs are not
  independent of each other.
- These are research judges on a benchmark, not a deployed stack.
- The direction is unsurprising: the artifact's own `ensemble_robustness.py` is
  described by its README as showing "ensembling does not fix safe-washing (the
  max-ensemble margin stays high because the vulnerability is correlated across
  judges)". The phenomenon was found and named by that author first.

## What it is good for

Exactly one thing: it establishes that the question is **non-degenerate on this
kind of data**, which E3 and E3B could not do — both of their pools drove the
marginals to the extremes where the Fréchet interval collapses to almost a
point. That is what made a real preregistration worth writing, and E7B is it.
