# Dispatch-ready drafts — PREPARED, NOT SENT

The owner sends; nothing in this repository sends anything. Items A and B
were reported sent by the owner on 2026-09-02 (permalink to be recorded in
`distribution/dispatch-log.yaml`); the rest have not been sent. Re-derive every numeral at the
dispatch commit (`python3 scripts/verification_manifest.py` green first).

## A. IBM contribution ask — SENT (owner-reported 2026-09-02) — RESPONSE PENDING

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

## B. The patch — SENT (owner-reported 2026-09-02, attached to A) — RESPONSE PENDING

`contrib/ape_joint.py` — tested by `contrib/test_joint_reporters.py` (brute-force
agreement, every input-contract refusal via the CLI with the declared exit
status, `.json` filename normalisation, pickle trust boundary disclosed).

## C. Same Scores feed-native post — PREPARED — NOT SENT

Artifact: `films/same-scores__social-square/renders/same-scores__social-square__square.mp4`
(1080×1080, 11 s, silent). Text (from `distribution/launch-units.yaml`, unit `same-scores__social-square`):

> Two guardrails each miss 10%.
> From those two scores alone, their joint miss rate can be anywhere from 0% to 10%.
> 1% is what independence selects — not what the scores imply.
> Constructed example. Run the 60-second proof: cubits11.github.io/try/#try-a

No thread. No biography. No second film. IBM is not mentioned or tagged.
Campaign `x-film-same-scores` (design: ecological_descriptive). Prerequisite:
the cold comprehension gate in `distribution/launch-units.yaml` has passed.
Before posting, freeze the account's baseline analytics; record snapshots at
T+36h, T+7d, T+14d in `campaigns.yaml` funnel observations with denominators.

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
