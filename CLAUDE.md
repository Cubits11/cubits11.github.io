# cubits11.github.io — working notes for Claude

A public claim registry and a measurement program about **guardrail
composition**: whether a stack of safety classifiers can be selected, or its
residual risk quoted, from per-guard marginals alone. The site's thesis is that
its own claims are mechanically prosecutable, so the conventions below are not
style — they are the product, and CI enforces them.

## Start here

```bash
python3 .claude/skills/evidence-ledger/ledger.py
```

Repo state in one screen: what has been measured, what is blocked on a human,
and how much protocol sits on top of how many rows. Cheaper and more honest
than reconstructing it from the program, the contract, the freeze and the last
report. See `.claude/skills/evidence-ledger/SKILL.md` for the two standing
rules — in particular: before writing another governing document, say the trade
out loud first.

## Before any commit

```bash
python3 scripts/verification_manifest.py
```

46 deterministic checks; exit 0 or the change is not ready.

## Conventions CI enforces

- **Generated pages are never hand-edited** — `/ledger/`, `/observatory/`,
  `/modules/*`, `/missing-column/*`, `/try/`, `/worldspace/`, `sitemap.xml`.
  Edit the source registry (`claims.yaml`, `modules.yaml`, `census.yaml`) and
  regenerate; nine `scripts/generate_*.py` have `--check` drift gates.
- **`claims.yaml` is schema v0.4.** Every claim needs a non-empty
  `falsifier.condition`, a fixed `NARROW|REJECT|HOLD` consequence, and a typed
  `forbidden_rescues` list (explicit `[]` is valid). A declared commit must be
  embedded in the support URL *and* reachable from its repo's default branch —
  a URL that resolves is not a binding. Each claim carries its own review
  window and fails when past it.
- **`verify_claims.py` exit 2 is not a pass.** It means a check could not be
  evaluated because its source was unreachable. A gate must not proceed on an
  unknown, and neither the log nor the ledger may record it as a refutation.
- **Local sha triggers.** Editing a file a claim pins by `sha256` fails the
  registry until the claim is re-pinned and `last_reviewed` bumped. Check
  `claims.yaml` before editing `DESIGN.md`, `scripts/verify_claims.py`, or
  anything else with a `local_content_change` trigger.
- **Figure numbers** are re-derived from stated constants in
  `scripts/verify_figures.py` to 1e-9.

## Voice

First person, declarative. No adjectives about the work itself. Every sentence
checkable. Non-claims stated explicitly — what a result does *not* license is
part of the result. Colors are semantic (evidence-cyan / review-amber /
invalid-red; gold is identity only) and state is never encoded by color alone.

## Hard boundaries

- **Nothing loads model weights on this host.** It is an 8 GB M1 and the
  adapters refuse. Collection runs only on the owner's authorized 24 GB box.
- **External actions are the owner's hand only** — dispatching asks, opening
  issues, accepting model licenses. Prepare them; never send them.
- **A threshold, estimator, hypothesis or criterion changed after outcomes are
  visible is a forbidden rescue.** The affected result is not reported. This is
  the one rule that voids work retroactively, so treat any post-hoc edit to a
  frozen file as a stop-and-ask.
- `ghost-ark` is read-only from here.

## Where things live

`claims.yaml` `claims_history.yaml` registry and its declared transitions ·
`census.yaml` the 20-row survey of who publishes joint outcomes ·
`experiments/e2/` the live measurement program (freeze, prereg, instrument) ·
`ARTIFACTS/12-WEEK-PROGRAM.md` the governing plan and its kill conditions ·
`distribution/` external asks and the qualified-outcome ledger ·
`scripts/` generators and verifiers · `docs/` estimands and cut decisions.

Work on `claude/<topic>` branches and merge to `main`.
