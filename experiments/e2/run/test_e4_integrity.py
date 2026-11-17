#!/usr/bin/env python3
"""E4 regressions: the calibrated configuration is a checked freeze.

Run with ``python3 -B experiments/e2/run/test_e4_integrity.py -v``.
Only two synthetic text fixtures are scored; real adapters are replaced
with deterministic in-memory scorers and all outputs use a temp directory.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FROZEN_ANALYSIS = {
    "N_MIN": 1097,
    "N_STOP": 600,
    "B": 2000,
    "PERM": 2000,
    "SEED": "MC-E2-PILOT-V1-FREEZE-2026-09-01",
}
GUARDS = ("lg4", "lg3", "sg2b")


def digest(config: dict) -> str:
    """Independent implementation of the documented canonical hash."""
    probe = dict(config, config_hash="")
    canonical = json.dumps(probe, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_script(name: str):
    spec = importlib.util.spec_from_file_location("e4_test_" + name,
                                                 HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FreezeIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="e2-e4-regression-")
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.config_path = self.scratch / "e2_config.json"
        self.freeze_path = self.scratch / "e2_config.freeze.json"
        self.config = {
            "study_id": "MC-E2-PILOT-V1",
            "fpr_target": 0.05,
            "calibrated": "on the frozen benign calibration half only",
            "analysis": dict(FROZEN_ANALYSIS),
            "results": {g: {"threshold": 0.4, "achieved_fpr": 0.05,
                            "distance_to_target": 0.0, "n": 800}
                        for g in GUARDS},
            "config_hash": "",
        }
        self.config["config_hash"] = digest(self.config)
        self.write_config()
        self.freeze_path.write_text(json.dumps({
            "config_hash": self.config["config_hash"]}))

    def write_config(self):
        self.config_path.write_text(json.dumps(self.config))

    @staticmethod
    def invoke(module, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            try:
                rc = module.main()
            except SystemExit as exc:
                rc = exc.code if isinstance(exc.code, int) else 1
                if exc.code and not isinstance(exc.code, int):
                    print(exc.code, file=sys.stderr)
        return rc, stdout.getvalue(), stderr.getvalue()

    def collect(self, label):
        collector = load_script("collect")
        adapters = types.ModuleType("adapters")
        adapters.SCORERS = {g: lambda text: 0.5 for g in GUARDS}
        texts = types.ModuleType("items_text")
        texts.benign_texts = lambda split: {"fixture-benign": "synthetic benign"}
        texts.harmful_texts = lambda: {"fixture-harmful": "synthetic harmful"}

        def read_items(name, stratum):
            return [{"id": "fixture-harmful" if stratum == "harmful"
                     else "fixture-benign", "stratum": stratum}]

        out = self.scratch / label
        with patch.dict(sys.modules, {"adapters": adapters, "items_text": texts}), \
                patch.object(collector, "read_items", read_items):
            result = self.invoke(collector, ["collect.py", "--config",
                                            str(self.config_path), "--out", str(out)])
        rows = [json.loads(line) for path in out.glob("*.jsonl")
                for line in path.read_text().splitlines()]
        return (*result, rows)

    def analyze(self, label):
        analyzer = load_script("analyze")
        rows_path = self.scratch / "empty.jsonl"
        rows_path.write_text("")
        return self.invoke(analyzer, ["analyze.py", "--rows", str(rows_path),
                                      "--config", str(self.config_path),
                                      "--freeze-record", str(self.freeze_path),
                                      "--out", str(self.scratch / label)])

    def assert_structured_refusal(self, rc, stdout, stderr):
        self.assertNotEqual(rc, 0, "configuration mismatch must bind the exit code")
        self.assertNotIn("Traceback", stdout + stderr)
        try:
            payload = json.loads(stderr.strip())
        except (json.JSONDecodeError, TypeError):
            self.fail("refusal stderr must be structured JSON: " + repr(stderr))
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload.get("error") or payload.get("reason"),
                        "structured refusal must name its error or reason")

    def test_01_stale_threshold_hash_refuses_before_emitting(self):
        original = self.collect("original")
        self.assertEqual(original[0], 0, original[2])
        original_bits = [r["normalized_outcome"] for r in original[3]]
        self.assertEqual(original_bits, [1, 1, 1, 0, 0, 0])
        for guard in GUARDS:
            self.config["results"][guard]["threshold"] = 0.6
        self.write_config()  # Deliberately retain the original .4 hash.
        stale = self.collect("stale")
        stale_bits = [r["normalized_outcome"] for r in stale[3]]
        print("E4 threshold .4->.6 stale-hash witness: " + json.dumps({
            "original_exit": original[0], "stale_exit": stale[0],
            "original_event_bits": original_bits, "stale_event_bits": stale_bits,
            "changed_event_bits": sum(a != b for a, b in
                                      zip(original_bits, stale_bits)),
            "stale_rows_emitted": len(stale[3]), "stderr": stale[2]},
            sort_keys=True), flush=True)
        self.assert_structured_refusal(*stale[:3])
        self.assertEqual(stale[3], [], "stale hashes must emit zero rows")

    def test_02_real_rows_carry_canonical_configuration_digest(self):
        result = self.collect("canonical")
        self.assertEqual(result[0], 0, result[2])
        self.assertEqual(len(result[3]), 6)
        self.assertEqual({r["configuration_hash"] for r in result[3]},
                         {digest(self.config)})

    def test_03_analyzer_rejects_freeze_record_hash_mismatch(self):
        self.freeze_path.write_text(json.dumps({"config_hash": "0" * 64}))
        self.assert_structured_refusal(*self.analyze("record-mismatch"))

    def test_04_analyzer_rejects_stale_content_hash(self):
        self.config["results"]["lg4"]["threshold"] = 0.6
        self.write_config()
        self.assert_structured_refusal(*self.analyze("content-mismatch"))

    def test_05_analysis_constants_are_hash_covered(self):
        original_hash = self.config["config_hash"]
        for key, value in FROZEN_ANALYSIS.items():
            changed = json.loads(json.dumps(self.config))
            changed["analysis"][key] = value + 1 if isinstance(value, int) else value + "-changed"
            self.assertNotEqual(digest(changed), original_hash, key)
        self.config["analysis"]["B"] += 1
        self.write_config()
        result = self.collect("analysis-constant-mismatch")
        self.assert_structured_refusal(*result[:3])
        self.assertEqual(result[3], [])


if __name__ == "__main__":
    unittest.main()
