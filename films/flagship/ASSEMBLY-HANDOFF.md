# Assembly handoff — 2026-09-05

The owner asked for completion of camera sections 1 and 7, with progress recorded where the existing film work lives. This file and the appended `films/LEDGER.md` entry are that handoff. The new work remains in the shared checkout; no commit, push, upload, public metadata change, or automated monitor was initiated by this task.

## What exists

- `script.json`: seven-section editorial narration and shot source, with a matched opening and closing performance.
- `CAMERA-CALL-SHEET.md`: the two recordable camera sections, shot direction, exact weaker claims and locators.
- `RECORDING-SCRIPT.md`: complete generated voice script; every spoken research numeral resolves from `facts.json`.
- `rehearsal.html`: 8:30 browser rehearsal, timed real-film playback, manual scrubbing, section selection, large script and mirror mode. Camera and capture gaps remain explicitly labelled.
- `source-map.json`: input hashes, evidence locators, spoken-number bindings and section operations. The builder checks contiguous beats, in-range film playback, fact values and the weaker sentence appearing once per section.
- `rehearsal-captions.srt`: provisional reading captions. Not aligned subtitles for an unrecorded performance.
- `../the-multiplication/`: rendered opening insert, with the independence assumption visible before the product. Uses the same bound example as The Stack.
- `../the-correction-invitation/`: rendered closing card with the exact corrections route held throughout.
- `CHANNEL-STRATEGY.md`: time-bounded channel observations, the first-frame experiment, packaging and next-episode treatments.

## Editorial changes and boundaries

The initial sketch's unbound 5% × 2% example becomes the already registered CC-001 example, so the opening and The Stack agree. No shared facts or evidence claim was edited to make this choice work.

The original flagship Markdown was not found locally. This package implements the supplied build architecture; reconcile it against that original if it later becomes available. Do not silently overwrite a parallel script version.

The planned 8:30 duration is a real sum of editorial slots, not a claim that the current film masters alone run that long. Existing films run at normal speed; the extra time belongs to the scoped explanations and evidence captures. Sections 4–6 require deliberate source holds, not repeated motion or padded loops. The rehearsal intentionally labels those outstanding shots.

## Recorded gate state

Before additions, `bind_facts.py --check` passed with 96 facts and `verify_films.py` passed all ten existing films, including the four flagship procedure films. Both new inserts rendered with deterministic recaptures and zero reported text overflows; contact sheets/poster were visually inspected.

The full verification manifest was attempted during this task. It passed the claim registry, then failed at the claim-history kernel:

> entries[38] differs from the prior accepted revision — accepted history is append-only

This appeared in concurrent, pre-existing claim-history changes. This task did not rewrite that history or weaken its check. Re-run the complete manifest after the history owner resolves the discrepancy. A green film check is not a green assembly gate.

## Remaining work before a finished video exists

Record owner camera takes for sections 1 and 7 and the full voice track. Capture the actual motif and live census terminal. Cut the evidence holds to the voice, keeping the ledger tag visible; do not leave the rehearsal's placeholders in a deliverable. Use the rendered numerals as authority and redo disagreeing takes. Align the captions to the final voice and make the final chapter times from the cut.

Then regenerate/check the source map, check all current film receipts, run the full verification manifest at the intended assembly commit, and verify the finished audiovisual file. The source map now has an explicit entry in the canonical verification manifest. The gate does not claim to perform speech recognition or to verify footage that has not been recorded.
