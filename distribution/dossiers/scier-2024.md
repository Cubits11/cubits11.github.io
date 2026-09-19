# Dossier — scier-2024

Row: **none — this is not a census row.** Classification ABSENT
(computable_via_prediction_release) · reconstruction UNIDENTIFIED · status:
**PREPARED, NOT SENT**.

Every other dossier in this directory derives from a row in `census.yaml`.
This one does not, and adding one would widen a guardrail census to scientific
information extraction. That is an owner decision recorded in
`distribution/TEMPLE-2026-09-19.md`, not a side effect of preparing an ask. The
dossier is written first so the decision can be made against a real artifact
instead of a description.

Target: `TUDMLab/SciER` — the dataset release for *SciER: An Entity and
Relation Extraction Dataset for Datasets, Methods, and Tasks in Scientific
Documents*, EMNLP 2024, pages 13083–13100 (Zhang, Chen, Pan, Caragea, Latecki,
Dragut). Two of the six authors are at Temple.

**1. What the source publishes.** The dataset, at commit
`db347813de379eb200e0813bbfee350d67e7c701`. Two test splits are released as
JSONL under `SciER/LLM/`: `test.jsonl` (854 sentences, 10 documents, 2,948
entity mentions — Method 1,890, Task 688, Dataset 370 — and 1,626 relations)
and `test_ood.jsonl` (580 sentences, 6 documents, 1,295 mentions — Method
1,018, Task 194, Dataset 83 — and 582 relations). Both are hash-pinned and
recounted by `scripts/reanalyze_scier_testset.py`. The paper reports three
supervised extractors on these splits — PURE, PL-Marker, HGERE — and LLM
baselines. The repository contains no predictions or outputs directory.

**2. What can be reconstructed.** The denominators, exactly: 4,243 entity
mentions across the two test splits. Nothing joint. Per-extractor scores are
published in the paper as marginals; no per-item outcome for any extractor is
released.

**3. What remains unidentified.** How many of the 4,243 mentions all three
extractors missed simultaneously; equivalently, every cell of the 2³ agreement
partition. Per-extractor F1 bounds that count and does not determine it. The
same holds for the relation task and for the LLM baselines.

**4. Smallest missing artifact.** Three id-keyed prediction files over the
released test split — one per extractor, entity spans only, no scores and no
model weights. The dataset is already public, so the predictions carry no
additional release burden.

**5. Smallest action the maintainer can perform.** One integer: of the 2,948
entity mentions in `test.jsonl`, how many were recalled by none of PURE,
PL-Marker and HGERE. No meeting, no re-run if the prediction files were
retained.

**6. Can we do 90 %+ of the work?** The counting side is done and public
(`scripts/reanalyze_scier_testset.py`, pinned and hash-verified). The joint
arithmetic already exists in this repository as `scripts/mjgd_reference.py`
and the id-aligned reporter pattern in `contrib/guardbench_joint.py`, which
aligns on item id and refuses otherwise. Neither has been adapted to SciER's
span format, because adapting a reporter to a prediction file that does not
exist would be scaffolding. **No patch is prepared, and that is deliberate.**
If the predictions arrive, the adapter is an afternoon.

**7. Success condition.** Either the one integer, verified against the pinned
split, or a prediction release that makes the 2³ partition computable. A
release is `paired_outcome_releases`; a maintainer statement that corrects
this dossier's reading of what is published is `source_corrections`. Neither
is credited until inspected under `distribution/EXTERNAL_EVENTS.md`.

**8. Correction condition.** Evidence that per-item predictions for these
extractors were already public on or before 2026-09-19 — in the repository, an
appendix, or a separate artifact — corrects point 1 and voids the ask. So does
evidence that the three extractors were not evaluated on a shared item pool,
which would make the all-miss count undefined rather than unidentified. I
searched the repository listing and the README and found no predictions
directory; I did not have authenticated access to the paper's supplementary
material from this host.

**Channel.** The project's own issue tracker,
`https://github.com/TUDMLab/SciER/issues`. One message. The owner sends.

**Verification limits, from this host.** `raw.githubusercontent.com` is
reachable and every byte counted above was downloaded and hashed here.
`github.com` HTML is not reachable for out-of-scope repositories from this
session (403 at the egress proxy), so the issue tracker's existing contents
were **not** inspected. The duplicate check in
`distribution/issues/2026-09-19-scier-joint-predictions.md` is therefore
outstanding and must be done in the browser at send time, as the GuardBench
draft's was.
