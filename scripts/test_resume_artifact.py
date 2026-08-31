#!/usr/bin/env python3
"""Regression coverage for the résumé PDF's source-binding receipt."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import resume_artifact as artifact


class ResumeArtifactTests(unittest.TestCase):
    def assert_changed_input_is_detected(self, changed: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rel in artifact.INPUTS:
                source = root / rel
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(f"original {rel}\n", encoding="utf-8")
            pdf = root / artifact.PDF_REL
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(b"%PDF-1.4\nsource-bound test\n")
            manifest = root / artifact.MANIFEST_REL
            with mock.patch.object(artifact, "ROOT", root), \
                 mock.patch.object(artifact, "PDF", pdf), \
                 mock.patch.object(artifact, "MANIFEST", manifest):
                artifact.write_manifest("test renderer")
                self.assertEqual(artifact.verify_manifest(), [])
                (root / changed).write_text(f"changed {changed}\n", encoding="utf-8")
                errors = artifact.verify_manifest()
            self.assertTrue(any("résumé print inputs changed" in error for error in errors))
            self.assertTrue(any(changed in error for error in errors))

    def test_source_edit_requires_a_new_pdf_receipt(self) -> None:
        self.assert_changed_input_is_detected("resume/index.html")

    def test_builder_edit_requires_a_new_pdf_receipt(self) -> None:
        self.assert_changed_input_is_detected("scripts/build_resume_pdf.py")


if __name__ == "__main__":
    unittest.main()
