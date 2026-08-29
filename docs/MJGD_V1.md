# Minimum Joint Guardrail Disclosure (MJGD) v1

MJGD v1 is a small machine-readable disclosure schema for one declared guardrail
evaluation. It is not a safety standard, a certification, a benchmark ranking,
or evidence that any organization has adopted it.

The point is narrow: make it impossible to present per-system marginals as
though they identified a static full-stack result. A conformant packet names
the population, event, systems and operating points, topology, missingness
policy, evidence kind, and the results that the declared evidence can support.

The JSON Schema is at
[schemas/mjgd-v1.schema.json](/schemas/mjgd-v1.schema.json). It checks the
structural envelope only; run the executable
[scripts/validate_mjgd.py](../scripts/validate_mjgd.py) for semantic
conformance.

## Replay

From a checkout of this repository:

~~~
python scripts/validate_mjgd.py --test
python scripts/validate_mjgd.py --fixtures
python scripts/validate_mjgd.py --json fixtures/mjgd-v1/parallel-full-exposure.json
~~~

The validator uses only the Python standard library and reuses the existing
sources of arithmetic:

- scripts/mjgd_reference.py recomputes complete static full-exposure
  outcomes.
- scripts/identification.py calculates exact finite all-miss identified
  sets from marginal catch counts and checks raw leave-one-out unions.

## Required envelope

Every packet has:

- a fixed population and separate positive and benign denominators;
- one positive-event and one flag-event definition;
- at least two systems with a version and fixed operating point;
- topology and explicit system order;
- explicit missingness codes and hold policy;
- a version/topology/operating-point repeat trigger;
- two boundary statements: static all-miss is neither route risk nor adaptive
  robustness.

Every item-system decision cell is explicit when per-item evidence is
released. An absent JSON key never means clear.

## Evidence states

| Evidence kind | Validator state | What the packet may say |
| --- | --- | --- |
| Complete binary per-item outcomes; parallel OR; same items; full exposure | RECOMPUTABLE_STATIC | Exact per-system catches, union detection, all-miss, ordered prefix unions, leave-one-out unions, and benign union burden are recomputed. |
| Complete positive-set aggregate-pattern counts plus a manifest | RECOMPUTED_FROM_AGGREGATE_PATTERNS | The submitted positive-set pattern table is complete, so every reported positive static result is recomputed from it without item identities. No benign union is accepted from this packet. The source aggregate is still not independently authenticated. |
| Per-system marginals only | NOT_IDENTIFIED_FROM_MARGINALS | The exact finite all-miss identified set is returned. No observed union, all-miss, residual, or leave-one-out result is permitted. |
| Sequential or gated route declaration plus a manifest | HOLD_ROUTE_TRACE_REQUIRED | The declared route is held; this packet does not verify or reduce a route trace to static full-exposure arithmetic. |
| Explicit timeout, error, or not-exposed raw cell under the hold policy | HOLD_MISSING_DATA | The missing cells are shown and all numerical static output, including benign burden, is withheld. |

The five committed fixtures demonstrate those states:

- fixtures/mjgd-v1/parallel-full-exposure.json
- fixtures/mjgd-v1/sequential-route.json
- fixtures/mjgd-v1/partial-release.json
- fixtures/mjgd-v1/aggregate-only.json
- fixtures/mjgd-v1/missing-data.json

They are illustrative fixtures, not measurements of a vendor, model, or
deployed system.

## Complete aggregate-pattern rules

An aggregate packet gives one non-negative count for every binary membership
pattern in declared execution order. With two systems ordered A then B, the
four keys are:

~~~
00  neither A nor B flagged
01  only B flagged
10  only A flagged
11  both A and B flagged
~~~

The zero pattern is mandatory and the pattern counts must sum to the positive
denominator. The validator recomputes positive-set per-system catches, union,
all-miss, ordered prefix unions, and leave-one-out unions directly from that
table. A complete pattern table makes the reported aggregates jointly
realizable by construction, while keeping item identities controlled. Because
the table covers positives only, a benign union burden must be explicitly
unavailable rather than copied in without matching benign evidence.

It does not authenticate the pattern table's source, manifest, or collection
process. That remains an attestation and review problem, not an arithmetic
one.

With marginals alone, the finite all-miss count remains in:

~~~
max(0, n - sum(c_i)) ... n - max(c_i)
~~~

That range is the output instead of an independence plug-in.

## Boundaries

MJGD v1 does not:

- estimate uncertainty, calibration, causal contribution, or deployment
  utility;
- score timeouts as catches or clears;
- infer a sequential or gated route result from a parallel static table;
- accept a benign result when the declared evidence does not cover the benign
  population;
- infer adaptive-attack robustness;
- authorize prompt/data redistribution;
- establish adoption, interoperability, or safety.

JSON Schema validation checks only a packet's structural envelope. CLI
validation adds the declared cross-field and arithmetic checks. Neither checks
the packet's source data, manifest integrity, or every substantive empirical
claim; those still need independent review.
