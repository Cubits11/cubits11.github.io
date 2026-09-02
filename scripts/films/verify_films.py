#!/usr/bin/env python3
"""Verify every film's claim manifest, render receipt, and evidence bindings.

For each films/<slug>/manifest.yaml:
  * required fields present: id, title, thesis, epistemic_operation, claim,
    scope, status, duration_s, evidence[], objects[], falsifier, non_claims[],
    evidence_commits, claim_frames[]
  * every evidence binding {fact, value} equals films/data/facts.json (which
    scripts/films/bind_facts.py --check keeps equal to the registries), so a
    number on screen can never drift from claims.yaml / census.yaml
  * every object on screen is labelled with one of OBSERVED / DERIVED / PROVED
    / CONSTRUCTED / ILLUSTRATIVE / UNKNOWN / REGISTRY / DOCUMENT
  * the primary render (render.primary — master by default, square for a feed
    cut) exists with a receipt: duration within one frame of the manifest,
    the format's resolution, zero text overflows, determinism check
    passed, and the receipt's input hashes match the current film source and
    facts file (a stale render fails)
  * every declared claim frame has its still on disk
  * duration inside the 8–90 s law

No browser is needed; this checks artifacts, not pixels. Exit 1 on any failure.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FILMS = ROOT / "films"
KINDS = {"OBSERVED", "DERIVED", "PROVED", "CONSTRUCTED", "ILLUSTRATIVE", "UNKNOWN", "REGISTRY", "DOCUMENT"}
REQUIRED = ["id", "title", "thesis", "epistemic_operation", "claim", "scope", "status", "duration_s",
            "evidence", "objects", "falsifier", "non_claims", "evidence_commits", "claim_frames"]

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"ok    {msg}")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_film(d: Path, facts: dict) -> None:
    slug = d.name
    mpath = d / "manifest.yaml"
    m = yaml.safe_load(mpath.read_text())
    for f in REQUIRED:
        if f not in m:
            fail(f"{slug}: manifest missing {f}")
    if failures and any(s.startswith(slug + ":") for s in failures):
        return
    if m["id"] != slug:
        fail(f"{slug}: manifest id {m['id']!r} differs from directory")
    dur = float(m["duration_s"])
    if not 8 <= dur <= 90:
        fail(f"{slug}: duration {dur}s outside the 8–90 s law")
    for e in m["evidence"]:
        fid = e.get("fact")
        if fid not in facts:
            fail(f"{slug}: evidence binds unknown fact {fid}")
            continue
        if json.dumps(e.get("value"), sort_keys=True) != json.dumps(facts[fid]["value"], sort_keys=True):
            fail(f"{slug}: {fid} manifest value {e.get('value')!r} != registry value {facts[fid]['value']!r}")
        if e.get("kind") and e["kind"] != facts[fid]["kind"]:
            fail(f"{slug}: {fid} manifest kind {e['kind']} != registry kind {facts[fid]['kind']}")
    for o in m["objects"]:
        if o.get("status") not in KINDS:
            fail(f"{slug}: object {o.get('object')!r} has status {o.get('status')!r}, not one of {sorted(KINDS)}")
    if not m["non_claims"]:
        fail(f"{slug}: non_claims is empty — every film states what it does not show")
    if not m["falsifier"]:
        fail(f"{slug}: falsifier missing")

    render_spec = m.get("render") or {}
    primary = render_spec.get("primary", "master")
    dims = {"master": (1920, 1080), "vertical": (1080, 1920), "square": (1080, 1080)}[primary]
    receipt_path = d / "renders" / f"{slug}__{primary}.receipt.json"
    if not receipt_path.exists():
        fail(f"{slug}: no {primary} render receipt ({receipt_path.relative_to(ROOT)})")
        return
    r = json.loads(receipt_path.read_text())
    if abs(r["duration_s"] - dur) > 1.0 / r["fps"] + 1e-9:
        fail(f"{slug}: rendered duration {r['duration_s']}s != manifest {dur}s")
    if (r["width"], r["height"]) != dims:
        fail(f"{slug}: {primary} resolution {r['width']}x{r['height']} is not {dims[0]}x{dims[1]}")
    if render_spec.get("kind") == "social":
        # a feed cut: 8–12 s, phone previews on disk, a real route, registered campaign and experiment
        if not 8 <= dur <= 12:
            fail(f"{slug}: social cut is {dur}s; the feed law is 8–12 s")
        previews = r["outputs"].get("phone_previews") or []
        if len(previews) < len(m["claim_frames"]):
            fail(f"{slug}: {len(previews)} phone previews for {len(m['claim_frames'])} claim frames — render with the phone-preview path")
        for pv in previews:
            if not (d / pv).exists():
                fail(f"{slug}: phone preview missing {pv}")
        route = m.get("cta_route", "")
        if not (ROOT / route.strip("/") / "index.html").exists():
            fail(f"{slug}: cta_route {route!r} is not a committed page")
        campaigns = {row["id"] for row in yaml.safe_load((ROOT / "campaigns.yaml").read_text())["campaigns"]}
        if m.get("campaign") not in campaigns:
            fail(f"{slug}: campaign {m.get('campaign')!r} is not registered")
        experiments = {e["id"] for e in yaml.safe_load((ROOT / "distribution" / "experiments.yaml").read_text())["experiments"]}
        if m.get("experiment") not in experiments:
            fail(f"{slug}: experiment {m.get('experiment')!r} is not registered")
        if m.get("derived_from") and not (ROOT / "films" / m["derived_from"] / "manifest.yaml").exists():
            fail(f"{slug}: derived_from {m['derived_from']} has no manifest")
        if not m.get("text_budget", {}).get("essential"):
            fail(f"{slug}: a social cut must declare its essential text budget")
    if r["text_overflows"]:
        fail(f"{slug}: {len(r['text_overflows'])} text overflow(s) in render: {r['text_overflows'][:2]}")
    if not r["determinism"]["identical"]:
        fail(f"{slug}: determinism check failed (re-captured frames differ)")
    for rel, digest in r["inputs"].items():
        p = d / rel if rel == "film.html" else ROOT / rel
        if not p.exists():
            fail(f"{slug}: receipt input {rel} missing")
        elif sha256_file(p) != digest:
            fail(f"{slug}: render is stale — {rel} changed since the receipt (re-render and re-inspect)")
    for out in ("master", "poster"):
        p = d / r["outputs"][out]
        if not p.exists():
            fail(f"{slug}: output {out} missing at {p.relative_to(ROOT)}")
    mp4 = d / r["outputs"]["master"]
    if mp4.exists() and sha256_file(mp4) != r["outputs"]["master_sha256"]:
        fail(f"{slug}: master mp4 bytes differ from the receipt")
    probe = r["outputs"].get("master_duration_probe_s")
    if probe is not None and abs(probe - dur) > 0.2:
        fail(f"{slug}: encoded duration {probe}s differs from manifest {dur}s")
    for s in r["outputs"]["stills"]:
        if not (d / s).exists():
            fail(f"{slug}: still missing {s}")
    if len(r["outputs"]["claim_frames"]) != len(m["claim_frames"]):
        fail(f"{slug}: manifest declares {len(m['claim_frames'])} claim frames, render exported {len(r['outputs']['claim_frames'])}")
    for cf in r["outputs"]["claim_frames"]:
        if not (d / cf["still"]).exists():
            fail(f"{slug}: claim-frame still missing {cf['still']}")
    # every fact the film read at render time must be declared in the manifest
    declared = {e["fact"] for e in m["evidence"]}
    undeclared = [f for f in r.get("facts_used", []) if f not in declared]
    if undeclared:
        fail(f"{slug}: film reads facts not declared in its manifest: {undeclared}")
    for c in m["evidence_commits"]:
        if not (isinstance(c.get("commit"), str) and len(c["commit"]) == 40):
            fail(f"{slug}: evidence commit {c!r} is not a 40-hex revision")
    if not any(s.startswith(slug + ":") for s in failures):
        ok(f"{slug}: manifest bound ({len(m['evidence'])} facts), receipt fresh, {r['frames']} frames @ {r['fps']}fps, "
           f"{r['duration_s']}s, determinism ok, 0 overflows, {len(r['outputs']['claim_frames'])} claim frames")


def main() -> int:
    facts_path = FILMS / "data" / "facts.json"
    if not facts_path.exists():
        fail("films/data/facts.json missing — run scripts/films/bind_facts.py")
        return 1
    facts = json.loads(facts_path.read_text())["facts"]
    dirs = sorted(p.parent for p in FILMS.glob("*/manifest.yaml"))
    if not dirs:
        fail("no film manifests found")
    for d in dirs:
        check_film(d, facts)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print(f"ok    {len(dirs)} film(s) verified against the bound facts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
