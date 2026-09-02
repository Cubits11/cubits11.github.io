# Dossier — ibm-adversarial-prompt-2025

Row: `ibm-adversarial-prompt-2025` · classification ABSENT · reconstruction PARTIALLY_IDENTIFIED · status of this dossier: PREPARED, nothing sent.

**1. What the source publishes.** Per-defence metrics (AUC, accuracy, F1, and per-dataset TPR/FPR) for fifteen defences on identical malicious and benign prompt pools, with released code (`IBM/Adversarial-Prompt-Evaluation`). No union, all-miss, overlap, or leave-one-out statistic; the paper's own conclusion that no single guardrail suffices is stated without a number about more than one.

**2. What can be reconstructed.** The harness saves, per defence and data file, `result_<model>_<data>.pickle` containing `x_test`, `y_test`, `y_pred` and `source` in prompt order. Anyone holding those pickles for two or more defences can compute union detection, all-miss, leave-one-out unions and exclusive coverage per source dataset exactly — the joint column is one script away. From the published marginals alone, the all-miss rate is identified only to `[max(0, Σp − (k−1)), min p]` (MC-003).

**3. What remains unidentified.** Everything joint: which prompts several defences miss together, whether a second defence adds exclusive coverage, and the benign union-flag burden. The pickles are not published, so the identified set cannot be closed from outside.

**4. Smallest missing artifact.** One line per source dataset: `union / all-miss / leave-one-out unions` at the saved decision rules, for any two or more of the fifteen defences. No prompt text and no per-item release is needed to print it.

**5. Smallest action the maintainer can perform.** Run one script against pickles they already have and paste its output into a README table or an issue reply. Or merge the script so future runs print it.

**6. Can we do 90 %+ of the work?** Yes. `contrib/ape_joint.py` is written against their exact pickle schema, uses the standard library only, refuses on misaligned prompts, and is proven on harness-shaped fixtures (`contrib/test_joint_reporters.py`). The remaining 10 % is running it on their machine.

**7. Success condition.** Either (a) a PR adding `scripts/main_joint_report.py` (the contrib file, renamed) is merged — `upstream_prs`; or (b) a maintainer posts union / all-miss for ≥2 defences on one data file — `paired_outcome_releases`; and the row's `joint_statistic_evidence` is updated and the classification moves to PRESENT with a dated revision entry.

**8. Correction condition (what proves our row wrong).** A public artifact dated on or before 2026-08-27 in which the paper, repository, or a release prints any joint statistic over two or more of the defences, or releases aligned per-prompt outcomes for two or more. That flips the row to PRESENT with the census's own falsifier, credited to whoever shows it.

**The ask, verbatim (owner sends via the repository's issue tracker):**

> We reconstructed your per-defence numbers' identified set from Table 2 alone: with those marginals, the fraction of prompts *all* defences miss is only bounded, not determined. Your harness already saves `result_<model>_<data>.pickle` with `y_pred` per prompt, so the joint numbers are one script away. I prepared `main_joint_report.py` (standard library, refuses on misaligned prompts): it prints union / all-miss / leave-one-out per source dataset. Would you accept it as a PR — or run it once on any two defences and paste the line?

**Channel.** GitHub issues on `IBM/Adversarial-Prompt-Evaluation` (the row's recorded route). One message. Silence after one message is the default.
