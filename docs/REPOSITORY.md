# Repository reference

Everything the README's front door leaves out: the workbench, the site stack,
local serving, the disclosure schema, deployment, layout and scheduled jobs.
The research argument is in [`RESEARCH.md`](../RESEARCH.md); the reproduction
lanes are in the [README](../README.md#reproduce-the-claims).

## The workbench and the experiment surface

[/explore/](https://cubits11.github.io/explore/) — a probability workbench and
entrance to the existing films and evidence. Change two marginal miss rates,
inspect their compatible joint distributions, distinguish an independence
assumption from a hypothetical joint constraint, and see contradictory inputs
produce an empty set. These are illustrative constructions, not measurements.
The original fixed-item instrument remains at `/worldspace/`.

The new workbench uses `assets/world.js` and the site's existing fonts and
colour system. No additional browser dependency. Numerical and public-page
discovery regressions can be checked with:

```bash
node --test tests/world.test.cjs
python3 tests/test_public_discovery.py
```

These checks supplement the release manifest. The workbench remains readable
without JavaScript and responds to keyboard input; motion respects the device
preference. Comprehension and audience impact have not been measured.

[cubits11.github.io/try](https://cubits11.github.io/try/) — three experiments,
each printed with its command, expected final line, falsifier and non-claim
before you run anything. Don't trust the graphic; reproduce it.

```bash
git clone https://github.com/Cubits11/cubits11.github.io.git && cd cubits11.github.io
python3 scripts/try_same_scores.py      # 60 s, standard library: two worlds from the same two scores
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt   # PyYAML, for the next line only
python3 scripts/reanalyze_bells_subset.py   # 3 min, network: a released file recomputed under a hash
python3 scripts/try_audit.py            # 15 min, standard library: the disclosure test on an evaluation you know
```

Or enter the same proof as an instrument before you run anything:
[cubits11.github.io/worldspace](https://cubits11.github.io/worldspace/) —
predict, then move the misses yourself; the two scores never move while the
number both miss runs the whole interval. Available, not yet validated with
users (`worldspace/LEDGER.md`).

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
Since 2026-09-02 a claim's commitment (proposition, scope, falsifier,
forbidden rescues, non-claims, expected values) can change only by appending a
declared transition to `claims_history.yaml`; `scripts/claims_history.py
verify` fails any undeclared change, any edit to accepted history, and any
re-minted baseline, from that genesis forward — it protected nothing before
it existed, and it does not bind an actor who can change the verifier, the
workflow, or the history in the same act.

## Run locally

```bash
python3 -m http.server 4173
```

Then open http://localhost:4173.

## MJGD v1

[Minimum Joint Guardrail Disclosure v1](MJGD_V1.md) is a
machine-readable disclosure schema for a declared multi-guard evaluation. Its
validator recomputes only complete static full-exposure outcomes and complete
positive-set aggregate pattern tables, returns identified sets for marginals, and holds
routes and missing cells rather than guessing. The JSON Schema is structural;
the CLI performs semantic conformance checks. MJGD is a schema, not a safety
standard or an adoption claim.

## Route receipt stub

[examples/route-receipt/](../examples/route-receipt/) is the separate, portable
two-file receipt for a declared item-level route. It emits only policy actions
from a direct route trace and returns HOLD for a post-hoc static
reconstruction. It is a template, not an adoption claim or a deployment
certificate.

## Deploy & verification

Open a PR, pass the verification workflow, and merge through the reviewed
path. The workflow verifies the claim registry — field shape (including
falsifiers and forbidden rescues), support-link liveness, ledger coverage, and
a freshness gate that fails when a claim passes its review window (also run
weekly) — then deploys the exact verified static artifact and checks the live
checksum, sitemap, rendered ladder, and correction policy.

**Configured deployment control.** GitHub Pages publishes through **GitHub
Actions**, and the `github-pages` environment permits only the default branch.
The branch-based Pages publisher is disabled: deployment waits for the claim
and reproduction gates, then the workflow smoke-tests the live artifact.

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
scripts/reproduce_cc001.py  clean-clone reproduction of CC-001 + CC-004 (disposable venv)
try/                        the experiment surface — GENERATED from distribution/experiments.yaml
scripts/try_same_scores.py  TRY-A: two worlds from the same marginals, standard library
scripts/try_audit.py        TRY-C: the disclosure test on an evaluation you know
distribution/               outcomes ledger, experiments, launch units, dossiers, external-events procedure
contrib/                    prepared joint-statistics reporters for two public harnesses (patches, unsent)
films/                      six deterministic evidence-bound films (see films/README.md)
scripts/validate_mjgd.py    MJGD v1 packet validator + fixture/refusal tests
schemas/mjgd-v1.schema.json MJGD v1 schema documentation (validator is the contract)
fixtures/mjgd-v1/           illustrative complete, aggregate, marginal, route, and hold packets
examples/stack-joint/       portable static-OR CSV receipt stub + fixture
docs/MJGD_V1.md             MJGD v1 semantics, replay commands, and non-claims
404.html                    not-found page
assets/                     shared stylesheet, self-hosted fonts, images
DESIGN.md                   design-decision ledger + changelogs + field-artifact notes
```

Content © Pranav Bhave. Code (HTML/CSS/JS) may be reused with attribution.

## Scheduled feedback and release updates

The existing local schedules record repository state daily and collect distribution
observations every four hours. Missing days and missed observation windows remain
missing; the jobs never interpolate evidence. Both jobs share a repository lock.
They prefer `.venv/bin/python3`; create that environment with Python 3.12 or newer
and install `requirements.txt` before enabling the schedules. `CUBITS11_PYTHON`
can select another environment explicitly.

A cycle starting from clean, synchronized `main` runs the verification manifest,
commits only its permitted outputs on a `claude/cycle-*` branch, and opens a pull
request. GitHub auto-merge uses a merge commit and remains subject to required
checks and review rules. A failed API call leaves the branch available for recovery;
a failed check retains the observations without publishing them. Logs live in
`_private/cron/`. No cycle dispatches a new outreach message.

This feedback loop records observations and tests known failures. It does not
autonomously change scientific criteria, promote a hypothesis, or accept a
contradicted result. Deployment checks compare the public pages, primary films,
posters and claim metadata with the verified revision, so an older page returning
HTTP 200 cannot stand in for the release.
