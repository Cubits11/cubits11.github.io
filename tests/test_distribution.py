#!/usr/bin/env python3
"""Adversarial checks using synthetic fixtures; no fixture enters live ledgers."""
import copy
import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import distribute as d

class DistributionTests(unittest.TestCase):
    def pub(self, ident='1', day=1):
        return {'post_id': ident, 'published_at': f'2026-09-{day:02}T12:00:00Z',
                **{k: 'fixture' for k in d.DIMS}}

    def metric(self, ident='1', day=2, clicks=10):
        return {'post_id': ident, 'observed_at': f'2026-09-{day:02}T12:00:00Z',
                'provider': 'fixture', 'scope': 'organic', 'source': 'https://example.org/fixture',
                'metrics': {'impressions': 100, 'link_clicks': clicks}}

    def test_unknown_and_zero_denominator(self):
        self.assertTrue(all(v is None for v in d.rates({}).values()))
        self.assertIsNone(d.rates({'impressions': 0, 'link_clicks': 0})['ctr'])
        self.assertEqual(d.rates({'impressions': 100, 'link_clicks': 0})['ctr'], 0)

    def test_no_summing_cumulative_snapshots(self):
        a = self.metric()
        b = copy.deepcopy(a); b['observed_at'] = '2026-09-02T13:00:00Z'
        report = d.learn([self.pub()], [a, b])
        self.assertEqual(len(report['comparisons']), 1)
        self.assertEqual(report['comparisons'][0]['rates']['ctr']['value'], .1)

    def test_delta_excludes_current_and_other_cohorts(self):
        report = d.learn([self.pub(), self.pub('2', 3)], [self.metric(), self.metric('2', 4, 20)])
        rate = report['comparisons'][1]['rates']['ctr']
        self.assertEqual(rate['baseline_n'], 1)
        self.assertAlmostEqual(rate['delta_percentage_points'], 10)
        other = self.pub('2', 3); other['audience'] = 'different'
        report = d.learn([self.pub(), other], [self.metric(), self.metric('2', 4)])
        self.assertEqual(report['comparisons'][1]['rates']['ctr']['baseline_n'], 0)

    def test_duplicate_negative_and_unknown_post_refuse(self):
        a = self.metric()
        with self.assertRaises(ValueError): d.validate_metrics([a, a], [self.pub()])
        a['metrics']['impressions'] = -1
        with self.assertRaises(ValueError): d.validate_metrics([a], [self.pub()])
        with self.assertRaises(ValueError): d.validate_metrics([self.metric()], [])

    def test_aggregate_attribution_refuses(self):
        a = self.metric(); a['metrics']['site_visits'] = 4
        with self.assertRaises(ValueError): d.validate_metrics([a], [self.pub()])

    def test_future_and_naive_dates_refuse(self):
        with self.assertRaises(ValueError): d.validate_metrics([self.metric(day=1)], [self.pub(day=3)])
        with self.assertRaises(ValueError): d.stamp('2026-09-01')

    def test_generated_claim_mutation_refuses(self):
        posts = d.draft(); posts[0]['posts'][0] = 'Proves every guardrail is safe.'
        with self.assertRaises(ValueError): d.verify(posts)

    def test_rejected_claim_stays_blocked_in_preview(self):
        from unittest.mock import patch
        original_read = d.read
        def rejected(path):
            doc = original_read(path)
            if path == 'claims.yaml':
                next(c for c in doc['claims'] if c['id'] == 'CC-001')['dimensions']['evidential_status'] = 'contradicted'
            return doc
        with patch.object(d, 'read', side_effect=rejected):
            with self.assertRaisesRegex(ValueError, 'Claim held: CC-001'):
                d.verify(d.draft(), allow_pending=True)

    def test_pending_preview_cannot_be_approved_or_dispatched(self):
        from unittest.mock import patch
        posts = d.draft()
        pending = copy.deepcopy(posts)
        pending[0]['sources'][0].update(commit=None, url=None, binding='pending_commit')
        with patch.object(d, 'draft', return_value=pending):
            self.assertTrue(d.verify(pending, allow_pending=True))
            with self.assertRaisesRegex(ValueError, 'awaits commit'):
                d.verify(pending)
            with self.assertRaisesRegex(ValueError, 'awaits commit'):
                d.approve(pending[0]['id'], 'fixture: no authorization')
            with self.assertRaisesRegex(ValueError, 'awaits commit'):
                d.dispatch_preconditions(pending[0], dry_run=True)

    def test_real_drafts_preserve_limits_and_hold(self):
        posts = d.draft(); self.assertTrue(d.verify(posts, allow_pending=True))
        for post in posts:
            self.assertEqual(post['state'], 'held_owner_review')
            self.assertIsNone(post['scheduled_at'])
            self.assertTrue(post['evidence_urls'])

if __name__ == '__main__': unittest.main()
