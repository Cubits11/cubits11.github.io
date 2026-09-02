# films/ — the cinematic research laboratory

Deterministic, evidence-bound, code-generated films about the record's
central epistemic operations. Not decoration: each film animates an operation
(fixed marginals with moving overlap; a union identifying a count; pairs
failing to identify a triple; a falsifier firing; a seal reaching the edge of
what it proves) and binds every number it shows to the registry that owns it.

```text
A story may start a question. Evidence must finish the answer.
```

## Laws

- **Truth contract.** Every object on screen is OBSERVED, DERIVED, PROVED,
  CONSTRUCTED, ILLUSTRATIVE, UNKNOWN, REGISTRY or DOCUMENT, and the frame
  says which (the ledger tag). A film never implies a bound is a frequency, a
  construction is data, a receipt proves safety, or a bounded search proves
  universal absence. If the evidence cannot license an impressive statement,
  the uncertainty is what gets staged.
- **Binding.** Films never retype a research number. `scripts/films/bind_facts.py`
  derives `films/data/facts.json` from `claims.yaml` (the same `expected`
  blocks the reproduction scripts assert), `census.yaml` (the same
  `compute_counts`), and a few constructions whose every constraint is
  asserted before the file is written. `--check` fails when the registries
  move, so a stale film cannot survive a registry edit unnoticed.
- **Storage.** No models, no stock assets, no texture packs. Everything is
  procedural: Canvas 2D in the installed Chrome, driven frame by frame.
  Frames are written outside the repository and deleted after encoding; the
  tree keeps sources, manifests, posters, review stills, contact sheets,
  receipts and compressed H.264 masters.
- **Creative.** No particles, gradients-for-mood, glow, glassmorphism,
  dashboards or wordmark lockups. The site's own type (Fraunces, Instrument
  Sans, Fragment Mono) and its semantic colour law: evidence cyan, review
  amber, invalid red, graphite unknown, gold as locator only — never a state
  by colour alone.

## Layout

```text
films/
  README.md            this file
  SLATE.md             GENERATED from slate.yaml — 30 scored concepts + the killed list
  LEDGER.md            the experiment ledger: predictions, observations, changed variables
  slate.yaml           source of truth for the slate
  data/facts.json      GENERATED — every number a film may show, with its epistemic kind
  lib/film.js          the runtime: seek(t), layout, typography with overflow accounting
  lib/tokens.css       site tokens and @font-face for the vendored faces
  <slug>/film.html     the film — a pure function of time
  <slug>/manifest.yaml the claim manifest (claim, scope, evidence, objects, falsifier, non-claims, claim frames)
  <slug>/renders/      <slug>__master.mp4 · poster · contact sheet · receipt.json · stills/
scripts/films/
  bind_facts.py        registries → facts.json (--check)
  render_film.py       capture + encode + stills + receipt (needs Chrome and the render venv)
  verify_films.py      manifests, bindings, receipts, freshness, overflow, determinism (no browser)
  slate.py             slate.yaml → SLATE.md (--check), with the score gate
```

## Render

```bash
python3 -m venv ~/.venvs/cubits-films && ~/.venvs/cubits-films/bin/pip install playwright imageio-ffmpeg numpy pillow
~/.venvs/cubits-films/bin/python scripts/films/render_film.py same-scores-different-worlds --format all
```

The renderer serves the repository root over localhost, opens the film with
`?capture=1&format=master`, waits for the vendored fonts and `facts.json`,
calls `window.__film.seek(t)` for every frame, captures over the DevTools
protocol (about 50 ms a frame), encodes with the bundled ffmpeg, keeps a
poster, five review stills, one still per declared claim frame and a contact
sheet, re-captures five sampled frames to prove determinism, and writes a
receipt naming the git HEAD, the sha256 of every input, and a digest over
every frame.

Preview any film by opening `films/<slug>/film.html` over a local server
(`python3 -m http.server 4173`), optionally with `?t=12.5` or `?guides=1`.

## Verify

```bash
python3 scripts/films/bind_facts.py --check   # facts current against the registries
python3 scripts/films/verify_films.py         # manifests bound, receipts fresh, no overflow, determinism ok
python3 scripts/films/slate.py --check        # slate gate and SLATE.md drift
```

All three run in `scripts/verification_manifest.py`, so a registry edit, a
stale render, or a concept that fails the gate fails the build.

## What a film is not

A rendered film is an attempt, not a result. It shows what the registry
already binds; it adds no evidence. Success is a stranger who understands an
operation from the pixels alone, or who is moved to rerun a reproduction
command the film names — recorded, if it ever happens, in
`distribution/outcomes.yaml`, never here.
