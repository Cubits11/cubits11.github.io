E4 evidence. Baseline SITE 5dd43af4f9f7ca864cc91b3ae907f00930374b2a; analyze.py SHA-256 d126a28f15e2599719b93d221659a8d8184d02c6e8f0866dd279847b98ad8248.

`python3 -B experiments/e2/run/test_e4_integrity.py -v`: baseline exit 1 (5 failures); fixed exit 0 (5 passes). Baseline files were extracted with `git show HEAD:<path>` to the temp tree recorded in pre.log.

`python3 experiments/e2/run/test_instrument.py`: exit 0.
`python3 experiments/e2/freeze/check_freeze.py`: exit 0, PREREG unchanged.

Canonical configuration digest uses config_hash empty, sort_keys=True, compact separators, ensure_ascii=False. Preserve e2_config.freeze.json independently; make_config refuses overwrite. No calibration or real model run occurred. Thresholds, event semantics, n=1320 population and frozen analysis values unchanged.
