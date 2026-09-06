# Two Guardrails Walk Into a Stack — production handoff

Status: camera sections scripted; both supporting inserts rendered and verified; rehearsal package built. Owner footage and final voice performance are required before assembly can be called complete. This package is the coordination point for this task; it does not supersede the evidence registries or the existing films.

The original `youtube-series-and-flagship.md` was not found in the accessible workspace. The owner's seven-section build plan supplied in this task is the editorial input. `script.json` is the editable narration and shot source for this package. `build_flagship.py` generates the recording script, source map, rehearsal captions and browser rehearsal desk from it. Never edit generated numerals.

An intentional continuity change: the opening uses the existing CC-001 illustrative marginals instead of the unbound 5% × 2% sketch. This keeps the opening and The Stack on the same example and avoids changing the shared facts registry. The camera performance says “these miss rates”; the insert renders the rates and multiplication from `facts.json`. Counts, dates and percentages in narration are generated through fact placeholders.

The operation in the opening is exposing the independence assumption. The operation in the close is turning a disagreement into a checkable correction. Each has a weaker sentence spoken verbatim. The visual signature is an amber question mark that returns as an invitation to test the claim; the product is a changed belief that remains open to correction.

Build and check from the repository root:

```sh
python3 scripts/films/build_flagship.py
python3 scripts/films/build_flagship.py --check
python3 scripts/films/verify_films.py
python3 scripts/verification_manifest.py
```

Open `rehearsal.html` through the repository's local web server. It is a timed editorial rehearsal with real film playback and explicit placeholders, not a finished video. Rehearsal captions are provisional timings: replace their timing against the recorded voice before release.

Assembly requires owner camera takes for sections 1 and 7, the voice track, the section 3 motif capture and section 4 terminal capture, a source-map re-run, fresh film receipts, and the full verification manifest green at the actual assembly commit. Do not repair unrelated claim-history changes by rewriting accepted history.
