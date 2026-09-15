> **Launch update — 2026-09-10:** Use [NEXT-POST.md](../NEXT-POST.md) as the current prepared launch. This earlier pack remains background material. E6-001 and E7B-001 now have formal rejection dispositions beside their original artifacts.

# X launch material

Prepared September 10, 2026. These are proposed posts, not scheduled or published. This pack supersedes the previous campaign's E6/E7B promotional copy. Neither disputed experiment is used as a confirmed headline. Review the accompanying audit before linking readers to their existing registry pages.

## Profile

Proposed bio: I test what AI safeguards miss together. Reproducible evaluations, practical tools, and public corrections.

Proposed pinned post, after the evidence destination carries the correction status:

> Two safeguards can look good separately and still fail on the same cases.
>
> I study what the second one actually adds: extra catches, extra false alarms, and the evidence behind the claim.
>
> Start with one question: what do they miss together?

## Lead post

> Two AI safeguards each miss 10 of 100 cases.
>
> If they miss different cases, the pair misses none.
> If they miss the same cases, the pair still misses 10.
>
> Same separate scores. Different protection.
>
> Ask for the overlap.
>
> Constructed example, not a benchmark result.

Optional source reply, same thread:

> This is a standard probability bound, not a new theorem. Dung and Mai discuss shared failure modes across AI alignment techniques: https://arxiv.org/abs/2510.11235
>
> The practical question is which extra cases a second safeguard catches.

## Follow-up: the decision

> Before adding a second AI safeguard, ask:
>
> What does it catch that the first misses?
> How many extra benign requests does it block?
> What latency does it add?
>
> A better individual score does not answer those three questions.

## Follow-up: the missing evidence

> “Both systems catch 90%” leaves a decision unanswered.
>
> Are they catching the same cases?
>
> Report four counts: both catch, only A catches, only B catches, neither catches.
>
> Then we can see what the pair adds.

## Follow-up: the assumption

> If two safeguards each miss 10%, independence gives a 1% joint miss rate.
>
> But the separate rates alone allow anything from 0% to 10%.
>
> The multiplication is correct under its assumption. The next question is whether the failures support that assumption.

## Follow-up: the contribution

> The question is not how many safeguards a system has.
>
> It is how much additional protection each one provides on the cases the others miss.
>
> Show the overlap, the operating thresholds, and the sample size. Then discuss the stack.

## Follow-up: adoption invitation

> If you already have paired pass/fail results for two safeguards, you have the ingredients for an overlap table.
>
> Count: both fail, only A fails, only B fails, neither fails.
>
> Which of those four cells changes your decision about adding B?

## Correction post — use only with a public correction record

> I found two problems in my analyses: a permutation routine changed the marginal weights it was meant to preserve, and a calibration pool differed from my preregistration.
>
> The original outputs are retained. The affected claims need correction before promotion.

A reply should link the actual public audit URL after it exists. Do not insert a guessed destination or describe a local file as published. This post is not an admission of an upstream author's error.

## Cadence

Three primary posts per week is a workload proposal. It is not a claim about an ideal X frequency. Space roots across different days; reserve intervening time for reading and useful technical replies. Observe real analytics at the existing 24-, 72-, and 168-hour windows. Do not compare different-aged totals as if they had equal exposure time.

Week 1: lead constructed example; decision questions; four-cell explanation.
Week 2: assumption explanation; a visual rendering of the same constructed table after comprehension review; answer one actual reader question if one exists.
Week 3: correction record when public; independently completed overlap example if obtained; incremental protection explanation.
Week 4: repeat the best-understood format on a verified example; report actual use and friction; publish the month's measured findings.

Conditional slots stay empty if the necessary evidence or reader question does not exist. No fictional interactions, quotations, or endorsement posts.

## Visual specification

Use two side-by-side 100-case grids with identical 10-case marginal miss counts. In the left example, A and B miss disjoint sets and joint misses are zero. In the right example, they miss the same ten cases and joint misses are ten. Label each panel “constructed.” Use symbols as well as color. Put the overlap count beside the grid, not in a distant caption.

The visual has one teaching objective: the reader can explain why the two separate scores do not determine joint performance. The existing film's cold-viewer requirement still applies to that film; this specification is not a completed or tested visual.
