# Dossier — multimodal-safeguard-bench-2026

Row: `multimodal-safeguard-bench-2026` · classification PRESENT (computable_via_item_release + printed_partial_stack) · reconstruction EXACTLY_RECONSTRUCTIBLE · status: an issue is already open (`PatrickKollman/Multimodal-Safeguard-Bench#1`, 2026-08-31, recorded as a diagnostic interaction); nothing further sent.

**1. What the source publishes.** Complete per-item `blocked` bits for three guards over 400 harmful and 500 benign items (text and image strata), printed per-guard metrics, and two printed two-guard compositions. No three-guard OR, no all-zero-row count, no leave-one-out table.

**2. What can be reconstructed.** Everything bitwise, exactly: MC-004's four strata (`python3 scripts/reanalyze_msbench.py`, eight hashes verified first), including the benign-image OR of 250/250 driven by one guard's column. What cannot be reconstructed: a shared-event catch statistic, because the harness maps distinct native `unsafe` predicates to one `blocked` bit without a source-defined event translation.

**3. What remains unidentified.** Whether the printed LG4→text / LG4∨ShieldGemma-2→image route was executed item-level or reconstructed post hoc from the per-guard files; and any matched operating-point calibration.

**4. Smallest missing artifact.** One yes/no, already asked in issue #1: direct route trace or static reconstruction.

**5. Smallest action the maintainer can perform.** Answer the issue. If direct, optionally attach the route's per-item terminal actions in the `examples/route-receipt` two-file shape (no prompt text).

**6. Can we do 90 %+ of the work?** The reconstruction is done and registered; the receipt format is written and tested (`examples/route-receipt/`). Only the author knows the answer to the question.

**7. Success condition.** An author reply confirming or correcting the route semantics (`source_corrections`, agreed true or false); MC-004's scope is then narrowed or restated under its registered falsifier, and the census row's `native_action_translation` field updated with a dated revision.

**8. Correction condition.** Evidence that a committed `blocked` column is not the named guard's verdict, that a printed metric disagrees with the recomputation, or that a source-defined translation to a common event exists — each fires MC-004's REJECT or NARROW as registered.

**The ask.** Already on the record in issue #1; no repeat. Silence is the default.
