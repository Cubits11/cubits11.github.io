# E2 pilot v1 — config-freeze record

Dated 2026-09-01. Implements step 3 of the commit order in
`docs/E2_PILOT_V1_CUT.md` (D7 struck). Governing contract:
`cc-framework@0b945025` `docs/research/E2_MEASUREMENT_CONTRACT.md` — it
wins any conflict. `python3 experiments/e2/freeze/check_freeze.py`
re-verifies this freeze from the committed artifacts alone.

**No outcome was inspected in making this freeze.** No guard was loaded
or run, no threshold was swept, and no prompt text is committed here —
item files carry ids, row indices, and text hashes only. Prompt text is
re-derivable from the pinned upstream revisions.

## What is pinned

- **Guards (G, three named systems; revisions from the HF API this
  date):** Llama-Guard-4-12B @ `87acb4b9`, Llama-Guard-3-8B @
  `7327bd9f`, shieldgemma-2b @ `d1dffc9c`. All three are gated
  ("manual"); their LICENSE bytes could not be hashed unauthenticated
  and are **OWNER-PENDING** — hashed on the owner's authenticated pull,
  before any collection.
- **Harmful pool:** AdvBench `harmful_behaviors.csv` at
  `llm-attacks/llm-attacks@098262ed` — 520 items, MIT (LICENSE bytes
  hashed in sources.json). Ids `advbench-<row>`.
- **Benign pool:** `bench-llm/or-bench` config `or-bench-80k` (80,359
  rows) at dataset revision `e36d8b80`, CC-BY-4.0 — a seeded sample of
  1,600, split 800 calibration / 800 evaluation. Parquet shard hashed.
  Ids `orbench80k-<row>`. Attribution required in any release.
- **Seed:** `MC-E2-PILOT-V1-FREEZE-2026-09-01`, with the exact sampling
  and split ranking written in sources.json and re-executed by
  check_freeze.py.

## Selection under the frozen rules (docs/E2_PILOT_V1_CUT.md, Items)

Both sources were selected on metadata only: event compatibility
(source-labelled harmful instructions; source-labelled benign prompts),
license (MIT; CC-BY-4.0), and size. Neither is HarmBench or XSTest;
committed id lists intersect the MSBench `fb6f32e6` item ids in zero
elements (the 900 ids are committed beside this file for the check).
Neither AdvBench nor OR-Bench appears anywhere in census.yaml, so no
member of G has published per-item outcomes on them known to this
record — the frozen condition, satisfied.

**Disclosed adjacency (does not violate the frozen rule):** the census
row `domyn-open-guards-2026` reports aggregate marginals — no per-item
outcomes — for fourteen systems including "Llama Guard 12B" and
"ShieldGemma 2B" on a 79,331-item pool that contains 154 filtered
StrongREJECT and 103 HarmBench items. That row is why StrongREJECT was
not selected, and it is recorded here so nobody discovers it later and
mistakes it for a hidden leak. Aggregate marginals on a different pool
identify nothing item-level about this freeze's lists.

## Sizing

n_harmful (520) + n_benign_eval (800) = **1,320 ≥ 1,097** — the dry-run
precision bar (CC-006, `E2_DRYRUN_FINDING.md` @ `327f0684`) passes at
the pinned counts. Complete-case n after missingness is a collection
outcome, not a freeze property; if it falls below the bar, the result
leads with precision HOLD exactly as the pilot states.

## The benign pool is a design choice, stated

OR-Bench prompts are benign items written to sit near refusal
boundaries. Calibrating FPR* = 5% on this pool defines the operating
points relative to boundary-adjacent benign traffic, not trivially
benign traffic. That is a property of the instrument, declared before
any outcome exists; it is not a claim that this pool represents any
deployment's traffic.

## What this freeze does NOT authorize

Nothing runs. Collection remains blocked on, in order: (1) the owner's
acceptance of the three gated model licenses for this use, with
`commercial_reuse` recorded per file and LICENSE bytes hashed on
authenticated pull; (2) the owner's written `AUTHORIZE COMPUTE:
<gpu, vram>`. Calibration (benign calibration half only) precedes any
evaluation or harmful scoring, per the pilot. No claims.yaml change is
part of this freeze; CC-005 restates only after conforming rows exist.
