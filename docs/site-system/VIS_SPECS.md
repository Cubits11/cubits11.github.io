# Visualization specs — candidates beyond the shipped instrument

Date: 2026-08-23. CC-VIS-001 (the feasible-worlds instrument) shipped on the
front page in v0.4. These are the frozen specs for the next candidates —
specs before implementations, each with the boundary it must not cross.
Nothing here is a commitment or a claim; a spec graduates only by being
built under the site's gates (geometry assertions, registry bindings,
reduced-motion neutrality, no-aggregate rule).

## CC-VIS-002 — Witness Theatre

- **Purpose.** Make sharpness visible: the interval's endpoints are not
  worst-case rhetoric but attained worlds.
- **Form.** The lower-endpoint and upper-endpoint witness distributions side
  by side as atom masses (2-guardrail case: four atoms each). A viewer can
  inspect every atom's mass; the values come from the kernel run that
  CC-004 continuously reproduces, never typed by hand.
- **Interaction.** Compare (side-by-side) and rotate representation (atom
  bars ↔ population strips). Any transition must preserve the supplied
  constraints visibly — marginals stay pinned on screen during the morph.
- **Boundary.** Must not imply either witness describes a real system;
  each panel carries "a feasible mathematical world" in its label.

## CC-VIS-003 — Pairwise Is Not Enough

- **Purpose.** E1's parity construction: identical singletons (0.5) and
  pairwise overlaps (0.25), different triple failure (0 vs 0.25).
- **Form.** Two three-circle fields with fixed singleton/pairwise readouts
  pinned at top; only the higher-order structure differs. The triple-event
  readout moves between its demonstrated endpoints.
- **Interaction.** Constrain (toggle even/odd parity world), with the
  pinned moments visually locked.
- **Boundary.** Marked SYNTHETIC on its face; never implies empirical
  prevalence in real stacks. Data source: the frozen study document CC-003
  binds — the figure fails its build check if the numbers disagree with
  the bound source.

## CC-VIS-004 — Assumption Architecture

- **Purpose.** Assumptions are load-bearing structures, not fine print.
- **Form.** Start from the full feasible interval; each added assumption
  (independence family, correlation cap, declared pairwise bound) renders
  as a named structural brace that visibly narrows the interval. The
  assumption's NAME stays on screen as long as its narrowing does.
- **Interaction.** Constrain / collapse; removing a brace re-widens.
- **Boundary.** Never implies a tighter interval is automatically more
  truthful — the caption states that narrowing is purchased with
  assumptions, and the price tag is the point.

## CC-VIS-005 — Claim Envelope (animated primitive)

- **Purpose.** One result traveling outward into its envelope: proposition
  → scope → support → challenge → test design → status → boundary →
  freshness.
- **Form.** The site's existing 8-field envelope grid, revealed as a
  sequence (reveal · lock); becomes a reusable primitive for module pages.
- **Boundary.** Only renders envelopes that exist in the registry; an
  envelope with absent fields shows the absence.

## GA-VIS-001 — Canonicalization Resolution

- **Purpose.** Ghost-Ark's kernel thesis: distinctions destroyed early are
  gone for every later consumer — and which loss matters depends on who
  consumes.
- **Form.** Pipeline `parse → canonicalize → digest → receipt → consumers`.
  Distinct inputs merge at parse/canonicalize; then the consumer set
  expands and a merged distinction that was irrelevant to consumer A
  becomes load-bearing for consumer B while the digest stays fixed.
- **Boundary.** Never implies signature failure caused the epistemic
  problem — the signature verifies throughout; that is the thesis. Source
  material only from ghost-ark at origin/main-reachable commits (the
  bound thesis at 98c90d82; figure data from the repo's figure-data.json
  idiom).

## AS-VIS-001 — Attestation Horizon · NOT PUBLICLY IMPLEMENTED

Decision 2026-08-23: not built. Private work does not enter the public claim
registry, and the mission rule stands — this concept ships publicly only when
there is a public repository and evidence that can support it. Module 004
carries the frozen question with explicit PLANNED stamps instead.

## Standing gates for any of these

1. Registry binding for every number shown; a `--check` that fails on
   divergence from the bound source (the verify_figures.py pattern).
2. User-driven, no autoplay; reduced-motion state epistemically neutral.
3. The named assumption/world label is part of the figure, not the caption.
4. Vendored assets only; zero external requests.
5. A non-claim in the caption: what the figure is not evidence of.
