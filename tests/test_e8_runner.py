#!/usr/bin/env python3
"""E8's runner consumes the contract: a changed contract changes what it selects.

Synthetic scores under constructed contracts only. No frozen experiment is
replayed here, and no row this file writes is an observation of anything.

E9 is E8 with one variable changed, the calibration population. Its checks live
in this file so that E9 adds no row to the verification manifest, which is a
trust-root file whose every change is a separately reviewed migration.
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


class Preregistration(unittest.TestCase):
    def test_prereg_renders_its_sources(self):
        # Correction C1: PREREG.md is a rendering of the contract, the scouting record and the
        # freeze. A hand edit to the prose that is not an edit to its source is drift.
        spec = importlib.util.spec_from_file_location("render_prereg", ROOT / "experiments/e8/run/render_prereg.py")
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)
        prereg = ROOT / "experiments/e8/PREREG.md"
        if not prereg.exists():
            self.skipTest("E8 has no PREREG.md yet")
        self.assertEqual(prereg.read_text(), render.render())


E9 = ROOT / "experiments/e9"


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _code(path):
    """The source after the module docstring."""
    return path.read_text().split('"""', 2)[2]


class E9Contract(unittest.TestCase):
    def test_only_id_and_status_differ_from_e8(self):
        e8 = json.loads((ROOT / "experiments/e8/contract.json").read_text())
        e9 = json.loads((E9 / "contract.json").read_text())
        self.assertEqual({k for k in set(e8) | set(e9) if e8.get(k) != e9.get(k)}, {"id", "status"})
        self.assertEqual(e9["status"], "frozen")

    def test_frozen_inputs_match_the_freeze_record(self):
        if not (E9 / "freeze/freeze.json").exists():
            self.skipTest("E9 has no freeze.json yet")
        self.assertEqual(_module("e9_freeze", E9 / "run/freeze.py").check(), [])

    def test_partitions_are_disjoint_and_new(self):
        draw = _module("e9_draw", E9 / "run/draw.py")
        names = sorted(p.stem for p in (E9 / "freeze").glob("items_*.csv"))
        if not names:
            self.skipTest("E9 has drawn nothing yet")
        sets = {n: draw.read_items(n) for n in names}
        prior = draw.prior_hashes(draw.plan())
        for i, a in enumerate(names):
            self.assertFalse(sets[a] & prior, f"{a} reuses an item a prior freeze holds")
            for b in names[i + 1:]:
                self.assertFalse(sets[a] & sets[b], f"{a} and {b} share items")


class E9Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.runner = _module("e9_runner", E9 / "run/runner.py")

    def tearDown(self):
        self.tmp.cleanup()

    def test_logic_is_e8s_with_e9s_identity(self):
        self.assertEqual(_code(E9 / "run/runner.py").replace("E9", "E8").replace("e9", "e8"), _code(RUNNER))

    def test_rows_carry_e9s_identity(self):
        cpath, spath = self.dir / "contract.json", self.dir / "scores.json"
        cpath.write_text(json.dumps(frozen()))
        spath.write_text(json.dumps(scores()))
        result = self.runner.run(cpath, spath, self.dir / "out")
        rows = [json.loads(l) for l in (self.dir / "out/observations.jsonl").read_text().splitlines()]
        self.assertEqual({r["experiment"] for r in rows}, {"E9"})
        self.assertEqual(result["experiment"], "E9")
        self.assertEqual(result["thresholds"], {"G1": 0.20, "G2": 0.70})


class E9Preregistration(unittest.TestCase):
    def test_prereg_renders_its_sources(self):
        prereg = E9 / "PREREG.md"
        if not prereg.exists():
            self.skipTest("E9 has no PREREG.md yet")
        self.assertEqual(prereg.read_text(), _module("e9_render", E9 / "run/render_prereg.py").render())

    def test_result_renders_its_sources(self):
        render = _module("e9_render_result", E9 / "run/render_prereg.py").render_result()
        result = E9 / "RESULT.md"
        if render is None:
            self.assertFalse(result.exists(), "RESULT.md exists but E9 has no analysis to render")
            return
        self.assertEqual(result.read_text(), render)

    def test_prereg_holds_no_outcome(self):
        """PREREG.md is a pre-result object: no admission or measurement section, ever."""
        text = (E9 / "PREREG.md").read_text()
        for heading in ("## Admission result", "## Measurement result", "# E9 — result"):
            self.assertNotIn(heading, text)


if __name__ == "__main__":
    unittest.main()
