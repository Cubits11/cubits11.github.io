#!/usr/bin/env python3
"""Evidence distribution: python3 scripts/distribute.py run (offline) · approve · publish · snapshot."""
import os
import sys
if __name__ == '__main__':
    # Run as a script, this process may hold the publishing credentials, and Python
    # searches the script's own directory first on every import. A session can write
    # anywhere in the repository, and git ignores *.pyc, so a planted file could run
    # before any check. Every repository directory except installed packages leaves
    # sys.path before anything else is imported; os and sys are already loaded at
    # startup, so importing them searched nothing.
    _repo = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    sys.path[:] = [p for p in sys.path if 'site-packages' in p
                   or not (os.path.realpath(p or os.curdir) + os.sep).startswith(_repo + os.sep)]
import argparse
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import statistics
import subprocess
import unicodedata
from urllib.parse import urlencode, urlsplit, urlunsplit
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = pathlib.Path('distribution/traction')
METRICS = ('impressions', 'profile_visits', 'link_clicks', 'bookmarks', 'replies',
           'follows', 'likes', 'reposts', 'engagements', 'repo_views', 'site_visits', 'research_actions')
DIMS = ('post_type', 'audience', 'topic', 'hook', 'visual', 'cta', 'thread_structure', 'time_slot')
ROLES = {
 'research_extraction': 'Read tracked artifacts; preserve source hashes and event kind.',
 'claim_audit': 'Check registry freshness, pins, scope, non-claims and source-specific gates.',
 'post_generation': 'Render source fields verbatim; changes require a new source revision.',
 'visual_selection': 'Bind existing media; hold films for the existing cold-comprehension gate.',
 'scheduling': 'Propose UTC slots; never dispatch or interpret a queue as authorization.',
 'metrics_ingestion': 'Import sourced cumulative snapshots; missing is null, never zero.',
 'attribution': 'Require direct post identifiers; aggregate traffic is contextual only.',
 'adversarial_review': 'Reject drift, invented claims, missing limits and unsupported inference.'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def read(path):
    return yaml.safe_load((ROOT / path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def pin(path):
    p = ROOT / path
    if not p.is_file() or not p.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError(f'Invalid source: {path}')
    commit = git('log', '-1', '--format=%H', '--', str(path))
    committed = bool(commit) and subprocess.check_output(['git', 'show', commit + ':' + str(path)], cwd=ROOT) == p.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'commit': commit if committed else None,
            'url': f'https://github.com/Cubits11/cubits11.github.io/blob/{commit}/{path}' if committed else None,
            'binding': 'committed' if committed else 'pending_commit'}


def stamp(s):
    t = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('Timestamp needs timezone')
    return t.astimezone(dt.timezone.utc)


def chunks(text, limit=240):
    # Conservative Unicode weighting (URLs are deliberately not discounted).
    words, parts, line = text.split(), [], ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if sum(1 if ord(c) < 0x1100 else 2 for c in candidate) > limit:
            if not line:
                raise ValueError('Unbreakable post token')
            parts.append(line)
            line = word
        else:
            line = candidate
    if line:
        parts.append(line)
    return parts


def extract():
    paths = {'claims.yaml': 'claims', 'claims_history.yaml': 'claim_change',
             'census.yaml': 'census', 'distribution/outcomes.yaml': 'metrics',
             'docs/graph/organism.receipt.json': 'visualization'}
    for pattern, kind in [('experiments/*/RESULT.md', 'result'), ('experiments/*/CORRECTION-*.md', 'correction'), ('experiments/*/STOP-*.md', 'contradiction'),
                          ('experiments/*/PREREG.md', 'experiment'), ('experiments/*/freeze/*.json', 'freeze'),
                          ('films/*/manifest.yaml', 'film')]:
        paths.update({p.relative_to(ROOT).as_posix(): kind for p in ROOT.glob(pattern)})
    events = []
    routes = draft()
    for path, kind in sorted(paths.items()):
        if (ROOT / path).exists():
            source = pin(path)
            events.append({'id': digest(source)[:16], 'kind': kind, 'source': source,
                           'draft_ids': [r['id'] for r in routes if any(s['path'] == path for s in r['sources'])],
                           'state': 'candidate_requires_claim_audit',
                           'hold_reason': 'Inventory alone does not authorize a claim; source-specific release gates and an approved reproduction route are required.',
                           'novelty': 'snapshot; not asserted newly published'})
    return events


def draft():
    reg = {c['id']: c for c in read('claims.yaml')['claims']}
    campaigns = read('campaigns.yaml')
    units = read('distribution/launch-units.yaml')['units']
    posts = []
    for proposal in records('schedule.json'):
        stamp(proposal['scheduled_at'])
    for exp in read('distribution/experiments.yaml')['experiments']:
        unit = next(u for u in units if u.get('experiment') == exp['id'])
        campaign = next(c for c in campaigns['campaigns'] if c['id'] == unit['campaign'])
        url = urlsplit(campaigns['site'] + campaigns['destinations'][campaign['destination']])
        link = urlunsplit((url.scheme, url.netloc, url.path,
                          urlencode({'utm_' + k: v for k, v in campaign['utm'].items()}), url.fragment))
        claimset = [reg[c] for c in exp['claims']]
        sources = [pin(p) for p in ['claims.yaml', 'distribution/experiments.yaml', 'distribution/launch-units.yaml', 'campaigns.yaml']]
        for c in claimset:
            for trigger in c.get('review_triggers', []):
                if trigger['type'] == 'local_content_change':
                    sources.append(pin(trigger['path']))
        sources.append(pin('films/' + exp['film'] + '/manifest.yaml'))
        text = chunks(exp['question']) + chunks(exp['epistemic_status']) + chunks(exp['non_claim'])
        text += chunks('Reproduce: ' + exp['command']) + chunks(link)
        evidence = list(dict.fromkeys(c['support']['url'] for c in claimset))  # one link per distinct source
        text += [u for u in evidence if len(u) <= 260]
        item = {'id': exp['id'].lower(), 'campaign': campaign['id'], 'claims': exp['claims'],
                'confidence': {c['id']: c['dimensions']['evidential_status'] for c in claimset},
                'scope': {c['id']: c['scope'] for c in claimset}, 'evidence_urls': evidence,
                'sources': sources, 'posts': text, 'attribution_url': link,
                'audience_hypothesis': campaign['audience'], 'why': campaign['intended_action'],
                'success_signal': campaign['success_signal'], 'post_type': 'thread',
                'topic': exp['slug'], 'hook': 'question', 'visual': 'none',
                'cta': 'reproduce', 'thread_structure': 'question-status-limits-command-evidence',
                'visual_candidate': {'path': unit['poster'], 'master': unit['master'],
                                     'state': 'held_existing_cold_test_gate'},
                'scheduled_at': next((r['scheduled_at'] for r in records('schedule.json') if r['draft_id'] == exp['id'].lower()), None), 'state': 'held_owner_review',
                'anti_hype': ['no vendor ranking', 'no population or causal inference',
                              'no synthetic engagement', 'retain non-claims', 'no automated replies'],
                'rank_basis': 'existing reproducible route; source order; no audience-performance evidence'}
        item['revision'] = digest(item)
        posts.append(item)
    for item in (read('distribution/educational-posts.json') or {}).get('items', []):
        campaign = next(c for c in campaigns['campaigns'] if c['id'] == item['campaign'])
        claimset = [reg[c] for c in item['claims']]
        post = {**item, 'sources': [pin(p) for p in item['source_paths']],
                'confidence': {c['id']: c['dimensions']['evidential_status'] for c in claimset},
                'scope': {c['id']: c['scope'] for c in claimset},
                'evidence_urls': [c['support']['url'] for c in claimset],
                'audience_hypothesis': campaign['audience'], 'why': campaign['intended_action'],
                'success_signal': campaign['success_signal'], 'state': 'held_owner_review',
                'scheduled_at': None, 'attribution_url': item['destination_url'],
                'rank_basis': 'constructed example; no disputed empirical headline'}
        post['revision'] = digest(post)
        posts.append(post)
    return posts


def verify(posts, *, allow_pending=False):
    if posts != draft():
        raise ValueError('Draft/provenance drift: regenerate; free text is not evidence')
    today = dt.date.today()
    claims = {c['id']: c for c in read('claims.yaml')['claims']}
    for p in posts:
        for cid in p['claims']:
            c = claims[cid]
            due = dt.date.fromisoformat(str(c['last_reviewed'])) + dt.timedelta(days=c['review_window_days'])
            if today > due or c['dimensions']['evidential_status'] != 'supported_within_scope':
                raise ValueError(f'Claim held: {cid}')
            for t in c.get('review_triggers', []):
                if t['type'] == 'local_content_change' and pin(t['path'])['sha256'] != t['sha256']:
                    raise ValueError(f'Broken pin: {cid}')
        for s in p['sources']:
            if not s['commit']:
                if allow_pending and s['binding'] == 'pending_commit' and pin(s['path'])['sha256'] == s['sha256']:
                    continue
                raise ValueError('Draft source awaits commit')
            if subprocess.check_output(['git', 'show', s['commit'] + ':' + s['path']], cwd=ROOT) != (ROOT / s['path']).read_bytes():
                raise ValueError('Source differs from committed provenance')
        if any(sum(1 if ord(c) < 0x1100 else 2 for c in t) > 280 for t in p['posts']):
            raise ValueError('Post too long')
    return True


def records(name):
    p = ROOT / BASE / name
    return json.loads(p.read_text()) if p.exists() else []


def validate_publications(rows, posts):
    seen = set()
    for row in rows:
        if row['post_id'] in seen or not re.fullmatch(r'[0-9]+', row['post_id']):
            raise ValueError('Duplicate/invalid platform post ID')
        seen.add(row['post_id'])
        if not re.fullmatch(r'https://x.com/[^/]+/status/' + row['post_id'], row['source_url']):
            raise ValueError('Publication needs matching public URL')
        p = next((p for p in posts + records('draft-history.json') if p['id'] == row['draft_id'] and p['revision'] == row['draft_revision']), None)
        if p is None or row['draft_revision'] != p['revision']:
            raise ValueError('Unknown draft revision; preserve a historical draft before changing sources')
        stamp(row['published_at'])
        if any(not isinstance(row[d], str) or not row[d] for d in DIMS):
            raise ValueError('Missing experiment dimensions')


def validate_metrics(rows, publications):
    pubs = {p['post_id']: p for p in publications}
    seen = set()
    for row in rows:
        key = (row['post_id'], row['observed_at'], row['provider'], row['scope'])
        if key in seen:
            raise ValueError('Duplicate snapshot')
        seen.add(key)
        if row['post_id'] not in pubs or row['scope'] not in ('organic', 'total', 'promoted'):
            raise ValueError('Unknown post or metric scope')
        if not isinstance(row.get('source'), str) or not row['source'].startswith('https://') or not row.get('provider'):
            raise ValueError('Metrics need a source receipt and provider')
        if stamp(row['observed_at']) < stamp(pubs[row['post_id']]['published_at']):
            raise ValueError('Metric observation precedes publication')
        if set(row['metrics']) - set(METRICS):
            raise ValueError('Unknown metric')
        for name, value in row['metrics'].items():
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Metric must be a nonnegative integer or null')
        if row.get('attribution') != 'direct_post' and any(row['metrics'].get(m) is not None for m in ('repo_views', 'site_visits', 'research_actions')):
            raise ValueError('Aggregate traffic cannot be attributed to a post')
    return rows


def validate_traffic(rows):
    seen = set()
    for row in rows:
        key = (row['provider'], row['surface'], row['start'], row['end'])
        if key in seen or row['surface'] not in ('repository', 'site'):
            raise ValueError('Duplicate traffic window or unknown surface')
        seen.add(key)
        if stamp(row['end']) <= stamp(row['start']) or not row['source'].startswith('https://'):
            raise ValueError('Traffic needs ordered time bounds and a source')
        for field in ('views', 'unique_visitors'):
            value = row.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Invalid traffic count')
    return rows


def rates(m):
    def ratio(a, b):
        return m.get(a) / m[b] if m.get(a) is not None and m.get(b) else None
    return {'ctr': ratio('link_clicks', 'impressions'),
            'engagement_rate': ratio('engagements', 'impressions'),
            'follower_conversion': ratio('follows', 'profile_visits'),
            'research_action_rate': ratio('research_actions', 'link_clicks')}


def learn(publications, snapshots):
    # One snapshot per post/scope/provider at each predeclared age, never sum cumulative snapshots.
    validate_metrics(snapshots, publications)
    pubs = {p['post_id']: p for p in publications}
    selected = {}
    for row in snapshots:
        age = (stamp(row['observed_at']) - stamp(pubs[row['post_id']]['published_at'])).total_seconds()/3600
        window = next((h for h in (24, 72, 168) if h <= age < h + 6), None)
        if window is None:
            continue
        key = (row['post_id'], row['scope'], row['provider'], window)
        if key not in selected or stamp(row['observed_at']) < stamp(selected[key]['observed_at']):
            selected[key] = row
    groups, comparisons = {}, []
    for key, row in sorted(selected.items(), key=lambda kv: stamp(pubs[kv[0][0]]['published_at'])):
        pub = pubs[row['post_id']]
        cohort = tuple(pub[d] for d in ('post_type', 'audience', 'topic', 'time_slot')) + (row['scope'], row['provider'], key[-1])
        previous = groups.setdefault(cohort, [])
        values = rates(row['metrics'])
        baseline = {}
        for metric, value in values.items():
            eligible = [r[metric] for t, r in previous[-20:] if r[metric] is not None and
                        0 <= (stamp(pub['published_at'])-t).total_seconds() <= 30*86400]
            avg = statistics.mean(eligible) if eligible else None
            baseline[metric] = {'value': value, 'baseline_mean': avg, 'baseline_n': len(eligible),
                                'delta_percentage_points': (value-avg)*100 if value is not None and avg is not None else None}
        previous.append((stamp(pub['published_at']), values))
        comparisons.append({'post_id': row['post_id'], 'cohort': list(cohort), 'rates': baseline,
                            'interpretation': 'descriptive; no randomization, significance or causal attribution',
                            'experiment': {d: pub[d] for d in DIMS}})
    observations = []
    for row in sorted(snapshots, key=lambda r: stamp(r['observed_at'])):
        age = (stamp(row['observed_at']) - stamp(pubs[row['post_id']]['published_at'])).total_seconds()/3600
        window = next((h for h in (24, 72, 168) if h <= age < h + 6), None)
        observations.append({**row, 'age_hours': round(age, 6), 'comparison_window_hours': window,
                             'window_status': 'eligible_window' if window else 'off_window_retained_not_compared'})
    return {'publication_count': len(publications), 'snapshot_count': len(snapshots), 'comparisons': comparisons,
            'observations': observations,
            'audience_model': 'No observed demand yet.' if not comparisons else 'Descriptive matched cohorts only; hypotheses remain unconfirmed.',
            'compounding': 'Qualified outcomes require verification in distribution/outcomes.yaml; attention never qualifies.',
            'next_experiment': 'Prepared show-overlap example: publish correction destination before dispatch. Missing historical windows stay missing; off-window observations remain visible.',
            'unavailable': 'No site analytics; UTM URLs do not measure visits. Import owner-visible platform receipts and repo traffic separately.'}


# ── publishing: X API v2, OAuth 1.0a user context, standard library only ─────
# Credentials are read from the environment, or from the owner-only file that
# X_CREDENTIALS_FILE names, and never written anywhere. The stage refuses unless:
# the tree is clean, HEAD is on a remote (the dispatch revision is public), the
# draft's current revision carries an approval in approvals.json signed by the
# owner, the credentials act as the recorded principal, and verify() passes at
# this revision.
ENV = ('X_API_KEY', 'X_API_KEY_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET')
CREDENTIALS_FILE = 'X_CREDENTIALS_FILE'
API = 'https://api.x.com/2'


def _oauth_header(method, url, params, creds):
    import base64, hmac, os, secrets, time, urllib.parse as up
    key, key_secret, token, token_secret = creds
    oauth = {'oauth_consumer_key': key, 'oauth_nonce': secrets.token_hex(16),
             'oauth_signature_method': 'HMAC-SHA1', 'oauth_timestamp': str(int(time.time())),
             'oauth_token': token, 'oauth_version': '1.0'}
    q = lambda s: up.quote(str(s), safe='~')
    base_params = '&'.join(f'{q(k)}={q(v)}' for k, v in sorted({**params, **oauth}.items()))
    base = '&'.join((method.upper(), q(url), q(base_params)))
    sig = base64.b64encode(hmac.new(f'{q(key_secret)}&{q(token_secret)}'.encode(), base.encode(), 'sha1').digest()).decode()
    oauth['oauth_signature'] = sig
    return 'OAuth ' + ', '.join(f'{q(k)}="{q(v)}"' for k, v in sorted(oauth.items()))


def x_request(method, path, creds, body=None, query=None):
    import urllib.request as ur, urllib.error as ue, urllib.parse as up
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    full = url + ('?' + up.urlencode(query) if query else '')
    req = ur.Request(full, data=data, method=method,
                     headers={'Authorization': _oauth_header(method, url, query or {}, creds),
                              'Content-Type': 'application/json', 'User-Agent': 'cubits11-distribute/1'})
    try:
        with ur.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except ue.HTTPError as e:
        raise ValueError(f'X API {e.code} on {method} {path}: {e.read().decode()[:400]}')


def credentials():
    """The four OAuth 1.0a values: from the file X_CREDENTIALS_FILE names if it is set, else the environment.

    A process that starts the gate can pass it a path instead of the secrets, so
    the secrets never enter that process's environment or its other children's.
    """
    import os
    if os.environ.get(CREDENTIALS_FILE):
        return credentials_file(pathlib.Path(os.environ[CREDENTIALS_FILE]).expanduser())
    missing = [k for k in ENV if not os.environ.get(k)]
    if missing:
        raise ValueError('Publishing needs environment credentials (never tracked): ' + ', '.join(missing))
    return tuple(os.environ[k] for k in ENV)


def credentials_file(path):
    """NAME=value lines for exactly the names in ENV. Errors name lines and names, never values."""
    try:
        mode = path.stat().st_mode
        text = path.read_text()
    except OSError as e:
        raise ValueError(f'The credentials file {path} cannot be read ({e.strerror})')
    if mode & 0o077:
        raise ValueError(f'{path} is open to other users (mode {mode & 0o777:o}); run: chmod 600 {path}')
    values = {}
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, sep, value = line.partition('=')
        name = name.removeprefix('export ').strip()
        if not sep or name not in ENV:
            raise ValueError(f'{path} line {n} is not NAME=value for one of ' + ', '.join(ENV))
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        values[name] = value
    missing = [k for k in ENV if not values.get(k)]
    if missing:
        raise ValueError(f'{path} lacks ' + ', '.join(missing))
    return tuple(values[k] for k in ENV)


def approval_for(post):
    return next((a for a in records('approvals.json') if a['draft_id'] == post['id'] and a['draft_revision'] == post['revision']), None)


# ── who publishes, and who may approve ────────────────────────────────────────
# A credential proves that X will accept a request, not which account it acts as
# or that the owner wanted this post. The principal file names the account; the
# approval carries a signature from a key only the owner holds. Both are checked
# before the first request of a dispatch.
NAMESPACE = 'glassroot-x-approval'
OWNER_LOGIN = 'Cubits11'   # GitHub account whose SSH signing keys may sign approvals


def principal():
    """The X account publishing must act as. Recorded by the owner, never inferred at dispatch."""
    doc = records('principal.json')
    if not isinstance(doc, dict) or not doc.get('username'):
        raise ValueError('No X principal recorded in distribution/traction/principal.json; '
                         'on the owner machine run: distribute.py principal')
    return doc


def check_principal(me, who):
    """Compare-and-swap on identity: the account the credentials act as must be the recorded one."""
    if who.get('account_id'):
        same = str(me.get('id')) == str(who['account_id'])
    else:
        same = str(me.get('username', '')).lower() == who['username'].lower()
    if not same:
        raise ValueError(f'Credentials act as @{me.get("username")} ({me.get("id")}), not the recorded principal '
                         f'@{who["username"]} ({who.get("account_id") or "id not yet observed"}); nothing was posted')


def observe_principal():
    """Owner-run: record the id of the account the credentials act as. Refuses to switch accounts."""
    me = x_request('GET', '/users/me', credentials())['data']
    doc = records('principal.json')
    doc = doc if isinstance(doc, dict) else {}
    if doc.get('username') and doc['username'].lower() != me['username'].lower():
        raise ValueError(f'Credentials act as @{me["username"]}, but the recorded principal is @{doc["username"]}; '
                         'change principal.json by hand if the account is meant to change')
    doc.update(username=me['username'], account_id=str(me['id']),
               observed_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
               observed_by='GET /2/users/me with the publishing credentials')
    (ROOT / BASE / 'principal.json').write_text(json.dumps(doc, indent=2) + '\n')
    return doc


def approval_payload(post, who):
    """The exact bytes an approval signs: the action, the draft revision, its posts and the account."""
    return json.dumps({'action': 'publish', 'draft_id': post['id'], 'draft_revision': post['revision'],
                       'posts_sha256': digest(post['posts']),
                       'principal': {'username': who['username'].lower(), 'account_id': who.get('account_id')}},
                      sort_keys=True, separators=(',', ':')).encode()


def owner_signing_keys():
    """The owner's SSH signing keys as GitHub publishes them: a root of trust no repository write can change."""
    import urllib.request as ur
    req = ur.Request(f'https://api.github.com/users/{OWNER_LOGIN}/ssh_signing_keys',
                     headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'cubits11-distribute/1'})
    try:
        with ur.urlopen(req, timeout=20) as r:
            keys = [k['key'] for k in json.loads(r.read().decode())]
    except Exception as e:  # noqa: BLE001
        raise ValueError(f'Cannot read {OWNER_LOGIN}\'s SSH signing keys from GitHub ({e}); '
                         'the approval is unverifiable, so dispatch refuses')
    if not keys:
        raise ValueError(f'{OWNER_LOGIN} has no SSH signing key on GitHub; add one before approvals can be verified')
    return keys


def verify_approval(post, row):
    """Refuse unless the approval's signature verifies, for this payload, against the owner's keys."""
    import shutil, tempfile
    if not row.get('signature'):
        raise ValueError(f'The approval for {post["id"]} at {post["revision"][:12]} is unsigned. On the owner machine: '
                         f'distribute.py approve --draft-id {post["id"]} --basis "..." --sign-with ~/.ssh/<signing key>')
    if not shutil.which('ssh-keygen'):
        raise ValueError('ssh-keygen is needed to verify approvals')
    payload = approval_payload(post, principal())
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        (t / 'allowed_signers').write_text(''.join(f'{OWNER_LOGIN} namespaces="{NAMESPACE}" {k}\n'
                                                   for k in owner_signing_keys()))
        (t / 'approval.sig').write_text(row['signature'])
        r = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(t / 'allowed_signers'), '-I', OWNER_LOGIN,
                            '-n', NAMESPACE, '-s', str(t / 'approval.sig')], input=payload, capture_output=True)
    if r.returncode:
        why = r.stderr.decode().strip()[:200] or 'no key on the owner account made this signature'
        raise ValueError(f'The approval signature for {post["id"]} does not verify against {OWNER_LOGIN}\'s '
                         f'signing keys for this revision and account: {why}')


def sign_approval(post, key_path):
    """Owner-run: sign the approval payload with an SSH key; the key never leaves ssh-keygen or its agent."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        payload = pathlib.Path(tmp) / 'approval.json'
        payload.write_bytes(approval_payload(post, principal()))
        subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key_path), '-n', NAMESPACE, str(payload)], check=True)
        return (payload.parent / 'approval.json.sig').read_text()


def approve(draft_id, basis, signature=None, sign_with=None):
    posts = draft()
    verify(posts)
    post = next((p for p in posts if p['id'] == draft_id), None)
    if post is None:
        raise ValueError(f'Unknown draft: {draft_id}')
    if sign_with:
        signature = sign_approval(post, sign_with)
    rows = [a for a in records('approvals.json') if not (a['draft_id'] == draft_id and a['draft_revision'] == post['revision'])]
    row = {'draft_id': draft_id, 'draft_revision': post['revision'], 'basis': basis,
           'approved_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
           'posts_sha256': digest(post['posts'])}
    if signature:
        row['signature'] = signature
    rows.append(row)
    (ROOT / BASE / 'approvals.json').write_text(json.dumps(rows, indent=2) + '\n')
    if not signature:
        print('unsigned approval recorded: dispatch refuses it until it is signed with --sign-with', file=sys.stderr)
    return post


def dispatch_preconditions(post, dry_run=False):
    head = git('rev-parse', 'HEAD')
    if not dry_run:
        if git('status', '--porcelain'):
            raise ValueError('Dispatch revision must be a clean tree; commit first')
        if not git('branch', '-r', '--contains', head):
            raise ValueError('HEAD is not on any remote; push before publishing so the dispatch revision is public')
    verify(draft())
    row = approval_for(post)
    if row is None:
        raise ValueError(f'No approval recorded for {post["id"]} at revision {post["revision"][:12]}; run: distribute.py approve --draft-id {post["id"]} --basis "..."')
    principal()
    verify_approval(post, row)
    done = [r for r in records('publications.json') if r['draft_revision'] == post['revision']]
    if any(r.get('status') == 'PARTIAL' for r in done):
        raise ValueError(f'{post["id"]} at this revision was partially published; resolve the recorded PARTIAL '
                         'receipt by hand before any further dispatch')
    if done:
        raise ValueError(f'{post["id"]} at this revision is already published')
    return head


def publish(draft_id, dry_run=False):
    post = next((p for p in draft() if p['id'] == draft_id), None)
    if post is None:
        raise ValueError(f'Unknown draft: {draft_id}')
    head = dispatch_preconditions(post, dry_run)
    bodies = [{'text': t} for t in post['posts']]
    if dry_run:
        print(json.dumps({'draft_id': draft_id, 'revision': post['revision'], 'dispatch_revision': head,
                          'requests': [{'method': 'POST', 'path': '/tweets', 'body': b} for b in bodies],
                          'chaining': 'each body after the first gains reply.in_reply_to_tweet_id of the previous response id',
                          'credentials': 'not read in dry run',
                          'principal': principal()}, indent=2))
        return None
    creds = credentials()
    me = x_request('GET', '/users/me', creds)['data']
    check_principal(me, principal())
    ids = []

    def receipt(**extra):
        now = dt.datetime.now(dt.timezone.utc)
        row = {'post_id': ids[0], 'source_url': f'https://x.com/{me["username"]}/status/{ids[0]}',
               'draft_id': post['id'], 'draft_revision': post['revision'],
               'published_at': now.isoformat(timespec='seconds').replace('+00:00', 'Z'),
               'dispatch_revision': head, 'thread_post_ids': list(ids),
               'post_type': post['post_type'], 'audience': post['audience_hypothesis'], 'topic': post['topic'],
               'hook': post['hook'], 'visual': post['visual'], 'cta': post['cta'],
               'thread_structure': post['thread_structure'], 'time_slot': f'utc-{now.hour:02d}', **extra}
        rows = records('publications.json') + [row]
        validate_publications(rows, draft())
        (ROOT / BASE / 'publications.json').write_text(json.dumps(rows, indent=2) + '\n')
        return row

    try:
        for body in bodies:
            if ids:
                body['reply'] = {'in_reply_to_tweet_id': ids[-1]}
            ids.append(x_request('POST', '/tweets', creds, body=body)['data']['id'])
    except Exception as exc:
        # Posts already accepted are live. Record them before re-raising, so the
        # log never holds fewer posts than X does and the revision cannot be re-sent.
        if ids:
            receipt(status='PARTIAL', error=str(exc)[:300])
            print(f'PARTIAL: {len(ids)} of {len(bodies)} posts of {post["id"]} are live and recorded', file=sys.stderr)
        raise
    checks, ok = readback(ids, post['posts'], creds, me)
    row = receipt(readback=checks, readback_ok=ok)
    print(f'published {post["id"]} as {row["source_url"]} ({len(ids)} posts); '
          f'read-back {"matches the approved text" if ok else "DIFFERS or was not evaluated: see the receipt"}')
    return row


def canonical(text):
    return unicodedata.normalize('NFC', text).strip()


def observed_text(tweet):
    """What X stored, projected back onto what was sent.

    X rewrites every URL to a t.co link and escapes &, < and > in `text`, and a
    long post's full text is in `note_tweet`. Comparing raw bytes would call every
    post with a link or an ampersand a mismatch, so the t.co links are expanded
    from the post's own entities and the escapes are decoded first.
    """
    note = tweet.get('note_tweet') or {}
    text = note.get('text') or tweet.get('text', '')
    for u in (note.get('entities') or tweet.get('entities') or {}).get('urls', []):
        if u.get('url') and u.get('expanded_url'):
            text = text.replace(u['url'], u['expanded_url'])
    return canonical(html.unescape(text))


def readback(ids, approved, creds, me):
    """Fetch the posts back and compare each with its approved text; never fatal, always recorded."""
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    try:
        data = x_request('GET', '/tweets', creds,
                         query={'ids': ','.join(ids), 'tweet.fields': 'author_id,entities,note_tweet'}).get('data') or []
    except Exception as exc:  # noqa: BLE001
        return [{'status': 'UNEVALUATED', 'error': str(exc)[:200]}], False
    by_id = {t['id']: t for t in data}
    checks = []
    for ident, text in zip(ids, approved):
        t = by_id.get(ident)
        seen = observed_text(t) if t else None
        checks.append({'post_id': ident, 'approved_sha256': sha(canonical(text)),
                       'observed_sha256': sha(seen) if seen is not None else None,
                       'equal': seen == canonical(text),
                       'author_matches': bool(t) and str(t.get('author_id')) == str(me['id'])})
    return checks, all(c['equal'] and c['author_matches'] for c in checks)


def snapshot(post_id):
    """One cumulative metrics snapshot from the API, recorded as a sourced row."""
    creds = credentials()
    pubs = {p['post_id']: p for p in records('publications.json')}
    if post_id not in pubs:
        raise ValueError('Unknown post; snapshots attach only to recorded publications')
    data = x_request('GET', f'/tweets/{post_id}', creds,
                     query={'tweet.fields': 'public_metrics,non_public_metrics,organic_metrics'})['data']
    pub, org, non = data.get('public_metrics', {}), data.get('organic_metrics', {}), data.get('non_public_metrics', {})
    pick = lambda *srcs: next((s[k] for s, k in srcs if s.get(k) is not None), None)
    row = {'post_id': post_id, 'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
           'provider': 'x_api_v2', 'scope': 'organic' if org else 'total',
           'source': f'{API}/tweets/{post_id}', 'attribution': 'direct_post',
           'metrics': {'impressions': pick((org, 'impression_count'), (non, 'impression_count')),
                       'link_clicks': pick((org, 'url_link_clicks'), (non, 'url_link_clicks')),
                       'profile_visits': pick((org, 'user_profile_clicks'), (non, 'user_profile_clicks')),
                       'likes': pick((org, 'like_count'), (pub, 'like_count')),
                       'reposts': pick((org, 'retweet_count'), (pub, 'retweet_count')),
                       'replies': pick((org, 'reply_count'), (pub, 'reply_count')),
                       'bookmarks': pick((pub, 'bookmark_count')),
                       'engagements': None, 'follows': None}}
    rows = validate_metrics(records('metrics.json') + [row], list(pubs.values()))
    (ROOT / BASE / 'metrics.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(f'snapshot recorded for {post_id}: ' + json.dumps(row['metrics']))
    return row


WINDOWS = (24, 72, 168)   # hours; six-hour tolerance, as learn() selects


def due_windows(publications, snapshots, now=None):
    """Which (post_id, window) pairs are inside their capture tolerance and not yet captured."""
    now = now or dt.datetime.now(dt.timezone.utc)
    have = set()
    for row in snapshots:
        pub = next((p for p in publications if p['post_id'] == row['post_id']), None)
        if pub is None:
            continue
        age = (stamp(row['observed_at']) - stamp(pub['published_at'])).total_seconds() / 3600
        w = next((h for h in WINDOWS if h <= age < h + 6), None)
        if w:
            have.add((row['post_id'], w))
    due = []
    for pub in publications:
        age = (now - stamp(pub['published_at'])).total_seconds() / 3600
        for w in WINDOWS:
            if w <= age < w + 6 and (pub['post_id'], w) not in have:
                due.append({'post_id': pub['post_id'], 'window_h': w, 'age_h': round(age, 2)})
    return due


def replies(post_id):
    """Harvest the conversation under a recorded root post as an interaction ledger.

    Records ids, timestamps, author ids and a content digest — never the text of
    another person's reply. Classification (technical / other) is an owner act;
    the row carries `classification: null` until then, and only an owner-classified
    technical row may later be counted toward the stop rule in outcomes.yaml.
    """
    creds = credentials()
    pubs = {p['post_id']: p for p in records('publications.json')}
    if post_id not in pubs:
        raise ValueError('Unknown post; replies attach only to recorded publications')
    own = set(pubs[post_id].get('thread_post_ids', [post_id]))
    me = x_request('GET', '/users/me', creds)['data']['id']
    data = x_request('GET', '/tweets/search/recent', creds,
                     query={'query': f'conversation_id:{post_id}', 'max_results': 100,
                            'tweet.fields': 'author_id,created_at,in_reply_to_user_id,referenced_tweets'}).get('data', [])
    old = records('interactions.json')
    seen = {r['reply_id'] for r in old}
    new = []
    for t in data:
        if t['id'] in own or t['id'] in seen or t.get('author_id') == me:
            continue
        new.append({'reply_id': t['id'], 'root_post_id': post_id, 'author_id': t['author_id'],
                    'created_at': t['created_at'], 'content_sha256': hashlib.sha256(t['text'].encode()).hexdigest(),
                    'source': f'https://x.com/i/status/{t["id"]}', 'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                    'classification': None, 'note': 'owner classifies; text is not stored'})
    (ROOT / BASE / 'interactions.json').write_text(json.dumps(old + new, indent=2) + '\n')
    print(f'{len(new)} new interaction(s) recorded under {post_id}; {len(old) + len(new)} total, '
          f'{sum(1 for r in old + new if r["classification"] is None)} unclassified')
    return new


def cycle():
    """One unattended pass: capture every due snapshot, harvest replies for every recorded post."""
    pubs = records('publications.json')
    due = due_windows(pubs, records('metrics.json'))
    for d in due:
        snapshot(d['post_id'])
    for p in pubs:
        replies(p['post_id'])
    print(f'cycle: {len(due)} snapshot(s) captured, {len(pubs)} conversation(s) harvested')


def build():
    posts = draft()
    # Working-tree previews must be reviewable. Approval and dispatch continue
    # to call strict verify() and cannot consume pending source bindings.
    verify(posts, allow_pending=True)
    pubs, metrics = records('publications.json'), records('metrics.json')
    validate_publications(pubs, posts)
    report = learn(pubs, metrics)
    report['traffic_context'] = validate_traffic(records('traffic.json'))
    report['qualified_outcomes'] = {k: len(v) for k, v in read('distribution/outcomes.yaml')['qualified'].items()}
    return {'events.json': extract(), 'drafts.json': posts,
            'queue.json': {'mode': 'approved_revisions_dispatch_via_publish_stage',
                           'publishing_enabled': 'publish stage; environment credentials; refuses without a clean, pushed tree and a matching approval',
                           'required_before_dispatch': ['full verification_manifest exit 0 at dispatch revision', 'owner content approval recorded in approvals.json for the exact revision', 'platform credentials in the environment', 'film cold test if attaching media'],
                           'items': [{**p, 'approval': approval_for(p)} for p in posts if not any(r['draft_revision'] == p['revision'] for r in pubs)]},
            'dashboard.json': report,
            'experiments.json': {'roles': ROLES, 'factors': list(DIMS),
                                 'status': 'proposed_no_observations' if not pubs else f'{len(pubs)} publication(s); baseline pending until a 24-hour snapshot exists',
                                 'deviations': records('deviations.json'),
                                 'interactions': {'recorded': len(records('interactions.json')),
                                                  'unclassified': sum(1 for r in records('interactions.json') if r['classification'] is None),
                                                  'rule': 'owner-classified technical interactions may enter outcomes.yaml; nothing here counts automatically'},
                                 'primary': 'verified independent reproduction or correction',
                                 'secondary': '24-hour link CTR', 'design': 'Sequential pilot; vary hook only after baseline; no causal effect claim',
                                 'stop_rule': read('distribution/outcomes.yaml')['stop_rule']}}


def dashboard(data):
    report = data['dashboard.json']
    esc = lambda x: html.escape(str(x))
    rows = ''.join('<article><h2>' + esc(p['id']) + ' · held for owner review</h2><p>' + esc(p['audience_hypothesis']) + '</p><p>' + esc(p['why']) + '</p><ol>' + ''.join('<li>' + esc(t) + '</li>' for t in p['posts']) + '</ol></article>' for p in data['drafts.json'])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Research distribution</title><style>body{max-width:960px;margin:40px auto;padding:20px;background:#101b22;color:#e5edf2;font:18px/1.6 system-ui}article{border-top:1px solid #548090;padding:20px 0}li{margin:14px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><a class="skip" href="#main">Skip to content</a><main id="main"><h1>Research → evidence → audience</h1><p>' + esc(report['publication_count']) + ' recorded publications · ' + esc(report['snapshot_count']) + ' sourced metric snapshots</p><p>' + esc(report['audience_model']) + '</p><p>' + esc(report['unavailable']) + '</p><p>Metric coverage: ' + ', '.join(esc(m) for m in METRICS) + ' — reported only where a source supplies the field.</p><h2>Next experiment</h2><p>' + esc(report['next_experiment']) + '</p>' + rows + '<h2>Timestamped observations and window comparisons</h2><pre>' + esc(json.dumps({'observations': report['observations'], 'comparisons': report['comparisons'], 'traffic_context': report['traffic_context'], 'qualified_outcomes': report['qualified_outcomes']}, indent=2)) + '</pre></main></html>\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['run', 'orient', 'extract', 'draft', 'verify', 'queue', 'ingest', 'learn', 'approve', 'publish', 'snapshot', 'due', 'replies', 'cycle', 'principal'], nargs='?', default='run')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--draft-id')
    ap.add_argument('--basis', help='approve: who approved and on what record')
    ap.add_argument('--sign-with', type=pathlib.Path, help='approve: an SSH signing key registered on the owner GitHub account')
    ap.add_argument('--signature', type=pathlib.Path, help='approve: an ssh-keygen -Y signature file made over the approval payload')
    ap.add_argument('--dry-run', action='store_true', help='publish: print the exact requests; read no credentials')
    ap.add_argument('--post-id', help='snapshot: the recorded root post id')
    ap.add_argument('--at', help='Proposed timezone-qualified slot; never schedules on X')
    ap.add_argument('--input', type=pathlib.Path)
    ap.add_argument('--kind', choices=['metrics', 'publications', 'traffic'], default='metrics')
    a = ap.parse_args()
    if a.stage == 'approve':
        if not (a.draft_id and a.basis):
            ap.error('approve requires --draft-id and --basis')
        post = approve(a.draft_id, a.basis, signature=a.signature.read_text() if a.signature else None,
                       sign_with=a.sign_with)
        print(f'approved {post["id"]} at revision {post["revision"][:12]}; regenerating the bundle')
    if a.stage == 'publish':
        if not a.draft_id:
            ap.error('publish requires --draft-id')
        publish(a.draft_id, dry_run=a.dry_run)
        if a.dry_run:
            return 0
    if a.stage == 'principal':
        who = observe_principal()
        print(f'principal recorded: @{who["username"]} ({who["account_id"]})')
        return 0
    if a.stage == 'snapshot':
        if not a.post_id:
            ap.error('snapshot requires --post-id')
        snapshot(a.post_id)
    if a.stage == 'due':
        due = due_windows(records('publications.json'), records('metrics.json'))
        print(json.dumps(due, indent=2) if due else 'no snapshot window is open right now')
        return 0
    if a.stage == 'replies':
        if not a.post_id:
            ap.error('replies requires --post-id')
        replies(a.post_id)
    if a.stage == 'cycle':
        cycle()
    if a.at:
        if a.stage != 'queue' or a.draft_id not in {p['id'] for p in draft()}:
            ap.error('--at requires queue --draft-id with a known draft')
        stamp(a.at)
        proposals = [r for r in records('schedule.json') if r['draft_id'] != a.draft_id]
        proposals.append({'draft_id': a.draft_id, 'scheduled_at': a.at})
        (ROOT / BASE / 'schedule.json').write_text(json.dumps(proposals, indent=2) + '\n')
    if a.stage == 'ingest':
        if not a.input:
            ap.error('ingest requires --input JSON receipt')
        incoming = json.loads(a.input.read_text())
        old = records(a.kind + '.json')
        new = old + [r for r in incoming if r not in old]
        if a.kind == 'publications':
            validate_publications(new, draft())
        elif a.kind == 'traffic':
            validate_traffic(new)
        else:
            validate_metrics(new, records('publications.json'))
        (ROOT / BASE / (a.kind + '.json')).write_text(json.dumps(new, indent=2) + '\n')
    data = build()
    pending = sorted({e['source']['path'] for e in data['events.json'] if e['source']['binding'] != 'committed'})
    if pending and not a.check:
        print('PREVIEW: pending source bindings; approval and dispatch still refuse. Commit sources and regenerate for release.')
    if not a.check and a.stage not in ('verify', 'orient'):
        history = records('draft-history.json')
        for post in data['drafts.json']:
            if not any(p['revision'] == post['revision'] for p in history):
                history.append(post)
        (ROOT / BASE / 'draft-history.json').write_text(json.dumps(history, indent=2) + '\n')
    if a.stage == 'orient':
        print(json.dumps(data['dashboard.json'], indent=2))
        return 0
    if a.stage == 'verify' and not a.check:
        saved = records('drafts.json')
        verify(saved)
        print('ok: exact-source drafts and local pins; remote release gates still required before dispatch')
        return 0
    data['dashboard.html'] = dashboard(data)
    data['manifest.json'] = {'version': 1, 'generator': 'scripts/distribute.py',
                             'outputs': {name: digest(value) for name, value in data.items()},
                             'gate': 'python3 scripts/distribute.py --check',
                             'publishing': 'publish stage under owner approval (approvals.json) and environment credentials; owner decision 2026-09-07'}
    for name, value in data.items():
        target = ROOT / BASE / name
        content = value if isinstance(value, str) else json.dumps(value, indent=2, default=str) + '\n'
        if a.check:
            if not target.exists() or target.read_text() != content:
                raise ValueError('Generated distribution drift: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    if not a.check and a.stage in ('run', 'ingest', 'queue', 'approve', 'publish', 'snapshot', 'replies', 'cycle'):
        subprocess.run([sys.executable, 'scripts/repo_graph.py', '--no-drift'], cwd=ROOT, check=True)
    print('ok: orient → extract → draft → verify → queue → ingest → learn; publish only for approved revisions')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, StopIteration) as exc:
        print('HOLD:', exc, file=sys.stderr)
        raise SystemExit(1)
