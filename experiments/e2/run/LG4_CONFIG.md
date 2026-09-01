# LG4 configuration — owner sentence, recorded

Dated 2026-09-01. Append-only; amends nothing in the freeze.

> LG4 CONFIG: 8-bit

Meaning, binding for every LG4 row and sentence:

- Llama-Guard-4-12B runs as a **local 8-bit conversion from the pinned
  revision `87acb4b9`** — converted on the authorized box from the
  authenticated pinned download, never a third-party pre-quantized
  upload. The conversion tool, version, exact command, and output file
  hashes are recorded append-only beside this file before LG4's
  calibration.
- Under contract Layer D this is a distinct configuration: every LG4
  observation row carries it in `configuration_hash`; thresholds are
  calibrated for this configuration; every public sentence about LG4
  names the 8-bit configuration and never bare "Llama-Guard-4-12B".
- Feasibility: ≈ 12–13 GB — fits the authorized 24 GB box. It does
  **not** fit the 8 GB M1 session host, which stays a writing and
  protocol machine (owner ruling, this date). Nothing loads there.
- The two other guards are unaffected: LG3-8B and shieldgemma-2b run at
  native BF16 on the authorized box.

Still open before any real token, unchanged: the license record on the
box's first authenticated pull (access at pins, LICENSE bytes hashed
append-only, `commercial_reuse` per file in the owner's words).
