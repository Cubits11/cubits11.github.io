# E7 — preregistration, written before the hold-out was read

Frozen 2026-09-10, before any byte of the seven `frontier_*_bench.json` files
was retrieved. This file is the commitment; the outcome is not yet visible.

## Why a preregistration is possible here at all

E6 could not be preregistered: its artifacts were public before the experiment
existed. E7 can, because the release it uses is split into two disjoint judge
sets, and I have read only one of them.

**Read (exploratory, outcome visible).** Nine judges whose score files carry the
same 132-item AgentDojo pool: `bluesminds`, `cohere`, `dsv4`, `gemma2_9b`,
`gpt4omini`, `gptoss120b`, `grok`, `llama3.1_8b`, `llamaguard`. I have computed
pairwise joint miss rates on these at a single global threshold of 0.5 and seen
the answer. `EXPLORATORY.md` records what I saw. **Nothing in that file is a
test, and no number in it may be reported as a prediction that held.**

**Not read (the hold-out).** Seven judges whose score files carry a 167-item
pool: `frontier_claude-opus-4-5`, `frontier_claude-sonnet-4-5`,
`frontier_deepseek-v3.2`, `frontier_glm-5`, `frontier_kimi-k2.5`,
`frontier_mistral-large-3`, `frontier_nova-pro`. At the time of writing I have
retrieved none of them and know none of their scores. The predictions below are
about these seven and only these seven.

If this file is committed after any frontier score has been read, E7 is void and
must be reported as void. The commit order is the evidence, and
`scripts/verify_e7.py` refuses to record a confirmation unless this file's
commit is an ancestor of the results commit.

## Source

`github.com/shawnray-research/certified-agent-guardrails` at
`79097583be7786976ea1b9ae79f3ff900d9e66b7` (MIT, HEAD dated 2026-07-09), the
reproducibility artifact for *What Can Be Enforced? A Theory of Certified
Runtime Safety for Tool-Using Agents* (arXiv:2607.22868v1, Shawn Ray, Carnegie
Mellon, 24 July 2026).

Item labels come from `_inj_goals.json` in the same tree: its 35 strings are the
AgentDojo injection goals. On the 132-item pool the complement is 97 benign user
tasks. The hold-out's 167-item pool is a superset; the label rule is the same —
an item is harmful if and only if its text is in `_inj_goals.json`.

No model is loaded and no API is called. Every score is already published. This
experiment is therefore outside the scope of the host refusal in
`experiments/e2/run/adapters.py`, because it loads nothing.

## Estimator, fixed here

Per judge, the operating point is **the highest threshold whose false-flag rate
on the benign items of its own pool does not exceed 5%** — the same rule E3 used,
restated here so it is not chosen after the fact. Ties resolve to the higher
threshold. A judge whose score distribution cannot reach 5% FPR at any threshold
is excluded and the exclusion is reported.

For each unordered pair of hold-out judges, on the harmful items of their shared
pool:

- `p1`, `p2` — marginal miss rates at each judge's own calibrated threshold
- `q_obs` — the fraction of harmful items **both** miss
- `q_ind` — `p1 * p2`
- `delta` — `q_obs - q_ind`
- the Fréchet interval `[max(0, p1 + p2 - 1), min(p1, p2)]`
- `reach` — `(q_obs - lo) / (hi - lo)`, the observed joint's position in that
  interval, reported only for pairs where `hi > lo`

A pair whose interval has zero width is **degenerate** and is excluded from every
prediction below, because on such a pair the marginals already fix the joint and
there is nothing to measure. The count of degenerate pairs is reported.

## Predictions

**P1 — direction.** Across the non-degenerate hold-out pairs, the median `delta`
is strictly positive.

**P2 — magnitude.** The mean `delta` across non-degenerate hold-out pairs is at
least **+0.05**.

**P3 — position.** The median `reach` across non-degenerate hold-out pairs is at
least **0.60**, i.e. the observed joint sits in the upper two fifths of the
interval its own marginals allow.

**P4 — containment.** Every `q_obs` lies inside its own Fréchet interval. This is
arithmetic and must hold; it is stated so that a bug shows up as a failed
prediction rather than as a silent correction.

**P5 — the marginal-only quote is wrong in the unsafe direction.** For at least
**two thirds** of non-degenerate hold-out pairs, `q_obs > q_ind`. A stack quoted
from marginals under independence would understate the both-miss rate on those
pairs.

Each of P1, P2, P3 and P5 is recorded HELD or FAILED on its own. A failure of any
one of them is a result, not a reason to revisit the estimator.

## What would falsify E7's interpretation

- Median `delta` at or below zero on the hold-out (P1 fails): the correlated
  failure seen in the nine read judges does not generalise to the frontier set,
  and the exploratory finding must be reported as pool-specific.
- Mean `delta` below +0.05 (P2 fails): the effect exists but is small enough that
  independence is a serviceable approximation on this pool.
- Median `reach` below 0.60 (P3 fails): the joint is not concentrated near its
  upper bound, and the strong form of the claim — that stacking buys little —
  is not supported here.

## Forbidden rescues, declared now

- No re-calibration, re-thresholding, or change of the 5% FPR rule after any
  hold-out number is seen.
- No dropping of a frontier judge after its scores are read, except by the
  pre-stated 5%-FPR-unreachable rule.
- No substitution of the 96-item intersection, the 132-item pool, or any other
  item set for the hold-out's own shared pool.
- No restatement of a failed prediction as exploratory, and no promotion of the
  exploratory nine-judge numbers to a confirmation.
- No pooling of the read and hold-out judges into one panel and reporting the
  combined figure as the test.

## Non-claims, declared now

- Nothing here is about a deployed guardrail stack. These are research judges
  scored on a benchmark.
- The pools are small — 35 harmful items on the read pool, an unread count on the
  hold-out — so every rate is coarse and no confidence interval is implied by a
  point estimate.
- Correlated failure among these judges is not evidence about any other set of
  guards, including E2's three.
- The theorem being applied is not this repository's. arXiv:2607.22868v1 states
  the Fréchet–Hoeffding bracket for an any-flag gate as a proposition, and that
  repository's own `ensemble_robustness.py` reports that the vulnerability is
  correlated across judges. E7 measures; it does not claim priority for either
  the bound or the phenomenon.
