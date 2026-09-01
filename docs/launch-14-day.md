# The 14-day launch pack

Publish-ready copy for the first distribution cycle. Every item names its
audience, its destination (campaign-tagged, built from `campaigns.yaml`), the
action it is asking for, the scope of what it claims, and the signal that says
it worked.

**Three rules that override any item here.**

1. **Scope is inherited, never widened.** The BELLS figures describe one
   author-selected 82-prompt stratum at unstated default configurations. They
   are not a claim about guardrails in general, not a vendor ranking, and not a
   population estimate. Any post that cannot fit the scope caveat is the wrong
   post.
2. **Replies beat broadcasts.** The twenty reply opportunities below are the
   highest-value items in this pack. One useful answer in a benchmark author's
   thread is worth more than any number of impressions.
3. **Nothing ships that the record cannot survive being checked on.** If a post
   states a number, the census states the same number, and the page it links to
   shows the source.

**Publishing prerequisite.** These link to `/answers/…`, `/work/`, and the
corrected flagship page. None of it exists publicly until the branch carrying
them is merged and deployed. Publishing before that sends real people to a page
that still contradicts itself.

---

## Day 0 — the pinned post

**Audience:** AI evaluation and benchmark authors
**Destination:** `https://cubits11.github.io/missing-column/?utm_source=x&utm_medium=profile&utm_campaign=missing-column-launch&utm_content=pinned`
**Visual:** `assets/img/og-missing-column.png` (the four-plus-one table)
**Action:** open the census, find your own evaluation, correct the row if it is wrong
**Claim scope:** a reporting fact about 20 examined artifacts — not a performance finding about anyone
**Success signal:** a benchmark author replies, opens an issue, or corrects a row —
`source_corrections` in `distribution/outcomes.yaml`, currently 0. Impressions are
not a success signal and are not recorded as one.

### Gate — every line must be true before this is posted

This is a checklist, not a formality. The post sends strangers to pages that
must already say what they mean.

- [ ] The branch carrying `/answers/…`, `/work/`, and the corrected flagship is
      merged and deployed. Publishing earlier sends people to a contradiction.
- [ ] `/now/` leads with E2's own state, not with the toy rehearsal, and the
      words "proven" and "validated" do not appear next to the dry run.
- [ ] `/ledger/` and `/observatory/` render study state separately from claim
      status, so "supported within scope" cannot be read as a result about
      guardrails.
- [ ] No unreleased or uncommitted study — a field test, a pilot, a local run —
      is reachable from any public page. An unactivated run is not evidence.
- [ ] `python3 scripts/verification_manifest.py` is green on the deployed commit.

### The post — long form

> Four guardrails. Four scores. One missing column.
>
> A stacked guardrail system fails when every guard misses the same item. That
> number is the one a deployment actually needs, and it is not recoverable from
> the per-guard scores that evaluations publish.
>
> I read 20 public guardrail evaluations against their primary sources. 14
> establish a shared item set and a common event definition. 5 preserve an
> artifact a joint statistic can be read or recomputed from. 0 document matched
> operating thresholds together with full exposure.
>
> The reviewer is one person: me. The inclusion wording was locked in
> repository history before any row was classified, every row binds to the
> passage it came from, and the correction route is on the page. If your
> evaluation is recorded wrong, tell me and it is logged the same day.
>
> Not a ranking, not a prevalence estimate, and not a claim that any stack is
> unsafe.

### The post — 280 characters

Use this when the long form will not fit. It carries the same ladder and the
same limit; nothing in it needs the long form as context.

> I read 20 public guardrail evaluations against primary sources.
>
> 5 preserve an artifact you can compute a joint miss rate from.
> 0 document matched thresholds with full exposure.
>
> One reviewer: me. Rows bind to sources; corrections logged same day.

Body is 247 characters. X counts a shortened link as 23 plus a separating
space, so the posted total is 271 of 280 — nine characters of margin. Re-count
before editing a word.

### Why this wording and not the earlier draft

The earlier draft said evaluations "almost never" publish the joint number.
The census says 5 of 20 preserve a usable artifact, which is 25% — "almost
never" is a stronger sentence than the file supports, and the first reader to
check would have found that. It also omitted the 14, which reads as picking the
two most favorable rungs; the full ladder is 20 / 14 / 5 / 0 and the post now
states three of them. It also omitted the single-reviewer limit, which is the
first thing a skeptic finds and the last thing that should look concealed.

**On expectations.** Rule 2 above is not decoration. An account with no audience
gets approximately no reach on a first post, and this one is not written to
travel — it is written to survive being checked by the twenty people who could
correct a row. The reply opportunities later in this pack are the mechanism; the
pinned post is the thing they land on afterwards.

---

## The eight standalone posts

Each stands alone. None requires the pinned post as context.

### 1 — the arithmetic

**Audience:** guardrail and AI-security engineers
**Destination:** `https://cubits11.github.io/answers/why-guardrail-miss-rates-do-not-multiply/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=arithmetic`
**Visual:** the interval bar — `[0%, 10%]` with a marked point at 1%
**Action:** read the interval and the worked recomputation
**Claim scope:** classical Fréchet–Hoeffding; no new mathematics claimed
**Success signal:** a practitioner says they will measure the joint row

> Two content filters, each published at a 10% miss rate on the same items.
> Stack them. What gets through both?
>
> Everyone says 1%. That's 0.10 × 0.10, and it's only right if the two fail on
> unrelated items — which nothing in the published rates tells you.
>
> What the data actually supports: somewhere in [0%, 10%]. Every value in that
> range is achievable by some real pairing of those two detectors.
>
> Independence isn't the answer. It's one point you picked.

### 2 — the recomputation

**Audience:** researchers working on safety measurement
**Destination:** same as (1)
**Visual:** the four-number strip — 82 / 73 / 9 / 3.1×
**Action:** read the scope block, then the identification claim
**Claim scope:** ONE author-selected subset, five supervisors, default configs. Say this in the post.
**Success signal:** someone checks the file themselves

> Almost no guardrail evaluation lets you check the independence assumption,
> because per-item outcomes are never released.
>
> One did. BELLS 2025 published a 170-prompt subset with per-item verdicts for
> five specialized supervisors, so the joint number is recomputable instead of
> assumed.
>
> Product of the five individual miss rates: 3.5%.
> Recomputed from the released file: 9 of 82 harmful prompts missed by all
> five. About 3.1× the plug-in.
>
> One subset, default configurations, no population estimate — that's the whole
> claim. But it's the one time it could be checked, and it was low.

### 3 — the ask

**Audience:** benchmark authors mid-writeup
**Destination:** `https://cubits11.github.io/missing-column/disclosure/?utm_source=x&utm_medium=social&utm_campaign=disclosure-adoption&utm_content=template`
**Visual:** the disclosure table, two rows highlighted
**Action:** paste the row into a results table
**Claim scope:** a proposal maintained by one person with no recorded external adoption
**Success signal:** an evaluation publishes a union or all-miss row

> If you're evaluating guardrails that will be deployed together, you're two
> numbers away from a table people can actually deploy from:
>
> — how often the union catches
> — how often everything misses the same item
>
> Same denominator, same event definition, declared operating points.
>
> If you kept one decision per item per system, that's a recomputation, not a
> new experiment. Template and a tested reference implementation here.

### 4 — the second guard

**Audience:** teams justifying a second detector
**Destination:** `https://cubits11.github.io/answers/what-does-the-second-guardrail-add/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=residual`
**Visual:** the leave-one-out strip
**Action:** measure residual coverage before buying the second detector
**Claim scope:** one stratum of one released file; not a vendor ranking
**Success signal:** a reply describing a stack where this was measured

> "Detector A catches 80%, detector B catches 70%, so together we're covered."
>
> B's 70% is measured over all items. The question you have is narrower: of the
> 20% A missed, how many does B stop?
>
> That can be anything from 0% to 100% while both headline numbers stay
> exactly as published. A detector that's excellent overall and blind to
> precisely A's blind spots looks identical on the leaderboard.

### 5 — the empty rung

**Audience:** evaluation designers
**Destination:** `https://cubits11.github.io/answers/how-to-evaluate-guardrails-you-plan-to-stack/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=arithmetic`
**Visual:** the three-rung ladder, top rung at 0
**Action:** decide the exposure condition before collecting data
**Claim scope:** a count of what 20 examined artifacts document, not a judgement of their quality
**Success signal:** someone asks how to declare exposure conditions

> "Comparable" is doing more work than it earns in most guardrail evaluations.
>
> Of the 20 I examined: 14 document a shared item set and a common event
> definition. 12 have no stated threshold mismatch. 0 document matched
> operating thresholds together with full exposure.
>
> The strongest reading is the one nobody reaches. That's not a failing grade —
> it's what the reporting currently supports.

### 6 — the correction

**Audience:** researchers and technically serious writers
**Destination:** `https://cubits11.github.io/corrections/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=reply`
**Visual:** none needed
**Action:** read how the record handles being wrong
**Claim scope:** describes this record's own process only
**Success signal:** a reply about evidence practice; a citation of the correction model

> My census said 19 evaluations examined, 4 preserving joint evidence.
>
> Then a post-release audit found a qualifying artifact my own documented
> search had missed. That met the claim's registered falsifier, so the old
> envelope was rejected — not reinterpreted, not quietly widened.
>
> It's 20 and 5 now. The 19/13/4 is still in the revision history with the date
> it stopped being true.
>
> A public claim you can't be shown wrong about isn't a result.

### 7 — the deployment caveat

**Audience:** AI-security and platform engineers
**Destination:** `https://cubits11.github.io/stack-study/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=arithmetic`
**Visual:** none needed
**Action:** run the preflight before designing the study
**Claim scope:** a statement about which arithmetic applies where
**Success signal:** someone realizes their evaluation is in a different regime than their deployment

> A thing that quietly breaks guardrail-stack numbers: your evaluation and your
> deployment aren't in the same world.
>
> Static full exposure — every system sees every item. Union and all-miss are
> well defined.
>
> Deployed sequential routing — an upstream block censors what downstream ever
> sees. Static composition arithmetic doesn't apply, and using it anyway
> flatters the stack.
>
> If your table doesn't say which one it is, a reader can't interpret it.

### 8 — the identity post

**Audience:** all five target groups
**Destination:** `https://cubits11.github.io/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=pinned`
**Visual:** the campaign object
**Action:** follow, or open the record
**Claim scope:** describes the work, claims no adoption
**Success signal:** follows from the target audiences; a reply asking about the method

> What I actually do: I measure what AI guardrail stacks miss together, and
> build evidence systems that show exactly what data can and cannot establish.
>
> Everything I publish carries a falsifier and the rescues I'm not allowed to
> make when someone comes for it. When my census was wrong, the record says so,
> with the date.

---

## Two mini-threads (only where a single post genuinely can't carry it)

### Thread A — the identification result (4 posts)

**Audience:** researchers in safety measurement and dependence
**Destination:** `https://cubits11.github.io/ledger/?utm_source=x&utm_medium=social&utm_campaign=missing-column-launch&utm_content=identification#MC-003`
**Success signal:** a substantive methodological reply, or a citation

1. Guardrail stacks are reported as if per-detector scores compose. They don't,
   and the gap is exactly measurable: for k guards at a common operating point
   under block-on-any, the all-miss rate is identified only up to
   [max(0, Σp − (k−1)), min p].
2. Both endpoints are attained. This isn't conservative padding — the upper end
   is a real world where the second guard catches nothing the first missed, and
   the lower end is a real world where their failures avoid each other.
3. What marginals *do* prove: a static OR composition is never worse than its
   best member. What they can't establish, whenever that interval is
   non-degenerate: any strictly positive benefit from adding the second guard.
4. Classical Fréchet–Hoeffding; I'm claiming no new mathematics. What's new is
   pricing, in probability units, what marginal-only guardrail reporting leaves
   undetermined — and finding that almost nobody publishes the number that
   would close it.

### Thread B — the census method (3 posts)

**Audience:** benchmark authors and curators
**Destination:** the pinned URL
**Success signal:** someone names an evaluation the search missed

1. How the census works, because "I surveyed the field" isn't a method:
   inclusion wording committed to repository history before any row was
   classified, a fixed query list, a declared snowball rule, and a stated
   budget.
2. Every row binds to a primary source with quoted passages, a fixed
   classification enum, and its own correction history. The headline is
   recomputed from the file in CI, so the marketing claim is an executable
   object.
3. It's bounded, and it says so: it covers what the documented search found,
   not everything in existence. A qualifying evaluation it missed doesn't
   embarrass the census — it rejects the current counts, which is what happened
   on 30 August.

---

## Three LinkedIn posts

### L1 — the finding, for a professional audience

**Audience:** hiring managers, assurance leads
**Destination:** `https://cubits11.github.io/missing-column/?utm_source=linkedin&utm_medium=social&utm_campaign=missing-column-launch&utm_content=launch`
**Action:** read the census
**Success signal:** an inbound conversation about evaluation or assurance work

> Most AI guardrail evaluations answer "which detector is best?".
>
> If you're deploying several together, that isn't your question. Yours is:
> what gets past all of them? And that number is almost never published — nor
> recoverable from the ones that are.
>
> I examined 20 public guardrail evaluations against primary sources. 5
> preserve an artifact from which a joint statistic can be read or recomputed.
> 0 document matched operating thresholds together with full exposure.
>
> The fix is small: union detection and all-miss rate over the same denominator
> — one row in a table you're already building. If you kept one decision per
> item per system, you already have the data.
>
> Census, method, and the disclosure template are public, and every row binds
> to its primary source.

### L2 — the correction, as a statement of practice

**Audience:** hiring managers, researchers
**Destination:** `https://cubits11.github.io/corrections/?utm_source=linkedin&utm_medium=social&utm_campaign=missing-column-launch&utm_content=launch`
**Action:** read the correction record
**Success signal:** a conversation about evidence practice

> Last week my census said 19 evaluations examined, 4 preserving joint
> evidence. It now says 20 and 5.
>
> A post-release audit found a qualifying artifact my own documented search had
> missed. I'd registered in advance what that would mean: the falsifier said
> REJECT, so the old envelope was rejected rather than reinterpreted, and it
> stays in the revision history with the date it stopped being true.
>
> I write down what would prove me wrong before I publish, and which
> face-saving moves I'm not allowed to make afterwards. It's uncomfortable
> exactly when it matters.
>
> If you're hiring for AI assurance, evaluation, or research engineering, this
> is what my work looks like when it's inconvenient.

### L3 — the offer

**Audience:** prospective collaborators and clients
**Destination:** `https://cubits11.github.io/work/?utm_source=linkedin&utm_medium=social&utm_campaign=work-with-me&utm_content=launch`
**Action:** email with a concrete artifact
**Success signal:** an email naming a results table, a claim, or a receipt format

> Three things I do, stated as deliverables rather than adjectives:
>
> **Guardrail evaluation design** — a shared-item measurement plan for union
> detection, all-miss rate, residual coverage, and exposure conditions, and a
> results table where the joint row is a first-class output.
>
> **AI claim and evidence audit** — one claim taken apart: evidence map,
> assumptions, reproduction from bound sources, an explicit falsifier, the
> rescues ruled out in advance, and a decision-facing summary.
>
> **Receipt and provenance threat model** — what an attestation actually
> identifies, which transformations leave it ambiguous, and what a verifier
> cannot conclude from a pass.
>
> None of these certify anything, and each states its own boundary in writing.
> If the evidence supports less than the claim does, the deliverable says so —
> that's the part you're paying for.

---

## Twenty reply opportunities

These are the highest-value items in the pack. **Do not mass-tag. Do not paste
the same reply twice. Do not reply where you have nothing specific to add.**
A reply that would work under any post is spam; delete it.

Rather than a list of accounts that will be stale by the time you read it, use
these as standing search-and-reply patterns. Each names the trigger, what to
say, and what makes it *not* self-promotion.

| # | Trigger you are looking for | What to add | Link? |
|---|---|---|---|
| 1 | Someone posts a new guardrail benchmark or leaderboard | Ask whether the items were shared across systems and whether a union/all-miss row is available. Nothing else. | No |
| 2 | A benchmark announces per-item data release | Say what becomes computable from it (union, all-miss, every intersection) and offer to run it | Yes — arithmetic |
| 3 | Someone multiplies two guardrail miss rates in public | Give the interval for their exact numbers. Do it as arithmetic, not correction. | Yes — arithmetic |
| 4 | "We layered two safety models for defence in depth" | Ask what the second caught among the first's misses — the residual-coverage question | Yes — second guard |
| 5 | A vendor claims a stacked-detection improvement | Ask which exposure condition it was measured under | No |
| 6 | Someone asks "how do I evaluate guardrails?" | The six-item checklist, compressed to a reply | Yes — evaluating |
| 7 | A paper reports AUPRC for a stack | Note that threshold-free metrics sidestep the operating-point question a deployed stack must answer | No |
| 8 | Discussion of prompt-injection detector ensembles | The identified-set result, stated as a bound, not a warning | Yes — arithmetic |
| 9 | Someone laments guardrail false positives | The benign-union floor: adding a guard adds burden even when it adds no exclusive coverage | Yes — second guard |
| 10 | A thread about reproducibility in AI evaluation | The per-item-outcomes ask, as the cheapest reproducibility win available | No |
| 11 | An author corrects their own benchmark in public | Say it plainly: this is the behaviour the field needs. No link. | No |
| 12 | "Is there a standard for reporting guardrail stacks?" | The MJGD, named as a proposal by one person with no adoption yet | Yes — disclosure |
| 13 | Someone building a guardrail router or cascade | Sequential routing censors downstream measurement; static arithmetic does not transfer | Yes — evaluating |
| 14 | A survey paper on LLM safety filters | Ask whether any surveyed evaluation reports a joint statistic | No |
| 15 | Agentic-safety discussion assuming composed detectors | The adaptive caveat: an intervention changes the trajectory, so there's no fixed population | No |
| 16 | Someone asks for guardrail eval datasets with item-level labels | Name the releases you know of, including ones outside your census | No |
| 17 | A hiring thread for AI safety/assurance engineering | Answer the technical question in the thread; do not pitch | No |
| 18 | Debate about whether benchmarks measure the right thing | The narrower, checkable version: they measure detectors, deployments run stacks | Yes — pinned |
| 19 | Someone publishes a leave-one-out or ablation analysis | Say what it identifies and what it doesn't (exclusive coverage, not pairwise overlap) | Yes — second guard |
| 20 | A benchmark author asks for feedback pre-release | The single highest-value comment: keep and release the per-item decisions | No |

Reply link URL, when a link is warranted:
`…?utm_source=x&utm_medium=reply&utm_campaign=missing-column-launch&utm_content=reply`

---

## Five outreach emails

Send to authors of evaluations recorded in the census. **Read the row first**;
each email must name the artifact's actual content. Send at most two per day.

**Census-row link:**
`https://cubits11.github.io/missing-column/?utm_source=email&utm_medium=outreach&utm_campaign=disclosure-adoption&utm_content=author#census`

**Disclosure template:**
`https://cubits11.github.io/missing-column/disclosure/?utm_source=email&utm_medium=outreach&utm_campaign=disclosure-adoption&utm_content=disclosure`

### E1 — to an author whose evaluation is recorded PRESENT

> Subject: your composition result is in a small group
>
> Hi [name] —
>
> I maintain a small public census of whether guardrail evaluations report what
> the declared stack misses together, not just what each detector misses. Your
> [artifact] is one of five out of twenty examined that preserves a
> joint-evidence artifact — in your case [the specific table/section].
>
> The row is here, with the passages I read it from: [link]#[row-id]. If I've
> characterized it wrong, I'd rather hear it from you than publish it; I log
> every report the same day and credit corrections in the row.
>
> Pranav

### E2 — to an author recorded ABSENT with no item release

> Subject: one row in your next results table
>
> Hi [name] —
>
> I read [artifact] carefully for a census of guardrail-stack reporting. It
> documents [the shared-item property you actually verified], which puts it
> ahead of most of what I examined.
>
> The one thing missing is what the combination misses: union detection and
> all-miss over the same items. If you kept per-item decisions, it's a
> recomputation. If item release isn't possible, leave-one-out unions are a
> compact alternative that still identifies each detector's exclusive
> contribution.
>
> Template: https://cubits11.github.io/missing-column/disclosure/?utm_source=email&utm_medium=outreach&utm_campaign=disclosure-adoption&utm_content=disclosure
> No obligation — I'd just rather ask than record
> an absence I could have helped fix.
>
> Pranav

### E3 — to an author whose row I corrected

> Subject: I corrected how I described your work
>
> Hi [name] —
>
> I recorded [artifact] in a public census and got [the specific detail] wrong.
> It's fixed, and the correction is in the public revision history with the
> date and the reason: [corrections link].
>
> The current row is [link]#[row-id]. If anything else is off, tell me and it
> gets logged the same day.
>
> Pranav

### E4 — to a researcher working on dependence or composition

> Subject: pricing what marginal-only guardrail reporting leaves open
>
> Hi [name] —
>
> Your work on [specific topic] overlaps something I've been formalizing: for k
> detectors at a common operating point under block-on-any, the all-miss rate
> is identified by the marginals only up to [max(0, Σp − (k−1)), min p], with
> both endpoints attained.
>
> The mathematics is classical — I'm claiming none of it. What I think is worth
> something is the application: pricing in probability units what
> marginal-only guardrail reporting leaves undetermined, plus leave-one-out
> unions as a privacy-preserving disclosure of exclusive coverage. Derivation
> and executable checks: [ledger MC-003 link].
>
> If the framing is wrong somewhere, I'd genuinely like to know.
>
> Pranav

### E5 — to a curator or newsletter editor

> Subject: a small, checkable result about guardrail benchmarks
>
> Hi [name] —
>
> Short version: guardrail evaluations publish a score per detector and almost
> never publish what the stack misses together — and that number can't be
> recovered from the published ones.
>
> I examined 20 public evaluations against primary sources. 5 preserve a
> joint-evidence artifact; 0 document matched thresholds with full exposure.
> Every row binds to its source, the counts are recomputed in CI, and when a
> review found an evaluation I'd missed, the old counts were rejected in public.
>
> [link] — no pitch beyond that; if it's not a fit, no reply needed.
>
> Pranav

---

## Hacker News submission

**Title:** `The Missing Column: 20 guardrail evaluations, 5 preserve joint evidence`
**URL:** `https://cubits11.github.io/missing-column/?utm_source=hn&utm_medium=forum&utm_campaign=missing-column-launch&utm_content=submission`
**Audience:** technically serious readers and curators
**Action:** read the census; challenge a classification
**Success signal:** a comment naming a qualifying evaluation the search missed

First comment, posted immediately, no marketing register:

> Author here. The method is deliberately narrow so it can be checked: a fixed
> query list, inclusion wording committed to repository history before any row
> was classified, a stated budget, and every row bound to primary-source
> passages.
>
> It's bounded and says so — it covers what the documented search found, not
> everything in existence. If you know a public guardrail evaluation published
> before 2026-08-27 that prints a union, all-miss, or composition result and
> isn't in there, that rejects the current counts rather than being a footnote.
> That already happened once, on 30 August, and the old envelope is still in
> the revision history.
>
> The empirical part is one recomputation from one released subset, and I've
> tried to keep its scope pinned down: 82 harmful prompts, five supervisors,
> default configurations, no population estimate.

---

## Community post

**Venue:** Lobsters, if its rules permit author-submitted work
**Destination:** `https://cubits11.github.io/answers/how-to-evaluate-guardrails-you-plan-to-stack/?utm_source=lobsters&utm_medium=forum&utm_campaign=missing-column-launch&utm_content=arithmetic`
**Action:** discuss the checklist; contribute a missing item
**Success signal:** a practitioner adds a condition worth putting in the page

> **Six things to decide before you evaluate guardrails you plan to stack**
>
> Not a survey — a checklist I built after examining 20 public guardrail
> evaluations against primary sources and finding that most of them can't
> answer the question a deployment actually asks.
>
> Shared items · one event definition · matched operating points · a declared
> exposure condition · the joint row · keep the per-item decisions.
>
> Five of the six cost nothing extra if you decide before you run. The write-up
> explains why each one matters and what breaks without it. If I've missed a
> condition that bit you in practice, I'd like to add it.

---

## GitHub launch note

Add to the profile README and pin the repository. Copy is in
`docs/identity.md` under *GitHub profile*.

**Repository description:**
> A public AI-assurance research record. The Missing Column Census: which
> guardrail evaluations report what the stack misses together — and which
> don't.

**Release note, if tagging one:**
> The Missing Column, v1 — 20 public guardrail evaluations examined against
> primary sources, 5 preserving a joint-evidence artifact, 0 documenting
> matched thresholds with full exposure. Counts recomputed in CI from
> census.yaml; every current factual surface bound to that arithmetic by
> scripts/verify_facts.py.

---

## Fourteen-day sequence

Cadence assumes the branch is merged and deployed on day 0.

| Day | Ship | Cost |
|---|---|---|
| 0 | Pinned post; profile copy on X, LinkedIn, GitHub; email signature | 45 min |
| 1 | Post 1 (arithmetic); 3 replies | 30 min |
| 2 | E1 outreach; 3 replies | 40 min |
| 3 | Post 2 (recomputation); 2 replies | 25 min |
| 4 | LinkedIn L1; 3 replies | 30 min |
| 5 | Post 4 (second guard); E2 outreach | 30 min |
| 6 | Rest from posting. 5 replies only. | 25 min |
| 7 | Thread A (identification); read week-1 signals into `campaigns.yaml` | 45 min |
| 8 | Post 3 (the ask); E3 + E4 outreach | 40 min |
| 9 | HN submission + first comment, morning US time; stay in the thread | 90 min |
| 10 | Post 6 (the correction); 3 replies | 30 min |
| 11 | LinkedIn L2; community post | 40 min |
| 12 | Post 5 (empty rung); E5 outreach; 3 replies | 35 min |
| 13 | Post 7 (deployment caveat); Thread B if week 1 showed method interest | 35 min |
| 14 | LinkedIn L3; record the 14-day reading in `campaigns.yaml`; decide what to repeat | 60 min |

**Day-14 review.** Write the reading into `campaigns.yaml` under `readings:`,
naming the source of every number. If a target is unmet, say so plainly. Do not
retroactively lower it, and do not claim significance from a sample this size.
