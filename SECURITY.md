# Evidence security and recovery

The repository must remain correctable. Protect original observations and the
record of corrections; do not protect a claim from being refuted. A hash proves
byte identity, not scientific truth. No repository can guarantee permanent
survival against every administrator, account compromise, hosting failure, or
physical loss.

## Boundaries

| Threat | Control | Limit |
|---|---|---|
| Frozen rows, preregistrations or estimators silently replaced | `security/evidence-policy.json` pins observed experiment artifacts; `evidence_guard.py` checks their bytes | Only the named artifacts are covered; new experiments need an explicit policy adoption |
| History rewritten and its hashes recomputed | Trusted-base comparison requires original sequences and genesis to remain intact | A local self-check alone is not an independent trust anchor |
| A pull request replaces both evidence and its checker | `evidence-boundary.yml` executes the base revision's checker and reads candidate Git blobs without executing them | This protection becomes enforceable only after deployment and selection as a required GitHub check |
| Force-push, branch deletion, or unchecked direct push | Prepared GitHub default-branch rules require PRs and verification, disallow force-push and deletion, with no bypass actors | Active ruleset verified through the GitHub API on 2026-09-15; administrators can still change rules |
| Lost uncommitted work or deleted local checkout | External-directory snapshot includes Git bundle, staging patch, workspace and file hashes; restore is tested in isolation | Same-device recovery does not survive loss of the device |
| Validly hashed but scientifically wrong computation | Existing correction dispositions, contract checks and substantive review | Execution conformance and inference remain separate obligations |

## Trusted-base check

```sh
python3 scripts/evidence_guard.py --local
python3 scripts/evidence_guard.py --base FULL_BASE_COMMIT --candidate FULL_CANDIDATE_COMMIT
python3 tests/test_epistemic_security.py
```

The local check verifies frozen pins only. The commit comparison reads its policy
from the base, compares append-only records against that base, and refuses changes
to the trust-root files or the workflow inventory. The Actions workflow checks out **only the base**. It
fetches the candidate as Git objects and never installs candidate dependencies,
imports candidate Python, or checks out candidate code. Its token is read-only
and checkout credentials are not persisted. This follows GitHub's guidance on
[untrusted code and privileged workflow triggers](https://docs.github.com/en/actions/reference/security/secure-use).

A trust-root upgrade cannot authorize itself. Change the checker, workflow or
policy through a separately reviewed administrator migration, retaining the old
policy and recovery snapshot first. Do not silently relax the old gate to get a
candidate through. CODEOWNERS routes review; it does not enforce approval by
itself. No independent second reviewer has been configured. A sole owner cannot
independently review their own pull request.

## Recovery

```sh
python3 scripts/recovery_snapshot.py create /ABSOLUTE/PATH/OUTSIDE/REPO/new-snapshot
python3 scripts/recovery_snapshot.py verify /ABSOLUTE/PATH/OUTSIDE/REPO/new-snapshot --manifest-sha256 DIGEST_FROM_CREATION
```

Creation refuses to overwrite an existing snapshot or place it inside the repo.
It captures tracked and non-ignored untracked files, all referenced Git history,
the staged patch, and workspace deletions. Symlinks are refused rather than
followed. A successful creation includes an actual isolated restore test, not
just an archive-listing check. Verification rejects an unexpected manifest hash,
corrupt artifacts, unsafe archive paths and mismatching recovered bytes. It
never overwrites the current checkout.

For manual recovery, clone `history.bundle` into a **new** directory, check out
the manifest's `head`, apply `staged.patch` with `git apply --cached`, then restore
workspace members and listed deletions according to `manifest.json`. Run the
provided verifier first and retain the original damaged checkout for diagnosis.

Keep the manifest digest separately. Copy the verified snapshot to independent
offline or separately administered storage before claiming disaster recovery.
No off-device copy or cloud retention policy has been configured by this work.
Ignored files, credentials, GitHub settings/issues and external model caches are
excluded; retain those through their own appropriate recovery mechanisms.

## Remote activation

The prepared ruleset targets the default branch with no bypass actors:
deletion and force-push blocked; PRs and resolved conversations required; the
`Claim registry` and `Reproduce bound artifacts` GitHub Actions checks must pass
against the current base. Required independent approvals are zero because no
second reviewer is established. These are [GitHub enforcement settings](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets), not claims made by a checked-in file.

After the security workflow has landed on the default branch and produced a
successful check, also require `Trusted evidence boundary` from GitHub Actions.
Do not require a check that cannot run yet and then add a bypass to escape the
resulting lockout. The initial ruleset was read back as active on 2026-09-15; the trusted-boundary check still needs its first default-branch run before being required.

Do not treat these controls as immunity to owner-account compromise. Account
recovery, strong authentication, an independent trusted reviewer, and an
off-device copy remain separate work.
