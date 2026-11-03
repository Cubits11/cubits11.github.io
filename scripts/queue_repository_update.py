#!/usr/bin/env python3
"""Queue a verified local cycle commit through protected-main review and CI.

This never dispatches outreach or edits evidence, and it never enables
auto-merge: the owner merges after the repository's required checks.
"""
import argparse
import json
import subprocess
import urllib.error
import urllib.request

REPOSITORY = 'Cubits11/cubits11.github.io'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def request(path, payload):
    credential = subprocess.run(['git', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\n\n', text=True, capture_output=True, check=True)
    fields = dict(line.split('=', 1) for line in credential.stdout.splitlines() if '=' in line)
    token = fields.get('password')
    if not token:
        raise RuntimeError('GitHub credential unavailable; commit remains local')
    req = urllib.request.Request('https://api.github.com' + path,
        data=json.dumps(payload).encode(), headers={
            'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'GitHub refused repository update: HTTP {exc.code}') from None
    if result.get('errors'):
        raise RuntimeError('GitHub refused the pull request; the commit remains on its branch')
    return result


def queue(branch):
    if not branch.startswith('claude/cycle-'):
        raise ValueError('only generated cycle branches may be queued')
    if git('branch', '--show-current') != branch or git('status', '--porcelain'):
        raise ValueError('queue requires its clean cycle branch')
    origin = git('remote', 'get-url', '--push', 'origin').lower()
    if origin not in ('https://github.com/cubits11/cubits11.github.io.git',
                       'git@github.com:cubits11/cubits11.github.io.git'):
        raise ValueError('unexpected publication remote')
    git('push', '-u', 'origin', 'HEAD:refs/heads/' + branch)
    pr = request('/repos/' + REPOSITORY + '/pulls', {
        'title': git('log', '-1', '--format=%s'), 'head': branch, 'base': 'main',
        'body': 'Append the scheduled observations and refresh their derived views. '
                'The local verification manifest passed before this commit. '
                'Missing observations remain missing. Required CI checks gate the merge.'})
    print('Queued repository update: ' + pr['html_url'])
    git('checkout', 'main')
    print('Pull request opened for the owner to merge; returned to main')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('branch')
    queue(parser.parse_args().branch)
