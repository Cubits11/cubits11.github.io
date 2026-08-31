# Static-OR receipt stub

This directory is deliberately standalone: copy `joint_or.py`, make one CSV,
and run it with Python's standard library. It uses no network and has no
project-specific registry or identifiers.

## What it will and will not print

The program prints a static OR only after a **self-described tuple** has a
complete manifest and complete binary item-by-system matrix. Its object is
strictly counterfactual, never a deployed route. There are two disjoint
interpretations:

```
shared_event   → union / all_miss, only with a declared shared-event translation
harness_action → blocked_by_any / blocked_by_none, only with a declared common action
```

`UNKNOWN` with a nonzero exit is the intended result whenever the tuple is
missing, routed, adaptive, threshold-defaulted, semantically uncontracted,
or structurally incomplete. A successful run means only “structurally complete
self-described tuple of the printed kind.” It cannot independently prove a common event,
source quotation, full real-world exposure, fixed-before-evaluation threshold,
item manifest, label provenance, or non-deployment.

In particular, do not call an OR of native `unsafe` labels a shared-event
catch statistic when their source-defined events differ. For that output,
write a shared-event translation contract, cite the native definitions in
`event_source`, cite the translation in `event_translation_source`, and
declare `event_translation` as either `shared_source_defined` or
`translation_declared`. The code requires those declarations; it cannot
verify them. If a harness itself declares that each binary decision triggers
one common block action, use `harness_action` instead. That prints only the
counterfactual action rate and never promotes it to safety efficacy.

## CSV contract

Start the file with the required declarations shown in `fixture.csv`:

```csv
# interpretation: shared_event | harness_action
# event: D=1 means the shared event E
# event_source: primary-source native-event quotations
# event_translation: shared_source_defined | translation_declared  [shared_event only]
# event_translation_source: shared-event contract or translation source [shared_event only]
# action_source: source defining D=1 as the common action [harness_action only]
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
interpretation=shared_event
n=4
union=3/4 = 0.75
all_miss=1/4 = 0.25
```

For a harness action, the same rows would instead print
`blocked_by_any=3/4` and `blocked_by_none=1/4`, preceded by
`interpretation=harness_action`.

The regression suite verifies that the stub refuses a blank event, default
thresholds, `NA`, missing cells, an entirely missing item or system, duplicate
cells, threshold drift, split drift, an action with no action source, a native
label aggregate smuggled into the shared-event mode, and non-static operator/
composition/exposure declarations. Its checks are structural, not a validity
certificate for the declared facts.
