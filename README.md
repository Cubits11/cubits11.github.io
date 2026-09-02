# cubits11.github.io

Personal site of **Pranav Bhave** — AI Assurance · Security Engineering ·
Evidence Systems; cloud security,
claim governance. Live at [cubits11.github.io](https://cubits11.github.io/).

## Try it first

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

A different result is the most useful thing you can send:
[file it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=reproduction.yml).
A counterexample, a benchmark the census missed, or joint outcomes you can
provide: [bring it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=counterexample.yml).
Qualified outcomes — reproductions, corrections, releases, merged patches,
cold runs by people who are not the author — are recorded in
`distribution/outcomes.yaml` and rendered on `/try/`; zero is shown as zero.

## Reproduce the claims

### First: MC-001 — the Missing Column census

The homepage begins with this bounded reporting claim: among 20 public
guardrail evaluations meeting the frozen criteria, 14 establish a shared item
set and common event definition, and 5 preserve a declared joint-evidence
artifact. The 14 is a shared-basis rung, not proof of matched operating
thresholds or full exposure; the stricter ladder is 14/12/0.

```bash
python3 -m pip install -r requirements.txt && python3 scripts/verify_census.py --counts
```

You should see `MC-001 expected counts match the census (N/M/K 20/14/5)` and
`MC-001 M ladder matches the census (14/12/0)`, followed by `Census verified`.
This is a source-bound census of reporting, not a vendor ranking, a population
safety estimate, or a claim that any stack is safe or unsafe. Change a row,
registered count, or frozen-criteria history and the verifier fails.

### Second: MC-004 — released verdicts, recomputed

The least favorable number comes first. On the release's pinned `full_run`
image items, the static OR of the harness-normalized native `unsafe` bits is
1 for `250/250` benign-labelled images and `200/200` harmful-labelled images.
Llama Guard 3 Vision has a 1-bit on every released image item in that
directory, so the OR inherits that column. The harness's fixed block action
makes this a valid counterfactual harness-block calculation on those pinned
rows — not a deployed route, a shared-event catch claim, a model law, or an
independent replication of the models.

```bash
python3 -m pip install -r requirements.txt && python3 scripts/reanalyze_msbench.py
```

The script verifies eight source hashes before it counts. Its scope, expected
stdout, pinned source, and correction route are on
[/missing-column/reproduce/](https://cubits11.github.io/missing-column/reproduce/).

### Third: MC-002 — a five-guard receipt

This command recomputes a joint miss from five vendors' released binary
verdicts, and asserts it against the registered value so a mismatch fails
loudly instead of quietly re-deriving a new answer.

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

`scripts/reproduce_cc001.py` (CC-001 and CC-004, the bound kernel) clones
cc-framework at its bound commit and installs it into a disposable virtual
environment inside the temporary clone, so it runs on externally managed
Pythons (Homebrew, Debian, Fedora) without touching your interpreter:

```bash
python3 scripts/reproduce_cc001.py
```

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

## Route receipt stub

[examples/route-receipt/](examples/route-receipt/) is the separate, portable
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
