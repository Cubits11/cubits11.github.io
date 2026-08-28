# cubits11.github.io

Personal site of **Pranav Bhave** — AI assurance research, cloud security,
claim governance. Live at [cubits11.github.io](https://cubits11.github.io/).

## Stack

Hand-written HTML and CSS, ~4.5 KB of vanilla JavaScript (theme toggle,
the feasible-worlds slider, scroll reveals, copy-email). No framework, no build step for the pages, no
analytics, no cookies. Fonts (Fraunces, Instrument Sans, Fragment Mono) are
self-hosted latin-subset woff2. The color system is sampled from the hero
photograph — every design decision and its rationale is in `DESIGN.md`.

The epistemic machinery is real, not rhetorical: `claims.yaml` (schema
v0.4) is the registry of every technical claim the site renders with an
evidence marker — with visibility, provenance, support role, evidential
status, and maturity as separate dimensions; a required falsifier condition
with a fixed `NARROW`/`REJECT`/`HOLD` consequence; a required
`forbidden_rescues` list (explicit `[]` when none applies); and structured
expected values that the reproduction script reads instead of hard-coding. `/ledger/` is
**generated** from it and drift-checked in CI; commit↔URL bindings are
validated and every bound commit is checked reachable from its
repository's default branch (one filtered clone per repo — GitHub serves
dangling objects, so a resolving URL proves nothing); executable review
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

Open a PR, pass the verification workflow, and merge through the protected
path. The workflow verifies the claim registry — field shape (including
falsifiers and forbidden rescues), support-link liveness, ledger coverage, and
a freshness gate that fails when a claim passes its review window (also run
weekly) — then deploys the exact verified static artifact and checks the live
checksum, sitemap, rendered ladder, and correction policy.

**One-time repository configuration.** In GitHub **Settings → Pages**, set
the publishing source to **GitHub Actions** and protect the `github-pages`
environment so only the default branch can deploy. Until that change is made,
branch-based Pages publishing remains a legacy, ungated deployment path; do
not describe the post-deploy smoke check as a preventive gate.

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
claims.yaml                 claim registry (schema v0.4) — the source of truth
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
