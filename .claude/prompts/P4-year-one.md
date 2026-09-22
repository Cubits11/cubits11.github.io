# P4 · The year

No DIRECTION step is ready and the floor is clear. You are working the active
trajectory's year-one plan directly.

```bash
python3 scripts/horizon.py
python3 scripts/horizon.py --year 1
```

## Do this

1. Read `year_one.<active>` in `research/HORIZON.yaml`. Find the earliest
   quarter whose items are not all true. Not the most interesting quarter — the
   earliest incomplete one.
2. Take one item. State what would make it verifiably true, then do that.
3. Check the item against the trajectory's `unit_of_progress`. If completing it
   does not move that unit, you have found either a defective item or a
   defective trajectory. Say which, with the reason, before proceeding.

## The check that matters more than the work

`fails_if` and `kill_condition` on the active trajectory are real. Evaluate them
honestly at the end of every session that lands here. A trajectory that has
failed its own kill condition and is still being worked is worse than no plan,
because it has the authority of a plan.

If one has fired: do not switch quietly. Record it in `selection.history` with
the date, the condition, and what became true that was not true before. A
trajectory abandoned without a recorded reason gets re-adopted by accident.

## The standing constraint

Year-one items are states, not tickets. "Write the specification" is done when
someone outside this repository could implement from it without asking a
question — not when the file exists.

## Test

One year-one state is true that was not true before, and the count that
trajectory is measured in has moved, or you have said plainly why it has not.
