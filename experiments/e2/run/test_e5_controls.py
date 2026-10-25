#!/usr/bin/env python3
"""E5 mutations: every computed control must bind the analysis gate.

No frozen constants, tolerances, outcomes, or sample rules are altered.
The duplicate fault changes only Delta(A,A) by +1e-6, above the frozen
1e-9 duplicate tolerance. The complete CLI fixture has n=600, so its
unmodified outcome is precision HOLD rather than STOP.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import itertools
import json
import math
import sys
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config_integrity import synthetic_config

GUARDS = ("lg4", "lg3", "sg2b")


def analyzer_module():
    spec = importlib.util.spec_from_file_location("e5_analyzer", HERE / "analyze.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def complete_fixture(n):
    return {f"fixture-{i:04d}": {g: (i >> j) & 1
                                for j, g in enumerate(GUARDS)}
            for i in range(n)}


class ControlsTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = analyzer_module()
        self.assertEqual(self.analyzer.B, 2000)
        self.assertEqual(self.analyzer.PERM, 2000)
        self.cc = complete_fixture(8)

    def run_main(self, *, duplicate_fault):
        with tempfile.TemporaryDirectory(prefix="e2-e5-regression-") as temp:
            scratch = Path(temp)
            cfg = synthetic_config()
            config_path = scratch / "e2_config.json"
            freeze_path = scratch / "e2_config.freeze.json"
            rows_path = scratch / "rows.jsonl"
            out = scratch / "out"
            config_path.write_text(json.dumps(cfg))
            freeze_path.write_text(json.dumps({"config_hash": cfg["config_hash"]}))
            rows = [{"item_id": item, "stratum": "harmful", "guardrail_id": guard,
                     "normalized_outcome": event, "missingness_code": "observed",
                     "configuration_hash": cfg["config_hash"], "synthetic": True}
                    for item, events in complete_fixture(600).items()
                    for guard, event in events.items()]
            rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            argv = ["analyze.py", "--rows", str(rows_path), "--config", str(config_path),
                    "--freeze-record", str(freeze_path), "--out", str(out)]
            original_delta = self.analyzer.delta

            def mutated_delta(cc, a, b):
                d, pa, pb, n = original_delta(cc, a, b)
                return (d + (1e-6 if duplicate_fault and a == b else 0), pa, pb, n)

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(self.analyzer, "delta", mutated_delta), \
                    patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout), \
                    contextlib.redirect_stderr(stderr):
                try:
                    rc = self.analyzer.main()
                except Exception:
                    rc = 1
                    traceback.print_exc()
            reports = [json.loads(p.read_text()) for p in out.glob("*.json")]
            result = rc, stdout.getvalue(), stderr.getvalue(), reports
            errors = [abs(control["delta_self"] - control["theoretical"])
                      for report in reports for stratum in report.get("strata", [])
                      for control in stratum.get("duplicate_column_control", {}).values()]
            print("E5 main witness: " + json.dumps({
                "duplicate_fault": duplicate_fault, "exit_code": rc,
                "stdout": result[1], "stderr": result[2],
                "report_count": len(reports), "duplicate_abs_errors": errors,
                "command": argv}, sort_keys=True), flush=True)
            return result

    def test_01_planted_duplicate_column_fault_binds_gate(self):
        rc, stdout, stderr, reports = self.run_main(duplicate_fault=True)
        self.assertEqual(rc, 1, "+1e-6 duplicate fault must bind the exit code")
        self.assertNotIn("Traceback", stdout + stderr)
        try:
            error = json.loads(stderr.strip())
        except json.JSONDecodeError:
            self.fail("failed control must emit structured JSON: " + repr(stderr))
        self.assertIn("duplicate", json.dumps(error).lower())
        self.assertNotIn("all five controls executed", stdout)
        for report in reports:
            self.assertFalse(any(s.get("pairs") or s.get("marginals")
                                 for s in report.get("strata", [])),
                             "a failed control must withhold final estimates")

    def test_02_fault_removed_passes_with_frozen_constants(self):
        rc, stdout, stderr, reports = self.run_main(duplicate_fault=False)
        self.assertEqual(rc, 0, stderr)
        self.assertIn("precision HOLD", stdout)
        self.assertTrue(reports)
        self.assertEqual(reports[0]["sizing"]["shared_n"], 600)

    def test_independent_calculator_fault_is_asserted(self):
        original = self.analyzer.delta_independent
        with patch.object(self.analyzer, "delta_independent",
                          lambda *args: original(*args) + 1e-6):
            with self.assertRaisesRegex((AssertionError, ValueError), "independent"):
                self.analyzer.analyze_stratum("harmful", self.cc, self.cc)

    def test_permutation_marginal_corruption_is_asserted(self):
        def corrupt_shuffle(rng, values):
            values[:] = [1] * len(values)

        with patch.object(self.analyzer.random.Random, "shuffle", corrupt_shuffle):
            with self.assertRaisesRegex((AssertionError, ValueError), "permutation"):
                self.analyzer.analyze_stratum("harmful", self.cc, self.cc)

    def test_nonfinite_bootstrap_interval_is_asserted(self):
        with patch.object(self.analyzer, "bootstrap_ci", lambda *args: (math.nan, math.nan)):
            with self.assertRaisesRegex((AssertionError, ValueError), "bootstrap"):
                self.analyzer.analyze_stratum("harmful", self.cc, self.cc)

    def test_label_noise_recalculation_fault_is_asserted(self):
        original = self.analyzer.delta

        def corrupt_noisy_delta(cc, a, b):
            d, pa, pb, n = original(cc, a, b)
            return (d + (1e-6 if cc is not self.cc else 0), pa, pb, n)

        with patch.object(self.analyzer, "delta", corrupt_noisy_delta):
            with self.assertRaisesRegex((AssertionError, ValueError), "label.noise"):
                self.analyzer.analyze_stratum("harmful", self.cc, self.cc)

    def test_invalid_missingness_interval_is_asserted(self):
        with patch.object(self.analyzer, "missingness_delta_bounds", lambda *args: (0.2, -0.2)):
            with self.assertRaisesRegex((AssertionError, ValueError), "missingness"):
                self.analyzer.analyze_stratum("harmful", self.cc, self.cc)

    def test_complete_data_missingness_mismatch_is_asserted(self):
        with patch.object(self.analyzer, "missingness_delta_bounds", lambda *args: (0.1, 0.1)):
            with self.assertRaisesRegex((AssertionError, ValueError), "missingness"):
                self.analyzer.analyze_stratum("harmful", self.cc, self.cc)

    def test_small_missingness_control_matches_all_completions(self):
        fixture = {"a": {"lg4": 1, "lg3": 1}, "b": {"lg4": 0},
                   "c": {"lg3": 1}, "d": {}}
        free = [(item, guard) for item, events in fixture.items()
                for guard in ("lg4", "lg3") if guard not in events]
        deltas = []
        for fill in itertools.product((0, 1), repeat=len(free)):
            completion = {item: dict(events) for item, events in fixture.items()}
            for (item, guard), bit in zip(free, fill):
                completion[item][guard] = bit
            n = len(completion)
            pa = sum(v["lg4"] for v in completion.values()) / n
            pb = sum(v["lg3"] for v in completion.values()) / n
            p11 = sum(v["lg4"] * v["lg3"] for v in completion.values()) / n
            deltas.append(p11 - pa * pb)
        self.assertEqual(self.analyzer.missingness_delta_bounds(fixture, "lg4", "lg3"),
                         (min(deltas), max(deltas)))


if __name__ == "__main__":
    unittest.main()
