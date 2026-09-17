# Dossier — bells-misuse-2025

Row: `bells-misuse-2025` · classification PRESENT (computable_via_item_release) · reconstruction PARTIALLY_IDENTIFIED · status: SENT September 16, 2026 (America/New_York), RESPONSE PENDING.

Issue: https://github.com/CentreSecuriteIA/bells_leaderboard/issues/1 · sent 2026-09-17T03:19:51Z · zero comments when verified.

**1. What the source publishes.** Per-supervisor results for twelve systems, and a released per-item subset: 170 non-adversarial prompts (82 harmful, 50 benign, 38 borderline) with binary verdict columns for five specialized supervisors, at a pinned commit (`507566c5…`, hash-verified in CI). Nothing joint is printed; the headline population's per-item outcomes and the ~4,165 adversarial prompts have no per-item release. The subset's selection rule is unstated.

**2. What can be reconstructed.** Exactly, on the released subset: union 73/82, all-miss 9/82, leave-one-out unions 55/70/73/73/73, benign union 19/50 (MC-002; `python3 scripts/reanalyze_bells_subset.py` — TRY-B). Bounded only, on the rest: the identified set from the published marginals (MC-003).

**3. What remains unidentified.** The joint behaviour on the unreleased 96.5 % of prompts; the selection rule for the 170; whether the released verdicts are at the configurations the paper's marginals used.

**4. Smallest missing artifact.** Either (a) one sentence stating how the 170 prompts were selected, or (b) the same five verdict columns for the remaining non-adversarial prompts (no prompt text is needed — item ids and bits suffice).

**5. Smallest action the maintainer can perform.** Reply with the selection rule (one sentence), or confirm that the released columns are the paper's supervisors at the paper's configurations (one yes/no).

**6. Can we do 90 %+ of the work?** The reproduction is already done and public; a wider release needs nothing from us except the same script re-run. No patch is required.

**7. Success condition.** An author reply that confirms or corrects the row (`source_corrections`, agreed true or false), or a wider per-item release (`paired_outcome_releases`) that the reproduction script is then extended to cover, with the expected block re-registered.

**8. Correction condition.** Evidence that a released column is not the labelled system's verdict, that the subset was released with a stated rule the row misreports, or that a fuller per-item release existed on or before 2026-08-27. Any of these corrects MC-002 or the row under their registered falsifiers.

**The ask, verbatim (as posted):**

> Thank you for releasing per-item supervisor verdicts in `data/non_adversarial_prompts.csv`.
>
> At commit `507566c5a4606c8e3dec0bd59a5c5fde62594951` the file has 170 rows, 82 of them with `harm_level` = `harmful`. On 9 of those 82 rows, all five specialized-supervisor columns (`lakera_guard`, `prompt_guard`, `langkit`, `nemo`, `llm_guard`) are 0. This script downloads the file at that commit, checks its SHA-256, and recomputes the count: https://github.com/Cubits11/cubits11.github.io/blob/4b659fb97bf50aff9793ff4a26c3410b7cf0a53c/scripts/reanalyze_bells_subset.py
>
> Your FAQ and the paper's Dataset Access appendix call the playground rows "representative examples". How were these 170 prompts selected from the full non-adversarial set? A sampling rule, a filter, manual choice, or a link to an existing description would answer it.
>
> I report 9/82 only as a count on these 170 released rows, not as an estimate for the full benchmark or for any deployed system. If I have misread the release, a correction is just as useful.

**Channel.** GitHub issues on `CentreSecuriteIA/bells_leaderboard` (the row's recorded route). One message.
