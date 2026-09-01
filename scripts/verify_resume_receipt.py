#!/usr/bin/env python3
"""The committed résumé PDF must still be a print of the committed page.

The PDF is a build artifact that ships in the repository, so nothing stops it
drifting from resume/index.html — someone edits the page, forgets the rebuild,
and the downloadable résumé quietly becomes a second, stale account of a
person's history. This gate closes that gap without needing a browser: it
recomputes the digests the receipt claims and refuses any mismatch.

Run: python scripts/verify_resume_receipt.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / "resume" / "pranav-bhave-resume.receipt.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not RECEIPT.exists():
        print(f"FAIL  {RECEIPT.relative_to(ROOT)} is missing — the PDF is unbound. "
              "Run: python scripts/build_resume_pdf.py")
        return 1
    receipt = json.loads(RECEIPT.read_text())
    errors: list[str] = []

    artifact = ROOT / receipt["artifact"]
    if not artifact.exists():
        errors.append(f"{receipt['artifact']} is missing")
    else:
        if artifact.stat().st_size != receipt["artifact_bytes"]:
            errors.append(f"{receipt['artifact']}: size {artifact.stat().st_size} "
                          f"!= receipt {receipt['artifact_bytes']}")
        digest = sha256(artifact)
        if digest != receipt["artifact_sha256"]:
            errors.append(f"{receipt['artifact']}: sha256 {digest[:12]}… "
                          f"!= receipt {receipt['artifact_sha256'][:12]}…")
        if artifact.read_bytes()[:5] != b"%PDF-":
            errors.append(f"{receipt['artifact']}: not a PDF")
        # Chromium resolves site-relative links against the local server used
        # during the print build unless the resume names canonical URLs. A
        # downloadable resume must never send a recruiter to a loopback host.
        pdf_bytes = artifact.read_bytes()
        for local_origin in (b"127.0.0.1", b"localhost"):
            if local_origin in pdf_bytes:
                errors.append(
                    f"{receipt['artifact']}: contains a local link target "
                    f"({local_origin.decode()}); rebuild with public URLs")

    for rel, expected in receipt["sources"].items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: source named by the receipt is missing")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(
                f"{rel} changed since the PDF was printed "
                f"({actual[:12]}… != {expected[:12]}…). The downloadable résumé no "
                "longer matches the page. Run: python scripts/build_resume_pdf.py")

    if errors:
        for error in errors:
            print(f"FAIL  {error}")
        return 1
    print(f"ok    résumé PDF is bound to its {len(receipt['sources'])} sources "
          f"(renderer: {receipt.get('renderer', 'unknown')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
