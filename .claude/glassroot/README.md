# glassroot

Steps prepared by an agent session for the owner to run. Nothing here runs in CI,
and nothing here counts toward `scripts/cadence.py`.

| file | what it does | when it can run |
|---|---|---|
| `owner/d4_transcribe.py` | appends the two falsifier-assessment transcriptions that Drive 10 decision D4 authorized, then deletes the test exemption that waits for them | after REL-001's review has landed, from the root of a checkout of `claude/falsifier-assessment-kernel`; it refuses unless `scripts/verification_manifest.py` exits 0 (D4 condition 1) |

`d4_transcribe.py` was dry-run on 2026-09-27 in a disposable clone of `c1b71f9`.
Both appends verified, the parsed history equalled HEAD plus two entries, and the
kernel and the dispositions test passed. The manifest gate refused there, because
REL-001's review is due and support URLs were unreachable through the session's
proxy.
