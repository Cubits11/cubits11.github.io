#!/usr/bin/env python3
"""The X gate: the one process that holds the X credentials, reached through four typed MCP tools.

A model connected to this server can list drafts and their approval state, see the
exact requests a dispatch would send, record due metrics and replies, and publish
an approved revision. It cannot read the credentials. This process reads them from
the owner-only file X_CREDENTIALS_FILE names, only when a tool needs them, and no
tool returns them.

Every check is in scripts/distribute.py:
- the recorded principal;
- the owner's signature on the approval;
- a clean and pushed tree;
- no earlier or partial publication.
This file adds one more: `x_publish` must name the revision it means, so a draft
that changed after the caller read it is refused before anything is sent.

Passing a path rather than the values keeps the secrets out of the MCP client's
environment, and so out of its shell and its other servers. The model's own tools
must not read the file either: deny it in user settings, as .claude/x/README.md
shows.

A session can also write anywhere in the repository, so this process imports
nothing from it by name. Every repository directory leaves sys.path before the
first import, and distribute.py is compiled from its source text, so no cached
bytecode is read. Start the gate with a Python whose packages, PyYAML among them,
are installed outside the repository. .claude/x/mcp-servers.json also starts it only
when this file and distribute.py match origin/main.

Run by an MCP client over stdio, for example:
  {"command": "/usr/bin/python3", "args": ["scripts/x_gate_mcp.py"],
   "env": {"X_CREDENTIALS_FILE": "~/.config/glassroot/x-credentials"}}
"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)


def inside_repo(path):
    real = os.path.realpath(path or os.curdir)
    return real == REPO or real.startswith(REPO + os.sep)


# os and sys are loaded before a script starts, so importing them searched nothing.
# X_GATE_TEST_REPO_PACKAGES keeps a virtualenv inside the repository importable for
# the test suite; the owner's MCP configuration does not set it.
TESTING = os.environ.get('X_GATE_TEST_REPO_PACKAGES') == '1'
sys.path[:] = [p for p in sys.path if not inside_repo(p) or (TESTING and 'site-packages' in p)]
if inside_repo(sys.prefix) and not TESTING:
    sys.exit('x-gate: this Python is a virtualenv inside the repository, and its pyvenv.cfg, which a session '
             'can edit, decides where the standard library is loaded from; start the gate with a Python outside it.')

import contextlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import types  # noqa: E402


def load(name):
    path = os.path.join(HERE, name + '.py')
    module = types.ModuleType(name)
    module.__file__ = path
    sys.modules[name] = module
    with open(path, encoding='utf-8') as f:
        exec(compile(f.read(), path, 'exec'), module.__dict__)
    return module


try:
    d = load('distribute')
except ImportError as exc:
    sys.exit(f'x-gate: {exc}. The gate imports nothing from inside the repository; start it with a Python '
             'whose packages, PyYAML among them, are installed outside it.')

PROTOCOL = '2025-06-18'
DRAFT = {'draft_id': {'type': 'string', 'description': 'a draft id from x_gate_status'}}
TOOLS = [
    {'name': 'x_gate_status',
     'description': 'Current drafts, whether each is approved and signed, whether it was published, the recorded '
                    'principal, and whether this gate holds credentials. Sends nothing to X.',
     'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
     'annotations': {'readOnlyHint': True, 'openWorldHint': False}},
    {'name': 'x_publish_dry_run',
     'description': 'The exact requests a dispatch of this draft would send, after every precondition that needs '
                    'no X credential, including the owner signature on the approval. Sends nothing to X.',
     'inputSchema': {'type': 'object', 'properties': DRAFT, 'required': ['draft_id'], 'additionalProperties': False},
     'annotations': {'readOnlyHint': True, 'openWorldHint': True}},
    {'name': 'x_cycle',
     'description': 'Capture every metrics snapshot now due and harvest replies under every recorded post, '
                    'appending sourced rows to metrics.json and interactions.json. Sends only GET requests to X.',
     'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
     'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': False,
                     'openWorldHint': True}},
    {'name': 'x_publish',
     'description': 'Publish an approved, owner-signed draft revision as the recorded principal. Public and not '
                    'reversible from here. Refuses unless `revision` (at least 12 hex characters) is a prefix of '
                    "the draft's current revision.",
     'inputSchema': {'type': 'object',
                     'properties': {**DRAFT, 'revision': {'type': 'string', 'minLength': 12,
                                                          'description': 'the revision the caller reviewed'}},
                     'required': ['draft_id', 'revision'], 'additionalProperties': False},
     'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': False,
                     'openWorldHint': True}},
]


def status(_args):
    pubs = d.records('publications.json')
    try:
        who = d.principal()
    except ValueError as exc:
        who = {'error': str(exc)}
    drafts = []
    for post in d.draft():
        row = d.approval_for(post)
        drafts.append({'draft_id': post['id'], 'revision': post['revision'],
                       'approved': row is not None, 'signed': bool(row and row.get('signature')),
                       'published': [r.get('status', 'COMPLETE') for r in pubs if r['draft_revision'] == post['revision']]})
    try:
        d.credentials()
        problem = None
    except ValueError as exc:
        problem = str(exc)  # names what is missing or wrong, never a value
    return {'principal': who, 'credentials_held': problem is None, 'credentials_problem': problem, 'drafts': drafts}


def cycle(_args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        d.cycle()
    return {'log': out.getvalue().strip().splitlines()}


def dry_run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        d.publish(args['draft_id'], dry_run=True)
    return json.loads(out.getvalue())


def publish(args):
    draft_id, revision = args['draft_id'], str(args.get('revision', ''))
    post = next((p for p in d.draft() if p['id'] == draft_id), None)
    if post is None:
        raise ValueError(f'Unknown draft: {draft_id}')
    if len(revision) < 12 or not post['revision'].startswith(revision):
        raise ValueError(f'The current revision of {draft_id} is {post["revision"][:12]}, not the {revision[:12] or "(none)"} '
                         'you named; nothing was sent')
    with contextlib.redirect_stdout(io.StringIO()):
        return d.publish(draft_id)


HANDLERS = {'x_gate_status': status, 'x_publish_dry_run': dry_run, 'x_cycle': cycle, 'x_publish': publish}


def call(params):
    name, args = params.get('name'), params.get('arguments') or {}
    if name not in HANDLERS:
        return {'content': [{'type': 'text', 'text': f'unknown tool {name}'}], 'isError': True}
    try:
        result = HANDLERS[name](args)
    except (ValueError, KeyError, StopIteration) as exc:
        return {'content': [{'type': 'text', 'text': f'HOLD: {exc}'}], 'isError': True}
    return {'content': [{'type': 'text', 'text': json.dumps(result, indent=2, default=str)}], 'isError': False}


def handle(msg):
    method, ident = msg.get('method'), msg.get('id')
    if ident is None:
        return None  # a notification needs no reply
    if method == 'initialize':
        result = {'protocolVersion': (msg.get('params') or {}).get('protocolVersion', PROTOCOL),
                  'capabilities': {'tools': {'listChanged': False}},
                  'serverInfo': {'name': 'glassroot-x-gate', 'version': '1'}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': TOOLS}
    elif method == 'tools/call':
        result = call(msg.get('params') or {})
    else:
        return {'jsonrpc': '2.0', 'id': ident, 'error': {'code': -32601, 'message': f'method not found: {method}'}}
    return {'jsonrpc': '2.0', 'id': ident, 'result': result}


def main():
    out = sys.stdout  # the JSON-RPC channel; tool code never writes to it
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}}
        else:
            reply = handle(msg) if isinstance(msg, dict) else {
                'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'batches are not supported'}}
        if reply is not None:
            out.write(json.dumps(reply) + '\n')
            out.flush()


if __name__ == '__main__':
    main()
