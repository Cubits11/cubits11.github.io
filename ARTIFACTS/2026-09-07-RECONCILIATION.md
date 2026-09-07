# Reconciliation — 2026-09-07

Trade, in one line: this record fixes the branch topology and names two
defects that cannot be edited away; it registers no claim and moves no gate.

Everything below was read from git objects and the working tree on
2026-09-07. Where an agent read it for me, I re-ran the command it cited.

## 1. What "172k pending lines" was

The working branch `claude/device-audit-render-harness` sat 17 commits ahead
of `origin/main` at 172,426 insertions. 160,720 of those lines are one file
held twice: `experiments/e3/freeze/or-bench-80k.csv` and
`experiments/e3b/freeze/or-bench-80k.csv`, byte-identical
(`22e95602…`). Each freeze is self-contained by design, so the duplicate
stays and is recorded by detector D7 in `docs/graph/repo-graph.json`. The
remaining ~11.7k lines are the E3 and E3B experiments, the MC-005
retraction, and the film re-render. Nothing in the 17 commits was found
uncommittable; see §4 for what an adversarial pass did find.

## 2. Branch topology, decided

| Ref | Was | Decision | Recoverable from |
|---|---|---|---|
| `main` (local) | 18 behind origin | fast-forwarded to `2174358` | — |
| `claude/spine` | 1 commit, content byte-identical on main | deleted | tag `archive/claude-spine-b454285` |
| `claude/e3-pilot-prereg`, `claude/foundations-push-cleanup`, `claude/mc-005-selection-regret` | merged into origin/main | local branches deleted | `origin/main`; two still exist as remote branches |
| `fix/e2-sizing-gate` | 1 commit, genuinely absent | **merged** (`--no-ff`); its 12-property instrument test passes | merge commit on the working branch |
| `docs/now-names-pc-001` | 2 commits, PC-001 absent from `/now/` | **merged** after the registry commit (sitemap conflict resolved by regeneration) | merge commit on the working branch |
| `codex/production-audit` | 1 commit, 77 behind, 20+ conflicts incl. a binary | deleted locally | tag `archive/codex-production-audit-fb754db`; re-derive intent, do not merge |
| `origin/claude/success-upgrade-i8gfz8` | 2 commits, 7 conflicts in the functions the working branch rewrote | **UNCERTAIN — left for the owner.** The withdrawn-vs-unreachable distinction in `verify_claims.py` looks genuinely new | remote branch |
| `origin/codex/external-queue-reconciliation` (PR 18) | 1 commit | **superseded — recommend close without merge.** Its IBM #7 state is already identical on the working branch; merging would revert `DISPATCH.md` §C to NOT SENT and delete the 17-line X dispatch record | remote branch |
| tag `prescrub-backup` | pre-existing | untouched | — |
| `.git/objects/*/tmp_obj_*` | 12 stale write temporaries from 2026-09-03 and 09-05 | pruned | nothing; they were incomplete objects |

Remote deletions and tag pushes are the owner's hand:

```
git push origin --delete claude/foundations-push-cleanup claude/mc-005-selection-regret
git push origin archive/claude-spine-b454285 archive/codex-production-audit-fb754db
```

## 3. What moved in the registry today

`census.yaml` gained nine `unexamined_candidates` rows (dated 2026-08-31 and
2026-09-07, including arXiv:2608.28327). None joins the frozen 20; N, M, K
are unchanged and `verify_census.py` recomputes them. MC-001's sha pin was
re-bound, `last_reviewed` and `last_owner_review` moved to 2026-09-07, and
every surface that prints the unexamined count moved from 15 to 24. The
census film shows that number on screen, so all twelve films were
re-rendered against the new facts file; receipts record it.

The E2 sample-size rule (`N_MIN = 1097`, `N_STOP = 600`, from
`PREREG_SELECTION.md` §3, frozen 2026-09-02) is now executable in
`experiments/e2/run/analyze.py`. E2 has no outcomes, so this is a gate
installed before data, not a threshold moved after it.

## 4. Two defects that stay on the record

**fde2a36's message is wrong about its own diff.** It says twelve receipts
were staled and eighteen were unchanged. The commit modifies eleven
receipts and *adds* a nineteenth (`same-scores__social-square`) with new
media. The eleven re-renders check out: only `rendered_from_head`, the
facts hash and `render_seconds` moved. A pushed commit message is not
edited; this paragraph is the correction.

**`experiments/e3b/e3b_config.json` carries E3's seed string**
(`MC-E3-PILOT-V1-FREEZE-2026-09-06`) while `e3b/run/draw.py` and
`e3b/freeze/sources.json` use `MC-E3B-…`. The draw itself is E3B's (the
calibration CSVs differ from E3's), so this is a stale label in a frozen
file. Correcting it after `RESULT.md` exists would be a post-hoc edit to a
frozen file, which the house rule treats as stop-and-ask. It is not
corrected. Detector D6 will keep printing it until the owner decides.

Also recorded, not resolved: E3's threshold rule reads "highest threshold
with FPR ≤ 5%" in `PREREG.md` and "lowest" in `e3_config.json`. The config
was committed before any harmful item was scored and the change is
disclosed at `experiments/e3/RESULT.md` line 86, so it survives the rescue rule; E3B fixed the
wording in its own prereg. The E3B commit clock (34 s between freeze and
thresholds) is implausibly short for real inference and no timing receipt
exists. Neither voids a result. Both are what a hostile reader will open
first.

## 5. Instruments added

- `scripts/repo_graph.py` — the dependency and evidence graph, derived from
  the manifest tuple, the registry's pins, static path references in
  scripts, experiment directories and git. `--orient` is the cold-entry
  briefing, `--tasks` the actions its detectors imply, `--check` the drift
  gate (now in the manifest). Eight detectors, listed in its docstring.
- `films/lib/blender/build_repo_organism.py` — the same graph grown as a
  plant in Blender 5.1.2, every placement a stated function of a graph
  field. Output `docs/graph/organism.png` with a receipt binding the
  graph's stable digest. Not in CI (no Blender there); `--orient` says
  whether it is stale.
- Two stdlib tests joined the manifest (`tests/test_public_discovery.py`,
  `experiments/e2/run/test_instrument.py`). `tests/world.test.cjs` needs
  node and stays outside it; D8 records that.
- `CLAUDE.md` no longer states a check count. It was 46; the tuple had 53
  before today. Count-speech is now detector D1.

## 6. Non-claims

This record does not claim the repository is now correct, only that its
tree is clean at the named commits and its branches are accounted for. It
does not claim the organism render is pixel-deterministic: two consecutive
grows on this host produced different PNG digests, so the receipt binds the
graph, not the picture. It does
not claim any of the D-detectors is complete; each is a named failure the
repository already forbade, made mechanical.
