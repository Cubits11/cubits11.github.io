# Upstream ask — GuardBench joint reporter

Status: PREPARED, not sent. Source: `distribution/dossiers/guardbench-2024.md`, the ask verbatim, plus one pinned link. Sender: the owner. This is an upstream tracker, so none of this repository's templates apply; the URL prefills title and body.

One click opens the new-issue form on `AmenRa/guardbench` with the message below:

https://github.com/AmenRa/guardbench/issues/new?title=Joint+%28all-miss%29+report+beside+the+per-model+marginals&body=GuardBench+already+writes+%60results%2F%3Cdataset%3E%2F%3Cmodel%3E.json%60+keyed+by+item+id%2C+so+the+one+number+the+leaderboard+cannot+show+%E2%80%94+how+many+unsafe+items+%2Aevery%2A+compared+model+missed+%E2%80%94+is+exactly+computable+and+one+script+away.+I+prepared+%60joint_report.py%60+%28standard+library%3B+aligns+on+id%2C+refuses+otherwise%29%3A+union%2C+all-miss%2C+leave-one-out+and+exclusive+coverage+per+dataset+at+the+0.5+threshold.+Would+you+accept+it+under+%60scripts%2F%60%2C+or+publish+one+dataset%27s+results+directory+so+anyone+can+run+it%3F%0A%0AThe+script%2C+pinned%3A+https%3A%2F%2Fgithub.com%2FCubits11%2Fcubits11.github.io%2Fblob%2Fe12ed3b133156798d73c7ed35c3133a689b20c73%2Fcontrib%2Fguardbench_joint.py%0A%0AFrom+the+published+marginals+alone+the+all-miss+rate+is+only+bounded%3B+with+two+result+files+for+one+dataset+it+is+an+integer.+If+I+have+misread+the+harness%27s+file+layout%2C+a+correction+is+as+useful+as+a+merge.

## Gate, from distribution/QUEUE.md row 3

- Eligible since 2026-09-09, one week after the IBM ask.
- Duplicate check, 2026-09-17, read in the browser pane: the tracker holds two issues, #6 "Proposal: EvalPort adapter for portable GuardBench datasets & results" and #3 "Can't load from the train split". Neither asks for a joint report and neither is from Cubits11. #6 is adjacent (portable results); the owner may want to read it first.
- The tracker banner asks contributors to read the contributing guidelines before opening an issue. Read them at send time.
- Record the permalink and UTC time in `distribution/dispatch-log.yaml` after sending, as the BELLS entry does. Never invent a dispatch date.

## Message as prefilled

Title: Joint (all-miss) report beside the per-model marginals

```
GuardBench already writes `results/<dataset>/<model>.json` keyed by item id, so the one number the leaderboard cannot show — how many unsafe items *every* compared model missed — is exactly computable and one script away. I prepared `joint_report.py` (standard library; aligns on id, refuses otherwise): union, all-miss, leave-one-out and exclusive coverage per dataset at the 0.5 threshold. Would you accept it under `scripts/`, or publish one dataset's results directory so anyone can run it?

The script, pinned: https://github.com/Cubits11/cubits11.github.io/blob/e12ed3b133156798d73c7ed35c3133a689b20c73/contrib/guardbench_joint.py

From the published marginals alone the all-miss rate is only bounded; with two result files for one dataset it is an integer. If I have misread the harness's file layout, a correction is as useful as a merge.
```

## What this is not

- Not sent. Nothing here dispatches anything; the owner's browser does.
- A reply, merge or release is a qualified outcome only after inspection under `distribution/EXTERNAL_EVENTS.md`.
- The pinned script was proven on harness-shaped fixtures, not on a GuardBench results directory, because none is published.
