#!/usr/bin/env python3
"""Bind the downloadable résumé PDF to the sources that render it.

The PDF is deliberately a committed artifact so visitors can download it
without a browser or an email exchange. A committed artifact needs a receipt:
otherwise a valid-but-old PDF can silently diverge from the web résumé it
claims to print. This module records both the PDF hash and every local input
that materially affects the printed page.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_REL = "resume/pranav-bhave-resume.pdf"
MANIFEST_REL = "resume/pranav-bhave-resume.manifest.json"
PDF = ROOT / PDF_REL
MANIFEST = ROOT / MANIFEST_REL

# The résumé loads the shared stylesheet, navigation script, and these local
# fonts in addition to its own markup. The builder and receipt code are inputs
# too: their command-line flags and validation rules determine what this
# artifact means. Keep the full print pipeline explicit so neither a visual
# change nor a renderer-rule change can leave a stale downloadable artifact.
INPUTS = (
    "resume/index.html",
    "assets/site.css",
    "assets/site.js",
    "assets/fonts/fraunces-roman.woff2",
    "assets/fonts/fraunces-italic.woff2",
    "assets/fonts/instrument-sans-roman.woff2",
    "assets/fonts/fragment-mono.woff2",
    "scripts/build_resume_pdf.py",
    "scripts/resume_artifact.py",
    "scripts/check_layout.py",
)
SCHEMA_VERSION = 1


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_digests() -> dict[str, str]:
    """Return the exact print inputs, rejecting a missing declared source."""
    result: dict[str, str] = {}
    for rel in INPUTS:
        source = ROOT / rel
        if not source.is_file():
            raise FileNotFoundError(f"declared résumé print input is missing: {rel}")
        result[rel] = digest(source)
    return result


def payload(renderer: str) -> dict[str, object]:
    if not PDF.is_file():
        raise FileNotFoundError(f"résumé PDF is missing: {PDF_REL}")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": PDF_REL,
        "artifact_sha256": digest(PDF),
        "sources": source_digests(),
        "renderer": renderer,
    }


def write_manifest(renderer: str) -> None:
    """Write the provenance receipt only after a validated PDF exists."""
    MANIFEST.write_text(json.dumps(payload(renderer), indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


def verify_manifest() -> list[str]:
    """Return every reproducibility error without mutating the checkout."""
    errors: list[str] = []
    if not MANIFEST.is_file():
        return [f"{MANIFEST_REL} is missing — rebuild with scripts/build_resume_pdf.py"]
    try:
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{MANIFEST_REL} is invalid JSON ({exc})"]
    if not isinstance(record, dict):
        return [f"{MANIFEST_REL} must contain an object"]
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{MANIFEST_REL} schema is {record.get('schema_version')!r}, "
                      f"expected {SCHEMA_VERSION}")
    if record.get("artifact") != PDF_REL:
        errors.append(f"{MANIFEST_REL} names {record.get('artifact')!r}, expected {PDF_REL}")
    if not isinstance(record.get("renderer"), str) or not record["renderer"].strip():
        errors.append(f"{MANIFEST_REL} has no renderer identity")

    try:
        expected_sources = source_digests()
    except FileNotFoundError as exc:
        errors.append(str(exc))
        expected_sources = None
    recorded_sources = record.get("sources")
    if expected_sources is not None:
        if not isinstance(recorded_sources, dict):
            errors.append(f"{MANIFEST_REL} has no source digest map")
        elif recorded_sources != expected_sources:
            changed = sorted(set(recorded_sources) ^ set(expected_sources))
            changed.extend(rel for rel in expected_sources
                           if recorded_sources.get(rel) != expected_sources[rel])
            names = ", ".join(dict.fromkeys(changed)) or "unknown input"
            errors.append(f"résumé print inputs changed since the PDF was built: {names}")

    if not PDF.is_file():
        errors.append(f"{PDF_REL} is missing")
    elif record.get("artifact_sha256") != digest(PDF):
        errors.append(f"{PDF_REL} does not match the hash in {MANIFEST_REL}")
    return errors
