#!/usr/bin/env python3
"""Reconstruct agent-entry state. Read-only by default; never dispatches actions.

Exit 0: state reconstructed / requested local operation succeeded.
Exit 2: required evidence unavailable, stale, conflicting, or invalid.
See docs/AGENT_ENTRY.md for trust boundaries and the cache/lease formats.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import tempfile
import uuid

SCHEMA = 'glassroot.agent-state.v1'
REQUIRED_ROOTS = {'repository_policy', 'claim_registry', 'control_plane', 'readiness_policy',
                  'dashboard', 'evidence_kernel', 'run_disclosure', 'pre_outcome',
                  'owner_decisions', 'lease'}
CAPABILITIES = {'READ', 'SCRATCH_WRITE', 'TEST', 'CANDIDATE_PATCH'}
PHASES = {'repair', 'preparation', 'frozen', 'revealed'}
EVIDENCE = {'observed', 'reproduced', 'clean_rerun', 'independently_reproduced',
            'owner_attested', 'inferred'}
HEX = re.compile(r'^[0-9a-f]{64}$')
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


class Refusal(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc)


def stamp(value=None):
    return (value or now()).isoformat(timespec='seconds')


def moment(value):
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError('timezone missing')
        return result
    except (TypeError, ValueError, AttributeError) as exc:
        raise Refusal('invalid timezone-qualified timestamp') from exc


def read_json(path):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise Refusal('duplicate JSON key: ' + k)
            result[k] = v
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(Refusal('nonfinite JSON')))


def safe_path(root, name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '.git' in p.parts or str(p) != name:
        raise Refusal('unsafe relative path')
    candidate = root / name
    if any(x.is_symlink() for x in [candidate, *candidate.parents] if x != root.parent):
        # Only inspect ancestors within the repository, not /tmp's OS alias.
        for i in range(1, len(p.parts) + 1):
            if root.joinpath(*p.parts[:i]).is_symlink():
                raise Refusal('symlink root refused: ' + name)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise Refusal('path escapes root')
    return candidate


def git(root, *args, optional=False):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(['git', '-c', 'core.fsmonitor=false', *args], cwd=root,
                            env=env, capture_output=True)
    if result.returncode and not optional:
        raise Refusal('git operation failed: ' + args[0])
    return result.stdout if result.returncode == 0 else None


def snapshot_repository(root):
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    branch = git(root, 'symbolic-ref', '--short', '-q', 'HEAD', optional=True)
    index = git(root, 'ls-files', '--stage', '-z')
    # Use an alternate index so even cache-tree updates cannot touch owner staging.
    index_path = Path(git(root, 'rev-parse', '--git-path', 'index').decode().strip())
    if not index_path.is_absolute():
        index_path = root / index_path
    with tempfile.TemporaryDirectory(prefix='agent-index-') as tmp:
        alternate = Path(tmp) / 'index'
        if index_path.exists():
            alternate.write_bytes(index_path.read_bytes())
        result = subprocess.run(['git', 'write-tree'], cwd=root, capture_output=True,
                                env=dict(os.environ, GIT_INDEX_FILE=str(alternate), GIT_OPTIONAL_LOCKS='0'))
    tree = result.stdout.decode().strip() if result.returncode == 0 else None
    status = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    fields = status.split(b'\0'); dirty = []; i = 0
    while i < len(fields) and fields[i]:
        raw = fields[i]; i += 1
        code, name = raw[:2].decode(), os.fsdecode(raw[3:])
        entry = {'path': name, 'status': code, 'provenance': 'unattributed_preserve'}
        if 'R' in code or 'C' in code:
            entry['old_path'] = os.fsdecode(fields[i]); i += 1
        p = root / name
        if p.is_symlink():
            entry.update(kind='symlink', content_sha256=digest(os.readlink(p)))
        elif p.is_file():
            entry.update(kind='file', content_sha256=file_hash(p), executable=bool(p.stat().st_mode & 0o111))
        elif p.exists():
            entry.update(kind='nonregular', content_sha256=None)
        else:
            entry.update(kind='deleted', content_sha256=None)
        dirty.append(entry)
    upstream = git(root, 'rev-parse', '--abbrev-ref', '@{upstream}', optional=True)
    upstream = upstream.decode().strip() if upstream else None
    upstream_head = git(root, 'rev-parse', '@{upstream}', optional=True) if upstream else None
    ahead = behind = None
    if upstream_head:
        ahead, behind = map(int, git(root, 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}').split())
    lock = Path(git(root, 'rev-parse', '--git-path', 'index.lock').decode().strip())
    if not lock.is_absolute():
        lock = root / lock
    return {'head': head, 'branch': branch.decode().strip() if branch else None,
            'index_tree': tree, 'index_entries_sha256': hashlib.sha256(index).hexdigest(),
            'dirty': sorted(dirty, key=lambda x: x['path']), 'upstream': upstream,
            'upstream_head': upstream_head.decode().strip() if upstream_head else None,
            'ahead': ahead, 'behind': behind, 'diverged': bool(ahead and behind),
            'remote_observation': 'local_tracking_ref_only', 'remote_observed_at': None,
            'index_lock_present': lock.exists()}


def environment():
    packages = sorted({(x.metadata['Name'].lower(), x.version) for x in importlib.metadata.distributions()
                       if x.metadata.get('Name')})
    return {'python': platform.python_version(), 'executable': sys.executable,
            'platform': platform.platform(), 'packages': packages,
            'git': subprocess.check_output(['git', '--version'], text=True).strip()}


def bound_root(root, spec, observed_at):
    """Validate data only. No script, shell command, URL, or key location is executed."""
    kind = spec['kind']
    path = safe_path(root, spec['path'])
    expected = spec.get('sha256')
    if not expected or not HEX.fullmatch(expected):
        raise Refusal('missing pinned SHA-256')
    actual = file_hash(path)
    if actual != expected:
        raise Refusal('root hash changed')
    result = {'kind': kind, 'path': spec['path'], 'sha256': actual}
    if kind == 'local':
        return result
    if kind != 'external_snapshot':
        raise Refusal('unsupported root kind')
    data = read_json(path)
    required = {'provider', 'object_id', 'revision_before', 'revision_after',
                'observed_at', 'payload', 'payload_sha256', 'coverage'}
    if not required <= data.keys():
        raise Refusal('incomplete external observation')
    if data['provider'] != 'google_drive' or data['object_id'] != spec['object_id']:
        raise Refusal('external object identity mismatch')
    if not data['revision_before'] or data['revision_before'] != data['revision_after']:
        raise Refusal('revision changed during observation or is missing')
    if digest(data['payload']) != data['payload_sha256']:
        raise Refusal('external payload changed')
    age = (observed_at - moment(data['observed_at'])).total_seconds()
    if age < 0 or age > spec.get('max_age_seconds', 3600):
        raise Refusal('external observation stale or from the future')
    if data['coverage'] != spec.get('coverage'):
        raise Refusal('external coverage mismatch')
    result.update(object_id=data['object_id'], revision=data['revision_after'],
                  payload_sha256=data['payload_sha256'], coverage=data['coverage'],
                  freshness='within_declared_observation_window',
                  evidence_level='observed', live_state_guaranteed=False)
    if spec.get('sheet'):
        payload = data['payload']
        if not isinstance(payload, dict) or not isinstance(payload.get('formula_fingerprint'), str):
            raise Refusal('sheet formula fingerprint absent')
        if not HEX.fullmatch(payload['formula_fingerprint']) or payload.get('formula_basis') is None:
            raise Refusal('sheet formula fingerprint or basis absent')
        if digest(payload['formula_basis']) != payload['formula_fingerprint']:
            raise Refusal('sheet formula fingerprint mismatch')
        result['formula_fingerprint'] = payload['formula_fingerprint']
    return result


def validate_lease(value, state, at):
    required = {'issuer', 'subject', 'capabilities', 'not_before', 'expires_at', 'phase', 'repository_head'}
    if not required <= value.keys():
        raise Refusal('incomplete capability lease')
    if not value['issuer'] or value['subject'] != state['execution'].get('execution_id'):
        raise Refusal('lease subject mismatch')
    caps = value['capabilities']
    if not isinstance(caps, list) or any(x not in CAPABILITIES for x in caps) or len(caps) != len(set(caps)):
        raise Refusal('capability not supported by this controller')
    if not moment(value['not_before']) <= at < moment(value['expires_at']):
        raise Refusal('lease expired or not yet valid')
    if value['phase'] != state['phase'] or value['repository_head'] != state['repository']['head']:
        raise Refusal('lease phase or repository mismatch')
    return sorted(caps)


def capture(root, config, at=None):
    at = at or now(); cfg = read_json(config)
    if cfg.get('version') != 1:
        raise Refusal('unsupported configuration schema')
    # A process with broad Git access cannot honestly promise blindness.
    if cfg.get('phase') == 'blind':
        raise Refusal('blind entry requires an externally isolated checkout and tool harness; not implemented here')
    roots = cfg.get('roots', {})
    if not isinstance(roots, dict) or not roots:
        raise Refusal('required root inventory absent')
    before = snapshot_repository(root)
    errors = [{'id': 'root:' + name, 'kind': 'required_root_not_declared', 'claim_refuted': False}
              for name in sorted(REQUIRED_ROOTS - roots.keys())]; resolved = {}
    for name, spec in sorted(roots.items()):
        try:
            resolved[name] = bound_root(root, spec, at)
        except (KeyError, OSError, ValueError) as exc:
            errors.append({'id': 'root:' + name, 'kind': 'missing_or_invalid_root', 'detail': str(exc),
                           'authority': 'root_custodian', 'claim_refuted': False})
    execution = cfg.get('execution', {})
    for field in ['model', 'provider', 'harness', 'effort', 'execution_id']:
        if not execution.get(field) or execution[field] == 'unknown':
            errors.append({'id': 'execution:' + field, 'kind': 'unknown_identity', 'claim_refuted': False})
    phase = cfg.get('phase', 'unknown')
    if phase not in PHASES:
        errors.append({'id': 'phase', 'kind': 'unknown_phase', 'claim_refuted': False})
    contamination = cfg.get('contamination', 'unknown')
    if contamination not in {'unknown', 'exposed', 'not_assessed'}:
        raise Refusal('this harness cannot attest unexposed/blind status')
    commitment = cfg.get('sealed_key_commitment')
    if not isinstance(commitment, str) or not HEX.fullmatch(commitment):
        errors.append({'id': 'sealed_key_commitment', 'kind': 'missing_commitment', 'claim_refuted': False})
        commitment = None
    if any('key_location' in x or 'key_path' in x for x in cfg):
        raise Refusal('sealed key locations must not enter the capsule')
    owner_decisions = []
    if 'owner_decisions' in resolved:
        data = read_json(safe_path(root, roots['owner_decisions']['path']))
        for item in data.get('decisions', []):
            if not {'id', 'status', 'source', 'alternatives'} <= item.keys():
                raise Refusal('owner decision is not source-bound')
            if item['status'] not in {'open', 'unknown', 'resolved'}:
                raise Refusal('unknown owner decision status')
            owner_decisions.append(item)
    else:
        errors.append({'id': 'owner_decisions', 'kind': 'unbound_owner_decisions', 'claim_refuted': False})
    if before['index_tree'] is None or before['index_lock_present']:
        errors.append({'id': 'index', 'kind': 'conflict_or_lock', 'claim_refuted': False})
    if any(x['kind'] == 'nonregular' for x in before['dirty']):
        errors.append({'id': 'dirty_nonregular', 'kind': 'unfingerprinted_surface', 'claim_refuted': False})
    chain = history(root / '_private/control')
    known_blockers = []
    if 'claim_registry' in resolved:
        import yaml
        claims = yaml.safe_load(safe_path(root, resolved['claim_registry']['path']).read_text())
        for claim in claims.get('claims', []):
            reviewed = dt.date.fromisoformat(str(claim['last_reviewed']))
            if (at.date() - reviewed).days > claim['review_window_days']:
                known_blockers.append({'id': claim['id'], 'kind': 'review_due',
                    'authority': 'owner', 'claim_refuted': False,
                    'source': resolved['claim_registry']['path'], 'blocks': 'publication_not_reconstruction'})
    state = {'schema': SCHEMA, 'repository': before, 'control_roots': resolved,
             'config_sha256': file_hash(config), 'controller_sha256': file_hash(Path(__file__)),
             'execution': execution, 'environment': environment(), 'phase': phase,
             'contamination': contamination, 'sealed_key_commitment': commitment,
             'last_durable_receipt': chain[-1]['event_id'] if chain else None,
             'known_blockers': known_blockers,
             'open_owner_decisions': [x for x in owner_decisions if x['status'] != 'resolved'],
             'blockers': errors, 'capabilities': [], 'authority': 'none',
             'non_claims': ['Reconstruction is not authorization or release readiness.',
                           'File ownership is not inferable from Git; unattributed work is preserved.',
                           'External roots are observed snapshots, not an atomic live Drive transaction.',
                           'This is a cooperative local controller, not an OS sandbox or issuer authenticator.',
                           'Same-host tests are not independent reproduction.']}
    if 'lease' in resolved:
        try:
            state['capabilities'] = validate_lease(read_json(safe_path(root, roots['lease']['path'])), state, at)
            state['authority'] = 'caller_pinned_lease; issuer_not_authenticated_by_this_tool'
        except (KeyError, ValueError) as exc:
            errors.append({'id': 'lease', 'kind': 'invalid_lease', 'detail': str(exc), 'claim_refuted': False})
    else:
        errors.append({'id': 'lease', 'kind': 'no_authority', 'claim_refuted': False})
    # Re-read exact required roots and repo after observation to catch common races.
    for name, value in resolved.items():
        if file_hash(safe_path(root, value['path'])) != value['sha256']:
            raise Refusal('root changed during capture: ' + name)
    if snapshot_repository(root) != before or file_hash(config) != state['config_sha256']:
        raise Refusal('repository or configuration changed during capture')
    state['status'] = 'BLOCKED' if errors else 'RECONSTRUCTED'
    state_id = digest(state)
    return {'state_id': state_id, 'state': state, 'observation': {'observed_at': stamp(at)}}


def verify_capsule(capsule):
    if capsule.get('state_id') != digest(capsule['state']) or capsule['state']['schema'] != SCHEMA:
        raise Refusal('capsule identity mismatch')
    return capsule['state']


def render(capsule):
    s = verify_capsule(capsule); r = s['repository']
    lines = ['# Current agent-entry state', '', '**' + s['status'] + '** — not publication approval.', '',
             'State: `' + capsule['state_id'] + '`', 'Observed: ' + capsule['observation']['observed_at'],
             '', 'Branch: ' + str(r['branch']), 'HEAD: `' + r['head'] + '`',
             'Index tree: `' + str(r['index_tree']) + '`',
             f"Upstream: {r['upstream']}; ahead {r['ahead']}; behind {r['behind']} (local tracking only)",
             'Phase: ' + s['phase'], 'Contamination: ' + s['contamination'],
             'Capabilities: ' + (', '.join(s['capabilities']) or 'none'), '', '## Blockers', '']
    lines += ['- ' + x['id'] + ': ' + x['kind'] + (' — ' + x['detail'] if x.get('detail') else '') for x in s['blockers']]
    lines += ['', '## Known blockers — not refutations', '']
    lines += ['- ' + x['id'] + ': ' + x['kind'] + ' (' + x['blocks'] + ')' for x in s['known_blockers']]
    lines += ['', '## Existing work — preserve', '']
    lines += [f"- `{x['path']}`: {x['status']} / {x['provenance']}" for x in r['dirty']]
    lines += ['', '## Bound roots', '']
    lines += ['- ' + k + ': `' + v['sha256'] + '` (' + v['kind'] + ')' for k, v in s['control_roots'].items()]
    lines += ['', '## Limits', ''] + ['- ' + x for x in s['non_claims']]
    return '\n'.join(lines) + '\n'


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / 'controller.lock'
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise Refusal('controller lock exists; inspect the recorded holder, never auto-delete') from exc
    try:
        (lock / 'holder.json').write_bytes(canonical({'pid': os.getpid(), 'started_at': stamp()}))
        yield
    finally:
        (lock / 'holder.json').unlink(missing_ok=True)
        lock.rmdir()


def publish_capsule(directory, capsule):
    """Local immutable snapshot plus one atomic pointer; not external publication."""
    ident = capsule['state_id']; verify_capsule(capsule)
    target = directory / 'states' / ident
    # Stable identity excludes observation time. Retain the first observation of it.
    if not target.exists():
        target.mkdir(parents=True)
        atomic_write(target / 'state.json', canonical(capsule) + b'\n')
        atomic_write(target / 'state.md', render(capsule).encode())
    else:
        verify_capsule(read_json(target / 'state.json'))
        if not (target / 'state.md').exists():
            raise Refusal('incomplete immutable snapshot; explicit recovery required')
    atomic_write(directory / 'current.json', canonical({'state_id': ident, 'json': f'states/{ident}/state.json',
                                                       'markdown': f'states/{ident}/state.md'}) + b'\n')


def history(directory, expected_head=None):
    chain = directory / 'events'; previous = None; result = []
    for seq, path in enumerate(sorted(chain.glob('*.json')) if chain.exists() else []):
        value = read_json(path); event_id = value.pop('event_id', None)
        if path.name != f'{seq:08d}.json' or value.get('previous') != previous or digest(value) != event_id:
            raise Refusal('event chain corrupted, missing, or reordered')
        previous = event_id; result.append(dict(value, event_id=event_id))
    if expected_head is not None and previous != expected_head:
        raise Refusal('event history differs from external anchor')
    return result


def append_event(directory, data):
    rows = history(directory); prior = rows[-1]['event_id'] if rows else None
    event = dict(data, previous=prior, sequence=len(rows)); ident = digest(event)
    path = directory / 'events' / f'{len(rows):08d}.json'
    if path.exists():
        raise Refusal('event already exists')
    atomic_write(path, canonical(dict(event, event_id=ident)) + b'\n')
    return ident


def plan(capsule):
    state = verify_capsule(capsule)
    actions = [
        {'id': 'resolve_roots', 'capability': 'READ', 'information_gain': 'high', 'reversibility': 'read_only',
         'reason': 'Resolve missing, ambiguous, or expired required roots without deciding their semantics.'},
        {'id': 'scratch_negative_controls', 'capability': 'TEST', 'information_gain': 'high', 'reversibility': 'scratch',
         'reason': 'Exercise refusal paths in disposable fixtures.'},
        {'id': 'prepare_candidate', 'capability': 'CANDIDATE_PATCH', 'information_gain': 'medium', 'reversibility': 'patch',
         'reason': 'Prepare a reviewable patch without applying or publishing it.'}]
    for action in actions:
        action['eligible'] = (state['status'] == 'RECONSTRUCTED' and action['capability'] in state['capabilities']
                              and (state['phase'] != 'frozen' or action['id'] == 'resolve_roots'))
    return {'state_id': capsule['state_id'], 'actions': actions,
            'selected': next((x['id'] for x in actions if x['eligible']), None),
            'stop_reason': None if any(x['eligible'] for x in actions) else 'No eligible transition under current roots and lease.',
            'dispatch': 'never; advisory ordering only, no numeric utility claim'}


def receipt_layers(legacy):
    """Lossless sidecar projection; does not replace or weaken legacy freshness checks."""
    required = {'film', 'format', 'inputs', 'outputs', 'frames_digest', 'runtime', 'rendered_from_head',
                'rendered_on', 'render_seconds', 'facts_used', 'determinism', 'text_overflows'}
    if not required <= legacy.keys():
        raise Refusal('incomplete film receipt')
    artifact = {'film': legacy['film'], 'format': legacy['format'],
                'video_sha256': legacy['outputs']['master_sha256'],
                'frames_digest': legacy['frames_digest'],
                'identity_scope': 'video_and_frame_digest_reported_by_legacy_receipt',
                'semantic_input_closure': 'not_established'}
    execution = {k: legacy[k] for k in ['runtime', 'rendered_on', 'render_seconds', 'determinism', 'text_overflows']}
    governance = {'input_bindings': legacy['inputs'], 'rendered_from_head': legacy['rendered_from_head'],
                  'facts_used': legacy['facts_used'], 'admissibility': 'not_evaluated',
                  'policy': 'legacy whole-registry freshness gate remains required'}
    return {'schema': 'glassroot.receipt-projection.v1', 'artifact_id': digest(artifact), 'artifact': artifact,
            'execution_fingerprint': digest(execution), 'execution': execution,
            'governance_id': digest(governance), 'governance': governance,
            'legacy_sha256_canonical': digest(legacy), 'legacy': legacy}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--config', type=Path, default=Path('_private/control/roots.json'))
    parser.add_argument('--output', type=Path, default=Path('_private/control'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('capture'); sub.add_parser('plan'); sub.add_parser('check')
    begin = sub.add_parser('begin'); begin.add_argument('--expected-state', required=True); begin.add_argument('--action', required=True)
    end = sub.add_parser('finish'); end.add_argument('--token', required=True); end.add_argument('--evidence', type=Path, required=True)
    check = sub.add_parser('history'); check.add_argument('--expected-head')
    split = sub.add_parser('split-receipt'); split.add_argument('receipt', type=Path)
    args = parser.parse_args(argv)
    root = args.repo.resolve(); config = args.config if args.config.is_absolute() else root / args.config
    directory = args.output if args.output.is_absolute() else root / args.output
    if directory.resolve() != (root / '_private/control').resolve():
        raise Refusal('one repository has one controller store: _private/control')
    # Local output is always ignored/private, not an arbitrary overwrite target.
    private = (root / '_private').resolve()
    if not directory.resolve().is_relative_to(private) or any(p.is_symlink() for p in [directory, private]):
        raise Refusal('output must be a private directory inside this repository')
    if args.command == 'split-receipt':
        print(json.dumps(receipt_layers(read_json(args.receipt)), indent=2)); return 0
    if args.command == 'history':
        print(json.dumps(history(directory, args.expected_head), indent=2)); return 0
    if args.command == 'finish':
        with locked(directory):
            pending = read_json(directory / 'active.json')
            if args.token != pending['token']:
                raise Refusal('transition token mismatch')
            evidence_path = args.evidence.resolve()
            if not evidence_path.is_relative_to(private):
                raise Refusal('evidence must be a private local artifact')
            evidence = read_json(evidence_path)
            if evidence.get('evidence_level') not in EVIDENCE or evidence.get('evidence_level') == 'independently_reproduced':
                raise Refusal('this local controller cannot attest independent reproduction')
            after = capture(root, config)
            event_id = append_event(directory, {'type': 'finish', 'execution_id': pending['execution_id'],
                'token': args.token, 'before_state': pending['state_id'], 'after_state': after['state_id'],
                'evidence_sha256': file_hash(evidence_path), 'evidence_level': evidence['evidence_level'],
                'disposition': 'recorded_not_accepted', 'observed_at': stamp()})
            (directory / 'active.json').unlink()
            publish_capsule(directory, capture(root, config))
            print(event_id); return 0
    try:
        capsule = capture(root, config)
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        if args.command == 'capture':
            with locked(directory):
                atomic_write(directory / 'current.json', canonical({'status': 'BLOCKED', 'error': str(exc), 'observed_at': stamp()}))
        raise
    if args.command == 'check':
        pointer = read_json(directory / 'current.json')
        stored = read_json(safe_path(directory, pointer['json'])); verify_capsule(stored)
        if stored['state_id'] != capsule['state_id']:
            raise Refusal('current capsule is stale')
    elif args.command == 'plan':
        print(json.dumps(plan(capsule), indent=2))
    elif args.command == 'begin':
        with locked(directory):
            current = capture(root, config)
            if current['state_id'] != args.expected_state:
                raise Refusal('compare-and-swap failed: state changed')
            if (directory / 'active.json').exists():
                raise Refusal('another transition is active; inspect it, do not steal it')
            eligible = [x['id'] for x in plan(current)['actions'] if x['eligible']]
            if args.action not in eligible:
                raise Refusal('action outside current capability/phase/root boundary')
            token = str(uuid.uuid4())
            pending = {'token': token, 'state_id': current['state_id'], 'action': args.action,
                       'execution_id': current['state']['execution']['execution_id'], 'started_at': stamp()}
            atomic_write(directory / 'active.json', canonical(pending))
            append_event(directory, dict(pending, type='begin', disposition='intent_only_no_dispatch'))
            print(token)
    else:
        with locked(directory):
            publish_capsule(directory, capsule)
        print(render(capsule))
    return 0 if capsule['state']['status'] == 'RECONSTRUCTED' else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Refusal, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
