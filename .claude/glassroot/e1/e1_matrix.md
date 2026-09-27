# E1 matrix

Predeclaration sha256 `6e7d28229e18d2aadc524b32755679ccbf901c53b7f7acf29729884accf5b361`. A cell is `W0/W1` decisions; ✓ = correct and, for a primary pair, different.

| pair | kind | query | expected | A/RECORDED | A/CAPACITY | B/RECORDED | B/CAPACITY | B+13.05/CAPACITY | C | K |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | primary | is T6's acceptance requirement met at the run commit? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES |
| P1b | primary | is the PR's own requirement met while an unrelated required check is red? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✗ NO/NO | ✓ NO/YES |
| P2 | primary | may session S execute the task? | YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO |
| P2c | control | may session S execute the task? | NO/NO | ✓ NO/NO | ✓ NO/NO | ✓ NO/NO | ✓ NO/NO | ✓ NO/NO | ✓ NO/NO | ✓ NO/NO |
| P3a | primary | is the flagship source map current? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES |
| P3b | primary | is REL-001's review current? | YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO |
| P3c | primary | is AF-001's support verified? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✗ YES/YES | ✓ NO/YES |
| P4 | primary | may agent S execute the blueprint's local-merge block? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES |
| P5a | primary | may a cold-entered session S append D4's two assessments? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES |
| P5b | primary | may publish execute for try-a? | YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✗ NO/NO | ✓ YES/NO |
| P5c | primary | may publish execute for try-a at 8318df5a? | YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✗ NO/NO | ✓ YES/NO |
| P6 | primary | may 13.12 scoring by a web-capable scorer be recorded as blind? | NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES |
| P7a | primary | must the correction's disposition equal the predecessor falsifier's consequence? | NO/YES | ✗ UNDECIDED/UNDECIDED | ✗ UNDECIDED/UNDECIDED | ✗ UNDECIDED/UNDECIDED | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES | ✓ NO/YES |
| P7b | primary | may E7B's CORRECT be recorded? | YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✗ NO/YES | ✓ YES/NO |
| R8 | primary | does the T1-T6 outcome count toward the ASTRA calibration row? | YES/NO | ✗ UNDECIDED/UNDECIDED | ✓ YES/NO | ✗ UNDECIDED/UNDECIDED | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO | ✓ YES/NO |
| R9a | primary | does 13.10's per-task score apply to the run? | YES/NO | ✗ UNDECIDED/UNDECIDED | ✗ UNDECIDED/UNDECIDED | ✗ UNDECIDED/UNDECIDED | ✗ UNDECIDED/UNDECIDED | ✓ YES/NO | ✗ UNDECIDED/UNDECIDED | ✓ YES/NO |
| R9b | control | does 13.10's per-task score apply to the run? | YES/YES | ✗ NO/YES | ✓ YES/YES | ✗ NO/YES | ✓ YES/YES | ✓ YES/YES | ✗ UNDECIDED/UNDECIDED | ✓ YES/YES |

## K single-component removal

| component | pairs that collapse |
|---|---|
| `G` | P2, P2c, P5a, P5b, P5c |
| `V` | P1, P1b, P3a, P3b, P3c, P6, P7b, R9a, R9b |
| `Rc` | P5c, R8, R9a, R9b |
| `T` | P7a, P7b |
| `FA` | P7a |
| `g.id` | — (unearned) |
| `g.issuer` | — (unearned) |
| `g.grantee` | P5a |
| `g.actions` | P5a |
| `g.subject_selector` | P5b |
| `g.conditions` | P5c |
| `g.policy_digest` | — (unearned) |
| `g.not_before` | — (unearned) |
| `g.expires` | — (unearned) |
| `v.verifier` | — (unearned) |
| `v.check` | P1b |
| `v.subject_digest` | R9a, R9b |
| `v.policy_digest` | — (unearned) |
| `v.environment` | — (unearned) |
| `v.result` | P1, P1b, P3a, P3b, P3c, P6, P7b |
| `v.evidence_refs` | — (unearned) |
| `r.action` | — (unearned) |
| `r.executor` | R8 |
| `r.subject_digest` | R9a, R9b |
| `fail_closed` | P3c |
| `derive_now` | P3b, P3c, P6 |
| `req_per_check` | P1b |
| `recheck_at_execution` | P5b |
| `default_deny` | P2, P2c, P5a, P5b, P5c |
| `veto` | — (unearned) |
| `epi_evidence` | P7b |

Backward elimination, listed order, irreducible set: `G`, `V`, `Rc`, `T`, `FA`, `g.grantee`, `g.actions`, `g.subject_selector`, `g.conditions`, `v.check`, `v.subject_digest`, `v.result`, `r.executor`, `r.subject_digest`, `fail_closed`, `derive_now`, `req_per_check`, `recheck_at_execution`, `default_deny`, `epi_evidence`

## C single-field removal (pairs C already passes that it loses)

| field | pairs lost |
|---|---|
| `Ia` | P1, P3a |
| `Ie` | R8 |
| `Ac` | P2, P2c, P4, P5a |
| `So` | — (unearned) |
| `Vc` | P1 |
| `Es` | — (unearned) |
| `Fa` | P7a |
| `Fe` | P3a, P3b |

## Expected versus actual

- A/CAPACITY: match — expected ['P7a', 'R9a'], actual ['P7a', 'R9a']
- A/RECORDED: match — expected ['P7a', 'R8', 'R9a', 'R9b'], actual ['P7a', 'R8', 'R9a', 'R9b']
- B/CAPACITY: match — expected ['R9a'], actual ['R9a']
- B/RECORDED: match — expected ['P7a', 'R8', 'R9a', 'R9b'], actual ['P7a', 'R8', 'R9a', 'R9b']
- C: match — expected ['P1b', 'P3c', 'P5b', 'P5c', 'P7b', 'R9a', 'R9b'], actual ['P1b', 'P3c', 'P5b', 'P5c', 'P7b', 'R9a', 'R9b']
- K_single_removal_earned: match — expected ['FA', 'G', 'Rc', 'T', 'V', 'default_deny', 'derive_now', 'epi_evidence', 'fail_closed', 'g.actions', 'g.conditions', 'g.grantee', 'g.subject_selector', 'r.executor', 'r.subject_digest', 'recheck_at_execution', 'req_per_check', 'v.check', 'v.result', 'v.subject_digest'], actual ['FA', 'G', 'Rc', 'T', 'V', 'default_deny', 'derive_now', 'epi_evidence', 'fail_closed', 'g.actions', 'g.conditions', 'g.grantee', 'g.subject_selector', 'r.executor', 'r.subject_digest', 'recheck_at_execution', 'req_per_check', 'v.check', 'v.result', 'v.subject_digest']
- K_single_removal_unearned: match — expected ['g.expires', 'g.id', 'g.issuer', 'g.not_before', 'g.policy_digest', 'r.action', 'v.environment', 'v.evidence_refs', 'v.policy_digest', 'v.verifier', 'veto'], actual ['g.expires', 'g.id', 'g.issuer', 'g.not_before', 'g.policy_digest', 'r.action', 'v.environment', 'v.evidence_refs', 'v.policy_digest', 'v.verifier', 'veto']
- C_single_removal_unearned: match — expected ['Es', 'So'], actual ['Es', 'So']

STOP rule: B/CAPACITY primary failures ['R9a']; controls none; with the owner-side 13.05 record type: none.
