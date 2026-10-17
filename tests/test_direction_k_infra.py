"""K-INFRA fires on calendar weeks, not row counts.

The defect these pin: k_infra stepped back seven *rows*, so nine daily
snapshots over eight days reported "two consecutive weeks" and fired. A week
here is seven elapsed days: boundaries are walked back one week at a time from
the newest snapshot, each measured from the boundary before it, so a gap pushes
the chain further back instead of collapsing a window.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("direction", ROOT / "scripts" / "direction.py")
direction = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(direction)


def series(days, *, evidence_moves_on=(), start=date(2026, 9, 1)):
    """One row per offset in `days`; scaffold rises daily, evidence only where told."""
    rows = []
    for i in days:
        row = {"date": (start + timedelta(days=i)).isoformat()}
        for f in direction.EVIDENCE:
            row[f] = 1 + sum(1 for m in evidence_moves_on if i >= m)
        for f in direction.SCAFFOLD:
            row[f] = 10 + i
        rows.append(row)
    return rows


class KInfraWeeks(unittest.TestCase):
    def run_on(self, rows):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "repo_state.jsonl"
            p.write_text("".join(json.dumps(r) + "\n" for r in rows))
            original, direction.SERIES = direction.SERIES, p
            try:
                return direction.k_infra()
            finally:
                direction.SERIES = original

    def test_seven_days_cannot_fire(self):
        r = self.run_on(series(range(8)))
        self.assertFalse(r["computable"])
        self.assertFalse(r.get("fired", False))

    def test_eight_days_cannot_fire(self):
        """The historical defect: nine rows over eight days used to fire."""
        r = self.run_on(series(range(9)))
        self.assertFalse(r["computable"])
        self.assertFalse(r.get("fired", False))

    def test_thirteen_days_cannot_fire(self):
        r = self.run_on(series(range(14)))
        self.assertFalse(r["computable"])
        self.assertFalse(r.get("fired", False))

    def test_fourteen_days_scaffold_only_fires(self):
        r = self.run_on(series(range(15)))
        self.assertTrue(r["computable"], r.get("why"))
        self.assertTrue(r["fired"])
        self.assertEqual(r["windows"], 2)
        self.assertEqual(r["span"], "2026-09-01 to 2026-09-15")

    def test_evidence_movement_in_either_window_does_not_fire(self):
        for moved in (3, 11):
            with self.subTest(day=moved):
                r = self.run_on(series(range(15), evidence_moves_on=(moved,)))
                self.assertTrue(r["computable"], r.get("why"))
                self.assertFalse(r["fired"])

    def test_gap_shifts_boundary_back_and_still_fires(self):
        """A missed day must not shorten a window: the chain walks back."""
        days = [i for i in range(20) if i != 12]
        r = self.run_on(series(days))
        self.assertTrue(r["computable"], r.get("why"))
        self.assertTrue(r["fired"])
        first, last = (date.fromisoformat(x) for x in r["span"].split(" to "))
        self.assertGreaterEqual((last - first).days, 14)

    def test_gap_without_enough_history_waits(self):
        """Rather than shorten a window, an unbacked gap is not computable."""
        r = self.run_on(series([i for i in range(15) if i != 7]))
        self.assertFalse(r["computable"])
        self.assertIn("no snapshot on or before", r["why"])

    def test_sparse_endpoints_only_still_fire(self):
        r = self.run_on(series([0, 7, 14]))
        self.assertTrue(r["computable"], r.get("why"))
        self.assertTrue(r["fired"])

    def test_year_boundary(self):
        rows = series(range(15), start=date(2026, 12, 24))
        r = self.run_on(rows)
        self.assertTrue(r["computable"], r.get("why"))
        self.assertTrue(r["fired"])
        self.assertEqual(r["span"], "2026-12-24 to 2027-01-07")

    def test_iso_week_52_to_1(self):
        r = self.run_on(series(range(15), start=date(2026, 12, 21)))
        self.assertTrue(r["computable"], r.get("why"))
        self.assertTrue(r["fired"])

    def test_iso_week_53_to_1(self):
        # 2020 has ISO week 53; the rule counts days, so the crossing is a non-event.
        r = self.run_on(series(range(15), start=date(2020, 12, 21)))
        self.assertTrue(r["computable"], r.get("why"))
        self.assertTrue(r["fired"])

    def test_dst_transition_is_not_an_hour_problem(self):
        # US DST ends 2026-11-01; dates are calendar dates, so 14 days stay 14 days.
        r = self.run_on(series(range(15), start=date(2026, 10, 25)))
        self.assertTrue(r["computable"], r.get("why"))
        self.assertEqual(r["span"], "2026-10-25 to 2026-11-08")

    def test_unordered_or_duplicate_dates_are_not_computable(self):
        rows = series(range(15))
        rows[5], rows[6] = rows[6], rows[5]
        self.assertFalse(self.run_on(rows)["computable"])
        dup = series(range(15))
        dup[6]["date"] = dup[5]["date"]
        self.assertFalse(self.run_on(dup)["computable"])

    def test_missing_counter_is_not_computable(self):
        rows = series(range(15))
        del rows[0][direction.EVIDENCE[0]]
        r = self.run_on(rows)
        self.assertFalse(r["computable"])
        self.assertIn("counter", r["why"])

    def test_invalid_date_is_not_computable(self):
        rows = series(range(15))
        rows[2]["date"] = "not-a-date"
        self.assertFalse(self.run_on(rows)["computable"])

    def test_empty_series_is_not_computable(self):
        self.assertFalse(self.run_on([])["computable"])

    def test_weeks_must_be_positive(self):
        with self.assertRaises(ValueError):
            direction.k_infra(0)

    def test_live_series_is_evaluated_not_asserted(self):
        """Whatever the real series says, it must not claim a window under 7 days."""
        r = direction.k_infra()
        if r["computable"]:
            first, last = (date.fromisoformat(x) for x in r["span"].split(" to "))
            self.assertGreaterEqual((last - first).days, 14)


if __name__ == "__main__":
    unittest.main(verbosity=2)
