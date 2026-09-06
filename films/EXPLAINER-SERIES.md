# The Explainer Series — ten episodes

**STATUS: DRAFT SCRIPTS. Nothing recorded, nothing uploaded, nothing scheduled.**
Written 2026-09-05 on branch `claude/mc-005-selection-regret`. This file
registers no claim, edits no registry, changes no generated page, and starts no
campaign. Every numeral below carries a locator; two are flagged as
**UNVERIFIED** and are barred from recording until checked.

## The trade, stated before writing

The evidence ledger's standing rule says name the trade before adding another
document. Here it is.

This deck does not produce an observation row, does not clear K1, and does not
move the one action the queue says is next — five to eight cold viewers running
the frozen Same Scores comprehension trial (`distribution/QUEUE.md` item 5).

I am writing it anyway for one reason, and it is not "the channel needs
content." The repository already contains a competent explanation of its own
work and consistently buries it at position fifteen. `WEAKEST_SENTENCE_THAT_SURVIVES`
is good teaching; it sits below a line nobody outside this frame can parse. The
failure is ordering, not content. Ten scripts is the cheapest way to force the
ordering to change, because a script has a first second and you cannot bury
anything in it.

The counterweight is real and it is in the reading that prompted this: fluency
is a confidence bug. Deslauriers et al. (2019, PNAS) found students rated
fluent lectures higher while learning less from them — *cited from memory; verify
before any of this is published.* The risk of getting good at explaining this
program is that a bounded counting exercise starts sounding like a result. Every
episode below therefore carries a **fluency guard**: a scripted moment where the
explanation is made to feel less finished than it just felt.

**Scope of this deck:** it is a production artifact for one person. It is not a
teaching practice running alongside the approved work. It runs *through* it —
Episode 1 is the rehearsal for the cold-viewer trial that is already the next
human action, and Episode 10 ends on that same action. If this file grows a
second file, it has become the disease it was written to cure.

---

## The pedagogy, in four sentences

1. **Teaching is an identifiability problem.** The learner's state is latent.
   Their questions are the only observable, and it is a narrow channel. Bad
   explanation is high-bandwidth emission into a channel you never read.
2. **So ask before you emit.** One well-chosen diagnostic question partitions
   the learner's state and saves three paragraphs. Formative assessment; the
   mapping to partial identification is exact, which is the only reason it is
   worth saying in this repository's vocabulary at all.
3. **Constraint before result.** People retain the shape of a problem better
   than its answer. Every episode states what is *not* determined before it
   states what is.
4. **Retrieval, not review.** A fact you pull out of your own head sticks; a
   fact you watch someone repeat does not. The architecture below is built to
   make the viewer pull.

## Vocabulary bar

No term invented inside this repository may appear before 0:60 of any episode.
Barred from every cold open: *identified set, marginal, joint, estimand,
partial identification, falsifier, envelope, ladder, workload, composition,
supervisor, operating point, stratum, non-claim.*

Permitted substitutes: **the two scores** (marginals), **how often they miss the
same thing** (the joint), **the range the scores still allow** (the identified
set), **what I wrote down in advance that would prove me wrong** (the falsifier),
**the sentence I'm still allowed to say** (the weakest surviving claim).

Falsifier for the bar: hand a cut to someone who cannot reproduce the result and
ask them to restate the limit. If they answer in this repository's words rather
than their own, the cold open failed. Mine, not theirs.

---

## Retrieval architecture

Four devices, in every episode.

| Device | Where | Rule |
|---|---|---|
| **Cold recall** | 0:00–0:12, from Ep 2 on | A question about an episode **at least two back**, never the previous one. Interleaved, not blocked. Answer given at the end, not immediately. |
| **Prediction hold** | before every reveal | State the choice, then **three seconds of actual silence**. No music bed under the hold. The hold is the lesson; do not fill it. |
| **The wrong answer on purpose** | once per episode | Say the plausible wrong answer in your own voice, let it stand unmarked for a beat, then show what it assumed. Never label it "wrong" before showing it. |
| **Exit ticket** | last 15 seconds | One question. Answer is checkable at a named URL, not in the pinned comment. The pinned comment holds the question, not the answer. |

### Interleaving schedule — each core fact retrieved three times at growing gaps

| Fact | Taught | Retrieved at | Gap pattern |
|---|---|---|---|
| F1 · Two separate scores do not fix how often both miss | Ep 1 | 3, 6, 9 | 2 / 3 / 3 |
| F2 · Only 8 of 32 possible miss-patterns actually occur | Ep 2 | 4, 10 | 2 / 6 |
| F3 · A column of zeros is a verdict, not a gap | Ep 3 | 5, 7, 8 | 2 / 4 / 1 |
| F4 · Remove-one is what identifies who is carrying the stack | Ep 4 | 7, 9 | 3 / 2 |
| F5 · Every pair can agree while the three-way answer changes | Ep 5 | 8, 10 | 3 / 2 |
| F6 · A rule written before the count has to be allowed to fire | Ep 6 | 9, 10 | 3 / 1 |
| F7 · Measuring the thing changed the arithmetic and changed no decision | Ep 7 | 10 | 3 |
| F8 · Which population a rate was computed on is recoverable, and usually unstated | Ep 8 | 10 | 2 |
| F9 · What a result does not license is part of the result | Ep 9 | 10 | 1 |

Episode 10 is the mass-retrieval capstone: it pulls F1–F9 in one pass and
answers none of them for the viewer.

---

## Pre-flight — must pass before any episode is recorded

```bash
python3 scripts/verification_manifest.py
python3 scripts/films/bind_facts.py --check
```

Both must exit 0. Additionally, three per-episode blocks:

| # | Blocker | Affects | State on 2026-09-05 |
|---|---|---|---|
| B1 | `exclusive_cells` is an **uncommitted working-tree addition** to MC-002. The 32-pattern table has no committed registry binding yet. | **Ep 2, Ep 4** | Open. I recomputed all 8 occupied patterns independently from the hash-verified released file and they agree exactly; the *fact* is solid, the *binding* is not. Commit and regenerate before filming. |
| B2 | MC-002 records the BELLS file's licence as `none declared upstream`; MC-005 at HEAD records `license: MIT` for the same file. `ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md` confirms the upstream repository declares no licence. | **Ep 7** | Open, and it is a registry inconsistency, not a filming detail. Do not record Ep 7 until one of the two records changes. |
| B3 | The all-miss category split (Ep 2) and the LLM Guard file-B count (Ep 8) are computed in-session, not registered. | **Ep 2, Ep 8** | Ep 2's split is reproducible from the released file today. Ep 8's requires a count on upstream file `d6ebd0e5` that **has not been taken** — marked UNVERIFIED in place. |
| B4 | `scripts/verification_manifest.py` **does not exit 0 on this working tree.** The claim-history kernel reports `entries[38] differs from the prior accepted revision — accepted history is append-only`, from the uncommitted `claims_history.yaml` change that accompanies B1. | **all ten** | Open as of 2026-09-05. This is the owner's in-progress edit, not something this deck touched, but the pre-flight rule is unconditional: nothing is recorded while the manifest fails. An accepted transition being rewritten rather than appended is also the exact shape the registry treats as serious — resolve it as a registry question first, not as a filming blocker. |

Every numeral spoken on camera must resolve from `films/data/facts.json`, from
`claims.yaml`, or from a command shown running on screen. If a spoken number
disagrees with the render, redo the take. No exceptions, including for a number
you are certain about.

---
# EPISODE 1 · THE COIN THAT LANDS TWICE

**Public title:** *You Can't Multiply Safety*
**Runtime:** 4:30 · **Form:** owner camera + two physical coins + bound whiteboard insert
**Teaches F1** · **Bound to:** CC-001, CC-004
**Doubles as:** the rehearsal script for the cold-viewer comprehension trial
(`distribution/QUEUE.md` item 5). If a cold viewer cannot restate this episode's
limit, the trial has told you something before you have spent a cent.

### Rejected conceits, and why

- *Two locks on a door.* Killed: locks compose in series, which imports the
  sequential-filtering confound this program spends a whole scope paragraph
  excluding. The wrong physical metaphor teaches the wrong estimand.
- *Swiss cheese slices.* Killed: it is the standard safety metaphor and it
  already assumes the answer — the holes are drawn independent. Using it would
  be arguing for my conclusion with a picture that presupposes it.
- *Two doctors reading the same X-ray.* Kept in reserve for Ep 5. Too strong
  here; it makes the correlation obvious, and the whole point of Ep 1 is that
  the correlation is invisible in the scores.

### Cold open · 0:00–0:14

> I'm going to give you two true facts and you're going to give me a confident
> wrong answer. It won't be your fault. The arithmetic that produces it is the
> arithmetic everybody does.

Hand enters frame, sets down two coins. No greeting, no channel logo, no name.

### Constraint before result · 0:14–0:50

> Here are two filters. Each one lets ten percent of bad stuff through. That's
> all you know. Not which ten percent. Not whether they're the same ten percent.
> Just: ten and ten.
>
> Question, and I want you to actually answer it before I do.
> **How often does something get past both?**

**PREDICTION HOLD — 3 seconds of real silence. No music.**

### The wrong answer on purpose · 0:50–1:20

Say it flat, in your own voice, with no irony:

> One percent. Ten percent of ten percent. One in a hundred.

Let it sit for a beat, unmarked. Then:

> That's what I said too. Here's what I didn't notice I'd assumed.

Whiteboard insert resolves `0.10 × 0.10 = 0.01`. **The amber assumption label
stays visible for the entire product shot.** Do not stage the product as a
result and disclaim it afterwards.

### The mechanism · 1:20–2:40

Two coins, hands, table. No graphics.

> Line the misses up. Everything the first one lets through, the second one
> catches. How often do both miss? **Zero.**
>
> Now stack them. Everything the first one lets through, the second one also
> lets through. How often do both miss? **Ten percent.** The whole ten.
>
> Check the two scores in both cases. Ten and ten. Ten and ten. **Nothing on
> either scorecard moved.**

Beat. Then the sentence the whole series rests on:

> So the true answer is somewhere between zero and ten percent, and the two
> scores do not tell you where. One percent is one point in that range. It's the
> point you land on if the two filters fail for completely unrelated reasons.
> Maybe they do. The scores don't say.

### The hidden step I nearly didn't notice · 2:40–3:20

The "just" hunt, on camera, about my own reasoning:

> I said "each one lets ten percent through" as if that were one simple fact.
> It's two. It's a rate, **and** it's a population — the same set of inputs, both
> filters seeing all of it. Change that and I'm answering a different question.
> If the second filter only ever sees what the first one passed, its ten percent
> means something else entirely, and none of what I just showed you applies.

### Weakest sentence that survives · 3:20–3:35

Spoken verbatim, no cut in the middle of it, looking into the lens:

> **Two separate miss rates do not tell you how often both filters miss the same
> thing. They tell you it's somewhere in a range, and the range can be wide.**

### Non-claims, said out loud · 3:35–4:00

> This is an illustration with made-up numbers. It is not a measurement of any
> product. It does not say any stack is bad, and it does not say stacking
> doesn't help — stacking never makes things worse. It says the improvement is
> not pinned down by the two numbers you were given.

### Fluency guard · 4:00–4:15

> That felt clean. I want to flag that: it felt clean because I chose two numbers
> that make the arithmetic pretty. On real files it is messier, and in three
> episodes I'll show you one where my own answer came out boring.

### Exit ticket · 4:15–4:30

> If both filters miss ten percent, and I tell you they *never* miss the same
> item — what's the biggest fraction that gets through the pair? Answer's at
> cubits11.github.io/try — build it yourself and watch the pile move.

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| each miss rate | 0.10 | `claims.yaml` CC-001 `expected.marginals` |
| both-miss range | [0.0, 0.10] | CC-001 `expected.bounds.and`; CC-004 `expected.interval` |
| either-miss range | [0.10, 0.20] | CC-001 `expected.bounds.or` |
| the point independence picks | 0.01 | `films/data/facts.json` → `CC-001.independence_and`, kind DERIVED, noted "an assumption-world, not an estimate" |

**Answer to the exit ticket:** 0. And the range's other end is 0.10. Both ends
have explicit witness distributions that sum to one and satisfy both marginals
— CC-004, checked to 1e-9 from a clean clone.

---

# EPISODE 2 · THIRTY-TWO DOORS

**Public title:** *I Checked Every Way Five AI Filters Can Fail. Only 8 Happen.*
**Runtime:** 5:00 · **Form:** physical 32-cell grid + terminal capture
**Teaches F2** · **Cold-recall: Ep 1** *(exception to the two-back rule — Ep 2 has
only one predecessor; from Ep 3 the rule binds)* · **Bound to:** MC-002
**BLOCKED BY B1 and B3.**

### Rejected conceits, and why

- *A leaderboard.* Killed on sight. A leaderboard is the exact object this
  series exists to complicate. Rendering one, even to knock it down, gives the
  viewer the frame to keep.
- *Venn diagram, five circles.* Killed: five-set Venn diagrams are unreadable
  and I'd spend ninety seconds teaching the diagram instead of the finding.
- *Binary counter ticking 00000 → 11111.* Killed: it's beautiful and it teaches
  binary, not this. The grid is worse-looking and better.

### Cold recall · 0:00–0:12

> Last time: two filters, ten percent each. What's the range for how often both
> miss? Hold your answer. I'll say it at the end.

### Constraint before result · 0:12–1:10

Physical wall: 32 pigeonholes, all shut.

> Five filters, one item. Each one either catches it or misses it. Catch, miss,
> catch, catch, miss — that's a pattern. **Thirty-two patterns exist.** Two to
> the fifth.
>
> Now here's a real file. Eighty-two prompts somebody labelled harmful, and five
> published safety filters' actual yes-or-no answers on every one of them. Not a
> simulation. A file you can download.
>
> **How many of the thirty-two patterns do you think show up?**

**PREDICTION HOLD — 3 seconds.**

### The wrong answer on purpose · 1:10–1:35

> I'd have guessed twenty-something. Five filters, eighty-two chances, plenty of
> room for variety.

Beat. Then open the doors. Eight open. Twenty-four stay shut.

> Eight.

### The reveal · 1:35–3:00

Terminal capture, real command, real output — never a typed mock-up:

```bash
python3 scripts/reanalyze_bells_subset.py
```

The eight occupied patterns, read left to right as Lakera Guard, Prompt Guard,
LangKit, NeMo, LLM Guard, where **1 means missed**:

| pattern | items | in words |
|---|---|---|
| `01101` | 26 | only Lakera and NeMo caught it |
| `01001` | 18 | only Lakera, LangKit and NeMo caught it |
| `11101` | 18 | only NeMo caught it |
| `11111` | **9** | **nobody caught it** |
| `00001` | 4 | all four that can fire, fired |
| `01111` | 3 | only Lakera caught it |
| `11001` | 3 | only LangKit and NeMo caught it |
| `00101` | 1 | Lakera, Prompt Guard and NeMo caught it |

> Twenty-four of the thirty-two patterns never happen once. Not rare. Zero.
>
> And look at the right-hand column. **Every single occupied pattern ends in a
> one.** One of these five filters has a 1 in every row of this file. That's
> episode three, and I'm not going to explain it yet.

### The hidden step · 3:00–3:35

> I said "eight patterns" like that's a fact about five filters. It isn't. It's a
> fact about five filters **on these eighty-two items** — items somebody else
> selected, by a rule they never wrote down. A different eighty-two could open
> more doors. The structure I just showed you is real and it is local.

### Weakest sentence that survives · 3:35–3:50

> **On this released file, the five filters' failures are not scattered across
> the possibilities — eight of thirty-two patterns hold everything, and nine
> items got past all five.**

### Non-claims · 3:50–4:20

> Nine out of eighty-two is not any product's error rate. These are one
> benchmark's released verdicts at whatever settings its authors used, in early
> 2025, on prompts they chose by a rule that isn't published. It is a count. It
> is not a safety rating, it is not current behaviour, and it is not a
> population.

### Fluency guard · 4:20–4:35

> The grid makes this look like a finished result. Here is what is unfinished:
> I do not know the rule that picked these eighty-two items out of a pool of a
> thousand and change. Nobody outside that project does. Episode eight is me
> failing to find it.

### Exit ticket · 4:35–5:00

> Nine items beat all five filters. If I told you which six harm categories
> those nine came from — would that tell you anything useful, or would it be
> noise? Have an opinion and keep it. I show you the split, and my answer, in
> **two** episodes.
>
> And last episode's answer: **zero to ten percent.**

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| items in file / harmful / benign / borderline | 170 / 82 / 50 / 38 | MC-002 `expected` |
| per-filter catches | Lakera 52 · Prompt Guard 5 · LangKit 25 · NeMo 70 · LLM Guard 0 | MC-002 `expected.per_guard_catches` |
| union / all-miss | 73 / 9 (11.0%) | MC-002 `expected.union_detection`, `all_miss` |
| product of miss rates | 3.5% | MC-002 proposition |
| ratio, recomputed to product | ≈3.1× | MC-002 proposition |
| the eight patterns | as tabled | MC-002 `expected.exclusive_cells` — **UNCOMMITTED (B1)**. Independently recomputed from the hash-verified file this session; the eight counts sum to 82 and each filter's row-sum equals `82 − catches`. |

---

# EPISODE 3 · THE SMOKE DETECTOR THAT NEVER BEEPED

**Public title:** *One of These Safety Filters Fired Zero Times. That's Data.*
**Runtime:** 4:15 · **Form:** owner camera + one prop + screen capture
**Teaches F3 · Retrieves F1** · **Bound to:** MC-002, MC-004

### Rejected conceits, and why

- *Naming and shaming the vendor.* Killed hard. The number is a released column
  from early 2025 at unstated settings. Turning it into a product verdict is
  exactly the inflation this program exists to prevent, and it would be the one
  clip that travels. Refuse it in the script so the temptation is settled before
  the edit.
- *"The guard that was asleep."* Killed: personification smuggles in intent.
- *A zero on a scoreboard.* Killed: too abstract, and it reads as a score, which
  is the frame being dismantled.

### Cold recall · 0:00–0:12 *(two back — Ep 1)*

> Two filters, ten percent each, and I tell you they always miss the *same*
> things. How often does something get past both? Hold it.

### Constraint before result · 0:12–1:00

A smoke detector on the table. Green light. Silent.

> This has been on the wall for a year. It has never gone off. Two stories fit
> that, and you cannot tell them apart from the ceiling:
>
> There was no fire. Or it doesn't work.
>
> **Which one do you need to know, and what would settle it?**

**PREDICTION HOLD — 3 seconds.**

### The finding · 1:00–2:10

> Eighty-two prompts labelled harmful. Five filters. Here's what each one caught.

Read them in order, on screen, one at a time — NeMo seventy, Lakera fifty-two,
LangKit twenty-five, Prompt Guard five, and then hold:

> LLM Guard. **Zero.** Out of eighty-two.
>
> And here's the thing I want you to sit with. **That is not a missing number.**
> A missing number is a blank. This is a column full of actual recorded answers,
> and every one of them is no.

Cut to the second file — Multimodal Safeguard Bench, three different guards:

> Same shape, different reason, and the difference is the whole lesson.
> ShieldGemma 2 also returns zero on all two hundred harmful text items. But
> that source **documents** it: that guard is image-only, so on text it passes by
> design. Its zero is a specification. The other zero is just a zero.
>
> One of those you can reason with. The other one you have to go ask about.

### The wrong answer on purpose · 2:10–2:40

> So drop the useless one. Five filters, one contributes nothing, run four.

Beat.

> That is a decision about a **deployment**, made from a **file**. I don't have
> the settings it ran at. I don't have a version number. I have one column from
> one snapshot in early 2025. Removing something from a live system on that
> basis is not evidence-led; it's evidence-shaped.

### The hidden step · 2:40–3:10

> Watch what I did without saying so: I compared five filters as if they were
> five answers to one question. In the second file they aren't even that — one
> guard reads images, one reads text and images, one reads only images. Putting
> their bits in a row is something *I* did. The source didn't do it for me, and
> it's the step most likely to be wrong.

### Weakest sentence that survives · 3:10–3:25

> **A recorded zero is an outcome, not a gap — but it only tells you what the
> filter did on those items at those settings, and unless the source says why,
> you cannot tell a broken detector from a quiet room.**

### Non-claims · 3:25–3:50

> No vendor is being rated here. No product is being called ineffective. I have
> counted a column in a public file and reported what it says, including the
> parts that embarrass my own story.

### Fluency guard · 3:50–4:00

> I have now given you two zeros and a clean distinction between them. The clean
> distinction is mine, not the sources'. Neither file uses it.

### Exit ticket · 4:00–4:15

> Next one is a game. Five filters catch seventy-three of eighty-two together.
> **Pull one out.** Pick which, and guess what the seventy-three becomes. Write
> the number down before you watch.
>
> Episode one's answer: **ten percent.** All of it. Same scores, worst case.

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| LLM Guard catches | 0 / 82 | MC-002 `expected.per_guard_catches.llm_guard` |
| ShieldGemma 2, harmful text | 0 / 200 | `films/data/facts.json` → `MC-004.harmful_text.per_guard.shield_gemma_2`; documented deterministic pass, MC-004 scope |
| LLM Guard, benign | 0 / 50 | MC-002 `expected.per_guard_benign_flags.llm_guard` |
| measurement dating | January–February 2025 | upstream FAQ, quoted in `ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md` |

---
# EPISODE 4 · PULL ONE OUT

**Public title:** *Which AI Guardrail Is Actually Doing the Work?*
**Runtime:** 5:00 · **Form:** physical five-block tower + terminal capture
**Teaches F4 · Retrieves F2** · **Bound to:** MC-002, MC-003
**BLOCKED BY B1** (the pattern table is the same uncommitted block).

### Rejected conceits, and why

- *Jenga.* Killed, reluctantly. Jenga's lesson is "everything is load-bearing
  eventually," which is the opposite of the finding. Using it would fight the
  result for the viewer's memory and probably win.
- *Firing people from a team.* Killed: invites a performance-review reading of
  numbers that are not performance measures.
- *Five columns of a spreadsheet, deleted one at a time.* Kept, but as the
  **terminal** half only. The physical half needs an object whose removal is
  visibly reversible — five wooden blocks in a row, lifted out and put back —
  because the point is that most removals change nothing.

### Cold recall · 0:00–0:14 *(two back — Ep 2, and it pays the debt)*

> Two episodes ago I asked which harm categories the nine all-miss items came
> from. Here they are: **Economic harm 2, Expert advice 2, Government
> decision-making 2, Privacy 1, Malware/Hacking 1, Fraud/Deception 1.**
>
> The tempting read is that Expert advice is the dangerous one — two of its four
> harmful items beat everything. **Four items.** I would not act on that and
> neither should you. I'm showing you the split because I promised it, and
> because "here is the number that doesn't support my story" is the habit.

### Constraint before result · 0:14–1:15

Five blocks in a row. A card on each. No labels visible yet.

> Five filters. Together they catch seventy-three of eighty-two. That's the only
> number you have.
>
> I'm going to lift one block out and run it again with the remaining four.
> **Before I do: how much do you think seventy-three drops?**
>
> Careful — the two scores can't tell you. You know each filter's individual
> catch count. That is not the same as knowing what it adds. Something that
> catches fifty-two items might add nothing at all, if every one of those
> fifty-two is also caught by somebody else.

**PREDICTION HOLD — 3 seconds.**

### The reveal, one block at a time · 1:15–2:45

Lift, run, replace. Real terminal each time. Never accelerate the counter.

| Remove | 73 becomes | Exclusive contribution |
|---|---|---|
| Prompt Guard | 73 | **0** |
| LangKit | 73 | **0** |
| LLM Guard | 73 | **0** |
| Lakera Guard | 70 | 3 |
| NeMo | 55 | **18** |

> Three of the five can be removed and the file's coverage does not move by a
> single item. Lakera — which catches fifty-two on its own — is worth **three**.
> NeMo is worth eighteen.
>
> Now compare that to the catch counts from two episodes ago. **Lakera fifty-two,
> LangKit twenty-five, Prompt Guard five.** The ranking by "how much do you
> catch" and the ranking by "what would we lose without you" are not the same
> ranking, and only one of them is in the published table.

### The wrong answer on purpose · 2:45–3:15

> So the answer is: run NeMo and Lakera, drop the other three, and you keep
> seventy-three catches with sixty percent of the cost.

Beat.

> On this file, at these settings, on these eighty-two items, that arithmetic is
> correct. As a procurement decision it's unsupported, and here's the specific
> reason, not a general disclaimer: the three I just dropped contribute zero
> **on the eighty-two harmful items**. They also flag benign traffic — LangKit
> eight of fifty, Prompt Guard zero, LLM Guard zero. I have shown you one side
> of a two-sided decision and then made the decision.

### The hidden step · 3:15–3:45

> The word to catch me on is "adds." I computed what each filter adds **last** —
> as the final member of a fixed set of five. Ask a different question, like what
> each one adds first, or on average over every order, and you get different
> numbers, and those numbers are not identified by what I have. Remove-one is a
> real quantity with a narrow meaning. It is not importance.

### Weakest sentence that survives · 3:45–4:05

> **On this file, removing any of three filters changes the group's coverage by
> zero items; removing one changes it by eighteen. How much a filter catches on
> its own does not tell you how much the group loses without it.**

### Non-claims · 4:05–4:30

> Nothing here says three of these filters are worthless. They cover different
> things, they were built for different threats, and this is one harm stratum of
> one author-selected subset. It says that on this file, at these settings,
> their catches were already covered by somebody else.

### Fluency guard · 4:30–4:45

> Remove-one is my favourite result in this whole program, which is exactly why
> I want to say the following out loud: it is a *disclosure* idea, not a
> discovery. Anybody with per-item outcomes can compute it in four lines. The
> interesting fact is that almost nobody publishes the data that lets you.

### Exit ticket · 4:45–5:00

> Five filters. You know each one's catch count and you know the union is
> seventy-three. **Can you work out the remove-one numbers from just those?**
> Yes or no, and why. cubits11.github.io/missing-column/

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| leave-one-out unions | 70 / 73 / 73 / 55 / 73 | MC-002 `expected.leave_one_out_union` |
| realized exclusive coverage | NeMo 18 · Lakera 3 · other three 0 | MC-003 proposition; `MC-003.members_zero_exclusive_full_stack_coverage` = 3 |
| bounds from marginals alone | NeMo [0,21] · Lakera [0,3] · LangKit [0,3] · Prompt Guard [0,3] · LLM Guard [0,0] | `films/data/facts.json` → `MC-003.aggregate_unique_contribution_bounds`, kind PROVED |
| benign flags | Lakera 7 · Prompt Guard 0 · LangKit 8 · NeMo 10 · LLM Guard 0, union 19/50 | MC-002 `expected` |
| all-miss category split | Economic harm 2 · Expert advice 2 · Government decision-making 2 · Privacy 1 · Malware/Hacking 1 · Fraud/Deception 1 | **computed in-session from the hash-verified released file, not registered (B3).** Reproduce before filming. |

**Answer to the exit ticket:** No — and this is the sharpest thing in the
series. Catch counts plus the union bound each filter's exclusive contribution
but do not fix it. LLM Guard's bound is the one exception, `[0,0]`, and it is
degenerate for a reason you already know from Episode 3. Everyone else's bound
is an interval and the realized value sits inside it. The remove-one numbers
are **extra evidence**, not arithmetic.

---

# EPISODE 5 · THE SHADOW PUZZLE

**Public title:** *Check Every Pair and You Still Miss It*
**Runtime:** 4:30 · **Form:** built object + light + the existing Parity Cube film
**Teaches F5 · Retrieves F3** · **Bound to:** CC-003

### Rejected conceits, and why

- *Three coins.* Killed: the construction is right but nothing is visible. The
  whole value here is that a viewer can *see* two different objects throwing
  identical pairs of shadows.
- *Rock-paper-scissors / non-transitive dice.* Killed: adjacent famous puzzle,
  different theorem. Viewers who know it will pattern-match and stop listening.
- *A love triangle.* Killed on contact. The mathematics is exact and the
  metaphor is not, and this program's entire credibility is that it doesn't do
  that.

### Cold recall · 0:00–0:12 *(two back — Ep 3)*

> A filter's column is all zeros. What's the one question that decides whether
> that's useful information? Hold it.

### Constraint before result · 0:12–1:10

Two objects, three walls, one light.

> Three filters this time. I'm going to tell you everything about them **in
> pairs.** How often filter one and two miss together. One and three. Two and
> three. Every pair, exactly measured, no uncertainty.
>
> **Now: how often do all three miss together?**
>
> This one has a real answer and it is not "you need more data." You have all
> the pairs. That's a lot.

**PREDICTION HOLD — 3 seconds.**

### The wrong answer on purpose · 1:10–1:35

> Pairs are most of the way there. Three filters, three pairs, and the three-way
> answer has to be somewhere close to what the pairs imply.

Beat. Bring up the second object.

> Two different objects. Same three shadows, pair by pair. **Different solid.**

### The construction · 1:35–2:50

Run the existing Parity Cube master at normal speed, once.

> Eight possible outcomes for three filters. Put equal weight on the four with an
> even number of misses. Then put equal weight on the four with an odd number.
>
> Both worlds: each filter misses **half** the time. Both worlds: any two miss
> together **a quarter** of the time. Every single-filter number matches. Every
> pair number matches.
>
> All three together: **zero** in one world. **A quarter** in the other.
>
> Not close. Not within error bars. Zero versus twenty-five percent, from
> identical pairwise measurements.

### The hidden step · 2:50–3:20

> Here is where I have to stop myself. I built these two worlds. I didn't find
> them. Nothing here says real filters look like either one, or that the gap is
> ever this wide in practice. What it establishes is that **no amount of pairwise
> measurement closes the question** — which is a statement about what evidence
> can do, not about how bad things are.
>
> A possibility proof is a real thing to have. It is also the cheapest kind, and
> I'd rather say that than let it feel like a finding.

### Weakest sentence that survives · 3:20–3:35

> **Measuring every pair of filters does not determine what three of them do
> together. Two constructions with identical singles and identical pairs differ
> in the three-way answer by twenty-five percentage points.**

### Non-claims · 3:35–4:00

> These are constructed distributions, not measurements of any system. This is a
> possibility proof: it shows a gap can exist, not that it does exist anywhere in
> particular, and not how large it typically is.

### Fluency guard · 4:00–4:15

> Parity is a beautiful trick and beautiful tricks are load-bearing in the wrong
> direction. This is the most elegant thing in the series and the least
> empirical. Rank it accordingly.

### Exit ticket · 4:15–4:30

> Two filters, every pair measured — which is just the one pair. Is the two-way
> answer pinned down? Think about why that's a different question. Build it:
> cubits11.github.io/try/

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| each filter alone | 0.5 | `films/data/facts.json` → `CC-003.singleton`, PROVED |
| every pair | 0.25 | `CC-003.pairwise`, PROVED |
| all three, even-parity world | 0.0 | `CC-003.triple_even`, PROVED |
| all three, odd-parity world | 0.25 | `CC-003.triple_odd`, PROVED |
| recorded decision | Narrow | CC-003 proposition — "E1 is synthetic; its recorded decision is Narrow" |

**Answer to Ep 3's recall:** does the source say *why* it's zero. ShieldGemma 2's
zero is documented — image-only classifier, text passes by design. LLM Guard's is
not documented anywhere.

---

# EPISODE 6 · THE NUMBER I HAD TO CROSS OUT

**Public title:** *I Wrote Down What Would Prove Me Wrong. Then It Happened.*
**Runtime:** 5:30 · **Form:** owner camera + the existing Falsifier film + screen capture
**Teaches F6 · Retrieves F1** · **Bound to:** MC-001

### Rejected conceits, and why

- *"Admitting I was wrong."* Killed: it's a confession video, and the point is
  the opposite — nothing was confessed, a rule executed. Framing it as humility
  makes the mechanism invisible and makes me the subject.
- *Dramatic music over the strike.* Killed. **Schedule deliberate silence over
  the strike.** A triumphant sting turns a correction into a personality trait.
- *"Science self-corrects."* Killed: it's a slogan, and the interesting content
  is the specific sentence written in advance that made the correction
  non-optional.

### Cold recall · 0:00–0:14 *(three back — Ep 3)*

> Episode three: two zeros, one you could reason with and one you couldn't. What
> was the difference? Hold it.

### Constraint before result · 0:14–1:20

> I went looking for a specific thing: published evaluations of AI safety filters
> that say how the filters do **together**, not just one at a time. I wrote the
> rules for what counts before I started looking. Then I counted.
>
> Twenty evaluations found. Fourteen test the filters on the same items with the
> same definition of failure. **Five** publish something you can get a joint
> answer out of.
>
> Here's the part that matters more than the count. Alongside it I wrote a
> sentence that said: *if somebody finds a qualifying evaluation I missed, this
> number is rejected.* Not revised. Not contextualised. **Rejected.**
>
> **What do you think happened?**

**PREDICTION HOLD — 3 seconds.**

### The strike · 1:20–2:30

> On the thirtieth of August I found one. Multimodal Safeguard Bench. Public
> before my cutoff. My search missed it.

Run the existing Falsifier film. **SILENCE over the strike — no music, no
sound effect.**

> The old numbers were nineteen, thirteen, four. They are struck through and
> they are still on the page. The new numbers are twenty, fourteen, five.
>
> Nobody made me do that. There was no reviewer. The rule was just sitting there
> from three days earlier, and it had already decided.

### The wrong answer on purpose · 2:30–3:00

> And that's the system working, so you can trust the twenty.

Beat.

> No. That's exactly the inference the correction doesn't license. The rule
> firing tells you the rule works. It tells you nothing about whether **twenty**
> is complete. If my search missed one evaluation, the honest posterior is that
> it probably missed others. The correction is evidence about the *process*, and
> people will keep hearing it as evidence about the *number*.

### The hidden step · 3:00–3:40

> Watch the word "missed." I said my search missed it, which sounds like an
> accident. Some of what looks like a missed row is a **rule that was too loose
> to be decidable.**
>
> There's a live example. An earlier draft claimed no printed joint result covered
> a commercial guardrail API. Same-day review found a counterexample under one
> defensible reading of "commercial." The rules already barred me from narrowing
> that word after seeing the outcome — so the clause was **dropped**, not
> reinterpreted, and the whole event is in the revision history.
>
> That's the rule that actually protects you. Not "I corrected an error." **"I
> was not allowed to redefine my way out of one."**

### Weakest sentence that survives · 3:40–4:00

> **A rule written before the count rejected my published number, and the old
> number is still visible next to the new one. That establishes what changed and
> why. It does not establish that the new count is complete.**

### Non-claims · 4:00–4:30

> Twenty, fourteen, five describes what one documented search found under its own
> rules. It is a claim about **reporting**, not about how well anything performs.
> It does not say joint evidence exists nowhere else. There is one reviewer — me
> — and the classifications are open to challenge. A different defensible reading
> of one criterion gives nineteen, thirteen, five, and that alternative is
> published alongside the main count rather than buried.

### Fluency guard · 4:30–4:50

> I have now told a story with a clean arc: rule written, rule fired, number
> changed. Real corrections are not this tidy and mine won't stay this tidy. If
> the next one is messier, that's not a system failure. That's what the tidiness
> of this one was hiding.

### Exit ticket · 4:50–5:30

> Fourteen of the twenty test their filters on the same items with the same
> failure definition. Of those fourteen, **how many document that the filters were
> compared at matched settings with everything seeing everything?**
>
> The answer is on the page and it is a single digit. Go find it, because finding
> it yourself is the entire point of this episode: cubits11.github.io/missing-column/
>
> Episode three's answer: whether the source **says why** the zero is there.

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| current envelope | 20 / 14 / 5 | MC-001 proposition; `facts.json` → `MC-001.N`, `.M`, `.K` |
| rejected envelope | 19 / 13 / 4 | `facts.json` → `MC-001.correction`, dated 2026-08-30, row `multimodal-safeguard-bench-2026` |
| declared sensitivity | 19 / 13 / 5 | `MC-001.sensitivities` → `named-products-only` |
| the ladder | M1 14 · M2 12 · **M3 0** | `MC-001.M1/.M2/.M3` |
| how K breaks down | prints a composition result 4 · releases computable per-item outcomes 2 · does both 1 | `MC-001.K.*` — overlapping routes, **not buckets you add** |
| criteria frozen | 2026-08-27, version 1 | `MC-001.frozen_as_of`, `.criteria_version` |
| reviewers | 1 | `MC-001.adjudication_mode` = `single_primary_reviewer` |

**Answer to the exit ticket: zero.** None of the fourteen. That is M3, and it is
the finding hiding inside a number that looks like bookkeeping.

---
# EPISODE 7 · I MEASURED IT AND IT CHANGED NOTHING

**Public title:** *I Spent a Month on This. The Answer Was "It Doesn't Matter."*
**Runtime:** 6:00 · **Form:** owner camera + terminal + one long unbroken take
**Teaches F7 · Retrieves F4 and F3** · **Bound to:** MC-005
**BLOCKED BY B2 — do not record until the licence contradiction is resolved.**

This is the episode that decides whether this channel is doing research or
marketing. It is the one where my own result argues against my own pitch. It
goes out at full length and it does not get a hopeful ending bolted on.

### Rejected conceits, and why

- *Framing it as a twist.* Killed. A null presented as a plot beat is still a
  performance; the viewer learns "he's clever," not "the result was small."
- *Burying it as a footnote in a stronger video.* Killed, and worth naming as a
  temptation: this result is the single most quotable-against-me thing in the
  registry, and there is real pressure to let it live only in a scope paragraph.
  Refuse that in advance, in writing, which is what this bullet is.
- *"Negative results matter!"* Killed: the genre where you congratulate yourself
  for publishing a null. Show the null. Don't editorialise it.

### Cold recall · 0:00–0:14 *(three back — Ep 4)*

> Three of five filters could be removed with zero change to the group's
> coverage. Which one cost eighteen items? Hold it.

### Constraint before result · 0:14–1:30

> Six episodes arguing that the missing measurement matters. Time to check
> whether it does. Here is the test I set up, and I want the shape of it before
> any numbers.
>
> You already have one filter running. You're adding a second. Two ways to pick:
>
> **The cheap way** — pick the partner with the best individual score. That's the
> number everybody publishes.
> **The expensive way** — pick the partner that actually covers the most
> together with what you already have. That needs the data nobody publishes.
>
> The gap between those two choices is the price of not having the data.
> **On this file, how big do you think it is?**

**PREDICTION HOLD — 3 seconds.**

### The wrong answer on purpose · 1:30–2:00

> Given everything I've shown you — pairs that don't determine triples, hidden
> overlap, filters worth zero — it should be substantial. That's the whole thesis.

Beat. Long one.

> **At most two items out of eighty-two. Two point four percentage points. And
> not one of the eleven confidence intervals excludes zero.**
>
> Zero of eleven. For the five main filters it's cleaner and worse: the cheap
> pick and the expensive pick name the **same partner, five times out of five.**
> Every regret zero. Every interval exactly zero to zero.

### The part that survives · 2:00–3:15

> So did the joint measurement do nothing? No — and the distinction is the entire
> episode.
>
> **The overlap is real and it is everywhere.** For every pair where the question
> is even defined, the filters miss together **more** than you'd predict by
> multiplying. Forty-five pairs out of forty-five. Not most. All of them.
>
> — And here's a callback worth catching: there were fifty-five pairs. Ten of
> them aren't in that count, and you already know why. They all involve the
> filter from episode three, the one that never fired. You can't measure the
> overlap of something with nothing.
>
> So: **the residual risk arithmetic moved.** Multiplying underestimates, every
> time, on this file. **The decision didn't move.** Both of those are true and
> only one of them is what I'd have liked.

### The hidden step · 3:15–4:00

> Now the part I have to say before somebody says it for me.
>
> The confidence intervals I just quoted are computed with the **picks held
> fixed** — I chose both partners using all the data, then resampled to put an
> interval on the difference between those two named candidates. That is not the
> same as an interval on a re-selected pair, and it is narrower than the honest
> version.
>
> The governing contract never specified which convention to use. I could have
> quietly picked the flattering one. It's written down in the run report as
> discrepancy D4 instead, because a convention chosen after seeing the outcome is
> exactly the thing this whole project is built to catch.
>
> There's a second one. The stratified odds ratios: seventeen of forty-five come
> out as infinity — a real positive with no discordant cases — and I count those
> as clearing my threshold. Nine more are genuinely undefined and I drop them.
> That's D3. Both of those decisions push my way. Both are logged.

### Weakest sentence that survives · 4:00–4:25

> **On this file, measuring how the filters fail together changed the residual
> risk arithmetic in every one of forty-five pairs, and changed no selection
> whose confidence interval excludes zero.**

Say it once. Do not soften it. Do not follow it with "but."

### Non-claims · 4:25–5:00

> This is counting on somebody else's file, at operating points somebody else
> chose. I loaded no model and ran no system. It does not show that joint
> measurement never changes a decision — one file, one harm stratum, eleven
> systems, unmatched settings. And it does not show that the multiplication
> assumption is safe. It shows the opposite of that, forty-five times.

### Fluency guard · 5:00–5:20

> If you came away thinking "so he was wrong and he's honest about it" — that's
> nicer than what happened and it's still wrong. The claim was always that
> marginals don't identify the joint. That claim held. What did not hold is the
> **implication** I was carrying around without stating: that the unidentified
> gap would be big enough to change what people pick. On this file it wasn't.

### Exit ticket · 5:20–6:00

> One number I quoted was computed on eighty-two prompts. Another was computed
> on three hundred and twenty-eight. **Same benchmark.** Where did the second
> number's population come from, and why doesn't the paper say?
>
> That's next episode, and it's the one where I go looking and don't fully find
> out.
>
> Episode four's answer: **NeMo. Seventy-three down to fifty-five.**

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| maximum selection regret | ≤ 2 items (2.4 pp) | MC-005 proposition (HEAD) |
| intervals excluding zero | 0 of 11 | MC-005 proposition |
| specialized supervisors, same pick | 5 of 5, regret 0, CI [0,0] | MC-005 proposition |
| positive excess joint miss | 45 of 45 non-degenerate pairs | MC-005 proposition |
| the ten pairs not counted | 55 total pairs (11 choose 2) − 45 | DERIVED here, not stated by MC-005: LLM Guard misses all 82, so its miss indicator is constant and its excess joint miss is identically zero against every partner — exactly 10 pairs. Verify against the run report before speaking it. |
| stratified odds ratio ≥ 1.5 | 23 of 36 defined | MC-005 proposition |
| +inf ratios counted / undefined dropped | 17 and 9 of 45 | MC-005 scope, discrepancies D3 |
| bootstrap | B = 2000, picks fixed, D4 | MC-005 scope |
| executed | owner, 2026-09-02; **not re-asserted by CI on every push, and the record says so** | MC-005 scope |
| independent recomputation | agrees on every pick, union, regret, benign union | `experiments/e2/results/retrospective/independent_t1.py` |

---

# EPISODE 8 · FIVE RECEIPTS FOR THE SAME DINNER

**Public title:** *A Percentage Is Half a Number*
**Runtime:** 5:30 · **Form:** owner camera + real git history on screen
**Teaches F8 · Retrieves F5** · **Bound to:** `ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md`
**PARTIALLY BLOCKED BY B3** — one beat is marked UNVERIFIED and must be
computed or cut.

### Rejected conceits, and why

- *Detective / magnifying glass.* Killed: the genre promises a solution, and
  this episode's honest ending is that the central question stays open.
- *"Gotcha, benchmark authors."* Killed twice over. They published the files that
  make this checkable at all, which is more than almost anyone in the census
  did. The episode's respect for them has to be structural, not a disclaimer.
- *Teaching the arithmetic trick first.* Killed: the trick — recover a hidden
  denominator by finding the smallest integer that makes every printed rate a
  whole count — is the fun part, so it goes in the middle, not the open.

### Cold recall · 0:00–0:14 *(three back — Ep 5)*

> Two constructed worlds, identical single rates, identical pair rates. What was
> the three-way answer in each? Hold both numbers.

### Constraint before result · 0:14–1:10

Five receipts on the table, same restaurant, same night, different totals.

> Somebody publishes "this filter catches sixty-six percent." Two thirds. Fine.
>
> Sixty-six percent **of what?** Because I went looking, and for one benchmark I
> found the population described **six different ways** across the paper and its
> own repository, and they are not the same set of items.
>
> **Before I show you: how many of the six do you think the paper's own text
> matches?**

**PREDICTION HOLD — 3 seconds.**

### The six · 1:10–2:30

Real commits, on screen, in order.

| number | composition | what it is |
|---|---|---|
| **990** | 330 / 330 / 330 | what the **paper** describes |
| **1080** | 360 / 360 / 360 | the first released file |
| **1077** | 358 / 359 / 360 | the second released file, three rows lighter, no note saying why |
| **1041** | 328 / 353 / 360 | the population the live leaderboard actually computes on |
| **174** | 86 / 50 / 38 | the first small subset |
| **170** | 82 / 50 / 38 | the small subset every number in this series uses |

> **990 is the paper's sentence. No released file has that composition.** Not
> one. It is a description, and I could not find the object it describes.

### The trick · 2:30–3:40

> So how do you find out what a published percentage was computed on, when
> nobody tells you? You use the fact that counts are whole numbers.
>
> A rate like 0.6646 is a fraction of two integers. Try denominators until every
> single filter's rate in the whole table comes out to a whole count. Eleven
> rows, one denominator. That's not a coincidence you can get by accident.
>
> It gave me 328 harmful, 353 benign, 360 borderline. And then the good part —
> **328 is not a new number.** It's the 358-row file with its thirty
> "Miscellaneous" rows taken out. 353 is the 359-row file minus six
> Miscellaneous. Borderline had none, so it doesn't move.
>
> Then the confirmation. For three of the five filters I have real per-item
> verdicts, so I can count those rows myself and compare to the leaderboard's
> numerators. **Nine numbers. Nine matches.** Lakera 218, 40, 104. NeMo 281, 63,
> 233. LLM Guard 2, 0, 1.
>
> That's identified. Not guessed.

### The question I'm making you answer · 3:40–4:20

> Now here's a diagnostic, and I want you to be wrong on purpose, because your
> error tells you which assumption is carrying weight in your head.
>
> **Thirty harmful rows were removed to make that population. LLM Guard's count
> in what's left is two. What do you now know about those thirty?**

**PREDICTION HOLD — 4 seconds.**

> Most people say: it fired zero times on them. That is the answer I gave, and
> it needs a premise I never checked — that LLM Guard's count on the *full*
> 358-row file is also two. If it's five, then it fired three times on the thirty.
> Two is a count **after** the removal. It is not a fact about the removal.
>
> Notice what just happened. You need **two** measurements to learn about the
> difference. One measurement plus an assumption is not a measurement of the
> difference; it's the assumption wearing a number's clothes. That is the same
> mistake as multiplying two miss rates, in a completely different costume.

> **[UNVERIFIED — B3. LLM Guard's harmful count on upstream file `d6ebd0e5` has
> not been taken. Either compute it and state it, or keep the beat exactly as
> written above, where not knowing it is the lesson. Do not assert it.]**

### Weakest sentence that survives · 4:20–4:40

> **The leaderboard's population is exactly one released file minus its
> Miscellaneous category — nine of nine independent checks agree. Which
> population the paper's own text refers to, I could not determine, and I am
> leaving it unreconciled rather than picking the one that fits.**

### Non-claims · 4:40–5:05

> Nothing here says anyone did anything wrong. This benchmark released per-item
> files, which is why any of this is checkable — most of the twenty evaluations
> in the census released nothing that would let you try. This is what a careful
> reader can and cannot recover from a public artifact, and the honest total is:
> the population, yes; the rule that picked the 170, **no.**

### Fluency guard · 5:05–5:20

> I found the denominator and I want the credit that's actually due, which is
> less than it feels like. The selection rule is still unknown. Only 74 to 76 of
> the 170 items appear in the earlier 174-row subset, so the small file is a
> **fresh draw**, not a trim. I don't know how it was drawn. Every number in this
> series sits on top of that.

### Exit ticket · 5:20–5:30

> Which number in the table is the one you should quote if you cite this
> benchmark? Trick question — say what you'd have to know first.
> cubits11.github.io/missing-column/reproduce/
>
> Episode five's answer: **zero, and twenty-five percent.**

### Bound numerals

Every row of the table above, the nine matching numerators, the 74–76 overlap,
`4165 = 3557 + 548 + 60` exactly, and the unreconciled 990-versus-1041 status all
resolve from `ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md`, Cut 0. Regenerate with
`python3 scripts/bells_denominators.py` (network, hash-asserted, nothing
redistributed) or `--cache DIR` offline. It exited 0 on 2026-09-05.

---
# EPISODE 9 · THE SENTENCE I'M STILL ALLOWED TO SAY

**Public title:** *How to Read a Safety Claim*
**Runtime:** 5:00 · **Form:** owner camera, one continuous setup, physical shrinking frame
**Teaches F9 · Retrieves F1, F4, F6** · **Bound to:** every prior episode

The transferable skill episode. Everything before this taught a finding; this
teaches the move, and the move is the only part a viewer can use on Monday.

### Rejected conceits, and why

- *"Ten red flags in AI safety marketing."* Killed: listicle framing produces
  suspicion, not skill. A viewer who learns to be suspicious has learned nothing
  checkable.
- *Debunking a real company's page.* Killed: it would be the most-watched episode
  in the series and it would make the channel about targets instead of method.
- *Abstract lecture on scope conditions.* Killed: that's the version currently
  sitting at position fifteen of every document in this repository. The whole
  premise of this deck is that the ordering is the bug.

### Cold recall · 0:00–0:16 *(three back — Ep 6)*

> The census number got rejected by my own rule and replaced. Does that make the
> new number more trustworthy? Yes or no. Hold it — I'll tell you at the end and
> it is not the answer most people give.

### Constraint before result · 0:16–1:10

A wooden frame on the table, adjustable, currently large.

> Every result in this series arrived the same way: a big claim walked in, and
> something made it smaller. Not weaker. **Smaller.** Narrower. And the narrow
> version is the one that's true.
>
> The move is one question and you can ask it about anything.
>
> **What would this same number look like if it were about something narrower
> than it sounds?**
>
> Watch me apply it to my own eight results. The frame gets smaller each time.

### The pass · 1:10–3:20

Shrink the frame physically at each step. Read the surviving sentence, then the
sentence it is *not*.

| Sounds like | Is actually |
|---|---|
| "Guardrails don't stack" | Two miss rates leave a range. Stacking never makes things worse. |
| "Filters fail in predictable patterns" | Eight of thirty-two patterns, **on 82 items somebody else selected** |
| "This product doesn't work" | One column of a public file, at settings nobody published, in early 2025 |
| "Most guardrails are useless" | Three of five added zero **to this group, on this stratum** |
| "Pairwise testing is useless" | Two **constructed** worlds show it can't determine the triple |
| "The census proves joint evidence doesn't exist" | One documented search, one reviewer, found five of twenty |
| "Joint measurement is essential" | Changed the arithmetic in 45 of 45 pairs. Changed no decision. |
| "The benchmark is unreliable" | Its population is exactly recoverable. Its **selection rule** is not. |

> Every one of those left-hand sentences would get more views than the
> right-hand one. That's not a coincidence and it's not a conspiracy. **The
> left-hand version is what the number feels like before you check what it's
> attached to.**

### The wrong answer on purpose · 3:20–3:50

> So the lesson is: be skeptical. Add caveats.

Beat.

> No. Caveats are decoration and everyone has learned to read past them. The move
> is not *add hedges*, it's **find the population.** Every single narrowing in
> that table came from one question: *which items, whose settings, when?* Not
> "how confident are you." That question has no wrong answer and therefore no
> teeth.

### The hidden step · 3:50–4:15

> And the step I keep making without announcing it: I put the limit **after** the
> finding, every time, even here. The number gets the good slot and the scope
> gets the cleanup slot. If you want to know whether someone actually believes
> their own limits, don't check whether the limits are present. **Check where
> they are.** Mine are usually thirty seconds too late, including in this
> episode, on purpose, so you can see it.

### Weakest sentence that survives · 4:15–4:30

> **What a result does not license is part of the result. The reliable way to
> find it is to ask which items, whose settings, and when — not to ask how
> confident somebody is.**

### Fluency guard · 4:30–4:45

> This episode is the most satisfying one in the series and it contains no new
> evidence at all. It is eight things you already saw, arranged. Notice how much
> more it felt like knowing something.

### Exit ticket · 4:45–5:00

> Take any AI safety number you've seen this month. Ask the three: which items,
> whose settings, when. If you can't answer even one — that's not a reason to
> disbelieve it. It's a reason to know you can't use it yet.
>
> **Episode six's answer: no.** The rule firing tells you the rule works. It says
> nothing about whether twenty is complete. If my search missed one, it probably
> missed others.

---

# EPISODE 10 · ZERO

**Public title:** *I Built a Research Program and It Has Measured Nothing*
**Runtime:** 6:30 · **Form:** owner camera + one live terminal command, unedited
**Mass retrieval: F1–F9** · **Bound to:** `.claude/skills/evidence-ledger/ledger.py`

The capstone, and the only episode that is genuinely uncomfortable to publish.
It runs one command on camera and reads its output without cutting away.

### Rejected conceits, and why

- *Ending on hope.* Killed. Any "but here's what's next!" turn converts an
  honest accounting into a pitch, and the whole series has been arguing that the
  turn is where claims get inflated.
- *Not making this episode.* Named because it was the real temptation. A channel
  that publishes nine competent explainers and hides the ledger is doing
  marketing with a research aesthetic. The ledger is the differentiator; the
  explainers are the doorway.
- *Making it episode one.* Killed on ordering grounds. "I've measured nothing"
  as a cold open with no prior context is self-deprecation. After nine episodes
  of actual findings, it's an accounting.

### Cold recall · 0:00–0:30 *(mass retrieval — no answers given)*

Nine questions, fast, no pauses for answers:

> Two filters, ten percent each — the range for both missing?
> How many of the thirty-two patterns actually occur?
> What makes a column of zeros usable?
> Which filter cost eighteen items when removed?
> Every pair identical — what can still differ?
> What did my own rule do to my own number?
> What did measuring the joint change, and what didn't it change?
> What's recoverable from a published percentage, and what isn't?
> What are the three questions?
>
> I'm not answering any of those. They're all in the previous nine.

### Constraint before result · 0:30–1:30

> Ten episodes. Every number checkable, every limit stated. Now the question
> nobody asks a channel like this, so I'm asking it about myself.
>
> **How much of what I've shown you did I measure?**

**PREDICTION HOLD — 3 seconds.**

### The command · 1:30–3:00

Run it live. Do not cut. Read the output as it appears.

```bash
python3 .claude/skills/evidence-ledger/ledger.py
```

> Seventeen registered claims. Own measurements: **zero.**
>
> Observation rows this repository has produced: **zero.**
>
> Qualified outcomes from the outside world: **zero.**
>
> The main experiment has **eight governing documents and zero rows.** Documents
> per row: infinity. The tool prints the infinity symbol, because I wrote it to.
>
> Eleven things are blocked on a human, and the oldest has been open four days.

### The honest accounting · 3:00–4:15

> So what have I actually been doing? Two things, and it's worth being exact.
>
> **Recounting other people's public files.** Every empirical number in this
> series is somebody else's measurement that I recomputed. That is real work —
> nine of nine independent checks landing on a hidden population is real, and
> three of five filters contributing zero is real. It is **arithmetic on
> released bits**, and I loaded no model to get it.
>
> **Building machinery that makes my own claims prosecutable.** Forty-six
> automatic checks. A rule that already rejected one of my published numbers. A
> registry where a claim expires if I don't re-check it.
>
> What I have not done is **measure anything myself.** Not once. The experiment
> that would is frozen, correctly, waiting on hardware I own and a human action I
> haven't taken.

### The wrong answer on purpose · 4:15–4:45

> Which means the machinery was premature. Should have measured first, built the
> apparatus after.

Beat.

> I don't think so, and I want to be precise about why, because "I was right to
> build it" is exactly the self-serving conclusion to watch me for.
>
> The rule that rejected my census number was written **three days before** it
> fired. If I'd written it after finding the missed evaluation, it would have
> been worthless — that's a threshold chosen after seeing the outcome, and it's
> the one thing this program treats as voiding the result retroactively.
>
> The apparatus has to be early or it isn't apparatus. **That's a reason for
> some of it. It is not a reason for eight documents and zero rows.** Those are
> different sentences and only the first one is defensible.

### Weakest sentence that survives · 4:45–5:10

> **This repository has produced zero measurements of its own. Everything
> empirical in these ten episodes is a recount of somebody else's public file.
> The apparatus that would catch me being wrong exists and has fired once. The
> measurement it was built for has not started.**

### The one action · 5:10–6:00

> There's one thing standing between here and the first row of my own data, and
> it is not code and it is not a model.
>
> **Five people who have never seen this project need to watch one short film,
> with the sound off, and answer three questions.** If two of them miss the same
> question, the film doesn't ship and I rewrite it. That gate is frozen. I
> haven't run it.
>
> That is the whole bottleneck. Not compute. Not funding. Five strangers and a
> stopwatch. Everything else in this repository is me building things I'm
> allowed to build without asking anyone.

### Fluency guard · 6:00–6:15

> Ten episodes is a lot of fluency about a program with zero rows. If these got
> good enough that the work started sounding established — that's the failure
> mode this series was designed against, and I built it anyway, and you should
> hold me to the counters rather than the delivery.

### Exit ticket · 6:15–6:30

> Run the command yourself. It's in the repository. If the zeros have changed by
> the time you're watching, that's the only evidence that any of this went
> anywhere. **cubits11.github.io**

### Bound numerals

| On screen | Value | Locator |
|---|---|---|
| claims / own-measurement | 17 / **0** | `ledger.py`, 2026-09-05 run |
| observation rows | 0 | same |
| qualified outcomes | 0, across 5 categories | same; `distribution/outcomes.yaml` |
| open blockers / oldest | 11 / 4 days | same |
| e2 scaffolding | 8 documents, 0 rows | same |
| automatic checks | 46 | `scripts/verification_manifest.py` |
| external interactions before the stop rule | 3 of 12 | `distribution/QUEUE.md` item 9 |
| the cold gate | 5 minimum, 8 maximum; two failures on one question holds release | `distribution/launch-units.yaml` → `cold_test_gate`; `QUEUE.md` item 5 |

---

## Series-level ideas that were killed

- **A "prerequisites" episode zero.** Killed: a prerequisites episode is where a
  channel puts the internal vocabulary it refused to cut. If a term needs
  teaching, teach it at the moment of use or don't use it.
- **Numbering the episodes on the thumbnails.** Killed: it tells a new viewer
  they're late. The interleaving works whatever order they arrive in — that's why
  every recall question is self-contained and every answer is deferred.
- **A companion newsletter / Discord / course.** Killed by the standing rule
  against new containers without an operational reason, and by `QUEUE.md`, which
  explicitly does not authorize a community platform, newsletter or monetisation.
  The reading that prompted this deck ended on "systematize it, package it,
  maybe literal financial value." That is the most seductive move in it and it is
  the one to refuse.
- **Guest experts.** Killed for now: the three outstanding technical asks are
  unanswered, and inviting someone on before they've replied to a research
  question converts a research contact into an audience contact. Wrong order.
- **Publishing all ten at once.** Killed: the interleaving schedule assumes gaps.
  Ship on the existing dispatch rule — one representation changed at a time, at
  least fourteen days apart — and let the retention data on each say whether the
  next is worth making.

## Falsifiers for this deck

Each is a stop condition, not a metric to optimise.

| # | Condition | Consequence |
|---|---|---|
| D1 | A cold viewer restates an episode's limit using this repository's vocabulary instead of their own | That cold open failed. Rewrite it. Not their fault. |
| D2 | Any spoken numeral disagrees with `films/data/facts.json` or the registry | Redo the take. No on-screen correction card, no verbal patch. |
| D3 | Two of the five cold viewers miss the same comprehension question | Release holds. Revise once, then a **fresh** cold set. Never rescore the old one. |
| D4 | An episode's most-clipped moment is a left-hand sentence from Episode 9's table | The narrowing is arriving too late in that episode. Move it earlier and re-cut. |
| D5 | The deck acquires a second file | It has become the thing it was written to cure. Delete the second file. |
| D6 | Episode 7 or 10 gets deferred twice while others ship | The series has become marketing. Ship 7 and 10 next or stop the series. |

## What this deck does not authorize

No upload, no schedule, no campaign, no dispatch, no new claim, no registry
edit, no change to any generated page, and no external contact. Publication
runs through `distribution/QUEUE.md` and its existing gates — including the
cold-viewer gate at item 5, which is still the next human action and which
Episode 1 is written to serve. Nothing in this file starts a clock.
