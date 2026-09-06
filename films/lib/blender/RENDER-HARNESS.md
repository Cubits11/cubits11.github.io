# Pinned render harness

Invoke with Python; the harness starts fresh Blender processes using the binary
and startup flags from `API-FACTS.md:Build under test` and `API-FACTS.md:The traps`:

```sh
python3 films/lib/blender/render.py \
  --blend ~/Documents/GitHub/cc-framework/visual_identity/claim_observatory/claim_observatory_world_v3.blend \
  --camera Camera_WorldHero --frame 120 \
  --output-dir _private/blender/world-hero-acceptance
```

Frame and camera locator: `API-FACTS.md:Determinism — measured`. The output directory
must be new, preventing stale receipts from surviving a failed attempt. Source
resolution, color depth and appearance are preserved unless resolution overrides
are explicit. Sampling is pinned to the engine's measured profile in that same
API facts table; engine availability is checked by assignment and readback.
Cycles additionally disables animated seeds and adaptive sampling explicitly.

World timeline camera bindings can change the selected camera on frame changes.
The harness clears those bindings **in memory**, records the affected marker
names, then sets the requested frame and camera. The camera and frame are checked
again after rendering. No source file is saved; its hash must remain unchanged.

Each fresh process records settings read from Blender. The parent requires both
settings records to agree, calls `determinism.compare`, rejects every unexpected
chunk difference, and only then publishes `determinism.receipt()` as JSON.
Receipt image equality uses IDAT; the file hash is supplementary provenance.
The receipt includes source hash, build identity, settings, both render hashes,
comparison and non-claims. Worker logs and settings remain available on failure.

Verification commands:

```sh
python3 scripts/test_device_audit_render.py
python3 scripts/audit_device.py --all
python3 scripts/verification_manifest.py
```

Non-claims: equality concerns the recorded scene, host, build and settings. It
establishes no cross-machine or cross-version guarantee, GPU behavior, scene
correctness, numeral provenance in world labels, physical or deployed device
faithfulness, independent audit, or learning efficacy. The world render is local
acceptance evidence, not a public claim-bearing illustration approved to ship.
