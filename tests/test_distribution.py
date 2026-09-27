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

    def test_observed_text_undoes_what_x_does_to_a_post(self):
        # X rewrites links to t.co, escapes &, and keeps a long post's full text in note_tweet.
        # A digest of the raw stored text would call every such post altered.
        sent = 'Same scores https://cubits11.github.io/overlap/ & limits.'
        link = {'url': 'https://t.co/abc123', 'expanded_url': 'https://cubits11.github.io/overlap/'}
        stored = {'text': 'Same scores https://t.co/abc123 &amp; limits.', 'entities': {'urls': [link]}}
        self.assertNotEqual(stored['text'], sent)
        self.assertEqual(d.observed_text(stored), d.canonical(sent))
        long_post = {'text': 'Same scores https://t.co/abc123…',
                     'note_tweet': {'text': stored['text'], 'entities': {'urls': [link]}}}
        self.assertEqual(d.observed_text(long_post), d.canonical(sent))
        self.assertNotEqual(d.observed_text({'text': 'Same scores, a different claim.'}), d.canonical(sent))

    # ── publish: identity, approval signature, read-back, partial threads ──────
    POST = {'id': 'fx-thread', 'revision': 'f' * 64, 'post_type': 'thread', 'audience_hypothesis': 'fixture',
            'topic': 'fixture', 'hook': 'fixture', 'visual': 'none', 'cta': 'fixture', 'thread_structure': 'fixture',
            'posts': ['Same scores https://cubits11.github.io/overlap/ & limits.', 'Reproduce it, then read the limits.']}
    OWNER = {'id': '1000000001', 'username': 'PranavBhave_'}
    WHO = {'username': 'PranavBhave_', 'account_id': '1000000001'}

    def fake_x(self, me, fail_on=None, stored=None):
        state = {'sent': [], 'posts': []}
        def x_request(method, path, creds, body=None, query=None):
            if (method, path) == ('GET', '/users/me'):
                return {'data': dict(me)}
            if (method, path) == ('POST', '/tweets'):
                n = len(state['sent']) + 1
                if n == fail_on:
                    raise ValueError('X API 503 on POST /tweets: fixture')
                state['sent'].append(body)
                text = (stored or {}).get(n, body['text'])
                ident = str(3 * 10**18 + n)
                state['posts'].append({'id': ident, 'author_id': me['id'], 'entities': {'urls': []},
                                       'text': text.replace('&', '&amp;')})
                return {'data': {'id': ident}}
            if (method, path) == ('GET', '/tweets'):
                return {'data': [p for p in state['posts'] if p['id'] in query['ids'].split(',')]}
            raise AssertionError((method, path))
        return x_request, state

    def publish(self, x_request, *, signature='valid', keys=None, git_state=None, approved=True):
        import contextlib, json, tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            base = pathlib.Path(tmp)
            (base / 'principal.json').write_text(json.dumps(self.WHO))
            row = {'draft_id': self.POST['id'], 'draft_revision': self.POST['revision'], 'basis': 'fixture',
                   'approved_at': '2026-09-27T00:00:00Z', 'posts_sha256': d.digest(self.POST['posts'])}
            if signature:
                row['signature'] = signature
            (base / 'approvals.json').write_text(json.dumps([row] if approved else []))
            repo = {'rev-parse': 'a' * 40, 'status': '', 'branch': 'origin/x', **(git_state or {})}
            for target, kw in (('BASE', {'new': base}), ('draft', {'return_value': [copy.deepcopy(self.POST)]}),
                               ('verify', {'return_value': True}), ('x_request', {'new': x_request}),
                               ('credentials', {'return_value': ('k', 'ks', 't', 'ts')}),
                               ('git', {'side_effect': lambda *a: repo[a[0]]}),
                               ('verify_approval', {'return_value': None}) if signature == 'valid' else
                               ('owner_signing_keys', keys if isinstance(keys, dict) else {'return_value': keys})):
                stack.enter_context(patch.object(d, target, **kw))
            outcome = None
            try:
                d.publish(self.POST['id'])
            except ValueError as e:
                outcome = str(e)
            receipts = json.loads((base / 'publications.json').read_text()) if (base / 'publications.json').exists() else []
            again = None
            if receipts:
                try:
                    d.dispatch_preconditions(copy.deepcopy(self.POST))
                except ValueError as e:
                    again = str(e)
            return outcome, receipts, again

    def test_dispatch_refuses_without_an_approval_or_a_clean_pushed_tree(self):
        for label, git_state, approved, refusal in (
                ('dirty tree', {'status': '?? scripts/json.py'}, True, 'clean tree'),
                ('HEAD not on a remote', {'branch': ''}, True, 'push before publishing'),
                ('no approval row', {}, False, 'No approval recorded')):
            with self.subTest(label):
                x, state = self.fake_x(self.OWNER)
                outcome, receipts, _ = self.publish(x, git_state=git_state, approved=approved)
                self.assertIn(refusal, outcome or '')
                self.assertEqual((state['sent'], receipts), ([], []))

    def test_publish_refuses_credentials_that_act_as_another_account(self):
        x, state = self.fake_x({'id': '2000000002', 'username': 'someone_else'})
        outcome, receipts, _ = self.publish(x)
        self.assertIn('not the recorded principal @PranavBhave_', outcome or '')
        self.assertEqual((state['sent'], receipts), ([], []))

    def test_readback_matches_what_was_approved_and_flags_what_was_not(self):
        x, _ = self.fake_x(self.OWNER)
        _, [ok], _ = self.publish(x)
        self.assertTrue(ok['readback_ok'])
        x, _ = self.fake_x(self.OWNER, stored={2: 'Reproduce it, and trust the result.'})
        _, [changed], _ = self.publish(x)
        self.assertFalse(changed['readback_ok'])
        self.assertEqual([c['equal'] for c in changed['readback']], [True, False])

    def test_partial_thread_is_recorded_and_blocks_redispatch(self):
        x, state = self.fake_x(self.OWNER, fail_on=2)
        outcome, [row], again = self.publish(x)
        self.assertIn('fixture', outcome)
        self.assertEqual((row['status'], len(row['thread_post_ids']), len(state['sent'])), ('PARTIAL', 1, 1))
        self.assertIn('partially published', again)

    @unittest.skipUnless(__import__('shutil').which('ssh-keygen'), 'ssh-keygen is needed to sign and verify approvals')
    def test_only_an_owner_signature_admits_a_dispatch(self):
        import subprocess, tempfile
        tmp = pathlib.Path(tempfile.mkdtemp())
        def key(name):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(tmp / name)], check=True)
            return tmp / name
        def sign(k, post=None, who=None):
            # ssh-keygen keeps an existing .sig and still exits 0, so remove it first.
            f, sig = tmp / 'payload', tmp / 'payload.sig'
            f.write_bytes(d.approval_payload(post or self.POST, who or self.WHO))
            sig.unlink(missing_ok=True)
            subprocess.run(['ssh-keygen', '-q', '-Y', 'sign', '-f', str(k), '-n', d.NAMESPACE, str(f)],
                           check=True, capture_output=True, stdin=subprocess.DEVNULL)
            return sig.read_text()
        owner, stranger = key('owner'), key('stranger')
        pub = [(tmp / 'owner.pub').read_text().strip()]
        cases = {'owner': (sign(owner), pub, None),
                 'unsigned': (None, pub, 'unsigned'),
                 'stranger key': (sign(stranger), pub, 'does not verify'),
                 'other revision': (sign(owner, dict(self.POST, revision='e' * 64)), pub, 'does not verify'),
                 'other account': (sign(owner, who={'username': 'someone_else', 'account_id': '2'}), pub, 'does not verify'),
                 'github unreachable': (sign(owner), {'side_effect': ValueError('Cannot read signing keys: fixture')}, 'Cannot read')}
        for label, (signature, keys, refusal) in cases.items():
            with self.subTest(label):
                x, state = self.fake_x(self.OWNER)
                outcome, _, _ = self.publish(x, signature=signature or '', keys=keys)
                if refusal:
                    self.assertIn(refusal, outcome or '')
                    self.assertEqual(state['sent'], [])
                else:
                    self.assertIsNone(outcome)
                    self.assertEqual(len(state['sent']), 2)

    def test_credentials_file_is_owner_only_and_never_echoed(self):
        import os, tempfile
        from unittest.mock import patch
        tmp = pathlib.Path(tempfile.mkdtemp())
        good = ['# X publishing credentials', 'export X_API_KEY=SENTINEL-a', 'X_API_KEY_SECRET="SENTINEL-b"',
                '', "X_ACCESS_TOKEN = 'SENTINEL-c'", 'X_ACCESS_TOKEN_SECRET=SENTINEL-d']
        def load(lines, mode=0o600):
            f = tmp / 'x-credentials'
            f.write_text('\n'.join(lines) + '\n'); f.chmod(mode)
            with patch.dict(os.environ, {d.CREDENTIALS_FILE: str(f)}):
                try:
                    return d.credentials()
                except ValueError as e:
                    return str(e)
        self.assertEqual(load(good), ('SENTINEL-a', 'SENTINEL-b', 'SENTINEL-c', 'SENTINEL-d'))
        refusals = {'open to other users': load(good, 0o644),
                    'line 2 is not NAME=value': load(['X_API_KEY=SENTINEL-a', 'X_API_KEYY=SENTINEL-typo']),
                    'line 1 is not NAME=value': load(['SENTINEL-bare-value']),
                    'lacks X_ACCESS_TOKEN_SECRET': load(good[:-1])}
        with patch.dict(os.environ, {d.CREDENTIALS_FILE: str(tmp / 'absent')}):
            with self.assertRaises(ValueError) as absent:
                d.credentials()
        refusals['cannot be read'] = str(absent.exception)
        for expected, message in refusals.items():
            with self.subTest(expected):
                self.assertIn(expected, message)
                self.assertNotIn('SENTINEL', message)
        env = {k: f'ENV-{k}' for k in d.ENV}
        with patch.dict(os.environ, env):
            os.environ.pop(d.CREDENTIALS_FILE, None)
            self.assertEqual(d.credentials(), tuple(env[k] for k in d.ENV))

    def test_the_gate_holds_the_credentials_and_never_returns_them(self):
        import json, os, subprocess, tempfile
        secret = {k: f'SENTINEL-{k}-must-not-leave-the-gate' for k in d.ENV}
        creds = pathlib.Path(tempfile.mkdtemp()) / 'x-credentials'
        creds.write_text(''.join(f'{k}={v}\n' for k, v in secret.items())); creds.chmod(0o600)
        env = {**{k: v for k, v in os.environ.items() if k not in d.ENV}, d.CREDENTIALS_FILE: str(creds)}
        if pathlib.Path(sys.prefix).resolve().is_relative_to(d.ROOT):
            env['X_GATE_TEST_REPO_PACKAGES'] = '1'   # the suite runs from a virtualenv inside the repository
        post = d.draft()[0]
        msgs = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'x_gate_status'}},
                {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'x_publish', 'arguments':
                    {'draft_id': post['id'], 'revision': '0' * 12}}},
                {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call', 'params': {'name': 'x_read_env'}}]
        p = subprocess.run([sys.executable, str(d.ROOT / 'scripts' / 'x_gate_mcp.py')], cwd=d.ROOT, env=env, text=True,
                           input=''.join(json.dumps(m) + '\n' for m in msgs), capture_output=True, timeout=300)
        replies = [json.loads(line) for line in p.stdout.splitlines()]   # stdout is JSON-RPC only
        self.assertEqual([r['id'] for r in replies], [1, 2, 3, 4, 5])  # the notification got no reply
        for value in secret.values():
            self.assertNotIn(value, p.stdout + p.stderr)
        tools = {t['name']: t for t in replies[1]['result']['tools']}
        self.assertEqual(set(tools), {'x_gate_status', 'x_publish_dry_run', 'x_cycle', 'x_publish'})
        self.assertFalse(tools['x_publish']['annotations']['readOnlyHint'])
        status = json.loads(replies[2]['result']['content'][0]['text'])
        self.assertEqual((status['credentials_held'], status['credentials_problem']), (True, None))
        self.assertTrue(replies[3]['result']['isError'])
        self.assertIn('nothing was sent', replies[3]['result']['content'][0]['text'])
        self.assertTrue(replies[4]['result']['isError'])

    # ── the processes that hold credentials load nothing a session planted ─────
    PLANT = ('import os, sys\n'
             'open(os.path.join({root!r}, "PLANTED-" + {name!r}), "w").write("ran")\n'
             'import importlib.machinery as m, importlib.util as u\n'
             'here = os.path.dirname(os.path.realpath(__file__))\n'
             'spec = m.PathFinder.find_spec({name!r}, [p for p in sys.path if os.path.realpath(p or ".") not in (here, {root!r})])\n'
             'real = u.module_from_spec(spec); sys.modules[{name!r}] = real; spec.loader.exec_module(real)\n'
             'globals().update({{k: v for k, v in real.__dict__.items() if not k.startswith("__")}})\n')

    def gate_session(self, argv, cwd, env, msgs=None):
        import json, subprocess
        msgs = msgs or [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
                        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}]
        p = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=120,
                           input=''.join(json.dumps(m) + '\n' for m in msgs))
        return p, [json.loads(line) for line in p.stdout.splitlines() if line.strip()]

    def test_nothing_planted_in_the_repository_runs_where_credentials_are(self):
        # A session can write anywhere in the repository, and git ignores *.pyc. Before
        # this guard, each planted file below ran inside distribute.py and the gate,
        # with the credentials in reach, and the tree still looked clean.
        import importlib.util, marshal, os, py_compile, shutil, struct, subprocess, tempfile
        root = pathlib.Path(tempfile.mkdtemp())
        (root / 'scripts').mkdir()
        for name in ('distribute.py', 'x_gate_mcp.py'):
            shutil.copy(d.ROOT / 'scripts' / name, root / 'scripts' / name)
        def plant(where, name):
            src = root / f'plant-{name}.py'
            src.write_text(self.PLANT.format(root=str(root), name=name))
            py_compile.compile(str(src), cfile=str(where / f'{name}.pyc'), doraise=True)
            src.unlink()
        for name in ('__future__', 'json', 'yaml'):
            plant(root / 'scripts', name)
        plant(root, 'contextlib')
        source = root / 'scripts' / 'distribute.py'           # bytecode a normal import would trust
        st, cache = source.stat(), root / 'scripts' / '__pycache__'
        cache.mkdir()
        body = f'open({str(root / "PLANTED-cache")!r}, "w").write("ran")\nexec(compile(open({str(source)!r}).read(), {str(source)!r}, "exec"))\n'
        (cache / f'distribute.{sys.implementation.cache_tag}.pyc').write_bytes(
            importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, int(st.st_mtime) & 0xFFFFFFFF, st.st_size & 0xFFFFFFFF)
            + marshal.dumps(compile(body, str(source), 'exec')))
        env = {**{k: v for k, v in os.environ.items() if k not in d.ENV}, 'PYTHONPATH': str(root)}
        env.pop('PYTHONDONTWRITEBYTECODE', None)
        cli = subprocess.run([sys.executable, 'scripts/distribute.py', '--help'], cwd=root, env=env,
                             capture_output=True, text=True, timeout=120)
        gate, replies = self.gate_session([sys.executable, 'scripts/x_gate_mcp.py'], root, env)
        self.assertEqual((cli.returncode, gate.returncode), (0, 0), cli.stderr + gate.stderr)
        self.assertEqual([r['id'] for r in replies], [1, 2])
        self.assertEqual(sorted(p.name for p in root.glob('PLANTED-*')), [])
        # And git shows such a file: only bytecode under __pycache__/ is ignored.
        ignored = lambda path: subprocess.run(['git', 'check-ignore', '-q', path], cwd=d.ROOT).returncode == 0
        self.assertEqual((ignored('scripts/json.pyc'), ignored('scripts/__pycache__/json.cpython-312.pyc')), (False, True))

    def test_the_template_launcher_starts_only_the_gate_on_main(self):
        import json, os, shutil, subprocess, tempfile
        tmp = pathlib.Path(tempfile.mkdtemp())
        git = lambda cwd, *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@invalid',
                                              '-c', 'init.defaultBranch=main', *a], cwd=cwd, check=True,
                                             capture_output=True, text=True)
        git(tmp, 'init', '-q', '--bare', 'origin.git')
        git(tmp, 'clone', '-q', str(tmp / 'origin.git'), 'clone')
        clone = tmp / 'clone'
        (clone / 'scripts').mkdir()
        for name in ('distribute.py', 'x_gate_mcp.py'):
            shutil.copy(d.ROOT / 'scripts' / name, clone / 'scripts' / name)
        git(clone, 'add', '-A'); git(clone, 'commit', '-q', '-m', 'gate'); git(clone, 'push', '-q', 'origin', 'HEAD:main')
        server = json.loads((d.ROOT / '.claude' / 'x' / 'mcp-servers.json').read_text())['mcpServers']['xgate']
        env = {**{k: v for k, v in os.environ.items() if k not in d.ENV and k != d.CREDENTIALS_FILE},
               'GLASSROOT_REPO': str(clone), 'GLASSROOT_PYTHON': sys.executable}
        argv = [server['command'], *server['args']]
        p, replies = self.gate_session(argv, tmp, env)
        self.assertEqual(([r['id'] for r in replies], p.returncode), ([1, 2], 0), p.stderr)
        p, replies = self.gate_session(argv, tmp, {**env, 'GLASSROOT_PYTHON': str(clone / '.venv' / 'bin' / 'python3')})
        self.assertEqual((replies, p.returncode), ([], 1))
        self.assertIn('GLASSROOT_PYTHON is inside the repository', p.stderr)
        with open(clone / 'scripts' / 'distribute.py', 'a') as f:
            f.write('# a change that has not reached main\n')
        p, replies = self.gate_session(argv, tmp, env)
        self.assertEqual((replies, p.returncode), ([], 1))
        self.assertIn('scripts/distribute.py differs from origin/main', p.stderr)

    def test_setup_doctor_names_each_missing_step_and_prints_no_secret(self):
        import contextlib, importlib.util, io, json, os, shlex, tempfile
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('x_setup', d.ROOT / 'scripts' / 'x_setup.py')
        xs = importlib.util.module_from_spec(spec); spec.loader.exec_module(xs)
        tmp = pathlib.Path(tempfile.mkdtemp())
        empty, home = tmp / 'empty', tmp / 'home'
        empty.mkdir()
        (home / '.config' / 'glassroot').mkdir(parents=True)
        creds = home / '.config' / 'glassroot' / 'x-credentials'
        creds.write_text(''.join(f'{k}=SENTINEL-{k}\n' for k in d.ENV)); creds.chmod(0o600)
        key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixtureFixtureFixtureFixtureFixtureFixture01'
        (home / '.config' / 'glassroot' / 'approval-key.pub').write_text(key + ' glassroot-approval\n')
        xurl = tmp / 'xurl'
        xurl.write_text('#!/bin/sh\necho "xurl v1.3.2"\n'); xurl.chmod(0o755)
        (home / '.claude').mkdir()
        rules = {'permissions': {'allow': ['mcp__xapi__searchPostsRecent'], 'deny': ['mcp__xapi__createPost']}}
        settings = xs.template('user-settings.json')
        settings['permissions']['allow'] += rules['permissions']['allow']
        settings['permissions']['deny'] += rules['permissions']['deny']
        (home / '.claude' / 'settings.json').write_text(json.dumps(settings))
        (home / '.claude.json').write_text(json.dumps(
            {'projects': {str(xs.ROOT): {'mcpServers': xs.servers(sys.executable, xurl)}}}))
        inventory = tmp / 'xapi-inventory.permissions.json'
        inventory.write_text(json.dumps(rules))
        principal = lambda name: {'username': 'PranavBhave_', 'account_id': '1'} if name == 'principal.json' else []
        clean_env = {k: v for k, v in os.environ.items() if k not in d.ENV}
        with patch.dict(os.environ, clean_env, clear=True), patch.object(xs, 'INVENTORY', inventory):
            before = {step: ok for ok, step, _ in xs.doctor(empty, signing_keys=[], gate_differs=lambda: None)}
            with patch.object(xs.d, 'records', principal):
                rows = xs.doctor(home, signing_keys=[key], gate_differs=lambda: [])
        self.assertEqual([step for step, ok in before.items() if ok], ['1 no X values in this environment'])
        interpreter = xs.python_problem(sys.executable)   # a virtualenv inside the repository cannot run the gate
        venv = tmp / 'repo' / '.venv' / 'bin'
        venv.mkdir(parents=True)
        (venv / 'python3').symlink_to(sys.executable)     # as a virtualenv links it
        with patch.object(xs, 'ROOT', tmp / 'repo'):
            self.assertIn('inside the repository', xs.python_problem(str(venv / 'python3')) or '')
        after = {step: ok for ok, step, _ in rows}
        self.assertEqual([step for step, ok in after.items() if not ok], ['5 xgate server'] if interpreter else [])
        self.assertNotIn('SENTINEL', json.dumps(rows))
        if not interpreter:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                xs.commands(sys.executable, str(xurl))
            printed = [shlex.split(line) for line in out.getvalue().splitlines()]
            self.assertEqual({p[5]: json.loads(p[6]) for p in printed}, xs.servers(sys.executable, xurl))

    def test_inventory_freezes_tools_and_treats_unhinted_tools_as_writes(self):
        import importlib.util, json, tempfile
        spec = importlib.util.spec_from_file_location('inv', d.ROOT / 'scripts' / 'x_mcp_inventory.py')
        inv = importlib.util.module_from_spec(spec); spec.loader.exec_module(inv)
        stub = ('import json,sys\n'
                'tools=json.loads(sys.argv[1])\n'
                'for line in sys.stdin:\n'
                ' m=json.loads(line)\n'
                ' if "id" not in m: continue\n'
                ' c=(m.get("params") or {}).get("cursor")\n'
                ' r={"protocolVersion":"2025-06-18","serverInfo":{"name":"stub"}} if m["method"]=="initialize" else '
                '({"tools":tools[:1],"nextCursor":"2"} if not c else {"tools":tools[1:]})\n'
                ' print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":r}),flush=True)\n')
        tools = [{'name': 'search', 'inputSchema': {}, 'annotations': {'readOnlyHint': True}},
                 {'name': 'publish_article', 'inputSchema': {}, 'annotations': {'readOnlyHint': False}},
                 {'name': 'delete_post', 'inputSchema': {}}]
        live = inv.capture([sys.executable, '-c', stub, json.dumps(tools)])
        self.assertEqual([t['name'] for t in live['tools']], ['delete_post', 'publish_article', 'search'])
        rules = inv.permissions('xapi', live)['permissions']
        self.assertEqual(rules, {'allow': ['mcp__xapi__search'],
                                 'deny': ['mcp__xapi__delete_post', 'mcp__xapi__publish_article']})
        self.assertEqual(inv.permissions('xapi', live, 'ask')['permissions']['ask'],
                         ['mcp__xapi__delete_post', 'mcp__xapi__publish_article'])
        drift = inv.capture([sys.executable, '-c', stub, json.dumps(tools + [{'name': 'send_dm', 'inputSchema': {}}])])
        self.assertEqual(inv.compare(live, drift), {'added': ['send_dm'], 'removed': [], 'changed': []})
        self.assertEqual(inv.compare(live, live), {'added': [], 'removed': [], 'changed': []})

    def test_real_drafts_preserve_limits_and_hold(self):
        posts = d.draft(); self.assertTrue(d.verify(posts, allow_pending=True))
        for post in posts:
            self.assertEqual(post['state'], 'held_owner_review')
            self.assertIsNone(post['scheduled_at'])
            self.assertTrue(post['evidence_urls'])

if __name__ == '__main__': unittest.main()
