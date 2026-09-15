> **Formal correction — September 10, 2026: SUPERSEDED FOR LAUNCH.** E6-001 and E7B-001 are rejected as stated. See the dated [E6 marginal-invariance disposition](../../experiments/e6/CORRECTION-2026-09-10.md) and [E7B pool-mismatch disposition](../../experiments/e7b/CORRECTION-2026-09-10.md). Original text below is retained as history, not current launch copy. Use the [constructed educational post](../NEXT-POST.md) for the replacement direction.

# Dossier — anthropic-econ-scenarios-2026

Not a census row: this is an economic scenario model, not a guardrail evaluation. It sits in `distribution/` because the ask is the same shape as the guardrail asks — one number, one row — and because E6 is bound to it. Status: **PREPARED, nothing sent.**

**1. What the source publishes.** Korinek, Jones, Sacher, Cotter & McCrory, *Economic Scenarios for Transformative AI*, Anthropic Institute Working Paper 2026-02, September 2026, plus an interactive explorer at `anthropic.com/institute/econ-scenarios` whose model runs client-side. Table 2 gives five per-item marginal quantiles from 10,980 US adults surveyed by Morning Consult, 11–23 August 2026. Table 3 gives three named scenarios' 2030 outcomes. Table 4 gives the outcome quantiles across the 3,259 respondents who answered all five items.

**2. What is already done right, and should be said first.** Table 4 is the joint-preserving computation: each respondent's own five-vector run through the model, then quantiles taken of the *outcomes*. Appendix B states the distinction in the authors' own words — the Table 2 medians are taken "item by item, so no single respondent need give all five median answers," while Table 4 requires "all five answers from the same person." Keeping the joint cost 70% of the sample. Almost nobody in guardrail evaluation pays that price. The shipped bundle also pins its own model kernel by commit, which is better provenance discipline than most published models ship.

**3. What remains unidentified.** One sentence, on the public site: "GDP is 10% higher by 2030 … and the overall unemployment rate has risen to around 5%." Table 4 prints 8.6 and 4.6. Two other summaries of the same survey do land on 10 and 5 — the vector of Table 2 medians pushed through the shipped kernel (**9.88** and **4.89**, measured in E6), and a mean rather than a median across respondents (**10.01** and **4.93** under the independent coupling of those marginals). The public record does not say which the sentence means. One is a synthetic respondent at the most-correlated corner; the other is an average over a right-skewed distribution.

**4. Smallest missing artifact.** One table row: the model's output at the Table 2 median vector, printed beside Table 4's 8.6.

**5. Smallest action the authors can perform.** Evaluate their own model once at `m₂₀₃₀ = 0.44`, `d₂₀₃₀ = 0.40`, `ψ = 0.47`, `a₂₀₃₀ = 0.44`, `μ = 0.064`, hold-outs at the substantial scenario's values, and state which of the two summaries the site's 10% is. If the numbers agree, saying so is the whole fix.

**6. Can we do 90%+ of the work?** It is already done. E6 evaluated it: **9.88** GDP, **4.89** unemployment, from the kernel the site ships, gated on reproducing all twelve printed Table 3 numbers to the printed decimal first. `experiments/e6/run/measure.js` and `scripts/verify_e6.py` are in this repository, and the 243 evaluated cells are committed. What we cannot do is say which summary the sentence names — only they can.

**7. Success condition.** A public artifact stating the output-of-medians beside the median-of-outcomes, or naming the estimand behind the site's 10%. A microdata release of the 3,259 five-vectors would be a larger success: it turns the coupling term from bounded into measured, and would make theirs the first published instrument where the width of the missing column is known rather than bracketed.

**8. Correction condition.** If a public artifact already states the output at the Table 2 median vector, or names the site figure's estimand, E6's unresolved-sentence finding is wrong and `experiments/e6/RESULT.md` must be corrected with a dated entry, crediting the source.

**The ask, verbatim:**

> Table 4 does the expensive thing: each respondent's own five answers through the model, quantiles taken of the outcomes. Appendix B says exactly why that differs from Table 2's item-by-item medians — "no single respondent need give all five median answers" — and it cost 70% of the sample to do.
>
> One number would close the loop. What does the model give at the Table 2 median vector (m = 0.44, d = 0.40, ψ = 0.47, a = 0.44, μ = 0.064, hold-outs at the substantial values)? I get 9.88% GDP and 4.89% unemployment from the kernel the explorer ships, after checking it reproduces all twelve printed numbers of Table 3. Table 4 prints 8.6 and 4.6, and the site says 10% and around 5% — which I can also reach as a mean across respondents (10.01, 4.93). I can't tell from the public record which of those the site's sentence is, and the two mean different things.
>
> Printing the output-of-medians beside the median-of-outcomes would settle it in one row. And if the 3,259 five-vectors were ever releasable, the gap between the two would become measurable rather than bounded — which as far as I can find would be the first published case of that.

**Channel.** One message. No thread, no tag, no public post first. The paper names a contact route; use theirs, not a mention.

**What must not be sent.** Any claim that they composed marginals, that the report contains an error, or that Table 4 is wrong. It is not, and E6 says so in its non-claims. The ask is a disambiguation request, and it is addressed to people who already documented the distinction better than the guardrail field has.
