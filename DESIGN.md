# Design ledger

The site's own discipline applied to its design: each decision names the
options weighed, the choice, the reason, and what evidence would make me
revisit it. Dated 2026-08-20.

## Frame

**Goal.** A personal site for the Pranav Bhave / Cubits11 identity that reads
as expensive the way a well-set book reads as expensive — through typography,
restraint, and honesty — and that embodies the work it describes: claims carry
evidence, and the absence of evidence is stated, not papered over.

**Audience.** Hiring managers and researchers in cloud security / AI safety,
arriving from GitHub or LinkedIn, mostly once, mostly on someone else's Wi-Fi.

**Hard constraints.** Static hosting (GitHub Pages). Complete identity
separation from other ventures. Only verifiable biography — nothing on this
page that a resume check or a repo visit would contradict.

## Decision ledger

### D1 — Distinctive signature: evidence semantics in the UI
*(Superseded in part — v0.3 filled the result slot with E₁'s verdict and the
correct stamp reads "Supported within scope — controlled synthetic · decision:
Narrow"; the empty-slot description below is the v0.1–v0.2 state, preserved.)*
- **Options.** (a) Pure visual polish, no concept. (b) Interactive gimmick
  (3D, WebGL, cursor effects). (c) An epistemic contract: every claim visibly
  linked to public evidence, or visibly marked `attested`.
- **Choice.** (c). Solid-dot chips link to public artifacts; dashed,
  hollow-dot chips mark attested-only claims, dated. A legend sits in the
  footer. The five-card protocol from CC-Framework gets its own section, with
  the result slot left empty and stamped **untested** — untested and
  inconclusive are different states, and the stamp uses the correct one.
- **Why.** It is the only option the subject's body of work argues for.
  Anyone can buy polish; a portfolio that refuses to overclaim *demonstrates*
  the discipline the projects sell. Gimmicks (b) decay within a trend cycle
  and tax low-end devices.
- **Revisit if.** Visitors read the chips as decoration rather than
  semantics (test: does anyone hover the attested chip's title?), or the
  conceit starts crowding out plain readability.

### D2 — Stack: zero-build, hand-written static
- **Options.** (a) Next.js/Astro with components. (b) A site builder.
  (c) One hand-written HTML file, inline CSS/JS, no dependencies.
- **Choice.** (c).
- **Why.** One page does not amortize a toolchain. No project-level
  dependencies means a small supply-chain surface — not zero: GitHub Pages,
  DNS, TLS, fonts, and browser behavior remain runtime dependencies — no
  page build step to break (CI verifies the claim registry; it does not
  build the pages), and view-source that is itself a portfolio
  artifact. Total JS is ~3 KB; the page works fully with JS disabled
  (reveals default to visible, theme follows the OS).
- **Revisit if.** The site grows past ~3 pages or needs data-driven content;
  then Astro, not a SPA.

### D3 — Type: Fraunces / Instrument Sans / Fragment Mono
- **Options.** (a) Inter alone (safe, ubiquitous). (b) A display grotesk
  (Space Grotesk et al. — reads "tech startup"). (c) Old-style editorial
  serif for display + quiet grotesk for prose + typewriter mono for evidence
  metadata.
- **Choice.** (c): Fraunces (variable, optical sizing) for display, Instrument
  Sans for prose/UI, Fragment Mono for kickers, chips, captions, and stamps.
- **Why.** Luxury is typographic confidence, and the mono layer gives the
  evidence apparatus its own voice — labels read like instrument markings,
  not decoration. Self-hosted latin-subset woff2 (~194 KB total, three
  preloaded) keeps rendering deterministic: no third-party request, no
  layout-shifting fallback swap on repeat visits.
- **Revisit if.** Font weight ever dominates the transfer budget on a page
  with more images, or a language beyond latin coverage is needed.

### D4 — Color: sampled from the photograph, receipts shown
*(Superseded in part — the hex values below are the v0.1–v0.2 palette; v0.3
deepened the field and ink (see D9) and v0.4 added the semantic state layer
(see D10). The provenance story — palette sampled from Fig. 01 — survives all
three versions.)*
- **Options.** (a) Fashion-neutral gray/black. (b) An arbitrary brand hue.
  (c) Palette quantized from the hero photograph (median-cut, 10 colors),
  hand-tuned for contrast, with the sampled hexes displayed under the photo.
- **Choice.** (c). Dominant samples: `#161719` (polo), `#566326`/`#657033`
  (foliage), `#D0A58A` (skin/light). Light theme = the sunlight (warm paper
  `#F5F2EA`, ink `#161A18`, moss accent `#435B33`); dark theme = the foliage
  (`#121611`, warm ivory `#ECE7DB`, sage `#A8C491`).
- **Why.** The palette then has provenance — the site's colors are a claim
  with a visible source, which is the whole brand. Both themes are cohesive
  with the photo by construction rather than by taste.
- **Measured.** All text token pairs pass WCAG AA; most pass AAA. See
  verification log.
- **Revisit if.** The hero photograph changes; the palette must be re-sampled
  or the swatch caption removed — showing stale receipts would be worse than
  showing none.

### D5 — Motion: functional minimum, one voice
- **Options.** (a) None. (b) Scroll-driven theatrics. (c) Sub-second entrance
  reveals + micro-transitions + view-transition theme cross-fade, all gated
  on `prefers-reduced-motion`.
- **Choice.** (c).
- **Why.** Motion should confirm structure, not perform. Everything runs
  once, under 900 ms, on compositor-friendly properties (opacity/transform).
  Reduced-motion users get a fully static page — reveals are opt-in via a
  `.js` class, so no-JS and reduced-motion both degrade to visible content.
- **Revisit if.** Any animation is noticeable on a mid-range phone's first
  load, or any layout shift becomes visible in a pass.

### D6 — Photography treatment
- **Options.** (a) Full-bleed hero background with text scrim. (b) Grayscale
  duotone for "seriousness". (c) The photo as a framed object — 4:5 crop,
  hairline frame on surface, mono caption, palette swatches.
- **Choice.** (c), crop at x₀ = 407 of the 2000 px original (face upper
  third, hand and frame balanced). Metadata stripped on re-encode. WebP
  480/720/960 + JPEG fallback, LQIP inline, explicit dimensions (reserved
  space reduces layout-shift risk; no instrumented score is claimed),
  `fetchpriority=high`.
- **Why.** A framed figure with a caption treats the subject as evidence —
  "Fig. 01" — which is both the aesthetic and the argument. Scrimmed text on
  faces (a) is the genre's most common cliché and costs legibility.
- **Revisit if.** A higher-resolution original of this photograph becomes
  available (current source is 2000×1333).

### D7 — Copy voice: first person, no adjectives about myself
- **Options.** (a) Third-person bio ("Pranav is a passionate…"). (b) Buzzword
  altitude ("driving innovation in…"). (c) First person, declarative, every
  sentence checkable, non-claims stated.
- **Choice.** (c). The flagship card carries an explicit **Non-claim** box
  mirroring the project's own claim boundary. Certifications are labeled
  attested with IDs on request, rather than implied-verified.
- **Why.** Adjectives are claims without falsifiers. The strongest sentence
  available is one that shows its evidence — or its restraint. Nothing on
  this page should be contradicted by the repos it links to.
- **Revisit if.** Anything here drifts out of sync with the linked evidence;
  stale claims must be removed the day they stale, per the "claims expire"
  principle.

### D8 — Identity separation
- **Choice.** This repository, its history, and its content contain only the
  Pranav Bhave / Cubits11 identity. Commits use the GitHub-noreply address.
  Other ventures are neither named, linked, styled after, nor implied.
- **Why.** Requirement, not preference.
- **Revisit if.** Never, absent an explicit decision by the owner.

## Budgets

Measured 2026-08-23 (v0.4). The v0.3 row values had themselves gone stale —
index had grown to ~53 KB by 2026-08-21 while this table still said 42.3 KB —
which is why the table now records its measurement date.

| Budget | Target | Shipped (v0.4, measured 2026-08-23) |
| --- | --- | --- |
| HTML (index, incl. inline CSS/JS) | < 55 KB | 48.6 KB |
| Shared stylesheet (assets/site.css) | < 20 KB | 16.1 KB |
| Fonts (4 × woff2, latin subsets) | < 220 KB | ~194 KB |
| Hero image (720 webp, typical load) | < 50 KB | ~31 KB |
| JavaScript (index, inline, incl. theme boot) | < 6 KB | 4.5 KB |
| Third-party requests from page code | 0 | 0 (hosting infrastructure excluded) |
| Layout shift | none visible | manual passes only — not instrumented |

## Verification log — 2026-08-20

- **Contrast (WCAG, computed):** light ink/bg 15.7 · muted/bg 5.6 ·
  accent/bg 6.8 · accent/surface 7.2; dark ink/bg 14.8 · muted/bg 7.9 ·
  accent/bg 9.6. All ≥ 4.5 (AA for normal text); most ≥ 7 (AAA).
- **Themes:** light and dark verified by screenshot; manual toggle overrides
  and persists via `localStorage`; system preference respected when unset.
- **Responsive:** 1280 px and 375 px verified by screenshot; no horizontal
  scroll; nav collapses to wordmark + toggle on small screens.
- **Reduced motion / no-JS:** reveals are additive (`.js` gate) — content
  visible without JavaScript; smooth-scroll disabled under reduced motion.
- **Metadata:** portrait re-encoded via PIL (EXIF dropped); OG image
  1200×630; JSON-LD ProfilePage/Person; canonical URL; sitemap.
- **Keyboard:** skip link, visible focus rings, all interactive elements
  reachable in order.
- **Layout shift:** none observed during the documented manual desktop and
  mobile passes. Instrumented CLS has not been recorded — the site runs no
  analytics by design, so no field-performance numbers are claimed anywhere.

## Non-claims

This site does not claim: traffic (no analytics exist), endorsement by any
institution named, verification of attested items (they are attested, dated,
IDs on request), or security guarantees for linked repositories. Hosting
headers are GitHub Pages defaults; no CSP is set — acceptable for a site with
zero third-party page code, revisit if that changes.

---

## Changelog — v0.2, 2026-08-20 · the audit corrections

An external audit of v0.1 found the correct core defect: *the interface
looked more epistemically disciplined than the underlying claim–evidence
relationship actually was.* v0.2 closes that gap. Every item below is a
truth correction or a mechanism that makes a previously rhetorical promise
operational.

**Truth corrections (P0)**
- Ghost-Ark recast from "transactional control plane" (stale) to what its
  repository actually is: a verifier and measurement harness for the
  provenance limits of AI-governance receipts, with its non-claim displayed.
- CC-Framework copy no longer says evidence "can never" overstate — no
  claim-governance system can guarantee that. It now states the
  partial-identification framing and carries "harder, not impossible."
- "Inconclusive — awaiting result" was an epistemic category error:
  inconclusive means evidence arrived and failed to discriminate; the empty
  card is **untested**. Corrected, and the distinction is now taught in the
  method note.
- Assay's description narrowed: attestation cannot establish a file's
  history prior to the first attested operation, and the copy now says so.
- The discipline's scope is declared (Option B): evidence markers cover
  technical project claims; biography is owner-attested unless linked.
- "Interactive demo" no longer labels source code; Ghost Visualizer is
  described as what it is — a local visual essay, source linked.
- This ledger's own language de-absolutized: "CLS 0" → manual observation;
  "zero supply-chain surface" → small project-level surface with named
  runtime dependencies; README's "no pipeline, nothing to break" removed
  (there is now deliberately a pipeline).

**Mechanisms (P1)**
- `claims.yaml`: a structured claim registry — proposition, scope, support
  bound to immutable commits, provenance, status, review triggers,
  non-claims. Rendered as the public evidence ledger (`/ledger/`).
- CI (`.github/workflows/verify.yml`): registry shape, link liveness,
  ledger coverage, and a freshness gate — claims past their review window
  fail the weekly run. "Claims that return for review" is now a mechanism,
  not a slogan.
- Flagship case study (`/essays/when-marginals-are-not-enough/`) with the
  kernel's actual recorded output at a bound commit, an endpoint-witness
  explanation, explicit non-claims, and its own filled claim envelope.
- Résumé page with a 90-second overview (phone deliberately withheld from
  the open web).
- Accessibility: attested state readable without hover (visible text +
  screen-reader expansion), copy action announced via a live region with a
  failure path, theme toggle exposes `aria-pressed` and a stateful label,
  descriptive link labels, mobile navigation restored.
- Hero restructured: plain-language proposition first, poetic thesis second
  — first-contact decoding cost lowered without giving up the voice.
- Reveal animations inverted: content is visible by default; hiding is
  applied only just-before-observing, with a timeout failsafe. Enhancement,
  never a dependency.
- Metadata: ProfilePage structured data, `imagesrcset` preload, stored-theme
  `theme-color` sync, sitemap, OG image alt.

**Held (P2 — research program)**
- The comprehension study (claim-bound vs control portfolio) is designed but
  not run. Until it runs, this site claims only that the grammar exists —
  not that it works on readers. That hypothesis stays open by design.

---

## Changelog — v0.3, 2026-08-20 · the claim engine and the record

A second verification audit of the deployed v0.2 found five places where the
site still *asserted* mechanics it did not *have* — mirroring called
generation, liveness called binding, a timer called evidence-responsiveness,
provenance collapsed into status, and this ledger's own leftover absolutes.
All five are documented publicly in
[Noetic Log 001](https://cubits11.github.io/notes/noetic-log-001/), and v0.3
closes them with machinery rather than wording:

**Engine (registry schema v0.2)**
- `claims.yaml` now separates visibility, provenance, support role,
  evidential status, and maturity. "Attested" is provenance only; an
  owner-attested claim with no public artifact reads *publicly untested*.
- `/ledger/` is **generated** by `scripts/generate_ledger.py`; CI
  regenerates and fails on drift. Hand-editing the ledger breaks the build.
- Binding means binding: the verifier requires each declared commit to be
  embedded in its support URL.
- Review triggers are typed and tagged `executable` or `manual`. Executable
  triggers run in CI against live evidence: bound file at bound ref vs
  default-branch HEAD (CC-001 kernel module, CC-002 manifest, GA-001 thesis,
  GV-001 README) and a local content hash for DESIGN.md itself (SITE-001).
  Manual triggers are displayed as manual instead of borrowing credibility.
- `scripts/reproduce_cc001.py` re-runs the bound computation from a clean
  clone in CI on every push and weekly — CC-001 is continuously reproduced,
  not merely recorded.

**D9 — v0.3 visual direction: "the record" (dossier)**
- **Options.** (a) Keep the sunlit-paper luxury of v0.1–v0.2. (b) A louder
  cinematic/WebGL direction. (c) A dossier: obsidian-first, bone text, a
  gold signal color, oversized stacked nameplate, outlined section numerals,
  classification and status strips, the photo double-framed as evidence.
- **Choice.** (c). The commission asked for a bolder, more formidable
  presence; the honest way to be formidable is to point the menace at
  claims, not people — the "threat" is the standard, made visible.
- **Palette provenance preserved.** Greens and ink remain the photograph's
  samples; the gold is the photograph's warm light sample `#D0A58A`
  deepened for signal duty (`#C9A15E` dark / `#755A2C` light — the light
  value chosen to clear WCAG AA at 5.5:1). All token pairs re-verified AA;
  most AAA.
- **Revisit if.** The dossier furniture (bars, numerals, stamps) starts
  outweighing the content it frames, or a reader-facing test shows the dark
  default hurting first-contact comprehension.

**Corrections in this ledger (found by the v0.2 audit)**
- D1 "stamped inconclusive" → stamped **untested** (the page had been
  corrected; this document hadn't — which is exactly the drift SITE-001's
  local-hash trigger now detects).
- D2 "no build breakage in five years" → no page build step to break; an
  unverifiable prediction replaced with a checkable description.
- D6 "(CLS 0)" → reserved space reduces layout-shift risk; no instrumented
  score is claimed.

---

## Field artifact P₀ — the evidence-bound portfolio

**Status:** experimental · **Version:** 0.2

**Research object.** A personal portfolio that encodes claim status,
evidence provenance, non-claims, and challenge conditions as persistent
interface structures.

**Hypothesis.** Making claim boundaries visible improves a visitor's
ability to distinguish public availability, evidential support, owner
attestation, test status, and explicit non-claims.

**Primary failure discovered (v0.1).** A visually coherent evidence system
can produce the impression of rigor even where the claim–support mapping is
stale, mutable, underspecified, or selectively applied. v0.1 conflated
visibility with support, attestation with evidential status, and unobserved
results with inconclusive ones; two project descriptions had drifted from
their repositories.

**Candidate contribution.** The claim envelope — proposition, scope,
support, challenge, test design, status, boundary, freshness — implemented
in `claims.yaml`, rendered in `/ledger/`, enforced in CI.

**Null hypothesis (alive).** The interface may improve aesthetic trust or
memory without improving reasoning, evidence selection, or calibration.

**Next experiment.** Compare this portfolio against a conventional control
version on comprehension, evidence-selection, status-decoding, non-claim
recall, and delayed transfer. Aesthetic preference measured separately from
epistemic performance — a reader may love the design and misread the
epistemology, and that must be detectable.

**Canon decision.** Nothing is canonical. The claim envelope is Candidate
after implementation; it advances only on user-testing evidence. The
public/attested dot semantics remain experimental and are expected to be
replaced by the envelope's richer state model.

## Fig. 02 — the bounds figure

**Decision.** Inline the animated figure rather than link it, and assert its
geometry at build time: overlap area must equal q to within 1e-9 in all eleven
frames.

**Why.** Inlining lets it inherit the site's tokens, so it obeys the theme
toggle rather than only the OS preference. Asserting the geometry means a figure
that lies about probability fails the build instead of looking fine.

**Correction, 2026-08-21.** The first build guarded label overflow with an
estimated 190px string width. Measured on the deployed page, the widest
right-hand label renders at **207px**. The guard passed only because it happened
to be conservative in the safe direction — an assertion built on a guessed
constant is not an assertion. The layout now leaves margin against the measured
value, and the first version's labels were in fact clipped in production before
this was caught by measuring the deployed SVG rather than trusting the source.

**What would make me revisit it.** A screen-reader user reporting that the
`desc` does not carry the argument, or any frame failing the geometry assertion.

**Correction, 2026-08-23.** The paragraph above claimed the geometry was
"asserted at build time" — and no such checker existed anywhere in this
repository. The assertion lived in an authoring script that was never
committed; the repo contained only its output. That is precisely the
"asserted mechanics it did not have" class that the v0.3 changelog documents
correcting, recurring in the document that documents it. The mechanism now
exists: `scripts/verify_figures.py` parses the committed frames and asserts —
to 1e-9 — pinned marginals, overlap-equals-q, atom-vector coherence, axis
linearity, and the 1% independence tick, plus the essay number-line's bands
and dots; `verify.yml` runs it on every push and weekly. The sentence became
true the day the checker was committed, and not before.

---

## Changelog — v0.4, 2026-08-23 · the observatory

The redesign that turned a five-page record into an evidence observatory:
modules, an observatory view, writing/archive/now surfaces, and a shared
design system. Registry schema v0.3 (maturity gains `superseded`; structured
`expected` blocks; the reachable-ref binding rule after CC-001 was found
pinned to history-rewritten commits). Full reconnaissance and rationale:
`docs/site-system/AUDIT.md`.

### D10 — Design system: one stylesheet, semantic state colors
- **Options.** (a) Keep per-page inline CSS (six diverging token copies had
  already accumulated, with the signal color named `--gold` on three pages
  and `--accent` on three others). (b) A build step compiling per-page CSS.
  (c) One shared `assets/site.css` carrying tokens and epistemic primitives;
  pages keep only page-specific layout inline.
- **Choice.** (c). This supersedes part of D2 ("one hand-written HTML file,
  inline CSS") under D2's own revisit clause — the site grew past three
  pages. The generator idiom stays; no framework arrives.
- **State palette.** Ported from CC-Framework's claim-observatory color law
  ("Cyan/white light marks evidence and replayable structure. Amber marks
  required review. Red is reserved for expiration/invalidation."):
  `--evidence` cyan (dark `#7FC4CF`, light `#175F6B`), `--review` amber
  (dark `#E9A23B` — the film's lure amber — light `#7E4E12`), `--invalid`
  red (dark `#E4796F`, light `#993127`). Unknown/inactive stays graphite
  (`--muted`). Green carries no semantic duty anywhere. Gold remains the
  identity accent only. Evidence chips' solid dot moved from sage to cyan;
  the 404 stamp moved to `--invalid` (a falsified claim is the one place red
  is earned).
- **Measured.** Contrast computed 2026-08-23 (WCAG relative luminance), on
  field/surface respectively — dark: evidence 9.84/9.40, review 8.92/8.52,
  invalid 6.68/6.38; light: evidence 6.22/6.68, review 6.01/6.45, invalid
  6.36/6.82. All ≥ 4.5:1 (AA); most ≥ 6.
- **Rule.** No state is ever encoded by color alone — every colored state
  pairs with a label, a shape (dot/square/dash), or both.
- **Revisit if.** Light-mode review-amber (`#7E4E12`) proves confusable with
  light-mode gold (`#755A2C`) in practice; the pairing rule is the current
  mitigation.

### D11 — Fig. 02 becomes an instrument: user-driven, never autoplaying
- **Options.** (a) Keep the 7-second infinite autoplay loop. (b) Add a pause
  button to satisfy WCAG 2.2.2. (c) Replace autoplay with a slider: the
  visitor drags the shared-miss overlap q through all eleven worlds while
  both marginals stay visibly pinned.
- **Choice.** (c). Moving the world is the argument; a viewer who chooses q
  feels the underdetermination that a loop merely displays. Each position
  reports P(both fail), P(at least one fails), and the world's name — the
  endpoints are labeled as witnesses, q=1% as "the world independence
  assumes."
- **Default state.** The previous reduced-motion fallback showed the 1%
  frame — the independence world, the exact world the figure exists to
  de-privilege. The static/no-JS/initial state is now the lower endpoint
  witness with the full supported interval always drawn on the cyan axis;
  the independence tick is amber (an assumption calling for attention, not
  an answer).
- **Accessibility.** Native range input (keyboard-operable), described by
  the SVG's long `desc`; no animation, so nothing to pause; the SVG scrolls
  inside an `overflow-x` guard on narrow screens.
- **Revisit if.** Anyone reads the slider as *estimating* the true
  dependence — the readout names each position as one feasible world to
  prevent exactly that.

### D12 — Information architecture: the observatory routes
- **Choice.** Primary navigation becomes Modules · Observatory · Ledger ·
  Writing · Archive · Résumé, on every page. New routes: `/modules/` (six
  generated module pages under one epistemic grammar), `/observatory/`
  (the registry rendered as one field of capsules, bindings, non-claims,
  decay clocks), `/writing/`, `/archive/` (intellectual lineage with
  succession records — GCE moves here under claim GCE-001), `/now/`. Every
  pre-v0.4 URL keeps resolving unchanged; nothing moved, so no redirects.
- **Why.** The homepage was carrying every role at once. The mission of the
  redesign is to make hidden epistemic structure visible; structure needs
  places.
- **Generated, drift-checked.** Modules and the observatory follow the
  ledger's idiom: registry → deterministic renderer → `--check` in CI. The
  homepage's registry facts (claim count, last owner review) are now
  cross-checked by `verify_claims.py` — the noetic log's "hand-written
  strips" residual is closed.
- **Revisit if.** A route stays empty of evidence long enough to read as
  decoration; planned modules must say PLANNED on their face.

## Verification log — 2026-08-23 (v0.4)

What was actually verified this pass, and how:

- **Gates (executed locally, all green):** `verify_claims.py` (12 claims —
  shape, bindings, executable triggers against live evidence, freshness,
  ledger coverage, homepage coherence); `generate_ledger.py --check`;
  `generate_modules.py --check` (7 pages); `generate_observatory.py --check`;
  `verify_figures.py` (Fig. 02's eleven frames + the essay number line, 1e-9);
  `check_links.py` (284 internal references across 17 pages);
  `reproduce_cc001.py` (clean GitHub clone at the bound commit — bounds and
  witness feasibility/attainment reproduced).
- **Browser pass (local server, Chromium):** desktop 1280×800 and a narrow
  (~375 px) pane, structural; dark and light themes verified by computed
  background and state tokens; fonts confirmed loaded via `document.fonts`;
  no horizontal body overflow on index (measured, not eyeballed).
- **Instrument:** slider drives the frames (q=0 → q=7 verified; exactly one
  frame visible; output announces the world's name); no-JS default is the
  lower-endpoint-witness frame by CSS.
- **Observatory:** 12/12 decay clocks drawn with correct elapsed days
  (0d for the 08-23 cohort, 3d for 08-20); no false review-due or expired
  states.
- **Module 004:** renders PLANNED stamps, the AS-001 envelope, and no
  fabricated sections.
- **Contrast:** computed ratios recorded under D10.
- **Not verified in the v0.4 pass, and therefore not claimed then:** a full
  keyboard-only traversal of the new pages, a screen-reader pass over the new
  SVG descriptions, and print styles for the new routes. These were listed as
  open QA items instead of being absorbed into "QA passed."

### Keyboard and screen-reader audit — 2026-08-23 (closing the v0.4 debt)

Run in a browser against the local server, DOM-level and interactive:

- **Keyboard operability — verified.** The feasible-worlds slider is a native
  range input with a resolving accessible name and `aria-describedby` pointing
  at the figure's `desc`; focusing it and stepping the value updates the live
  output (q = 3% → 4% observed). Every nav link is a real `<a href>`
  (keyboard-reachable), the theme toggle is a `<button>` exposing
  `aria-pressed`, the skip link targets `#main` and the target exists,
  and a `:focus-visible` outline rule is present. Across the six new pages
  (observatory, now, writing, archive, noetic-log-002, module 005): exactly one
  `h1` each, **no skipped heading levels**, skip link present on all.
- **Screen-reader structure — verified statically.** No page carries a `title=`
  attribute holding unique information (the hover-only concern is fully closed);
  no image lacks `alt`; the observatory's decay-clock SVG is `aria-hidden` so a
  screen reader receives the textual `reviewed … window` dates rather than a
  bare ring; each capsule carries an `h2`; the three owner-attested capsules are
  each visibly marked with an attested chip and a dashed neutral rail, and
  maturity renders on every capsule.
- **Still honestly owed:** a session with a real assistive technology
  (VoiceOver / NVDA), which a DOM-and-keyboard audit approximates but does not
  replace, and print styles for the new routes. The accessibility score in
  Noetic Log 002 stays provisional until the AT session runs.
