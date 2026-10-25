#!/usr/bin/env python3
"""E3 CLI regressions: STOP outputs contain counts, never estimates."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config_integrity import synthetic_config

GUARDS = ("lg4", "lg3", "sg2b")
ESTIMATE_KEYS = {
    "pairs", "delta", "p", "pa", "pb", "p11", "marginals",
    "bootstrap95", "bootstrap", "estimates", "estimate", "wilson95",
    "stack_secondary", "all_event_rate", "product_of_event_rates",
    "permutation_null_95band", "independent_calculator",
    "duplicate_column_control", "label_noise_control", "missingness_bounds",
    "frechet_set_counts", "loo_exclusive", "delta_self", "theoretical",
}
COUNT_KEYS = {
    "shared_n", "complete_case_n", "items_with_missing_cells",
    "n_min", "n_stop", "observed_n", "missing_n", "item_n",
}


def estimate_leaks(value, path=()):
    """Recursively catch estimate fields and unexpected numeric leaves.

    STOP may disclose its frozen sizing counts. Numeric leaves elsewhere,
    including nested lists or renamed statistic fields, are leaks.
    """
    leaks = []
    if isinstance(value, dict):
        for key, child in value.items():
            if (key.lower() in ESTIMATE_KEYS or
                    any(word in key.lower() for word in
                        ("delta", "estimate", "bootstrap", "marginal"))):
                leaks.append(".".join((*path, key)))
            leaks.extend(estimate_leaks(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaks.extend(estimate_leaks(child, (*path, str(index))))
    elif type(value) in (int, float):
        allowed_count = (path and path[-1] in COUNT_KEYS) or \
                        (len(path) >= 2 and path[-2] == "per_stratum")
        if not allowed_count:
            leaks.append("numeric:" + ".".join(path))
    return leaks


class StopGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="e2-e3-regression-")
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.config = synthetic_config()
        self.config_path = self.scratch / "e2_config.json"
        self.config_path.write_text(json.dumps(self.config))
        self.freeze_path = self.scratch / "e2_config.freeze.json"
        self.freeze_path.write_text(json.dumps({
            "config_hash": self.config["config_hash"]}))

    def row(self, item, guard, event, *, stratum="harmful"):
        observed = event is not None
        item_hash = hashlib.sha256(item.encode()).hexdigest()
        return {
            "schema_version": "cc.e2_observation_row.v1",
            "study_id": "MC-E2-PILOT-V1", "run_id": "SYNTHETIC-E3-REGRESSION",
            "item_id": item, "item_source": "synthetic E3 regression fixture",
            "item_source_version": "1", "item_hash": item_hash,
            "guardrail_id": guard, "guardrail_version": "SYNTHETIC",
            "policy_version": "SYNTHETIC", "configuration_hash": self.config["config_hash"],
            "raw_input_hash": item_hash,
            "raw_output_hash": hashlib.sha256(str(event).encode()).hexdigest()
                               if observed else None,
            "raw_outcome": "allow" if event == 1 else "hard_block" if observed else None,
            "raw_outcome_detail": None, "normalized_outcome": event,
            "normalizer_version": "h.miss.v1", "stratum": stratum,
            "execution_timestamp": "2026-10-24T00:00:00Z",
            "execution_status": "success" if observed else "timeout",
            "missingness_code": "observed" if observed else "timeout",
            "predeclared_exclusion": False, "replicate_id": 1,
            "reference_label": 1, "reference_label_uncertainty": None,
        }

    def run_fixture(self, label, rows):
        rows_path = self.scratch / (label + ".jsonl")
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        out = self.scratch / (label + "-out")
        command = [sys.executable, "-B", str(HERE / "analyze.py"),
                   "--rows", str(rows_path), "--config", str(self.config_path),
                   "--freeze-record", str(self.freeze_path), "--out", str(out)]
        proc = subprocess.run(command, capture_output=True, text=True)
        reports = [json.loads(path.read_text()) for path in out.glob("*.json")]
        leaks = [leak for report in reports
                 if report.get("sizing", {}).get("verdict") == "STOP"
                 for leak in estimate_leaks(report)]
        print("E3 fixture witness: " + json.dumps({
            "fixture": label, "command": command, "exit_code": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr,
            "report_count": len(reports), "deep_scan_leak_count": len(leaks),
            "deep_scan_leaks": leaks}, sort_keys=True), flush=True)
        return proc, reports, leaks

    def assert_stop(self, result, *, reason=None):
        proc, reports, leaks = result
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("Traceback", proc.stdout + proc.stderr)
        self.assertTrue(reports, "structured STOP artifact is required")
        for report in reports:
            verdict = report.get("verdict", report.get("status",
                                  report.get("sizing", {}).get("verdict")))
            self.assertEqual(verdict, "STOP")
            if reason:
                actual = report.get("reason", report.get("sizing", {}).get("reason"))
                self.assertEqual(actual, reason)
        self.assertEqual(leaks, [], "STOP disclosed estimate fields or values")

    def test_small_complete_case_stop_has_no_estimates(self):
        rows = [self.row("complete-" + str(i), guard, i % 2)
                for i in range(2) for guard in GUARDS]
        self.assert_stop(self.run_fixture("two-complete-items", rows))

    def test_empty_input_is_structured_no_complete_cases_stop(self):
        self.assert_stop(self.run_fixture("empty", []), reason="no_complete_cases")

    def test_all_missing_is_structured_no_complete_cases_stop(self):
        rows = [self.row("all-missing", guard, None) for guard in GUARDS]
        self.assert_stop(self.run_fixture("all-missing", rows), reason="no_complete_cases")

    def test_partial_observations_zero_complete_cases_is_structured_stop(self):
        rows = [self.row("partial", guard, 1 if guard == "lg4" else None)
                for guard in GUARDS]
        self.assert_stop(self.run_fixture("partial-zero-complete", rows),
                         reason="no_complete_cases")

    def test_nonstop_wave_retains_unavailable_stratum_counts(self):
        rows = [self.row("complete-" + str(i), guard, (i >> j) & 1)
                for i in range(600) for j, guard in enumerate(GUARDS)]
        rows += [self.row("unavailable", guard, None, stratum="benign_eval")
                 for guard in GUARDS]
        proc, reports, _ = self.run_fixture("nonstop-with-unavailable-stratum", rows)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Traceback", proc.stdout + proc.stderr)
        self.assertEqual(reports[0]["sizing"]["shared_n"], 600)
        unavailable = next((row for row in reports[0]["strata"]
                            if row["stratum"] == "benign_eval"), None)
        self.assertIsNotNone(unavailable, "entirely missing strata must remain counted")
        self.assertEqual(unavailable["complete_case_n"], 0)
        self.assertEqual(unavailable["items_with_missing_cells"], 1)
        self.assertEqual(estimate_leaks(unavailable), [])


if __name__ == "__main__":
    unittest.main()
