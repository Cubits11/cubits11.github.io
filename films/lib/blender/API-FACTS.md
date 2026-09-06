# Blender API facts — probed, not remembered

Every line below was produced by running the installed Blender on 2026-09-05
and reading its output. Nothing here is recalled from documentation. Where a
fact contradicts what the API *appears* to say, that is noted, because those are
the ones that cost an agent a wasted run.

**Build under test.** `Blender 5.1.2`, build hash `ec6e62d40fa9`, build date
2026-05-19. Binary: `/Applications/Blender.app/Contents/MacOS/Blender`. No CLI
on `PATH` — invoke the absolute path.

Reproduce any row: `Blender -b --factory-startup -noaudio -P <script>`.

## The traps

| # | What you would assume | What actually happens |
|---|---|---|
| T1 | `RenderSettings.bl_rna.properties['engine'].enum_items` lists the engines. | It returns **`['BLENDER_EEVEE']` only** — before *and after* `addon_utils.enable("cycles")`. Plugin render engines register outside the static enum. **Test by assignment:** `scene.render.engine = 'CYCLES'` succeeds and reads back `'CYCLES'`. Introspecting the enum will make you wrongly conclude Cycles is unavailable. |
| T2 | Two identical renders produce identical PNG files. | They do not. The `tEXt` chunk carries render metadata and differs every run. Everything else — `IDAT IHDR cHRM gAMA sRGB pHYs oFFs eXIf` — is byte-identical. **Hash `IDAT`.** |
| T3 | EEVEE is a rasterizer, so it is non-deterministic. | **Measured false on this build.** See below. |
| T4 | `--factory-startup` is optional. | It is mandatory. Without it a user preference silently changes output and the receipt cannot say so. |

## Determinism — measured

Two runs, same scene, IDAT compared with `determinism.py`.

| Engine | Scene | Settings | Result |
|---|---|---|---|
| **Cycles** | 4 UV spheres at the even-parity corners, 1 ortho camera, 1 sun | `device='CPU'`, `samples=8`, `seed=0`, `use_denoising=False`, 120×120 | **IDAT identical.** `bcda94a7f811…`, 7634 bytes both runs |
| **EEVEE** | `claim_observatory_world_v3.blend`, 267 objects, frame 120, `Camera_WorldHero` | `taa_render_samples=48`, `use_taa_reprojection=True`, `use_raytracing=False`, `use_shadows=True`, 200×200 | **IDAT identical.** `386f4dd9868a05cb…` |

Both are pixel-deterministic and both differ only in `tEXt`. **The existing
world file is receipt-eligible as it stands** — it does not need converting to
Cycles, and converting it would change every frame's look.

**Non-claim.** One host, one build, one scene each, CPU and EEVEE only. GPU was
never tested. Nothing here holds across Blender versions or machines.

## Settings a receipt must pin

Anything below can change pixels without changing the `.blend`'s meaning, so all
of it is recorded or the receipt is not a receipt.

```
render.engine                 render.resolution_x / _y / _percentage
render.image_settings.file_format, .color_depth
view_settings.view_transform  view_settings.look
scene.frame_current           scene.camera.name
cycles.device / .samples / .seed / .use_denoising      # Cycles
eevee.taa_render_samples / .use_taa_reprojection / .use_raytracing / .use_shadows
```

Enumerated on this build: camera types `PERSP ORTHO PANO CUSTOM`; image formats
include `PNG OPEN_EXR WEBP AVIF TIFF FFMPEG`; colour depths `8 10 12 16 32`;
Cycles devices `CPU GPU`.

## The world file

`cc-framework/visual_identity/claim_observatory/claim_observatory_world_v3.blend`
— **read-only from this repository.** 267 objects, 111 meshes, EEVEE, AgX view
transform with look `AgX - Medium High Contrast`, 1920×1080, 24 fps, frames
0–660, compositor nodes on, **zero geometry-node groups** (so glTF export is
clean and no reachable-state logic hides in the file).

Sixteen collections, and they are already this repository's epistemology:

```
00_WorldRoot          01_ArrivalHall            02_ClaimCapsuleChamber
03_EvidenceVault      04_SupportGraphOrrery     05_NonClaimsWall
06_DecayClockRoom     07_ChallengeRange         08_ReplayManifestEngine
09_HumanReviewTribunal 10_LedgerTower           11_FrechetAtomGarden
12_CameraRig          13_Lighting               14_TextLabels
15_RenderHelpers
```

Twelve cameras, one per room, all `PERSP`: `Camera_Arrival`,
`Camera_ChallengeRange`, `Camera_ClaimCapsule`, `Camera_DecayClockRoom`,
`Camera_EvidenceVault`, `Camera_FrechetAtomGarden`, `Camera_HumanReviewTribunal`,
`Camera_LedgerTower`, `Camera_NonClaimsWall`, `Camera_ReplayManifestEngine`,
`Camera_SupportGraphOrrery`, `Camera_WorldHero`.

The earlier `claim_observatory.blend` is the v1: 199 objects, one animated
cinematic camera, 360 frames, and it already contains
`EvidenceArtifacts_FiniteAtomFrechetPoint_0_0_0` / `_0_0_1` — the atoms, modelled
before this program had a name for them.

**No object in either file has been modified, and none should be from here.**
`cc-framework` is a separate repository.

## Export

`bpy.ops.export_scene.gltf` is present. It exposes `export_apply`,
`export_cameras`, `export_animations`, `export_draco_mesh_compression_enable`,
`export_attributes` among ~60 parameters. Draco compression is available for
mesh payload, which matters because a 267-object scene is not a web asset as
modelled.

**Design rule that survives all of this:** Blender owns appearance, code owns
what is reachable. Export geometry; never export the state machine.
