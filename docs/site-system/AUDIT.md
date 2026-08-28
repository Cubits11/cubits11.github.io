# Evidence Observatory — reconnaissance audit

Date: 2026-08-23. Conducted before any redesign work, per the mission's Phase 0
gate. Four mutually exclusive audit lanes (claims/CI · information architecture ·
visual assets · build/accessibility) were run over the local checkouts listed
below; every finding here carries the evidence its lane recorded. Working state
during the audit lived at `/tmp/cubits-site-audit/` (ephemeral); this document
is the durable record.

## Ground truth at audit time

| Repo | State | Role |
| --- | --- | --- |
| cubits11.github.io | main@4862190, clean, CI green (last push run 2026-08-21) | primary target |
| cc-framework | main@167aa1e, clean, CI green (2026-08-22) | secondary target |
| ghost-ark | lab checkout, dirty (47 paths), branch 0 ahead / 1 behind origin/main@98c90d8 | read-only source |
| noetic-stair | local branch `codex/reg-001-evidence-readiness` is 1 ahead of origin/main and **not pushed** | read-only, not yet a public surface |
| ghost-visualizer | not local; inspected remotely | link-source-only (see V3) |
| Assay | private subproject with an IP-confidentiality evaluation | PRIVATE — no public claim expansion |

Registry health: all 8 claims fresh (windows expire 2026-12-18 at the
earliest); every executable trigger verified quiet on 2026-08-23 by re-running
CI's own comparisons; `DESIGN.md` sha256 matches SITE-001's recorded hash.

## Findings that gate the redesign

### P0-1 · CC-001 is bound to garbage-collectable history, and the essay's own expiry condition is met

`claims.yaml:48` binds commit `21f5ff68…`. That commit is unreachable from
every branch and tag of cc-framework (`git cat-file -t` → bad object in a full
clone; a bare probe clone's complete ref set does not contain it; GitHub API
`compare/main...21f5ff68` → `diverged`). It survives only as a dangling GitHub
object (raw + commit page still HTTP 200) and in the local `cc-framework-broken`
recovery copy — i.e. the flagship "immutable binding" is anchored to a
pre-rewrite history that GitHub could garbage-collect, which would 404 the
support URL and fail three CI gates at once (URL liveness, trigger fetch,
`reproduce_cc001.py` checkout).

Compounding it: the essay's envelope says freshness "expires on kernel change
**or when the default branch advances beyond the binding**"
(`essays/when-marginals-are-not-enough/index.html:197`). The default branch
*has* advanced (18 ahead), so the page's own expiry condition is met while its
status still renders "Supported within scope."

The kernel file at the bound ref is byte-identical to current HEAD
(sha256 `33937cae…`), so this is a stale *pin*, not a stale *result*.

**Resolution:** re-execute the kernel claim at a reachable current-main commit,
re-bind CC-001 (support URL/commit + trigger `bound_ref`), update the essay's
recorded-output commit line, align the essay's freshness wording with the
registry's actual executable trigger, bump `last_reviewed`, regenerate the
ledger. Adopt the rule: **only bind commits reachable from a protected ref.**

### P0-2 · DESIGN.md asserts a Fig-02 geometry check that does not exist

`DESIGN.md:330-336` states the bounds figure's geometry is asserted "at build
time: overlap area must equal q to within 1e-9 in all eleven frames." No such
checker exists anywhere in `scripts/` or `.github/` (verified by grep); the
11-frame SVG is hand-inlined. A public document bound as SITE-001 evidence
asserts a mechanism the repository does not contain — precisely the
"asserted mechanics it did not have" class that DESIGN.md's own v0.3 changelog
documents correcting.

**Resolution:** make the sentence true — commit `scripts/verify_figures.py`
that parses the frames and asserts the geometry, wire it into `verify.yml`.

### P1-3 · GCE renders an evidence-marked claim with no registry entry, presented beside current theory it is superseded by

`index.html:529-533` gives GCE a solid-dot evidence chip and a technical claim
("toggle guardrails and watch composed behavior diverge from intuition") while
the ledger opens with "Every technical claim the site renders with an evidence
marker, in envelope form" — and GCE has no registry entry. Meanwhile
cc-framework explicitly classifies GCE's framing as superseded: "Older names
such as `cc_max`, `cc_rel`, `delta_add`, and `delta_mult` are legacy/deprecated
compatibility surfaces. They should not be presented as the front-door theory"
(README:473-475; deprecation table in `docs/theory/metric_taxonomy.md`). GCE
also escapes the GitHub-profile legend (unlabeled About text; the legend's
"2025 or earlier" fallback may not cover it).

**Resolution:** move GCE to the Archive as intellectual lineage with an explicit
succession story; register it (GCE-001, superseded/historical) so its marker is
covered; recommend labeling its GitHub About like its sibling repos.

### P1-4 · Evidence-cards display contract (constraint on the Observatory)

cc-framework ships `evidence-cards/site-evidence-manifest.v1.json` — literally
built for a site surface — whose own non-claims forbid the obvious rendering:
"Counts are reported per label. There is no aggregate score, and any surface
that computes one from this file is misusing it." / "A card with verdict
'not-run' has no result. It must not be displayed as passing, pending, or
healthy." All 8 cards are currently `verdict: not-run`, `publication_state:
draft`. **Acceptance criteria for any observatory surface:** no meters, no
aggregates, no health language; verdict / evidence_state / publication_state
rendered as three orthogonal labels using the manifest's own `label_meanings`.
(v1 of the site Observatory renders the site's own `claims.yaml` instead and
links out to the cards.)

### P1-5 · Six diverging copies of the design tokens

Every page carries its own inline `:root` block; three call the signal color
`--gold`, three call it `--accent`; only index carries `--noise-opacity`/`--ease`.
Extending the tokens six times over is the cc-framework drift problem in
miniature. **Resolution:** one shared stylesheet (`assets/site.css`) as the
single token + primitive source; pages keep only page-specific styles inline.
This supersedes part of DESIGN.md D2 (zero-build, styles inline) under D2's own
revisit clause — the site is growing past ~3 pages — and must be recorded in
the design ledger.

### P1-6 · No deploy gate

GitHub Pages publishes on push to main regardless of `verify.yml` results
(the workflow itself notes Pages deploys asynchronously). A bad push goes live
first and turns red after. **Runbook rule:** the full local verification
sequence (below) runs before any push; pushing main is publishing.

### Notable P2/P3 (fold into implementation)

- **GA-001 paraphrase lag** — the bound thesis has refined its claim: soundness
  is ternary (`Sound(C, Σ, P)`), the kernel is a property of the whole
  `parse → canonicalize → digest` **pipeline**, not of the canonicalizer, and
  "C2 stands as a statement about what is possible and does not stand as a
  statement about what is prevalent." Reword GA-001 at re-review; the trigger
  is quiet so CI would never catch this class.
- **Two theorem ledgers in cc-framework** — the site must link
  `docs/theory/theorem_ledger.md` (T1…T8; the file the evidence cards pin)
  exclusively, never `docs/research/THEOREM_LEDGER.md`.
- **"Last owner review" is derived nowhere** — ledger header and index footer
  say 2026-08-20 while SITE-001 was reviewed 2026-08-21. Generator should derive
  the display date; the registry field gets bumped by this redesign's re-review.
- **Hand-written registry facts on index** ("Registry v0.2 · 8 claims") are
  covered by no check; a 9th claim silently falsifies the homepage. Add a
  cross-check to `verify_claims.py`.
- **The stamp primitive is broken** — `.stamp` styling is scoped to
  `.pcard-empty`, which no longer exists in the markup; the flagship Method
  stamp renders as plain text.
- **DESIGN.md D1/D4 are stale against shipped v0.3** (D1 describes the result
  slot as empty/untested; D4's hexes predate the v0.3 palette). Add supersession
  notes; DESIGN.md warns itself that "showing stale receipts would be worse
  than showing none."
- **Fig-02 reduced-motion state shows the independence frame** — the one world
  the figure exists to warn against. The redesign's interactive object must
  default its static state to the *interval*, not the point.
- **Fig-02 autoplays infinitely** (WCAG 2.2.2 wants a pause control for >5s
  motion). Making the object user-driven (slider) removes autoplay entirely.
- **SVG text illegible at 320px** (~3.7px effective); wrap wide figures in
  `overflow-x:auto` containers with a min-width.
- **Head inconsistency across pages** (theme-color only on index; OG missing on
  ledger/resume; JSON-LD only on index). Standardize during the rebuild.
- **"Before You See It" chip is the only unpinned evidence URL** (`tree/main/…`).
  Pin it.
- **sitemap `lastmod` stale**; regenerate with the new routes.
- **Hover-only palette receipts** (swatch hexes in `title=` attributes);
  surface visibly.
- **noetic-stair's REG-001 material is unpushed** — nothing on the site may
  reference it until it exists on origin; NS stays off the public surface this
  round. Its CC pin (`source-lock.json` → cc@167aa1ee, deliberate-repin
  semantics) must never be described as "continuously in sync."
- **ghost-visualizer's own QA verdict** ("8.2/10 for private serious-contact
  demo quality… still not a public flagship video… use as a private credibility
  artifact") forbids using its media as flagship visuals; the site's current
  link-source-only treatment is correct and must survive the redesign.
- **ghost-ark quoting rule** — the lab checkout is dirty; the site quotes
  ghost-ark only from origin/main@98c90d8 (the bound thesis is byte-identical
  local/bound/remote today).
- **cc-framework regression surface for the port** — editing any of the 18
  manifest-referenced files (README included) requires regenerating
  `evidence-cards/` (`build_evidence_cards.py`, CI `--check`-gated); any
  `docs/**` change triggers `mkdocs build --strict` on Python 3.10–3.13.

## Public ontology (Phase 1 classification)

| Project | Class | Basis |
| --- | --- | --- |
| CC-Framework | CURRENT RESEARCH | E0 established; E1 complete (decision: Narrow); E2 frozen untested; CC-001/CC-002 registered |
| Ghost-Ark | CURRENT RESEARCH | active lab repo; GA-001; falsifier F2 CONFIRMED 2026-08-12; F3 open |
| This site (field artifact P₀) | CURRENT INSTRUMENT | claims.yaml + generated ledger + CI prosecution; comprehension hypothesis untested |
| Ghost Visualizer | CURRENT INSTRUMENT (private-demo bound) | GV-001; its own VIS-001 score caps public use |
| Before You See It (cc-framework asset) | CURRENT INSTRUMENT | finished deterministic film; ILLUSTRATION-stamp honesty mechanic |
| Module 004 / attestation boundary | PLANNED | public question only; no private-project envelope is rendered |
| Assay | PRIVATE / UNTESTED | no public registry entry; IP-confidentiality posture; no expansion |
| GCE | SUPERSEDED | front-door coefficient framing deprecated by cc-framework metric taxonomy |
| guardrails-cc, ghost-guardrail-composer, guardrail-comp-theory | SUPERSEDED | profile-labeled "[SUPERSEDED by cc-framework]" |
| cubits-os, resonance-theory, ghost-protocol family, ghost_secure_portfolio | HISTORICAL | profile-labeled |
| noetic-stair | not yet public surface | REG-001 evidence-readiness work unpushed |

## Decisions

1. **No pushes.** Site deploys on push; everything stops at PR-ready topic
   branches (`feat/evidence-observatory`, `feat/web-system-port`).
2. **Extend the registry idiom, don't replace it.** `modules.yaml` →
   `scripts/generate_modules.py` → generated pages → `--check` drift gate in
   `verify.yml`, exactly parallel to `claims.yaml` → `generate_ledger.py`.
   Structured expected values live in registry data, not in reproducer code
   (the `reproduce_cc001.py` lesson).
3. **All existing URLs keep resolving.** The redesign adds routes
   (`/modules/…`, `/observatory/`, `/writing/`, `/now/`, `/archive/`) and
   rewrites index in place; nothing moves, so no redirects are needed. The
   preserve-list is the audit's §3 link surface (5 pages + 8 ledger anchors +
   `claims.yaml`, `robots.txt`, `sitemap.xml`, `assets/img/og.jpg`).
4. **Palette: adopt cc-framework's own observatory color law as the site's
   semantic state layer** — evidence/replayable = spectral cyan, review
   required = amber, invalidation/expiry = red, unknown/inactive = graphite —
   on the existing photo-derived carbon field and bone ink, with gold retained
   as the identity accent. This is a port of an in-repo standard
   (`visual_identity/claim_observatory/README.md`: "Cyan/white light marks
   evidence and replayable structure. Amber marks required review. Red is
   reserved for expiration/invalidation."), not an invented brand. Green loses
   all semantic duty. Every new pair contrast-computed before shipping.
5. **Media is vendored, never hotlinked.** The site's zero-external-request
   property is load-bearing; cc-framework figures are copied into
   `assets/`, captioned with their source repo + pinned revision.
6. **The epistemic-machine compression gets a manifest + test in cc-framework**
   (five cinematic panels ↔ six logical rows; the bridge caption already exists
   at README:132 — the manifest makes it unbreakable).
7. **New public claims are registered or not made.** Planned additions:
   CC-003 (E1 pairwise result, bound to the study doc), CC-004 (endpoint
   witnesses, machine-verified by extending `reproduce_cc001.py`),
   GCE-001 (supersession record), SITE-002 (the freshness gate itself,
   hash-bound to `verify_claims.py`), plus re-reviews of CC-001 and GA-001.
   Every module page states status honestly; planned modules show
   `PUBLIC EVIDENCE — NONE YET` as a feature.

## Verification surface (must pass before any push)

```
python3 scripts/verify_claims.py            # registry, bindings, triggers, freshness, coverage
python3 scripts/generate_ledger.py --check  # ledger drift
python3 scripts/generate_modules.py --check # modules drift (new)
python3 scripts/generate_observatory.py --check  # observatory drift (new)
python3 scripts/verify_figures.py           # Fig-02 geometry (new; makes DESIGN.md true)
python3 scripts/reproduce_cc001.py          # clean-clone kernel reproduction (network + pip)
```

cc-framework (for the port branch): `make test-kernel` unaffected-but-run;
targeted `pytest` for the new manifest test; `make docs` if `docs/**` changed;
`build_evidence_cards.py --check` if any manifest-referenced file changed.

## Adversarial review outcome (Phase 16, 2026-08-23)

An independent hostile reviewer was charged with proving the redesign
creates an impression stronger than its evidence. Verdict: the numeric
core survived intact — every recomputed value (all eleven frame
geometries, E1's parity numbers, twelve WCAG ratios, byte budgets, poster
text vs manifest, ghost-ark quotes at the bound commit) verified exactly.
Twelve findings were reported; **all twelve were accepted and fixed**, no
disagreements retained:

- **P0** — module 005's Result slot inflated the machinery's track record
  (five→three re-reviews; "already fired" with no public firing; the
  stranded binding credited to triggers that were structurally blind to
  it). Rewritten to the exact record.
- **P1×3** — the ref-reachability rule was stated but unenforced (now
  enforced: `verify_claims.py` clones each bound repo bare/filtered and
  requires every bound commit to be an ancestor of the default branch);
  the observatory painted its cyan evidence rail on attested capsules
  (attested capsules now carry a dashed neutral rail, and maturity renders
  on every capsule); the masthead over-promised coverage ("every technical
  claim" → "every marked claim") and the E2 preregistration facts were the
  most rhetorically valuable unbound claims on the page (now registered as
  CC-005, chipped from the question strip and /now/).
- **P2×4 / P3×4** — "Audited twice" → "Self-audited twice"; the amber
  legend broadened to its real law and non-conforming amber uses recolored;
  ghost-ark's F3 restored to its actual subject (consumer-set stability)
  with the incidence gap attributed to the thesis; GV-001's edit got its
  review-date bump; README's JS figure updated; "expires" → "comes due";
  the planned module's "frozen" stamp downgraded to "stated"; capsules now
  show maturity (GCE reads "Superseded" at scan level).

The review's could-not-break list (16 attack lines, each checked rather
than skipped) is retained verbatim in the session's review artifact and
summarized here as the strongest available evidence that the remaining
surface holds.

## Unresolved, carried forward

- Which ref historically contained `21f5ff68` and GitHub's retention horizon —
  unknowable locally; mitigated by re-binding.
- ghost-visualizer bound commit `3fbe3efc` branch-membership (repo not local;
  README hash equality verified remotely).
- Live Pages settings (branch-serving inferred from repo contents + README).
- The Fig-02 generator with the original 1e-9 assertion, if it ever existed
  outside the repo — replaced by a committed checker either way.
