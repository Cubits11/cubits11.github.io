# E6 correction — marginal-invariance failure

Recorded 2026-09-10. **Disposition: REJECT the fixed-marginal coupling-range claim E6-001 as stated.** The original computation is retained for audit, not promoted as a valid range. The registry retains the ID with `contradicted` status; the history transition is `CORRECT`, because the ID remains addressable rather than being removed by `RETRACT`.

The construction in `run/measure.js` and `scripts/verify_e6.py` assigns masses (0.25, 0.50, 0.25) to row indices and permutes the values in the last four coordinates. Permuting unequal-mass atoms does not generally preserve their marginal distribution. For the permutation (1,0,2), the masses on values (q25,q50,q75) become (0.50,0.25,0.25). Only identity and reversal preserve the stated masses, giving 2^4 = 16 valid constructions among 6^4 = 1,296 enumerated constructions.

Therefore the endpoints 2.1169 and 18.0684 are not established as a range obtained by holding these marginals fixed. Repeating the same arithmetic in the old verifier reproduces the error. Its passing output is a historical arithmetic replay, not a scientific acceptance of this claim.

This is an unanticipated failure of a premise of the proposition. The old falsifier did not explicitly test preservation of marginal masses. Rejection is recorded on the stronger direct evidence; it is not misrepresented as an old numerical-tolerance test firing. The original falsifier and forbidden rescues remain visible, unchanged.

Other unsupported interpretations are withdrawn with the claim: that every intermediate median is attainable, that arbitrary finer discretizations can only widen the range, and that a difference between summaries of different respondent populations measures only dependence. The statement that 1.6 lies in [2.12,18.07] is also false. No replacement interval is asserted here.

The frozen inputs, extractor, model-evaluation rows, results JSON, and historical verifier are unchanged. `RESULT.md` now begins with a dated notice; the original body is preserved below it. A valid later experiment would require a new identity, explicit feasible marginal constraints, separate invariant checks, and honest treatment of the fact that these outcomes are already known.

Reproduce the audit: `python3 distribution/research-2026-09-10/audit.py`.

Evidence: [audit output](../../distribution/research-2026-09-10/audit-results.json), [preserved-byte manifest](../../corrections/records/2026-09-10-preserved-inputs.json), [original rows](results/observations.jsonl), [original result](results/e6_result.json), [public correction destination](https://cubits11.github.io/corrections/#e6-marginals).
