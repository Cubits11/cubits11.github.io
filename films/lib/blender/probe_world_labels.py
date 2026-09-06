"""Record what the world file's text labels say — read-only, receipt out.

The world (`claim_observatory_world_v3.blend`, in the sibling `cc-framework`
repository) is read-only from here. Its rooms speak through FONT objects in
the `14_TextLabels` collection, and nothing in this repository can grep a
.blend. This probe opens the file in a background Blender, reads every text
body, and writes a receipt that `spine.yaml` can bind: the file's sha256, the
build that read it, and each label's name, body and collections. Nothing is
saved back; the file is never modified.

Run, from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender -b \
        ../cc-framework/visual_identity/claim_observatory/claim_observatory_world_v3.blend \
        --factory-startup -noaudio -P films/lib/blender/probe_world_labels.py \
        -- --out films/lib/blender/world-labels.receipt.json

`--factory-startup` is mandatory (films/lib/blender/API-FACTS.md, T4). The
receipt's `blend.path` is relative to the directory that holds both
repositories, so `scripts/verify_spine.py` can re-hash the file where it is
present and say so where it is not.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import bpy  # noqa: E402 — only importable inside Blender


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(args[args.index("--out") + 1]) if "--out" in args else None
    blend = Path(bpy.data.filepath).resolve()
    labels = []
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        if obj.type != "FONT":
            continue
        labels.append({
            "name": obj.name,
            "body": obj.data.body,
            "collections": sorted(c.name for c in obj.users_collection),
        })
    # relative to the directory holding both repositories, when it does
    anchor = blend
    for parent in blend.parents:
        if parent.name == "GitHub" or (parent / "cubits11.github.io").exists():
            anchor = parent
            break
    receipt = {
        "_generated_by": "films/lib/blender/probe_world_labels.py — read-only probe; regenerate, never edit",
        "probed_at": datetime.date.today().isoformat(),
        "blender": {"version": bpy.app.version_string, "build_hash": bpy.app.build_hash.decode()
                    if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash)},
        "blend": {
            "path": str(blend.relative_to(anchor)) if anchor != blend else str(blend),
            "sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
            "objects": len(bpy.data.objects),
            "text_objects": len(labels),
        },
        "labels": labels,
    }
    text = json.dumps(receipt, indent=1, ensure_ascii=False) + "\n"
    if out:
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out} ({len(labels)} labels, sha256 {receipt['blend']['sha256'][:12]})")
    else:
        print(text)


main()
