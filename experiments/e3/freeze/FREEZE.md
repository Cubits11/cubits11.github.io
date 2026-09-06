# E3 FREEZE — 2026-09-06

Adopted by owner decision. Supersedes `PREREG.md`'s harmful pool only; every
other line of the preregistration stands unchanged — guards, sizes, FPR\*,
estimands, predictions, kill rule, forbidden rescues, non-claims.

## Why the pool changed

`PREREG.md` drew harmful items from AdvBench. E2 had frozen **all 520** of them.
The disjointness gate fired at zero cost — `STOP-2026-09-06.md`. Replacing an
exhausted pool **before any item is scored** is the same permission the
preregistration already grants for guards: *"Adding a guard before scoring is
not a rescue. Adding one after is."* Zero items were scored when this was
decided.

## What is frozen

| | value |
|---|---|
| seed | `MC-E3-PILOT-V1-FREEZE-2026-09-06` |
| harmful | OR-Bench `or-bench-toxic`, 400 of 655, `3be45901faae3b4b…` |
| benign calibration | OR-Bench `or-bench-80k`, 400 |
| benign evaluation | OR-Bench `or-bench-80k`, 400 |
| pool revision | `e36d8b80e81837c8a8f264bbb2a49f1b32c7e272` — the revision E2 already pinned |
| G1 | `protectai/deberta-v3-base-prompt-injection-v2` @ `90c9989b`, 0.2B, Apache-2.0, licence bytes hashed |
| G2 | `dcarpintero/pangolin-guard-base` @ `eb220d9f`, 0.1B, Apache-2.0 **declared only — no licence file exists** |

Harmful and benign now come from one dataset at one revision. That is a
**lineage correlation** and it is a limitation, not a convenience: any Δ here is
measured inside a single authors' construction of what "toxic" and "seemingly
toxic but benign" mean. It travels with the result.

## Disjointness — the gate, at text level

Ranking removes E2's 2,120 frozen items by `sha256(text)` **before** the draw,
so the gate cannot pass by luck.

```
E2 frozen text hashes           2120
E3 harmful ∩ E2                    0
E3 benign  ∩ E2                    0
E3 harmful ∩ BELLS-170             0     ← MC-002 / MC-003 / MC-005 stay uncontaminated
```

Reproduce: `python3 experiments/e3/run/draw.py experiments/e3/freeze/or-bench-toxic.csv` — exits nonzero on any intersection, before a model loads.

## Order of operations — the part with no recovery

1. ✅ draw · 2. ✅ disjointness gate · 3. ✅ freeze committed
4. ⬜ score benign calibration **only**
5. ⬜ calibrate each guard to the highest threshold with FPR ≤ 5%
6. ⬜ write `e3_config.json`, hash it, record the hash **in a commit**
7. ⬜ only then score harmful

**Scoring one harmful item before step 6's hash exists is a forbidden rescue
with no recovery.** The ordering is provable from the git object graph, which is
why step 6 is a commit and not a file write.

## Not yet true

No item is scored. No threshold exists. `e3_config.json` does not exist. The
evidence ledger's observation-row count is **0** and this freeze does not change
it. A freeze is a promise about what will be done, not a result.
