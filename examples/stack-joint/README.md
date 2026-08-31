# Static-OR receipt stub

This directory is deliberately standalone: copy `joint_or.py`, make one CSV,
and run it with Python's standard library. It uses no network and has no
project-specific registry or identifiers.

## What it will and will not print

The program prints a static OR only after a **self-described tuple** has a
complete manifest and complete binary item-by-system matrix. Its object is
strictly a counterfactual static OR, never a deployed route:

```
union    = mean_i max_s D[i,s]
all_miss = mean_i min_s (1 - D[i,s])
```

`UNKNOWN` with a nonzero exit is the intended result whenever the tuple is
missing, routed, adaptive, threshold-defaulted, semantically uncontracted,
or structurally incomplete. A successful run means only “structurally complete
self-described tuple.” It cannot independently prove a common event,
source quotation, full real-world exposure, fixed-before-evaluation threshold,
item manifest, label provenance, or non-deployment.

In particular, do not use this file to OR native `unsafe` labels from systems
whose source-defined events differ. First write a shared event translation
contract, cite the native definitions in `event_source`, cite the translation
in `event_translation_source`, and declare `event_translation` as either
`shared_source_defined` or `translation_declared`. The code requires those
declarations; it cannot verify them.

## CSV contract

Start the file with the required declarations shown in `fixture.csv`:

```csv
# event: D=1 means the shared event E
# event_source: primary-source native-event quotations
# event_translation: shared_source_defined | translation_declared
# event_translation_source: shared-event contract or translation source
# item_set: stable denominator token
# item_ids: exact,comma,separated,item,IDs
# item_count: number of IDs above
# systems: exact,comma,separated,system,IDs
# operator: static_or
# composition: counterfactual_static
# exposure: declared_full
# threshold_rule: fixed_per_system
# threshold_source: fixed-threshold configuration reference
# missingness: none
# label_source: harm/benign label provenance
# adaptive: untested
item_id,system_id,decision,item_set,threshold,exposure
```

The six data columns are exact. `decision` is literal `0` or `1`; `NA` is
rejected rather than silently dropped. Every declared item and system must
occur, every row must agree with the item-set and exposure declarations, and
the matrix must have exactly one cell for every declared item×system pair.
The threshold must be nonempty, fixed within each system, and not a placeholder
such as `default`, `vendor_default`, `matched`, or `unknown`.

## Run and test

```bash
python3 joint_or.py fixture.csv
python3 test_joint_or.py
```

Expected good-fixture output:

```
n=4
union=3/4 = 0.75
all_miss=1/4 = 0.25
```

The regression suite verifies that the stub refuses a blank event, default
thresholds, `NA`, missing cells, an entirely missing item or system, duplicate
cells, threshold drift, split drift, and non-static operator/composition/
exposure declarations. Its checks are structural, not a validity certificate
for the declared facts.
