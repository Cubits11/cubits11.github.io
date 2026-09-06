#!/usr/bin/env python3
"""devices.yaml -> static, answer-first nodes and the compiled T1 machine."""
from pathlib import Path
import argparse
import hashlib
from html import escape as e
import json
import re
import sys
import yaml

from audit_device import transition_tables
from verify_room_atom_map import verify as verify_rooms

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT/'docs/foundations/devices.yaml'
OUTPUT = ROOT/'foundations'
ASSETS = ROOT/'assets/foundations'


def page(device, registry, tables):
    key = device['id']
    spec = registry['web_nodes'][key]
    source = f'docs/foundations/devices.yaml:web_nodes.{key}'
    loc = f'docs/foundations/devices.yaml:devices[id={key}]'
    options = ''.join(f'<label class="option"><input type="radio" name="answer" value="{i}" required>'
                      f'<span>{e(option["label"])}</span></label>' for i, option in enumerate(spec['options']))
    readouts = ''.join(f'''<article class="readout" id="answer-{i}" data-answer="{i}" data-skip="{str(option['skip_repair']).lower()}">
<h2>{e(option['label'])}</h2><p>{e(option['readout'])}</p>
<p class="excluded"><strong>Excluded world.</strong> {e(option['excluded_world'])}</p>
<a href="#non-claim">{'Carry the limit forward' if option['skip_repair'] else 'Write the limit in your own words'}</a></article>'''
                      for i, option in enumerate(spec['options']))
    nav = ''.join(f'<a href="/foundations/{d["id"].lower()}/">{e(d["name"])}</a>' for d in registry['devices'])
    limits = [device.get('cannot_show', device.get('rung_reason', ''))] + registry['web_scope']['non_claims']
    if key == 'D-007':
        limits += ['Atomic parity switching only. Loose-bead arrangements and emptying intermediates are not certified.',
                   'Text reports the projected and corner occupancies, but equivalence for non-sighted learners has not been user-tested.']
    if key == 'D-006':
        limits += ['The digital cell uses the representative local constraints named in the audit model; no concrete puzzle was supplied.']
    if key == 'D-004':
        limits += ['The digital model audits one ruler on a fixed strict ordering, not coupled rulers, ties, or detector performance.']
    if key == 'D-002':
        limits += ['The digital model is the finite integer overlap grid, not every real-valued probability in the continuous interval.']
    nonclaims = ''.join(f'<li>{e(text)}</li>' for text in limits)
    state = ''
    if key in tables:
        state = f'''<section class="device-panel" data-device="{key}" data-locator="docs/foundations/AUDIT-MODELS.md:{key}">
<h2>Move the device</h2><p class="model-scope">{e(tables[key]['scope'])}</p>
<button type="button" class="load-device">Open the mesh</button>
<div class="mesh-view" role="img" aria-label="{e(device['name'])} geometry" hidden></div>
<p class="mesh-status" role="status"></p><output class="state-readout" aria-live="polite"></output>
<div class="moves" aria-label="Permitted moves"></div>
<p>Model scope: SELF-AUDITED. <a href="/docs/foundations/AUDIT-MODELS.md">Read the exact constraints and limits</a>.</p>
<noscript><p>The mesh is optional. The full instruction, question, alternatives, and readouts are available on this page.</p></noscript></section>'''
    else:
        state = f'<section data-locator="docs/foundations/devices.yaml:audit_state_space.{key}"><h2>Text exercise</h2><p>{e(registry["audit_state_space"][key])}. No mesh state machine is claimed.</p></section>'
    projections = ''
    if key == 'D-007':
        projections = '<section class="projection-proof"><h2>The rendered comparison</h2>'
        for arrangement in ('even', 'odd'):
            projections += f'<h3>{arrangement.title()} arrangement</h3><div class="projections">'
            for face in ('xy', 'xz', 'yz', 'corner'):
                alt = (f'{arrangement.title()} {face} orthographic projection: each pair bin is occupied.' if face != 'corner'
                       else f'{arrangement.title()} far-corner inset: ' + ('empty.' if arrangement == 'even' else 'occupied.'))
                projections += f'<figure><img loading="lazy" width="256" height="256" src="/films/lib/blender/bead-cube-renders/first/{arrangement}-{face}.png" alt="{alt}"><figcaption>{face.upper() if face != "corner" else "Far corner"}</figcaption></figure>'
            projections += '</div>'
        projections += '<p>The face images are rendered orthographic bead silhouettes. The corner view clips away the opposite layer; the lattice is hidden for these measurements. This constructed example permits matching pairs and different triple occupancy.</p><a href="/films/lib/blender/bead-cube-renders/receipt.json">Projection receipt and non-claims</a></section>'
    atom_names = '; '.join(registry['atoms'][atom] for atom in device['atoms'])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(device['name'])} · Foundations</title><meta name="description" content="{e(atom_names)}">
<link rel="stylesheet" href="/assets/foundations/foundations.css">
<script type="importmap">{{"imports":{{"three":"/assets/foundations/vendor/three/three.module.js"}}}}</script>
<script type="module" src="/assets/foundations/foundations.js"></script></head>
<body data-node="{key}" data-locator="{loc}">
<!-- Generated by scripts/generate_foundations.py. Edit devices.yaml, never this page. -->
<a class="skip" href="#main">Skip to content</a>
<a class="claim-exit" href="/ledger/#{spec['claim']}">Open the claim ↗</a>
<main id="main"><section class="hinge" data-locator="{source}">
<h1>{e(device['action'])}</h1><form class="hinge-form"><fieldset><legend>{e(spec['question'])}</legend>
<div class="options">{options}</div><button class="submit" type="submit">Read this answer</button></fieldset></form>
<a class="no-script-readouts" href="#readouts">Read all answer branches</a>
</section>
<div id="after-answer"><section id="readouts" tabindex="-1" data-locator="{source}"><h2 class="section-title">What that answer leaves out</h2>{readouts}</section>
{state}{projections}
<section id="non-claim" tabindex="-1"><h2>What does this fail to establish?</h2>
<label for="limit">Write the nearest claim this example does not support.</label><textarea id="limit" rows="3"></textarea>
<p>Your words stay on this page. Nothing is sent or stored.</p><ul>{nonclaims}</ul>
<a href="/ledger/#{spec['claim']}">Return to the claim</a></section>
<section class="later-hinge"><h2>Without the device</h2><p>Look away from the object, then answer the question again. This is a prompt for reflection, not a measured learning outcome.</p>
<details><summary>{e(spec['question'])}</summary><ul>{''.join('<li>'+e(o['label'])+'</li>' for o in spec['options'])}</ul></details></section>
<footer><p>{e(device['name'])} · {e(atom_names)}</p>
<a href="/docs/foundations/devices.yaml">Device source and numeral locators</a> · <a href="/docs/foundations/AUDIT-MODELS.md">Audit scopes</a>
<nav aria-label="Other devices">{nav}</nav><a href="/foundations/meshes/">Bare mesh loading page</a></footer>
</div></main></body></html>
'''


def bare(tables):
    panels = ''.join(f'''<section class="device-panel" data-device="{key}" data-locator="{table['locator']}">
<h2>{key}</h2><button class="load-device" type="button">Load mesh</button>
<div class="mesh-view" role="img" aria-label="{key} mesh" hidden></div><p class="mesh-status" role="status"></p>
<output class="state-readout" aria-live="polite"></output><div class="moves"></div>
<p>{e(table['scope'])}</p></section>''' for key, table in tables.items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Device mesh loader</title><link rel="stylesheet" href="/assets/foundations/foundations.css">
<script type="importmap">{{"imports":{{"three":"/assets/foundations/vendor/three/three.module.js"}}}}</script>
<script type="module" src="/assets/foundations/mesh-test.js"></script></head><body>
<a class="skip" href="#main">Skip to content</a><main id="main"><h1>Device mesh loader</h1>
<p>Geometry only. Moves come from the compiled Python audit models. Each load is user initiated.</p>
{panels}<p>No physical fidelity, independent audit, learner outcome or cross-browser guarantee is asserted.</p>
<a href="/assets/foundations/meshes/receipt.json">Export receipt and size locators</a>
<a href="/foundations/">Return to the questions</a></main></body></html>'''


def outputs():
    registry = yaml.safe_load(REGISTRY.read_text())
    tables = transition_tables()
    devices = registry['devices']
    assert set(registry['web_nodes']) == {d['id'] for d in devices}
    for key, spec in registry['web_nodes'].items():
        assert len(spec['options']) == 4 and any(o['skip_repair'] for o in spec['options']), key
        assert all(o['excluded_world'] and o['readout'] for o in spec['options']), key
        assert re.fullmatch(r'(CC|MC)-\d{3}', spec['claim']), key
        assert f'id="{spec["claim"]}"' in (ROOT/'ledger/index.html').read_text(), key
    result = {OUTPUT/d['id'].lower()/'index.html':page(d, registry, tables) for d in devices}
    result[OUTPUT/'index.html'] = page(next(d for d in devices if d['id']=='D-007'), registry, tables)
    result[OUTPUT/'meshes/index.html'] = bare(tables)
    payload = {'source': 'scripts/audit_device.py:models',
               'source_sha256': hashlib.sha256((ROOT/'scripts/audit_device.py').read_bytes()).hexdigest(),
               'non_claims': registry['web_scope']['non_claims'], 'devices': tables}
    result[ASSETS/'states.json'] = json.dumps(payload, sort_keys=True, indent=2)+'\n'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify_rooms()
    expected = outputs()
    drift = []
    for path, content in expected.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                drift.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    stale = set(OUTPUT.rglob('*.html')) - set(expected)
    drift += [str(p.relative_to(ROOT)) for p in stale]
    if drift:
        print('FAIL generated foundations drift: ' + ', '.join(drift))
        return 1
    print('Foundations source and generated outputs agree.' if args.check else 'Generated foundations nodes and T1 transitions.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
