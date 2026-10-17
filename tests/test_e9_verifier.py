#!/usr/bin/env python3
"""E9 numerical replay mutants; no test is a claim of external validity."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_e9", ROOT / "scripts/verify_e9.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class E9Verifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = verifier.load_inputs()
        e9 = ROOT / "experiments/e9"
        cls.before = {str(p.relative_to(e9)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in e9.rglob("*") if p.is_file()}
        # One real 2,000-bootstrap replay, shared by all validation mutants.
        cls.replay = verifier.replay_analyzer(e9)
        cls.after = {str(p.relative_to(e9)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in e9.rglob("*") if p.is_file()}

    def setUp(self):
        self.mutant = copy.deepcopy(self.data)

    def rejected(self, pattern):
        with self.assertRaisesRegex(verifier.Mismatch, pattern):
            verifier.verify(self.mutant, self.replay)

    def test_committed_result_replays_with_limits(self):
        report = verifier.verify(self.data, self.replay)
        self.assertEqual(report["rows"], 1000)
        self.assertEqual(report["miss_counts"], {"G1": 337, "G2": 787})
        self.assertEqual(report["both_miss_count"], 322)
        self.assertTrue(report["ci_excludes_zero"])
        self.assertFalse(report["ci_wholly_beyond_sesoi"])
        self.assertTrue(report["rule_omission_retained"])

    def test_replay_does_not_write_frozen_artifacts(self):
        self.assertEqual(self.before, self.after)

    def test_duplicate_measurement_item_is_rejected(self):
        self.mutant["rows"][1]["item_id"] = self.mutant["rows"][0]["item_id"]
        self.rejected("duplicate or invalid")

    def test_missing_guard_is_rejected(self):
        del self.mutant["rows"][0]["miss"]["G2"]
        self.rejected("miss must contain exactly both guards")

    def test_nonbinary_flag_is_rejected(self):
        self.mutant["rows"][0]["flag"]["G1"] = 2
        self.rejected("flag must be a binary integer")

    def test_boolean_is_not_accepted_as_an_integer_flag(self):
        self.mutant["rows"][0]["flag"]["G1"] = False
        self.rejected("flag must be a binary integer")

    def test_flag_and_miss_must_follow_frozen_threshold(self):
        row = self.mutant["rows"][0]
        row["flag"]["G1"], row["miss"]["G1"] = 1, 0
        self.rejected("does not follow frozen threshold")

    def test_score_tampering_fails_even_without_changing_any_count(self):
        self.mutant["rows"][0]["scores"]["G1"] += 1e-6
        self.rejected("committed score")

    def test_nonfinite_score_is_rejected(self):
        self.mutant["rows"][0]["scores"]["G1"] = float("nan")
        self.rejected("score must be finite")

    def test_measurement_ids_must_match_the_score_pool(self):
        self.mutant["rows"].pop()
        self.rejected("measurement IDs do not match")

    def test_registry_expected_numbers_cannot_drift(self):
        self.mutant["claim"]["expected"]["q_obs"] += 0.0001
        self.rejected("registry expected.q_obs")

    def test_registry_expected_interval_cannot_drift(self):
        self.mutant["claim"]["expected"]["delta_ci95"][0] = 0.051
        self.rejected("registry interval")

    def test_analyzer_interval_cannot_be_substituted(self):
        self.mutant["analysis"]["delta_ci95"][0] = 0.051
        self.rejected("full frozen analyzer replay.delta_ci95")

    def test_ci_excludes_zero_is_not_a_wholly_beyond_sesoi_claim(self):
        self.mutant["claim"]["expected"]["ci_wholly_beyond_sesoi"] = True
        self.rejected("interval wholly beyond SESOI")

    def test_measurement_threshold_must_equal_independent_calibration(self):
        self.mutant["result"]["thresholds"]["G1"] += 0.001
        self.rejected("measurement thresholds")

    def test_admission_threshold_mismatch_is_rejected(self):
        self.mutant["protocol"]["results"]["thresholds"]["G1"] += 0.001
        self.rejected("admission thresholds")

    def test_registry_threshold_mismatch_is_rejected(self):
        self.mutant["claim"]["expected"]["thresholds"]["G2"] += 0.001
        self.rejected("registry thresholds")

    def test_aggregate_result_cannot_override_rows(self):
        self.mutant["result"]["evaluation"]["all_miss"] += 1
        self.rejected("result evaluation.all_miss")

    def test_c1_omission_cannot_be_removed(self):
        self.mutant["claim"]["non_claims"] = [s for s in self.mutant["claim"]["non_claims"] if "C1" not in s]
        self.rejected("retain verdict-rule omission")

    def test_registration_cannot_claim_complete_preregistration_conformance(self):
        self.mutant["claim"]["proposition"] = self.mutant["claim"]["proposition"].replace(
            "does not certify complete", "certifies complete")
        self.rejected("must not certify complete")

    def test_prose_cannot_promote_zero_exclusion_to_wholly_beyond_sesoi(self):
        self.mutant["claim"]["proposition"] = self.mutant["claim"]["proposition"].replace(
            "does not lie wholly beyond", "lies wholly beyond")
        self.rejected("not wholly beyond SESOI")

    def test_partial_support_cannot_be_promoted_by_replay(self):
        self.mutant["claim"]["dimensions"]["evidential_status"] = "supported_within_scope"
        self.rejected("retain partial support")

    def test_frozen_analyzer_itself_refuses_moved_measurement_threshold(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "e9"
            for name in ("contract.json", "freeze/freeze.json", "freeze/protocol.json",
                         "results/result.json", "results/observations.jsonl", "run/analyze.py"):
                target = copied / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "experiments/e9" / name, target)
            path = copied / "results/result.json"
            result = json.loads(path.read_text())
            result["thresholds"]["G1"] += 0.001
            path.write_text(json.dumps(result))
            with self.assertRaisesRegex(verifier.Mismatch, "refused temporary replay"):
                verifier.replay_analyzer(copied)


if __name__ == "__main__":
    unittest.main()
