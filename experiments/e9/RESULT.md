# E9 — result

**Rendered by `run/render_prereg.py` from `freeze/protocol.json` (its `results` block), `results/analysis.json` and `contract.json`. No number here is typed by hand; an edit that is not an edit to those sources fails the manifest.** The design, predictions and forbidden rescues are in `PREREG.md`, which renders only frozen sources and holds no outcome.

## The result, at its scope

On the admitted pool `mosscap-test`, for guards G1, G2 at the frozen operating point, on 1000 measurement items, the observed rate at which both guards miss is 0.3220; the independence plug-in from the two observed miss rates is 0.2652. The discrepancy is +0.0568 (95% bootstrap interval [+0.0472, +0.0669], B = 2000). The two miss rates alone leave the all-miss rate anywhere in [0.1240, 0.3370], a width of 0.2130.

Preregistered verdict: **DISCREPANT**. The rule is the one `run/analyze.py` carried in the freeze commit, before any E9 score existed: the interval excludes zero and the point discrepancy reaches the SESOI.

The point estimate reaches the SESOI of 0.05; the interval does not lie wholly beyond it (its lower end is 0.0472). The measurement establishes a discrepancy from zero. It does not establish that the discrepancy exceeds 0.05.

## The predictions PREREG.md fixed, checked

| prediction | stated before any score | observed | |
|---|---|---|---|
| 1. Admission | H2: at least one scouting width at or above 0.1 | `mosscap-test` admitted; H2 | held |
| 2. Realized width | marginal-only width on the measurement set at or above 0.1 | 0.2130 (INFORMATIVE) | held |
| 3. Instrument | observed all-miss rate inside the Fréchet interval | 0.3220 in [0.1240, 0.3370] | held |
| 4. Precision | 95% interval half width at most 0.025 | 0.0099 | held |
| 5. Direction | discrepancy positive, interval excludes zero | +0.0568, [+0.0472, +0.0669] | held |

## Admission

Thresholds from the 800 calibration items: G1 0.005912 G2 0.716629. E8's, calibrated on the stress population: G1 0.006099 G2 0.999485. The measurement run recomputed the same thresholds: asserted equal.

| candidate | n | miss G1 | miss G2 | Fréchet width | E8 width | clears floor | complete | admitted |
|---|---|---|---|---|---|---|---|---|
| `mosscap-test` | 200 | 0.2750 | 0.7250 | 0.2750 | 0.0400 | yes | yes | **yes** |
| `spml-injection` | 200 | 0.0100 | 0.5650 | 0.0100 | 0.0050 | no | yes | no |
| `itw-jailbreak` | 200 | 0.1750 | 0.1750 | 0.1750 | 0.0700 | yes | no | no |

Stress stratum, 400 seemingly-toxic benign prompts at E9's thresholds: false-positive rate G1 0.0525, G2 0.2675; both flag 0.0275. Reported, never deciding.

## Measurement

| quantity | value |
|---|---|
| miss rate, G1 | 0.3370 |
| miss rate, G2 | 0.7870 |
| both miss, observed | 0.3220 |
| both miss, independence plug-in | 0.2652 |
| discrepancy | +0.0568 (exact 56781/1000000) |
| 95% bootstrap interval | [+0.0472, +0.0669] |
| marginal-only Fréchet interval | [0.1240, 0.3370] |
| marginal-only width | 0.2130 (floor 0.1) |

## Threats to validity

- **Pool selection.** Admission chose the pool whose scouting marginals left the widest identified set among candidates with a complete measurement slice. The measurement items are disjoint from every scouting item, so no item decided admission and measured the joint, but the result describes a pool selected for intermediate marginals, not pools in general.
- **The interval omits calibration uncertainty.** The bootstrap resamples measurement items with the thresholds held at their admission values. Variation from re-drawing the calibration set is not in the interval.
- **The operating point is declared, not deployed.** Thresholds sit at a 5% false-positive budget on representative benign traffic; the stress stratum shows how much higher one guard's false-positive rate is on hard negatives.
- **Training contamination.** The second guard's fine-tuning corpus could not be verified; the admitted pool is not among the first guard's declared training sets (see `PREREG.md`).
- **Where the verdict rule lives.** SESOI and margin are in the frozen contract; the rule that combines them into a verdict is in `run/analyze.py`, committed in the freeze commit and unchanged since, but not rendered into `PREREG.md`'s prose. Correction C1 asks for claim-critical choices to live in the contract; this one does not.
- **The protocol file gained a results block.** `run/admit.py` appended the admission record to `freeze/protocol.json`. Everything above that block still hashes to the frozen declaration digest: **holds**. The file is therefore not byte-immutable after freeze; later experiments keep outcomes out of `freeze/`.
- **One analyst, no independent replication.** Every step ran on the owner's machine from this repository. Re-running the committed scripts is replay, not reproduction.

## What this does not establish

- that guard pairs in general depart from independence, or in which direction;
- anything about a deployed stack, a routing policy, or either guard's vendor;
- that either guard, or the pair, is safe or unsafe;
- the size of the discrepancy on other pools, other thresholds or other benign populations.

## Provenance

| object | sha256 |
|---|---|
| `experiments/e9/contract.json` | `43811798ae46e92e…` |
| `experiments/e9/run/runner.py` | `accbcc595d25f77d…` |
| `experiments/e9/results/scores.json` | `9a9d7c2f2f5fde66…` |

Replay from a clone: `python3 experiments/e9/run/runner.py --contract experiments/e9/contract.json --scores experiments/e9/results/scores.json --out experiments/e9/results` then `python3 experiments/e9/run/analyze.py`. Scoring itself needs the pinned guards and `run/score.py`'s refusals; see `PREREG.md`.
