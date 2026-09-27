#!/usr/bin/env python3
"""X10: can a file a session writes into scripts/, and git does not show, run inside the
process that holds the X credentials, before any dispatch check?

Usage: x10.py <distribute.py> <x_gate_mcp.py> <label> <.gitignore>
Prints one JSON object. Everything happens in a temporary directory; nothing leaves it.

Base inputs: distribute.py as of f2249c1 (`git show f2249c1:scripts/distribute.py`), and
x_gate_mcp.py with its loader replaced by the one it had before the guard:
`sys.path.insert(0, <scripts>)` then `import distribute`. The gitignore is the repository's.
"""
import ast, importlib.util, json, marshal, os, pathlib, py_compile, shutil, struct, subprocess, sys, tempfile

DIST, GATE, LABEL = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve(), sys.argv[3]
REPO_GITIGNORE = pathlib.Path(sys.argv[4]).resolve()
ENV_NAMES = ('X_API_KEY', 'X_API_KEY_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET')

# A planted module records that it ran and whether the credentials were in reach,
# then puts the real module in its place so the host carries on as if nothing happened.
PLANT = '''
import os, sys
_mark = os.path.join({root!r}, 'MARK-' + {name!r})
open(_mark, 'w').write(repr({{'ran': True, 'saw_credentials': all(os.environ.get(k, '').startswith('SENTINEL')
                                                                  for k in {env!r})}}))
import importlib.machinery as _m, importlib.util as _u
_here = os.path.dirname(os.path.realpath(__file__))
_spec = _m.PathFinder.find_spec({name!r}, [p for p in sys.path if os.path.realpath(p or '.') not in (_here, {root!r})])
_real = _u.module_from_spec(_spec); sys.modules[{name!r}] = _real; _spec.loader.exec_module(_real)
sys.modules[{name!r}] = _real
globals().update({{k: v for k, v in _real.__dict__.items() if k not in ('__name__', '__file__', '__spec__', '__loader__')}})
'''


def plant_pyc(root, where, name):
    src = root / f'plant_{name}.py'
    src.write_text(PLANT.format(root=str(root), name=name, env=ENV_NAMES))
    py_compile.compile(str(src), cfile=str(where / f'{name}.pyc'), doraise=True)
    src.unlink()


def poison_cache(root):
    """A cached-bytecode file for distribute.py whose header matches the source, so a normal import trusts it."""
    source = root / 'scripts' / 'distribute.py'
    st = source.stat()
    body = PLANT.format(root=str(root), name='distribute-cache', env=ENV_NAMES).split('import importlib.machinery')[0]
    body += f'exec(compile(open({str(source)!r}).read(), {str(source)!r}, "exec"))\n'
    code = compile(body, str(source), 'exec')
    tag = sys.implementation.cache_tag
    cache = root / 'scripts' / '__pycache__'
    cache.mkdir(exist_ok=True)
    header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, int(st.st_mtime) & 0xFFFFFFFF, st.st_size & 0xFFFFFFFF)
    (cache / f'distribute.{tag}.pyc').write_bytes(header + marshal.dumps(code))


def marks(root):
    return {p.name[5:]: ast.literal_eval(p.read_text()) for p in sorted(root.glob('MARK-*'))}


def main():
    root = pathlib.Path(tempfile.mkdtemp(prefix='x10-'))
    (root / 'scripts').mkdir()
    shutil.copy(DIST, root / 'scripts' / 'distribute.py')
    shutil.copy(GATE, root / 'scripts' / 'x_gate_mcp.py')
    shutil.copy(REPO_GITIGNORE, root / '.gitignore')
    git = lambda *a: subprocess.run(['git', '-C', str(root), *a], capture_output=True, text=True, check=True).stdout
    git('init', '-q'); git('add', '-A')
    git('-c', 'user.name=x10', '-c', 'user.email=x10@invalid', 'commit', '-q', '-m', 'fixture')
    for name in ('__future__', 'yaml', 'json'):
        plant_pyc(root, root / 'scripts', name)       # beside the scripts
    plant_pyc(root, root, 'contextlib')               # at the repository root
    poison_cache(root)
    clean = git('status', '--porcelain') == ''
    env = {**{k: v for k, v in os.environ.items() if k not in ENV_NAMES and k != 'X_CREDENTIALS_FILE'},
           **{k: f'SENTINEL-{k}' for k in ENV_NAMES}, 'PYTHONPATH': str(root)}
    env.pop('PYTHONDONTWRITEBYTECODE', None)

    cli = subprocess.run([sys.executable, 'scripts/distribute.py', '--help'], cwd=root, env=env,
                         capture_output=True, text=True, timeout=60)
    cli_marks = marks(root)
    for p in root.glob('MARK-*'):
        p.unlink()

    msgs = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}]
    gate = subprocess.run([sys.executable, 'scripts/x_gate_mcp.py'], cwd=root, env=env, text=True, timeout=60,
                          input=''.join(json.dumps(m) + '\n' for m in msgs), capture_output=True)
    replies = [json.loads(l) for l in gate.stdout.splitlines() if l.strip()]
    print(json.dumps({
        'label': LABEL, 'python': sys.version.split()[0], 'git_status_porcelain_empty': clean,
        'distribute_cli': {'rc': cli.returncode, 'planted_ran': sorted(cli_marks),
                           'planted_saw_credentials': any(m['saw_credentials'] for m in cli_marks.values())},
        'gate': {'rc': gate.returncode, 'answered': [r.get('id') for r in replies],
                 'tools': [t['name'] for t in replies[1]['result']['tools']] if len(replies) > 1 else None,
                 'planted_ran': sorted(marks(root)),
                 'poisoned_cache_for_distribute_ran': 'distribute-cache' in marks(root),
                 'stderr_tail': gate.stderr.strip().splitlines()[-1:]},
    }, indent=1))
    shutil.rmtree(root)


main()
