# Experiment ledger — the film laboratory

DEFEAT → DATA → ADAPTATION → NEW EXPERIMENT → SUCCESS. Every entry names a
prediction, what the pixels showed, the likely cause, the variable changed,
and the next experiment. A single attractive result is evidence, not canon.
Nothing here is deleted; a wrong prediction is the most useful row.

Grading is of pixels, never of code: every observation below was made on
rendered stills (open / quarter / mid / three-quarter / end, plus the claim
frames) and on the encoded motion.

## Experiment 1 — inspected 2026-09-01, treated as data

Objects inspected: `cc-framework/visual_identity/before_you_see_it` (15 s film,
five frames extracted from the encoded master, plus its poster), the
Claim Observatory Blender stills (`world_v3_hero.png`, `world_v3_decay_clock.png`),
and the site's Fig. 02 feasible-worlds slider.

| what was conceptually powerful | what became generic | what needed explanation | what was memorable | what was brittle | what was epistemically excellent | what failed to produce a strong object |
|---|---|---|---|---|---|---|
| "name it before you see it" — the result slot left empty while the protocol locks; the honest `INCONCLUSIVE` + `ILLUSTRATION` stamp | drifting gold embers, a glowing notebook, a vignette-and-grain charcoal void, five accent-coloured cards, a wordmark lockup with a five-colour rule | the blue notebook (a source-ledger easter egg a stranger cannot decode); a grid of 84 labelled coincidences at 11 px | the empty dashed fifth card | Linux fallback fonts (Charter / DejaVu) instead of the site's vendored faces; a fixed fake timestamp and hash as set dressing; Blender 5.1 for the observatory | the verdict rule — the film refuses to display a verdict it was not given | no number appears anywhere; nothing is bound to evidence; the film animates sentences (CLAIM · FALSIFIER · CONTROL) rather than an operation |
| Fig. 02: marginals pinned, overlap sliding, atoms printed, independence tick de-privileged, geometry asserted in CI | — | — | the interval always on the axis | SVG text ~3.7 px at 320 px wide | the only Experiment 1 object whose every pixel is checkable | flat rectangles — no population, no world, no motion in the poster |
| Observatory: cyan/amber/red colour law (evidence / review / invalidation) — ported into the site | glass cylinders, orbit rings, floating labels, mirrored text, a "dashboard in space" | everything | nothing legible | a 24 GB-class render path | the colour law | the whole scene |

**Changed variables for Experiment 2**

1. Evidence exists now: CC-001/CC-004 bounds and witnesses, CC-003 parity, MC-001 census (20/14/5, ladder 14/12/0, correction 19/13/4 → 20/14/5), MC-002 BELLS counts (73/82, 9/82, leave-one-out 55/70/73/73/73), MC-003 identified sets, MC-004 strata, GA-001 non-claims. Experiment 1 had none of these.
2. A fact registry (`scripts/facts.py`) and `expected` blocks exist; numbers can be bound, not retyped (`scripts/films/bind_facts.py`).
3. The site's own fonts and semantic colour law exist; a film can share the pages' provenance.
4. Capture at 50 ms per frame over the DevTools protocol; a 30-second film renders in about a minute, so pixels can be graded and revised in the same hour.
5. The reviewer can see: every render is graded on five stills and its claim frames before it counts.
6. A truth contract per film (`manifest.yaml`: claim, scope, evidence, objects with OBSERVED/DERIVED/PROVED/CONSTRUCTED/ILLUSTRATIVE/UNKNOWN status, falsifier, non-claims, claim frames) verified by `scripts/films/verify_films.py`.

**Lessons carried, not repeated**

- Keep: the verdict rule (never display what you were not given) — generalised into the object ledger tag on every frame that carries an object.
- Keep: the colour law and the empty-cell motif.
- Drop: particles, vignette, film grain, glow-for-its-own-sake, wordmark lockups, fake hashes, fallback fonts.
- Replace: the fake protocol bar with real dates and real hashes (slate: `frozen-before-seen`).

## Experiment 2 — Cohort A, pre-render predictions (written before the first render)

| film | prediction | risk named in advance |
|---|---|---|
| same-scores-different-worlds | the ring hop will carry the idea silently; the split frame will be the poster | the scoreboard and axis will need two passes; vertical may crowd |
| thirteen-worlds | one sliding rod will make "which quantity is free" obvious; the 2.87 ghost will read | 82 columns at 1080 px wide may be too fine; the bracket text may crowd the rods |
| parity-cube | identical shadow walls under different cubes will land in one look | own 3D projection risks illegible corners; the 111 label may collide with edges |
| the-missing-column-census | the emptying third ladder column will be the strongest beat | twenty long ids and six columns may overflow; too much prose |
| leave-one-out | the shutter beat (−18) will be the memorable image | the constructed wall must never read as the released rows; lamp labels may overflow at 212 px |
| what-the-seal-proves | the merge into one card and the light stopping at the line | two acts in 34 s may rush; the quoted sentence is long |

## Experiment 2 — observations (from the rendered stills, three passes on 2026-09-01)

Method: after every pass, the five review stills (open / q1 / mid / q3 / end), the
contact sheet, and each declared claim frame were inspected for both formats; the
receipts' overflow counts were read before the pixels. Fixes were made in the film
source and the runtime, never by hand-editing a frame.

| film | prediction held? | observed problem (pass 1) | likely cause | changed variable | result (pass 3) |
|---|---|---|---|---|---|
| same-scores-different-worlds | yes — the hop carries the idea silently; the split frame is the poster | black frame at t=0 and at the act cut (15.0 s); act-2 score lines, π vectors, interval sentence and axis all collided; vertical tag ran off the left edge | fade-in from black; two eased alphas meeting at 0 on the cut; act 2 laid out by guess, not by stacking; single-line tags with no wrap | hard cuts (no black dip); act 2 rebuilt as a vertical stack with "=" between the equal scores and "≠" between the joint counts; tags and locators wrap in the runtime | 0 overflows both formats; claim frames clean; the end frame keeps the locator |
| thirteen-worlds | yes — one sliding rod makes the free quantity obvious | the RELEASE-RECOMPUTED stamp sat on the axis; beads appeared only after 0.4 s; the ledger tag overlapped the kicker | stamp anchored to the count instead of the union line; pour offset; tag placed at the same top-left as the kicker | stamp moved to the union line's right end; pour starts at frame 0; runtime rule: master right-side tags keep to 62 % width, vertical tags live in a band above the locator | 0 overflows; the end frame is the poster |
| parity-cube | yes — identical walls under different cubes land in one look | title over the "same singles" line; world labels inside the cube; a corner over the kicker; vertical: three labels overflowed by 1–17 px and a cube sat on its own wall | absolute y positions chosen before the cube's projected extent (R × 1.49) was known | cubes lowered and shrunk (R 190→175); world labels moved beneath the cube; label maxW and sizes; vertical stack re-spaced | 0 overflows both formats; the 111-corner frame is the poster |
| the-missing-column-census | partly — the emptying third column is the strongest beat, but pass 1 never showed it | 36 px rows pushed the "0 of 20…" sentence and the correction block below the frame; the sixth header ran off the right edge; joint tallies collided with the ladder tallies; vertical bottom block overflowed | table sized without summing the rows; joint tally anchored under the joint column | 30 px rows, six columns re-measured to end inside the table, tallies under the ROW column, sentence and correction as wrapped paragraphs, vertical tag pinned to the top | 0 overflows both formats; the 14 / 12 / 0 frame with the sentence is the poster |
| leave-one-out | yes — the −18 shutter frame is the memorable image | lamp labels overflowed a 212 px pitch while 40 % of the frame sat empty; the summary was one 1916 px line; vertical labels overflowed | the lamp row copied the wall's width instead of the frame's | lamp pitch 300 px; summary and shutter readout moved into the empty column as wrapped paragraphs; short vertical label variants | 0 overflows both formats |
| what-the-seal-proves | half — act 2 (the boundary) landed first time; act 1 did not | act 1: cards fading in from nothing, tiny horizontal rollers, the merged card sitting on the DIGEST roller, the seal on the card; "AUTHORIZED?" 16 px wider than its door | horizontal rollers at the cards' own height; doors sized before the serif was measured | act 1 rebuilt as three vertical gates the cards pass through; cards present at frame 0 with the ≠; seal moved beside the merged card; doors 280 px with a 34 px face | 0 overflows both formats; the boundary frame is the poster |

**Cross-cutting findings**

1. Every pass-1 defect was a layout defect, none was an epistemic defect: the fact binding held from the first render, and no number on screen ever needed correcting. Binding before drawing is the change that paid most.
2. Text overflow accounting in the runtime found every clipped label before the eye did; the eye found every collision the accounting could not (overlaps are not overflows). Both are needed; neither replaces the other.
3. "Empty frame at t=0" recurred in three films — the habit of fading in from black. Rule adopted: the opening frame is composed, never black.
4. The vertical cut is not a crop; it is a second layout. Films whose vertical branch was an afterthought (census, leave-one-out) needed a second pass; films designed as stacks (thirteen-worlds, seal) did not.
5. Storage: PNG review stills were 19 MB against 12 MB of video; stills are now JPEG (quality 90) and posters stay PNG.

**Next experiment (Cohort B) — predictions recorded before any Cohort B frame exists**

- The Benign Floor will be the hardest to keep silent-legible: a floor drawn before the data is a temporal claim, and the film must show the order, not just the levels.
- Review Due will read as "false" unless the red lamp is paired with REVIEW DUE at poster size; predict one pass to get that pairing right.
- Frozen Before Seen is the direct replacement for Experiment 1's fabricated protocol bar; predict it is the cheapest film of the cohort and the one most likely to be mistaken for a preregistration claim — the "lock proves preservation, not ignorance" line must be on the poster frame.

## E3.1 — the feed-native derivative (2026-09-01)

Prediction, written before the first render: the master's grammar compressed to a
square would carry the invariant on its own if the two readouts were large and
literally motionless, and the phone-size gate would fail first on supporting
text, not on the readouts.

| pass | observed on the 390 px previews | changed variable |
|---|---|---|
| 1 | readouts, BOTH counter, reveal and CTA all legible at phone size; the amber point was absent from the interval frame (it landed 0.0 s after the claim frame); the independence label sat on the axis and collided with the caption; DIFFERENT WORLDS. and the CTA overflowed their boxes | point lands 0.4 s earlier; caption and ticks above the axis, independence labels below; reveal 54 px; CTA band full width |
| 2 | one supporting caption 31 px over the sheet edge; the CTA began fading in inside the interval claim frame | caption 28 px; CTA starts at 9.9 s; claim frames re-timed |
| 3 | 0 overflows, deterministic; every ESSENTIAL item readable on the phone sheet; FIXED and the two supporting captions are ~11 px at phone size and are classified SUPPORTING | — |

What the cut removes relative to the master: the per-world atom vectors, the
endpoint-witness stamps, the ledger tags, the kicker, the registry locator,
and the whole first act's scoreboard prose. What survives: two readouts, one
moving arrangement, one counter, one name, one interval with one point, one
action. Every surviving motion changes information: the hop changes the
arrangement, the counter changes the joint count, the dim shifts attention to
the interval, the point lands, the CTA appears. Nothing drifts.

Lesson recorded: the prediction held on the readouts and failed on timing —
a claim frame declared at the exact second an object begins to appear
captures its absence. Claim frames must be declared after the eased arrival,
not at its start.

## 2026-09-05 — the-missing-column-trailer (master, 34 s)

Prediction before render: the census act is the weakest beat because four numerals with qualifiers compete for one frame; the Same Scores act will carry the open. Observed on the contact sheet: the open, the endpoint, the axis and the close read cleanly; the census act stages its four rows sequentially and the third row (0, in review amber) is the only coloured numeral, which is the intended emphasis. One overflow class (DIFFERENT WORLDS. at 54 px against a 1920 frame) fixed by sizing the name to 41 px at x = 1420; second render 0 overflows, determinism ok, 16 facts bound, 7 claim frames. Not published to any feed: the cold-comprehension gate in distribution/launch-units.yaml applies to this cut as to every other, and no cold trial has been scored.
