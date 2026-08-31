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

---

# CORRECTION (2026-08-31) — the marginal this rests on is reported twice, differently

The independent adjudication found that this artifact publishes the LLM Guard
marginal in two places that disagree, at the same pinned commit:

- `README.md` table → recall 46.31% (TP 94, 109 misses of 203 positives)
- committed `llm_guard_threshold_metrics.png` at the same 0.034 threshold →
  recall ≈ 40.2% (TP 82, 121 misses)

The plot is stale output from a superseded commit. Protocol v1 says nothing
about which figure is *the* marginal, so the choice was mine, and it is
load-bearing:

| | README reading | PNG reading |
|---|---|---|
| both-miss count | [11, 105] | [23, 105] |
| both-miss rate | [5.42%, 51.72%] | [11.33%, 51.72%] |
| union recall | [48.28%, 94.58%] | [48.28%, 88.67%] |
| requirement ≤ 5% | DETERMINED: FAIL | DETERMINED: FAIL |
| **requirement ≤ 10%** | **UNDETERMINED** | **DETERMINED: FAIL** |
| requirement ≤ 20% | UNDETERMINED | UNDETERMINED |
| requirement ≤ 55% | DETERMINED: PASS | DETERMINED: PASS |

**The two readings give different decisions at a 10% requirement.** The
original table above used the README reading throughout and did not disclose
that a defensible alternative reading existed. That was an overstatement of
precision, and the table should be read with this correction attached.

The substantive conclusion is unchanged and is arguably strengthened: over the
10–40% band where operational requirements usually sit, the published evidence
remains compatible with both accepting and rejecting the stack under either
reading. But the exact boundary at which the decision becomes determined is
itself not identified by the artifact — the ambiguity compounds rather than
cancelling.

Also unrecorded in the original analysis, and material: every published marginal
here is really the marginal of "detector OR (crash → allow)", because
`main.py:73-76` and `main.py:88-91` catch all exceptions and record a non-
detection. The crash rate is never reported, so the true detector-only marginals
are bounded above by the published ones and the interval above is, if anything,
optimistic.

The denominator (N=546, 203 positives) is not published by the artifact at all.
It was recovered from a baseline annotation inside the committed PNGs plus
integrality against the four-significant-figure ratios. Without that recovery
none of these bounds would be computable, and the reconstruction class
`PARTIALLY_IDENTIFIED` would be assignable but empty.
