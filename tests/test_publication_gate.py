"""Synthetic publication records exercise the hold; they are not reader evidence."""
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
            'limit':gate.HUMAN_LIMIT}
        patch=(ROOT/self.ready['title']['patch']).read_bytes()
        (self.root/'publication').mkdir()
        (self.root/self.ready['title']['patch']).write_bytes(patch)
        self.ready['title']['patch_sha256']=gate.sha(self.root/self.ready['title']['patch'])
        for name,content in {
            'assets/site.css':"body{font:16px sans-serif} @font-face{src:url('fonts/test.woff2')}",
            'assets/site.js':'/* synthetic fixture */','assets/fonts/test.woff2':'synthetic font fixture',
            'index.html':'<link rel="stylesheet" href="/assets/site.css"><script src="/assets/site.js"></script><p>Synthetic homepage fixture</p>',
            'try/index.html':'<link rel="stylesheet" href="/assets/site.css"><p>Synthetic proof fixture</p>',
            'films/lib/film.js':'/* synthetic runtime */','films/lib/tokens.css':'/* synthetic tokens */',
            'films/data/facts.json':'{"synthetic":true}',
        }.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
        slugs=list(gate.read(ROOT/'films/curation.json')['films'])
        write(self.root/'films/curation.json',{'films':{s:{'phone_composition':True} for s in slugs}})
        for slug in slugs:
            folder=self.root/'films'/slug;folder.mkdir()
            (folder/'manifest.yaml').write_text('render:\n  formats: [vertical]\n')
            (folder/'film.html').write_text('<p>Synthetic film source fixture</p>')
            (folder/'index.html').write_text(f'<link rel="stylesheet" href="/assets/site.css"><video poster="/films/{slug}/renders/{slug}__master.poster.png" data-phone-poster="/films/{slug}/renders/{slug}__vertical.poster.png"><source src="/films/{slug}/renders/{slug}__vertical.mp4"><source src="/films/{slug}/renders/{slug}__master.mp4"></video>')
            video=folder/'renders'/f'{slug}__vertical.mp4';video.parent.mkdir();video.write_bytes(b'synthetic unit-test byte fixture, not a rendered film')
            for suffix in ('master.mp4','master.poster.png','vertical.poster.png'):
                (folder/'renders'/f'{slug}__{suffix}').write_bytes(b'synthetic visible asset fixture')
            receipt={'film':slug,'format':'vertical','width':1080,'height':1920,
                'phone_text':{'media_width_css_px':280,'minimum_css_px':14,'minimum_canvas_px':54,'audited_draws':10},
                'determinism':{'identical':True},'text_overflows':[],
                'capture':{'pixel_equivalent':True,'pixel_equivalence_samples':5},
                'inputs':{name:gate.sha(folder/name if name=='film.html' else self.root/name) for name in gate.REQUIRED_INPUTS},
                'outputs':{'master':str(video.relative_to(folder)),'master_sha256':gate.sha(video)}}
            write(folder/'renders'/f'{slug}__vertical.receipt.json',receipt)
        self.save_ready()
        readers={'schema_version':1,'protocol_sha256':None,'artifact_sha256':{},
                 'facilitator':{'id':None,'attests_humans':False,'attests_unfamiliar':False,'attests_distinct':False,'recorded_on':None},
                 'rater':{'id':None,'criteria':{}},'participants':[]}
        write(self.root/'publication/readers.json',readers)
        gate.bind(self.root)
        self.ready=gate.read(self.root/'publication/readiness.json')
        self.readers=gate.template(self.root)
        self.readers['facilitator']={'id':'SYNTHETIC-FACILITATOR','attests_humans':True,'attests_unfamiliar':True,'attests_distinct':True,'recorded_on':'2026-10-17'}
        self.readers['rater']['id']='SYNTHETIC-RATER'
        for reader in self.readers['participants']:
            reader.update(kind='human',unfamiliar=True,recorded_at='2026-10-17T12:00:00-04:00')
            reader['homepage']={'elapsed_seconds':20,'subject_answer':'Synthetic raw answer: AI guardrail scores and overlapping failures.','contact_answer':'Synthetic raw answer: displayed email link.','subject_pass':True,'contact_pass':True,'rater_notes':'Synthetic fixture matched the pre-recorded criteria.'}
            reader['film']={'slug':gate.FILM,'watched_full':True,'explanation':'Synthetic answer: most evaluations, 14 of 20, do not record what happened to both guards on the same item.','one_sentence':True,'pass':True,'rater_notes':'Synthetic fixture matched the pre-recorded criteria.','elapsed_seconds':90}
            reader['proof']={'activation_count':1,'method':'keyboard','destination':'/try/','pass':True,'observation':'Synthetic observation: activated the below-player link once and reached /try/.','rater_notes':'Synthetic fixture matched the pre-recorded criteria.'}
        self.save_readers()

    def save_ready(self): write(self.root/'publication/readiness.json',self.ready)
    def save_readers(self): write(self.root/'publication/readers.json',self.readers)
    def check(self): return gate.evaluate(self.root)
    def blocked(self,phrase):
        report=self.check();self.assertEqual(report['status'],'BLOCKED');self.assertTrue(any(phrase in b for b in report['blockers']),report)

    def test_complete_synthetic_records_can_satisfy_record_gate(self):
        report=self.check();self.assertEqual(report['status'],'READY',report)
        self.assertEqual(report['reader_successes'],{'homepage_joint':5,'film_missing_column':5,'proof_activation':5})
        self.assertIn('not independently verified by automation',report['human_evidence_limit'])

    def test_four_of_five_passes_each_task(self):
        reader=self.readers['participants'][0]
        reader['homepage']['subject_pass']=False;reader['film']['pass']=False;reader['proof']['pass']=False
        self.save_readers();self.assertEqual(self.check()['status'],'READY')

    def test_missing_readers_blocks_and_cli_exits_two(self):
        self.readers['participants']=[];self.save_readers();self.blocked('five actual unfamiliar-reader')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code=gate.main(['--root',str(self.root)])
        self.assertEqual(code,2);self.assertIn('BLOCKED',output.getvalue())

    def test_homepage_requires_joint_success_not_separate_four_of_fives(self):
        self.readers['participants'][0]['homepage']['subject_pass']=False
        self.readers['participants'][1]['homepage']['contact_pass']=False
        self.save_readers();self.blocked('gate failed')

    def test_two_homepage_timeouts_fail_even_with_correct_answers(self):
        for reader in self.readers['participants'][:2]:reader['homepage']['elapsed_seconds']=20.01
        self.save_readers();self.blocked('gate failed')

    def test_film_explanation_has_no_invented_twenty_second_cutoff(self):
        for reader in self.readers['participants']:reader['film']['elapsed_seconds']=1000
        self.save_readers();self.assertEqual(self.check()['status'],'READY')

    def test_failed_explanations_block(self):
        for reader in self.readers['participants'][:2]:reader['film']['pass']=False
        self.save_readers();self.blocked('gate failed')

    def test_multiple_sentence_answers_do_not_count_as_successes(self):
        for reader in self.readers['participants'][:2]:reader['film']['one_sentence']=False
        self.save_readers();self.blocked('gate failed')

    def test_one_incomplete_film_counts_as_a_failure_without_discarding_the_reader(self):
        self.readers['participants'][0]['film']['watched_full']=False
        self.readers['participants'][0]['film']['pass']=False
        self.save_readers();report=self.check();self.assertEqual(report['status'],'READY');self.assertEqual(report['reader_successes']['film_missing_column'],4)

    def test_one_observed_no_activation_is_preserved_as_a_failure(self):
        self.readers['participants'][0]['proof'].update(method='none',activation_count=0,destination='NOT_REACHED',**{'pass':False})
        self.save_readers();report=self.check();self.assertEqual(report['status'],'READY');self.assertEqual(report['reader_successes']['proof_activation'],4)

    def test_wrong_film_is_not_substituted(self):
        self.readers['participants'][0]['film']['slug']='the-missing-column-trailer'
        self.save_readers();self.blocked('full named film')

    def test_two_proof_activations_do_not_count_as_one(self):
        for reader in self.readers['participants'][:2]:reader['proof']['activation_count']=2
        self.save_readers();self.blocked('gate failed')

    def test_foreign_try_destination_does_not_count(self):
        for reader in self.readers['participants'][:2]:reader['proof']['destination']='https://example.com/try/'
        self.save_readers();self.blocked('gate failed')

    def test_agent_is_rejected_even_when_labeled_as_a_pass(self):
        self.readers['participants'][0]['kind']='agent';self.save_readers();self.blocked('agent, familiar or undated')

    def test_duplicate_reader_ids_are_rejected(self):
        self.readers['participants'][1]['id']=self.readers['participants'][0]['id'];self.save_readers();self.blocked('identifiers must be distinct')

    def test_familiar_reader_is_rejected(self):
        self.readers['participants'][0]['unfamiliar']=False;self.save_readers();self.blocked('agent, familiar or undated')

    def test_unknown_reader_schema_is_not_accepted(self):
        self.readers['schema_version']=99;self.save_readers();self.blocked('unsupported reader-evidence schema')

    def test_facilitator_attestation_is_required(self):
        self.readers['facilitator']['attests_humans']=False;self.save_readers();self.blocked('facilitator must attest')

    def test_raw_answers_cannot_be_replaced_by_grades(self):
        self.readers['participants'][0]['homepage']['subject_answer']='';self.save_readers();self.blocked('raw answers')

    def test_rater_criteria_cannot_drift(self):
        self.readers['rater']['criteria']['missing_column']='Any positive reaction passes.';self.save_readers();self.blocked('pre-recorded criteria')

    def test_tested_css_drift_requires_a_new_study(self):
        (self.root/'assets/site.css').write_text('body{font-size:4px}');self.blocked('tested artifacts are unbound or have changed')

    def test_tested_html_drift_requires_a_new_study(self):
        (self.root/'index.html').write_text('<p>Different visible homepage</p>');self.blocked('tested artifacts are unbound or have changed')

    def test_tested_video_drift_blocks_even_when_its_receipt_is_fresh(self):
        folder=self.root/'films'/gate.FILM
        video=folder/'renders'/f'{gate.FILM}__vertical.mp4';video.write_bytes(b'different visible film')
        path=folder/'renders'/f'{gate.FILM}__vertical.receipt.json';receipt=gate.read(path);receipt['outputs']['master_sha256']=gate.sha(video);write(path,receipt)
        self.blocked('tested artifacts are unbound or have changed')

    def test_phone_poster_drift_is_bound_even_when_selected_by_script(self):
        (self.root/'films'/gate.FILM/'renders'/f'{gate.FILM}__vertical.poster.png').write_bytes(b'different visible poster')
        self.blocked('tested artifacts are unbound or have changed')

    def test_receipt_and_manifest_bookkeeping_do_not_require_new_readers(self):
        folder=self.root/'films'/gate.FILM
        path=folder/'renders'/f'{gate.FILM}__vertical.receipt.json';receipt=gate.read(path);receipt['rendered_on']='2026-10-18';write(path,receipt)
        (folder/'manifest.yaml').write_text('render:\n  formats: [vertical]\n# Bookkeeping comment; visible film unchanged.\n')
        self.assertEqual(self.check()['status'],'READY')

    def test_fresh_source_binding_for_identical_visible_media_keeps_reader_binding(self):
        folder=self.root/'films'/gate.FILM
        (folder/'film.html').write_text('<p>Synthetic film source fixture</p><!-- harmless source comment -->')
        path=folder/'renders'/f'{gate.FILM}__vertical.receipt.json';receipt=gate.read(path);receipt['inputs']['film.html']=gate.sha(folder/'film.html');write(path,receipt)
        self.assertEqual(self.check()['status'],'READY')

    def test_protocol_drift_invalidates_existing_results(self):
        self.ready['protocol']['rater_criteria']['subject']='Any answer passes.';self.save_ready();self.blocked('protocol binding')

    def test_rebinding_collected_results_is_refused(self):
        with self.assertRaisesRegex(gate.Blocked,'cannot rebind an existing reader study'):gate.bind(self.root)

    def test_unconfirmed_protocol_blocks(self):
        self.ready['protocol']['status']='PENDING';self.save_ready();self.blocked('awaits confirmation')

    def test_local_title_preparation_does_not_claim_public_title_changed(self):
        self.ready['title']['public_application']['status']='public_not_updated';self.save_ready();self.blocked('public title application is still pending')

    def test_old_external_revision_cannot_support_renamed_public_title(self):
        self.ready['title']['public_application']['revision']=self.ready['title']['base_revision'];self.save_ready();self.blocked('new immutable external revision')

    def test_reviewable_title_patch_must_keep_its_hash(self):
        (self.root/self.ready['title']['patch']).write_text('placeholder');self.blocked('external title patch changed')

    def test_phone_composition_must_be_finished_for_all_twelve(self):
        path=self.root/'films/curation.json';data=gate.read(path);data['films'][gate.FILM]['phone_composition']=False;write(path,data);self.blocked('phone composition is unfinished')

    def test_phone_receipt_requires_actual_font_audit(self):
        path=self.root/'films'/gate.FILM/'renders'/f'{gate.FILM}__vertical.receipt.json';data=gate.read(path);data.pop('phone_text');write(path,data);self.blocked('14px text audit')

    def test_small_phone_type_is_rejected(self):
        path=self.root/'films'/gate.FILM/'renders'/f'{gate.FILM}__vertical.receipt.json';data=gate.read(path);data['phone_text'].update(minimum_css_px=13,minimum_canvas_px=13*1080/280);write(path,data);self.blocked('14px text audit')

    def test_phone_pixel_equivalence_is_required(self):
        path=self.root/'films'/gate.FILM/'renders'/f'{gate.FILM}__vertical.receipt.json';data=gate.read(path);data['capture']['pixel_equivalent']=False;write(path,data);self.blocked('five passing canvas/browser equivalence samples')

    def test_five_pixel_equivalence_samples_are_required(self):
        path=self.root/'films'/gate.FILM/'renders'/f'{gate.FILM}__vertical.receipt.json';data=gate.read(path);data['capture']['pixel_equivalence_samples']=4;write(path,data);self.blocked('five passing canvas/browser equivalence samples')

    def test_phone_source_drift_is_rejected(self):
        (self.root/'films'/gate.FILM/'film.html').write_text('changed source');self.blocked('stale phone receipt input')

    def test_phone_video_drift_is_rejected(self):
        (self.root/'films'/gate.FILM/'renders'/f'{gate.FILM}__vertical.mp4').write_bytes(b'changed');self.blocked('video bytes differ')

    def test_deployment_guard_precedes_pages_configuration_and_upload(self):
        workflow=(ROOT/'.github/workflows/verify.yml').read_text().split('\n  deploy:\n',1)[1].split('\n  deployed:\n',1)[0]
        gate_at=workflow.index('run: python scripts/publication_gate.py')
        self.assertLess(gate_at,workflow.index('name: Configure GitHub Pages'))
        self.assertLess(gate_at,workflow.index('name: Upload the verified static artifact'))
        self.assertIn('actions/setup-python@',workflow)


if __name__=='__main__':unittest.main()
