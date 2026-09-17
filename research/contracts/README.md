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

## The inference block — S5

```sh
python3 research/contracts/validate_contract.py research/contracts/fixtures/valid-frozen-inference.json
```

Correction C2 separates three questions a single power number conflates. The
block declares them as three required groups, and each is checked on its own
terms.

`identification` declares the width the design's structure permits and the
widest that width may be for the declared target. No sample size reduces it, so
a declared width above that maximum is rejected as an identification limit
rather than reported as a precision shortfall. An admitted width wider than the
SESOI is rejected too: a design can meet its own identification bound and still
be unable to separate the smallest effect it would act on.

`precision` declares the interval half width sampling is asked to deliver. It
must be smaller than the equivalence margin, or no observed value could
conclude equivalence. `decision` declares that margin, the smallest effect
worth acting on, and the two error costs; a margin above the SESOI would waive
a difference the contract says it would act on.

`minimum_information_condition` names the joint rule, evaluated exactly:
identification width plus twice the interval half width must not exceed the
SESOI. The three group checks do not imply it — a contract can pass all three
and still overrun, which `test_minimum_information_is_not_implied_by_the_three_group_checks`
holds. The arithmetic is decimal for the reason the marginal-mass check is
exact: 0.1 + 2 × 0.1 exceeds 0.3 in binary, and a rounding artifact must not
decide whether a design can answer its own question. The boundary is admitted;
only a strict overrun is rejected. One condition name is implemented, and an
unimplemented name fails closed instead of passing silently.

The block is required at `status: frozen` only, so it exists before an
expensive run rather than after its outcomes. The five retrospective fixtures
stay `constructed_fixture` and are not retrofitted; a test asserts that none of
them is rejected for a missing inference block.

C2's eight declared names appear as `inferential_target`, `estimand` (already
top-level), `identification.width_max`, `decision.SESOI`,
`precision.desired_ci_half_width`, `decision.equivalence_margin`,
`decision.loss` and `minimum_information_condition`. `identification.width` and
`identification.source` are added, because a declared maximum with no declared
actual width cannot be compared with anything.

Passing establishes internal consistency of the declaration only. It does not
prove the runner consumes the contract, that actual item IDs match the planned
pools, that a freeze preceded observation, or that the design supports an
inference. S3–S8 remain responsible for those obligations. The inference block does not
soften that sentence: it compares declared numbers with each other. Nothing
here establishes that the declared identification width is the width the design
actually has, and no number in the block is evidence about any real pool. A future runner must
load validated contract values directly; its preregistration should render those
values instead of independently restating scientific choices.
