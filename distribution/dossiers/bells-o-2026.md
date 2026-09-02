# Dossier — bells-o-2026

Row: `bells-o-2026` · classification ABSENT · reconstruction PARTIALLY_IDENTIFIED · status: PREPARED, nothing sent.

**1. What the source publishes.** The largest supervisor comparison in the census — 28 systems from 17 providers on identical workloads under one harness — with every published number per-supervisor.

**2. What can be reconstructed.** From the marginals alone: only the identified set of the all-miss rate (MC-003). Per-item outcomes exist privately by construction (the harness's own output), so a release of any two systems' verdicts on one workload would make union, all-miss and leave-one-out exact.

**3. What remains unidentified.** All joint quantities for all pairs and stacks of the 28.

**4. Smallest missing artifact.** For one workload: item id → verdict for any two systems, or the five leave-one-out scalars for any declared stack. No prompt text.

**5. Smallest action the maintainer can perform.** Attach one workload's per-item verdicts (two systems) to a release, or print one union / all-miss row in the leaderboard.

**6. Can we do 90 %+ of the work?** If verdicts are released keyed by item id, `contrib/guardbench_joint.py` computes the joint row unchanged (its input is exactly id → score plus id → label). We can run it and file the numbers within the day.

**7. Success condition.** `paired_outcome_releases` — a per-item or leave-one-out release for at least one workload and two systems; the row moves to PRESENT with a dated revision.

**8. Correction condition.** Any public artifact on or before 2026-08-27 printing a joint statistic over two or more of the 28, or releasing aligned per-item verdicts. The row flips under the census falsifier, credited.

**The ask, verbatim:**

> BELLS-O compares 28 supervisors on identical workloads, so the one quantity a deployer of two of them needs — what both miss together — is already sitting in your harness output. Would you release item-level verdicts for any two systems on one workload (ids and bits, no prompt text), or print one union / all-miss row? I can run the joint arithmetic the same day and credit the release.

**Channel.** GitHub issues on `CentreSecuriteIA/BELLS-O`. One message.
