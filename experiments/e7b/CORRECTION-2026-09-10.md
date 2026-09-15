# E7B correction — calibration and evaluation pool mismatch

Recorded 2026-09-10. **Disposition: REJECT E7B-001 as a preregistration-conforming confirmatory result.** The original rows and HELD labels remain historical output, not accepted predictions. The registry retains the ID with `contradicted` status and a `CORRECT` history transition. E7's earlier VOID status is unchanged.

`PREREG.md` specifies calibration on each judge's own benign pool. `run/measure.py` first intersects all nine judge pools and uses that shared benign set to calibrate every judge. Eight files have 97 own-pool benign examples; the shared set has 75. Nemotron's threshold is 0.95 under the written rule, whereas the recorded implementation chooses 1.00. This is a substantive mismatch, not equivalent wording.

The code also evaluates every included pair on the global intersection of all nine pools. The written estimator calls for the harmful items of the pair's shared pool. The six included judges each have the same 132-item pool, containing 35 harmful items, but an excluded judge's smaller pool reduces the original evaluation to 21 harmful items. The audit records the pool identities and sizes; it does not recalculate replacement outcomes.

The preregistration-conformance falsifier in E7B-001 explicitly covers an applied operating-point rule differing from `PREREG.md`. Its fixed consequence is REJECT. That condition is met. No threshold, calibration budget, hypothesis, pair inclusion rule, or prediction verdict is silently rewritten to rescue the run.

The frozen preregistration, score files, runner, pair rows and results JSON remain byte-identical. `RESULT.md` carries a new dated status notice above its preserved historical body. The original numerical results may describe what the implementation computed, but they are not a clean execution of the preregistration and are not used as launch evidence. P4 remains an arithmetic invariant, not an independent empirical confirmation.

A later corrected calculation must receive a separate correction or exploratory identity and cannot recover an unread holdout after these scores have been inspected. No such replacement run is made or claimed here.

Reproduce the audit: `python3 distribution/research-2026-09-10/audit.py`.

Evidence: [audit output](../../distribution/research-2026-09-10/audit-results.json), [preserved-byte manifest](../../corrections/records/2026-09-10-preserved-inputs.json), [frozen preregistration](PREREG.md), [historical output](results/e7_result.json), [public correction destination](https://cubits11.github.io/corrections/#e7b-pools).
