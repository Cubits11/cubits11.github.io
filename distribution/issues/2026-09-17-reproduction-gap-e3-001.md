# Reproduction gap — E3-001 has no independent run

Status: PREPARED, not sent. Template: `.github/ISSUE_TEMPLATE/reproduction.yml`. Sender: the owner.

One click opens the form with every field below filled in. The `commit` field is left for the owner: it must be `git rev-parse HEAD` of the clone the command ran in, at send time.

https://github.com/Cubits11/cubits11.github.io/issues/new?template=reproduction.yml&title=Reproduction%3A+E3-001+%E2%80%94+match+%28author-run%3B+no+independent+run+exists%29&claim=E3-001&evidence_class=static-reconstruction&environment=Darwin+25.6.0%3B+Python+3.14.6&command=python3+scripts%2Fverify_e3.py+--show&outcome=Match+%E2%80%94+exit+0%2C+final+line+matched+the+page%27s+expected+output&stdout=AUTHOR-RUN.+Not+an+independent+reproduction.+Filed+to+name+the+gap%3A+no+one+outside+this+repository+has+run+this+command%2C+and+the+direct+route+has+not+been+run+by+anyone+since+2026-09-06.%0A%0AStatic+route%2C+this+host%3A%0A---+e3+%28E3-001%29+recomputed+from+2400+committed+rows%0A++++harmful.n++++++++++++++++400%0A++++harmful.p_miss_G1++++++++0.9825%0A++++harmful.p_miss_G2++++++++0.9625%0A++++harmful.q_obs++++++++++++0.9475%0A++++harmful.q_ind++++++++++++0.9456562500000001%0A++++harmful.delta++++++++++++0.0018437499999999218%0A++++harmful.frechet++++++++++%5B0.9450000000000001%2C+0.9625%5D%0A++++harmful.inside_frechet+++True%0A++++delta_ci95++++++++++++%5B-0.0009562499999999918%2C+0.007062499999999972%5D%0A++++ci_excludes_zero++++++False%0A++++benign.n+++++++++++++++++400%0A++++benign.p_miss_G1+++++++++0.0525%0A++++benign.p_miss_G2+++++++++0.025%0A++++benign.q_obs+++++++++++++0.005%0A++++benign.q_ind+++++++++++++0.0013125%0A++++benign.delta+++++++++++++0.0036875%0A++++benign.frechet+++++++++++%5B0.0%2C+0.025%5D%0A++++benign.inside_frechet++++True%0Aok++++E3-001%3A+2400+committed+rows+reproduce+every+registered+quantity+%28delta+%2B0.001844%2C+CI+%5B-0.000956%2C+%2B0.007062%5D%2C+Frechet+width+0.0175%29%0A%0ADirect+route%2C+never+run+independently%3A+pull+protectai%2Fdeberta-v3-base-prompt-injection-v2+at+revision+90c9989b1a342275dd0d1a95aad283c04e075671+and+dcarpintero%2Fpangolin-guard-base+at+eb220d9f8d75cfbc82cc9d430fa19f85d9764cef%3B+score+the+400+ids+in+experiments%2Fe3%2Ffreeze%2Fitems_harmful.csv+from+or-bench-toxic+at+e36d8b80%3B+apply+the+thresholds+in+experiments%2Fe3%2Fe3_config.json%3B+count.+A+both-miss+count+other+than+379+is+a+mismatch+and+is+wanted.&credit=No+%E2%80%94+record+the+run+without+naming+me

## The gap

Two routes reproduce E3-001. The static route recomputes every registered quantity from the 2,400 committed rows; it has run on this host only. The direct route rescores the 400 frozen ids with the pinned model revisions; it has not run anywhere since the original run on 2026-09-06. Neither has an independent record. This issue is the author's own static run, labelled as such, so the gap has a place to be closed.

## Gate before sending: the form must be listed

On 2026-09-17 GitHub's template chooser for this repository listed only "Census row correction". Both YAML forms were unlisted because their `description` exceeded GitHub's 200-character limit (the file page says: "Description must be between 3 and 200 characters"), so every prefilled link, including the ones on the live /try/ page, opened a blank issue. The descriptions are shortened in this branch and `scripts/verify_consequence.py` now fails on the limit. Until that commit is on `main`, this link opens a blank form. Check https://github.com/Cubits11/cubits11.github.io/issues/new/choose lists the form first.

## Fields as prefilled

- claim: E3-001
- evidence_class: static-reconstruction
- environment: Darwin 25.6.0; Python 3.14.6
- command: `python3 scripts/verify_e3.py --show`
- outcome: Match — exit 0, final line matched the page's expected output
- credit: No — record the run without naming me
- stdout:

```
AUTHOR-RUN. Not an independent reproduction. Filed to name the gap: no one outside this repository has run this command, and the direct route has not been run by anyone since 2026-09-06.

Static route, this host:
--- e3 (E3-001) recomputed from 2400 committed rows
    harmful.n                400
    harmful.p_miss_G1        0.9825
    harmful.p_miss_G2        0.9625
    harmful.q_obs            0.9475
    harmful.q_ind            0.9456562500000001
    harmful.delta            0.0018437499999999218
    harmful.frechet          [0.9450000000000001, 0.9625]
    harmful.inside_frechet   True
    delta_ci95            [-0.0009562499999999918, 0.007062499999999972]
    ci_excludes_zero      False
    benign.n                 400
    benign.p_miss_G1         0.0525
    benign.p_miss_G2         0.025
    benign.q_obs             0.005
    benign.q_ind             0.0013125
    benign.delta             0.0036875
    benign.frechet           [0.0, 0.025]
    benign.inside_frechet    True
ok    E3-001: 2400 committed rows reproduce every registered quantity (delta +0.001844, CI [-0.000956, +0.007062], Frechet width 0.0175)

Direct route, never run independently: pull protectai/deberta-v3-base-prompt-injection-v2 at revision 90c9989b1a342275dd0d1a95aad283c04e075671 and dcarpintero/pangolin-guard-base at eb220d9f8d75cfbc82cc9d430fa19f85d9764cef; score the 400 ids in experiments/e3/freeze/items_harmful.csv from or-bench-toxic at e36d8b80; apply the thresholds in experiments/e3/e3_config.json; count. A both-miss count other than 379 is a mismatch and is wanted.
```

## What this is not

- Not an independent reproduction, and it says so in its first line. An author-run match is not a qualified outcome.
- Not a /try/ experiment: E3-001 has none, and this draft does not add one.
- A direct-route mismatch would be handled under the same-day correction policy and credited beside the claim.
