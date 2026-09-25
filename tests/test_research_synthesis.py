#!/usr/bin/env python3
"""RESEARCH.md quotes numbers; each one must be the number its source holds.

The synthesis is prose, so nothing regenerates it. What keeps it honest is
that every figure it states is recomputed here from the registry, the census
claim's expected values, or a frozen experiment's result file, and must appear
in the text exactly as the source gives it. A quoted number with no source, or
a source that moved, fails.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEXT = (ROOT / "RESEARCH.md").read_text(encoding="utf-8")


def claim(cid: str) -> dict:
    registry = yaml.safe_load((ROOT / "claims.yaml").read_text(encoding="utf-8"))
    return next(c for c in registry["claims"] if c["id"] == cid)


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class ResearchSynthesis(unittest.TestCase):
    def assertQuoted(self, literal: str, source: str) -> None:
        self.assertIn(literal, TEXT, f"RESEARCH.md does not quote {literal!r} from {source}")

    def test_identification(self):
        e = claim("CC-004")["expected"]
        a, b = e["marginals"]
        self.assertEqual(e["interval"], [max(0.0, a + b - 1), min(a, b)])
        self.assertQuoted(f"each miss {a:.0%}", "CC-004 marginals")
        self.assertQuoted(f"[{e['interval'][0]}, {e['interval'][1]:.2f}]", "CC-004 interval")
        self.assertQuoted(f"gives {a * b:.0%}", "the independence product of CC-004's marginals")

    def test_census(self):
        e = claim("MC-001")["expected"]
        self.assertQuoted(f"Of {e['n_examined']} evaluations", "MC-001 n_examined")
        self.assertQuoted(f"examined, {e['m_shared_basis']} establish", "MC-001 m_shared_basis")
        self.assertQuoted(f"and {e['k_present']}\npreserve", "MC-001 k_present")
        s = e["m_strata"]
        self.assertQuoted(f"{s['shared_basis']}/{s['threshold_not_contradicted']}/"
                          f"{s['threshold_documented_full_exposure']}", "MC-001 ladder")

    def test_released_verdicts(self):
        e = claim("MC-002")["expected"]
        n = e["n_harmful"]
        misses = [n - c for c in e["per_guard_catches"].values()]
        lo, hi = max(0, sum(misses) - (len(misses) - 1) * n) / n, min(misses) / n
        self.assertQuoted(f"{e['all_miss']} of {n} harmful", "MC-002 all_miss / n_harmful")
        self.assertQuoted(f"[{lo:.2%}, {hi:.2%}]", "MC-002 marginal-only bounds")

    def test_lineage_widths(self):
        for exp, rel in (("E3", "experiments/e3/results/e3_result.json"),
                         ("E3B", "experiments/e3b/results/e3_result.json")):
            lo, hi = load(rel)["harmful"]["frechet"]
            width = round(hi - lo, 4)
            self.assertQuoted(f"| {exp} |", exp)
            self.assertQuoted(f"width {width:g}", f"{exp} Fréchet width")
        scouting = load("experiments/e8/freeze/scouting.json")["results"]["candidates"]
        floor = load("experiments/e8/contract.json")["inference"]["informativeness"]["marginal_only_width_min"]
        widest = max(c["width_float"] for c in scouting)
        self.assertTrue(all(not c["eligible"] for c in scouting))
        self.assertQuoted(f"widest {widest:g} against {floor:g}", "E8 scouting widths and floor")

    def test_e9(self):
        a = load("experiments/e9/results/analysis.json")
        admitted = load("experiments/e9/freeze/protocol.json")["results"]["candidates"]
        sesoi = load("experiments/e9/contract.json")["inference"]["decision"]["SESOI"]
        lo, hi = a["delta_ci95"]
        for literal, what in (
                (f"{a['n']:,} measurement items", "n"),
                (f"both miss at a rate of {a['q_obs']:.4f}", "q_obs"),
                (f"is {a['q_ind']:.4f}", "q_ind"),
                (f"discrepancy is {a['delta']:+.4f}", "delta"),
                (f"[{lo:+.4f}, {hi:+.4f}]", "95% interval"),
                (f"[{a['frechet'][0]:.4f}, {a['frechet'][1]:.4f}]", "Fréchet interval"),
                (f"verdict is {a['verdict'].split(':')[0]}", "verdict"),
                (f"below the {sesoi}", "SESOI")):
            self.assertQuoted(literal, f"E9 {what}")
        # The sentence about the SESOI is only true while the interval straddles it.
        self.assertTrue(lo < sesoi <= a["delta"])
        clears = sum(1 for c in admitted if c["width_clears_floor"])
        chosen = sum(1 for c in admitted if c["admitted"])
        words = {1: "One", 2: "Two", 3: "three"}
        self.assertQuoted(f"{words[clears]} of {words[len(admitted)]} pools cleared the floor", "E9 admission")
        self.assertEqual(chosen, 1)

    def test_no_unbound_percentages(self):
        """Every percentage in the text is one of the figures asserted above."""
        level = load("experiments/e9/freeze/freeze.json")["bootstrap"]["interval"]
        self.assertIn("95%", level, "E9's frozen bootstrap interval is not a 95% interval")
        allowed = {"10%", "1%", "0.00%", "14.63%", "95%"}
        found = set(re.findall(r"\d+(?:\.\d+)?%", TEXT))
        self.assertLessEqual(found, allowed, f"unbound percentage(s): {sorted(found - allowed)}")


if __name__ == "__main__":
    unittest.main()
