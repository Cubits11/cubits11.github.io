# cubits11.github.io

Personal site of **Pranav Bhave** — AI assurance research, cloud security,
claim governance. Live at [cubits11.github.io](https://cubits11.github.io/).

## Stack

Hand-written HTML and CSS, ~3 KB of vanilla JavaScript (theme toggle,
scroll reveals, copy-email). No framework, no build step for the pages, no
analytics, no cookies. Fonts (Fraunces, Instrument Sans, Fragment Mono) are
self-hosted latin-subset woff2. The color system is sampled from the hero
photograph — every design decision and its rationale is in `DESIGN.md`.

The epistemic machinery is real, not rhetorical: `claims.yaml` (schema
v0.3) is the registry of every technical claim the site renders with an
evidence marker — with visibility, provenance, support role, evidential
status, and maturity as separate dimensions, and structured expected values
that the reproduction script reads instead of hard-coding. `/ledger/` is
**generated** from it and drift-checked in CI; commit↔URL bindings are
validated (and must point at ref-reachable commits); executable review
triggers watch the bound evidence upstream and fail the build when it
changes; figure geometry is asserted by `scripts/verify_figures.py`; and
CC-001 + CC-004 (bounds and endpoint witnesses) are re-reproduced from a
clean clone on every push and weekly. What v0.2 merely asserted is
documented in
[Noetic Log 001](https://cubits11.github.io/notes/noetic-log-001/).

## Run locally

```bash
python3 -m http.server 4173
```

Then open http://localhost:4173.

## Deploy & verification

Push to `main`; GitHub Pages serves the repository root (`.nojekyll`
disables Jekyll). CI (`.github/workflows/verify.yml`) then verifies the
claim registry — field shape, support-link liveness, ledger coverage, and a
freshness gate that fails when a claim passes its review window (also run
weekly) — and collects report-only Lighthouse artifacts for the live site.

## Layout

```
index.html                  the record's front page (feasible-worlds instrument inline)
essays/when-marginals-are-not-enough/   flagship case study (real kernel output)
modules/                    module system — GENERATED from modules.yaml
observatory/                claim observatory — GENERATED from claims.yaml
ledger/                     evidence ledger — GENERATED from claims.yaml
writing/  archive/  now/    writing index · intellectual lineage · current work
notes/noetic-log-001/       public audit log: what v0.2 pretended to implement
resume/                     web résumé with 90-second overview
claims.yaml                 claim registry (schema v0.3) — the source of truth
modules.yaml                module registry — questions, status, bindings
scripts/generate_ledger.py  registry → ledger renderer (CI drift-checks it)
scripts/generate_modules.py module registry → module pages (CI drift-checks)
scripts/generate_observatory.py  claims.yaml → observatory (CI drift-checks)
scripts/verify_claims.py    registry verifier: bindings, triggers, freshness
scripts/verify_figures.py   figure geometry assertions (Fig. 02 + essay)
scripts/reproduce_cc001.py  clean-clone reproduction of CC-001 + CC-004
404.html                    not-found page
assets/                     shared stylesheet, self-hosted fonts, images
DESIGN.md                   design-decision ledger + changelogs + field-artifact notes
```

Content © Pranav Bhave. Code (HTML/CSS/JS) may be reused with attribution.
