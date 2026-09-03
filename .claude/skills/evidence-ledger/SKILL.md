---
name: evidence-ledger
description: Count what this repository has actually measured, and what only a human can unblock, before adding more protocol to it. Use at the start of a session to load repo state in one command instead of nine documents, and before writing any new preregistration, freeze, contract, program, decision record, or verifier. Also for "what is blocking us", "what have we actually shown", "is this worth building", "what should I do next".
---

# Evidence ledger

## What this is for

Every other verifier here asks whether a claim is well-formed. This one asks the
question none of them ask: **has anything been measured?**

```bash
python3 .claude/skills/evidence-ledger/ledger.py
```

Five counts from the committed artifacts: claims by whose artifact supports them,
per-item rows this repository produced, open blockers with their age, governing
documents per experiment against rows produced, and qualified external outcomes.
It is a mirror, not a gate — deliberately absent from `verification_manifest.py`,
because a number that can fail CI becomes a number people manage.

## The failure mode it exists to catch

This repository is unusually good at preventing false claims and has no
comparable machinery for producing true ones. Preregistration, freezes,
forbidden rescues, kill rules, claim history, forty-four CI checks — every
mechanism points at *not being wrong*. None points at *finding out*. An immune
system with no opposing force reaches equilibrium by producing more immune
system, and the ledger is the only place that shows up as a number.

The specific shape it takes here: the next measurement is blocked on a human
action; Claude fills the wait with another governing document; the commit log
records progress; the observation-row count stays at zero. Every document in
that sequence is individually correct and rigorous. That is what makes it hard
to see without counting.

## Two standing rules

**Open sessions with the ledger.** It is the repo's state in one screen and
costs one command. The alternative is reading the program, the contract, the
cut, the freeze, the preflight and the last report to reconstruct the same
thing — a tax this repository charges every session and never records.

**Before writing a new governing document or verifier, run it and say the
trade out loud.** One sentence, before you write, naming the open blocker and
what it would take to clear it. Then write the document if it is still the right
call — often it is. The point is that the owner sees the trade at the moment it
is made, not in the commit log a week later. Do not silently add the ninth
document governing a measurement with zero rows.

## Reading the numbers

`own-measurement` is the one that matters: claims resting on a per-item result
this repository produced by running an instrument against a system it chose.
Re-analysis of someone else's released file is real work and real evidence, but
it is `third-party-artifact` — it does not establish that this repository can
measure anything.

`open` blockers are the honest bottleneck. Several markers usually trace to one
human action; read them as actions, not as lines.

`docs/row ∞` means an experiment has governing documents and no rows. That is
not automatically wrong — a design phase looks exactly like this — but it should
never be discovered in month three.

## Extending it

`BLOCK_MARKERS` in `ledger.py` is a declared table of markers and their state
(`open` / `cleared` / `named`). Add a marker when the repo grows one. The
classification rule for claim origin is the owner's account name plus one path
pattern, both at the top of the file, both checkable by eye. Keep them that way:
a ledger nobody can audit is another document.
