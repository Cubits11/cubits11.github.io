# Contribution dossiers

One per census row where an outsider's smallest action could change the
record (P9). Each dossier derives, from the row's own evidence in
`census.yaml` and from the harness's public code:

1. what the source actually publishes;
2. what can be reconstructed from it;
3. what remains unidentified;
4. the smallest missing artifact;
5. the smallest action the maintainer can perform;
6. whether we can do 90 %+ of the work ourselves (and the prepared patch);
7. the exact success condition;
8. the exact correction condition — what would prove our row wrong.

Requests are tiny: one integer, one confirmation, one merged file. Prefer a
patch over a proposal. No contact address appears here (routes are
de-harvested by design); the channel is the project's own issue tracker or
the authors' stated route, and the owner sends — nothing in this directory
has been sent. Status of every ask below: **PREPARED**.

| row | class | smallest ask | prepared patch |
|---|---|---|---|
| [ibm-adversarial-prompt-2025](ibm-adversarial-prompt-2025.md) | ABSENT, one re-run away | accept `main_joint_report.py`, or run it once and paste one line | `contrib/ape_joint.py` |
| [guardbench-2024](guardbench-2024.md) | ABSENT, one re-run away | accept `joint_report.py`, or publish the results directory for one dataset | `contrib/guardbench_joint.py` |
| [bells-misuse-2025](bells-misuse-2025.md) | PRESENT via partial release | confirm the subset's selection rule, or release the remaining per-item verdicts | none needed — the reproduction exists |
| [bells-o-2026](bells-o-2026.md) | ABSENT, per-item outcomes exist by construction | release per-item verdicts for one workload, or one leave-one-out row | `contrib/guardbench_joint.py` adapts to id-keyed JSON |
| [multimodal-safeguard-bench-2026](multimodal-safeguard-bench-2026.md) | PRESENT via full release | one yes/no: was the printed LG4→text / LG4∨SG2→image route executed item-level, or reconstructed? | issue already open (#1) |
