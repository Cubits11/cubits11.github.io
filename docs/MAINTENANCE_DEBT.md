# Maintenance debt

Known, dated, and deliberately not fixed yet — with the evidence needed to fix
it mechanically. An item lives here when the *problem* is verified but the
*fix* is not yet verified, because shipping an unverified fix to remove a
warning trades reproducibility for tidiness.

---

## MD-001 · Pinned actions declare the deprecated Node 20 runtime

**Opened** 2026-08-31 · **Severity** low (warning, not failure) · **Status** open

**Observed.** Every CI run emits:

> Node.js 20 is deprecated. The following actions target Node.js 20 but are
> being forced to run on Node.js 24: `actions/checkout@11d5960a…`,
> `actions/setup-python@a26af69b…`

**Verified upstream** (read from each repository's `action.yml` at the tag, via
`git`, not inferred):

| action | tag | commit | `runs.using` |
|---|---|---|---|
| actions/checkout | v4 | `11d5960a326750d5838078e36cf38b85af677262` | `node20` ← in use |
| actions/checkout | v5 | `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` | `node24` |
| actions/setup-python | v5 | `a26af69be951a213d495a4c3e4e4022e16d87065` | `node20` ← in use |
| actions/setup-python | v6 | `ece7cb06caefa5fff74198d8649806c4678c61a1` | `node24` |

**Why it is not fixed in this change.** Two reasons, and neither is that the
work is hard.

1. The runtime declaration is verified; **behavioural equivalence across a major
   version bump is not**. `checkout@v5` and `setup-python@v6` are major
   releases, and this repository's deploy path depends on `fetch-depth: 0`
   ancestry for the clean-clone replay. A bump belongs in a change whose only
   job is that bump.
2. Landing it beside unrelated work would give any CI failure two candidate
   causes. The census change and the toolchain change must be able to fail
   independently.

GitHub already forces these actions onto Node 24 at runtime, so the current
pins are functionally fine today. This is a deadline, not a defect.

**How to close it.** Replace the two SHAs above with their `node24` counterparts
— keeping full-SHA pinning and the trailing `# v5` / `# v6` comment — in
`.github/workflows/verify.yml` (4 uses of checkout, 3 of setup-python), push as
a standalone change, and require: claim registry green, clean-clone replay
green, Pages deploy green, and deployed smoke green. If any fails, revert to the
pins in this table, which are known green as of merge `a6bf3a2`.

## Observed 2026-09-01 (film laboratory branch) — `reproduce_cc001.py` cannot run on a PEP 668 host

`scripts/reproduce_cc001.py` installs the cloned cc-framework with
`python3 -m pip install -e` into whatever interpreter runs it. On a Homebrew
Python 3.14 host that is an "externally managed environment", pip refuses,
and the script exits with a `CalledProcessError` before the kernel assertion
runs. CI's runner is not externally managed, so the gate is green there; the
local replay documented in README is not. Recorded, not fixed: the fix (a
throwaway venv inside the script's temp directory, then run the assertion
with that venv's interpreter) belongs in a change whose only job is that
change, so a red clean-clone replay keeps one candidate cause. Not a defect
in any claim; CC-001/CC-004 values used by `films/` are read from claims.yaml's
expected block, not recomputed on this host.
