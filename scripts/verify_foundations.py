#!/usr/bin/env python3
"""Cheap reproducible gates for foundations sources, model tables and artifacts."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml
from audit_device import models, transition_tables
from generate_foundations import outputs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'films/lib/blender'))
import determinism
from build_bead_cube import ARRANGEMENTS
from export_devices import DEVICES, PARAMETERS, glb_json


class Numerals(HTMLParser):
    """Every visible numeric text node must inherit a source locator."""
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in {'meta','link','input','img','br','hr','source','wbr'}:
            self.stack.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                return

    def handle_data(self, text):
        if any(t in ('script','style') for t, _ in self.stack):
            return
        if re.search(r'\d', text) and not any('data-locator' in attrs for _, attrs in self.stack):
            self.errors.append(text.strip())


def verify():
    expected = outputs()
    for path, content in expected.items():
        assert path.exists() and path.read_text() == content, f'generated drift: {path}'
        if path.suffix == '.html':
            audit = Numerals(); audit.feed(content)
            assert not audit.errors, (path, audit.errors)
            assert not re.search(r'\bcorrect\b|data-score|autoplay', content, re.I), path
    payload = json.loads((ROOT/'assets/foundations/states.json').read_text())
    # JSON normalization converts tuples to arrays without changing any state.
    assert payload['devices'] == json.loads(json.dumps(transition_tables()))
    assert payload['source_sha256'] == determinism.file_sha256(ROOT/'scripts/audit_device.py')
    registry = yaml.safe_load((ROOT/'docs/foundations/devices.yaml').read_text())
    assert registry['counts']['nodes_generated'] == len(registry['web_nodes'])
    assert registry['counts']['with_audit_script'] == len(models())
    parity_states = models()['D-007'].universe
    assert all(tuple(map(tuple, points)) in parity_states for points in ARRANGEMENTS.values())
    projection_dir = ROOT/'films/lib/blender/bead-cube-renders'
    proof = json.loads((projection_dir/'receipt.json').read_text())
    assert proof['claim'] == 'CC-003' and proof['non_claims']
    assert proof['build_script_sha256'] == determinism.file_sha256(ROOT/'films/lib/blender/build_bead_cube.py')
    blend_hash = determinism.file_sha256(ROOT/'films/lib/blender/bead_cube.blend')
    for stem, receipt in proof['renders'].items():
        assert receipt['blend']['sha256'] == blend_hash, 'source scene changed'
        files = [projection_dir/run/(stem+'.png') for run in ('first','repeat')]
        comparison = determinism.compare(*files)
        assert comparison['identical_pixels'] and not comparison['unexpected'], stem
        for path, recorded in zip(files, receipt['renders']):
            assert determinism.idat_sha256(path) == recorded['idat_sha256'], path
        assert receipt['determinism'] == comparison
        settings = receipt['settings']
        required = {'engine','res_x','res_y','res_percentage','format','color_depth',
                    'view_transform','look','frame','camera','sampling'}
        assert required <= settings.keys(), stem
        assert settings['camera_type'] == 'ORTHO'
        assert settings['camera'].startswith('Camera_'+stem.split('-')[0]+'_')
    for face, recorded in proof['comparisons'].items():
        comparison = determinism.compare(projection_dir/'first'/f'even-{face}.png', projection_dir/'first'/f'odd-{face}.png')
        assert comparison == recorded
        if face == 'corner':
            assert not comparison['identical_pixels'] and comparison['unexpected'] == ['IDAT']
        else:
            assert comparison['identical_pixels'] and not comparison['unexpected']
    exported = json.loads((ROOT/'assets/foundations/meshes/receipt.json').read_text())
    assert set(exported['exports']) == set(DEVICES)
    assert exported['source_sha256'] == determinism.file_sha256(ROOT/'films/lib/blender/export_devices.py')
    assert exported['bead_cube_sha256'] == blend_hash
    for device, record in exported['exports'].items():
        path = ROOT/record['path']
        assert path.stat().st_size == record['bytes'] < PARAMETERS['max_glb_bytes'], device
        assert determinism.file_sha256(path) == record['sha256'], device
        gltf = glb_json(path)
        assert not any(gltf.get(key) for key in ('cameras','animations','skins'))
        assert all('KHR_draco_mesh_compression' in primitive.get('extensions', {})
                   for mesh in gltf['meshes'] for primitive in mesh['primitives'])
        assert not any(node.get('extras') for node in gltf['nodes']), 'State must not be embedded in glTF'
    browser = json.loads((ROOT/'assets/foundations/meshes/browser.receipt.json').read_text())
    for path, sha in browser['source_sha256'].items():
        assert determinism.file_sha256(ROOT/path) == sha, f'Browser acceptance stale: {path}'
    assert {row['device'] for row in browser['exports']} == set(DEVICES)
    assert all(row['loaded'] and row['reachable_states'] == len(payload['devices'][row['device']]['states'])
               for row in browser['exports'])
    assert browser['no_js_nodes'] == len(registry['web_nodes'])
    print('Foundations verified: source locators, generated T1 transitions, projection IDATs, and device-only Draco exports.')
    print('Non-claims: this gate does not replace rendering, browser tests, independent review, or learner observation.')

if __name__ == '__main__':
    verify()
