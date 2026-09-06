# Foundations build and acceptance

The source is `devices.yaml`; the Python audit defines the finite digital models.
The public nodes are generated. Do not edit their HTML or the compiled state table.
Registry rungs remain unchanged. The digital model reports remain SELF-AUDITED.

## Bead projections

```sh
python3 films/lib/blender/build_bead_cube.py
```

This builds `films/lib/blender/bead_cube.blend`, then renders each arrangement
in fresh Blender processes. The scene contains actual bead meshes, a lattice
scaffold, and the requested orthographic cameras. The script assigns the bead
positions for each camera's named arrangement before rendering. The saved scene
opens at the even arrangement; the build script is the authoritative recipe for
both arrangements. There are no geometry nodes, physics, particles, or state
rules embedded in geometry.

The renderer, not image-drawing code, produces the face silhouettes and clipped
corner insets. The scaffold is hidden for these measurement images. Unlit bead
surfaces remove illumination as an unintended depth cue. Exact axis-permutation
camera matrices keep the screen-coordinate transforms stable. The corner inset
uses the corresponding face camera with a narrowed view and far clipping plane;
its receipt records that change. It does not substitute a drawn corner symbol.

`films/lib/blender/bead-cube-renders/receipt.json:comparisons` records the face
IDAT equalities and corner IDAT inequality. Every shot also has a repeat-render
comparison and the full pinned settings. Design dimensions and sampling values
resolve to `films/lib/blender/build_bead_cube.py:PARAMETERS`; the arrangement
coordinates resolve to `devices.yaml:devices[id=D-007].action` and CC-003.
The images and non-claims are presented together on the generated bead node.

Non-claims: this is a constructed finite-world witness under the stated
projection settings, not a typical gap, a vendor performance observation, an
arbitrary-lighting equality, or a cross-host determinism guarantee. The
orthographic comparison is the evidential image; the optional perspective web
mesh is a manipulable view, not that projection test.

## Camera bindings

```sh
python3 scripts/verify_room_atom_map.py
```

`devices.yaml:room_atom_map` explicitly lists every camera named in API-FACTS.md.
The verifier prints both unmapped rooms and rooms lacking an atom binding.
Claim freshness is a named lifecycle concept, not an invented atom. Proposed
room capacity is not evidence that anyone learns from that room. No external
world geometry was changed or exported.

## Device-only web geometry

```sh
python3 films/lib/blender/export_devices.py
```

Only models enumerated by T1 receive meshes. The exporter uses fresh local scenes
and selects mesh objects only. The bead model uses the local proof scene, not the
external world. Draco is required on every primitive; cameras, animations, skins,
and state extras are absent. Sizes and source hashes are recorded in
`assets/foundations/meshes/receipt.json:exports`; the size ceiling resolves to
`films/lib/blender/export_devices.py:PARAMETERS.max_glb_bytes`.

The bare loading page is `/foundations/meshes/`. All dependencies are vendored
under `assets/foundations/vendor/three/`, with the upstream license and provenance.
There are no CDN, analytics, account, storage, or outbound-message calls.

The actual `audit_device.py:models` moves are compiled by
`audit_device.py:transition_tables` into `assets/foundations/states.json`.
`machine.js` interprets this graph and rejects edges outside it; it does not
reimplement any device's permitted moves. `viewer.js` maps the current state to
mesh poses and textual readouts. The glTF contributes no rules. All poses reachable
through the UI are covered by the browser test. Mesh dimensions are design
choices; public numeric readouts inherit the corresponding model locator.

Non-claims: the unbounded and temporal devices have text exercises only. The
coin model is an integer grid; the sorting model has a fixed strict ordering and
one ruler; the cell model uses explicitly chosen local constraints; the bead
model switches atomically between parity states. None certifies loose physical
manipulations or user learning. The hasp and exposure meshes label rule choices;
they are not simulations of lock mechanics or readers.

## Generated answer-first nodes

```sh
python3 scripts/generate_foundations.py
python3 scripts/generate_foundations.py --check
python3 scripts/verify_foundations.py
python3 scripts/check_links.py
python3 scripts/verify_frontend.py
```

The initial view contains the instruction, hinge, options, and always-visible
claim exit. With JS enabled, explanations and meshes remain hidden until an
answer. No mesh is loaded or animated automatically. Answer branches select a
specific readout; a held concept skips repair to the learner's own non-claim.
With JS disabled, all answer readouts and excluded worlds remain inline, along
with the limits and a prompt to revisit the hinge without the device.

`devices.yaml:web_nodes` owns the questions, alternatives, excluded worlds,
branch behavior and claim exits. Nodes without an existing `binds` entry use an
explicit pedagogical exit in this source block; this does not alter the claim
registry or assert new support. Numeric text inherits a file-and-key locator.

A browser acceptance run uses a local static server and Playwright:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
# In another terminal, with Playwright available (or PLAYWRIGHT_MODULE set):
node scripts/test_foundations_browser.cjs
```

The port is a local test parameter in `scripts/test_foundations_browser.cjs`.
The test loads every export, walks every reachable UI state, tests a rejected
move, checks answer gating and branching, checks mobile overflow, and checks all
nodes with JS disabled. Its source-bound result is
`assets/foundations/meshes/browser.receipt.json`; screenshots remain local under
`_private/foundations-browser/`.

Non-claims: local Chrome acceptance is not cross-browser coverage, an assistive
technology certification, accessibility-path equivalence, independent review,
or an observed learning or transfer outcome. No claim rungs are promoted.
The envelope has no configurational audit; the receipts exercise has no supplied
totals or ceiling and computes no diner count.

All deterministic gates are registered in `scripts/verification_manifest.py`.
That manifest must pass before any commit; individual green checks do not waive
an unrelated failing release gate.
