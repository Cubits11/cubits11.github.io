#!/usr/bin/env python3
"""Freeze what an MCP server actually offers, and check later that it has not changed.

Documentation says what a server should expose; the server says what it does. This
starts an MCP server over stdio and asks it for every tool. It records each tool's
name, schema and the server's own read-only and destructive hints, and hashes the
set. From that inventory it writes Claude Code permission rules: read-only tools by
name in `allow`, everything else by name in `deny` (or `ask`, with --writes ask). A
tool with no read-only hint counts as a write. With --compare it exits 1 if the
live inventory differs from a frozen one.

Writes default to `deny` because CLAUDE.md admits one path for acting on X:
scripts/distribute.py publish, with an owner-signed approval and a recorded
receipt. A write approved at a prompt would leave neither.

The command runs as the owner, on the owner's machine, with whatever credentials
the server holds. The inventory records no environment and no credential.

  python3 scripts/x_mcp_inventory.py --server xapi --out distribution/x/xapi-inventory.json -- xurl mcp
  python3 scripts/x_mcp_inventory.py --server xapi --compare distribution/x/xapi-inventory.json -- xurl mcp
"""
import os
import sys
if __name__ == '__main__':
    # The server this starts can reach the owner's X token; see the same guard in distribute.py.
    _repo = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    sys.path[:] = [p for p in sys.path if 'site-packages' in p
                   or not (os.path.realpath(p or os.curdir) + os.sep).startswith(_repo + os.sep)]
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import queue
import subprocess
import threading
import time

PROTOCOL = '2025-06-18'


class Session:
    """One MCP client session over a child process's stdin and stdout; each answer must arrive within `timeout`."""

    def __init__(self, argv, timeout):
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.timeout, self.n, self.lines = timeout, 0, queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.p.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def request(self, method, params=None):
        self.n += 1
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params or {}}) + '\n')
        self.p.stdin.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                line = self.lines.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                raise SystemExit(f'no answer to {method} within {self.timeout}s')
            if line is None:
                raise SystemExit(f'the server closed its output before answering {method}')
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                raise SystemExit(f'the server wrote a line that is not JSON-RPC while answering {method}')
            if msg.get('id') == self.n and 'method' not in msg:
                if 'error' in msg:
                    raise SystemExit(f'{method} failed: {msg["error"]}')
                return msg['result']

    def notify(self, method):
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': method}) + '\n')
        self.p.stdin.flush()

    def close(self):
        self.p.stdin.close()
        try:
            self.p.wait(self.timeout)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            self.p.wait()
        self.p.stdout.close()


def capture(argv, timeout=120):
    s = Session(argv, timeout)
    try:
        init = s.request('initialize', {'protocolVersion': PROTOCOL, 'capabilities': {},
                                        'clientInfo': {'name': 'glassroot-inventory', 'version': '1'}})
        s.notify('notifications/initialized')
        tools, cursor = [], None
        while True:
            page = s.request('tools/list', {'cursor': cursor} if cursor else {})
            tools += page.get('tools', [])
            cursor = page.get('nextCursor')
            if not cursor:
                break
    finally:
        s.close()
    keep = ('name', 'title', 'description', 'inputSchema', 'outputSchema', 'annotations')
    tools = sorted(({k: t[k] for k in keep if k in t} for t in tools), key=lambda t: t['name'])
    return {'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            'command': [pathlib.Path(argv[0]).name, *argv[1:]],
            'protocol_version': init.get('protocolVersion'), 'server_info': init.get('serverInfo'),
            'tools_sha256': hashlib.sha256(json.dumps(tools, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'tools': tools}


def is_read_only(tool):
    """Only the server's own readOnlyHint makes a tool a read. No hint, or any other value, is a write."""
    return (tool.get('annotations') or {}).get('readOnlyHint') is True


def permissions(server, inventory, writes='deny'):
    reads = [t['name'] for t in inventory['tools'] if is_read_only(t)]
    rest = [t['name'] for t in inventory['tools'] if not is_read_only(t)]
    return {'permissions': {'allow': [f'mcp__{server}__{n}' for n in reads],
                            writes: [f'mcp__{server}__{n}' for n in rest]},
            'note': ('Merge into ~/.claude/settings.json. These rules name the tools frozen at capture. A tool the '
                     'server adds later matches no rule here and falls to the session permission mode, so re-run '
                     'with --compare after any update to the server or its bridge.'),
            'inventory_sha256': inventory['tools_sha256']}


def compare(frozen, live):
    old = {t['name']: t for t in frozen['tools']}
    new = {t['name']: t for t in live['tools']}
    return {'added': sorted(set(new) - set(old)), 'removed': sorted(set(old) - set(new)),
            'changed': sorted(n for n in set(old) & set(new) if old[n] != new[n])}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--server', required=True, help='the MCP server name used in the client config, e.g. xapi')
    ap.add_argument('--out', type=pathlib.Path, help='write the inventory here, and the permission rules beside it')
    ap.add_argument('--compare', type=pathlib.Path, help='a frozen inventory to compare the live one against')
    ap.add_argument('--writes', choices=('deny', 'ask'), default='deny',
                    help='the rule for every tool the server does not mark read-only (default: deny)')
    ap.add_argument('--timeout', type=int, default=120, help='seconds to wait for each answer')
    ap.add_argument('command', nargs=argparse.REMAINDER, help='-- then the command that starts the server')
    a = ap.parse_args(argv)
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd:
        ap.error('give the server command after --')
    live = capture(cmd, a.timeout)
    reads = sum(is_read_only(t) for t in live['tools'])
    print(f'{len(live["tools"])} tools ({reads} read-only by the server\'s own hint); sha256 {live["tools_sha256"]}',
          file=sys.stderr)
    if a.compare:
        diff = compare(json.loads(a.compare.read_text()), live)
        print(json.dumps(diff, indent=2))
        return 1 if any(diff.values()) else 0
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(live, indent=2) + '\n')
        rules = a.out.with_name(a.out.stem + '.permissions.json')
        rules.write_text(json.dumps(permissions(a.server, live, a.writes), indent=2) + '\n')
        print(f'wrote {a.out} and {rules}', file=sys.stderr)
    else:
        print(json.dumps(live, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
