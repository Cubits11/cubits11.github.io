# Evidence distribution

`python3 scripts/distribute.py run` computes orient → extract → draft → verify → held queue → ingest existing receipts → learn. Each stage name also refreshes the derived bundle; `verify` checks saved drafts, `orient` prints the current model. `--check` detects drift without writes. Open `dashboard.html` locally.

Inputs remain claims, campaign routes, reproduction experiments, film manifests and outcome records. `events.json` inventories content-addressed candidate events; inventory is not a claim audit. The first three threads use the existing verified reproduction routes. Other events remain held for source-specific semantic review. Draft wording comes from source fields, with confidence, scope and limits preserved. Exact-text educational posts are sourced from `distribution/educational-posts.json`. The existing publisher uses owner-approved revisions and environment credentials; browser observations can be imported as sourced metrics. Queue times are null proposals. Agent role contracts are in `experiments.json`; they grant no external-action capability.

Before owner dispatch, run `python3 scripts/verification_manifest.py` successfully at the exact revision and review the complete thread. A local pin check is not a remote source verification or proof of truth. Film candidates remain held by `distribution/launch-units.yaml`'s cold-viewer gate. Existing campaign holds stay in effect.

After actual publication, import a JSON array via `python3 scripts/distribute.py ingest --kind publications --input PATH`. Each entry needs `post_id` (digits), `source_url` (matching https://x.com/ACCOUNT/status/ID), `draft_id`, `draft_revision`, timezone-qualified `published_at`, and string dimensions `post_type`, `audience`, `topic`, `hook`, `visual`, `cta`, `thread_structure`, `time_slot`. Use the root post as the measurement unit; do not sum thread impressions as unique people. Historical drafts persist by revision in `draft-history.json`.

Import metric arrays via `python3 scripts/distribute.py ingest --kind metrics --input PATH`: `post_id`, timezone-qualified `observed_at`, `provider`, `scope` (`organic`, `total`, `promoted`), `source` (HTTPS receipt/analytics URL), `attribution` (`direct_post` only when evidenced), and `metrics` mapping any of impressions, profile_visits, link_clicks, bookmarks, replies, follows, likes, reposts, engagements, repo_views, site_visits, research_actions to nonnegative integers or null. These are cumulative snapshots, not increments. Never paste credentials or personal reply text into tracked receipts. An import validates structure, not the authenticity of an owner's receipt. Export unobservable fields as null.

CTR = link clicks/impressions; engagement rate = provider-reported engagements/impressions; follower conversion = post-attributed follows/profile visits. We do not sum overlapping engagement counters. Capture snapshots at 24, 72 and 168 hours (six-hour tolerance); only the earliest snapshot per post/provider/scope/window is used. Compare like post type, audience hypothesis, topic and UTC slot within the preceding 30 days, capped at 20 prior posts. Baselines are unweighted means of available per-post rates, with n and percentage-point differences. Missing denominators stay null; no p-values, significance, independence or causal claims. Hypothesized audience is not measured audience membership.

Aggregate repository traffic belongs in the existing campaign/outcome context, not a post conversion field. The site has no visitor instrumentation. UTM strings cannot supply destination counts. Verified research actions must also enter the existing qualified-outcome ledger with its required evidence; clicks and self-reported actions do not qualify automatically. Existing stop rules are displayed in the experiment ledger.

Platform references checked 2026-09-07: [X analytics](https://docs.x.com/x-api/posts/get-post-analytics), [X developer guidelines](https://docs.x.com/developer-guidelines). Availability depends on account access and metric scope. This implementation uses owner exports, not an assumed API entitlement.

Propose a slot: `python3 scripts/distribute.py queue --draft-id try-a --at 2026-09-10T16:00:00Z`. This records an owner-review proposal, never a platform schedule. No optimal time is inferred before measurements.

Import aggregate traffic with `ingest --kind traffic --input PATH`. Each row has `provider`, `surface` (repository/site), timezone-qualified `start`/`end`, HTTPS `source`, and nullable `views`/`unique_visitors`. Windows are shown as context without summing overlapping windows or attributing them to posts. `manifest.json` binds derived output values; live imported ledgers stay separate from synthetic test fixtures.

## Publishing (owner decision 2026-09-07)

Publishing is a stage of the same script, and it dispatches only what the
record already binds:

```
python3 scripts/distribute.py approve --draft-id try-a --basis "who approved, on what record"
python3 scripts/distribute.py publish --draft-id try-a --dry-run     # prints the exact requests, reads no credentials
python3 scripts/distribute.py publish --draft-id try-a               # posts the thread to X
python3 scripts/distribute.py snapshot --post-id <root post id>      # one cumulative metrics snapshot, as a sourced row
```

`approvals.json` records a draft id, its exact revision, the approval basis and
a digest of the post texts. `publish` refuses unless the tree is clean, HEAD is
on a remote (the dispatch revision must be public), `verify` passes at that
revision, an approval matches the current revision, and that revision is not
already in `publications.json`. Any source edit changes the revision and voids
the approval.

Credentials come only from the environment — `X_API_KEY`, `X_API_KEY_SECRET`,
`X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` (OAuth 1.0a user context for the
posting account) — and are never written to any tracked or untracked file. The
client is the standard library; no package is installed. A published thread is
recorded as a `publications.json` row with the root post as the unit, the
dispatch commit, every post id, and the experiment dimensions; that row is
then subject to the same validators as an imported receipt. `snapshot` reads
public, organic and non-public metrics for the root post and records them at
the current time; capture at 24, 72 and 168 hours as before. `engagements`
and `follows` stay null: the v2 endpoint does not supply them per post.

## Unattended cycle

```
python3 scripts/distribute.py due                      # which (post, window) snapshots are open now
python3 scripts/distribute.py replies --post-id <root>  # harvest the conversation as interaction rows (ids and digests only)
python3 scripts/distribute.py cycle                     # every due snapshot + every conversation, one pass
```

`cycle` is the one command a scheduler calls with the four credentials in its
environment. A crontab line that covers the 24, 72 and 168-hour windows with
their six-hour tolerance:

```
0 */4 * * *  cd /path/to/cubits11.github.io && python3 scripts/distribute.py cycle && git add distribution docs && git commit -qm "distribution: unattended cycle" && git push -q origin main
```

`interactions.json` holds reply ids, timestamps, author ids and a content
digest, never another person's text. `classification` starts null; only the
owner classifies a row as technical, and only an owner-classified technical
row may be counted toward the stop rule in `outcomes.yaml`. Nothing replies,
follows, likes, or quotes: the harvester reads.

`deviations.json` records where the owner departed from the stated design,
with the consequence for what the data can then say.

## Correction-aware launch and working-tree previews (2026-09-10)

E6-001 and E7B-001 are contradicted in the live registry. Their dated dispositions live beside the original reports and appear on `/corrections/`. The old coupling campaign is superseded for launch. `show-overlap` is the prepared replacement: a constructed example for two checks in a common process, with the correction notice before evidence links at `/overlap/`.

`draft` and `--check` can render and validate a working-tree preview whose source records explicitly say `pending_commit`, with null commit and URL fields. This supports reviewing exact content before a source commit. It grants no publication capability: `approve`, `verify`, and `publish` still require committed source bytes; publishing still requires the existing clean, pushed tree and exact-revision approval. After committing source changes, regenerate the preview because its source bindings and draft revision will change.

The dashboard now shows every sourced observation with its actual timestamp and computed age. Off-window snapshots remain visible but do not enter the 24/72/168-hour comparisons. Fresh September 10 owner-panel captures are in `distribution/analytics/2026-09-10T1601Z-owner-snapshots.json`; earlier observations lacking exact capture times remain outside the timed ledger. Unavailable metrics are null, and displayed self-replies or repeat views are not independent audience actions.
