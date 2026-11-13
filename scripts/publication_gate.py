#!/usr/bin/env python3
"""Check the title and phone-film records before the deployment job publishes.

The five-reader approval requirement was retired by owner decision on
2026-11-13 (publication/readiness.json, `reader_test`). This gate no longer
reads reader records, and nothing replaces them. It checks the published
title attestation and every film's phone receipt; it does not establish that
any reader understands the site. Ordinary consistency CI runs this gate's unit
tests; the deployment job runs the actual gate.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'films'))
import facts_digest  # noqa: E402

TITLE = 'What AI Guardrail Scores Cannot Tell You'
# Files a receipt binds whole; the facts it read are bound by facts_subset (facts_digest.py).
REQUIRED_INPUTS = ('film.html','films/lib/film.js','films/lib/tokens.css')


class Blocked(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Blocked(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def confined(root, relative):
    need(isinstance(relative,str) and bool(relative), 'an evidence path is absent')
    path=(root/relative).resolve()
    need(path.is_relative_to(root.resolve()), f'evidence path escapes its artifact directory: {relative}')
    return path


def text(value):
    return isinstance(value,str) and bool(value.strip())


def number(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def dated(value):
    try:
        dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return True
    except (AttributeError,ValueError,TypeError):
        return False


def title_check(root, ready, source_root=None):
    t=ready['title']
    need(t['target']==TITLE and t['project']=='Cubits11/ghost-visualizer' and t['source_status']=='prepared_local', 'precise title source preparation is missing')
    patch=confined(root,t['patch'])
    need(sha(patch)==t['patch_sha256'], 'external title patch changed or is missing')
    patch_text=patch.read_text()
    need('+    <title>'+TITLE+'</title>' in patch_text and '+          <h1>'+TITLE+'</h1>' in patch_text,
         'reviewable title patch does not change both visible H1 and document title')
    need(set(t['source_sha256'])=={'index.html','src/components/CinematicShell.tsx','README.md','docs/ghost-visualizer-repository-vision.md'}
         and all(re.fullmatch('[0-9a-f]{64}',v or '') for v in t['source_sha256'].values()), 'prepared title source hashes are incomplete')
    if source_root is not None:
        for name,value in t['source_sha256'].items():
            need(sha(confined(source_root,name))==value, f'prepared external title source drifted: {name}')
    application=t['public_application']
    need(application['status']=='owner_verified_published', 'external title is prepared locally; public title application is still pending')
    revision=application['revision']
    need(isinstance(revision,str) and re.fullmatch('[0-9a-f]{40}',revision) and revision!=t['base_revision'], 'published title needs a new immutable external revision')
    need(application['source_url']==f'https://github.com/Cubits11/ghost-visualizer/commit/{revision}', 'published title source URL is not bound to its revision')
    need(application['verified_title']==application['verified_h1']==TITLE, 'published document title and visible H1 need exact inspection records')
    need(all(application['verified_source_sha256'].get(k)==t['source_sha256'][k] for k in ('index.html','src/components/CinematicShell.tsx')), 'published title sources differ from the prepared title sources')
    need(text(application['verified_by']) and dated(application['verified_on']), 'published title inspection needs a named owner attestation and date')


def phone_receipts(root):
    curation=read(root/'films/curation.json')['films']
    slugs={p.parent.name for p in (root/'films').glob('*/manifest.yaml')}
    need(len(curation)==12 and set(curation)==slugs, 'all twelve film compositions must be accounted for')
    facts=read(root/facts_digest.FILE)['facts']
    receipts={}
    for slug,entry in curation.items():
        need(entry.get('phone_composition') is True, f'{slug}: phone composition is unfinished')
        folder=root/'films'/slug
        manifest=yaml.safe_load((folder/'manifest.yaml').read_text())
        formats=manifest['render']['formats']
        fmt='vertical' if 'vertical' in formats else 'square' if 'square' in formats else None
        need(fmt is not None, f'{slug}: no declared phone format')
        path=folder/'renders'/f'{slug}__{fmt}.receipt.json'
        receipt=read(path)
        need(receipt['film']==slug and receipt['format']==fmt and receipt['width']==1080
             and receipt['height']==(1920 if fmt=='vertical' else 1080), f'{slug}: phone receipt identity or dimensions differ')
        audit=receipt.get('phone_text') or {}
        need(audit.get('media_width_css_px')==280 and number(audit.get('minimum_css_px'))
             and audit['minimum_css_px']>=14-1e-6 and number(audit.get('minimum_canvas_px'))
             and abs(audit['minimum_canvas_px']*280/receipt['width']-audit['minimum_css_px'])<=1e-6
             and type(audit.get('audited_draws')) is int and audit['audited_draws']>0,
             f'{slug}: receipt lacks a passing 14px text audit at 280px media width')
        need(receipt['determinism']['identical'] is True and receipt['text_overflows']==[], f'{slug}: render failed determinism or text bounds')
        capture=receipt.get('capture') or {}
        need(capture.get('pixel_equivalent') is True and capture.get('pixel_equivalence_samples')==5,
             f'{slug}: phone pixels lack five passing canvas/browser equivalence samples')
        need(set(receipt['inputs'])==set(REQUIRED_INPUTS), f'{slug}: phone receipt input bindings are incomplete')
        for name,value in receipt['inputs'].items():
            actual=confined(folder,name) if name=='film.html' else confined(root,name)
            need(sha(actual)==value, f'{slug}: stale phone receipt input {name}')
        why=facts_digest.stale(receipt,facts)
        need(why is None, f'{slug}: phone receipt facts binding: {why}')
        video=confined(folder,receipt['outputs']['master'])
        need(sha(video)==receipt['outputs']['master_sha256'], f'{slug}: phone video bytes differ from receipt')
        receipts[slug]=(path,receipt)
    return receipts


def evaluate(root=ROOT, title_source=None):
    root=root.resolve(); blockers=[]
    try:
        ready=read(root/'publication/readiness.json')
        need(ready['schema_version']==1,'unsupported publication-readiness schema')
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc:
        return {'status':'BLOCKED','blockers':[f'readiness record: {exc}']}
    try: title_check(root,ready,title_source)
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc: blockers.append(f'title: {exc}')
    try: phone_receipts(root)
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc: blockers.append(f'phone films: {exc}')
    return {'status':'BLOCKED' if blockers else 'READY','blockers':blockers}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--title-source',type=Path,help='optional isolated external source directory to check prepared source hashes')
    args=parser.parse_args(argv)
    report=evaluate(args.root,args.title_source)
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='READY' else 2


if __name__=='__main__':
    sys.exit(main())
