#!/usr/bin/env python3
"""Owner-run X setup: print the exact commands, then check what is in place.

  python3 scripts/x_setup.py commands --python /path/to/python3 [--xurl /path/to/xurl]
  python3 scripts/x_setup.py doctor

`commands` prints a `claude mcp add-json` line for each server in
.claude/x/mcp-servers.json, with this clone's paths filled in. Run the lines from this
clone's root: they add the servers at local scope, so they load only in this project.

`doctor` checks each step of .claude/x/README.md and prints one line per step: `ok`,
or `todo` with the step to do. It prints no secret. It parses the credentials file
for its four names, compares settings with .claude/x/user-settings.json, and asks
GitHub for the owner's SSH signing keys.
"""
import os
import sys
if __name__ == '__main__':
    # This process reads the credentials file; see the same guard in distribute.py.
    _repo = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    sys.path[:] = [p for p in sys.path if 'site-packages' in p
                   or not (os.path.realpath(p or os.curdir) + os.sep).startswith(_repo + os.sep)]
import argparse
import json
import pathlib
import shlex
import shutil
import subprocess
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / '.claude' / 'x'
INVENTORY = ROOT / 'distribution' / 'x' / 'xapi-inventory.permissions.json'
GATE_FILES = ('scripts/distribute.py', 'scripts/x_gate_mcp.py')
XURL_VERSION = 'v1.3.2'


def load_distribute():
    path = ROOT / 'scripts' / 'distribute.py'
    module = types.ModuleType('distribute')
    module.__file__ = str(path)
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    return module


d = load_distribute()


def inside_repo(path):
    """By the path as given or as resolved: a virtualenv's python3 is a symlink out of the repository,
    yet the pyvenv.cfg beside it, which a session can edit, decides what it loads."""
    for p in (pathlib.Path(os.path.abspath(path)), pathlib.Path(os.path.realpath(path))):
        if p == ROOT or ROOT in p.parents:
            return True
    return False


def template(name):
    return json.loads((TEMPLATES / name).read_text())


def python_problem(python):
    """Why this interpreter cannot run the gate, or None."""
    if not python or not os.access(python, os.X_OK):
        return f'{python} is not an executable'
    if inside_repo(python):
        return f'{python} is inside the repository, where a session can write'
    r = subprocess.run([python, '-c', 'import os, yaml; print(os.path.realpath(yaml.__file__))'],
                       cwd=pathlib.Path.home(), capture_output=True, text=True)
    if r.returncode:
        return f'{python} cannot import PyYAML; run: {python} -m pip install --user pyyaml'
    if inside_repo(r.stdout.strip()):
        return f'{python} imports PyYAML from inside the repository'
    return None


def servers(python, xurl):
    s = template('mcp-servers.json')['mcpServers']
    s['xgate']['env'].update(GLASSROOT_REPO=str(ROOT), GLASSROOT_PYTHON=str(python))
    s['xapi']['command'] = str(xurl)
    return s


def commands(python, xurl):
    problem = python_problem(python)
    if problem:
        raise SystemExit(f'--python: {problem}')
    if not xurl or not os.access(xurl, os.X_OK):
        raise SystemExit(f'--xurl: {xurl} is not an executable; install it with '
                         f'go install github.com/xdevplatform/xurl@{XURL_VERSION}')
    for name, config in servers(python, xurl).items():
        print(f'claude mcp add-json --scope local {name} {shlex.quote(json.dumps(config))}')


# ── doctor ────────────────────────────────────────────────────────────────────
def contains(have, want):
    """Every entry of the template `want` is present in the settings `have`."""
    if isinstance(want, dict):
        return isinstance(have, dict) and all(contains(have.get(k), v) for k, v in want.items())
    if isinstance(want, list):
        return isinstance(have, list) and all(any(contains(h, w) for h in have) for w in want)
    return have == want


def missing(have, want, path=''):
    if isinstance(want, dict):
        return [m for k, v in want.items() for m in missing((have or {}).get(k) if isinstance(have, dict) else None, v, f'{path}.{k}' if path else k)]
    if isinstance(want, list):
        return [f'{path}: {json.dumps(w)}' for w in want if not (isinstance(have, list) and any(contains(h, w) for h in have))]
    return [] if have == want else [f'{path} = {json.dumps(want)}']


def configured(home, name):
    doc = json.loads((home / '.claude.json').read_text()) if (home / '.claude.json').exists() else {}
    local = doc.get('projects', {}).get(str(ROOT), {}).get('mcpServers', {})
    return local.get(name) or doc.get('mcpServers', {}).get(name)


def gate_differs_from_main():
    """The gate files that differ from origin/main after a fresh fetch, as the launcher compares them; None if the fetch fails."""
    git = lambda *a: subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True)
    if git('fetch', '-q', 'origin', 'main').returncode:
        return None
    return [f for f in GATE_FILES
            if git('rev-parse', f'FETCH_HEAD:{f}').stdout.strip() != git('hash-object', '--no-filters', '--', f).stdout.strip()]


def doctor(home, signing_keys=None, gate_differs=gate_differs_from_main):
    """(ok, step, detail) for each step; `signing_keys` and `gate_differs` are injectable for tests."""
    out = []
    creds = home / '.config' / 'glassroot' / 'x-credentials'
    try:
        d.credentials_file(creds)
        out.append((True, '1 credentials file', str(creds)))
    except ValueError as exc:
        out.append((False, '1 credentials file', str(exc)))
    leaked = [k for k in d.ENV if os.environ.get(k)]
    out.append((not leaked, '1 no X values in this environment',
                'unset ' + ' '.join(leaked) + ' in the shell that starts Claude Code' if leaked else 'none set'))

    who = d.records('principal.json')
    out.append((bool(isinstance(who, dict) and who.get('account_id')), '2 principal id recorded',
                f'@{who.get("username")} {who.get("account_id") or "has no account_id; run: distribute.py principal"}'
                if isinstance(who, dict) else 'distribution/traction/principal.json is missing'))

    pub = home / '.config' / 'glassroot' / 'approval-key.pub'
    if not pub.exists():
        out.append((False, '3 approval key registered on GitHub', f'{pub} does not exist'))
    else:
        mine = ' '.join(pub.read_text().split()[:2])
        try:
            keys = signing_keys if signing_keys is not None else d.owner_signing_keys()
            ok = any(' '.join(k.split()[:2]) == mine for k in keys)
            out.append((ok, '3 approval key registered on GitHub',
                        'listed' if ok else f'not among {d.OWNER_LOGIN}\'s SSH signing keys; add it as a Signing Key'))
        except ValueError as exc:
            out.append((False, '3 approval key registered on GitHub', str(exc)))

    path = home / '.claude' / 'settings.json'
    have = json.loads(path.read_text()) if path.exists() else {}
    want = template('user-settings.json')
    gaps = missing(have, want)
    out.append((not gaps, '4 user settings', 'match .claude/x/user-settings.json' if not gaps
                else f'merge .claude/x/user-settings.json into {path}' if len(gaps) == len(missing({}, want))
                else f'{path} lacks ' + '; '.join(gaps)))

    gate, want = configured(home, 'xgate'), template('mcp-servers.json')['mcpServers']['xgate']
    if not gate:
        out.append((False, '5 xgate server', 'not configured; run: python3 scripts/x_setup.py commands --python ...'))
    else:
        env = gate.get('env', {})
        problems = [p for p in (
            'launcher differs from .claude/x/mcp-servers.json' if gate.get('args') != want['args'] else None,
            f'GLASSROOT_REPO is not {ROOT}' if env.get('GLASSROOT_REPO') != str(ROOT) else None,
            python_problem(env.get('GLASSROOT_PYTHON')),
            'X_CREDENTIALS_FILE is not set' if not env.get('X_CREDENTIALS_FILE') else None,
            'its env holds credential values; give it X_CREDENTIALS_FILE instead' if any(k in env for k in d.ENV) else None,
        ) if p]
        out.append((not problems, '5 xgate server', '; '.join(problems) or 'configured as the template'))

    reader = configured(home, 'xapi')
    if not reader:
        out.append((False, '6 xapi server', 'not configured'))
    else:
        r = subprocess.run([reader.get('command', ''), 'version'], capture_output=True, text=True) \
            if shutil.which(reader.get('command', '')) else None
        version = r.stdout.strip() if r and r.returncode == 0 else ''
        out.append((XURL_VERSION in version, '6 xapi server',
                    version or f'{reader.get("command")} does not run; go install github.com/xdevplatform/xurl@{XURL_VERSION}'))

    if not INVENTORY.exists():
        out.append((False, '7 xapi inventory frozen and applied', f'{INVENTORY.name} does not exist; see step 7'))
    else:
        gaps = missing(have, {'permissions': json.loads(INVENTORY.read_text())['permissions']})
        out.append((not gaps, '7 xapi inventory frozen and applied', 'rules applied' if not gaps
                    else f'{path} lacks ' + '; '.join(gaps)))

    differ = gate_differs()
    out.append((differ == [], '5 gate code equals origin/main',
                'git fetch origin main failed' if differ is None else
                'the launcher will start the gate' if not differ else
                ', '.join(differ) + ' differ from origin/main; the launcher will refuse to start the gate'))
    return sorted(out, key=lambda row: row[1])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stage', choices=('commands', 'doctor'))
    ap.add_argument('--python', help='commands: a python3 outside the repository, with PyYAML')
    ap.add_argument('--xurl', default=shutil.which('xurl') or str(pathlib.Path.home() / 'go' / 'bin' / 'xurl'),
                    help='commands: the xurl binary (default: on PATH, else ~/go/bin/xurl)')
    a = ap.parse_args(argv)
    if a.stage == 'commands':
        if not a.python:
            ap.error('commands needs --python')
        commands(a.python, a.xurl)
        return 0
    rows = doctor(pathlib.Path.home())
    for ok, step, detail in rows:
        print(f'{"ok  " if ok else "todo"}  {step}: {detail}')
    return 0 if all(ok for ok, _, _ in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
