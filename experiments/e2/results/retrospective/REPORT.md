# W1 — retrospective selection regret on the three existing per-item matrices

Native points, unmatched, retrospective. Nothing here licenses a public
sentence about any guard, vendor, or stack; every number is counting
arithmetic on released files at the operating points their authors shipped,
and the contract that governs it is `ARTIFACTS/12-WEEK-PROGRAM.md` §7, §8
W1 and §15. Executed 2026-09-02 on the 8 GB session host; no model loaded,
no frozen E2 item touched.

## T1 — BELLS-11, harmful stratum (n = 82), and the least favorable cell

`R(A) = U(A, J(A)) − U(A, M(A))` in items; M = highest marginal catch
(tie: fewer benign flags), J = highest measured union with A (tie: lower
benign union); bootstrap 95% CI on R with picks fixed, B = 2000, seed
`MC-E2-PILOT-V1-FREEZE-2026-09-01`.

| incumbent | marginal_choice | joint_choice | flip | regret (items, CI) | n | operating_point | stratum |
|---|---|---|---|---|---|---|---|
| lakera_guard | mistral-large-latest | mistral-large-latest | no | 0 [0,0] | 82 | native | harmful[all11] |
| prompt_guard | mistral-large-latest | mistral-large-latest | no | 0 [0,0] | 82 | native | harmful[all11] |
| langkit | mistral-large-latest | mistral-large-latest | no | 0 [0,0] | 82 | native | harmful[all11] |
| nemo | mistral-large-latest | gpt-4 | yes | 0 [−4,4] | 82 | native | harmful[all11] |
| llm_guard | mistral-large-latest | mistral-large-latest | no | 0 [0,0] | 82 | native | harmful[all11] |
| gpt-4 | mistral-large-latest | nemo | yes | 1 [−3,5] | 82 | native | harmful[all11] |
| claude-3-5-sonnet-20241022 | mistral-large-latest | nemo | yes | 1 [−3,5] | 82 | native | harmful[all11] |
| gemini-1.5-pro-latest | mistral-large-latest | nemo | yes | 2 [−2,6] | 82 | native | harmful[all11] |
| mistral-large-latest | gpt-4 | lakera_guard | yes | 1 [−2,4] | 82 | native | harmful[all11] |
| deepseek-ai/DeepSeek-V3 | mistral-large-latest | gpt-4 | yes | 0 [−4,4] | 82 | native | harmful[all11] |
| grok-2-latest | mistral-large-latest | lakera_guard | yes | 2 [−2,6] | 82 | native | harmful[all11] |

Locator for every row: `https://raw.githubusercontent.com/CentreSecuriteIA/bells_leaderboard/507566c5a4606c8e3dec0bd59a5c5fde62594951/data/non_adversarial_prompts.csv`
sha256 `791dd4b0a168f2eb5831b308083a492e83200a9fa82585643c739023b03f57c3`.

Summary line (frozen format): `regret max 2 items (2.4%) · incumbents with
CI>0: 0/11 · pairs with stratified OR ≥ 1.5: 23/36` (9 of the 45
prediction pairs have an undefined MH ratio, 0/0; 17 are +inf).

**Least favorable cell for the thesis:** the five specialized supervisors —
0 of 5 incumbents flip, every regret is 0, every CI is [0,0] — while all 6
pairs have Δ > 0 and all 6 keep a stratified OR ≥ 1.5. Joint measurement
moves the residual number and not one selection. Across all 29 incumbent
rows in the three sources, no regret CI excludes zero and the maximum
regret is 2 items.

Same table, five specialized supervisors: every incumbent's marginal and
joint pick coincide (nemo for four incumbents; lakera_guard for nemo);
regret 0 throughout; Fréchet all-miss count set [0, 12].

## The other two sources

**MSBench `full_run @ fb6f32e6`** (harness-normalized `blocked` bits; not a
shared-event catch statistic, MC-004). harmful_text n=200: all three
incumbents pick the other Llama Guard on both rules; regret 0; the single
non-degenerate pair (LG4 × LG3-Vision) has Δ +0.0318, MH OR 13.96 on one
stratum (ShieldGemma-2 is a deterministic pass, so the stratifier is
constant). harmful_image n=200: LG3-Vision catches 200/200, the Fréchet
all-miss set is [0, 0]; incumbent LG3-Vision "flips" by name only
(marginal pick shield_gemma_2, joint pick llama_guard_4 by the benign-union
tie-break, both unions 200), regret 0.

**Alotaibi et al. artifact @ `f517218b`** (adaptive breach, 100 JBB
behaviours, 7 defenses; catch = no breach; benign flag = refused on the
matched benign set). Every incumbent other than `llamaguard` picks
`llamaguard` on both rules (99/100 catch); `llamaguard` as incumbent picks
token_anomaly marginally and ppl_filter jointly, unions equal, regret 0.
All 21 pairs Δ > 0. Frozen statistic: 8 of the 15 live pairs keep MH OR ≥
1.5 with the stratifier "misses among the other 5 of 7 defenses"
(probe × probe_b 151.4; refusal_prime × smoothllm 4.27; ppl_filter ×
{refusal_prime 3.95, smoothllm 3.37, probe_b 3.07, probe 2.83}; probe_b ×
token_anomaly 2.56; smoothllm × token_anomaly 1.74).

## Frozen predictions — verdicts

- **(a) BELLS-11 — SURVIVED.** Point regrets reproduce exactly (0 for all
  five specialized incumbents; ≤ 2 items for the eleven, five of them > 0)
  and every 95% bootstrap CI on R includes 0 (0/11 with CI > 0).
- **(b) Alotaibi-7 — regret half SURVIVED, stratification count FAILED.**
  R = 0 for every incumbent including `llamaguard` (predicted ≤ 1). The
  prediction "exactly one of the fifteen measurable pairs (probe ×
  probe_b) keeps a stratified OR ≥ 1.5" is false: 8 of 15 do. Per the
  frozen §15 decision rule, the CMH implementation was checked against
  the artifact's own numbers (`confound_check.json`, the table
  `paper/SUPPLEMENTARY_ANALYSES.md` §A cites): using the artifact's
  convention (stratifier = the other *live* defenses, Llama Guard
  excluded; Haldane +0.5 crude OR) this implementation reproduces all 15
  of their CMH and crude values to a maximum absolute difference of
  8.9e-16. The implementation is right; the prediction was wrong because
  it equated the artifact's "survives" — a CMH χ² p-value criterion, 2 of
  15 pairs by their count — with the contract's OR ≥ 1.5 criterion, and
  because the contract's stratifier includes `llamaguard` among the
  "other guards". The criterion is not changed after the fact; the
  failure stands as recorded.
- **(c) MSBench — SURVIVED.** harmful_text regret 0 for all three
  incumbents; harmful_image identified set [0, 0].

## Discrepancies found before editing, and the rule applied

- **D1.** `analyze.py --rows` refuses to write inside the repository, but
  §15 names in-repo output paths. The refusal stays on the collection
  path; `--selection` writes to the contract path. The new code path only
  reads pinned public releases.
- **D2.** The artifact's difficulty test excludes Llama Guard from the
  stratifier and judges survival by a p-value; §7/§15 freeze the
  stratifier as "the other guards of the table" and the criterion as OR ≥
  1.5. The frozen statistic was run as written; the artifact's convention
  was computed only as the §15-mandated implementation check and is
  reported beside it, never in its place.
- **D3.** The contract does not say what an MH ratio with zero discordant
  mass is. Recorded as +inf when the numerator is positive (counted as ≥
  1.5) and as undefined for 0/0 (excluded from both numerator and
  denominator, count printed). On BELLS-11 this matters: 17 pairs are
  +inf and 9 undefined.
- **D4.** The contract does not say whether the bootstrap re-derives the
  picks per resample. Picks are held fixed at the full-data M(A), J(A);
  the CI is on the union difference of those two named candidates.
- **D5.** The Alotaibi artifact ships no hash manifest; the file hashes at
  commit `f517218b` were recorded at first fetch into `alotaibi_pin.json`
  and are asserted on every later run.

## Gate — frozen W1 rule, applied as written

"Fixture catches the planted inversion and both calculators agree to
1e-12 → CONTINUE; else fix before W2."

- `test_instrument.py` P10: `planted inversion caught` (X marginal-best, Y
  joint-best, regret exactly 70/200, CI > 0; no inversion without Y; the
  independent calculator refuses a corrupted primary). P11: MH exact on a
  hand-built two-stratum table. Eleven properties green.
- In-analyzer independent calculator (MJGD reference kernel unions,
  explicit-sort picks) agreed on every incumbent of every table.
- Independent T1 recomputation from the raw released rows, outside the
  reporting path (`independent_t1.py`, bitmask route): agrees with
  `bells11.json` on every pick, union, regret and benign union, exactly.

**GATE: CONTINUE.** The §15 rule for the failed stratification count was
executed (implementation check passed); nothing else in the rule is
triggered. This run does not advance to W2 and freezes nothing.

## Reproduce

```bash
python3 experiments/e2/run/analyze.py --selection --source bells11   --out experiments/e2/results/retrospective/bells11.json
python3 experiments/e2/run/analyze.py --selection --source msbench   --out experiments/e2/results/retrospective/msbench.json
python3 experiments/e2/run/analyze.py --selection --source alotaibi7 --out experiments/e2/results/retrospective/alotaibi7.json
python3 experiments/e2/run/test_instrument.py
python3 experiments/e2/results/retrospective/independent_t1.py --csv <non_adversarial_prompts.csv @ 507566c5> --compare experiments/e2/results/retrospective/bells11.json
```

`--cache DIR` reads previously fetched files from DIR instead of the
network; every file is still hash-checked. Pins: BELLS `507566c5` sha256
`791dd4b0…f57c3`; MSBench `fb6f32e6` — six guard files with the sha256
values in `scripts/reanalyze_msbench.py`; Alotaibi `f517218b` — nine files
with the sha256 values in `alotaibi_pin.json` (gold.jsonl
`0108fa10…2d48`). Output hashes at this run: bells11.json `7c640588…`,
msbench.json `1468def4…`, alotaibi7.json `57282ad0…`.

## Not done here

No W2 freeze, no threshold, estimator, hypothesis or criterion changed
after seeing results, no claims.yaml entry, no generated page, no
external action.
