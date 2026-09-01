# E2 pilot — compute authorization and preflight record

Dated 2026-09-01. Step 4 of the commit order in `docs/E2_PILOT_V1_CUT.md`.

## The authorization, verbatim

> AUTHORIZE COMPUTE: Apple M-series, 24GB unified

Recorded 2026-09-01. Scope per the pilot: calibration first (benign
calibration half only), then collection. This record authorizes no
deviation from the freeze at `experiments/e2/freeze/` (config hash
`07b06dea…`).

## Preflight measurement of the session host — NOT the authorized box

Measured 2026-09-01 on the machine this record was written from:
Apple **M1**, **8 GB** unified memory, 29 Gi free disk, no cached
Hugging Face credentials, no torch/mlx/transformers installed.

That is not the authorized 24 GB box. Verdict for this host: the
pilot's defeater applies — **box lacks VRAM: stay design-only**. No
weight was downloaded, no model was loaded, no forward pass ran, on any
item, frozen or otherwise. Collection and calibration happen on the
authorized box or not at all.

## Feasibility arithmetic for the authorized box (24 GB unified)

Guards load one at a time; full exposure does not require co-residency.
Per-model peak memory at native precision (weights alone, BF16 ≈ 2
bytes/param; runtime and KV overhead extra):

| Guard | BF16 weights | Fits 24 GB unified? |
|---|---|---|
| google/shieldgemma-2b | ≈ 5 GB | yes |
| meta-llama/Llama-Guard-3-8B | ≈ 16 GB | yes, tight (batch 1) |
| meta-llama/Llama-Guard-4-12B | ≈ 24 GB | **no** — weights alone equal the box |

**Open seat, one owner sentence required before LG4 calibration** (the
other two guards are not blocked by it):

- `LG4 CONFIG: 8-bit` — local quantized conversion **from the pinned
  revision** `87acb4b9` (tool, version, command, and output hashes
  recorded in an append-only file beside this one; ≈ 12–13 GB, fits).
  Under contract Layer D this is a distinct configuration: every LG4
  row carries it in `configuration_hash`, thresholds are calibrated for
  it, and every public sentence about LG4 names the quantized
  configuration, never bare "Llama-Guard-4-12B".
- or `LG4 DEFER: <box>` — LG4 runs later on a larger box at BF16; the
  pilot proceeds two-guard ({lg3, sg2b}, one pair) and says so.
- Third-party pre-quantized uploads are ruled out: they are not the
  pinned bytes.

## License gates still open (unchanged from FREEZE.md, restated)

All three guards are gated on Hugging Face. On the authorized box, the
first authenticated pull must: (1) confirm access at the pinned
revisions (which evidences the account-level license acceptance), (2)
hash the LICENSE bytes into an append-only record here — never by
mutating the frozen `sources.json` — and (3) record `commercial_reuse`
per file in the owner's words for the planned outcome-bit release. No
collection before all three.

## Runbook for the authorized box

1. `python3 experiments/e2/freeze/check_freeze.py` — must exit 0.
2. Create a venv; install torch (MPS build) + transformers
   (+ mlx-lm only if `LG4 CONFIG: 8-bit` is authorized). Record exact
   versions in the run log.
3. Authenticated download of each guard at its pinned revision only
   (`--revision <sha>`); hash LICENSE bytes → `LICENSES.md` here.
4. Harness shakeout: `python3 experiments/e2/run/calibrate.py
   --synthetic --out <scratch>` and, if wired, cc-framework
   `e2_dryrun` synthetic rows. No candidate-source item is touched in
   shakeout.
5. Calibration, per guard, benign **calibration half only**
   (`items_benign_calibration.csv`): score all 800, sweep to
   FPR* = 5% nearest-not-exceeding, record achieved FPR and distance.
6. Freeze thresholds into `e2_config.json` (hash-stamped). **No
   threshold moves after this point.**
7. Only then: benign evaluation half and the harmful set, full
   exposure, missingness codes, 3 replicates where stochastic.

## What this record does not do

It does not amend the freeze, does not touch claims.yaml, does not
authorize any run on this 8 GB host, and does not decide the LG4
configuration or the license-use sentences — those remain the owner's.
