#!/usr/bin/env python3
"""Create and independently restore-test a local snapshot, including uncommitted work."""
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.PIPE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '.git' in p.parts or str(p) != name:
        raise ValueError(f'unsafe recovery path: {name}')
    return p


def create(root, destination):
    root, destination = root.resolve(), destination.resolve()
    if destination.is_relative_to(root):
        raise ValueError('snapshot must be outside the repository')
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'bundle', 'create', str(destination / 'history.bundle'), '--all')
    (destination / 'staged.patch').write_bytes(git(root, 'diff', '--cached', '--binary', 'HEAD'))
    paths = sorted(set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')) - {''})
    files, deleted = {}, []
    with tarfile.open(destination / 'workspace.tar.gz', 'w:gz') as archive:
        for name in paths:
            safe_path(name)
            path = root / name
            if path.is_symlink():
                raise ValueError(f'symlink requires explicit backup support: {name}')
            if not path.exists():
                deleted.append(name)
                continue
            data = path.read_bytes()
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), path.stat().st_mode & 0o777
            archive.addfile(info, io.BytesIO(data))
            files[name] = {'sha256': sha(data), 'mode': info.mode}
    manifest = {'version': 1, 'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'head': head, 'refs': git(root, 'show-ref').decode().splitlines(),
                'files': files, 'deleted': deleted,
                'limitations': ['same-device copy; not disaster isolation',
                                'ignored files, credentials, GitHub issues/settings and external model caches excluded'],
                'artifacts': {n: sha((destination / n).read_bytes()) for n in
                              ('history.bundle', 'staged.patch', 'workspace.tar.gz')}}
    data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (destination / 'manifest.json').write_bytes(data)
    return sha(data)


def verify(snapshot, expected):
    data = (snapshot / 'manifest.json').read_bytes()
    if sha(data) != expected:
        raise ValueError('manifest differs from separately retained digest')
    manifest = json.loads(data)
    for name, digest in manifest['artifacts'].items():
        if name not in ('history.bundle', 'staged.patch', 'workspace.tar.gz'):
            raise ValueError('unexpected artifact')
        if sha((snapshot / name).read_bytes()) != digest:
            raise ValueError(f'corrupt snapshot artifact: {name}')
    with tempfile.TemporaryDirectory(prefix='cubits-restore-') as tmp:
        restored = Path(tmp) / 'repo'
        subprocess.run(['git', 'clone', '--no-checkout', str(snapshot / 'history.bundle'), str(restored)],
                       check=True, capture_output=True)
        git(restored, 'checkout', '--detach', manifest['head'])
        git(restored, 'fsck', '--full')
        for ref in manifest['refs']:
            git(restored, 'cat-file', '-e', ref.split()[0])
        patch = snapshot / 'staged.patch'
        if patch.stat().st_size:
            git(restored, 'apply', '--cached', str(patch))
        if git(restored, 'diff', '--cached', '--binary', 'HEAD') != patch.read_bytes():
            raise ValueError('staging restoration differs')
        for name in manifest['deleted']:
            safe_path(name)
            path = restored / name
            if not path.resolve().is_relative_to(restored.resolve()):
                raise ValueError('restoration would escape checkout')
            path.unlink(missing_ok=True)
        seen = set()
        with tarfile.open(snapshot / 'workspace.tar.gz') as archive:
            for member in archive:
                safe_path(member.name)
                if not member.isfile() or member.name in seen or member.name not in manifest['files']:
                    raise ValueError('unexpected recovery member')
                seen.add(member.name)
                content = archive.extractfile(member).read()
                record = manifest['files'][member.name]
                if sha(content) != record['sha256'] or member.mode != record['mode']:
                    raise ValueError('workspace content differs')
                target = restored / member.name
                if not target.resolve().is_relative_to(restored.resolve()):
                    raise ValueError('restoration would escape checkout')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(record['mode'])
        if seen != set(manifest['files']):
            raise ValueError('missing workspace members')
        for name, record in manifest['files'].items():
            if sha((restored / name).read_bytes()) != record['sha256']:
                raise ValueError('restored bytes differ')
    return {'restored_files': len(seen), 'head': manifest['head'], 'status': 'RESTORE_TEST_PASSED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['create', 'verify'])
    parser.add_argument('destination', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.action == 'create':
        digest = create(args.root, args.destination)
        print(json.dumps({'snapshot': str(args.destination), 'manifest_sha256': digest,
                          **verify(args.destination.resolve(), digest)}, indent=2))
    else:
        if not args.manifest_sha256:
            parser.error('verify requires the separately retained --manifest-sha256')
        print(json.dumps(verify(args.destination.resolve(), args.manifest_sha256), indent=2))


if __name__ == '__main__':
    main()
