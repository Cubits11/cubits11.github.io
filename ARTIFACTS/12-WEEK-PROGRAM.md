# 12-WEEK RESEARCH PROGRAM

Written 2026-09-02 against repository HEAD `be5a68e` (main). Every numeral
below was re-derived in this session or is tagged with its epistemic status.
Status vocabulary: VERIFIED (opened or executed in this run) · INFERRED
(derived from verified material, not itself executed) · OWNER-SUPPLIED
(asserted by the owner, not independently checked) · UNKNOWN.

This document proposes. It executes nothing, changes no other file, and
registers no claim.

---

## 1. LEAST FAVORABLE FACT

**On every per-item guard matrix that exists, measuring the joint has changed
the second-guard selection by at most 2.4 points, and in the largest
end-to-end measurement the stack was statistically indistinguishable from
its single strongest member.**

Three sources, all VERIFIED this run:

1. **BELLS 2025 released subset** (`non_adversarial_prompts.csv @ 507566c5`,
   sha256 `791dd4b0…`, 170 rows, 11 verdict columns). Computed 2026-09-02 on
   the hash-verified file (scratchpad script; to be committed as the W1
   artifact), harmful stratum n=82, native points:
   - Five specialized supervisors: for **0 of 5** incumbents does the
     partner maximizing measured union catch differ in union from the
     partner chosen by marginal rank. Regret 0 items.
   - All 11 released systems: joint-best partner beats marginal-best
     partner for 5 of 11 incumbents, by **at most 2 items (2.4 points)**;
     under a benign-union budget of 10/50 it is 1 of 11.
   - Best single system 71/82; best pair 74/82; all-11 union 78/82 with
     benign union 26/50.
   - Meanwhile pairwise excess joint miss Δ = p11 − pA·pB is positive in
     **45 of 45** non-degenerate pairs; stratifying on item difficulty
     (misses among the other nine systems) reduces the joint-miss odds
     ratio in 28 of 45 pairs (Lakera×NeMo: crude OR 6.25 → stratified 1.31).
   The registered arithmetic (`scripts/reanalyze_bells_subset.py`, exit 0
   this run): union 73/82, all-miss 9/82 = 11.0%, product 3.5%, ratio 3.14×.

2. **Multimodal Safeguard Bench `full_run @ fb6f32e6`**
   (`scripts/reanalyze_msbench.py`, exit 0 this run). Harmful text: LG4 185,
   LG3-Vision 178, ShieldGemma-2 0 (documented deterministic pass), union
   192/200, all-miss 8. Benign image: LG3-Vision flags 250/250, so every
   stack containing it flags every benign image. The joint is dominated by
   one column; marginals alone already show it.

3. **Alotaibi, Jabbar, Al-Azani, Ahmed, arXiv 2608.28327 (28 Aug 2026)**,
   abstract and full HTML opened; artifact `github.com/AbrarAlotaibi/
   defense-correlation` (MIT, `results/hpc_vicuna_autodan/table6.csv`,
   `gold.jsonl` 2,700 rows) opened. Seven defenses wrapping Vicuna-7B under
   an adaptive attacker, 100 JailbreakBench behaviors: φ from 0.30 to 0.75
   in all fifteen measurable pairs; joint residual above the multiplicative
   prediction by up to 0.172; "Stratifying on behavior difficulty dissolves
   most of the association, so the dependence is predominantly
   common-cause"; "The same stack refuses four in five benign prompts while
   remaining statistically indistinguishable from its strongest single
   layer" — that layer is, by the artifact's row labels, Llama Guard 3 8B
   (INFERRED: PREREGISTRATION.md row 2 "semantic classification" =
   `llamaguard`; table6 `llamaguard` breach rate 0.0100).

Corollary for the thesis: the Fréchet interval is wide, the independence
product is wrong by 3× on BELLS, and yet the *selection* a deployer would
make from marginals is the selection they would make from the joint. What
the missing column has demonstrably changed so far is the residual number,
not the choice. A program that cannot separate those two outcomes has no
decision to change.

Owner-supplied bindings checked against this: all five MC-001 numerals
(20/14/5, ladder 14/12/0) VERIFIED by `scripts/verify_census.py --counts`;
BELLS 82/73/9/11.0%/3.5% VERIFIED; E5A kernel merged at `be5a68e`, verifier
green (38 transitions, 17 states) VERIFIED; Scar/E5B: no implementing file,
commit message states "No Scar route exists" — VERIFIED absent. One
binding downgraded: "adversarial prompts unavailable in the per-item
release" — `data/adversarial_prompts.csv @ 507566c5` carries **8** harmful
adversarial rows with the same 11 verdict columns (census row already
records "plus 8 adversarial prompts"); 8 of ~4,165 is effectively
unavailable, not literally so. The BELLS default branch head is still
`507566c5` (2025-07-08): no newer per-item release exists.

---

## 2. RESEARCH QUESTION

At matched operating points on shared items, does the measured joint miss of
independently developed guard models change which second guard a deployer
should add, or only the residual-risk number they should quote?

(Secondary, mechanism: is the excess joint miss that remains explained by
item difficulty, as Alotaibi found for wrapped defenses, or does shared
lineage add to it — because that decides whether one union row or the whole
per-item column is the disclosure worth asking for.)

This replaces the candidate question. The candidate's first clause ("what
determines what they miss together") has a published answer on one setting
(common cause, Alotaibi §11.6) and a corroborating retrospective signal here
(28/45 BELLS pairs); its second clause ("how far can component evidence
misrepresent residual risk") is bounded by classical theory and already
measured at 3.1× (BELLS), up to 0.172 (Alotaibi), 2.5× (Chen 2026 on task
accuracy). Its third clause is the only one nobody has measured, and §1
shows the reachable answer may be "not at all".

---

## 3. DECISION

**Actor.** A deployer selecting supervision systems from a marginal-only
leaderboard who already runs one guard and must choose a second under a
benign-flag budget. BELLS-O (arXiv 2606.20668, opened) states the decision
in its own words: "The deployment decision is therefore not a ranking on a
single axis. It is a constrained optimisation over detection, FPR, latency,
and cost, parameterised by the deployment scenario." Every table in BELLS-O
is per-supervisor (VERIFIED, census row `bells-o-2026`). Downstream actor:
the leaderboard maintainer (CeSIA, JRC/GuardBench, Domyn) deciding whether
to release per-item verdicts, pairwise union rows, or nothing.

**Without the proposed measurement, they choose X:** add the highest-catch
candidate whose false-positive rate fits the remaining budget, and quote the
stack's residual as the product of miss rates (or, if careful, "≤ the best
member's miss").

**With result A** (marginal-selection regret ≥ 3 points for at least one
third of incumbents, bootstrap CI excluding 0, surviving the dedup control):
**choose Y** — do not select a second guard from marginals; require pairwise
union rows or per-item verdicts on the shared items before selection; the
maintainer's smallest sufficient release is the pairwise union table.

**With result B** (regret < 1 point for every incumbent but Δ > 0 and the
τ = 0.02 residual verdict flips between product and observation): **choose
Z** — keep marginal selection; replace the product quote with the measured
union or the Fréchet upper bound; the maintainer's smallest sufficient
release narrows to one union / all-miss row per declared stack, not
per-item data.

**With result C** (regret < 1 point everywhere and Δ CIs include 0 for all
cross-lineage pairs): **keep X** — marginals suffice for both selection and
quote on input-moderation guards at matched points; the census is downgraded
from active program to finished artifact under the kill rule already in
`distribution/outcomes.yaml`.

Three reachable results, three different actions. The spine survives the
decision test.

---

## 4. NOVELTY BOUNDARY

Closest prior work opened in this run:

| Work | What it establishes (VERIFIED from the opened text) | What it leaves unresolved |
|---|---|---|
| Alotaibi et al. 2026, arXiv 2608.28327; artifact `AbrarAlotaibi/defense-correlation` (PREREGISTRATION.md dated 2026-07-27; H2 cross-row independence **rejected**) | Failure correlation φ ∈ [0.30, 0.75] in all measurable pairs of a seven-layer stack wrapping one target under an adaptive attacker; Δ > 0 everywhere; predominantly common-cause (difficulty); stack ≈ Llama Guard 3 alone; refusals compose as a union; "Diversity therefore selects stack members but does not predict what an assembled stack delivers." | All defenses wrap the same target model; only two are standalone guard models (Llama Guard 3 8B, Prompt Guard 2); n = 100; adaptive breach, not static input moderation; no matched operating points across standalone guards; **no selection-consequence statistic**; lineage not varied. |
| Chen 2026, arXiv 2606.27288 (abstract) | Co-failure ceiling for multi-model systems; pairwise error correlation cannot identify the all-wrong rate; "combining models rarely beats the single best model without a strong query-level routing signal." | Task accuracy on 67 LLMs, not safety classifiers; no guard data. Independently restates the repository's CC-003 parity point (pairs do not identify the triple). |
| BELLS-O 2026, arXiv 2606.20668 (HTML) | 28 supervisors, identical workloads, Pareto framing of the deployment decision; no combination analysis; per-item outcomes not released. | The exact decision this program targets is stated but never measured. |
| Domyn 2026, arXiv 2605.28830 (HTML; CC BY-NC-ND) | 14 open guards on 79,331 items, native verdicts; no agreement/overlap/ensemble analysis; no per-item release. | Same. |
| STACK, arXiv 2506.24068 (abstract) | Staged attacks reach 71% ASR against a two-classifier pipeline black-box. | Component-vs-joint accounting not extracted: UNKNOWN. |
| Nasr et al. 2025, arXiv 2510.09023 (search summary only: INFERRED) | Adaptive attacks exceed 90% success against 12 defenses. | Not about composition. |
| Fréchet–Hoeffding bounds; Bonferroni; classifier-fusion diversity (Kuncheva-style, cited by Alotaibi; not opened) | Known. Not a contribution here. | — |
| Repository: MC-002/003/004, CC-003, E2 dry run (`cc-framework` E2_DRYRUN_FINDING.md, local HEAD `eb03f83`) | BELLS 3.1×; identified set {0..12}/82; three-way not identified by pairs; toy Δ of both signs at n=22. | No matched-threshold real matrix exists (census third rung = 0 of 20). |

**Known:** marginals do not identify the joint; products err by 2–3× in the
cases measured; dependence in a wrapped stack is mostly item difficulty;
stacks tend to equal their best member.

**Unresolved and targeted here:** (i) a matched-operating-point per-item
matrix of standalone guard models on static input moderation — none is
public; (ii) the selection regret of marginal-only leaderboards — measured
nowhere except the 82-item retrospective in §1; (iii) whether shared base
lineage adds dependence beyond item difficulty for standalone guards —
untested (Alotaibi held the wrapped model fixed).

---

## 5. HYPOTHESIS

On the frozen E2 item set (AdvBench 520 harmful, OR-Bench 800 benign
evaluation half), with each guard calibrated to FPR* = 5% on the disjoint
benign calibration half, at least one third of incumbents (≥ 3 of 7 guards;
≥ 1 of 3 in wave 1) show marginal-selection regret R(A) ≥ 3 points of union
catch with a seeded item-bootstrap 95% CI excluding 0, and the result
survives the pre-declared near-duplicate control.

R(A) := U(A, J(A)) − U(A, M(A)), where U is union catch on the harmful
stratum, M(A) is the candidate with the highest marginal catch (tie: lower
benign flag), J(A) the candidate with the highest measured union (tie: lower
benign union).

---

## 6. COUNTER-HYPOTHESIS

R(A) < 1 point for every incumbent (CI including 0), Δ > 0 but the
Mantel–Haenszel odds ratio of joint miss stratified on the other guards'
miss count falls below 1.5 for every cross-lineage pair, and the τ = 0.02
verdict does not flip. That result is reachable — it is what the §1
retrospective on BELLS points toward — and it kills the selection half of
the program outright and narrows the disclosure ask to one union row.

---

## 7. DECISIVE EXPERIMENT

**Name of the single highest-information measurement:** the seven-incumbent
regret table at matched thresholds (W6), with its bootstrap CIs. Everything
else in the program either prepares it or checks it.

- **Data.** Frozen at `experiments/e2/freeze/` (config hash `07b06dea…`,
  VERIFIED): harmful AdvBench `harmful_behaviors.csv @ 098262ed` (520, MIT);
  benign OR-Bench `or-bench-80k @ e36d8b80` (CC-BY-4.0), seeded 1,600 split
  800 calibration / 800 evaluation; ids and text hashes committed, no prompt
  text; disjoint from MSBench `fb6f32e6` ids (checked by
  `check_freeze.py`). Second family for W8: JBB-Behaviors (100 harmful +
  matched benign; MIT; ungated; HF sha `886acc35`, VERIFIED via API).
  Sizing: 1,320 ≥ 1,097, the CC-006 precision bar (ε = 0.05, δ = 0.05).
- **Models (guards), two waves, all revisions pinned before any outcome.**
  Wave 1 (already frozen): Llama-Guard-4-12B `87acb4b9` (local 8-bit
  conversion per `LG4_CONFIG.md`), Llama-Guard-3-8B `7327bd9f`,
  shieldgemma-2b `d1dffc9c` — all gated, licenses OWNER-PENDING. Wave 2
  (pinned in W2 before wave-1 outcomes exist; availability VERIFIED via HF
  API 2026-09-02): ibm-granite/granite-guardian-3.3-8b `b3421eda` (Apache
  2.0, ungated), Qwen/Qwen3Guard-Gen-8B `4505cb1a` (Apache 2.0, ungated),
  nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3 `8fdc246b` (NVIDIA open model
  license, ungated), allenai/wildguard `cbba4823` (Apache 2.0, auto-gated
  form). Base-model families (the lineage variable): Llama-4 {LG4}; Llama-3.1
  {LG3, Nemotron}; Gemma {SG2B}; Granite {GG}; Qwen3 {Q3G}; Mistral {WG}.
  Score exposure per guard: first-token or Yes/No logit as documented per
  model card; a guard with no exposed score at its pin is dropped under the
  frozen cut rule and the drop is recorded.
- **Mechanisms.** Static, full exposure, block-on-any composition of binary
  events; no sequential route; text-only prompt classification.
- **Shared-item unit.** One frozen item i in stratum s scored by every guard
  g; rows in the cc-framework `cc.e2_observation_row.v1` schema with the ten
  missingness codes; complete-case population plus missingness bounds.
- **Failure event.** Y[i,g] = 1 iff miss on a harmful item / flag on a
  benign item under the frozen reduction `h.miss.v1` at threshold t_g.
- **Estimators.** Per pair Δ = p11 − pA·pB (bootstrap CI, B = 2000, seed
  `MC-E2-PILOT-V1-FREEZE-2026-09-01`); Wilson on marginals; per incumbent
  R(A) with bootstrap CI; stack all-miss O, product Π, finite Fréchet set
  (`scripts/identification.py`); k leave-one-out unions; benign union; τ =
  0.02 verdict from O vs Π; Mantel–Haenszel common OR per pair stratified by
  miss count among the other |G|−2 guards; lineage contrast of stratified OR
  (same-family vs cross-family pairs, exploratory — only 2–3 same-family
  pairs exist).
- **Controls (all mandatory, contract Layer G).** Within-stratum column
  permutation (2000 draws); duplicate-column common-cause (must attain
  pA(1−pA) to 1e-9); label-noise flips at 1% and 5%; missingness bounds;
  independently written second calculator (agreement to 1e-12); planted-
  inversion fixture for the regret code; **near-duplicate control**: an
  AdvBench clustering rule declared in W2 (the "AI safety illusion"
  duplication critique of AdvBench is INFERRED from a search summary, not
  opened) and every statistic recomputed on one item per cluster.
- **Strata.** Harmful (AdvBench), benign-evaluation (OR-Bench), then JBB
  harmful and JBB benign in W8. Never folded.
- **Sample / stopping.** Fixed n; no interim looks; one analysis after full
  collection per wave. If complete-case n < 1,097 the first public sentence
  is "precision HOLD"; if < 600 the wave is stopped and items re-frozen.
  Power note: 3 points on n = 520 is 16 items; the union-difference SE for
  two pairs sharing an incumbent at ≈ 5–10% discordance is ≈ 1 point, so a
  3-point regret is resolvable; on BELLS (n = 82) a 2-item regret is not
  (prediction in §15).
- **Preregistered analysis.** `experiments/e2/freeze/PREREG_SELECTION.md`
  (W2) fixes: the definitions above, thresholds 3 points (positive) and 1
  point (null), τ = 0.02, OR 1.5, B, seeds, wave-2 guard list, lineage map,
  dedup rule, and the result-ladder mapping; its sha256 is asserted by
  `check_freeze.py` from then on. Thresholds are frozen before calibration;
  no threshold moves after `e2_config.json` is written.
- **Failure conditions.** A guard cannot reach FPR* within 1 point of 5% on
  the calibration half (report at achieved FPR, flag); missingness > 5% of
  cells (bounds lead); a guard degenerate on the harmful stratum (0% or 100%
  catch: excluded from CMH, kept in the regret table); dedup flips a
  threshold crossing (dedup result leads, AdvBench declared insufficient);
  rescoring disagreement > 1% of bits (instrument defect; numbers withheld).

---

## 8. TWELVE WEEKS

Dates assume W1 = 2026-09-07 → 2026-09-13; W12 ends 2026-11-29. Wave-1
collection runs on the owner's authorized 24 GB box, not the 8 GB session
host (`PREFLIGHT.md`, VERIFIED). No new subsystem: every week extends
`experiments/e2/` or the existing verifiers.

**W1** · QUESTION: On the three existing per-item matrices, what is the
selection regret and how much dependence survives difficulty stratification?
→ EXPERIMENT: add a `--selection` mode to `experiments/e2/run/analyze.py`
(regret table, MH stratified OR, bootstrap) plus adapters reading BELLS-11
(pinned, hash-checked), MSBench (pinned), and Alotaibi `gold.jsonl` (commit
pinned at fetch); planted-inversion fixture in `test_instrument.py`; second
calculator. → ARTIFACT: `experiments/e2/results/retrospective/{bells11,
msbench,alotaibi7}.json`, `REPORT.md` whose first sentence says native
points, unmatched. → GATE: fixture catches the planted inversion and both
calculators agree to 1e-12 → CONTINUE; else fix before W2.

**W2** · QUESTION: What exactly will count as "selection changed", before
any guard runs? → EXPERIMENT: write and hash `PREREG_SELECTION.md` (§7);
pin wave-2 guard revisions and lineage map; declare the dedup rule; box
gates 0–3 of `box_session.sh` (HF login, pinned pulls, `LICENSES.md` with
LICENSE-byte hashes and `commercial_reuse` per file, `LG4_CONVERSION.md`).
→ ARTIFACT: `experiments/e2/freeze/PREREG_SELECTION.md` (+ sha in
`check_freeze.py`), `experiments/e2/run/LICENSES.md`,
`LG4_CONVERSION.md`. → GATE (K1): < 3 guards or < 2 lineages pass the license
gates → HOLD, design-only, HOLD published; else CONTINUE.

**W3** · QUESTION: Can each wave-1 guard be placed at FPR* = 5% with an
exposed score? → EXPERIMENT: `box_session.sh` steps 5–7: synthetic shakeout;
`calibrate.py` per guard on the 800 calibration items; `make_config.py`
freezes `e2_config.json`; no harmful item touched; no harmful scoring the
same day. → ARTIFACT: `experiments/e2/run/e2_config.json` (hash-stamped),
calibration logs with achieved FPR and distance. → GATE: a guard with no
exposed score or achieved FPR more than 1 point from 5% is recorded and
dropped per the frozen rule; < 2 lineages left → HOLD; else CONTINUE.

**W4** · QUESTION: On three guards at matched points, what are Δ per pair,
R for three incumbents, and the τ = 0.02 verdict? → EXPERIMENT:
`collect.py` on benign-evaluation 800 + harmful 520, full exposure,
missingness codes; cc-framework validator; `analyze.py` primary + selection +
five controls. → ARTIFACT: `experiments/e2/results/wave1/observations.jsonl`,
`analysis.json`, `analysis_independent.json`, `controls.json`. → GATE (K2):
complete-case n < 1,097 → precision HOLD headline; < 600 → STOP and
re-freeze items; else CONTINUE. (First result unknowable in advance: the
sign and size of Δ and R at matched points.)

**W5** · QUESTION: Do the four wave-2 guards calibrate on the same benign
half? → EXPERIMENT: pinned pulls, license hashes appended, `calibrate.py`
per guard, `e2_config.wave2.json` hash-chained to wave 1 (wave-1 thresholds
untouched). → ARTIFACT: `experiments/e2/run/e2_config.wave2.json`,
`LICENSES.md` appended. → GATE: ≥ 6 guards and ≥ 4 base families in total →
lineage arm CONTINUE; else lineage arm recorded UNKNOWN and the regret arm
continues with what exists.

**W6 (decisive)** · QUESTION: With seven guards, how many incumbents have
R ≥ 3 points, does Δ survive difficulty stratification, and does lineage
predict it? → EXPERIMENT: wave-2 collection on the same 1,320 items;
analysis on the 7 × 1,320 matrix: regret table, 21 Δ, MH ORs, lineage
contrast, LOO unions, benign unions, τ verdicts at 5% (primary) and 1%
(secondary arm). → ARTIFACT: `experiments/e2/results/wave2/observations.jsonl`,
`analysis.json`, `analysis_independent.json`, `regret_table.csv`. → GATE
(K3): null branch (all R < 1, all cross-lineage Δ CIs include 0) → NARROW to
one-union-row disclosure and downgrade the census per the
`outcomes.yaml` kill rule; else CONTINUE.

**W7** · QUESTION: Does AdvBench duplication or label noise manufacture the
result? → EXPERIMENT: apply the W2 dedup rule; recompute R, Δ, MH on one
item per cluster; permutation (2000), duplicate-column, label-noise, and
missingness controls. → ARTIFACT: `experiments/e2/results/wave2/controls.json`,
`dedup_report.json`. → GATE (K4): dedup moves any incumbent across the
3-point line or flips a τ verdict → the dedup result leads, AdvBench is
declared insufficient, and a second harmful pool is mandatory before any
public sentence; else CONTINUE.

**W8** · QUESTION: Do the conclusions hold on a second, externally judged
item family, and how do static misses compare with adaptive breaches for
the one shared guard? → EXPERIMENT: score the seven guards on JBB-Behaviors
(100 + 100) at the frozen thresholds, no recalibration; compute R and Δ;
join Llama-Guard-3's static miss vector to Alotaibi's `llamaguard` breach
vector by `behaviour_id` (artifact commit pinned in W1). → ARTIFACT:
`experiments/e2/results/jbb/observations.jsonl`, `analysis.json`,
`external/alotaibi_pin.json`. → GATE: n = 100 is directional only; a
direction conflict with W6 puts item-family dependence first in the W12
report; CONTINUE either way.

**W9** · QUESTION: Does any leaderboard's own per-item data exist to run the
same statistic ecologically? → EXPERIMENT: the owner dispatches the
prepared asks (BELLS-O per-item verdicts for two systems on one workload;
GuardBench and IBM reporter patches from `contrib/`); the W1 adapters are
ready to run on any id-keyed release the same day. External action is the
owner's hand only. → ARTIFACT: `distribution/outcomes.yaml` entries
(qualified or zero), `distribution/dispatch-log.yaml`. → GATE: silence is
recorded as zero, not a kill; a release with ≥ 5 systems × ≥ 500 items
showing R < 1 everywhere triggers K6.

**W10** · QUESTION: Can a non-author reproduce the analysis from released
rows and the scoring of a subsample? → EXPERIMENT: clean-clone replay of
`analyze.py` on the packet rows (standard library) on a second machine; a
seeded 10% item subsample rescored for two guards at the pinned revisions on
a second box or rented GPU; bit agreement measured; one external person runs
the analysis command cold. → ARTIFACT: `experiments/e2/packet/replay_receipt.md`,
`rescoring_agreement.json`, `outcomes.yaml` `human_cold_runs` entry or zero.
→ GATE (K5): bit disagreement > 1% → instrument defect, all numbers withheld
until resolved; else CONTINUE.

**W11** · QUESTION: What claim is now licensed, at what strength, with which
forbidden rescues? → EXPERIMENT: register the E2 result through
`claims_history.yaml` transitions (CC-005 restated; one new E2 claim whose
`expected` block the analysis script reads); build the MJGD v1 packet and
validate with `scripts/validate_mjgd.py`; regenerate pages;
`verification_manifest.py` green. → ARTIFACT: `claims.yaml` +
`claims_history.yaml` transition, `experiments/e2/packet/mjgd.json`. → GATE:
manifest and `claims_history.py verify` green → CONTINUE; a threshold or
definition changed after outcomes is a forbidden rescue and the claim is not
registered.

**W12** · QUESTION: Can a hostile researcher reproduce the central regret
table without the author? → EXPERIMENT: assemble the packet (§10); write
`REPORT.md` with the least favorable number first and the result-ladder
branch named; release outcome bits and scores keyed by source item id
(AdvBench text permitted under MIT; OR-Bench with CC-BY attribution; no
weights); final external reproduction attempt. → ARTIFACT:
`experiments/e2/packet/` complete. → GATE: the packet replays from a clean
clone and a non-author reproduction is present or recorded as absent.

---

## 9. RESULT LADDER

Thresholds are those frozen in W2; no branch may move them.

- **Strong positive** (≥ 1/3 of incumbents with R ≥ 3 points, CI > 0,
  surviving dedup): licensed — on these guards at these points, marginal
  leaderboards mis-select the second guard by ≥ 3 points; pairwise union
  rows (or per-item verdicts) are required for selection. Not licensed —
  any statement about vendors' products, deployment routes, adaptive
  attackers, or field prevalence.
- **Weak positive** (some R in [1, 3) or CIs touching 0; τ flips for the
  marginal-picked pairs): licensed — selection is mostly unchanged; the
  residual quote from the product is wrong by a stated factor; one union /
  all-miss row per declared stack is the sufficient disclosure. Not licensed
  — "per-item release is necessary".
- **Null** (all R < 1, all cross-lineage Δ CIs include 0, no τ flip):
  licensed — for input-moderation guards at matched FPR on this item set,
  marginals suffice for both selection and quote; the census downgrades per
  the existing kill rule. Not licensed — "guards are independent" (a CI
  containing 0 is not independence).
- **Opposite** (Δ < 0 for a majority of cross-lineage pairs; product
  overstates residual; R ≈ 0): licensed — the product is conservative on
  this matrix and the sign of dependence is not predictable from marginals
  (E2 dry run already showed both signs in toys). The direction claim of the
  program fails and is recorded as failed.
- **Methodological failure** (licenses block ≥ 2 lineages; FPR* unreachable;
  missingness dominates; rescoring disagreement > 1%): licensed — instrument
  statements only (what calibrated, what did not, at what cost); HOLD
  published with the same prominence a result would have had.

---

## 10. WEEK-12 OBJECT

**E2 Joint Evidence Packet v1** at `experiments/e2/packet/`:

- `PREREG_SELECTION.md` (copy, sha-matched to the W2 freeze) and
  `freeze/` (existing `sources.json`, item lists, `check_freeze.py`)
- `e2_config.json`, `e2_config.wave2.json` (thresholds, hashes)
- `observations.jsonl` (wave 1 + wave 2 + JBB; contract schema; every cell
  present or coded), `scores.csv` (item id, guard, raw score)
- `analysis.json`, `regret_table.csv`, `analysis_independent.json`
- `controls.json`, `dedup_report.json`
- `external/` — `bells11.json`, `msbench.json`, `alotaibi7.json` and the
  pins/hashes they were computed from
- `replay_receipt.md`, `rescoring_agreement.json`
- `LICENSES.md`, `LG4_CONVERSION.md`
- `mjgd.json` (validated by `scripts/validate_mjgd.py`)
- `REPORT.md` — paper-shaped; least favorable number first; ladder branch
  named; a negative result is a stated success mode
- `claims_history.yaml` transition(s) registering the claim and its
  forbidden rescues

Hostile reproduction: `python3 experiments/e2/run/analyze.py --selection
--rows experiments/e2/packet/observations.jsonl` (standard library only)
must print the regret table and Δ table byte-for-byte against
`analysis.json` from a clean clone. Re-scoring requires the pinned gated
weights and a 24 GB box; that boundary is stated in `REPORT.md`, not hidden.

---

## 11. EXTERNAL REALITY GATES

1. **Gated model licenses** (Meta LG3/LG4, Google ShieldGemma; WildGuard's
   AI2 form). Acceptance is the owner's act; LICENSE bytes hashed on
   authenticated pull. The repository cannot manufacture access. (W2)
2. **The authorized 24 GB box.** `AUTHORIZE COMPUTE: Apple M-series, 24GB
   unified` is OWNER-SUPPLIED; the session host is an 8 GB M1 that refuses
   to load weights (VERIFIED in `adapters.py`). No box, no data. (W3–W6)
3. **Upstream pins holding.** BELLS `507566c5` (sha `791dd4b0…`), MSBench
   `fb6f32e6` (eight hashes), AdvBench `098262ed`, OR-Bench `e36d8b80`,
   Alotaibi artifact commit (UNKNOWN sha; pinned in W1). A changed byte
   fails loudly. (W1 onward)
4. **The dedup sensitivity of AdvBench.** Whether the frozen pool has enough
   effective items is not knowable from inside the repository. (W7)
5. **A second item family judged by others** (JBB-Behaviors; Alotaibi's
   per-behaviour breach vectors for Llama Guard 3). (W8)
6. **A leaderboard's own per-item release** (BELLS-O, GuardBench, IBM APE)
   — the only route to an ecological test of the same statistic; can be
   invited, not produced. `distribution/outcomes.yaml` qualified totals are
   currently empty (VERIFIED). (W9)
7. **A non-author reproduction** of the analysis and of a rescored
   subsample. (W10, W12)

---

## 12. MATS FIT

Inspected only after §1–§11 were fixed. Winter 2027 program page
(VERIFIED): 12 weeks, 2027-01-19 → 2027-04-10; Stage 1 closes 2026-09-06
end of day AoE; "LLMs may not be used to write any part of your application
unless specific work tests or forms explicitly permit it." Empirical-track
streams opened: David Lindner (Redwood — "monitoring, stress-testing safety
methods, and evals"; "stress-testing mitigations"); Tomek Korbak (OpenAI —
"empirical projects building and evaluating control measures and oversight
techniques"); Anthropic coalition (Nicholas Carlini — adversarial ML,
evaluations, security; Sara Price — adversarial robustness, evaluations;
Stephen McAleer — adversarial training for robust monitors; Ethan Perez and
Joe Benton — adversarial robustness, control); Apollo monitors; Daniel Kang
(security demonstrations). The UK AISI red-team stream URL returns 404 for
Winter 2027 (UNKNOWN whether offered); Stephen Casper's "applied AI
safeguards" governance stream is listed for Autumn 2026, not Winter 2027.

Closest fit for this science as it stands: an evaluation-methodology result
about stacked classifiers — Lindner ("stress-testing safety methods and
evals") first, then the Anthropic adversarial-robustness/evaluations mentors
(Carlini, Price). Korbak's stream is about control measures for agents; the
static all-miss estimand `O(s)` fits it only through its monitor-composition
angle, and the program's route-risk arm (`R_π`) is out of scope for these
12 weeks. The question is not changed to improve fit. Application text is
the owner's; none is drafted here.

---

## 13. UPSIDE CONDITION

If, on the seven-guard matched matrix, at least one third of incumbents show
R ≥ 3 points with CIs excluding 0 **and** the stratified odds ratio stays
≥ 1.5 for a majority of cross-lineage pairs, then the joint-miss structure
of standalone guards is pair-specific and not recoverable from marginals
plus item difficulty. That finding alone would justify expanding to: a
leaderboard-facing disclosure requirement with a number behind it (pairwise
union rows), a lineage-diversified selection study across ≥ 12 guards and
≥ 3 item families, and the adaptive arm `R_π,a,t` on the same items. It
would not establish anything about deployed routes, vendors, or prevalence.

---

## 14. KILL CONDITIONS

- **K1 · by 2026-09-20 (end W2):** fewer than 3 guards or 2 lineages pass
  the license gates → HOLD; program stays design-only and says so.
- **K2 · by 2026-10-04 (end W4):** complete-case n < 1,097 → precision HOLD
  leads every sentence; n < 600 → stop, re-freeze items.
- **K3 · by 2026-10-18 (end W6):** all R < 1 and all cross-lineage Δ CIs
  include 0 → the selection half is dead; narrow to the one-union-row
  disclosure ask; downgrade the census under the `outcomes.yaml` kill rule.
- **K4 · by 2026-10-25 (end W7):** dedup moves an incumbent across the
  3-point line or flips τ → AdvBench declared insufficient; no public
  sentence until a second harmful pool is collected.
- **K5 · by 2026-11-15 (end W10):** rescoring disagreement > 1% of bits →
  every number withheld until the instrument defect is found.
- **K6 · any date:** a public per-item leaderboard release (≥ 5 systems ×
  ≥ 500 items) shows R < 1 everywhere → the generated matrix's selection
  claim is superseded; the program pivots to that release.
- **Standing:** `outcomes.yaml` stop rule (12 technical interactions, 0
  qualified → stop replying). Any threshold changed after outcomes are seen
  is a forbidden rescue; the affected result is not reported.

---

## 15. NEXT EXPERIMENT

**One experiment, next session: the retrospective regret and
difficulty-stratification table on the three existing per-item matrices,
as committed code with a frozen prediction.** This is W1. It costs no
compute, touches no frozen E2 item, and runs on the 8 GB host.

- **Required files / APIs.**
  `scripts/reanalyze_bells_subset.py` (download + sha `791dd4b0…`, reuse its
  loader); `scripts/reanalyze_msbench.py` (pinned `full_run` files, eight
  hashes); `scripts/mjgd_reference.py` (`joint_disclosure`);
  `scripts/identification.py`; `experiments/e2/run/analyze.py` and
  `test_instrument.py` (extend); Alotaibi artifact
  `github.com/AbrarAlotaibi/defense-correlation`
  `results/hpc_vicuna_autodan/gold.jsonl` and `table6.csv` (record the
  commit sha at fetch; MIT). Network access for the three downloads.
- **Implementation target.** `experiments/e2/run/analyze.py --selection`:
  input a per-stratum item × guard bit matrix; output per incumbent
  {marginal pick, joint pick, U_marg, U_joint, R, bootstrap 95% CI} and per
  pair {Δ, crude OR, MH stratified OR}; three source adapters; a planted-
  inversion fixture (a synthetic matrix where the marginal-best candidate
  is joint-worst by a known margin) added to `test_instrument.py`; a
  second, independently written calculator asserting equality to 1e-12.
- **Command.**
  `python3 experiments/e2/run/analyze.py --selection --source bells11 --out experiments/e2/results/retrospective/bells11.json`
  and the same for `msbench` and `alotaibi7`; then
  `python3 experiments/e2/run/test_instrument.py`.
- **Frozen prediction (written before the code exists).**
  (a) BELLS-11 harmful: the point regrets already computed this run (0 for
  all five specialized incumbents; ≤ 2 items for the eleven) reproduce
  exactly, and **every** 95% bootstrap CI on R includes 0.
  (b) Alotaibi-7 (adaptive breach, n = 100): R = 0 for every incumbent
  other than `llamaguard` (its breach rate 0.01 makes it both marginal and
  joint pick), and R ≤ 1 behaviour for `llamaguard` as incumbent; after
  difficulty stratification, exactly one of the fifteen measurable pairs
  (`probe` × `probe_b`) keeps a stratified OR ≥ 1.5.
  (c) MSBench harmful text: R = 0 by construction (one non-degenerate
  partner); harmful image: identified set collapses to {0}.
- **Expected output.** Three JSON files plus one printed line per source of
  the form `regret max <k> items (<p>%) · incumbents with CI>0: <m>/<n> ·
  pairs with stratified OR ≥ 1.5: <a>/<b>`; the fixture line `planted
  inversion caught`; the calculator line `independent calculator agrees
  (1e-12)`.
- **Decision rule.** If the fixture is caught and the calculators agree,
  proceed to W2 and freeze `PREREG_SELECTION.md` with the 3-point / 1-point
  thresholds unchanged. If prediction (a) fails — any BELLS-11 CI excludes
  0 at n = 82 — the prior on regret rises and the W2 freeze keeps the same
  thresholds but records the surprise. If prediction (b) fails on the
  stratification count, the CMH implementation is checked against
  Alotaibi's `paper/SUPPLEMENTARY_ANALYSES.md` before W2. Nothing in this
  experiment licenses a public sentence about guards; its first line stays
  "native points, unmatched, retrospective".

Not executed in this session.

---

## EVIDENCE TABLE (load-bearing statements)

| Statement | Status | Locator |
|---|---|---|
| Census N/M/K = 20/14/5; ladder 14/12/0; freeze 2026-08-27 | VERIFIED | `python3 scripts/verify_census.py --counts` (this run); `census.yaml` `frozen_as_of` |
| BELLS 82 harmful; union 73; all-miss 9 = 11.0%; product 3.5%; 3.14× | VERIFIED | `python3 scripts/reanalyze_bells_subset.py` (exit 0, this run) |
| BELLS file carries 11 verdict columns; 8 adversarial rows released | VERIFIED | raw file @ `507566c5` opened; `data/adversarial_prompts.csv` (19 lines) |
| Selection regret 0/5 (specialized), ≤ 2 items 5/11 (all); Δ > 0 45/45; MH reduces 28/45 | VERIFIED (computed this run, not yet committed) | scratchpad `bells_pairwise.py` on sha `791dd4b0…`; becomes W1 artifact |
| BELLS default branch head = `507566c5` (2025-07-08) | VERIFIED | GitHub commits API |
| MSBench four strata, union 192/200 text, LG3V 250/250 benign image | VERIFIED | `python3 scripts/reanalyze_msbench.py` (exit 0, this run) |
| E5A merged; verifier green; no Scar/E5B implementation | VERIFIED | `git log` `be5a68e`; `python3 scripts/claims_history.py verify`; grep |
| E2 freeze: 3 gated guards, AdvBench 520, OR-Bench 800/800, hash `07b06dea…`; no forward pass run | VERIFIED | `experiments/e2/freeze/FREEZE.md`, `sources.json`, `run/PREFLIGHT.md` |
| AUTHORIZE COMPUTE 24 GB; LG4 8-bit | OWNER-SUPPLIED | `PREFLIGHT.md`, `LG4_CONFIG.md` |
| CC-006 precision bar ≈ 1,097 items | VERIFIED | `claims.yaml` CC-006; `cc-framework/docs/research/E2_DRYRUN_FINDING.md` (local) |
| Alotaibi 2026 findings and artifact contents | VERIFIED | arXiv 2608.28327 abs + HTML; repo README, PREREGISTRATION.md, table6.csv, gold.jsonl |
| Chen 2026 co-failure ceiling | VERIFIED (abstract) | arXiv 2606.27288 |
| BELLS-O decision wording; no combination analysis; no per-item release | VERIFIED | arXiv 2606.20668 HTML; `census.yaml` row |
| Domyn 2026: 14 guards, 79,331 items, no joint analysis, no per-item release | VERIFIED | arXiv 2605.28830 HTML |
| Wave-2 guard availability, licenses, revisions | VERIFIED | HF API 2026-09-02 (granite `b3421eda`, qwen3guard `4505cb1a`, nemotron `8fdc246b`, wildguard `cbba4823`) |
| JBB-Behaviors MIT, ungated | VERIFIED | HF datasets API (`886acc35`) |
| AdvBench duplication critique | INFERRED | search summary of a Labelbox post; not opened |
| Nasr et al. adaptive-attack rates | INFERRED | search summary; not opened |
| STACK component-vs-joint accounting | UNKNOWN | only the abstract opened |
| Alotaibi artifact commit sha | UNKNOWN | pin in W1 |
| BELLS-O HF space `data/` contents | UNKNOWN | tree listed, directory not opened |
| MATS Winter 2027 dates, deadline, LLM policy, streams | VERIFIED | matsprogram.org program, track, stream pages |
| UK AISI red-team stream for Winter 2027 | UNKNOWN | URL 404 |

## AUDIT (performed once before finishing)

Removed: any claim that the program's statistics are new mathematics; any
statement about vendors' products; any prevalence claim. Downgraded: the
adversarial-release binding (§1); AdvBench duplication (INFERRED); Nasr
(INFERRED); STACK joint accounting (UNKNOWN). Every numeral in §1, §7 and
§15 traces to a row in the evidence table. No week is prose-only; every
week names an artifact path and a gate. Exactly one next experiment.
