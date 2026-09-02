# Dossier — bells-misuse-2025

Row: `bells-misuse-2025` · classification PRESENT (computable_via_item_release) · reconstruction PARTIALLY_IDENTIFIED · status: PREPARED, nothing sent.

**1. What the source publishes.** Per-supervisor results for twelve systems, and a released per-item subset: 170 non-adversarial prompts (82 harmful, 50 benign, 38 borderline) with binary verdict columns for five specialized supervisors, at a pinned commit (`507566c5…`, hash-verified in CI). Nothing joint is printed; the headline population's per-item outcomes and the ~4,165 adversarial prompts have no per-item release. The subset's selection rule is unstated.

**2. What can be reconstructed.** Exactly, on the released subset: union 73/82, all-miss 9/82, leave-one-out unions 55/70/73/73/73, benign union 19/50 (MC-002; `python3 scripts/reanalyze_bells_subset.py` — TRY-B). Bounded only, on the rest: the identified set from the published marginals (MC-003).

**3. What remains unidentified.** The joint behaviour on the unreleased 96.5 % of prompts; the selection rule for the 170; whether the released verdicts are at the configurations the paper's marginals used.

**4. Smallest missing artifact.** Either (a) one sentence stating how the 170 prompts were selected, or (b) the same five verdict columns for the remaining non-adversarial prompts (no prompt text is needed — item ids and bits suffice).

**5. Smallest action the maintainer can perform.** Reply with the selection rule (one sentence), or confirm that the released columns are the paper's supervisors at the paper's configurations (one yes/no).

**6. Can we do 90 %+ of the work?** The reproduction is already done and public; a wider release needs nothing from us except the same script re-run. No patch is required.

**7. Success condition.** An author reply that confirms or corrects the row (`source_corrections`, agreed true or false), or a wider per-item release (`paired_outcome_releases`) that the reproduction script is then extended to cover, with the expected block re-registered.

**8. Correction condition.** Evidence that a released column is not the labelled system's verdict, that the subset was released with a stated rule the row misreports, or that a fuller per-item release existed on or before 2026-08-27. Any of these corrects MC-002 or the row under their registered falsifiers.

**The ask, verbatim:**

> Your released 170-prompt subset lets anyone recompute what the five specialized supervisors miss *together*: 9 of 82 harmful prompts, against an independence plug-in of 2.87 — and the leave-one-out unions show three of the five add no exclusive coverage on that stratum. One question so the row about your work is right: how were the 170 prompts selected? If the row is wrong, say so — corrections land dated in the public file.

**Channel.** GitHub issues on `CentreSecuriteIA/bells_leaderboard` (the row's recorded route). One message.
