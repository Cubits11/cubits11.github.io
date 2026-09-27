"""Regression checks for rejection visibility, original-byte preservation and teaching counts."""
from pathlib import Path
import hashlib,json,subprocess,sys,unittest
import yaml
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import distribute
import claims_history as history

# Drive 09 requires a falsifier assessment for every governed correction. These two predate the assessment kind,
# and their transcription is the owner's decision (Drive 10, D4). The exemption can only shrink: its members are
# transition digests, each a transition recorded before the kind existed (entries[:50], which the kernel's
# append-only rule keeps fixed); it must equal exactly the governed legacy corrections still unassessed, so an
# appended assessment fails until its digest is deleted here, and a member cannot be deleted without one; an
# empty set fails, so the exemption is removed with its last member.
LEGACY_UNASSESSED=frozenset({
    '3405d1d9d4f086cf17ebc7a1217fc9e563448a65d50293641ca170b61fa59c23',  # E6-001 entries[48]
    '4a8f7a510eff285e97aa79495fe51982ce1c96074550723d8d9f2093375aeea5',  # E7B-001 entries[49]
})
LEGACY_END=50

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
    def test_disposition_follows_falsifier_only_when_it_fired(self):
        # A disposition must equal the predecessor falsifier's consequence only when an assessment says that
        # falsifier FIRED; NOT_FIRED asserts no relation. A governed correction with no assessment fails, except
        # for the members of LEGACY_UNASSESSED.
        hist=yaml.safe_load((ROOT/'claims_history.yaml').read_text())
        legacy={e['digest'] for e in hist['entries'][:LEGACY_END] if e.get('kind')=='transition'}
        known=history.commitments_by_digest(hist)
        unassessed=set()
        for row in json.loads((ROOT/'corrections/records/2026-09-10.json').read_text())['records']:
            t=[e for e in hist['entries'] if e.get('claim_id')==row['claim_id']][-1]
            pred=history.predecessor_commitment(t,known)
            self.assertIsNotNone(pred,row['claim_id'])
            rel=history.falsifier_relation(hist,t,pred)
            if rel=='FIRED':self.assertEqual(row['disposition'],pred['falsifier']['consequence'],row['claim_id'])
            elif rel=='UNASSESSED':
                self.assertIn(t['digest'],legacy,f"{row['claim_id']}: a governed correction needs a falsifier assessment")
                unassessed.add(t['digest'])
        self.assertEqual(set(LEGACY_UNASSESSED),unassessed,'the exemption lists exactly the legacy corrections still unassessed')
        self.assertTrue(LEGACY_UNASSESSED,'the exemption is empty: delete LEGACY_UNASSESSED, LEGACY_END and this check')
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
