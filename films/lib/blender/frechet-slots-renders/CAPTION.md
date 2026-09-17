# What the frame shows, and what it does not

Each row is one run's harmful stratum. The slots are the both-miss counts the two per-guard miss counts allow. The solid sphere is the count the rows recorded. Rings are worlds the marginals permit and the run did not produce. The amber tick is the independence plug-in.

| run | n | G1 miss | G2 miss | band from marginals | slots | recorded both-miss | plug-in |
|---|---|---|---|---|---|---|---|
| E3 | 400 | 393 | 385 | [378, 385] | 8 | 379 | 378.2625 (30261/80) |
| E3B | 400 | 0 | 159 | [0, 0] | 1 | 0 | 0.0000 (0) |

Sources, pinned:

- `experiments/e3/results/observations.jsonl` sha256 `952416606e0c…` at commit `031dc66871da`
- `experiments/e3/results/e3_result.json` sha256 `84e21e59665b…` at commit `3ca78ec08004`
- `experiments/e3b/results/observations.jsonl` sha256 `00e75bf47f68…` at commit `058d6f635ce3`
- `experiments/e3b/results/e3_result.json` sha256 `a9685abb1ca6…` at commit `058d6f635ce3`

## Not shown

- Shows which feasible integer each run landed on, not why; it is not evidence of dependence, and the amber tick is the independence plug-in, a model's point, not an observation.
- One pool and one frozen operating point per run, two research classifiers under 1B parameters; nothing about E2, its guards, its pools, or any deployed guardrail.
- E3B's single slot is a structural zero: G1 missed no injection, so both-miss was fixed at 0 before any joint count; it is not evidence of independence or of a good guard.
- Slot positions are exact integer counts recounted from committed rows; the image carries no numerals, and every number is in receipt.json, pinned to the commit that last touched its source.
- One host and one Blender build, EEVEE on CPU; no cross-version, GPU, physical-device, independent-review or learning claim.
