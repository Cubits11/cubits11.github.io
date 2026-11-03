#!/usr/bin/env python3
"""Enforce the owner's publication hold; missing human evidence is BLOCKED.

This gate checks records and artifact bindings. It cannot establish that a
participant is human, unfamiliar, distinct, or quoted faithfully: those remain
facilitator attestations. Ordinary consistency CI runs this gate's unit tests,
not a fictitious passing reader study. The deployment job runs the actual gate.
"""
from __future__ import annotations
import argparse
import copy
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'films'))
import facts_digest  # noqa: E402

TITLE = 'What AI Guardrail Scores Cannot Tell You'
FILM = 'the-missing-column-census'
# Files a receipt binds whole; the facts it read are bound by facts_subset (facts_digest.py).
REQUIRED_INPUTS = ('film.html','films/lib/film.js','films/lib/tokens.css')
HUMAN_LIMIT = 'Human identity, unfamiliarity, distinctness and raw-answer fidelity are facilitator attestations, not independently verified by automation.'


class Blocked(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Blocked(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


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


def protocol_check(ready):
    p=ready['protocol']
    need(p['status']=='CONFIRMED' and text(p['confirmation_source']), 'reader protocol awaits confirmation')
    need(p['sample_size']==5 and p['minimum_successes_per_task']==4 and p['homepage_seconds']==20,
         'confirmed protocol requires five readers, four successes per task and a joint 20-second homepage task')
    need(p['film']==FILM and text(p['film_selection']), 'Missing Column film selection is unresolved')
    need(p['tasks']==['homepage_joint','film_missing_column','proof_activation'], 'all three confirmed reader tasks are required')
    need(set(p['rater_criteria'])=={'subject','contact','missing_column','proof'}
         and all(text(s) for s in p['rater_criteria'].values()), 'rater criteria must be recorded before the study')
    return p


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


class Resources(HTMLParser):
    def __init__(self):
        super().__init__(); self.paths=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for key in ('src','poster','data-phone-poster'):
            if a.get(key): self.paths.append(a[key])
        if tag=='link' and a.get('rel')=='stylesheet' and a.get('href'):
            self.paths.append(a['href'])


def binding_paths(root, ready, receipts):
    slug=ready['protocol']['film']
    paths={'index.html','try/index.html',f'films/{slug}/index.html'}
    # Bind what the participant sees, including every referenced local player
    # rendition, poster, stylesheet, script and stylesheet font/image resource.
    for name in list(paths):
        if not name.endswith('index.html'): continue
        parser=Resources(); parser.feed((root/name).read_text())
        for url in parser.paths:
            parts=urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path: continue
            path=unquote(parts.path)
            relative=path.lstrip('/') if path.startswith('/') else str(Path(name).parent/path)
            paths.add(confined(root,relative).relative_to(root.resolve()).as_posix())
    for name in list(paths):
        if not name.endswith('.css'): continue
        for url in re.findall(r'url\([\'"]?([^\)\'\"]+)',(root/name).read_text()):
            if urlsplit(url).scheme or url.startswith('data:'): continue
            relative=url.lstrip('/') if url.startswith('/') else str(Path(name).parent/url)
            paths.add(confined(root,relative).relative_to(root.resolve()).as_posix())
    # Source, facts, manifests and receipt bookkeeping are checked separately
    # by phone_receipts. Only changed participant-visible bytes require a new
    # reader study; a fresh receipt for identical media does not.
    return sorted(paths)


def current_binding(root,ready,receipts):
    return {name:sha(confined(root,name)) for name in binding_paths(root,ready,receipts)}


def readers_check(root,ready,receipts):
    p=protocol_check(ready)
    readers=read(confined(root,ready['readers_path']))
    need(readers['schema_version']==1, 'unsupported reader-evidence schema')
    participants=readers['participants']
    need(isinstance(participants,list) and len(participants)==5, f'five actual unfamiliar-reader records required; found {len(participants) if isinstance(participants,list) else "invalid"}')
    need(ready['protocol_sha256']==readers['protocol_sha256']==digest(p), 'reader protocol binding is missing or drifted')
    expected=current_binding(root,ready,receipts)
    need(ready['artifact_sha256']==readers['artifact_sha256']==expected, 'tested artifacts are unbound or have changed since the reader test')
    facilitator=readers['facilitator']
    need(text(facilitator['id']) and dated(facilitator['recorded_on'])
         and all(facilitator.get(key) is True for key in ('attests_humans','attests_unfamiliar','attests_distinct')),
         'facilitator must attest five distinct unfamiliar humans; automation cannot establish this')
    rater=readers['rater']
    need(text(rater['id']) and rater['criteria']==p['rater_criteria'], 'rater and pre-recorded criteria must be preserved')
    identifiers=set(); counts={'homepage_joint':0,'film_missing_column':0,'proof_activation':0}
    for participant in participants:
        pid=participant['id']
        need(text(pid) and pid not in identifiers, 'reader identifiers must be distinct and nonempty')
        identifiers.add(pid)
        need(participant['kind']=='human' and participant['unfamiliar'] is True and dated(participant['recorded_at']), f'{pid}: agent, familiar or undated participant record')
        home,film,proof=(participant[k] for k in ('homepage','film','proof'))
        need(number(home['elapsed_seconds']) and all(text(home[k]) for k in ('subject_answer','contact_answer','rater_notes'))
             and type(home['subject_pass']) is bool and type(home['contact_pass']) is bool, f'{pid}: homepage raw answers, elapsed time and ratings are required')
        counts['homepage_joint']+=int(home['subject_pass'] and home['contact_pass'] and home['elapsed_seconds']<=20)
        need(film['slug']==p['film'] and type(film['watched_full']) is bool and text(film['explanation'])
             and type(film['one_sentence']) is bool and type(film['pass']) is bool and text(film['rater_notes']), f'{pid}: full named film, raw explanation and rating are required')
        if 'elapsed_seconds' in film and film['elapsed_seconds'] is not None:
            need(number(film['elapsed_seconds']),f'{pid}: optional film response time must be nonnegative')
        counts['film_missing_column']+=int(film['watched_full'] and film['pass'] and film['one_sentence'])
        need(type(proof['activation_count']) is int and proof['activation_count']>=0 and proof['method'] in ('keyboard','click','none')
             and text(proof['destination']) and type(proof['pass']) is bool
             and text(proof['observation']) and text(proof['rater_notes']), f'{pid}: proof activation observation and rating are required')
        counts['proof_activation']+=int(proof['pass'] and proof['activation_count']==1 and proof['destination']=='/try/')
    need(all(value>=4 for value in counts.values()), f'unfamiliar-reader gate failed: {counts}; each task requires four of five')
    return counts


def evaluate(root=ROOT, title_source=None):
    root=root.resolve(); blockers=[]; counts=None
    try:
        ready=read(root/'publication/readiness.json')
        need(ready['schema_version']==1,'unsupported publication-readiness schema')
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc:
        return {'status':'BLOCKED','blockers':[f'readiness record: {exc}'],'human_evidence_limit':HUMAN_LIMIT}
    for label,check in (('protocol',lambda:protocol_check(ready)),('title',lambda:title_check(root,ready,title_source))):
        try: check()
        except (Blocked,OSError,ValueError,KeyError,TypeError) as exc: blockers.append(f'{label}: {exc}')
    try: receipts=phone_receipts(root)
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc:
        blockers.append(f'phone films: {exc}'); receipts=None
    # Missing participants is reported even while phone renders are unfinished.
    try:
        readers=read(confined(root,ready['readers_path']))
        need(isinstance(readers['participants'],list) and len(readers['participants'])==5,
             f'five actual unfamiliar-reader records required; found {len(readers["participants"]) if isinstance(readers["participants"],list) else "invalid"}')
        if receipts is not None: counts=readers_check(root,ready,receipts)
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc: blockers.append(f'readers: {exc}')
    return {'status':'BLOCKED' if blockers else 'READY','blockers':blockers,'reader_successes':counts,'human_evidence_limit':HUMAN_LIMIT}


def bind(root=ROOT):
    """Pin the candidate before collection; never rebind existing observations."""
    ready=read(root/'publication/readiness.json'); protocol_check(ready)
    readers_path=confined(root,ready['readers_path']); readers=read(readers_path)
    need(readers['participants']==[], 'cannot rebind an existing reader study; record its result and start a dated new study')
    receipts=phone_receipts(root)
    ready['protocol_sha256']=readers['protocol_sha256']=digest(ready['protocol'])
    ready['artifact_sha256']=readers['artifact_sha256']=current_binding(root,ready,receipts)
    (root/'publication/readiness.json').write_text(json.dumps(ready,indent=2)+'\n')
    readers_path.write_text(json.dumps(readers,indent=2)+'\n')
    return readers


def template(root=ROOT):
    ready=read(root/'publication/readiness.json'); data=copy.deepcopy(read(confined(root,ready['readers_path'])))
    need(data['participants']==[], 'template is available only before observations are recorded')
    data['rater']['criteria']=ready['protocol']['rater_criteria']
    data['participants']=[{'id':f'P{i:02d}','kind':None,'unfamiliar':None,'recorded_at':None,
       'homepage':{'elapsed_seconds':None,'subject_answer':'','contact_answer':'','subject_pass':None,'contact_pass':None,'rater_notes':''},
       'film':{'slug':ready['protocol']['film'],'watched_full':None,'explanation':'','one_sentence':None,'pass':None,'rater_notes':'','elapsed_seconds':None},
       'proof':{'activation_count':None,'method':None,'destination':'','pass':None,'observation':'','rater_notes':''}}
       for i in range(1,6)]
    return data


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--title-source',type=Path,help='optional isolated external source directory to check prepared source hashes')
    actions=parser.add_mutually_exclusive_group(); actions.add_argument('--bind',action='store_true',help='bind current artifacts before any reader observations')
    actions.add_argument('--template',action='store_true',help='print an unfilled worksheet; never creates reader evidence')
    args=parser.parse_args(argv)
    try:
        if args.bind:
            bind(args.root.resolve()); print('Candidate bound before collection. No reader evidence created.'); return 0
        if args.template:
            print(json.dumps(template(args.root.resolve()),indent=2)); return 0
    except (Blocked,OSError,ValueError,KeyError,TypeError) as exc:
        print(f'BLOCKED: {exc}'); return 2
    report=evaluate(args.root,args.title_source)
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='READY' else 2


if __name__=='__main__':
    sys.exit(main())
