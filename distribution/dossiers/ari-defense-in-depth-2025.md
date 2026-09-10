# Dossier — ari-defense-in-depth-2025

Not a census row: an advocacy explainer, not a guardrail evaluation. Status: **PREPARED, nothing sent.** Read the fairness section before drafting anything.

**1. What the source publishes.** Americans for Responsible Innovation, *Securing AI Through Defense in Depth: The Challenge of Jailbreaks*, by Ben Hayum, 30 July 2025. A policymaker-facing explainer on layered jailbreak defences. It contains, verbatim:

> "If each layer has a 90% success rate at blocking an attack, chaining five of them together (assuming independence) reduces the chance of a successful breach to just 0.001%."

**2. What is arithmetically wrong with it.** Five events each of probability 0.10 have an intersection bounded by Fréchet–Hoeffding at `[max(0, Σpᵢ − 4), min pᵢ] = [0, 0.10]`. The quoted `0.00001` is the independence point. The upper bound is **10,000× larger**, and the two published rates do not distinguish them. E7B measures a case where real judges land at the top of exactly this kind of interval: two guardrail judges each missing ~50% of injection goals, independence predicting a 24.9% both-miss rate, the measured rate 47.6% — the ceiling.

**3. Fairness, before any draft.** All three of these must survive into the message or it is unfair:
- The parenthetical **"(assuming independence)" is theirs.** They flagged the assumption. The criticism is that the assumption carries four orders of magnitude and is never revisited, not that it was hidden.
- The piece **also hedges** elsewhere, noting that "sophisticated adversaries will continue to search for and occasionally find pathways through layered defenses."
- The sentence is a **hypothetical illustration**, not a measured claim about any system, and the article's own list of layers is **six heterogeneous mechanisms**, of which three are not per-item gates at all. So "five layers on a shared item pool" is our reconstruction, not their stated setup. Do not attribute a measured joint statistic to them.

**4. What remains unidentified.** Nothing about their data — they present none. What is missing is the interval beside the point: a reader is given `0.001%` and no indication that the same marginals permit `10%`.

**5. Smallest missing artifact.** One clause. "…reduces the chance of a successful breach to just 0.001% *if the layers fail independently; if their failures coincide, the same per-layer rates permit up to 10%, and measured guardrail failures tend toward the coincident end.*"

**6. Smallest action they can perform.** Add that clause, or replace the number with the interval.

**7. Success condition.** The published piece carries the bound alongside the point, or is amended to state the interval. Credited, with a dated entry.

**8. Correction condition.** If the piece already carries such a clause elsewhere and we missed it, the ask is void and nothing is sent.

**The ask, verbatim:**

> Your defense-in-depth explainer flags its own assumption, which is more than most do — "(assuming independence)" is right there in the sentence. I want to suggest that the parenthetical is carrying more weight than it can.
>
> Five layers each blocking 90% bound the all-five-miss probability, by Fréchet–Hoeffding, to somewhere in [0%, 10%]. Independence picks 0.001%. The upper end is ten thousand times larger, and the five published rates do not distinguish between them — the difference is entirely in whether the layers fail on the same inputs.
>
> That is not hypothetical. On published per-item scores from a July 2026 CMU artifact, two guardrail judges each missing about half of prompt-injection goals both missed 47.6% of them, where independence predicts 24.9%. Fifteen pairs, all above the independence product, most near the ceiling. Working: cubits11.github.io/ledger/#E7B-001.
>
> One clause would fix it: "…to just 0.001% if the layers fail independently; if their failures coincide, the same per-layer rates permit up to 10%." A policy audience acting on the 0.001% is being handed the most optimistic corner of an interval as though it were the answer.

**Channel.** One message to the author or the publication's stated contact. **Not a public quote-post.** The verified reading of this piece is "a careful advocacy writer flagged the assumption and then relied on it", not "a policy shop got arithmetic wrong", and a public thread would make the second claim whatever the words say. If it goes anywhere public, it goes as the general pattern with this as one cited instance among several, never as the headline target.
