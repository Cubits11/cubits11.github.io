# E3 — stop before estimation

The sizing gate now uses counts from every observed or missing stratum before any estimator runs. STOP artifacts contain only sizing metadata and stratum counts. Empty, entirely missing, and partially observed zero-complete-case inputs produce `reason: no_complete_cases`, exit 1, and no traceback. A stratum with zero complete cases remains disclosed by counts when other shared strata permit analysis.

- `pre.log`: five regression failures against E2 commit `9259091`; the two-item STOP emitted 86 forbidden field/value paths, the partial-observation input raised ZeroDivisionError, and empty/all-missing inputs omitted the reason.
- `post.log`: the same five regressions pass; all four STOP fixtures exit 1, each recursive scan finds 0 leaks, and the non-STOP fixture retains its entirely missing stratum.
- `n1320.log`: the existing pooled synthetic 1,320-item fixture (1,288 complete cases) exits 0; the full report equals the E2 baseline, including SHA-256 `67b56c22a81700a7691b2472118f70252297f5140815f7fccb3b5febd24a5234`.
- `instrument.log`: the existing twelve-property instrument battery exits 0 with the governing CONTRACT schema.

Every log includes its exact command and exit code. `analyze.py` remains stdlib-only; the instrument battery uses the existing validator environment because its collector checks require jsonschema. PREREG and all frozen thresholds, seeds, sample rules, and resample counts are unchanged.
