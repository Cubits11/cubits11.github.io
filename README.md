# Cubits11

Evidence-bound evaluation of composed AI guardrails. Pranav Bhave ·
[cubits11.github.io](https://cubits11.github.io/)

**Research question.** What can a stack-level assurance claim establish when
each guard's performance is known and their joint behavior is not?

Per-guard miss rates do not determine how often every guard misses the same
input. I study that gap as four connected problems, each with its own artifact:

1. **Identification.** The miss rates fix a set of possible joint miss rates,
   not one. Bounds and attained endpoint witnesses: CC-001 and CC-004 in the
   [ledger](https://cubits11.github.io/ledger/), argued in full in
   [When marginals are not enough](https://cubits11.github.io/essays/when-marginals-are-not-enough/).
2. **Reporting.** Do public guardrail evaluations preserve the joint evidence?
   The [Missing Column census](https://cubits11.github.io/missing-column/)
   (MC-001) answers for a bounded, source-bound set of them.
3. **Measurement.** Preregistered runs that measure the joint quantity directly,
   failures kept: `experiments/`. The latest is
   [E9](experiments/e9/RESULT.md).
4. **Claim governance.** Every public claim is a registry entry with its
   support, falsifier, forbidden rescues, non-claims and review window
   (`claims.yaml`), checked on every push.

**The argument, with its numbers and its limits:** [`RESEARCH.md`](RESEARCH.md).

**What this does not establish:** that guards in general depart from
independence; anything about a deployed stack or a vendor's product; that any
guard or stack is safe or unsafe; independent reproduction. Every run so far is
mine.

## Correct it

A different result is the most useful thing you can send:
[file it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=reproduction.yml).
A counterexample, a benchmark the census missed, or joint outcomes you can
provide: [bring it](https://github.com/Cubits11/cubits11.github.io/issues/new?template=counterexample.yml).
Qualified outcomes — reproductions, corrections, releases, merged patches,
cold runs by people who are not the author — are recorded in
`distribution/outcomes.yaml` and rendered on `/try/`; zero is shown as zero.

## Reproduce the claims

### First: MC-001 — the Missing Column census

The homepage begins with this bounded reporting claim: among 20 public
guardrail evaluations meeting the frozen criteria, 14 establish a shared item
set and common event definition, and 5 preserve a declared joint-evidence
artifact. The 14 is a shared-basis rung, not proof of matched operating
thresholds or full exposure; the stricter ladder is 14/12/0.

```bash
python3 -m pip install -r requirements.txt && python3 scripts/verify_census.py --counts
```

You should see `MC-001 expected counts match the census (N/M/K 20/14/5)` and
`MC-001 M ladder matches the census (14/12/0)`, followed by `Census verified`.
This is a source-bound census of reporting, not a vendor ranking, a population
safety estimate, or a claim that any stack is safe or unsafe. Change a row,
registered count, or frozen-criteria history and the verifier fails.

### Second: MC-004 — released verdicts, recomputed

The least favorable number comes first. On the release's pinned `full_run`
image items, the static OR of the harness-normalized native `unsafe` bits is
1 for `250/250` benign-labelled images and `200/200` harmful-labelled images.
Llama Guard 3 Vision has a 1-bit on every released image item in that
directory, so the OR inherits that column. The harness's fixed block action
makes this a valid counterfactual harness-block calculation on those pinned
rows — not a deployed route, a shared-event catch claim, a model law, or an
independent replication of the models.

```bash
python3 -m pip install -r requirements.txt && python3 scripts/reanalyze_msbench.py
```

The script verifies eight source hashes before it counts. Its scope, expected
stdout, pinned source, and correction route are on
[/missing-column/reproduce/](https://cubits11.github.io/missing-column/reproduce/).

### Third: MC-002 — a five-guard receipt

This command recomputes a joint miss from five vendors' released binary
verdicts, and asserts it against the registered value so a mismatch fails
loudly instead of quietly re-deriving a new answer.

```bash
python3 -m pip install -r requirements.txt && python3 scripts/reanalyze_bells_subset.py
```

You should see `MC-002 reproduced` and a joint miss of `9/82 = 11.0%` against
an independence plug-in of `3.5%` — a ratio of `3.14x`. **What that is:**
counting arithmetic on 82 author-selected prompts at five vendors' released
binary verdicts. **What it is not:** a population estimate, a claim about any
vendor's product, or evidence that stacks are unsafe.

Then price what the marginals alone leave undetermined:

```bash
python3 scripts/identification.py --bells
```

The five published miss rates pin the all-miss rate only to `[0.00%, 14.63%]`
— a width equal to the best single guard's miss rate. Independence names
`3.49%`, a point inside that set it was never entitled to. The registered
value is `10.98%`. On the benign side the same marginals pin the stack's
flag rate to `[20.00%, 50.00%]`: **a floor that is strictly positive.** It
actually lands at `38.00%`. From published marginals alone one can prove this
stack burdens legitimate users, and cannot prove it catches a single harmful
item its best member would have missed.

`scripts/reproduce_cc001.py` (CC-001 and CC-004, the bound kernel) clones
cc-framework at its bound commit and installs it into a disposable virtual
environment inside the temporary clone, so it runs on externally managed
Pythons (Homebrew, Debian, Fedora) without touching your interpreter:

```bash
python3 scripts/reproduce_cc001.py
```

To re-run every gate the way CI does, from a clean clone of a given commit:

```bash
python3 scripts/verify_clean_clone.py --commit HEAD
```

**To falsify any of this:** change a byte of the pinned upstream file and the
hash check fails; change a registered count and the reproduction fails; change
a generated page by hand and the drift check fails. Corrections are logged at
[/corrections/](https://cubits11.github.io/corrections/), same calendar day.


## Everything else

The probability workbench, the site stack, local serving, the MJGD disclosure
schema, deployment, layout and scheduled jobs:
[`docs/REPOSITORY.md`](docs/REPOSITORY.md). What the repository's own checks do
and do not protect: [`SECURITY.md`](SECURITY.md).

Content © Pranav Bhave. Code (HTML/CSS/JS) may be reused with attribution.
