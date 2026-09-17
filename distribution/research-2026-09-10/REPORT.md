> **Status update — September 10, 2026:** The proposed dispositions below have now been recorded: [E6-001 rejected as stated](../../experiments/e6/CORRECTION-2026-09-10.md) and [E7B-001 rejected as a preregistration-conforming confirmation](../../experiments/e7b/CORRECTION-2026-09-10.md). The original campaign is superseded for launch. Use the [next constructed post](../NEXT-POST.md). Later [timestamped X observations](../analytics/README.md) are preserved separately from this report’s earlier untimed observations; none fills the missing 24-hour window.

# Show the overlap

## Recommendation

Build a recognizable practice around one question: **What does the second safeguard catch that the first misses?** Make that question easy to answer with a four-cell table, a concrete example, and a reproducible record. The opportunity is an accessible reporting practice and a useful instrument. Claiming a new discovery of correlated failure would be false positioning.

The immediate priority is scientific correction, followed by distribution to a small, relevant audience. Two central campaign claims do not survive an audit of their implementation. E6's advertised fixed-marginal range is computed with permutations that usually change marginal weights. E7B's implementation calibrates on a different pool from the preregistration. Amplifying those claims would create avoidable credibility damage. These are findings about the local analyses, not evidence that Anthropic or the upstream guardrail author made these errors.[1]

The account is at an early distribution stage: the live X profile displayed 3 followers, 25 following, and 45 posts. Three September 7 campaign roots displayed 14, 5, and 6 views at inspection on September 10. The three owner analytics panels subsequently showed 14, 5, and 7 impressions, respectively, with zero profile visits and zero detail expansions on all three. The third counter changed from the earlier profile observation; snapshots were sequential, and self-views may affect counts. These observations are too sparse to estimate a probability of going viral. They are sufficient to reject a strategy that treats a large existing audience as available.[2]

A successful next month would establish a few relevant relationships, independent uses of the method, and a measurable improvement in exposure. A breakthrough remains possible, but it should be an upside scenario rather than the operating assumption.

## What the reports actually establish

### E6: the advertised coupling range is not supported

The declared marginal approximation assigns probability masses 0.25, 0.50, and 0.25 to three values. The enumeration permutes those values while retaining weights tied to the original index. Swap the first two values and their resulting marginal probabilities become 0.50, 0.25, and 0.25. That is a different marginal distribution. Only the identity and outer-value reversal preserve these masses for a dimension. Across four independently permuted dimensions, only 16 of the 1,296 enumerated constructions preserve all declared marginals.[1]

Consequently, the reported 2.12–18.07 range is not established as a range obtained by changing dependence alone. Reproducing the same endpoints with a verifier that repeats the enumeration does not fix the problem. The verifier checks reproducibility of the computation but omits the scientific invariant that matters.

There are further interpretation problems. Quartiles do not specify full marginal distributions. Replacing a distribution by three atoms is an approximation, and arbitrary refinements need not create nested feasible sets. Therefore, the assertion that a finer discretization can only widen this range requires a proof or an explicitly nested construction. The report also says that 1.6 is contained at the lower edge of [2.12,18.07]; it is not. A finite set of attained medians does not by itself show that every real value between the minimum and maximum is attainable.

The contrast between an output at a median vector and a median of individual outputs remains a legitimate statistical teaching example. However, the recorded survey summaries use different respondent populations. Their difference cannot be attributed wholly to dependence without controlling that distinction. Likewise, a mean computed from an assumed independent synthetic distribution is not a measured mean of the actual respondents.

The current official PDF returned 57 pages, whereas the earlier narrative repeatedly described 40. This may reflect version drift or an earlier counting error; the present research does not resolve which. Absolute claims about word absence or exact artifact identity require a byte-matched version. The live paper identifies its scenarios as conditional comparisons, not probabilistic forecasts. Any future treatment should preserve that distinction.[3]

### E7B: a real implementation-to-preregistration discrepancy

The preregistration specifies the lowest admissible threshold among each judge's own benign scores, with false flags at or below 5% on that judge's own benign pool. The implementation instead computes the intersection of all nine judge pools before calibration, giving 75 benign items. Eight judge files contain 97 benign items in their own pools; one contains 75.[1]

This difference changes the Nemotron threshold from the recorded 1.00 to 0.95 under the written own-pool rule. The discrepancy is therefore consequential, not merely editorial. In addition, pair evaluation is performed on the global intersection, while the written method describes pairwise shared pools. One excluded judge with a smaller pool consequently still restricts every included pair's analysis.

Do not call the existing output a clean execution of the frozen preregistration. Preserve the old outputs, identify the deviation, and decide the formal disposition through the repository's claim-transition mechanism. A later corrected computation would need an explicit correction designation; it must not silently inherit the previous confirmatory status. No new experiment verdict is asserted here.

Even apart from that discrepancy, “all five predictions held” overstates the independent evidential content. P4 is an arithmetic containment invariant, not an empirical scientific surprise. The remaining criteria reuse the same small panel and harmful examples. Fifteen judge pairs do not constitute fifteen independent samples. Threshold exclusions are conditional on the specified candidate set; they do not establish that no conceivable threshold can meet the false-positive budget.

### Campaign-level numerical and rhetorical errors

| Current language | Problem | Replacement |
|---|---|---|
| “Rates permit anything from 5% to 48%” for 11/21 and 10/21 misses | Their sum is 1, so the lower bound is 0 | “The rates permit a both-miss rate from 0 to 10/21.” |
| “Each misses 10%… measured judges land at the ceiling, not 1%” | Conflates a constructed example with a different empirical sample | Keep the 10% example explicitly constructed; discuss empirical results separately after disposition. |
| “One judge's misses are a strict subset” whenever the upper bound is reached | Equality of miss sets also reaches the bound | Say “one miss set is contained in the other”; use “strict” only after checking unequal set sizes. |
| “The second guard catches nothing” | Depends on which guard is added to which | Report the directional incremental catch count relative to a named baseline. |
| “The most optimistic corner” for independence | Independence is generally an interior point; zero can be allowed | Say “an assumption-dependent point inside the feasible interval.” |
| “What is arithmetically wrong” about an explicitly independent example | Conditional arithmetic can be correct | Explain the consequence of relaxing the stated assumption. |
| “First published case” of a mean/median distinction | No defensible priority search supports this | Remove the priority claim. |
| “The 56-agent sweep proves novelty” | Search volume is not priority evidence | Cite the closest prior work and specify the incremental contribution. |

These are not cosmetic changes. They determine whether a technically informed reader can safely repeat the claim.

## Prior work and the actual space for originality

Dung and Mai's 2025 paper directly discusses overlapping failure modes across alignment techniques. Ray's July 2026 work and released artifact already address guardrail guarantees and correlated vulnerability. Their existence rules out broad novelty claims about discovering that multiple safeguards may fail together.[4][5]

The untrusted-monitoring safety case is a useful collaboration target, but the previous campaign undersells what it already does. Appendix B.7 explicitly discusses dependence, reports preliminary investigations, and recommends joint modeling and sensitivity analysis. The useful extension would be to implement and evaluate a concrete treatment of its specific joint events, not to announce that the authors overlooked dependence.[6]

Three levels of contribution should be kept distinct:

| Level | Defensible opportunity | Evidence needed |
|---|---|---|
| Communication | A memorable, reusable way to inspect overlap | Cold readers understand and apply it correctly. |
| Engineering | An input-to-report tool that preserves item identities, thresholds, and missingness | Independent users reproduce results on their own data. |
| Research | A method that improves decisions about adding safeguards under an explicit cost and threat model | New evaluation, strong baselines, held-out data, uncertainty treatment, and prior-work comparison. |

The proposed public phrase, “Show the overlap,” is a positioning choice, not a claim of inventing the words or owning the field. A limited exact-phrase search did not establish a dedicated guardrail movement using it, but that is not proof of uniqueness. The defensible identity would come from repeated useful work and independent adoption.

The most promising research direction is **incremental protection at a stated operating cost**. If A misses an item, how often does B catch it? How many additional benign items are blocked? What is the added latency? Does selecting a pair from one sample improve performance on another? This converts an abstract critique into a decision people already need to make. Its novelty must be assessed at the level of the proposed method and experiment, not the general question.

## Why the present X strategy stalls

The visible recent roots ask abstract questions without giving a concrete payoff. Follow-up posts expose internal distinctions such as “OBSERVED,” “DERIVED,” and “PROVED” before a reader has a reason to care. The vocabulary is useful in a methods appendix, but it asks a cold audience to decode the project before receiving value.[2]

Two roots were published about three minutes apart. That makes comparison difficult and compresses the opportunity for each post to gather attention. It does not prove that timing caused low reach. The account's small observed follower base, technical subject matter, and absence of measured audience demand are competing explanations.

Displayed reply counts also require interpretation: an author's own thread continuations are replies. They must not be counted as independent audience participation. The local ledger's recorded technical interactions and qualified outcomes have different definitions; neither can be inferred from these public counters.

The profile bio currently lists research categories. A clearer proposed version is: “I test what AI safeguards miss together. Reproducible evaluations, practical tools, and public corrections.” This explains the activity and its value in ordinary language. It is a proposed edit, not a claim that the profile has been changed.

## What research says about diffusion

Berger and Milkman's study associates sharing with factors including practical usefulness and activating emotion. It studied a different platform and period, so it does not supply an effect size for X in 2026. The relevant creative hypothesis is to combine a useful decision with surprise: let a reader see why two good-looking scores do not answer their actual question.[7]

Goel and colleagues distinguish broad broadcasting from multigenerational sharing. Their large Twitter study shows that popular content can grow through different structures, with low structural virality common. For this account, the implication is to create something a relevant researcher can readily cite or explain to their own audience. An expert amplification is a different mechanism from a slogan spontaneously spreading; the measurement should distinguish them.[8]

Centola and Macy's work on complex contagion provides a reason to distinguish seeing an idea from adopting a practice. As a strategic hypothesis, benchmark authors are more likely to add an unfamiliar reporting convention after seeing several credible peers use it. This supports depth in one technical community before breadth across unrelated audiences. The study does not prove that any specific number of contacts will make this campaign succeed.[9]

The current X algorithm repository describes personalized retrieval and ranking, including predicted viewer actions, repeated-author effects, and visibility filtering. It explicitly warns against interpreting model weights as fixed exchange rates between raw likes and reports. There is no defensible “one reply equals N likes” recipe here. Use the code to understand mechanisms, not to promise distribution.[10]

## A trend people can participate in

The recurring unit should be one problem, one overlap table, and one decision. The reader first sees two marginal miss rates, then the joint table, then the incremental protection provided by adding a second guard. Every instance names the data source, sample size, operating points, and whether the numbers are constructed or observed.

The minimal table has four counts: both miss; A misses and B catches; B misses and A catches; both catch. This is ordinary contingency-table reasoning made accessible. A “receipt” is useful only if it makes those counts inspectable; it should not become another elaborate governance document.

A practical recurring format:

1. **Predict:** “Two systems each miss 10 of 100 cases. How many do both miss?”
2. **Reveal:** Show two constructed worlds with the same separate scores: disjoint miss sets and identical miss sets.
3. **Decide:** Ask what evidence is needed before paying for the second system.
4. **Reuse:** Offer a four-cell template a benchmark author can fill with existing data.

The social payoff is competence: someone sharing the example helps colleagues avoid a decision error. The practice can spread without agreeing with a sweeping criticism of AI safety. Do not use fake controversy, manufactured supporters, mass tagging, or promises that engagement will unlock hidden information.

Three recurring editorial tracks are enough. “Show the overlap” teaches one decision. “What changed my conclusion” documents a substantive correction. “One more useful column” demonstrates a concrete reporting improvement from a public dataset. Keep economics as an occasional adjacent example after E6 is repaired; it should not dilute the guardrail identity.

## Audience and distribution choices

| Audience | Their immediate question | Useful artifact | Desired action |
|---|---|---|---|
| Guardrail engineers | Does another guard add protection worth its cost? | Four-cell counts plus incremental catches and false blocks | Run on their data. |
| Benchmark maintainers | Can a small reporting change make the release more useful? | Minimal schema/example based on their release | Add a joint table or preserve item IDs. |
| AI-control researchers | How does dependence alter this safety argument? | Analysis tied to their actual compound events | Technical review or replication. |
| Technical educators | Can I explain this clearly? | A correct constructed example with reusable caption | Teach or cite it. |
| General AI readers | Why do two scores fail to answer the question? | Short visual puzzle with immediate explanation | Understand, save, or follow. |

Relevant researchers are potential collaborators, not a list of accounts to tag. Ray's artifact is the first credit reference for its own data. Dung and Mai are intellectual prior work. The untrusted-monitoring authors are a candidate technical audience for a specific extension. This report does not assert that any of them will respond or endorse the project.

Use X as the discovery layer; use the repository as the evidence layer. One post should contain one useful idea without requiring a click. A source link then rewards deeper interest. An interactive tool is worth promoting when it correctly enforces its invariants and someone unfamiliar with the project can use it without assistance.

## Thirty-day execution

### Days 1–3: repair and establish an honest baseline

Record the E6 marginal-invariance failure and E7B pool mismatch alongside their original artifacts. Mark the previous campaign as superseded for launch purposes. Prepare formal claim dispositions rather than quietly changing frozen estimators. Retrieve the available X analytics and preserve observation times; do not backdate them into missing 24-hour windows.

Use a simple constructed example for the next educational post. It can teach the central idea without depending on either disputed headline. Have the evidence destination explain current correction status before directing readers to old empirical claims.

### Days 4–10: learn which entry point gets understood

Publish three primary educational units across the week, spaced to allow observation. This cadence is a proposed workload, not an algorithmic optimum. Compare a concrete puzzle, a practical engineering question, and a plain-language explanation. Keep the underlying constructed example and call to action comparable. Capture the audience's actual misunderstandings rather than assuming silence means agreement.

Contribute a small number of substantive responses in relevant conversations when there is something specific to add. The test is whether the response is useful even without a link to this project. Do not count self-replies or acknowledgments as technical demand.

### Days 11–20: demonstrate use by someone else

Offer the four-cell reporting template to people who have already shown interest. Seek one independently produced table or reproduction. Record whether the person completed it without assistance, what failed, and whether the result changed a decision. This is stronger evidence of a useful practice than another internally generated instrument.

If the correction work is complete, publish a single compact account of the original mistake, the failed invariant, and the new disposition. Avoid presenting willingness to correct as proof that every other claim is reliable. Make corrections findable without turning the account into a stream about its own process.

### Days 21–30: repeat the useful unit and choose the next experiment

Repeat the best-understood format on a second suitable source only if the evidence is sound. Present a before-and-after reporting example. Publish the month's measured outcomes, including zeros and unavailable fields. If no independent use occurs, interview the interested readers about workflow cost before building more features.

The next research experiment should be chosen for decision value: a paired evaluation at explicit false-block and latency budgets, with independent calibration and test pools. Do not commission a large speculative campaign before this can be measured.

## Traction scenarios and decision metrics

The observed three-root view counts have a median of 6 and a range of 5–14. A mechanical extrapolation of that range across 12 future roots gives 60–168 displayed views. This is a scale reference only: post age differs, observations are sparse, and future content can behave differently. Views are not unique people; X says author views and repeat views can count.[2][11]

For planning, define an absolute attention breakout as at least 10,000 impressions on one root within seven days. Define a research breakout separately as at least three independently evidenced reproductions or uses within thirty days. These thresholds are managerial choices, not learned statistical boundaries. A post crossing ten times this tiny account baseline would not on its own establish meaningful traction.

| Conditional scenario for 12 roots | Assumed average impressions/root | Total impressions | Assumed click rate | Implied clicks | Assumed completion per click | Implied completed actions |
|---|---:|---:|---:|---:|---:|---:|
| Minimal discovery | 10 | 120 | 0.5% | 0.6 | 5% | 0.03 |
| Relevant audience reached | 250 | 3,000 | 1.0% | 30 | 5% | 1.5 |
| Repeated expert amplification | 2,500 | 30,000 | 1.5% | 450 | 3% | 13.5 |

Every rate and exposure level in this table is an explicit assumption, not an industry benchmark or calibrated forecast. Fractional outcomes are expected-count arithmetic, not people already observed. A completed action still needs external evidence before qualifying as a research outcome. The attached CSV preserves the inputs and arithmetic.

The funnel is impressions × click rate × completion rate. At a 1% click rate and 5% completion rate, one expected completion requires 2,000 impressions. This arithmetic explains why asking a handful of viewers to run a complex reproduction is a weak acquisition strategy. Improve qualified discovery and reduce completion friction before scaling output volume.

Do not assign probabilities to these scenarios yet. The account has too little history, and a single amplification can dominate outcomes. After a larger set of comparable posts, report empirical distributions, exposure windows, and uncertainty. Followers can be tracked as net account change, but should not be called post-attributed follows without a direct attribution source.

### Measurement definitions

| Metric | Unit and source | Interpretation |
|---|---|---|
| Impressions | Root post, provider, cumulative observation time | Exposure; not unique people. |
| Profile visits / impressions | Same post and window | Interest in the author; undefined with missing denominator. |
| Link clicks / impressions | Directly observed platform field | Interest in the destination; not completed research. |
| Detail expansions | Platform count where available | Diagnostic of opening the post. |
| Substantive replies | Unique external participants, reviewed for technical content | Conversation quality; excludes own continuations. |
| Independent uses | Evidence-backed completed reproductions or reporting changes | Primary adoption outcome. |
| Corrections resolved | Publicly traceable issue and disposition | Scientific maintenance; not audience growth. |

Capture 24-, 72-, and 168-hour snapshots using the repository's existing windows where available. Preserve cumulative observations rather than summing them. The present observations must be labeled at their real capture time and assessed against those windows. Do not sum all posts in a thread as unique reach.

If exposure stays near the present baseline across six well-spaced, comprehensible roots, treat distribution as the unresolved problem. If exposure improves but profile visits and meaningful replies do not, revise the entry point. If clicks arrive but no one completes the action, reduce workflow cost. These are diagnostic branches rather than causal conclusions.

## What to build next

The highest-value instrument is a tiny overlap report that accepts already paired binary outcomes and produces the four counts, denominators, marginal rates, both-miss rate, and directional incremental catch rate. It should reject duplicate item IDs, make missing data explicit, and show whether the evaluation and calibration sets overlap. Those functions address failures discovered in this audit.

A more ambitious successor could compare candidate stacks under cost constraints, but selecting a stack and evaluating it on the same cases would bias the result. The holdout design matters more than a larger interface. A new scientific contribution would come from demonstrated decision improvement under a stated sampling process.

The current campaign should not be escalated with paid reach. Its observed numbers are not enough to estimate demand, and its two featured research claims need disposition. The path to a distinctive audience is a repeated useful question, accessible evidence, and demonstrated outside use.

## Sources

1. Local primary artifacts inspected September 10, 2026: `experiments/e6/RESULT.md`, `experiments/e6/freeze/sources.json`, `scripts/verify_e6.py`, `experiments/e7b/PREREG.md`, `experiments/e7b/run/measure.py`, frozen E7B score files, `distribution/CAMPAIGN-2026-09-10.md`, and cited distribution dossiers. The accompanying `audit-results.json` pins key inputs by SHA-256; `audit.py` reproduces the structural findings without rewriting experiment outputs.
2. Pranav Bhave, [X profile](https://x.com/PranavBhave_), inspected September 10, 2026, approximately 14:00 UTC. Owner analytics inspected for [TRY-A](https://x.com/PranavBhave_/status/2097018101602660408/analytics), [TRY-B](https://x.com/PranavBhave_/status/2097092670556373187/analytics), and [TRY-C](https://x.com/PranavBhave_/status/2097093498054840551/analytics). Private analytics require the account session. Counts are time-specific. Local publications and dashboard ledgers supply recorded publication dates, not a complete account history.
3. Korinek, Jones, Sacher, Cotter, and McCrory. [Economic Scenarios for Transformative AI](https://www-cdn.anthropic.com/files/4zrzovbb/website/cf58f84d46a4a76bf5a5b039ac695fba6b80041c.pdf). Anthropic Institute Working Paper 2026-02, September 2026. Current PDF inspected; historical hash equivalence was not established. [Scenario explorer](https://www.anthropic.com/institute/econ-scenarios).
4. Leonard Dung and Florian Mai. [AI Alignment Strategies from a Risk Perspective: Independent Safety Mechanisms or Shared Failures?](https://arxiv.org/abs/2510.11235). October 13, 2025.
5. Shawn Ray. [What Can Be Enforced? A Theory of Certified Runtime Safety for Tool-Using Agents](https://arxiv.org/abs/2607.22868). July 24, 2026. [Primary code and data repository](https://github.com/shawnray-research/certified-agent-guardrails); README explicitly describes correlated vulnerability.
6. [When can we trust untrusted monitoring? A safety case sketch across collusion strategies](https://arxiv.org/html/2602.20628v1). 2026. Appendix B.7, “Handling Dependence of Scores.” This report uses the primary paper rather than treating the campaign's LessWrong paraphrase as the full account.
7. Jonah Berger and Katherine L. Milkman. [What Makes Online Content Viral?](https://cssh.northeastern.edu/pandemic-teaching-initiative/wp-content/uploads/sites/43/2020/09/What-Makes-Online-Content-Viral.pdf). Journal of Marketing Research 49(2), 2012, pp. 192–205. Original paper hosted by Northeastern University.
8. Sharad Goel, Ashton Anderson, Jake Hofman, and Duncan J. Watts. [The Structural Virality of Online Diffusion](https://pubsonline.informs.org/doi/10.1287/mnsc.2015.2158). Published online July 22, 2015; Management Science 62(1), 2016, pp. 180–196.
9. Damon Centola and Michael Macy. [Complex Contagions and the Weakness of Long Ties](https://ndg.asc.upenn.edu/wp-content/uploads/2016/04/Centola-Macy-2007-AJS.pdf). American Journal of Sociology 113(3), 2007. Original paper hosted by the University of Pennsylvania.
10. xAI. [X algorithm repository](https://github.com/xai-org/x-algorithm). Live documentation inspected September 10, 2026, including August/September 2026 updates and warnings about interpreting predicted-action weights.
11. X Help. [View counts](https://help.x.com/en/using-x/view-counts). Live documentation inspected September 10, 2026.
12. X Developer Platform. [Get Posts Analytics](https://docs.x.com/x-api/posts/get-post-analytics). Live documentation inspected September 10, 2026. Endpoint availability does not establish this account's API access; no complete posting credentials were present in the task environment. The connected Metricool brand returned no connected networks; authenticated browser access was available.
