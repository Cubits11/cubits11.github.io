"""Regression checks for rejection visibility, original-byte preservation and teaching counts."""
from pathlib import Path
import hashlib,json,subprocess,sys,unittest
import yaml
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import distribute

class Corrections(unittest.TestCase):
    def test_frozen_bytes_are_unchanged(self):
        m=json.loads((ROOT/'corrections/records/2026-09-10-preserved-inputs.json').read_text())
        for p,want in m['sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),want,p)
    def test_old_report_bodies_are_retained(self):
        m=json.loads((ROOT/'corrections/records/2026-09-10-preserved-inputs.json').read_text())
        for e in ('e6','e7b'):
            p=f'experiments/{e}/RESULT.md'
            old=subprocess.check_output(['git','show',m['baseline_commit']+':'+p],cwd=ROOT).decode()
            current=(ROOT/p).read_text()
            self.assertTrue(current.startswith('> **Correction recorded'))
            self.assertTrue(current.endswith(old))
    def test_dispositions_and_history_agree(self):
        reg={c['id']:c for c in yaml.safe_load((ROOT/'claims.yaml').read_text())['claims']}
        hist=yaml.safe_load((ROOT/'claims_history.yaml').read_text())['entries']
        for row in json.loads((ROOT/'corrections/records/2026-09-10.json').read_text())['records']:
            c=reg[row['claim_id']]
            self.assertEqual(row['disposition'],'REJECT')
            self.assertEqual(c['dimensions']['evidential_status'],'contradicted')
            self.assertTrue(c['proposition'].startswith('REJECTED AS STATED'))
            self.assertEqual(c['falsifier']['consequence'],'REJECT')
            last=[e for e in hist if e.get('claim_id')==c['id']][-1]
            self.assertEqual(last['transition_type'],'CORRECT')
    def test_audit_demonstrates_both_failures(self):
        audit=json.loads((ROOT/'distribution/research-2026-09-10/audit-results.json').read_text())
        self.assertNotEqual(audit['e6']['counterexample_resulting_weights'],audit['e6']['specified_weights'])
        self.assertEqual(audit['e6']['valid_constructions'],16)
        self.assertEqual(audit['e7b']['changed_thresholds'],1)
    def test_notice_precedes_evidence_links(self):
        page=(ROOT/'overlap/index.html').read_text()
        self.assertLess(page.index('Correction status'),page.index('href="/ledger/'))
        self.assertIn('Constructed example',page)
        self.assertIn('either-check-catches',page)
        self.assertIn('Pairwise tables also do not generally determine',page)
        ledger=(ROOT/'ledger/index.html').read_text()
        self.assertLess(ledger.index('Current correction status'),ledger.index('<article class="claim"'))
    def test_all_constructed_tables_preserve_both_marginals(self):
        js="const assert=require('assert');const {counts}=require('./overlap/example.js');for(let q=0;q<=10;q++){let c=counts(q);assert.equal(c.bothMiss+c.aOnly,10);assert.equal(c.bothMiss+c.bOnly,10);assert.equal(Object.values(c).reduce((a,b)=>a+b),100);assert(Object.values(c).every(x=>x>=0));}for(let q of [-1,11,.5,NaN])assert.throws(()=>counts(q),RangeError);"
        subprocess.run(['node','-e',js],cwd=ROOT,check=True)
    def test_off_window_snapshots_are_retained_but_not_compared(self):
        pub={'post_id':'999','published_at':'2026-09-01T00:00:00Z',**{d:'fixture' for d in distribute.DIMS}}
        row={'post_id':'999','observed_at':'2026-09-03T23:00:00Z','scope':'total','provider':'fixture','source':'https://example.org/analytics','metrics':{'impressions':15,'link_clicks':None}}
        report=distribute.learn([pub],[row])
        self.assertEqual(report['snapshot_count'],1)
        self.assertEqual(report['comparisons'],[])
        self.assertEqual(row['observed_at'],'2026-09-03T23:00:00Z')

if __name__=='__main__':unittest.main()
