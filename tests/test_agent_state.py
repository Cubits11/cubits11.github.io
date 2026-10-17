"""Adversarial local fixtures; no real remote, Drive writes, or publication."""
import copy
import contextlib
import io
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/agent_state.py'
spec = importlib.util.spec_from_file_location('agent_state', SCRIPT)
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
AT = dt.datetime(2026, 9, 26, 12, tzinfo=dt.timezone.utc)


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Fixture'); self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        (self.root / '.gitignore').write_text('_private/\n')
        (self.root / 'owner.txt').write_text('owner bytes')
        self.git('add', '.'); self.git('commit', '-qm', 'base')
        self.store = self.root / '_private/control'; self.store.mkdir(parents=True)
        self.cfg = {'version': 1, 'phase': 'repair', 'contamination': 'unknown',
                    'sealed_key_commitment': 'a' * 64,
                    'execution': dict(model='test', provider='fixture', harness='unittest', effort='test', execution_id='run-1'),
                    'roots': {}}
        for name in a.REQUIRED_ROOTS:
            data = {'fixture': name}
            if name == 'owner_decisions':
                data = {'decisions': [{'id': 'K7', 'status': 'open', 'source': 'fixture', 'alternatives': ['A', 'B']}]}
            if name == 'claim_registry':
                data = {'claims': [{'id': 'REL-001', 'last_reviewed': '2026-08-24', 'review_window_days': 30}]}
            if name == 'lease':
                data = {'issuer': 'fixture-owner', 'subject': 'run-1', 'capabilities': ['READ', 'TEST'],
                        'phase': 'repair', 'repository_head': self.git('rev-parse', 'HEAD'),
                        'not_before': '2026-09-26T00:00:00+00:00', 'expires_at': '2026-09-27T00:00:00+00:00'}
            self.bind(name, data)
        self.config = self.store / 'roots.json'; self.save()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def bind(self, name, data):
        p = self.store / (name + '.json'); p.write_text(json.dumps(data))
        self.cfg['roots'][name] = {'kind': 'local', 'path': str(p.relative_to(self.root)), 'sha256': a.file_hash(p)}

    def save(self): self.config.write_text(json.dumps(self.cfg))
    def capture(self): self.save(); return a.capture(self.root, self.config, AT)

    def test_valid_reconstruction_is_not_authorization_to_publish(self):
        c = self.capture(); self.assertEqual(c['state']['status'], 'RECONSTRUCTED')
        self.assertEqual(c['state']['known_blockers'][0]['kind'], 'review_due')
        self.assertFalse(c['state']['known_blockers'][0]['claim_refuted'])
        self.assertNotIn('PUBLISH', c['state']['capabilities'])
        self.assertEqual(c['state']['open_owner_decisions'][0]['status'], 'open')

    def test_timestamp_is_not_state_identity(self):
        c = self.capture(); later = a.capture(self.root, self.config, AT + dt.timedelta(seconds=1))
        self.assertEqual(c['state_id'], later['state_id']); self.assertNotEqual(c['observation'], later['observation'])

    def test_dirty_staged_and_untracked_bytes_are_preserved(self):
        (self.root / 'owner.txt').write_text('staged'); self.git('add', 'owner.txt')
        (self.root / 'owner.txt').write_text('unstaged')
        (self.root / 'draft\nname.txt').write_text('private draft')
        index = (self.root / '.git/index').read_bytes(); c = self.capture()
        self.assertEqual(index, (self.root / '.git/index').read_bytes())
        self.assertEqual((self.root / 'owner.txt').read_text(), 'unstaged')
        self.assertEqual(len(c['state']['repository']['dirty']), 2)
        self.assertTrue(all(x['provenance'] == 'unattributed_preserve' for x in c['state']['repository']['dirty']))

    def test_same_path_different_bytes_changes_identity(self):
        (self.root / 'owner.txt').write_text('one'); first = self.capture()
        (self.root / 'owner.txt').write_text('two'); self.assertNotEqual(first['state_id'], self.capture()['state_id'])

    def test_detached_head_is_explicit(self):
        self.git('checkout', '--detach', '-q'); self.assertIsNone(self.capture()['state']['repository']['branch'])

    def test_missing_required_inventory_cannot_pass(self):
        del self.cfg['roots']['control_plane']; self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_missing_root_cannot_pass(self):
        (self.store / 'control_plane.json').unlink(); self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_modified_root_cannot_pass(self):
        (self.store / 'control_plane.json').write_text('{}'); self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_symlink_cannot_bind_secret_outside_repo(self):
        p = self.store / 'control_plane.json'; p.unlink(); p.symlink_to('/etc/hosts')
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_traversal_is_refused(self):
        self.cfg['roots']['control_plane']['path'] = '../secret'; self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_unknown_executor_stops_entry(self):
        self.cfg['execution']['model'] = 'unknown'; self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_blind_claim_is_refused_before_git_access(self):
        self.cfg['phase'] = 'blind'; self.save()
        with patch.object(a, 'snapshot_repository', side_effect=AssertionError('must not read repo')):
            with self.assertRaisesRegex(a.Refusal, 'isolated'): a.capture(self.root, self.config, AT)

    def test_sealed_location_is_refused(self):
        self.cfg['sealed_key_path'] = 'secret'; self.assertRaises(a.Refusal, self.capture)

    def test_unexposed_claim_is_refused(self):
        self.cfg['contamination'] = 'unexposed'; self.assertRaises(a.Refusal, self.capture)

    def lease(self): return a.read_json(self.store / 'lease.json')

    def test_self_escalation_to_publication_is_refused(self):
        lease = self.lease(); lease['capabilities'].append('PUBLISH'); self.bind('lease', lease)
        c = self.capture(); self.assertEqual(c['state']['status'], 'BLOCKED'); self.assertEqual(c['state']['capabilities'], [])

    def test_expired_lease_is_refused(self):
        lease = self.lease(); lease['expires_at'] = '2026-09-25T00:00:00Z'; self.bind('lease', lease)
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_wrong_executor_is_refused(self):
        lease = self.lease(); lease['subject'] = 'other'; self.bind('lease', lease)
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_wrong_phase_is_refused(self):
        lease = self.lease(); lease['phase'] = 'revealed'; self.bind('lease', lease)
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_wrong_head_is_refused(self):
        lease = self.lease(); lease['repository_head'] = '0' * 40; self.bind('lease', lease)
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def external(self):
        value = {'provider': 'google_drive', 'object_id': 'document-1', 'revision_before': 'rev-1',
                 'revision_after': 'rev-1', 'observed_at': AT.isoformat(), 'coverage': ['body'], 'payload': {'text': 'source'}}
        value['payload_sha256'] = a.digest(value['payload']); return value

    def bind_external(self, value):
        self.bind('control_plane', value)
        self.cfg['roots']['control_plane'].update(kind='external_snapshot', object_id='document-1', coverage=['body'])

    def test_complete_observation_is_not_live_guarantee(self):
        self.bind_external(self.external()); c = self.capture()
        self.assertEqual(c['state']['status'], 'RECONSTRUCTED')
        self.assertFalse(c['state']['control_roots']['control_plane']['live_state_guaranteed'])

    def test_revision_race_is_refused(self):
        e = self.external(); e['revision_after'] = 'rev-2'; self.bind_external(e)
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_external_payload_tampering_is_refused(self):
        e = self.external(); e['payload']['text'] = 'tampered'; self.bind_external(e)
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_stale_and_future_external_observations_refuse(self):
        for days in [-2, 2]:
            e = self.external(); e['observed_at'] = (AT + dt.timedelta(days=days)).isoformat(); self.bind_external(e)
            self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_partial_sheet_is_not_complete(self):
        e = self.external(); self.bind_external(e); self.cfg['roots']['control_plane']['sheet'] = True
        self.assertEqual(self.capture()['state']['status'], 'BLOCKED')

    def test_concurrent_edit_is_refused(self):
        original = a.snapshot_repository; calls = 0
        def racing(root):
            nonlocal calls
            calls += 1
            if calls == 2: (root / 'owner.txt').write_text('concurrent')
            return original(root)
        with patch.object(a, 'snapshot_repository', side_effect=racing):
            self.assertRaisesRegex(a.Refusal, 'changed during capture', self.capture)

    def test_capsule_tampering_refuses(self):
        c = self.capture(); c['state']['capabilities'].append('PUBLISH')
        self.assertRaises(a.Refusal, a.verify_capsule, c)

    def test_duplicate_json_keys_refuse(self):
        self.config.write_text('{"version":1,"version":2}'); self.assertRaises(a.Refusal, a.read_json, self.config)

    def test_lock_is_not_stolen(self):
        with a.locked(self.store):
            with self.assertRaises(a.Refusal):
                with a.locked(self.store): pass

    def test_immutable_snapshot_and_atomic_pointer(self):
        c = self.capture(); a.publish_capsule(self.store, c)
        pointer = a.read_json(self.store / 'current.json')
        self.assertEqual(a.read_json(self.store / pointer['json'])['state_id'], c['state_id'])
        a.publish_capsule(self.store, c)
        self.assertEqual(len(list((self.store / 'states').iterdir())), 1)

    def test_chain_tampering_and_external_truncation_anchor(self):
        one = a.append_event(self.store, {'type': 'test'})
        two = a.append_event(self.store, {'type': 'test2'})
        self.assertEqual(len(a.history(self.store, two)), 2)
        (self.store / 'events/00000001.json').unlink()
        self.assertRaises(a.Refusal, a.history, self.store, two)
        p = self.store / 'events/00000000.json'; v = a.read_json(p); v['type'] = 'tampered'; p.write_text(json.dumps(v))
        self.assertRaises(a.Refusal, a.history, self.store)

    def test_blocked_state_never_selects_action(self):
        del self.cfg['roots']['lease']; self.assertIsNone(a.plan(self.capture())['selected'])

    def call(self, *args):
        self.save()
        with patch.object(a, 'now', return_value=AT), contextlib.redirect_stdout(io.StringIO()) as output:
            status = a.main(['--repo', str(self.root), *args])
        return status, output.getvalue().strip()

    def test_begin_refuses_stale_state(self):
        old = self.capture()['state_id']
        (self.root / 'owner.txt').write_text('changed')
        with self.assertRaisesRegex(a.Refusal, 'compare-and-swap'):
            self.call('begin', '--expected-state', old, '--action', 'scratch_negative_controls')

    def test_transition_is_intent_and_finish_is_not_acceptance(self):
        c = self.capture()
        status, token = self.call('begin', '--expected-state', c['state_id'], '--action', 'scratch_negative_controls')
        self.assertEqual(status, 0)
        self.assertEqual(a.history(self.store)[0]['disposition'], 'intent_only_no_dispatch')
        next_state = self.capture()['state_id']
        with self.assertRaisesRegex(a.Refusal, 'another transition'):
            self.call('begin', '--expected-state', next_state, '--action', 'scratch_negative_controls')
        evidence = self.store / 'test-evidence.json'; evidence.write_text('{"evidence_level":"clean_rerun","outcome":"pass"}')
        self.call('finish', '--token', token, '--evidence', str(evidence))
        self.assertFalse((self.store / 'active.json').exists())
        self.assertEqual(a.history(self.store)[-1]['disposition'], 'recorded_not_accepted')
        self.assertEqual(self.call('check')[0], 0)

    def test_finish_rejects_foreign_token_and_independent_claim(self):
        c = self.capture(); _, token = self.call('begin', '--expected-state', c['state_id'], '--action', 'resolve_roots')
        evidence = self.store / 'test-evidence.json'; evidence.write_text('{"evidence_level":"independently_reproduced"}')
        with self.assertRaisesRegex(a.Refusal, 'token mismatch'):
            self.call('finish', '--token', 'foreign', '--evidence', str(evidence))
        with self.assertRaisesRegex(a.Refusal, 'independent reproduction'):
            self.call('finish', '--token', token, '--evidence', str(evidence))
        self.assertTrue((self.store / 'active.json').exists())

    def test_failed_capture_invalidates_current_pointer(self):
        self.call('capture')
        self.cfg['phase'] = 'blind'
        with self.assertRaises(a.Refusal): self.call('capture')
        self.assertEqual(a.read_json(self.store / 'current.json')['status'], 'BLOCKED')

    def test_snapshot_half_write_is_refused(self):
        c = self.capture(); target = self.store / 'states' / c['state_id']; target.mkdir(parents=True)
        (target / 'state.json').write_text(json.dumps(c))
        self.assertRaises(a.Refusal, a.publish_capsule, self.store, c)

    def test_receipt_layers_separate_three_changes(self):
        r = dict(film='film', format='master', inputs={'registry': 'a'}, outputs={'master_sha256': 'v'},
                 frames_digest='f', runtime={'browser': '154'}, rendered_from_head='head', rendered_on='date',
                 render_seconds=1, facts_used=['x'], determinism={'identical': True}, text_overflows=[])
        base = a.receipt_layers(r)
        r['render_seconds'] = 2; timed = a.receipt_layers(r)
        self.assertEqual(base['artifact_id'], timed['artifact_id']); self.assertEqual(base['governance_id'], timed['governance_id'])
        self.assertNotEqual(base['execution_fingerprint'], timed['execution_fingerprint'])
        r['inputs']['registry'] = 'b'; governed = a.receipt_layers(r)
        self.assertEqual(timed['artifact_id'], governed['artifact_id']); self.assertNotEqual(timed['governance_id'], governed['governance_id'])
        r['outputs']['master_sha256'] = 'new'; self.assertNotEqual(governed['artifact_id'], a.receipt_layers(r)['artifact_id'])
        self.assertEqual(a.receipt_layers(r)['legacy'], r)


if __name__ == '__main__': unittest.main()
