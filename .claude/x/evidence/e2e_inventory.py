#!/usr/bin/env python3
"""End-to-end: scripts/x_mcp_inventory.py -> the real xurl v1.3.2 bridge -> a local stand-in for api.x.com/mcp.

Usage: e2e_inventory.py <xurl binary> <checkout> <workdir>
Nothing leaves localhost. The token in the throwaway HOME is a fixture string.
"""
import http.server, json, os, pathlib, subprocess, sys, threading

XURL, CHECKOUT, WORK = map(lambda p: pathlib.Path(p).resolve(), sys.argv[1:4])
WORK.mkdir(parents=True, exist_ok=True)
SEEN = {'auth': set(), 'session': set(), 'methods': []}
EXTRA = []   # tools added for the drift run

PAGE1 = [{'name': 'searchPostsRecent', 'description': 'fixture read', 'inputSchema': {'type': 'object'},
          'annotations': {'readOnlyHint': True}},
         {'name': 'getUsersMe', 'description': 'fixture read', 'inputSchema': {'type': 'object'},
          'annotations': {'readOnlyHint': True, 'openWorldHint': True}}]
PAGE2 = [{'name': 'createArticle', 'description': 'fixture write', 'inputSchema': {'type': 'object'},
          'annotations': {'readOnlyHint': False, 'destructiveHint': False}},
         {'name': 'deletePost', 'description': 'fixture tool with no hints', 'inputSchema': {'type': 'object'}}]


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        SEEN['auth'].add(self.headers.get('Authorization'))
        if self.headers.get('Mcp-Session-Id'):
            SEEN['session'].add(self.headers['Mcp-Session-Id'])
        msg = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        SEEN['methods'].append(msg.get('method'))
        if 'id' not in msg:
            self.send_response(202); self.end_headers(); return
        if msg['method'] == 'initialize':
            body = {'jsonrpc': '2.0', 'id': msg['id'], 'result': {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}},
                                                                 'serverInfo': {'name': 'x-mcp-standin', 'version': '0'}}}
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Mcp-Session-Id', 'sess-fixture-1'); self.end_headers()
            self.wfile.write(json.dumps(body).encode()); return
        if msg['method'] == 'tools/list':
            cursor = (msg.get('params') or {}).get('cursor')
            if not cursor:
                body = {'jsonrpc': '2.0', 'id': msg['id'], 'result': {'tools': PAGE1, 'nextCursor': 'p2'}}
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(json.dumps(body).encode()); return
            body = {'jsonrpc': '2.0', 'id': msg['id'], 'result': {'tools': PAGE2 + EXTRA}}
            self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
            self.wfile.write(b'event: message\ndata: ' + json.dumps(body).encode() + b'\n\n'); return
        self.send_response(404); self.end_headers()

    def do_GET(self):
        self.send_response(405); self.end_headers()

    def do_DELETE(self):
        self.send_response(200); self.end_headers()


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_address[1]}/mcp'

home = WORK / 'home'
(home / '.xurl').mkdir(parents=True, exist_ok=True)
(home / '.xurl' / 'auth.yml').write_text(
    'apps:\n  default:\n    client_id: fixture-client\n    client_secret: fixture-secret\n    default_user: fixture\n'
    '    oauth2_tokens:\n      fixture:\n        type: oauth2\n        oauth2:\n'
    '          access_token: FAKE-ACCESS-TOKEN-FIXTURE\n          refresh_token: FAKE-REFRESH\n'
    '          expiration_time: 4102444800\ndefault_app: default\n')
os.chmod(home / '.xurl' / 'auth.yml', 0o600)
env = {**os.environ, 'HOME': str(home)}
for k in ('CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI'):
    env.pop(k, None)

inv_py = CHECKOUT / 'scripts' / 'x_mcp_inventory.py'
out = WORK / 'xapi-inventory.json'
r1 = subprocess.run([sys.executable, str(inv_py), '--server', 'xapi', '--out', str(out), '--', str(XURL), 'mcp', url],
                    env=env, capture_output=True, text=True, timeout=120)
inv = json.loads(out.read_text()) if out.exists() else None
rules = json.loads(out.with_name('xapi-inventory.permissions.json').read_text()) if out.exists() else None

r2 = subprocess.run([sys.executable, str(inv_py), '--server', 'xapi', '--compare', str(out), '--', str(XURL), 'mcp', url],
                    env=env, capture_output=True, text=True, timeout=120)
EXTRA.append({'name': 'sendDirectMessage', 'description': 'added after the freeze', 'inputSchema': {'type': 'object'}})
r3 = subprocess.run([sys.executable, str(inv_py), '--server', 'xapi', '--compare', str(out), '--', str(XURL), 'mcp', url],
                    env=env, capture_output=True, text=True, timeout=120)
srv.shutdown()

result = {
    'xurl': subprocess.run([str(XURL), 'version'], capture_output=True, text=True).stdout.strip(),
    'capture_rc': r1.returncode, 'capture_stderr_tail': r1.stderr.strip().splitlines()[-2:],
    'tools': [t['name'] for t in inv['tools']] if inv else None,
    'tools_sha256': inv and inv['tools_sha256'],
    'allow': rules and rules['permissions']['allow'], 'deny': rules and rules['permissions']['deny'],
    'bridge_sent_authorization': sorted(a for a in SEEN['auth'] if a),
    'bridge_echoed_session': sorted(SEEN['session']),
    'methods_seen': SEEN['methods'],
    'compare_unchanged_rc': r2.returncode, 'compare_unchanged_diff': json.loads(r2.stdout) if r2.stdout.strip() else r2.stderr[-300:],
    'compare_drift_rc': r3.returncode, 'compare_drift_diff': json.loads(r3.stdout) if r3.stdout.strip() else r3.stderr[-300:],
    'inventory_holds_no_token': inv is not None and 'FAKE-ACCESS' not in out.read_text(),
}
print(json.dumps(result, indent=1))
