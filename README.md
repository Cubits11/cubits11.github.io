# cubits11.github.io

Personal site of **Pranav Bhave** — AI assurance research, cloud security,
claim governance. Live at [cubits11.github.io](https://cubits11.github.io/).

## Reproduce the claim in under a minute

The headline result is one command. It downloads a hash-pinned public file,
recomputes the joint statistics from it, and asserts them against the number
registered in `claims.yaml` — so a mismatch fails loudly instead of quietly
re-deriving a new answer.

```bash
python3 -m pip install -r requirements.txt && python3 scripts/reanalyze_bells_subset.py
```

You should see `MC-002 reproduced` and a joint miss of `9/82 = 11.0%` against
an independence plug-in of `3.5%` — a ratio of `3.14x`. **What that is:**
counting arithmetic on 82 author-selected prompts at five vendors' released
binary verdicts. **What it is not:** a population estimate, a claim about any
vendor's product, or evidence that stacks are unsafe.

Then price what the marginals alone leave undetermined:

```bash
python3 scripts/identification.py --bells
```

The five published miss rates pin the all-miss rate only to `[0.00%, 14.63%]`
— a width equal to the best single guard's miss rate. Independence names
`3.49%`, a point inside that set it was never entitled to. The registered
value is `10.98%`. On the benign side the same marginals pin the stack's
flag rate to `[20.00%, 50.00%]`: **a floor that is strictly positive.** It
actually lands at `38.00%`. From published marginals alone one can prove this
stack burdens legitimate users, and cannot prove it catches a single harmful
item its best member would have missed.

To re-run every gate the way CI does, from a clean clone of a given commit:

```bash
python3 scripts/verify_clean_clone.py --commit HEAD
```

**To falsify any of this:** change a byte of the pinned upstream file and the
hash check fails; change a registered count and the reproduction fails; change
a generated page by hand and the drift check fails. Corrections are logged at
[/corrections/](https://cubits11.github.io/corrections/), same calendar day.

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

## MJGD v1

[Minimum Joint Guardrail Disclosure v1](docs/MJGD_V1.md) is a
machine-readable disclosure schema for a declared multi-guard evaluation. Its
validator recomputes only complete static full-exposure outcomes and complete
positive-set aggregate pattern tables, returns identified sets for marginals, and holds
routes and missing cells rather than guessing. The JSON Schema is structural;
the CLI performs semantic conformance checks. MJGD is a schema, not a safety
standard or an adoption claim.

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
stack-study/                browser-local study preflight; static / route / adaptive scopes stay distinct
claims.yaml                 claim registry (schema v0.4) — the source of truth
modules.yaml                module registry — questions, status, bindings
scripts/generate_ledger.py  registry → ledger renderer (CI drift-checks it)
scripts/generate_modules.py module registry → module pages (CI drift-checks)
scripts/generate_observatory.py  claims.yaml → observatory (CI drift-checks)
scripts/verify_claims.py    registry verifier: bindings, triggers, freshness
scripts/verify_figures.py   figure geometry assertions (Fig. 02 + essay)
scripts/verify_frontend.py  static frontend structure + local-only preflight gate
scripts/reproduce_cc001.py  clean-clone reproduction of CC-001 + CC-004
scripts/validate_mjgd.py    MJGD v1 packet validator + fixture/refusal tests
schemas/mjgd-v1.schema.json machine-readable MJGD v1 contract
fixtures/mjgd-v1/           illustrative complete, aggregate, marginal, route, and hold packets
docs/MJGD_V1.md             MJGD v1 semantics, replay commands, and non-claims
404.html                    not-found page
assets/                     shared stylesheet, self-hosted fonts, images
DESIGN.md                   design-decision ledger + changelogs + field-artifact notes
```

Content © Pranav Bhave. Code (HTML/CSS/JS) may be reused with attribution.
