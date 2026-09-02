# Execution queue — external consequence, in priority order

Ordered by expected information gain per unit of author effort. Every item
names its owner (the human, or the repository's CI), its gate, and the
smallest observable result that would move it. Nothing below has been sent.

| # | action | owner | gate | observable result |
|---|---|---|---|---|
| 1 | Merge `claude/film-laboratory-e2` + `claude/external-consequence-e3` after review; deploy; confirm `/try/` returns 200 and `scripts/smoke_deployed.py` is green | owner | full manifest green (it is, locally: 39 checks) | `/try/` live; the three commands run from a clean clone of `main` |
| 2 | Send the IBM dossier ask (one issue on `IBM/Adversarial-Prompt-Evaluation`) with `contrib/ape_joint.py` attached as a proposed `scripts/main_joint_report.py` | owner | `/try/` live (so the link in the ask resolves) | a maintainer reply; a merged PR (`upstream_prs`) or a pasted joint line (`paired_outcome_releases`) |
| 3 | Send the GuardBench dossier ask (one issue on `AmenRa/guardbench`) with `contrib/guardbench_joint.py` | owner | as above; one week after item 2 (one card per week) | same buckets |
| 4 | Dispatch campaign `x-film-same-scores` (post draft in `distribution/launch-units.yaml`); record the dispatch date in `campaigns.yaml` readings | owner | items 1; owner re-derives numerals at the dispatch commit | 14-day window: `/try/` referrals in GitHub Insights (denominator: impressions); ≥1 reproduction issue |
| 5 | Run three blinded comprehension trials on Same Scores (question and scoring rule fixed in `launch-units.yaml`); record in `outcomes.yaml` diagnostics | owner | viewers who have not seen the site | pass/fail per the pre-registered rule; a fail is the more useful result |
| 6 | Reply to the BELLS-misuse authors' announcement with the row and the one question (selection rule) | owner | one card per week; PRESENT rows first | a confirmation or correction (`source_corrections`) |
| 7 | Dispatch `x-film-thirteen-worlds`, then `x-film-leave-one-out`, one variable changed each, 14 days apart | owner | item 4's decision rule applied first | reproductions of TRY-B; a paired-outcome release |
| 8 | If any qualified outcome arrives: run `distribution/EXTERNAL_EVENTS.md` steps 1–7 the same day; regenerate; credit | owner + CI | — | the first non-zero line in `outcomes.yaml` |
| 9 | Stop rule: at 12 technical interactions with 0 qualified outcomes, stop optimising posts; apply `campaigns.yaml → funnel.interpretation` to the observations and change exactly one variable | owner | `scripts/outcomes.py` prints TRIGGERED | a diagnosed stage, not a redesigned surface |
| 10 | Cohort B films: only on gate A–D in the E2 brief (external evidence, a failed cold trial, a new empirical result, a contributor use case) | — | the gate, recorded in `films/LEDGER.md` | not a film; the evidence that justifies one |

Not on the queue, deliberately: more films, a wider census, an analytics
endpoint, a Discord, a newsletter, any monetisation. Each was considered and
adds cognitive load without improving conversion or evidence.
