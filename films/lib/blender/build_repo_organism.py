#!/usr/bin/env python3
"""Grow the repository as a plant, from docs/graph/repo-graph.json, in Blender.

    python3 films/lib/blender/build_repo_organism.py            # builds, renders, writes receipt
    python3 films/lib/blender/build_repo_organism.py --check    # receipt matches the current graph?

Nothing is placed by hand. Every object's position, size and colour is a function
of a field in the graph file, and the mapping is written here so it can be read
before the picture is:

  ROOTS      registries the graph pins or reads (claims.yaml, census.yaml, ...)
             spheres below ground; a claim is a rootlet hanging from its registry,
             coloured by review window: cyan fresh · amber within 14 days · red past.
  TRUNK      scripts/verification_manifest.py — one cylinder, height = checks / 10.
  BRANCHES   generators, radiating from the trunk crown; each ends in a leaf, the
             page it writes. A verifier is a thorn on the trunk (short, dark).
  FRUIT      experiments hang at branch height: radius = log10(observation rows + 1) / 3.
             Zero rows renders as a wireframe husk — the shape of a result with none in it.
  NERVES     manifest edges (cyan) and sha pins (red) as thin curves; the pin curve
             is drawn broken when the pin does not hold.
  SAPLINGS   git branches not reachable from origin/main, in a ring outside the
             canopy: height = commits ahead / 4, lean = commits behind / 40, grey when
             the last commit is older than 14 days.
  RINGS      one red torus on the ground per finding, at the object it names.
  HISTORY    the last 30 days of commits as a spiral of cubes, height = commits that day.

Colour is semantic and never the only encoding: every red object is also a torus
or a broken curve; every dead structure is also a wireframe.

Outputs (docs/graph/): organism.png · organism.receipt.json · and, gitignored,
_private/blender/organism/organism.blend. The receipt binds the graph file's
sha256, the Blender build, object counts and the render digest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GRAPH = ROOT / "docs" / "graph" / "repo-graph.json"
OUT_DIR = ROOT / "docs" / "graph"
BLEND_DIR = ROOT / "_private" / "blender" / "organism"
BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")

CYAN, AMBER, RED, GREY, BARK, LEAF, DARK = ((0.0, 0.75, 0.9), (1.0, 0.65, 0.1), (0.9, 0.2, 0.2),
                                            (0.35, 0.35, 0.38), (0.36, 0.25, 0.16), (0.2, 0.6, 0.3), (0.12, 0.12, 0.14))
REGISTRIES = ("claims.yaml", "census.yaml", "spine.yaml", "modules.yaml", "campaigns.yaml", "claims_history.yaml")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── inside Blender ────────────────────────────────────────────────────────────
def grow(graph: dict, png: Path, blend: Path) -> dict:
    import bpy
    from mathutils import Vector

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.image_settings.compression = 90
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(png)
    counts: dict[str, int] = {}
    mats: dict[tuple, object] = {}

    def mat(color):
        if color not in mats:
            m = bpy.data.materials.new(f"m{len(mats)}")
            m.diffuse_color = (*color, 1)
            mats[color] = m
        return mats[color]

    def add(kind: str, name: str, loc, scale, color, wire=False, rot=(0, 0, 0)):
        {"sphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=loc),
         "cyl": lambda: bpy.ops.mesh.primitive_cylinder_add(vertices=24, location=loc, rotation=rot),
         "cube": lambda: bpy.ops.mesh.primitive_cube_add(location=loc),
         "torus": lambda: bpy.ops.mesh.primitive_torus_add(location=loc, major_radius=1, minor_radius=0.08),
         "cone": lambda: bpy.ops.mesh.primitive_cone_add(vertices=8, location=loc, rotation=rot)}[kind]()
        o = bpy.context.active_object
        o.name = name
        o.scale = scale
        o.data.materials.append(mat(color))
        if wire:
            m = o.modifiers.new("husk", "WIREFRAME")
            m.thickness = 0.02
        o["graph_id"] = name
        counts[kind] = counts.get(kind, 0) + 1
        return o

    def curve(name, a, b, color, broken=False):
        c = bpy.data.curves.new(name, "CURVE")
        c.dimensions, c.bevel_depth = "3D", 0.012
        a, b = Vector(a), Vector(b)
        segs = [(a, a.lerp(b, 0.42)), (a.lerp(b, 0.58), b)] if broken else [(a, b)]
        for p, q in segs:
            s = c.splines.new("POLY")
            s.points.add(1)
            s.points[0].co, s.points[1].co = (*p, 1), (*q, 1)
        o = bpy.data.objects.new(name, c)
        o.data.materials.append(mat(color))
        bpy.context.collection.objects.link(o)
        counts["curve"] = counts.get("curve", 0) + 1

    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    pos: dict[str, tuple] = {}

    # ground: a wire grid, so the roots stay visible beneath it
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=24, size=26, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.data.materials.append(mat(GREY))
    ground.modifiers.new("grid", "WIREFRAME").thickness = 0.015

    # TRUNK
    trunk = nodes["scripts/verification_manifest.py"]
    th = trunk["checks"] / 10
    add("cyl", "TRUNK", (0, 0, th / 2), (0.35, 0.35, th / 2), BARK)
    pos["scripts/verification_manifest.py"] = (0, 0, th)

    # ROOTS: registries + claims
    regs = [r for r in REGISTRIES if (ROOT / r).exists()]
    for i, r in enumerate(regs):
        ang = 2 * math.pi * i / len(regs)
        p = (2.2 * math.cos(ang), 2.2 * math.sin(ang), -1.4)
        add("sphere", r, p, (0.32,) * 3, BARK)
        pos[r] = p
        curve(f"root:{r}", (0, 0, 0.05), p, BARK)
    claims = [n for n in graph["nodes"] if n["type"] == "claim"]
    for j, c in enumerate(claims):
        ang = 2 * math.pi * j / max(len(claims), 1)
        p = (4.2 * math.cos(ang), 4.2 * math.sin(ang), -2.6)
        col = RED if c["days_left"] < 0 else AMBER if c["days_left"] <= 14 else CYAN
        add("sphere", c["id"], p, (0.16,) * 3, col)
        pos[c["id"]] = p
        curve(f"rootlet:{c['id']}", pos["claims.yaml"], p, BARK)

    # BRANCHES: generators → leaves; verifiers as thorns
    gens = [n for n in graph["nodes"] if n["type"] == "script" and n["kind"] == "generator"]
    vers = [n for n in graph["nodes"] if n["type"] == "script" and n["kind"] == "verifier"]
    writes = {}
    for e in edges:
        if e["rel"] == "writes" and e["from"] in {g["id"] for g in gens}:
            writes.setdefault(e["from"], e["to"])
    for i, g in enumerate(gens):
        ang = 2 * math.pi * i / max(len(gens), 1)
        tip = (3.4 * math.cos(ang), 3.4 * math.sin(ang), th + 1.2 + 0.4 * math.sin(3 * ang))
        curve(f"branch:{g['id']}", (0, 0, th), tip, BARK)
        pos[g["id"]] = tip
        leaf = (tip[0] * 1.12, tip[1] * 1.12, tip[2] + 0.25)
        add("sphere", writes.get(g["id"], f"leaf:{g['id']}"), leaf, (0.2, 0.2, 0.08), LEAF if g["has_check_mode"] else GREY)
    for i, v in enumerate(vers):
        z = 0.4 + (th - 0.8) * i / max(len(vers), 1)
        ang = 2.4 * i
        add("cone", v["id"], (0.5 * math.cos(ang), 0.5 * math.sin(ang), z), (0.06, 0.06, 0.25), DARK,
            rot=(math.pi / 2, 0, ang + math.pi / 2))
        pos[v["id"]] = (0.5 * math.cos(ang), 0.5 * math.sin(ang), z)

    # FRUIT: experiments
    exps = [n for n in graph["nodes"] if n["type"] == "experiment"]
    for i, x in enumerate(exps):
        ang = 2 * math.pi * (i + 0.5) / max(len(exps), 1)
        r = math.log10(x["observation_rows"] + 1) / 3
        p = (2.0 * math.cos(ang), 2.0 * math.sin(ang), th + 0.6)
        add("sphere", x["id"], p, (max(r, 0.25),) * 3, CYAN if x["observation_rows"] else GREY, wire=not x["observation_rows"])
        pos[x["id"]] = p
        curve(f"stem:{x['id']}", (0, 0, th), p, BARK)

    # NERVES
    for e in edges:
        if e["basis"] == "MANIFEST" and e["to"] in pos:
            curve(f"nerve:{e['check']}", pos[e["from"]], pos[e["to"]], CYAN)
        if e["basis"] == "PIN" and e["from"] in pos and e["to"] in pos:
            curve(f"pin:{e['from']}", pos[e["from"]], pos[e["to"]], RED if not e["holds"] else AMBER, broken=not e["holds"])

    # SAPLINGS: unmerged branches
    saps = [n for n in graph["nodes"] if n["type"] == "branch" and not n["reachable_from_origin_main"] and n["id"] != "origin/main"]
    for i, b in enumerate(saps):
        ang = 2 * math.pi * i / max(len(saps), 1)
        h = max(b["ahead_of_origin_main"] / 4, 0.3)
        lean = min(b["behind_origin_main"] / 40, 1.2)
        stale = (date.today() - date.fromisoformat(b["last_commit"])).days > 14
        p = (7.5 * math.cos(ang), 7.5 * math.sin(ang), h / 2)
        add("cyl", b["id"], p, (0.08, 0.08, h / 2), GREY if stale else LEAF, rot=(lean * math.cos(ang), lean * math.sin(ang), 0))
        pos[b["id"]] = p

    # RINGS: findings
    for f in graph["findings"]:
        key = f.get("file", "").split(":")[0] or f.get("generator") or f.get("claim") or f.get("branch") or f.get("experiment") or f.get("test")
        if key in pos:
            x, y, _ = pos[key]
            add("torus", f"finding:{f['detector']}:{key}", (x, y, 0.02), (0.5, 0.5, 0.5), RED)

    # HISTORY spiral
    log = subprocess.run(["git", "log", f"--since={(date.today() - timedelta(days=30)).isoformat()}", "--format=%cs"],
                         cwd=ROOT, capture_output=True, text=True).stdout.split()
    per_day: dict[str, int] = {}
    for d in log:
        per_day[d] = per_day.get(d, 0) + 1
    for i in range(30):
        d = (date.today() - timedelta(days=29 - i)).isoformat()
        n = per_day.get(d, 0)
        ang, rad = i * 0.42, 9.5 + i * 0.05
        add("cube", f"day:{d}", (rad * math.cos(ang), rad * math.sin(ang), n * 0.12 / 2 + 0.01), (0.15, 0.15, max(n * 0.12, 0.02) / 2),
            CYAN if n else DARK)

    # camera + light
    bpy.ops.object.empty_add(location=(0, 0, th * 0.4))
    aim = bpy.context.active_object
    bpy.ops.object.camera_add(location=(24, -24, 14))
    cam = bpy.context.active_object
    cam.data.lens = 32
    cam.constraints.new("TRACK_TO").target = aim
    scene.camera = cam
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 12))
    bpy.context.active_object.data.energy = 3

    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.render.render(write_still=True)
    return counts


# ── outside Blender ───────────────────────────────────────────────────────────
def receipt_body(counts: dict | None, png: Path) -> dict:
    return {"graph": GRAPH.relative_to(ROOT).as_posix(), "graph_sha256": sha(GRAPH),
            "graph_stable_digest": json.loads(GRAPH.read_text()).get("stable_digest"),
            "blender": subprocess.run([str(BLENDER), "--version"], capture_output=True, text=True).stdout.splitlines()[0],
            "objects": counts, "render_sha256": sha(png) if png.exists() else None,
            "mapping": "see module docstring; every placement is a function of a graph field",
            "non_claims": ["a picture of the repository's metadata, not a measurement of anything in the world",
                           "object sizes encode counts under the stated functions and no other property",
                           "the render is not pixel-deterministic: two consecutive grows on the same host differed (2026-09-07); the receipt binds the graph digest, and render_sha256 is informational only"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not GRAPH.exists():
        print("FAIL  docs/graph/repo-graph.json missing — run scripts/repo_graph.py first")
        return 1
    png, rec = OUT_DIR / "organism.png", OUT_DIR / "organism.receipt.json"
    if a.check:
        if not rec.exists():
            print("FAIL  organism receipt missing — run build_repo_organism.py")
            return 1
        r = json.loads(rec.read_text())
        if r.get("graph_stable_digest") != json.loads(GRAPH.read_text()).get("stable_digest"):
            print("FAIL  organism was grown from a different graph — rebuild")
            return 1
        print(f"ok    organism receipt binds the current graph ({sum((r.get('objects') or {}).values())} objects)")
        return 0
    if not BLENDER.exists():
        print(f"FAIL  {BLENDER} not found")
        return 1
    cmd = [str(BLENDER), "-b", "--factory-startup", "-noaudio", "--python-exit-code", "1",
           "-P", str(Path(__file__).resolve()), "--", "--worker"]
    log = BLEND_DIR / "build.log"
    BLEND_DIR.mkdir(parents=True, exist_ok=True)
    with log.open("w") as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=True)
    counts = json.loads((BLEND_DIR / "counts.json").read_text())
    rec.write_text(json.dumps({"grown_at": datetime.now().astimezone().isoformat(timespec="seconds"), **receipt_body(counts, png)}, indent=1) + "\n")
    print(f"grew {png.relative_to(ROOT)} · {sum(counts.values())} objects · receipt {rec.relative_to(ROOT)} · blend in {BLEND_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        graph = json.loads(GRAPH.read_text())
        counts = grow(graph, OUT_DIR / "organism.png", BLEND_DIR / "organism.blend")
        (BLEND_DIR / "counts.json").write_text(json.dumps(counts))
    else:
        sys.exit(main())
