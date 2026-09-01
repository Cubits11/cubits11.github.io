# E0 estimand file

Status: **draft for owner review**. Dated 2026-09-01. Bound to repo state
`57715f4` (= origin/main at the time this file was written). This file does
not itself compute any census count. Census numerals below are restated from
`claims.yaml` expected blocks and `docs/FRONTIER_ROADMAP.md` at that SHA.
Re-derive with `python3 scripts/verify_census.py` before any public use if
HEAD moves.

Evidential status of this file: **proposed protocol object**. It is not a
claim in `claims.yaml`. It is not Q1. It licenses no stack-safety sentence.

---

## 0. One question, one falsifier

**Question (programme, next phase):** When multiple AI safeguards are
evaluated on shared items at matched operating points with full exposure,
how much does observed joint failure differ from the stack risk implied by
independence — and does that difference change an actual deployment
decision?

**This file's job:** name the estimand so that later measurements cannot
quietly change the target.

**Falsifier of this file:** a later empirical page, claim, or post states a
stack result without naming which of `O`, `R_π`, or `R_π,a,t` it reports,
or reports an E0 number as the Q1 answer. Consequence: REJECT the page;
do not rescue by adding the missing label after the fact.

**Forbidden rescues:**
- do not relabel unmatched native-threshold arithmetic as matched-threshold
  measurement after seeing the numbers
- do not fold strata (harmful/benign, text/image, borderline) to move a
  ratio
- do not quote a position inside a Fréchet interval as a score
- do not treat an independence product as a null hypothesis test on a file
  whose operating points were not matched

---

## 1. Population

Three nested populations. Mixing them is a scope error.

| Label | Population | Status on 2026-09-01 |
|---|---|---|
| P0 | Public multi-system guardrail evaluations meeting Missing Column inclusion criteria v1, freeze 2026-08-27 | Bounded census. N = 20 at `census.yaml` via `verify_census.compute_counts` (`claims.yaml` MC-001 expected). Not a sample of an industry. |
| P1 | Shared-item matrices already released and pinned | BELLS 2025 per-item subset, `non_adversarial_prompts.csv` @ `507566c5` (MC-002). Multimodal Safeguard Bench `full_run` @ `fb6f32e6` (MC-004). |
| P2 | Prospective matched-operating-point matrix (E2 pilot — docs/E2_PILOT_V1_CUT.md) | Empty. No conforming dataset collected (CC-005). |

E0 uses P1 only, and only as an unmatched-thresholds demonstration.

The E2 pilot (docs/E2_PILOT_V1_CUT.md) requires a new P2: one item set,
one event definition, documented matched thresholds, full exposure. P2
does not exist in this repository today. (Naming: cc-framework E2 under
the CC-005 contract; the earlier "E1–E3" program labels are retired.)

---

## 2. Unit

The unit is **one pre-intervention item** `i` in a named stratum `s`,
scored by every eligible guard `g` in a named set `G`.

Not a session. Not a user. Not a vendor. Not a paper.

Strata are part of the unit definition. A count that pools strata after
seeing outcomes is a different estimand.

Declared strata already in the record:

- BELLS released subset (`claims.yaml` MC-002 expected): 82 harmful, 50
  benign, 38 borderline. Borderline is never folded into either other
  denominator.
- MSBench `full_run` (`claims.yaml` MC-004 expected): harmful-text 200,
  harmful-image 200, benign-text 250, benign-image 250.

---

## 3. Event

Let `A_g(i)` be guard `g`'s native predicate on item `i` (unsafe / flag /
block — whatever the source names).

Let `E_g(i)` be the **common event** used for composition. `E_g = A_g`
only when a source-defined translation exists.

Two events are in scope for the static estimand:

- **miss:** `E_g(i) = 0` (the guard does not catch item `i`)
- **all-miss:** `∩_g {E_g(i) = 0}`
- **union catch:** `∪_g {E_g(i) = 1}`

Identity, when the event is shared and the composition rule is
block-on-any: `all-miss = 1 − union` on the same denominator.

**Recorded event defects (do not paper over):**

- MC-004: the committed bit is a harness-normalized native `unsafe` mapped
  to `blocked`. The claim's own non-claim: this is not a shared-event catch
  statistic. Llama Guard 3 Vision and ShieldGemma 2 are different native
  predicates. E0 may compute Boolean OR of those bits. E0 may not call that
  OR a common-event union.
- MC-002: the columns are released binary verdicts at unstated default
  configurations. Event is "flagged in the released column." That is a
  file event, not a source-matched operating-point event.

Missing data (timeouts, errors, deterministic-pass columns) must carry a
stated scoring policy before they enter a denominator. ShieldGemma 2's
text-item zeros are a documented deterministic pass in the MSBench
release, not missing data (MC-004 forbidden rescue).

---

## 4. Operating-point definition

An operating point is a documented rule that turns a score or generation
into a binary decision.

**Matched** means: every `g ∈ G` is calibrated to the same declared
quantity on the same benign set (example: common false-positive rate),
and that calibration is written down before outcomes on the evaluation
set are inspected.

**Native** means: each guard is used at the threshold or decoding rule
its authors shipped.

E0 uses native points on P1. That is the demonstration, not the Q1
answer.

Census third rung at MC-001 expected `m_strata.threshold_documented_full_exposure`:
**0** of 20. That 0 is the load-bearing reporting fact. It does not
say the five joint-evidence rows are invalid.

Full exposure means every eligible guard scores every item. Sequential
routing censors later guards; that is a different estimand (`R_π`).

---

## 5. Estimand ladder (already named in FRONTIER_ROADMAP §1)

| Symbol | Name | Functional | Evidence required | E0 status |
|---|---|---|---|---|
| `O(s)` | Static all-miss | `P(∩_g miss_g \| s)` on a fixed pre-intervention item set | Full-shadow per-item outcomes, or a same-denominator union plus the marginals | Computable on P1 at *native* points. Not Q1. |
| `R_π(s)` | Operational route risk | Probability an unsafe terminal action survives route `π` | Replayable traces; predeclared ablations | Not computed. No route tensor in this repository. |
| `R_π,a,t(s)` | Adaptive robustness | Same, under a declared attacker budget and access, over time | Sealed holdout, versioned reruns | Not computed. |

Repository rule already written (`docs/FRONTIER_ROADMAP.md` §4.3): no
future empirical page may state a result without naming which of these
three it is about.

**Independence plug-in** (not an estimand): `Π_g p_g` where `p_g = P(miss_g)`.
It is one point inside the Fréchet set when that set is non-degenerate.
It is not a measurement.

**Identified set from marginals only** (`scripts/identification.py`, MC-003):

```
max(0, Σ p_g − (k−1))  ≤  O(s)  ≤  min_g p_g
```

Finite version with catch counts `c_g` on `n` items:

```
{ max(0, n − Σ c_g), …, n − max_g c_g }
```

Direction rule (theorem, not a finding): `O(s) ≤ min_g p_g`. Marginals
never certify that a static OR stack is better than its best member.
Never quote a location inside the interval as a score.

---

## 6. Decision set (frozen before E3; named now so E0 cannot invent it later)

Three decisions, fixed in advance of E3. E0 does not answer them.

1. **Add/remove guard k.** Deploy `G` versus `G \ {k}` under the same
   event, operating points, and exposure. Decision statistic: change in
   `O(s)` and in benign-union flag rate, with leave-one-out unions as
   the compact disclosure of exclusive full-stack coverage.
2. **Choose a pair under a budget.** Two candidate pairs; same item set;
   same event; matched points. Decision statistic: whether the ranking
   by independence products agrees with the ranking by observed
   `O(s)` and benign burden.
3. **Accept residual risk τ.** Pre-declare τ for the highest-risk
   stratum. Decision statistic: whether observed `O(s)` (or its upper
   confidence bound, method named later) is ≤ τ, and whether that
   inequality flips relative to `Π p_g`.

A negative result — dependence does not flip any of the three — is a
stated success mode (`docs/FRONTIER_ROADMAP.md` §2).

---

## 7. Null and competing explanations

Pre-committed, inherited from FRONTIER_ROADMAP §2:

1. Shared blind spots: observed `O(s)` sits near `min p_g`; added layers
   catch little of the residual.
2. Conditional complementarity: added layers catch a predeclared fraction
   of the residual at acceptable benign-union cost.
3. Sequential / adaptive collapse: `O(s)` looks favorable; `R_π` or
   `R_π,a,t` lose the gain.

Null for Q1 on a matched matrix: no detectable departure of observed
`O(s)` from `Π p_g` on that sample, at a pre-registered test. That
sentence is not "independence is true."

Null for E0: not defined as a hypothesis test. E0 is pipeline shakeout
plus an effect-size prior under *unmatched* points.

---

## 8. What E0 computes this week (zero new data)

On each P1 matrix, at native points, per released stratum:

- per-guard catch and miss counts
- union and all-miss
- product of miss rates
- Fréchet / finite identified set from those marginals
- leave-one-out unions and exclusive full-stack coverage
- ratio `observed all-miss / product`, printed only with the unmatched
  and selection caveats in the same sentence

Locator for the arithmetic already in CI:

- BELLS: `scripts/reanalyze_bells_subset.py` + `claims.yaml` MC-002
  expected block
- MSBench: `scripts/reanalyze_msbench.py` + `claims.yaml` MC-004
  expected block
- bounds: `scripts/identification.py` + MC-003 expected block

E0 does not download new files. E0 does not invent a third matrix.

---

## 9. Non-claims

This file does not show:

- that any vendor product is unsafe
- that dependence is large in deployment
- that the BELLS 3.1× ratio or any MSBench ratio is a law
- that unmatched-threshold OR bits are a matched-threshold stack
- that MJGD is a standard
- that P0 is representative of an industry
- that dual review of the census has been done (it has not; archival
  v1.0 gate remains)

---

## 10. Strongest objection to treating E0 as progress

The two matrices in hand fail the third census rung by construction.
Computing `O` on them produces numbers that look like Q1 and will be
quoted as Q1 unless this file is attached to every table. The honest
product of E0 is a *named target* plus a *labelled demonstration*, not
a finding about stacks.

What would change that objection: a P2 matrix with documented matched
thresholds and full exposure. That is the E2 pilot
(docs/E2_PILOT_V1_CUT.md). It has not started.
