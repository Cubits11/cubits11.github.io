#!/usr/bin/env python3
"""Attack fixtures and a real recovery drill on an isolated synthetic repository."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


guard = module('evidence_guard')
recovery = module('recovery_snapshot')


class Security(unittest.TestCase):
    def setUp(self):
        self.base = {'rows.json': b'original observation', 'checker.py': b'trusted checker',
                     'history.json': b'[1,2]', 'claims.yaml': b'genesis: original\nentries: [a, b]\n'}
        self.policy = {'immutable': {'rows.json': hashlib.sha256(self.base['rows.json']).hexdigest()},
                       'trust_root': ['checker.py'], 'append_only': [
                           {'path': 'history.json', 'format': 'json'},
                           {'path': 'claims.yaml', 'format': 'yaml', 'field': 'entries', 'fixed_fields': ['genesis']}]}

    def check(self, candidate):
        def read(name):
            if name not in candidate:
                raise FileNotFoundError(name)
            return candidate[name]
        return guard.compare(self.policy, self.base.__getitem__, read)

    def test_valid_append(self):
        c = dict(self.base, **{'history.json': b'[1,2,3]', 'claims.yaml': b'genesis: original\nentries: [a, b, c]\n'})
        self.assertEqual(self.check(c), [])

    def test_rewrite_and_recomputed_checker_still_fail(self):
        c = dict(self.base, **{'rows.json': b'invented observation', 'checker.py': b'print("PASS")'})
        failures = self.check(c)
        self.assertTrue(any('frozen evidence changed' in e for e in failures))
        self.assertTrue(any('trust-root change' in e for e in failures))

    def test_deletion_fails(self):
        c = dict(self.base); del c['rows.json']
        self.assertTrue(self.check(c))

    def test_truncation_reorder_and_rewrite_fail(self):
        for data in (b'[1]', b'[2,1]', b'[1,9]', b'null', b'{'):
            self.assertTrue(self.check(dict(self.base, **{'history.json': data})))

    def test_genesis_replacement_fails(self):
        c = dict(self.base, **{'claims.yaml': b'genesis: replacement\nentries: [a, b]\n'})
        self.assertTrue(any('anchor changed' in e for e in self.check(c)))

    def test_paths_cannot_escape(self):
        for path in ('../outside', '/tmp/outside', '.git/config', 'a/../b'):
            with self.assertRaises(ValueError): guard.safe(path)
            with self.assertRaises(ValueError): recovery.safe_path(path)

    def test_read_candidate_blobs_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.repo(root)
            (root / 'payload.py').write_text('raise RuntimeError("must never execute")')
            self.git(root, 'add', '.'); self.git(root, 'commit', '-qm', 'payload')
            ref = self.git(root, 'rev-parse', 'HEAD').decode().strip()
            self.assertIn(b'must never execute', guard.read(root, ref, 'payload.py'))
            with self.assertRaises(ValueError): guard.read(root, '--help', 'payload.py')

    @staticmethod
    def git(root, *args):
        return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.PIPE)

    def repo(self, root):
        self.git(root, 'init', '-q')
        self.git(root, 'config', 'user.email', 'fixture@example.invalid')
        self.git(root, 'config', 'user.name', 'Fixture')
        (root / 'file.txt').write_text('baseline\n')
        (root / 'deleted.txt').write_text('delete from workspace\n')
        self.git(root, 'add', '.'); self.git(root, 'commit', '-qm', 'baseline')

    def test_restore_uncommitted_staged_unstaged_and_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'source'; root.mkdir(); self.repo(root)
            (root / 'file.txt').write_text('staged\n'); self.git(root, 'add', 'file.txt')
            (root / 'file.txt').write_text('unstaged\n')
            (root / 'new.txt').write_text('not committed\n')
            (root / 'deleted.txt').unlink()
            destination = Path(td) / 'backup'
            digest = recovery.create(root, destination)
            self.assertEqual(recovery.verify(destination, digest)['status'], 'RESTORE_TEST_PASSED')
            self.assertEqual((root / 'file.txt').read_text(), 'unstaged\n')
            with self.assertRaises(ValueError): recovery.verify(destination, '0' * 64)
            with (destination / 'workspace.tar.gz').open('ab') as stream: stream.write(b'tamper')
            with self.assertRaises(ValueError): recovery.verify(destination, digest)

    def test_no_in_repository_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.repo(root)
            with self.assertRaises(ValueError): recovery.create(root, root / 'backup')

    def test_new_workflow_is_visible_to_trusted_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.repo(root)
            workflows = root / '.github/workflows'; workflows.mkdir(parents=True)
            (workflows / 'original.yml').write_text('trusted')
            self.git(root, 'add', '.'); self.git(root, 'commit', '-qm', 'workflow baseline')
            base = self.git(root, 'rev-parse', 'HEAD').decode().strip()
            (workflows / 'extra.yml').write_text('unreviewed workflow')
            self.git(root, 'add', '.'); self.git(root, 'commit', '-qm', 'workflow candidate')
            candidate = self.git(root, 'rev-parse', 'HEAD').decode().strip()
            self.assertNotEqual(guard.workflow_inventory(root, base), guard.workflow_inventory(root, candidate))


if __name__ == '__main__':
    unittest.main()
