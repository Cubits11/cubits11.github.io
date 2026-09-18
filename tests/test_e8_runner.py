#!/usr/bin/env python3
"""E8's runner consumes the contract: a changed contract changes what it selects.

Synthetic scores under constructed contracts only. No frozen experiment is
replayed here, and no row this file writes is an observation of anything.
"""
import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "experiments/e8/run/runner.py"
FIXTURES = ROOT / "research/contracts/fixtures"

spec = importlib.util.spec_from_file_location("runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

# Twenty benign calibration scores per guard and ten harmful evaluation items.
# At a 5% budget one false positive is allowed, so the lowest feasible 'ge'
# threshold is the second-highest benign score for each guard.
BENIGN_G1 = [i / 100 for i in range(1, 21)]            # 0.01 .. 0.20
BENIGN_G2 = [0.5 + i / 100 for i in range(1, 21)]      # 0.51 .. 0.70
HARMFUL = {f"h{i}": {"G1": g1, "G2": g2} for i, (g1, g2) in enumerate([
    (0.30, 0.90), (0.30, 0.90), (0.30, 0.55), (0.05, 0.90), (0.05, 0.55),
    (0.05, 0.55), (0.19, 0.69), (0.20, 0.70), (0.21, 0.71), (0.00, 0.00)])}


def scores():
    return {"guards": ["G1", "G2"],
            "pools": {"per_judge_benign": {f"b{i}": {"G1": a, "G2": b} for i, (a, b) in enumerate(zip(BENIGN_G1, BENIGN_G2))},
                      "pair_shared_harmful": copy.deepcopy(HARMFUL)}}


def frozen():
    return json.loads((FIXTURES / "valid-frozen-inference.json").read_text())


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, contract, sc=None, require_frozen=True):
        cpath, spath = self.dir / "contract.json", self.dir / "scores.json"
        cpath.write_text(json.dumps(contract))
        spath.write_text(json.dumps(sc or scores()))
        return runner.run(cpath, spath, self.dir / "out", require_frozen=require_frozen)

    def test_frozen_contract_selects_lowest_feasible_ge_threshold(self):
        result = self._run(frozen())
        self.assertEqual(result["thresholds"], {"G1": 0.20, "G2": 0.70})
        ev = result["evaluation"]
        self.assertEqual(ev["miss_counts"], {"G1": 5, "G2": 5})
        self.assertEqual(ev["all_miss"], 4)
        self.assertEqual(ev["band_counts"], [0, 5])
        self.assertEqual(ev["cells_derived_from_rows"], {"00": 4, "01": 1, "10": 1, "11": 4})
        rows = [json.loads(l) for l in (self.dir / "out/observations.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["scores"], HARMFUL["h0"])
        self.assertEqual(result["provenance"]["contract_status"], "frozen")

    def test_budget_in_the_contract_moves_the_threshold(self):
        c = frozen()
        c["operating_point"]["fpr_budget"] = 0.10
        result = self._run(c)
        self.assertEqual(result["thresholds"], {"G1": 0.19, "G2": 0.69})
        self.assertEqual(result["evaluation"]["miss_counts"], {"G1": 4, "G2": 4})

    def test_comparator_in_the_contract_flips_the_selection(self):
        c = frozen()
        c["operating_point"]["comparator"] = "le"
        c["operating_point"]["direction"] = "highest"
        sc = scores()
        for pool in sc["pools"].values():
            for v in pool.values():
                v["G1"], v["G2"] = 1 - v["G1"], 1 - v["G2"]
        result = self._run(c, sc)
        self.assertAlmostEqual(result["thresholds"]["G1"], 0.80, places=12)
        self.assertAlmostEqual(result["thresholds"]["G2"], 0.30, places=12)
        self.assertEqual(result["evaluation"]["all_miss"], 4)

    def test_historical_threshold_direction_defect_is_refused_before_execution(self):
        c = frozen()
        c["operating_point"]["direction"] = "highest"   # E7's defect under a 'ge' comparator
        with self.assertRaises(runner.Refusal) as ctx:
            self._run(c)
        self.assertIn("validate_contract.py", str(ctx.exception))

    def test_unfrozen_contract_produces_no_rows(self):
        c = json.loads((FIXTURES / "valid-guard-selection.json").read_text())
        with self.assertRaises(runner.Refusal) as ctx:
            self._run(c)
        self.assertIn("frozen", str(ctx.exception))
        self.assertFalse((self.dir / "out").exists())

    def test_pool_named_by_the_contract_must_exist_in_the_scores(self):
        sc = scores()
        sc["pools"]["harmful_from_somewhere_else"] = sc["pools"].pop("pair_shared_harmful")
        with self.assertRaises(runner.Refusal) as ctx:
            self._run(frozen(), sc)
        self.assertIn("pair_shared_harmful", str(ctx.exception))

    def test_no_feasible_candidate_excludes_the_judge_and_refuses_a_pair(self):
        c = frozen()
        sc = scores()
        # A constant benign score leaves one candidate, which flags every benign item.
        for v in sc["pools"]["per_judge_benign"].values():
            v["G2"] = 0.6
        with self.assertRaises(runner.Refusal) as ctx:
            self._run(c, sc)
        self.assertIn("excluded ['G2']", str(ctx.exception))

    def test_realized_width_below_the_declared_floor_is_identification_limited(self):
        # Five of ten missed by each guard: lo = 0, hi = 5, marginal-only width 1/2.
        c = frozen()
        c["inference"]["informativeness"] = {"marginal_only_width_min": 0.6,
                                             "consequence_when_below": "IDENTIFICATION-LIMITED"}
        c["inference"]["decision"]["SESOI"] = 0.6      # the floor may not sit below the SESOI
        c["inference"]["decision"]["equivalence_margin"] = 0.6
        ident = self._run(c)["identification"]
        self.assertEqual(ident["marginal_only_width"], "1/2")
        self.assertEqual(ident["status"], "IDENTIFICATION-LIMITED")
        self.assertFalse(ident["delta_claimable"])
        self.assertEqual(ident["delta_all_miss"], "3/20")   # 4/10 - (5/10)(5/10), recorded, not claimed
        c["inference"]["informativeness"]["marginal_only_width_min"] = 0.5   # the boundary is admitted
        c["inference"]["decision"]["SESOI"] = 0.5
        c["inference"]["decision"]["equivalence_margin"] = 0.5
        ident = self._run(c)["identification"]
        self.assertEqual(ident["status"], "INFORMATIVE")
        self.assertTrue(ident["delta_claimable"])

    def test_a_contract_without_a_floor_gets_no_verdict(self):
        ident = self._run(frozen())["identification"]
        self.assertEqual(ident["status"], "NOT-DECLARED")
        self.assertFalse(ident["delta_claimable"])
        self.assertIsNone(ident["floor"])

    def test_runner_source_holds_no_claim_critical_literal(self):
        src = RUNNER.read_text()
        self.assertIsNone(re.search(r"[=(]\s*['\"](lowest|highest)['\"]", src), "a direction literal")
        self.assertNotIn("0.05", src, "a budget literal")
        self.assertIsNone(re.search(r"width_min\W*[=:]\s*[0-9]", src), "a floor literal")
        self.assertIsNone(re.search(r"comparator\W+=\W+['\"](ge|le)['\"]", src), "a comparator literal")


if __name__ == "__main__":
    unittest.main()
