# Cubits11 world — implementation record, 2026-09-05

Built locally and verified. Not deployed by this session. No audience outcome
or comprehension result has been measured. The local recording studio is a
separate private artifact outside the repository.

## What exists

The homepage now opens with **Keep the wonder. Check the claim.** and two
explicitly constructed, hundred-item worlds. Each guard misses ten items in
both worlds; the overlap differs. The existing research dossier, factual
bindings, portrait, proof, and contact routes remain below the entrance.

`/explore/` connects a probability workbench, a screening room for three
existing films, and paths to Worldspace, the census, corrections, and archive.
The workbench changes the two marginal rates, constructs the full feasible
joint interval, selects an independence assumption, or intersects a
hypothetical joint constraint. Contradictions visibly yield an empty set.
The four areas of the displayed square are the actual joint probabilities.
A source link and the algebra make the illustration inspectable.

The private **Off the Record** recorder has an opt-in camera/microphone
preview, local recording, elapsed time, playback, download, and three speaking
anchors. It does not stream or upload. Nothing has been recorded by the owner
as part of this implementation. Browser testing used synthetic devices.

## Why this bet

The site already had a visual identity, deterministic film runtime,
Worldspace, an archive, and a generated observatory. A second movie engine or
new dashboard would duplicate those investments. The missing connection was
between the first encounter, a manipulable idea, and the inspectable record.
The recording brief also called for getting a first human conversation made;
the private recorder makes that next action concrete without creating a
public episode that does not exist.

The following is a qualitative creative allocation, not measured value or
an estimate of growth. Epistemic value, distinctiveness, comprehension, reuse,
feasibility, durability, and cost informed the ordering; they are not given
invented numerical precision.

| Rank | Creative bet | Decision and trade |
|---|---|---|
| 1 | An entrance built around two incompatible-looking worlds with identical scores | Built. Reuses the lab's core question; low infrastructure cost. |
| 2 | A variable-marginal workbench with assumption and constraint switches | Built. Complements the fixed-item Worldspace; mathematical behavior can be checked. |
| 3 | A private first-take recorder with three anchors | Built outside the site. Makes speaking possible today; no podcast platform. |
| 4 | A screening room that lets existing films lead into evidence | Included in Explore. Reuses completed media rather than manufacturing more. |
| 5 | Shareable, downloadable witness figures | Deferred. The workbench creates a concrete source for a future export. |
| 6 | Claim history as a temporal reading experience | Deferred. Existing claim-history machinery supports it; concurrent registry edits make this a poor first integration. |
| 7 | A correction-centered annotated reading tour | Existing corrections and archive linked. New public interpretation needs source-by-source editorial work. |
| 8 | A public KILL gallery | Killed for this slice. The recent scout is private; no publication of it is implied. |
| 9 | An interactive book/essay renderer | Deferred. A renderer would precede a demonstrated need for more chapters. |
| 10 | A navigable 3D museum of provenance | Killed for this slice. High rendering, accessibility, and maintenance cost without a corresponding explanatory gain. |

## Design lineage

The site retains its self-hosted Fraunces, Instrument Sans, and Fragment Mono,
carbon/bone field, gold identity, cyan evidence, amber assumptions, and red
contradiction. The hero line already exists in the repository's sibling
`visual_identity/before_you_see_it/DIRECTORS_CUT.md`; it is an evolution of
existing identity, not a new research proposition.

External references informed mechanisms, not a copied visual identity:

- [Ink & Switch](https://www.inkandswitch.com/): connect an invitation to play
  with clearly differentiated essays, projects, and lab notebooks.
- [Red Blob Games](https://www.redblobgames.com/): put direct manipulation
  next to explanation and offer a deeper implementation route.
- [Mechanical Watch](https://ciechanow.ski/mechanical-watch/): use visual
  changes to explain a mechanism rather than decorating a page.
- [Explorable Explanations](https://explorabl.es/): treat the reader as a
  participant in constructing an intuition.

These are design judgments, not evidence that this implementation improves
comprehension or reach.

## Epistemic boundary

The workbench instantiates established two-event Fréchet bounds. It adds no
new theorem. All inputs are illustrative exact probabilities; joint
constraints are hypothetical. The visual is a distribution, not a dataset,
confidence interval, deployed route, or safety estimate. Human comprehension
remains untested. Film sources and research claims retain their own scope.

No claims.yaml, claims_history.yaml, freeze, BELLS result, E2 contract, or
Ghost-Ark file was edited by this work. E2 remains untested by design and P2
empty. The counterfactual-audit theory branch was not reopened.

## Verification

- Existing `scripts/verification_manifest.py`: all 46 checks passed after
  the page-discovery fix, including bindings, generated-page drift,
  reproductions, film receipts, and the original Worldspace verification.
- `node --test tests/world.test.cjs`: four tests passed. Includes 51,005
  witness constructions over the full 1%-increment marginal grid, 10,201
  independence cases, and exhaustive enumeration of ten-item binary worlds.
- `python3 tests/test_public_discovery.py`: private/cache discovery regression
  passed for the sitemap, acquisition checks, and frontend checks.
- Browser: 1440, 768, 390, and 320px widths with normal and reduced motion;
  marginal extremes, lower/upper witnesses, independence, valid/invalid/empty
  joint intervals, reset, keyboard sliders, mobile menu/Escape, and theme toggle.
- Static proof readable with JavaScript disabled. No page-level horizontal
  overflow in tested sizes. SVG cell areas equal their probabilities.
- No browser exceptions, third-party requests, or video-file preload in the
  explorer checks. New runtime approximately 6.6 kB; new CSS approximately
  8.1 kB, uncompressed. Existing film posters account for about 1.04 MB of
  the explorer's resources; that remains a possible mobile optimization.
- Private recorder: synthetic camera/audio, record/stop, playable metadata,
  a nonempty downloaded file, device release, and a second preview cycle.
- Structural accessibility and keyboard checks are not an assistive-technology
  audit or a user study. Synthetic camera testing does not verify the owner's
  real microphone, camera permissions, long recordings, or every browser.

A pre-existing working-tree problem was discovered: public-page discovery
walked ignored `_private` research caches. It generated private paths into a
candidate sitemap and caused duplicate-page checks. Discovery now excludes
hidden and underscore-prefixed paths. The sitemap was regenerated with
30 public page URLs, no private entries. The link, frontend, and acquisition
checks use the same private-path exclusion.

The repository already contained staged and unstaged scientific edits when
this session began. They have been preserved. No commit, push, or deployment
was performed. A green working-tree run is not a claim that a clean-clone
release has occurred.

## Next three bets

1. Record the first short Off the Record take, review it locally, and extract
   one honest question in the creator's own voice. Recording is the next
   artifact; no distribution machinery is needed to begin.
2. Let a reader use the workbench, then explain why the scores cannot pick
   the overlap. A wrong explanation is information for revising the interface,
   not a metric to cosmetically improve.
3. Add a small, source-bound export of the selected witness, its inputs, and
   its assumptions. The implemented calculation makes this concrete; it need
   not become a general graphics or publishing framework.
