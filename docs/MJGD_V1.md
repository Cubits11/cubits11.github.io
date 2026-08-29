# Minimum Joint Guardrail Disclosure (MJGD) v1

MJGD v1 is a small machine-readable disclosure schema for one declared guardrail
evaluation. It is not a safety standard, a certification, a benchmark ranking,
or evidence that any organization has adopted it.

The point is narrow: make it impossible to present per-system marginals as
though they identified a static full-stack result. A conformant packet names
the population, event, systems and operating points, topology, missingness
policy, evidence kind, and the results that the declared evidence can support.

The JSON Schema is at
[schemas/mjgd-v1.schema.json](/schemas/mjgd-v1.schema.json). The executable
reference is [scripts/validate_mjgd.py](../scripts/validate_mjgd.py).

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
| Sufficient aggregates plus a manifest | ATTESTED_AGGREGATES_NOT_RECOMPUTED | The aggregates are feasibility-checked and labelled attested, not independently recomputed. |
| Per-system marginals only | NOT_IDENTIFIED_FROM_MARGINALS | The exact finite all-miss identified set is returned. No observed union, all-miss, residual, or leave-one-out result is permitted. |
| Sequential or gated route trace | HOLD_ROUTE_TRACE_REQUIRED | A route is recorded but is not reduced to static full-exposure arithmetic. |
| Explicit timeout, error, or not-exposed raw cell under the hold policy | HOLD_MISSING_DATA | The missing cells are shown and numerical static output is withheld. |

The five committed fixtures demonstrate those states:

- fixtures/mjgd-v1/parallel-full-exposure.json
- fixtures/mjgd-v1/sequential-route.json
- fixtures/mjgd-v1/partial-release.json
- fixtures/mjgd-v1/aggregate-only.json
- fixtures/mjgd-v1/missing-data.json

They are illustrative fixtures, not measurements of a vendor, model, or
deployed system.

## Static aggregate rules

For a positive denominator n, per-system catch counts c_i, and a reported
union U, the validator requires:

~~~
max(c_i) <= U <= min(n, sum(c_i))
all_miss = n - U
~~~

It also checks that ordered prefix unions are feasible and terminate at U,
and that every leave-one-out union is feasible against the other systems'
counts. These checks do not reconstruct a controlled per-item tensor and
therefore do not upgrade an aggregate release to a recomputed result.

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
- infer adaptive-attack robustness;
- authorize prompt/data redistribution;
- establish adoption, interoperability, or safety.

Schema validation is only a check of a declared packet's shape and stated
evidence boundary. The packet's source data, manifest integrity, and every
substantive empirical claim still need independent review.
