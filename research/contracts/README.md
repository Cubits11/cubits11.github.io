# Executable contracts — S2

Validate a proposed contract before using it:

```sh
python3 research/contracts/validate_contract.py research/contracts/fixtures/valid-guard-selection.json
python3 tests/test_contracts.py
```

`schema.json` defines two bounded contract types. Guard selection declares the
score comparator, sensitivity objective, threshold direction, candidate set,
false-positive budget, no-feasible-candidate policy, and both pool rules.
Finite coupling declares atom weights, actual planned permutations, and the
marginal-preservation obligation. Unknown fields are rejected.

JSON Schema checks structure and the threshold-direction relation. The validator
also compares declared and planned pools and computes the mass at each permuted
atom. Those arbitrary numerical and cross-field comparisons require semantic
checks; schema validity alone is not sufficient.

The E6, E7 and E7B fixtures reconstruct the defects retrospectively. They live
here, outside frozen experiment directories. They do not replace the original
estimators, yield corrected scientific results, or measure prospective detection
performance. The valid fixtures are constructed examples, not new experiments.

For a `ge` comparator, maximum sensitivity selects the lowest feasible observed
benign score; for `le`, the highest. This encodes the stated objective, not a
universal ban on other threshold objectives. Exclusion is explicit when no
candidate satisfies the budget. Changing objectives requires a separately
declared contract type rather than overloading this one.

Passing establishes internal consistency of the declaration only. It does not
prove the runner consumes the contract, that actual item IDs match the planned
pools, that a freeze preceded observation, or that the design supports an
inference. S3–S8 remain responsible for those obligations. A future runner must
load validated contract values directly; its preregistration should render those
values instead of independently restating scientific choices.
