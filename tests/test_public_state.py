"""Deadline boundary cases and status failure paths; no scientific criteria change."""
from __future__ import annotations
import copy
import os
import datetime as dt
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import generate_public_state as public


class PublicStateTests(unittest.TestCase):
    def setUp(self):
        self.claims = {'claims':[{'id':'TEST-001','last_reviewed':'2024-01-31','review_window_days':30,
                                  'dimensions':{'evidential_status':'untested'}}]}
        self.publications = {'deadlines':[]}

    def test_review_date_is_calculated_not_retyped(self):
        item = public.records(self.claims, self.publications)[0]
        self.assertEqual(item['due'], '2024-03-01')
        self.claims['claims'][0]['last_reviewed'] = '2024-02-01'
        self.assertEqual(public.records(self.claims,self.publications)[0]['due'], '2024-03-02')

    def test_overdue_requests_review_without_promoting_or_refuting_claim(self):
        original = copy.deepcopy(self.claims)
        item = public.records(self.claims,self.publications)[0]
        self.assertEqual(public.label(item,dt.date(2024,2,29)),'SCHEDULED')
        self.assertEqual(public.label(item,dt.date(2024,3,1)),'DUE TODAY')
        self.assertEqual(public.label(item,dt.date(2024,3,2)),'OVERDUE — REVIEW REQUIRED')
        self.assertEqual(self.claims,original)
        self.assertEqual(item['evidential_status'],'untested')

    def test_elapsed_promise_needs_disposition_or_overdue(self):
        item={'kind':'publication-promise','due':'2026-09-23'}
        self.assertEqual(public.label(item,dt.date(2026,10,17)),'OVERDUE')
        item['disposition']={'date':'2026-10-17'}
        self.assertEqual(public.label(item,dt.date(2026,10,16)),'OVERDUE')
        self.assertEqual(public.label(item,dt.date(2026,10,17)),'DISPOSITION RECORDED')

    def test_duplicate_deadline_ids_are_rejected(self):
        self.claims['claims'].append(copy.deepcopy(self.claims['claims'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            public.records(self.claims,self.publications)

    def test_renewal_keeps_the_previous_registry_deadline_visible(self):
        previous = {'TEST-001':self.claims['claims'][0]}
        renewed = copy.deepcopy(previous)
        renewed['TEST-001']['last_reviewed'] = '2024-03-10'
        self.publications['review_dispositions'] = [{'claim_id':'TEST-001',
            'before_revision':'a'*40,'after_revision':'b'*40,'summary':'Review renewed; study untested.'}]
        with patch.object(public,'registry_at',side_effect=[previous,renewed]):
            old = next(item for item in public.records(self.claims,self.publications) if '@' in item['id'])
        self.assertEqual(old['due'],'2024-03-01')
        self.assertEqual(public.label(old,dt.date(2024,3,9)),'OVERDUE — REVIEW REQUIRED')
        self.assertEqual(public.label(old,dt.date(2024,3,10)),'DISPOSITION RECORDED')

    def test_a_disposition_cannot_link_to_an_absent_result(self):
        self.publications['deadlines']=[{'id':'bad','title':'Missing','due':'2026-09-23',
            'source':'/now/','disposition':{'date':'2026-10-17','url':'/this-result-does-not-exist/'}}]
        with self.assertRaisesRegex(ValueError,'target does not exist'):
            public.records(self.claims,self.publications)

    def test_draft_result_must_link_its_exact_revision(self):
        draft={'revision':'a'*40,'result_url':'https://github.com/Cubits11/cubits11.github.io/blob/main/RESULT.md'}
        with self.assertRaisesRegex(ValueError,'not pinned'):
            public.draft_board([draft],'2026-10-17')

    def test_browser_status_failure_paths(self):
        subprocess.run([os.environ.get('CUBITS11_NODE', 'node'),'--test','tests/check-status.test.cjs'],cwd=public.ROOT,check=True)


if __name__ == '__main__':
    unittest.main()
