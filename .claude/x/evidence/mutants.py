#!/usr/bin/env python3
"""Mutation controls for the X gate. Each mutant removes or weakens one guard; the named
test must fail against it. Usage: mutants.py <checkout> <python>. Restores every file."""
import json, pathlib, subprocess, sys

W, PY = pathlib.Path(sys.argv[1]).resolve(), sys.argv[2]
D, G, I, S, T, GI = (W / 'scripts/distribute.py', W / 'scripts/x_gate_mcp.py', W / 'scripts/x_mcp_inventory.py',
                     W / 'scripts/x_setup.py', W / '.claude/x/mcp-servers.json', W / '.gitignore')
ORIG = {p: p.read_text() for p in (D, G, I, S, T, GI)}

gate = ORIG[G]
strip_a = gate.index("sys.path[:] = [p for p in sys.path if not inside_repo(p)")
strip_b = gate.index("\n\nimport contextlib")
load_a = gate.index('def load(name):')
load_b = gate.index('    return module\n', load_a) + len('    return module\n')


def launcher(edit):
    doc = json.loads(ORIG[T])
    doc['mcpServers']['xgate']['args'][1] = edit(doc['mcpServers']['xgate']['args'][1])
    return json.dumps(doc, indent=2) + '\n'


# label: ({file: (old, new) | full text}, test)
MUTANTS = {
    'M1 publish skips the principal check': (
        {D: ("    check_principal(me, principal())\n", "")}, 'test_publish_refuses_credentials_that_act_as_another_account'),
    'M2 read-back keeps t.co links': (
        {D: ("    for u in (note.get('entities') or tweet.get('entities') or {}).get('urls', []):",
             "    for u in []:")}, 'test_observed_text_undoes_what_x_does_to_a_post'),
    'M3 read-back keeps &amp;': (
        {D: ("    return canonical(html.unescape(text))", "    return canonical(text)")},
        'test_observed_text_undoes_what_x_does_to_a_post'),
    'M4 dispatch skips the signature': (
        {D: ("    verify_approval(post, row)\n    done", "    done")}, 'test_only_an_owner_signature_admits_a_dispatch'),
    'M5 a partial thread leaves no receipt': (
        {D: ("            receipt(status='PARTIAL', error=str(exc)[:300])", "            pass")},
        'test_partial_thread_is_recorded_and_blocks_redispatch'),
    'M6 read-back always reports a match': (
        {D: ("    return checks, all(c['equal'] and c['author_matches'] for c in checks)", "    return checks, True")},
        'test_readback_matches_what_was_approved_and_flags_what_was_not'),
    'M7 a partial receipt does not block re-dispatch': (
        {D: ("    if any(r.get('status') == 'PARTIAL' for r in done):", "    if False:")},
        'test_partial_thread_is_recorded_and_blocks_redispatch'),
    'M8 a missing approval row is treated as an empty one': (
        {D: ("    if row is None:\n        raise", "    if row is None:\n        row = {}\n    if False:\n        raise")},
        'test_dispatch_refuses_without_an_approval_or_a_clean_pushed_tree'),
    'M9 a dirty tree is accepted': (
        {D: ("        if git('status', '--porcelain'):", "        if False:")},
        'test_dispatch_refuses_without_an_approval_or_a_clean_pushed_tree'),
    'M10 an unpushed HEAD is accepted': (
        {D: ("        if not git('branch', '-r', '--contains', head):", "        if False:")},
        'test_dispatch_refuses_without_an_approval_or_a_clean_pushed_tree'),
    'C1 a credentials file open to others is accepted': (
        {D: ("    if mode & 0o077:", "    if False:")}, 'test_credentials_file_is_owner_only_and_never_echoed'),
    'C2 a malformed line is echoed in the error': (
        {D: ("            raise ValueError(f'{path} line {n} is not NAME=value for one of ' + ', '.join(ENV))",
             "            raise ValueError(f'{path} line {n} ({line}) is not NAME=value for one of ' + ', '.join(ENV))")},
        'test_credentials_file_is_owner_only_and_never_echoed'),
    'G1 status returns the credentials': (
        {G: ("    return {'principal': who, 'credentials_held': problem is None,",
             "    return {'values': list(d.credentials()), 'principal': who, 'credentials_held': problem is None,")},
        'test_the_gate_holds_the_credentials_and_never_returns_them'),
    'G2 x_publish does not check the named revision': (
        {G: ("    if len(revision) < 12 or not post['revision'].startswith(revision):", "    if False:")},
        'test_the_gate_holds_the_credentials_and_never_returns_them'),
    'I1 a tool with no hint counts as a read': (
        {I: ("    return (tool.get('annotations') or {}).get('readOnlyHint') is True",
             "    return (tool.get('annotations') or {}).get('readOnlyHint', True) is True")},
        'test_inventory_freezes_tools_and_treats_unhinted_tools_as_writes'),
    'I2 the inventory reads only the first page': (
        {I: ("            cursor = page.get('nextCursor')", "            cursor = None")},
        'test_inventory_freezes_tools_and_treats_unhinted_tools_as_writes'),
    'MX1 distribute.py keeps the repository on sys.path': (
        {D: ("    sys.path[:] = [p for p in sys.path if 'site-packages' in p\n                   or not (os.path.realpath(p or os.curdir) + os.sep).startswith(_repo + os.sep)]\n",
             "    pass\n")}, 'test_nothing_planted_in_the_repository_runs_where_credentials_are'),
    'MX2 the gate imports distribute by name, its directory first': (
        {G: gate[:strip_a] + 'sys.path.insert(0, HERE)\nTESTING = True' + gate[strip_b:load_a]
            + 'def load(name):\n    return __import__(name)\n' + gate[load_b:]},
        'test_nothing_planted_in_the_repository_runs_where_credentials_are'),
    'MX3 the gate loads distribute through the import system (trusts cached bytecode)': (
        {G: gate[:load_a] + ('def load(name):\n    import importlib.util\n'
                             '    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))\n'
                             '    module = importlib.util.module_from_spec(spec); sys.modules[name] = module\n'
                             '    spec.loader.exec_module(module)\n    return module\n') + gate[load_b:]},
        'test_nothing_planted_in_the_repository_runs_where_credentials_are'),
    'MX4 the gate removes only its own directory': (
        {G: ("sys.path[:] = [p for p in sys.path if not inside_repo(p) or",
             "sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != HERE or")},
        'test_nothing_planted_in_the_repository_runs_where_credentials_are'),
    'MX7 .gitignore hides *.pyc outside __pycache__': (
        {GI: ("__pycache__/\n", "__pycache__/\n*.pyc\n")},
        'test_nothing_planted_in_the_repository_runs_where_credentials_are'),
    'MX5 the launcher does not compare the gate with main': (
        {T: launcher(lambda a: a[:a.index('cd "$GLASSROOT_REPO"')] + 'cd "$GLASSROOT_REPO" && exec "$GLASSROOT_PYTHON" scripts/x_gate_mcp.py')},
        'test_the_template_launcher_starts_only_the_gate_on_main'),
    'MX6 the launcher accepts a Python inside the repository': (
        {T: launcher(lambda a: a[a.index('cd "$GLASSROOT_REPO"'):])},
        'test_the_template_launcher_starts_only_the_gate_on_main'),
    'D1 the doctor finds no missing setting': (
        {S: ("def missing(have, want, path=''):\n", "def missing(have, want, path=''):\n    return []\n")},
        'test_setup_doctor_names_each_missing_step_and_prints_no_secret'),
    'D2 the doctor accepts any interpreter': (
        {S: ('def python_problem(python):\n    """Why this interpreter cannot run the gate, or None."""\n',
             'def python_problem(python):\n    """Why this interpreter cannot run the gate, or None."""\n    return None\n')},
        'test_setup_doctor_names_each_missing_step_and_prints_no_secret'),
}


def apply(changes):
    for path, change in changes.items():
        if isinstance(change, tuple):
            old, new = change
            assert ORIG[path].count(old) == 1, (path.name, old[:70])
            path.write_text(ORIG[path].replace(old, new))
        else:
            path.write_text(change)


results = {}
try:
    base = subprocess.run([PY, '-m', 'unittest', 'tests.test_distribution'], cwd=W, capture_output=True, text=True)
    results['unmutated suite'] = 'PASS' if base.returncode == 0 else 'FAIL'
    for label, (changes, test) in MUTANTS.items():
        apply(changes)
        r = subprocess.run([PY, '-m', 'unittest', f'tests.test_distribution.DistributionTests.{test}'],
                           cwd=W, capture_output=True, text=True, timeout=600)
        why = [l for l in r.stderr.splitlines() if 'Error' in l or 'error' in l]
        results[label] = {'test': test, 'outcome': 'KILLED' if r.returncode else 'SURVIVED',
                          'failure': why[-1][:160] if r.returncode and why else None}
        for path in changes:
            path.write_text(ORIG[path])
finally:
    for path, text in ORIG.items():
        path.write_text(text)
print(json.dumps(results, indent=1))
