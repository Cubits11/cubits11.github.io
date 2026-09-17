# FABLE BRIEF — the cut protocol, and the one integration left

Fable has one demonstrated genre in this repository and it is a good one:
`ARTIFACTS/2026-09-05-FABLE-5.1-OBS-CUT.md`. It opened bytes, labelled every
line OBSERVED / DERIVED / UNKNOWN, identified a hidden denominator from nine
independent numerators, checked which live sentences depended on it, and then
**decided not to spend** — leaving 990 versus 1041 unreconciled rather than
picking the one that fit.

That genre generalises. §A templates it. §B is the thing it has not been pointed
at yet.

---

## §A — CUT (paste verbatim; ~20 lines is the whole protocol)

```
CUT <topic>
DECISION this cut informs: <one sentence. If you cannot write it, do not run the cut.>

Cut 0 is free: bytes already public, commands already in this repo. No spend, no live API, no send.
Cut 1 costs something. You may only enter it if Cut 0 says so, in writing, in the DECISION section.

Per line, one label, no fourth option:
  OBSERVED  bytes opened or a command executed IN THIS RUN
  DERIVED   arithmetic on OBSERVED material, with the arithmetic shown
  UNKNOWN   ships as UNKNOWN. Never upgraded to finish a row.

Hard stops, checked BEFORE Cut 1. Any one fires -> STOP and name which:
  - the comparison object is not the same object (version, config, endpoint semantics)
  - agreement would not confirm and disagreement would not falsify
  - the answer changes no live sentence in this repository

Output, in order:
  VERDICT (<=3 sentences, the decision first)
  the table (one row per artifact, every cell labelled)
  LIVE-CLAIM CHECK (every public sentence that depends on this; does it require what you tested?)
  DECISION (PROCEED or STOP, and the stop rule that fired)
  OBSERVED / DERIVED / UNKNOWN, as three lists

Registers nothing. Edits no registry. Writes exactly one file: ARTIFACTS/<date>-<topic>-CUT.md
An empty cell ships. A forced cell is the failure this protocol exists to prevent.
```

### First cut to run — CLOSED 2026-09-06

`MC-005 removal` (the claim is now retracted). Diagnosed 2026-09-05, decided
2026-09-06, and the kernel is
green: `scripts/claims_history.py verify` passes with the prefix rule satisfied.

What was wrong: `entries[38]` — the registration of the now-retracted MC-005 —
had been replaced rather
than appended after, so the working tree's history was not a prefix of the
accepted one. What was done: entry 38 was kept, a **RETRACT** for MC-005 was
appended as entry 39 with `direction_basis: DECLARED_HUMAN_JUDGMENT`, and the
MC-002 CLARIFY followed it. The retraction reason is on the record and it is
narrow: the registered support block declared `license: MIT` for a BELLS file
whose upstream declares no licence, while MC-002 binds the same file and records
`none declared upstream`. Two records disagreeing about one file's licence is a
defect in the register, not a judgement about the result — and the reason says
so explicitly, so the W1 selection-regret computation is untouched by the
retraction.

**Where that computation now lives, and what it may be called.** The numbers are
real, executed 2026-09-02, and reproducible: `experiments/e2/results/retrospective/`
holds the run report, the three matrices, and `independent_t1.py`, which
recomputes T1 from the raw released rows outside the analyzer's path. They are
**unregistered**. No claim id carries them, no CI check re-asserts them, and no
surface in this repository may attribute them to a registered claim.
`scripts/verify_retracted.py` enforces exactly that: any line naming a retracted
id must say on the same line that it is retracted, and the gate runs in the
verification manifest.

Re-registering the same content is not available as a shortcut. The kernel
refuses a second registration for a claim that already has a protected state
(`claims_history.py:333`), and registering it under a fresh id would reverse a
recorded owner judgement without a recorded reason. If the owner wants these
numbers registered, that is a new decision with its own entry — and it needs the
licence block to match MC-002 and a CI re-assertion script before it is worth
making.

---

## §B — THE SPINE (the one-shot integration)

Everything in this repository is already the same object at different
bandwidths, and nothing checks that the renderings agree.

MC-003 exists five times over:

| bandwidth | rendering |
|---|---|
| registry | `claims.yaml:MC-003` — identified set `{0/82 … 12/82}`, 13 values |
| film | `films/thirteen-worlds/` — thirteen, animated |
| device | `D-006`, the Sudoku cell — a cell narrowed to a short list |
| room | `11_FrechetAtomGarden` — atoms you can walk around |
| page | `/observatory/`, `/missing-column/` |

Change the identified set from 13 to 14 and **four of those five keep saying
thirteen.** The film has a receipt, the device has an audit, the page has a
drift gate — and not one of them knows the others exist. `verify_facts.py` binds
numerals *within* a surface. Nothing binds *across* them.

> **The spine is: one claim, N renderings, one gate.**

### What to build

`spine.yaml` — for each claim id, the renderings that assert it, and for each
rendering the numerals it speaks and the strongest sentence it says out loud.
Then `scripts/verify_spine.py` with a `--check` gate, enforcing four rules.

**S1 · Numeral agreement.** Every numeral a rendering speaks resolves to a key
in that claim's `expected` block. An unbound numeral fails. This is
`verify_facts.py` extended past the page boundary — to film scripts, device
records, room labels, hinge options.

**S2 · No rendering outruns the claim.** The anti-inflation gate, and the reason
to build this at all. A rendering may not introduce a scope-widening token
absent from the claim's own text. If MC-002 says *"the five specialized
supervisors on the released file"* and a film says *"guardrails"*, that is a
quantifier the claim never licensed. Crude as a lexical check, real as a gate,
and it fires on exactly the failure this program says it fears: the explanation
outrunning the weakest surviving sentence.

**S3 · Non-claims travel.** Every rendering carries its claim's non-claims in
the same artifact. Not in a description, not in a follow-up, not in a pinned
comment. In the artifact.

**S4 · Coverage is reported, never optimised.** Print renderings per claim. The
honest current answer is that most claims have one and several have none, and
that number is a fact about the repository, not a target. A rising coverage
count with no new evidence is the same disease as a rising device count.

### Acceptance

```
python3 scripts/verify_spine.py --check                       # exits 0
python3 scripts/verify_spine.py --explain MC-003              # prints all five renderings and their agreement
```

Then the real test, and it must be run: **change one numeral in `claims.yaml`
MC-003 in a scratch branch and confirm the film, the device record, the room
label and the page all fail.** A gate nobody has watched fail is not a gate. If
only the page fails, S1 does not reach across the boundary yet and the spine is
not built.

### What the spine is not

Not evidence that any rendering teaches anyone anything. Not a claim that five
renderings are better than one. Not a reason to manufacture renderings for
claims that have none — S4 exists to make that visible rather than rewarding.
And a green spine means the renderings agree with each other; it says nothing
about whether the claim is true.

---

## Standing constraints

Author is Cubits11 alone; no co-author trailers, in commits or anywhere else.
`python3 scripts/verification_manifest.py` exits 0 before any commit. **Commit
with explicit paths** — a bare `git commit -m` takes whatever is staged, which
in this repository is routinely someone else's in-flight registry surgery.
Generated pages are never hand-edited. No external send. `cc-framework` and
`ghost-ark` are read-only from here. K7 still binds: no second device is audited
until `distribution/QUEUE.md` item 5 produces one real viewer response.
