# Dossier — certified-agent-guardrails-2026

Census candidate: **PRESENT** by `computable_via_item_release`, pending a census pass. Status: **PREPARED, nothing sent.** This one is not an ask. It is a credit, a correction to our own novelty position, and a result handed back.

**1. What the source publishes.** Shawn Ray (Carnegie Mellon), *What Can Be Enforced? A Theory of Certified Runtime Safety for Tool-Using Agents*, arXiv:2607.22868v1, 24 July 2026. Reproducibility artifact at `github.com/shawnray-research/certified-agent-guardrails` (MIT), HEAD `79097583be7786976ea1b9ae79f3ff900d9e66b7`, 2026-07-09. Twenty-three judge score files, each a JSON map from item text to a float, over nested AgentDojo pools (96 ⊂ 132 ⊂ 167 items); `_inj_goals.json` carries the 35 injection-goal texts that label them.

**2. What this costs us, stated first.** The paper contains, as a proposition, that "for the conservative any-flag gate and fixed marginal error rates, Fréchet–Hoeffding bounds bracket the step-level miss," with the displayed bounds and the note that they hold "for every coupling," plus the attainability caveat for `m > 2` that our own E6 states independently. Its `ensemble_robustness.py` is described by the repository's README as showing "ensembling does not fix safe-washing (the max-ensemble margin stays high because the vulnerability is correlated across judges)."

So: the bound was stated independently, and the correlated-failure phenomenon was found and named, by this author, before E7B measured anything. **Nothing in this repository may claim priority for either.** A registry search for novelty language found none to retract, and E7B-001's non-claims say this in as many words. If a public sentence of ours ever implied otherwise, it is a correction, not a nuance.

**3. What the release makes possible.** Every joint statistic over these judges is computable by anyone, with no request to anyone and no model loaded. That is the rarest kind of census row: not ABSENT, not a request, but PRESENT-by-computation.

**4. What we did with it.** E7B: nine of the twenty-three judge files, unread when the preregistration was committed at `f646e136`; six reached a 5% benign false-flag budget on their shared 96-item pool (21 injection goals); fifteen non-degenerate pairs. Median excess joint miss **+0.2018**, mean **+0.1852**, median position **0.900** of the way to the Fréchet upper bound, **15 of 15** pairs above the independence product, all five preregistered predictions HELD. Seven pairs sit exactly at the bound — one judge's misses a subset of the other's. E7, the run before it, is VOID on a defective preregistration and is recorded as void.

**5. Smallest thing worth telling the author.** That their release supported an independent preregistered measurement of the bound their own proposition states, that all five predictions held, and where the numbers are. Nothing is being requested.

**6. What we could offer.** The 21-item harmful pool is small and the fifteen pairs come from six judges. The obvious extension needs what they have and we do not: the InjecAgent and AgentHarm columns, which the README says are access-gated and must be obtained from the originals. If they ever re-score on a larger shared pool, the same preregistered estimator runs unchanged.

**7. Census action.** Add as an examined row, classification PRESENT, `joint_scope: computable_via_item_release`, with the coverage stated precisely: item sets are **nested, not identical** — 15 files share 132 keys, 7 carry 167, one carries 96, and the intersection across all 23 is 96. Any joint statistic over all 23 judges must be reported on the 96-item core. A reader who quotes a 132- or 167-item denominator for a 23-judge joint is wrong, and the row must say so.

**8. Correction condition.** If the item sets turn out to be identical rather than nested, or if the scores are not per-item outcomes of separately attributable judges, the row's classification is wrong and changes with a dated entry.

**The message, verbatim:**

> Your artifact let me run a preregistered test of the bound your Proposition states, without asking anyone for anything — which is unusual enough to be worth telling you about.
>
> I took the nine judge score files I had not opened, froze the estimator and five predictions in a commit before retrieving any of them, then calibrated each judge to a 5% false-flag rate on the benign items of its own pool and computed pairwise joint miss on the 21 injection goals in the shared 96-item core. Six judges cleared the budget; fifteen pairs were non-degenerate. Median excess joint miss over the independence product was +0.20, the median pair sat 90% of the way to the Fréchet upper bound, and seven of fifteen sat exactly at it — one judge's misses a subset of the other's. All five predictions held.
>
> Two things I want on the record. The bound is yours, not mine: your Proposition states it for the any-flag gate, and `ensemble_robustness.py` had already named the correlation. And the run before this one was void — I wrote "highest threshold" where your calibration and my own earlier experiment both use the lowest, every gate flagged nothing, and the rules cost me those seven judges.
>
> Everything is at cubits11.github.io/ledger/#E7B-001 if useful. No ask attached.

**Channel.** One message, to whichever route the author offers. A GitHub issue on the artifact is the natural one. Do not open a PR unasked.
