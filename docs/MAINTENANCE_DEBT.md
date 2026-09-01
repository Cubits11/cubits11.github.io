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

---

## MD-002 · The liveness witness rule covers only GitHub object URLs

**Opened** 2026-09-01 · **Severity** low (one claim, correctly failing) ·
**Status** open

**Observed.** `scripts/verify_claims.py` now separates a withdrawn support URL
(404/410) from one this runner could not reach (403/407/429/5xx/transport),
and discharges the second only when the claim's own `remote_content_change`
trigger fetched that exact repository and commit from `raw.githubusercontent.com`.
On a runner whose egress policy answers 403 to `CONNECT github.com:443`, that
rule holds 11 of 12 probes and fails one:

```
hold  CC-001 CC-002 CC-003 CC-004 CC-005 CC-006 MC-002 MC-004 GA-001 GV-001 GCE-001
FAIL  AF-001: support URL liveness indeterminate from this runner
      (<urlopen error Tunnel connection failed: 403 Forbidden>) and no
      bound-ref witness covers it:
      https://academy.claude.com/tutorials/the-ai-fluency-index
```

AF-001's support is a third-party web page, not a repository object. It has no
second host that can answer for it, so the rule has nothing to consult and the
run fails — which is the designed behaviour, not a bug: an unverifiable support
link with no independent witness is a defect in the registry, and a blanket
"the network was blocked" exemption is exactly the forbidden rescue SITE-002
now names.

**Why it is not fixed in this change.** The obvious fix is wrong. Re-fetching
`academy.claude.com` from a second code path is not a second witness — same
host, same policy, same failure. A real witness for a non-repository URL has to
be an *archival* one, and this repository already owns the machinery and the
discipline for that: `scripts/verify_wayback.py` distinguishes "a snapshot
exists" from "a request did not complete," and `scripts/verify_wayback_states.py`
pins that distinction offline. Wiring it in is a design decision with its own
failure modes — the availability API is rate-limited and external, the current
tool is deliberately a preflight rather than a gate, and a stale snapshot must
not be allowed to impersonate a live page. That belongs in a change whose only
job is that decision.

**What it costs today.** Nothing on GitHub-hosted CI, where `academy.claude.com`
resolves and the probe returns 200. The failure is visible only on restricted
runners, where it is a true statement about that runner.

**How to close it.** Either (a) extend the witness rule to accept a dated
Wayback capture of the exact support URL, recorded in `claims.yaml` beside the
support entry so the capture is bound rather than looked up at run time, and
assert the new branch in `verify_claims.py --test`; or (b) decide that
non-repository support URLs are not gate-able and record *that* as the claim's
own scope, which would narrow SITE-002 rather than rescue it. Do not close it
by widening the indeterminate exemption.
