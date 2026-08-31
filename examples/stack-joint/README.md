# Static OR receipt stub

This directory is deliberately standalone: copy `joint_or.py`, make one CSV,
and run it with Python's standard library. It uses no network and has no
project-specific registry or identifiers.

## Estimand

For one declared item set, event `E`, and binary decisions `D[i,s]`, where
`D=1` means the event was flagged:

```
union   = mean_i max_s D[i,s]
all_miss = mean_i min_s (1 - D[i,s])
```

Both values use the same denominator `n`: the number of distinct `item_id`
values. The stub prints only `n`, `union`, and `all_miss`.

## CSV contract

Start the file with all four comment headers. They declare the event, whether
every system saw every item, threshold policy, and exposure. `static_full` is
the only exposure this stub accepts; a routed or missing exposure prints
`UNKNOWN` and no rates.

```csv
# event: D=1 means ...
# every_system_saw_every_item: yes
# thresholds: describe each fixed operating point
# exposure: static_full
item_id,system_id,decision,split,threshold,exposure
```

The six columns are, in this exact order:

- `item_id`: stable item key.
- `system_id`: system and operating-point key.
- `decision`: literal `0` or `1`, with `1` defined by `# event`.
- `split`: one identical denominator label for every row.
- `threshold`: nonempty and invariant within each system.
- `exposure`: `static_full` for every row.

The program refuses missing or extra fields, a missing metadata header,
nonbinary decisions, duplicate cells, incomplete item-by-system coverage,
multiple splits, varying per-system thresholds, and routed exposure. It checks
the claimed full coverage against the actual Cartesian matrix; the comments
alone are not proof of execution conditions.

## Run

```bash
python3 joint_or.py fixture.csv
```

Expected output:

```
n=4
union=3/4 = 0.75
all_miss=1/4 = 0.25
```

If the item-level bytes cannot be released, print the two rates; keep the
matrix. A shape check cannot independently verify an unattested event
definition, threshold policy, or execution exposure.
