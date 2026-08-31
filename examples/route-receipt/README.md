# Route receipt stub

This directory is a portable, standard-library-only packet for an item-level
declared evaluation or production route trace. It is deliberately not an
extension of MJGD v1: MJGD holds route evidence rather than turning it into
static full-exposure arithmetic, and this stub reports only declared route
actions.

The packet has exactly two files:

1. route-receipt.json — route, policy, versions, operating points, population,
   terminal-event contract, and the SHA-256 of the row file.
2. route-outcomes.jsonl — one opaque-ID row per declared item.

Copy fixture-receipt.json and fixture-outcomes.jsonl, replace only their
illustrative values, hash the exact JSONL bytes, and run:

~~~sh
python3 route_receipt.py route-receipt.json
~~~

The validator recomputes the route's blocked / allowed / held action from the
declared stages. It prints a positive-stratum terminal-event outcome only when
the manifest gives a source-defined event. For benign strata it prints only
benign route blocks; it does not manufacture a safety event or FPR.

## Directness is a hard boundary

Set execution.evidence_origin to exactly one of:

- direct_route_trace — the publisher declares that the rows came from
  execution of the declared route. A structural pass prints action counts
  headed "declared direct trace," not proof of that assertion.
- derived_static_reconstruction — the rows were recombined after the fact
  from component logs or an unguarded baseline. The script validates the
  provenance envelope, then returns HOLD with no route metric. It cannot be
  marketed as a direct-route result.

That distinction is the point. A post-hoc calculation can be valuable and
reproducible, but it is not evidence that a combined route executed. A
publisher's directness assertion still needs an immutable source artifact and
independent scrutiny; this validator does not supply either.

## Required per-row fields

~~~text
item_id           opaque, stable identifier
stratum_id        one manifest stratum containing that ID
route_id          the route selected for that stratum
stage_decisions   every declared stage: flag|clear|timeout|error|not_exposed
terminal_action   block|allow|hold, consistent with the declared policy
terminal_event    occurred|not_occurred|not_observed
~~~

For a parallel block-on-any route, every stage must be exposed and a mixed
timeout/error plus flag/clear is refused as ambiguous. For a sequential route,
the rows must show a clear prefix, then a flag/nondecision (if any), followed
only by not_exposed. Timeouts and errors obey the manifest's explicit
nondecision policy; they are never silently dropped.

No raw prompt, image, or completion is required. A blocked or held row must
say terminal_event=not_observed: it has not observed the downstream target
event. The receipt still does not authenticate a cited source, prove the
declared trace was direct, establish deployment, establish policy alignment
between guards, or establish safety.

## Exercise it

~~~sh
python3 route_receipt.py fixture-receipt.json
python3 test_route_receipt.py
~~~

The fixture is illustrative. It is not a measurement of any vendor, model, or
deployed system.
