# P3 · The heading

The floor is clear: no blocker is older than the escalation window and qualified
outcomes are non-zero. That is rare. Take the heading.

```bash
python3 scripts/direction.py
```

Take the first step whose status is `next` and whose dependencies are done. If
`direction.py` reports the budget rule violated — infrastructure outstanding
exceeding work outstanding — take a non-infrastructure step instead, whatever
order the file lists them in.

## Before you write anything

Say the trade out loud: one sentence naming what this step costs and what open
thing it is being done instead of. Then write it.

## The rules that void work retroactively

- A threshold, estimator, hypothesis or criterion changed after outcomes are
  visible is a forbidden rescue. The affected result is not reported.
- No claim-critical choice is implemented as a literal inside the runner when
  the frozen contract can supply it (correction C1).
- A kill rate over unclassified mutants is not a measurement (C2, SM requirement).
- Discovery rows are never promoted to confirmatory status (C4).
- Reuse of frozen rows is not reuse of confirmatory status (C3).

## Before you commit

```bash
python3 scripts/verification_manifest.py
```

Exit 0, or the change is not ready. Check `claims.yaml` for a
`local_content_change` trigger on anything you touched.

## Test

The step's `done_when` is true, verified by running something, and
`scripts/direction.py` moves it off `next`.
