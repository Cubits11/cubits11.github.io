#!/usr/bin/env python3
"""Deterministic-render receipts for the 3D film lane.

A PNG that Blender writes carries a tEXt chunk with the render time, so two
byte-identical images have different file hashes. The pixel data lives in IDAT.
Hash IDAT; record the file hash only as provenance.

Verified 2026-09-05, Blender 5.1.2 (ec6e62d40fa9): IDAT is identical across
runs for Cycles CPU (seed 0, denoising off) and for EEVEE (48 TAA samples) on
claim_observatory_world_v3.blend. See API-FACTS.md.

Standalone: needs no bpy. Run against rendered PNGs.
"""
from __future__ import annotations
import hashlib, json, struct, subprocess, sys
from pathlib import Path

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def png_chunks(path: Path) -> dict[str, bytes]:
    """Concatenated payload per chunk type. PNG only; raises on anything else."""
    b = path.read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    out: dict[str, bytes] = {}
    i = 8
    while i < len(b):
        (ln,) = struct.unpack(">I", b[i : i + 4])
        typ = b[i + 4 : i + 8].decode("ascii")
        out[typ] = out.get(typ, b"") + b[i + 8 : i + 8 + ln]
        i += 12 + ln
    return out


def idat_sha256(path: Path) -> str:
    """The hash that means 'this is the same image'."""
    return hashlib.sha256(png_chunks(path)["IDAT"]).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(a: Path, b: Path) -> dict:
    """Chunk-level diff. Two renders of one scene must differ only in tEXt."""
    ca, cb = png_chunks(a), png_chunks(b)
    types = sorted(set(ca) | set(cb))
    diff = [t for t in types if ca.get(t) != cb.get(t)]
    return {
        "identical_pixels": ca.get("IDAT") == cb.get("IDAT"),
        "differing_chunks": diff,
        "expected_differing": ["tEXt"],
        "unexpected": [t for t in diff if t != "tEXt"],
        "idat_sha256": idat_sha256(a),
    }


def blender_build() -> dict:
    """Build identity. Determinism was verified on one build; say which."""
    out = subprocess.run(
        [BLENDER, "--version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    d = {"version_line": out[0].strip()}
    for line in out[1:6]:
        if ":" in line:
            k, v = line.split(":", 1)
            d[k.strip().replace(" ", "_")] = v.strip()
    return d


def receipt(blend: Path, renders: list[Path], settings: dict) -> dict:
    """A 3D render receipt. Mirrors films/*/renders/*.receipt.json in spirit."""
    return {
        "kind": "blender_render_receipt",
        "schema": 0,
        "blend": {"path": str(blend), "sha256": file_sha256(blend)},
        "blender": blender_build(),
        "settings": settings,
        "renders": [
            {
                "path": str(p),
                "idat_sha256": idat_sha256(p),
                "file_sha256": file_sha256(p),
            }
            for p in renders
        ],
        "determinism": (
            compare(renders[0], renders[1]) if len(renders) >= 2 else "not_verified"
        ),
        "non_claims": [
            "Determinism verified on one host, one build, one scene, CPU/EEVEE only.",
            "No claim holds across Blender versions, machines, sample counts, or GPU.",
            "A matching IDAT means the image is identical. It means nothing about the scene's correctness.",
        ],
    }


if __name__ == "__main__":
    args = [Path(a) for a in sys.argv[1:]]
    if len(args) == 2 and all(a.suffix == ".png" for a in args):
        print(json.dumps(compare(*args), indent=1))
    elif len(args) == 1:
        print(idat_sha256(args[0]))
    else:
        print(__doc__)
        print("usage: determinism.py A.png [B.png]")
        sys.exit(2)
