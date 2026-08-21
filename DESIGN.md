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
- **Why.** One page does not amortize a toolchain. Zero dependencies means
  zero supply-chain surface, zero build breakage in five years, and
  view-source that is itself a portfolio artifact. Total JS is ~2 KB; the
  page works fully with JS disabled (reveals default to visible, theme
  follows the OS).
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
  load, or CLS creeps above 0.

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
| HTML (index, incl. inline CSS/JS) | < 40 KB | 31.4 KB |
| Fonts (4 × woff2, latin subsets) | < 220 KB | ~194 KB |
| Hero image (720 webp, typical load) | < 50 KB | ~31 KB |
| JavaScript | < 4 KB | ~2 KB |
| Third-party requests | 0 | 0 |
| CLS | 0 | dimensions + preload; verified visually |

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
  1200×630; JSON-LD Person; canonical URL.
- **Keyboard:** skip link, visible focus rings, all interactive elements
  reachable in order.

## Non-claims

This site does not claim: traffic (no analytics exist), endorsement by any
institution named, verification of attested items (they are attested, dated,
IDs on request), or security guarantees for linked repositories. Hosting
headers are GitHub Pages defaults; no CSP is set — acceptable for a site with
zero third-party code, revisit if that changes.
