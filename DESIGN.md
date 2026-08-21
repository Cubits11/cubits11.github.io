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
- **Options.** (a) Pure visual polish, no concept. (b) Interactive gimmick
  (3D, WebGL, cursor effects). (c) An epistemic contract: every claim visibly
  linked to public evidence, or visibly marked `attested`.
- **Choice.** (c). Solid-dot chips link to public artifacts; dashed,
  hollow-dot chips mark attested-only claims, dated. A legend sits in the
  footer. The five-card protocol from CC-Framework gets its own section, with
  the result slot left empty and stamped inconclusive.
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
  build breakage in five years, and view-source that is itself a portfolio
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
  480/720/960 + JPEG fallback, LQIP inline, explicit dimensions (CLS 0),
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

| Budget | Target | Shipped |
| --- | --- | --- |
| HTML (index, incl. inline CSS/JS) | < 45 KB | 39.3 KB (v0.2) |
| Fonts (4 × woff2, latin subsets) | < 220 KB | ~194 KB |
| Hero image (720 webp, typical load) | < 50 KB | ~31 KB |
| JavaScript | < 4 KB | ~3 KB |
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
