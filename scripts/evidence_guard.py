#!/usr/bin/env python3
"""Compare a candidate's data to policy from a trusted base; never execute candidate code."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'security/evidence-policy.json'


def safe(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '.git' in p.parts or str(p) != name:
        raise ValueError('unsafe policy path')
    return name


def read(root, ref, name):
    safe(name)
    if ref == 'WORKTREE':
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('evidence path cannot be a symlink or escape repository')
        return path.read_bytes()
    if not re.fullmatch('[0-9a-f]{40,64}', ref):
        raise ValueError('commit must be a full object ID')
    tree = subprocess.check_output(['git', 'ls-tree', ref, '--', name], cwd=root)
    if not tree.startswith((b'100644 blob ', b'100755 blob ')):
        raise ValueError(f'not a regular evidence blob: {name}')
    return subprocess.check_output(['git', 'show', f'{ref}:{name}'], cwd=root)


def document(data, kind):
    if kind == 'json':
        return json.loads(data)
    if kind == 'jsonl':
        return [json.loads(line) for line in data.splitlines() if line.strip()]
    return yaml.safe_load(data)


def workflow_inventory(root, ref):
    if ref == 'WORKTREE':
        return sorted(str(p.relative_to(root)) for p in (root / '.github/workflows').rglob('*') if p.is_file())
    if not re.fullmatch('[0-9a-f]{40,64}', ref):
        raise ValueError('commit must be a full object ID')
    names = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', ref,
                                     '--', '.github/workflows'], cwd=root)
    return sorted(n for n in names.decode().split('\0') if n)


def compare(policy, old, new):
    """Readers return bytes. Only data is parsed; no candidate imports or commands."""
    errors = []
    for path, digest in policy['immutable'].items():
        try:
            if hashlib.sha256(new(path)).hexdigest() != digest:
                errors.append(f'frozen evidence changed: {path}')
        except (OSError, ValueError, subprocess.CalledProcessError):
            errors.append(f'frozen evidence missing or unsafe: {path}')
    if old is None:
        return errors
    # Protect the checker and its wiring from being replaced by the same change
    # whose evidence is being judged. An upgrade needs an explicit admin migration.
    for path in policy['trust_root']:
        try:
            if old(path) != new(path):
                errors.append(f'trust-root change requires separate migration: {path}')
        except (OSError, ValueError, subprocess.CalledProcessError):
            errors.append(f'trust-root file missing: {path}')
    for rule in policy['append_only']:
        path = rule['path']
        try:
            before = document(old(path), rule['format'])
            after = document(new(path), rule['format'])
            for field in rule.get('fixed_fields', []):
                if before[field] != after[field]:
                    errors.append(f'history anchor changed: {path}:{field}')
            if rule.get('field'):
                before, after = before[rule['field']], after[rule['field']]
            if not isinstance(before, list) or not isinstance(after, list) or after[:len(before)] != before:
                errors.append(f'history rewritten or truncated: {path}')
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, subprocess.CalledProcessError):
            errors.append(f'history unavailable or malformed: {path}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='local pin check only; no trusted-base guarantee')
    parser.add_argument('--base')
    parser.add_argument('--candidate')
    args = parser.parse_args()
    try:
        if args.local:
            if args.base or args.candidate:
                parser.error('--local cannot be combined with commit comparisons')
            policy = json.loads(read(ROOT, 'WORKTREE', POLICY))
            old, new = None, lambda p: read(ROOT, 'WORKTREE', p)
        else:
            if not args.base or not args.candidate:
                parser.error('both --base and --candidate are required')
            policy = json.loads(read(ROOT, args.base, POLICY))
            old = lambda p: read(ROOT, args.base, p)
            new = lambda p: read(ROOT, args.candidate, p)
        errors = compare(policy, old, new)
        ref = 'WORKTREE' if args.local else args.candidate
        if workflow_inventory(ROOT, ref) != policy['workflow_paths']:
            errors.append('workflow inventory changed: separate trust-root migration required')
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f'UNDETERMINED: trusted inputs unavailable: {type(exc).__name__}')
        return 2
    for error in errors:
        print('FAIL:', error)
    if not errors:
        print('PASS: frozen evidence pins' if args.local else 'PASS: evidence extends the trusted base')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
