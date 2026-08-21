# cubits11.github.io

Personal site of **Pranav Bhave** — AI assurance research, cloud security,
claim governance. Live at [cubits11.github.io](https://cubits11.github.io/).

## Stack

Hand-written HTML and CSS, ~3 KB of vanilla JavaScript (theme toggle,
scroll reveals, copy-email). No framework, no build step for the pages, no
analytics, no cookies. Fonts (Fraunces, Instrument Sans, Fragment Mono) are
self-hosted latin-subset woff2. The color system is sampled from the hero
photograph — every design decision and its rationale is in `DESIGN.md`.

The epistemic machinery is real, not rhetorical: `claims.yaml` is the
registry of every technical claim the site renders with an evidence marker
— proposition, scope, support bound to immutable commits, provenance,
status, review triggers, non-claims. `/ledger/` renders it; CI enforces it.

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
index.html                 the site (styles and script inline)
essays/when-marginals-are-not-enough/   flagship case study (real kernel output)
ledger/                    evidence ledger, rendered from claims.yaml
resume/                    web résumé with 90-second overview
claims.yaml                claim registry — the source of truth
scripts/verify_claims.py   registry verifier (runs in CI)
404.html                   not-found page
assets/                    self-hosted fonts, portrait derivatives, OG image
DESIGN.md                  design-decision ledger + changelog + field-artifact notes
```

Content © Pranav Bhave. Code (HTML/CSS/JS) may be reused with attribution.
