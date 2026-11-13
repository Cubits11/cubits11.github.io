"""Synthetic publication records exercise the title and phone-film checks.

The five-reader requirement was retired by owner decision on 2026-11-13; one
case below holds that the gate no longer reads reader records.
"""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publication_gate',ROOT/'scripts/publication_gate.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
FILM='the-missing-column-census'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


class PublicationGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.ready=copy.deepcopy(gate.read(ROOT/'publication/readiness.json'))
        self.ready['title']['public_application']={
            'status':'owner_verified_published','revision':'b'*40,
            'source_url':'https://github.com/Cubits11/ghost-visualizer/commit/'+'b'*40,
            'verified_title':gate.TITLE,'verified_h1':gate.TITLE,
            'verified_source_sha256':{k:self.ready['title']['source_sha256'][k]
                                      for k in ('index.html','src/components/CinematicShell.tsx')},
            'verified_by':'SYNTHETIC TEST FIXTURE','verified_on':'2026-10-17',
            'limit':'Synthetic fixture; not an owner attestation.'}
        patch=(ROOT/self.ready['title']['patch']).read_bytes()
        (self.root/'publication').mkdir()
        (self.root/self.ready['title']['patch']).write_bytes(patch)
        self.ready['title']['patch_sha256']=gate.sha(self.root/self.ready['title']['patch'])
        for name,content in {
            'films/lib/film.js':'/* synthetic runtime */','films/lib/tokens.css':'/* synthetic tokens */',
            'films/data/facts.json':json.dumps({'facts':{'SYNTHETIC.read':{'value':[14,20]},'SYNTHETIC.unread':{'value':5}}}),
        }.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
        slugs=list(gate.read(ROOT/'films/curation.json')['films'])
        self.assertIn(FILM,slugs)
        write(self.root/'films/curation.json',{'films':{s:{'phone_composition':True} for s in slugs}})
        for slug in slugs:
            folder=self.root/'films'/slug;folder.mkdir()
            (folder/'manifest.yaml').write_text('render:\n  formats: [vertical]\n')
            (folder/'film.html').write_text('<p>Synthetic film source fixture</p>')
            video=folder/'renders'/f'{slug}__vertical.mp4';video.parent.mkdir();video.write_bytes(b'synthetic unit-test byte fixture, not a rendered film')
            receipt={'film':slug,'format':'vertical','width':1080,'height':1920,
                'phone_text':{'media_width_css_px':280,'minimum_css_px':14,'minimum_canvas_px':54,'audited_draws':10},
                'determinism':{'identical':True},'text_overflows':[],
                'capture':{'pixel_equivalent':True,'pixel_equivalence_samples':5},
                'inputs':{name:gate.sha(folder/name if name=='film.html' else self.root/name) for name in gate.REQUIRED_INPUTS},
                'facts_used':['SYNTHETIC.read'],
                'facts_subset':gate.facts_digest.binding(gate.read(self.root/'films/data/facts.json')['facts'],['SYNTHETIC.read']),
                'outputs':{'master':str(video.relative_to(folder)),'master_sha256':gate.sha(video)}}
            write(folder/'renders'/f'{slug}__vertical.receipt.json',receipt)
        self.save_ready()

    def save_ready(self): write(self.root/'publication/readiness.json',self.ready)
    def check(self): return gate.evaluate(self.root)
    def blocked(self,phrase):
        report=self.check();self.assertEqual(report['status'],'BLOCKED');self.assertTrue(any(phrase in b for b in report['blockers']),report)

    def test_complete_synthetic_records_satisfy_the_gate(self):
        report=self.check();self.assertEqual(report['status'],'READY',report);self.assertEqual(report['blockers'],[])

    def test_reader_records_are_not_required(self):
        self.assertFalse((self.root/'publication/readers.json').exists())
        self.assertEqual(self.ready['reader_test']['status'],'retired')
        self.assertEqual(self.check()['status'],'READY')

    def test_blocked_gate_exits_two(self):
        path=self.root/'films/curation.json';data=gate.read(path);data['films'][FILM]['phone_composition']=False;write(path,data)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code=gate.main(['--root',str(self.root)])
        self.assertEqual(code,2);self.assertIn('BLOCKED',output.getvalue())

    def test_local_title_preparation_does_not_claim_public_title_changed(self):
        self.ready['title']['public_application']['status']='public_not_updated';self.save_ready();self.blocked('public title application is still pending')

    def test_old_external_revision_cannot_support_renamed_public_title(self):
        self.ready['title']['public_application']['revision']=self.ready['title']['base_revision'];self.save_ready();self.blocked('new immutable external revision')

    def test_reviewable_title_patch_must_keep_its_hash(self):
        (self.root/self.ready['title']['patch']).write_text('placeholder');self.blocked('external title patch changed')

    def test_phone_composition_must_be_finished_for_all_twelve(self):
        path=self.root/'films/curation.json';data=gate.read(path);data['films'][FILM]['phone_composition']=False;write(path,data);self.blocked('phone composition is unfinished')

    def test_phone_receipt_requires_actual_font_audit(self):
        path=self.root/'films'/FILM/'renders'/f'{FILM}__vertical.receipt.json';data=gate.read(path);data.pop('phone_text');write(path,data);self.blocked('14px text audit')

    def test_small_phone_type_is_rejected(self):
        path=self.root/'films'/FILM/'renders'/f'{FILM}__vertical.receipt.json';data=gate.read(path);data['phone_text'].update(minimum_css_px=13,minimum_canvas_px=13*1080/280);write(path,data);self.blocked('14px text audit')

    def test_phone_pixel_equivalence_is_required(self):
        path=self.root/'films'/FILM/'renders'/f'{FILM}__vertical.receipt.json';data=gate.read(path);data['capture']['pixel_equivalent']=False;write(path,data);self.blocked('five passing canvas/browser equivalence samples')

    def test_five_pixel_equivalence_samples_are_required(self):
        path=self.root/'films'/FILM/'renders'/f'{FILM}__vertical.receipt.json';data=gate.read(path);data['capture']['pixel_equivalence_samples']=4;write(path,data);self.blocked('five passing canvas/browser equivalence samples')

    def test_phone_source_drift_is_rejected(self):
        (self.root/'films'/FILM/'film.html').write_text('changed source');self.blocked('stale phone receipt input')

    def set_fact(self,fid,value):
        path=self.root/'films/data/facts.json';doc=gate.read(path);doc['facts'][fid]['value']=value;write(path,doc)

    def test_a_fact_the_phone_cut_read_cannot_change(self):
        self.set_fact('SYNTHETIC.read',[13,20]);self.blocked('phone receipt facts binding')

    def test_a_fact_the_phone_cut_never_read_does_not_stale_it(self):
        self.set_fact('SYNTHETIC.unread',6);self.assertEqual(self.check()['status'],'READY')

    def test_whole_file_facts_receipt_is_refused(self):
        path=self.root/'films'/FILM/'renders'/f'{FILM}__vertical.receipt.json';data=gate.read(path)
        data.pop('facts_subset');data['inputs']['films/data/facts.json']=gate.sha(self.root/'films/data/facts.json');write(path,data)
        self.blocked('input bindings are incomplete')

    def test_phone_video_drift_is_rejected(self):
        (self.root/'films'/FILM/'renders'/f'{FILM}__vertical.mp4').write_bytes(b'changed');self.blocked('video bytes differ')

    def test_deployment_guard_precedes_pages_configuration_and_upload(self):
        workflow=(ROOT/'.github/workflows/verify.yml').read_text().split('\n  deploy:\n',1)[1].split('\n  deployed:\n',1)[0]
        gate_at=workflow.index('run: python scripts/publication_gate.py')
        self.assertLess(gate_at,workflow.index('name: Configure GitHub Pages'))
        self.assertLess(gate_at,workflow.index('name: Upload the verified static artifact'))
        self.assertIn('actions/setup-python@',workflow)


if __name__=='__main__':unittest.main()
