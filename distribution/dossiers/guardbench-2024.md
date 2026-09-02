# Dossier — guardbench-2024

Row: `guardbench-2024` · classification ABSENT · reconstruction PARTIALLY_IDENTIFIED · status: PREPARED, nothing sent.

**1. What the source publishes.** Thirteen guardrail models on forty datasets under one harness (`AmenRa/guardbench`, EUPL-1.2), with per-model precision / recall / F1 (and a leaderboard). Every published number is a marginal.

**2. What can be reconstructed.** The library writes `results/<dataset>/<model>.json` — item id → unsafe probability — and each dataset's `test.jsonl` carries `id` and a boolean `label`. With two or more result files for one dataset, union, all-miss, leave-one-out and exclusive coverage at the 0.5 threshold are exact and id-aligned. The results directory is not published; from the leaderboard's marginals alone the all-miss rate is only bounded (MC-003).

**3. What remains unidentified.** Every joint quantity, for every dataset, for every pair of the thirteen models.

**4. Smallest missing artifact.** For one dataset: the `results/<dataset>/` directory for any two models (two JSON files of id → probability), or the one line a reporter prints from them.

**5. Smallest action the maintainer can perform.** Publish one dataset's results directory as a release asset, or merge a reporter so `Report` can print the joint row beside the marginals.

**6. Can we do 90 %+ of the work?** Yes. `contrib/guardbench_joint.py` reads their exact file layout (`results/<dataset>/<model>.json` + `test.jsonl`), standard library only, refuses on id mismatch, proven on harness-shaped fixtures. Integrating it into `guardbench.report.Report` as an optional `joint=True` column is a small follow-up we can also draft.

**7. Success condition.** A merged PR adding `scripts/joint_report.py` (`upstream_prs`), or a published results directory for one dataset from which we re-run the reporter and file the numbers (`paired_outcome_releases`); the row moves to PRESENT with a dated revision entry.

**8. Correction condition.** A public artifact on or before 2026-08-27 — paper, docs, leaderboard, or release — printing a union / all-miss / overlap for two or more of the thirteen models, or releasing a results directory. The row flips to PRESENT under the census falsifier, credited.

**The ask, verbatim:**

> GuardBench already writes `results/<dataset>/<model>.json` keyed by item id, so the one number the leaderboard cannot show — how many unsafe items *every* compared model missed — is exactly computable and one script away. I prepared `joint_report.py` (standard library; aligns on id, refuses otherwise): union, all-miss, leave-one-out and exclusive coverage per dataset at the 0.5 threshold. Would you accept it under `scripts/`, or publish one dataset's results directory so anyone can run it?

**Channel.** GitHub issues on `AmenRa/guardbench`. One message.
