# Dispatch-ready drafts — PREPARED, NOT SENT

Every item below is ready to send and has not been sent. The owner sends;
nothing in this repository sends anything. Re-derive every numeral at the
dispatch commit (`python3 scripts/verification_manifest.py` green first).

## A. IBM contribution ask — PREPARED — NOT SENT

Channel: a single issue on `IBM/Adversarial-Prompt-Evaluation`. Attach or
link `contrib/ape_joint.py` as the proposed `scripts/main_joint_report.py`.

> Your `main_evaluate.py` already preserves what the paper's tables cannot
> show: `result_<model>_<data>.pickle` holds each defence's per-prompt
> `y_pred` on the same shared prompt pool. From the published marginals alone
> the share of prompts *every* defence misses is only bounded, not determined.
>
> The attached script (`main_joint_report.py`, standard library) reads two or
> more of those pickles, refuses unless prompts, labels and sources are
> identical and in the same order (exit 2, nothing counted), and prints per
> source dataset: union detection, all-miss, leave-one-out unions, exclusive
> coverage, and the benign union flag count. It is counting arithmetic at
> each defence's saved decision rule — not a dependence estimate, not a
> ranking, not a deployed route.
>
> Would a PR adding it under `scripts/` be useful? If not, the smallest
> useful result is one line: for any two defences on either data file, the
> union and all-miss counts over the malicious prompts.

## B. The patch — PREPARED — NOT SENT

`contrib/ape_joint.py` — tested by `contrib/test_joint_reporters.py` (brute-force
agreement, every input-contract refusal via the CLI with the declared exit
status, `.json` filename normalisation, pickle trust boundary disclosed).

## C. Same Scores feed-native post — PREPARED — NOT SENT

Artifact: `films/same-scores__social-square/renders/same-scores__social-square__square.mp4`
(1080×1080, 11 s, silent). Text (from `distribution/launch-units.yaml`, unit `same-scores__social-square`):

> Two guardrails. Each misses 10 of 100. How many of the 100 do they jointly
> miss? Anywhere from 0 to 10 — the scores never move. Independence picks 1%;
> nothing in the scores does. 11 s, sound off. Run the 60-second proof
> yourself: cubits11.github.io/try

No thread. No biography. No second film. Campaign `x-film-same-scores`
(design: descriptive); record the dispatch date in `campaigns.yaml` readings.

## D. Canonical URLs

- https://cubits11.github.io/try/
- https://cubits11.github.io/try/#try-a
- https://cubits11.github.io/try/#counterexample
- https://cubits11.github.io/ledger/#CC-001
- https://github.com/Cubits11/cubits11.github.io/issues/new?template=reproduction.yml
- https://github.com/Cubits11/cubits11.github.io/issues/new?template=counterexample.yml

## E. Fallback one-integer ask — PREPARED — NOT SENT

If the PR is declined or unanswered after one week, the smallest request,
in one sentence, on the same issue:

> For any two defences on `sub_sample_filtered_data.json`, how many
> malicious prompts did both miss?

One integer. No meeting. Silence after that is recorded as silence.
