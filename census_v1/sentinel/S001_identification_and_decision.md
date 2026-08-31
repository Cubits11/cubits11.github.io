# S001 — from disclosure to identification to decision relevance

One worked instance on the sentinel. Not a framework, not a page, not a brand.
It exists to test whether the third object in the spine is real and computable
from an artifact classified under the protocol.

## Input — only what the artifact publishes

| detector | recall on injections | miss rate |
|---|---|---|
| LLM Guard | 0.4631 | 0.5369 |
| Pytector | 0.4828 | 0.5172 |

No overlap, no per-item verdicts, no combined result (L3, L4, L6 all absent).

## Identification — what those marginals admit

For the OR-stack, "the stack misses" means both detectors miss the same item.
Sharp Frechet-Hoeffding limits from the marginals alone:

    lower = max(0, m1 + m2 - 1) = 5.41%     (maximum complementarity)
    upper = min(m1, m2)         = 51.72%    (maximum redundancy)

    admissible interval: [5.41%, 51.72%]   — 46.31 points wide
    independence would give 27.77%          — one point inside it, not implied

The independence point is what a reader multiplying the two miss rates would
report. The published evidence does not license it, and the interval it sits in
spans nearly half the scale.

## Decision relevance — does the gap change an actual decision?

| requirement | verdict from published evidence |
|---|---|
| stack all-miss ≤ 5% | **DETERMINED: FAIL** — the whole interval violates it |
| stack all-miss ≤ 10% | **UNDETERMINED** — compatible with PASS and FAIL |
| stack all-miss ≤ 20% | **UNDETERMINED** — compatible with PASS and FAIL |
| stack all-miss ≤ 40% | **UNDETERMINED** — compatible with PASS and FAIL |
| stack all-miss ≤ 55% | **DETERMINED: PASS** — the whole interval satisfies it |

Both directions are real, and saying so is the point:

- At a **5%** requirement the missing column changes nothing. The marginals
  alone already settle it, and settle it as a failure. Reporting the joint would
  not have altered the decision.
- At **10–40%** — the range most operational requirements actually fall in —
  the published evidence is compatible with both accepting and rejecting the
  stack. There the omission is decision-relevant, not merely untidy.

## What this instance does not establish

One artifact, chosen adversarially under a pre-registered rule but still one.
The interval is wide here partly because both detectors have low recall; a pair
of strong detectors would produce a narrower interval and more determined
decisions. Nothing here says how often the interval straddles a requirement
across the population — that is what a prospective pilot would measure, and it
is not measured yet.

The quantity bounded is the OR-composition all-miss rate. Per the protocol's L6
caveat, an OR union is one composition and not automatically the behaviour of a
deployed system.
