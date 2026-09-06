# Executable device model scopes

`scripts/audit_device.py` checks N2 for explicit digital models. Registry source:
`docs/foundations/devices.yaml:audit_state_space`. It does not amend registry rungs.
The user's explicit request to audit all models overrides PROGRAM.md's ordering
constraint for this implementation; no viewer response is inferred.

## D-002

Registry locators: `devices[id=D-002].parameters`, `.materials`, `.feasible_set`.
Integer overlaps run from zero through ten. The two miss counts are ten each;
the stated marginal of one tenth implies a population of one hundred. The
readout is overlap divided by that population, without rounding. The finite
coin grid is audited, not every real-valued probability in a continuous interval.
Moves increment or decrement overlap within the coin budget. Feasibility is
computed independently from the integer Fréchet inequalities.

## D-003

Registry locator: `devices[id=D-003].state_space`. Toggle between the named
both-must-open and either-opens rules. These encode conjunction and disjunction;
no rate, routing order, or assertion of which rule is safer is modeled.

## D-004

Registry locator: `audit_state_space.D-004`. One ruler on the fixed strict ordering
has twenty-one cuts on twenty objects. A cut encodes a binary suffix; moves shift
the cut one place. The predicate independently checks monotonicity. Object sizes,
ties, coupled rulers, and detector performance are not audited.

## D-005

Registry locators: `devices[id=D-005].state_space`, `.feasible_set`. Toggle the
handed artifact. Whole page encodes full exposure; slip encodes routed exposure.
No response accuracy, adaptive page changes, or routing arithmetic is claimed.

## D-006

Registry locators: `devices[id=D-006].materials`, `audit_state_space.D-006`.
The registry does not give a concrete Latin fragment. This model explicitly
chooses symbols one through four, a target row excluding one and no additional
column exclusion. Thus the candidate universe has four symbols and the legal
cell has three values. Moves step between legal symbols. This representative
local constraint model does not certify an unspecified puzzle, global Sudoku
uniqueness, or transfer to MC-003.

## D-007

Registry locators: `devices[id=D-007].action`, `audit_state_space.D-007`.
Enumerate all seventy choices of four occupied distinct binary corners. Feasible
worlds have one bead in each bin of every pair projection. The permitted digital
move atomically switches between the two complete parity arrangements. The
predicate enumerates pair shadows without consulting that move.

Non-claim: the physical loose-bead cube permits other arrangements and emptying
intermediates. This constrained digital model does not certify that physical
cube or a future UI. Allowing arbitrary bead moves would fail this audit; that
failure must not be rescued by promoting its rung. It is a constructed possibility
proof, not a practical gap estimate. The registry's accessibility exclusion remains.

## D-001 / D-008 / D-009 / D-010

Registry locators: the corresponding `audit_state_space` entries. No marble
budget, mark count, or denominator ceiling is supplied for the configurable
unaudited models. They report `parameters_required`. The temporal envelope
reports `no_audit_possible`, with its ILLUSTRATIVE rung. Neither status is a pass.
An all-device run exits successfully if no evaluated model fails; a single-device
request that cannot be evaluated exits with the conventional CLI unevaluated code.

## Non-claims

Every successful model is SELF-AUDITED. This checks set equality for the stated
parameters, not all device criteria, physical construction, deployed behavior,
independent review, teaching efficacy, or audit freshness after a bound claim
changes. Numerals in audit results resolve to the device locator and this model
scope; counts are computed by exhaustive search rather than copied from prose.
