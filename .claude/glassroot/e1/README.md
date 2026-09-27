# E1 and E1b

Representation-ablation experiments on the claim-history and dispatch contract,
run 2026-09-27 by the session that wrote `claude/falsifier-assessment-kernel`.
Each was declared before it ran. `e1_predeclared.json` has sha256 `6e7d2822…`,
recorded 2026-09-27T00:31:49Z. `e1b_predeclared.json` has sha256 `58a7d673…`,
recorded 2026-09-27T01:52:16Z. The harness refuses to run if its predeclaration
has changed.

| file | what it is |
|---|---|
| `e1_harness.py`, `e1_results.json`, `e1_matrix.md`, `e1_run.log` | 15 world pairs and 2 controls, with the fields and rules each pair earns |
| `pending_controls.*`, `clause_controls.*`, `disable_controls.*` | the controls that each rule of the exemption and of the kernel flips |
| `e1b_results.json` | X1 (issuer earned), X2 (hermeticity earned as a rule), X3 (collapses: E1's "B + 13.05 = 15/15" withdrawn) |
| `x3_dispatch_binding.py`, `x3_result.json` | the synthetic v1/v2 dispatch against the owner-side receipt columns |
| `fixtures/` | the observations the harness reads but cannot compute: a registry excerpt, the main-branch ruleset, the public fetch of the 13.12 key |

Four inputs are not here, because they come from the owner's private workspace:
`fixtures/drive10_D4.txt`, `fixtures/p1305_receipt_columns.json`, the full body of the
proxy's 403 (`e1b_results.json` quotes its first sentence), and the 13.05 export that `x3_dispatch_binding.py` reads. Those
texts are in the owner's Drive file "13.13 — E1 and E1b package". Put the two
fixtures back in `fixtures/` to re-run the harness.

The same session wrote the predictions, the encodings and the harness.
Agreement between them shows internal consistency, not independent
confirmation.
