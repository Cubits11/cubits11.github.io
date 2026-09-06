# ASTRA BRIEF — one-shot build order for the 3D foundations lane

Written 2026-09-05 for an external model with repo access. Everything expensive
has already been measured; this file is short because the findings are compressed
into `films/lib/blender/API-FACTS.md`. **Read that file first — it will stop you
losing runs to three traps that are not in Blender's documentation.**

Paste §A + one task from §B. Do not paste the whole file.

---

## §A — CONTRACT (paste verbatim)

```
REPO github.com/Cubits11/cubits11.github.io  BRANCH claude/<topic>  AUTHOR Cubits11 only, no co-author trailers
READ FIRST: films/lib/blender/API-FACTS.md · docs/foundations/PROGRAM.md §2 §11 §12 · docs/foundations/devices.yaml

BLENDER /Applications/Blender.app/Contents/MacOS/Blender  v5.1.2 ec6e62d40fa9  (not on PATH)
  ALWAYS  -b --factory-startup -noaudio -P script.py -- args
  ENGINE  assign scene.render.engine and read back; bl_rna enum lists only BLENDER_EEVEE and is WRONG
  HASH    PNG IDAT chunk, never the file; tEXt differs every render
  DETERMINISM verified: Cycles CPU seed=0 denoise=off | EEVEE taa_render_samples=48. Both IDAT-stable.
  PIN in every receipt: engine, res_x/y/%, format, color_depth, view_transform, look, frame, camera, engine sampling props

WORLD (read-only, separate repo, never modify):
  ~/Documents/GitHub/cc-framework/visual_identity/claim_observatory/claim_observatory_world_v3.blend
  EEVEE · AgX / "AgX - Medium High Contrast" · 1920x1080 · 24fps · frames 0-660 · 267 objects · 0 geonode groups
  16 collections 00_WorldRoot..15_RenderHelpers  ·  12 PERSP cameras Camera_<Room>

HARD RULES
  1 Blender owns appearance. Code owns what is reachable. Never encode device state in geometry nodes.
  2 Generated pages are never hand-edited. Source -> scripts/generate_*.py -> page, with a --check gate.
  3 Every numeral on any surface resolves to a locator (claim id or file:key) or it does not ship.
  4 No numeral may be invented, rounded silently, or carried across files without its scope.
  5 A device is FAITHFUL only if reachable(states) == feasible(estimand). Self-assessment = SELF-AUDITED.
  6 Non-claims ship in the same artifact as the claim, never in a follow-up.
  7 python3 scripts/verification_manifest.py must exit 0 before any commit.

FORBIDDEN
  physics sims · particle systems · flythrough "risk landscapes" · any visual whose arrangement space is unenumerated
  external sends (issues, emails, uploads) · touching claims.yaml / claims_history.yaml / census.yaml
  vendor performance verdicts · scores, streaks, badges, accounts, certificates
  raising a device's rung after a failed audit (forbidden rescue)

OUTPUT one commit per task, message = what changed + what is still unverified. State every non-claim.
```

---

## §B — TASKS, each with the command that must exit 0

Ordered by value per token. **T1 needs no Blender and is the one that matters
most** — it turns §2's rubric into a verifier.

| # | Build | Acceptance |
|---|---|---|
| **T1** | `scripts/audit_device.py` — for a device id, enumerate `reachable(S₀, moves)`, evaluate `feasible(θ)`, assert set equality. On failure print the witness: the reachable-but-infeasible config, or the feasible-but-unreachable world. Pure Python, no bpy. State spaces are in `devices.yaml:audit_state_space` (D-002: 11, D-006: 3, D-007: 70, D-004: 21, D-003/D-005: 2). | `python3 scripts/audit_device.py --all` exits 0 and prints a rung per device. D-009 must be reported `no_audit_possible`, not passed. |
| **T2** | `films/lib/blender/render.py` — pinned render harness. Renders twice, calls `determinism.py:compare`, refuses to emit a receipt when `unexpected` is non-empty. Writes `receipt()` JSON. | Renders `Camera_WorldHero` frame 120 from the world twice; receipt shows `identical_pixels: true`, `unexpected: []`. |
| **T3** | **The Bead Cube scene** (`films/lib/blender/bead_cube.blend` + build script). 2×2×2 lattice, 4 beads, two arrangements — even `{000,011,101,110}`, odd `{001,010,100,111}`. **Six orthographic cameras: three faces × two arrangements.** The three face images must be *rendered projections*, not drawn. | The three face IDATs are **identical across the two arrangements**; the corner-inset IDATs **differ**. That equality is the proof of CC-003 and the test is the film. |
| **T4** | Room→atom map in `devices.yaml`. Bind each of the 12 existing cameras to the atom(s) it can carry. `11_FrechetAtomGarden`→A2/A6/A7, `05_NonClaimsWall`→A10, `06_DecayClockRoom`→claim freshness, `07_ChallengeRange`→falsifiers. Leave unmapped rooms unmapped and say so. | `devices.yaml` parses; every mapped room names its atom; the count of unmapped rooms is printed, not hidden. |
| **T5** | glTF export for the web devices. `export_scene.gltf` with Draco on, cameras off, animations off. Per-device meshes only — **never the whole world.** | Each exported `.glb` under 2 MB, loads in a bare three.js page, and the page's state machine is the T1 code, not the file. |
| **T6** | `scripts/generate_foundations.py` → `/foundations/`, with `--check`. Nodes from `devices.yaml`. Implements PROGRAM.md §5: no prose above the fold, nothing plays before an answer, no "correct", no score, branch on answer, exitable to the claim, **renders fully with JS off**. | `--check` exits 0; the page passes `scripts/check_links.py` and `scripts/verify_frontend.py`; every readout names an excluded world (§10 L6). |

### Known-open, do not paper over

- `films/data/facts.json` is stale against `claims.yaml`; the gate says regenerate **and re-inspect every film**. That re-inspection is human. Do not regenerate and declare it done.
- `claims_history.yaml` entry 38 fails the append-only check in the working tree. Do not commit around it.
- MC-002 and MC-005 disagree on the BELLS licence (`none declared upstream` vs `MIT`).
- **K7 binds:** no second device may be audited until `distribution/QUEUE.md` item 5 produces one real viewer response.

### Non-claims for anything built from this brief

Determinism was measured on one host, one build, CPU and EEVEE only; GPU untested.
A machine-checked faithfulness proof is a statement about the object and never
evidence that a learner understood it. Zero devices are independently audited.
Zero learners have used any of this. The world file was authored before this
program existed and its rooms were not designed against these atoms.
