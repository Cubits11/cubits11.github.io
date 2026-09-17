# Counterexample invitation — E3-001, the one number this repository measured itself

Status: PREPARED, not sent. Template: `.github/ISSUE_TEMPLATE/counterexample.yml`. Sender: the owner.

One click opens the form with every field below filled in:

https://github.com/Cubits11/cubits11.github.io/issues/new?template=counterexample.yml&title=counterexample%3A+E3-001+both-miss+379%2F400+recomputes+differently&kind=I+found+a+counterexample+to+a+registered+claim&target=E3-001&source=https%3A%2F%2Fgithub.com%2FCubits11%2Fcubits11.github.io%2Fblob%2F031dc66871dab39548ae83ed064bd8e19ff43c5c%2Fexperiments%2Fe3%2Fresults%2Fobservations.jsonl&evidence=E3-001+registers%2C+on+400+or-bench-toxic+items+at+thresholds+frozen+before+scoring%3A+G1+missed+393%2C+G2+missed+385%2C+both+missed+379.+The+two+marginals+allow+any+both-miss+count+from+378+to+385%3B+the+rows+recorded+379.%0A%0AI+recomputed+from+the+2%2C400+committed+rows+at+commit+031dc66871da+with%3A%0A++++python3+scripts%2Fverify_e3.py+--show%0Aand+got%3A+%3Cpaste+the+recomputed+table+here%3E%0A%0AWhat+differs+from+the+registered+block%3A+%3Cname+the+quantity+and+both+values%3E&consequence=If+any+recomputed+quantity+differs+from+the+expected+block+in+claims.yaml+beyond+1e-12%2C+or+the+observed+joint+miss+lies+outside+the+interval+its+own+marginals+fix%2C+the+claim%27s+registered+consequence+is+REJECT.+A+rescoring+of+the+same+400+items+with+the+pinned+model+revisions+that+lands+on+a+different+count+is+a+reproduction+mismatch%2C+not+this+falsifier%3B+file+it+under+the+Reproduction+template.

## Why this number

E3-001 is the only own-measurement claim with a joint cell in it. The marginals (G1 missed 393 of 400, G2 missed 385) fix the both-miss count only to [378, 385]; the rows recorded 379. That integer is recounted from the committed rows by `scripts/verify_e3.py` and rendered at `films/lib/blender/frechet-slots-renders/`. If it is wrong, the claim is REJECTED under its own falsifier.

## Gate before sending: the form must be listed

On 2026-09-17 GitHub's template chooser for this repository listed only "Census row correction". Both YAML forms were unlisted because their `description` exceeded GitHub's 200-character limit (the file page says: "Description must be between 3 and 200 characters"), so every prefilled link, including the ones on the live /try/ page, opened a blank issue. The descriptions are shortened in this branch and `scripts/verify_consequence.py` now fails on the limit. Until that commit is on `main`, this link opens a blank form. Check https://github.com/Cubits11/cubits11.github.io/issues/new/choose lists the form first.

## Fields as prefilled

- kind: I found a counterexample to a registered claim
- target: E3-001
- source: https://github.com/Cubits11/cubits11.github.io/blob/031dc66871dab39548ae83ed064bd8e19ff43c5c/experiments/e3/results/observations.jsonl
- evidence:

```
E3-001 registers, on 400 or-bench-toxic items at thresholds frozen before scoring: G1 missed 393, G2 missed 385, both missed 379. The two marginals allow any both-miss count from 378 to 385; the rows recorded 379.

I recomputed from the 2,400 committed rows at commit 031dc66871da with:
    python3 scripts/verify_e3.py --show
and got: <paste the recomputed table here>

What differs from the registered block: <name the quantity and both values>
```

- consequence:

```
If any recomputed quantity differs from the expected block in claims.yaml beyond 1e-12, or the observed joint miss lies outside the interval its own marginals fix, the claim's registered consequence is REJECT. A rescoring of the same 400 items with the pinned model revisions that lands on a different count is a reproduction mismatch, not this falsifier; file it under the Reproduction template.
```

## What this is not

- Not a claim that the number is right. It is the falsifier, made one click reachable.
- An issue the owner opens is not a qualified outcome (distribution/QUEUE.md, row 8). Its use is to be linked from where strangers arrive.
- Rescoring with the pinned models is a reproduction, handled under the same-day correction policy, not under this falsifier.
