# E6 — the width of the missing column, measured on a published economic model

Run 2026-09-10. Not preregistered; see the note below before reading any number
here as a prediction that held.

## What I did

The Anthropic Institute published *Economic Scenarios for Transformative AI*
(Working Paper 2026-02, September 2026) and, alongside it, an interactive
scenario explorer at `anthropic.com/institute/econ-scenarios`. The model maps a
five-vector of beliefs about AI — capability `m₂₀₃₀`, adoption `d₂₀₃₀`, autonomy
`ψ`, productivity gain `a₂₀₃₀`, re-employment speed `μ` — to a 2030 economy.

The explorer computes in the browser, so the model is in the page. I extracted
the kernel from the shipped bundle (Turbopack module `303412`, sha256
`0a75763f…`), gated it against the twelve numbers printed in Table 3 of the
report, and then evaluated it only at parameter vectors built from the five
marginal quantiles printed in Table 2. Nothing in the kernel is patched: the
factory's own source is re-instantiated with an appended closure-scoped `eval`
probe, so the arithmetic that runs is the arithmetic the site ships.

Two gates ran before any figure below was recorded:

- **Table 3 agreement.** The extracted kernel reproduces all twelve printed
  numbers of Table 3 — GDP, total unemployment, cognitive unemployment and the
  labour share, in each of the modest, substantial and extreme scenarios — to
  the one decimal the report prints. `1.61 / 8.29 / 32.41` against the printed
  `1.6 / 8.3 / 32.4`, and so on for the other nine.
- **Monotonicity.** GDP is strictly increasing in each of the five parameters
  over their published interquartile ranges. This is what licenses reading a
  comonotone quantile off a quantile vector; without it no comonotone figure
  would be reported.

Every other parameter is held at the substantial scenario's value, which is
what the note to Table 4 says its own simulations do: `ρ = 0.25`,
`θ_H = 0.25`, `ξ = 0.5`, `ε = 3`.

## The primary result

These carry no discretionary choice. Every input is a numeral printed in the
report; the hold-outs are the ones Table 4's note names.

| quantity | value |
|---|---|
| GDP % above the no-AI path at the **vector of Table 2 medians** | **9.88** |
| unemployment at that same vector | **4.89** |
| GDP median across the 3,259 per-respondent runs (**Table 4**) | **8.6** |
| unemployment, same (Table 4) | **4.6** |
| GDP interquartile range under **comonotone** coupling of the same marginals | **[1.01, 40.12]** |
| GDP interquartile range of the **measured joint** (Table 4) | **[3, 19]** |

The vector of medians and the median of outcomes are different objects, and the
report is the authority on that. Its Appendix B says so in its own words: the
Table 2 medians are taken "item by item, so no single respondent need give all
five median answers," while Table 4 "run[s] the model on each respondent's five
values" and requires "all five answers from the same person," which is why it
uses 3,259 of the 10,980 people surveyed. The marginals and the joint are
computed on different populations, and the joint costs 70% of the sample.

The words *joint*, *correlation* and *copula* do not appear in the report. The
distinction survives in Appendix B and is gone by the abstract, which reports
"the median respondent's answers" — a respondent who, by Appendix B, need not
exist. The introduction states the procedure as "running the simulations using
their median answers as inputs to the model," which is not the procedure the
note to Table 4 describes.

## One set of marginals, three couplings

Replacing each marginal with three atoms at its published quartiles — weights
0.25, 0.50, 0.25 — gives 243 cells, all committed. This discretisation is a
choice I made with the outcomes already visible, and it is declared as such in
`freeze/sources.json`. It makes the range below an **inner** bound: a finer
discretisation of the same marginals can only widen it.

| coupling of the five marginals | median 2030 GDP, % above no-AI |
|---|---|
| comonotone — perfect rank agreement | **9.88** |
| independent | **8.32** |
| the joint Anthropic actually measured | **8.6** |
| range over all 1,296 rank-permutation couplings | **[2.12, 18.07]** |
| support over the 243 cells | **[1.01, 40.12]** |

The five published marginals admit a median answer anywhere across
**[2.12, 18.07]**. That interval contains the modest scenario's 1.6 at its
lower edge, the substantial scenario's 8.3 in its middle, and reaches more than
halfway to the extreme scenario's 32.4. The marginals do not determine the
answer. Anthropic measured the coupling and got 8.6.

The thing worth naming is which corner the obvious summary sits in. Pushing the
vector of medians through the model is not an independence assumption. Because
GDP is monotone in all five parameters, it is the **comonotone** answer — the
one you get if every respondent who is bullish on capability is equally bullish
on adoption, autonomy, productivity and re-employment. It is the
most-correlated-possible respondent, not the typical one. Here it sits 1.28
points of GDP above the measured joint, and 1.57 above independence.

## The sentence I cannot resolve

The site says:

> The typical respondent's answers imply outcomes close to the "substantial
> change" scenario: GDP is 10% higher by 2030 than it would be without AI, and
> the overall unemployment rate has risen to around 5%.

Neither figure is the pair Table 4 prints (8.6 and 4.6). Two different summaries
of the same survey do land there, and I cannot tell from the public record which
one the sentence means:

- the vector of published medians pushed through the model — **9.88** GDP,
  **4.89** unemployment; or
- a mean rather than a median across respondents — under the independent
  coupling of these marginals, **10.01** GDP and **4.93** unemployment.

Both round to "10%" and "around 5%". They are statements about different things:
one is a synthetic respondent at the comonotone corner, the other is an average
outcome over a right-skewed distribution. **I am not claiming the site composed
its marginals.** I am recording that its headline figure's estimand is not
identified from the artifact, and that the two candidates differ in kind.

## The ask

One number, on one row.

> Print the model's output at the Table 2 median vector
> (`m₂₀₃₀ = 0.44`, `d₂₀₃₀ = 0.40`, `ψ = 0.47`, `a₂₀₃₀ = 0.44`, `μ = 0.064`,
> hold-outs at the substantial values) next to Table 4's 8.6, and say which of
> the two the site's "10%" is.

If they match, that is worth stating. If they differ, the introduction's
sentence needs one word changed. Either way the reader learns that the two are
different objects, which is the whole of what E6 is about.

The larger ask is the microdata: releasing the 3,259 five-vectors would let
anyone compute the coupling term directly instead of bounding it. Anthropic
already paid for the joint. Almost nobody in guardrail evaluation has.

## What this does not license

- **This is not a preregistered test and no prediction here held.** The
  artifacts were public before this directory existed. E6 is a re-derivation,
  not an experiment.
- **No error in the report is claimed.** Table 4 does the joint-preserving
  computation, and does it correctly. The two gates confirm the kernel agrees
  with the report wherever both speak.
- **Nothing here is about a guardrail.** It is the same identification structure
  as this repository's guardrail claims — marginals fix an interval, not a point
  — measured on a different object. It transfers no number to any safety
  classifier, pool or operating point.
- **The coupling range is an inner bound under a declared discretisation**, not
  a sharp Fréchet bound. In five dimensions the comonotone corner is attainable
  but the lower envelope is not a copula, so the sharp lower bound is a
  Makarov–Rüschendorf optimisation I have not solved. The claim is that the
  interval is wide, not that these are its endpoints.
- **The kernel URL is ephemeral.** It is a build-hashed asset path and will
  change on the next deploy. The digest identifies the bytes; a third party
  reproducing this after a redeploy must obtain the pinned bytes from an archive
  or re-pin and record that it is a different kernel.
- **These 243 rows are not measurements of a guardrail on an item.** They are
  evaluations of someone else's model at published parameter vectors. The
  evidence ledger counts them as rows this repository produced, which they are;
  its single observation-row total must not be read as growth in guard-item
  measurement. E3 and E3B's 4,800 rows are that kind. These are not.
- **No claim about anyone's intent, competence or good faith.** The reviewers
  named in the report include Acemoglu, Autor and Romer. If this distinction can
  go unnamed there, the vocabulary is missing, not the care.

## Reproduce

```bash
node experiments/e6/run/measure.js     # needs the pinned kernel bytes; exits 2 without them
python3 scripts/verify_e6.py           # re-derives every number above from the committed rows
```

`verify_e6.py` touches no network and never re-runs the model. It reads the 243
committed rows and recomputes all 34 registered quantities from them.
