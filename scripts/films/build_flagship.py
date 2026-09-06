#!/usr/bin/env python3
"""Build/check the flagship recording package. Never claims the camera has been recorded."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'films/flagship'
TOKEN = re.compile(r'\{\{([^|{}]+)\|(int)\}\}')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clock(t, srt=False):
    seconds = int(t)
    if srt:
        return f'{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02},000'
    return f'{seconds // 60:02}:{seconds % 60:02}'


def build():
    data = json.loads((PACK / 'script.json').read_text())
    facts = json.loads((ROOT / 'films/data/facts.json').read_text())['facts']
    import yaml
    registry = {c['id'] for c in yaml.safe_load((ROOT / 'claims.yaml').read_text())['claims']}
    source_map = {'status': 'EDITORIAL_REHEARSAL_NOT_FINAL_ASSEMBLY', 'inputs': {}, 'sections': []}
    for rel in ['films/flagship/script.json', 'scripts/films/build_flagship.py', 'films/flagship/rehearsal-template.html', 'films/data/facts.json', 'claims.yaml', 'census.yaml']:
        source_map['inputs'][rel] = sha(ROOT / rel)
    script = ['# Two Guardrails Walk Into a Stack — recording script', '', 'GENERATED. Voice and camera are not recorded. Timings are editorial targets, not speech alignment.', 'Numbers resolve from facts.json. If a spoken number disagrees with the render, redo the take.', 'No music under speech. Production timings and section identifiers are editorial metadata, not research facts.', '']
    camera = ['# Camera call sheet — sections 1 and 7', '', 'Read these takes from this generated sheet. Record clean voice for the remaining sections from RECORDING-SCRIPT.md. Do not improvise factual numbers.', '', 'Use the same lens, framing, exposure and eye line for the opening and closing return. Record unnumbered GUARD A and GUARD B cards; the bound insert supplies every on-screen research numeral. Record room tone and a tail on each take. No background music during speech.', '']
    captions, cues, time = [], [], 0
    assert [s['id'] for s in data['sections']] == list(range(1, 8))
    for s in data['sections']:
        assert s['operation'] and s['ledger'] and s['weaker']
        for locator in s['locators']:
            if '/' in locator or '.' in locator:
                assert (ROOT / locator).exists(), locator
                source_map['inputs'][locator] = sha(ROOT / locator)
            else:
                assert locator in registry, locator
        lines = [f"## {s['id']}. {s['title']} · {clock(time)}–{clock(time+s['duration_s'])}", '', f"Form: {s['form']}", f"Operation: {s['operation']}", f"Ledger: {s['ledger']}", f"Margin locators: {', '.join(s['locators'])}", '', 'Direction:', '']
        lines += [f'- {x}' for x in s['shots']]
        lines += ['', f"Weaker sentence, spoken verbatim: **{s['weaker']}**", '']
        smap = {'id': s['id'], 'start_s': time, 'end_s': time+s['duration_s'], 'operation': s['operation'], 'ledger': s['ledger'], 'locators': s['locators'], 'weaker': s['weaker'], 'bindings': []}
        prev = 0
        full_voice = []
        for b in s['beats']:
            assert b['start'] == prev and b['end'] > b['start']
            prev = b['end']
            # Literal research digits in a spoken line must be replaced with a fact token.
            assert not re.search(r'\d', TOKEN.sub('', b['voice'])), b['voice']
            def resolve(m):
                fid, fmt = m.groups()
                fact = facts[fid]
                assert fact['value'] == int(fact['value']), fid
                rendered = str(int(fact['value']))
                smap['bindings'].append({'fact': fid, 'kind': fact['kind'], 'value': fact['value'], 'rendered': rendered, 'source': fact['source'], 'at_s': time+b['start']})
                return rendered
            voice = TOKEN.sub(resolve, b['voice'])
            assert '{{' not in voice
            full_voice.append(voice)
            if b.get('film'):
                slug = b['film']
                manifest = ROOT / 'films' / slug / 'manifest.yaml'
                spec = yaml.safe_load(manifest.read_text())
                assert b['film_in'] >= 0 and b['film_in'] + b['end'] - b['start'] <= spec['duration_s'], slug
                source_map['inputs'][str(manifest.relative_to(ROOT))] = sha(manifest)
                for evidence in spec['evidence']:
                    assert evidence['value'] == facts[evidence['fact']]['value'], evidence['fact']
                media = f"../{slug}/renders/{slug}__master.mp4"
            else:
                media = None
            cue = {'section': s['id'], 'title': s['title'], 'start': time+b['start'], 'end': time+b['end'], 'voice': voice, 'ledger': s['ledger'], 'form': s['form'], 'locators': s['locators'], 'media': media, 'mediaIn': b.get('film_in', 0), 'weaker': s['weaker']}
            cues.append(cue)
            lines += [f"**{clock(cue['start'])}–{clock(cue['end'])}** — {voice or '[SILENCE — let the strike execute.]'}", '']
            if voice:
                # Reading captions only; evenly partitioned cues are deliberately not final subtitles.
                words = voice.split()
                chunks = [' '.join(words[i:i+12]) for i in range(0, len(words), 12)]
                duration = cue['end'] - cue['start']
                for i, chunk in enumerate(chunks):
                    start = cue['start'] + duration*i/len(chunks)
                    end = cue['start'] + duration*(i+1)/len(chunks)
                    captions.append(f'{len(captions)+1}\n{clock(start, True)} --> {clock(end, True)}\n{chunk}\n')
        assert prev == s['duration_s']
        assert ' '.join(full_voice).count(s['weaker']) == 1, s['id']
        smap['word_count'] = len(' '.join(full_voice).split())
        source_map['sections'].append(smap)
        script += lines
        if s['id'] in (1,7):
            camera += lines
        time += s['duration_s']
    assert 480 <= time <= 600
    source_map['duration_s'] = time
    source_map['word_count'] = sum(s['word_count'] for s in source_map['sections'])
    payload = json.dumps({'title': data['title'], 'duration': time, 'cues': cues}, ensure_ascii=False).replace('</', r'<\/')
    template = (PACK / 'rehearsal-template.html').read_text()
    outputs = {'RECORDING-SCRIPT.md': '\n'.join(script)+'\n', 'CAMERA-CALL-SHEET.md': '\n'.join(camera)+'\n', 'source-map.json': json.dumps(source_map, indent=2, ensure_ascii=False)+'\n', 'rehearsal-captions.srt': '\n'.join(captions), 'rehearsal.html': template.replace('__PAYLOAD__', payload)}
    return outputs, source_map


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    outputs, smap = build()
    for name, content in outputs.items():
        path = PACK / name
        if args.check:
            assert path.exists() and path.read_text() == content, f'{name} stale: rebuild flagship'
        else:
            path.write_text(content)
    print(f"ok    flagship source map: {len(smap['sections'])} sections, {smap['duration_s']} s, {smap['word_count']} words; weaker sentences present once; fact tokens and film ranges checked")
    print('NOTE  editorial package only: final camera, voice, captures, speech alignment and assembly-commit gate still required')


if __name__ == '__main__':
    main()
