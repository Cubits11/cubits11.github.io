#!/usr/bin/env python3
"""Render the one integer the marginals cannot show: which feasible both-miss
count a run landed on.

For a harmful stratum of n items scored by two guards, the per-guard miss
counts m1 and m2 fix the both-miss count only to the integer band
[max(0, m1 + m2 - n), min(m1, m2)]. Every slot in that band is a world the
marginals allow. One slot is the world the rows recorded. This scene draws the
band as slots and lights the recorded one; the independence plug-in
m1 * m2 / n is a thin amber tick, a model's point, never an observation.

Inputs are the committed observation rows of E3 and E3B. Every count is
recounted from the rows, cross-checked against each run's result file, and
pinned in the receipt to the commit that last touched each source. The image
carries no numerals: the numbers live in receipt.json and CAPTION.md, which
this script writes from the same facts, so neither can drift from the other.

Pipeline: the bead-cube harness, unchanged. Scene configuration, materials,
determinism comparison and receipt come from build_bead_cube.py and
determinism.py. Nothing here is a second render pipeline.

    python3 films/lib/blender/build_frechet_slots.py
"""
from fractions import Fraction
from pathlib import Path
import argparse
import collections
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import determinism
import build_bead_cube as harness

# Runs whose rows are drawn, top to bottom. Each is a harmful stratum, two guards.
RUNS = ('e3', 'e3b')
SOURCES = {run: {'rows': f'experiments/{run}/results/observations.jsonl',
                 'result': f'experiments/{run}/results/e3_result.json'} for run in RUNS}
# Scene parameters; a locator for the receipt, as in build_bead_cube.PARAMETERS.
PARAMETERS = {'resolution': (512, 256), 'samples': 48, 'frame': 0, 'ortho_scale': 10.0,
              'camera_distance': 6, 'slot_pitch': 1.0, 'row_gap': 1.6,
              'observed_radius': 0.32, 'ring_major': 0.32, 'ring_minor': 0.05,
              'tick_radius': 0.03, 'tick_depth': 0.9, 'rail_radius': 0.012,
              'segments': 32, 'rings': 16}
# Semantic colours. State is never colour alone: observed is a solid sphere,
# a feasible unobserved world is a ring, the plug-in is a tick.
COLOURS = {'observed': (0.3, 0.8, 0.65),      # evidence-cyan, as the bead silhouette
           'feasible': (0.12, 0.25, 0.28),    # dim: allowed by the marginals, not recorded
           'plug_in': (0.95, 0.65, 0.15),     # review-amber: a model's point
           'rail': (0.1, 0.2, 0.18)}          # the lattice colour: the band's extent
NON_CLAIMS = [
    'Shows which feasible integer each run landed on, not why; it is not evidence of dependence, '
    'and the amber tick is the independence plug-in, a model\'s point, not an observation.',
    'One pool and one frozen operating point per run, two research classifiers under 1B parameters; '
    'nothing about E2, its guards, its pools, or any deployed guardrail.',
    'E3B\'s single slot is a structural zero: G1 missed no injection, so both-miss was fixed at 0 '
    'before any joint count; it is not evidence of independence or of a good guard.',
    'Slot positions are exact integer counts recounted from committed rows; the image carries no '
    'numerals, and every number is in receipt.json, pinned to the commit that last touched its source.',
    'One host and one Blender build, EEVEE on CPU; no cross-version, GPU, physical-device, '
    'independent-review or learning claim.']


def git_pin(path: str) -> str:
    return subprocess.run(['git', 'log', '-1', '--format=%H', '--', path], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout.strip()


def facts() -> dict:
    """Recount every integer from the rows; refuse if the run's own result disagrees."""
    out = {}
    for run in RUNS:
        rows_path = ROOT / SOURCES[run]['rows']
        result_path = ROOT / SOURCES[run]['result']
        by_item: dict[str, dict[str, int]] = collections.defaultdict(dict)
        guards = set()
        for line in rows_path.read_text().splitlines():
            r = json.loads(line)
            if r['stratum'] != 'harmful':
                continue
            by_item[r['item_id']][r['guard']] = r['miss']
            guards.add(r['guard'])
        g1, g2 = sorted(guards)
        assert (g1, g2) == ('G1', 'G2'), guards
        n = len(by_item)
        m1 = sum(d[g1] for d in by_item.values())
        m2 = sum(d[g2] for d in by_item.values())
        both = sum(d[g1] and d[g2] for d in by_item.values())
        lo, hi = max(0, m1 + m2 - n), min(m1, m2)
        assert lo <= both <= hi, (run, lo, both, hi)
        plug_in = Fraction(m1 * m2, n)
        result = json.loads(result_path.read_text())['harmful']
        for label, ours, theirs in (('n', n, result['n']), ('p_miss_G1', m1 / n, result['p_miss_G1']),
                                    ('p_miss_G2', m2 / n, result['p_miss_G2']), ('q_obs', both / n, result['q_obs']),
                                    ('q_ind', float(plug_in) / n, result['q_ind']),
                                    ('frechet_lo', lo / n, result['frechet'][0]), ('frechet_hi', hi / n, result['frechet'][1])):
            if abs(ours - theirs) > 1e-12:
                raise SystemExit(f'{run}: recount of {label} = {ours} disagrees with {result_path}: {theirs}')
        out[run] = {'experiment': run.upper(), 'stratum': 'harmful', 'n': n,
                    'miss_G1': m1, 'miss_G2': m2, 'both_miss_observed': both,
                    'band_counts': [lo, hi], 'band_slots': hi - lo + 1,
                    'plug_in_count': {'exact': str(plug_in), 'float': float(plug_in)},
                    'structural_zero': hi == 0,
                    'sources': {k: {'path': p, 'sha256': determinism.file_sha256(ROOT / p), 'commit': git_pin(p)}
                                for k, p in SOURCES[run].items()}}
    return out


def caption(f: dict) -> str:
    lines = ['# What the frame shows, and what it does not', '',
             'Each row is one run\'s harmful stratum. The slots are the both-miss counts the two '
             'per-guard miss counts allow. The solid sphere is the count the rows recorded. Rings are '
             'worlds the marginals permit and the run did not produce. The amber tick is the '
             'independence plug-in.', '',
             '| run | n | G1 miss | G2 miss | band from marginals | slots | recorded both-miss | plug-in |',
             '|---|---|---|---|---|---|---|---|']
    for run in RUNS:
        r = f[run]
        lines.append(f"| {r['experiment']} | {r['n']} | {r['miss_G1']} | {r['miss_G2']} | "
                     f"[{r['band_counts'][0]}, {r['band_counts'][1]}] | {r['band_slots']} | "
                     f"{r['both_miss_observed']} | {r['plug_in_count']['float']:.4f} ({r['plug_in_count']['exact']}) |")
    lines += ['', 'Sources, pinned:', '']
    for run in RUNS:
        for k, s in f[run]['sources'].items():
            lines.append(f"- `{s['path']}` sha256 `{s['sha256'][:12]}…` at commit `{s['commit'][:12]}`")
    lines += ['', '## Not shown', ''] + [f'- {c}' for c in NON_CLAIMS] + ['']
    return '\n'.join(lines)


def build(facts_path: Path):
    import bpy
    from mathutils import Vector
    f = json.loads(facts_path.read_text())
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    harness.configure(scene)
    scene.render.resolution_x, scene.render.resolution_y = PARAMETERS['resolution']
    scene.eevee.taa_render_samples = PARAMETERS['samples']
    scene.frame_set(PARAMETERS['frame'])
    mats = {k: harness.material(k, c) for k, c in COLOURS.items()}
    P = PARAMETERS
    ys = {run: (len(RUNS) - 1) / 2 * P['row_gap'] - i * P['row_gap'] for i, run in enumerate(RUNS)}
    widest = max(f[run]['band_slots'] for run in RUNS)
    for run in RUNS:
        r = f[run]
        lo, hi = r['band_counts']
        # Centre every band on the widest one so a one-slot band sits under the middle.
        x0 = (widest - r['band_slots']) / 2 * P['slot_pitch']
        y = ys[run]
        for k in range(lo, hi + 1):
            x = x0 + (k - lo) * P['slot_pitch']
            if k == r['both_miss_observed']:
                bpy.ops.mesh.primitive_uv_sphere_add(segments=P['segments'], ring_count=P['rings'],
                                                     radius=P['observed_radius'], location=(x, y, 0))
                obj = bpy.context.object
                obj.name = f'{run}_observed_{k}'
                obj.data.materials.append(mats['observed'])
            else:
                bpy.ops.mesh.primitive_torus_add(major_radius=P['ring_major'], minor_radius=P['ring_minor'],
                                                 major_segments=P['segments'], minor_segments=P['rings'],
                                                 location=(x, y, 0))
                obj = bpy.context.object
                obj.name = f'{run}_feasible_{k}'
                obj.data.materials.append(mats['feasible'])
        if hi > lo:
            start, end = Vector((x0, y, -0.4)), Vector((x0 + (hi - lo) * P['slot_pitch'], y, -0.4))
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=P['rail_radius'], depth=(end - start).length,
                                                location=(start + end) / 2)
            obj = bpy.context.object
            obj.name = f'{run}_rail'
            obj.rotation_euler = (end - start).to_track_quat('Z', 'Y').to_euler()
            obj.data.materials.append(mats['rail'])
        tick_x = x0 + (r['plug_in_count']['float'] - lo) * P['slot_pitch']
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=P['tick_radius'], depth=P['tick_depth'],
                                            location=(tick_x, y, 0.5))
        obj = bpy.context.object
        obj.name = f'{run}_plug_in'
        obj.rotation_euler = (1.5707963267948966, 0, 0)
        obj.data.materials.append(mats['plug_in'])
    data = bpy.data.cameras.new('slots')
    camera = bpy.data.objects.new('Camera_slots', data)
    scene.collection.objects.link(camera)
    data.type = 'ORTHO'
    data.ortho_scale = P['ortho_scale']
    camera.location = ((widest - 1) / 2 * P['slot_pitch'], 0, P['camera_distance'])
    scene.camera = camera
    assert not any(g.bl_idname == 'GeometryNodeTree' for g in bpy.data.node_groups)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'frechet_slots.blend'))


def render(out: Path):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'frechet_slots.blend'))
    scene = bpy.context.scene
    harness.configure(scene)
    scene.render.resolution_x, scene.render.resolution_y = PARAMETERS['resolution']
    scene.eevee.taa_render_samples = PARAMETERS['samples']
    camera = bpy.data.objects['Camera_slots']
    scene.camera = camera
    scene.render.filepath = str(out / 'frechet-slots.png')
    bpy.ops.render.render(write_still=True)
    settings = {'engine': scene.render.engine, 'res_x': scene.render.resolution_x,
                'res_y': scene.render.resolution_y, 'res_percentage': scene.render.resolution_percentage,
                'format': scene.render.image_settings.file_format, 'color_depth': scene.render.image_settings.color_depth,
                'color_mode': scene.render.image_settings.color_mode, 'view_transform': scene.view_settings.view_transform,
                'look': scene.view_settings.look, 'frame': scene.frame_current, 'camera': camera.name,
                'camera_type': camera.data.type, 'camera_matrix': [list(row) for row in camera.matrix_world],
                'ortho_scale': camera.data.ortho_scale, 'clip_start': camera.data.clip_start, 'clip_end': camera.data.clip_end,
                'sampling': {k: getattr(scene.eevee, k) for k in ('taa_render_samples', 'use_taa_reprojection', 'use_raytracing', 'use_shadows')},
                'objects': sorted(o.name for o in scene.objects),
                'parameter_locator': 'films/lib/blender/build_frechet_slots.py:PARAMETERS', 'claims': ['E3-001', 'E3B-001']}
    (out / 'frechet-slots.settings.json').write_text(json.dumps(settings, indent=2) + '\n')


def run_blender(*args):
    subprocess.run([determinism.BLENDER, '-b', '--factory-startup', '-noaudio', '--python-exit-code', '1',
                    '-P', str(Path(__file__).resolve()), '--', *args], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker', choices=['build', 'render'])
    p.add_argument('--output', type=Path, default=HERE / 'frechet-slots-renders')
    args = p.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    args.output.mkdir(parents=True, exist_ok=True)
    facts_path = args.output / 'facts.json'
    if args.worker == 'build':
        build(facts_path)
    elif args.worker == 'render':
        render(args.output)
    else:
        receipt_path = args.output / 'receipt.json'
        receipt_path.unlink(missing_ok=True)
        f = facts()
        facts_path.write_text(json.dumps(f, indent=2) + '\n')
        run_blender('--worker', 'build', '--output', str(args.output))
        for run in ('first', 'repeat'):
            (args.output / run).mkdir(exist_ok=True)
            run_blender('--worker', 'render', '--output', str(args.output / run))
        paths = [args.output / run / 'frechet-slots.png' for run in ('first', 'repeat')]
        check = determinism.compare(*paths)
        if check['unexpected'] or not check['identical_pixels']:
            raise RuntimeError(f'Non-deterministic render: {check}')
        settings = [json.loads((args.output / run / 'frechet-slots.settings.json').read_text()) for run in ('first', 'repeat')]
        assert settings[0] == settings[1]
        # The scene must contain exactly the slots the facts declare, one sphere per run.
        for run in RUNS:
            names = [o for o in settings[0]['objects'] if o.startswith(run + '_')]
            assert sum(o.startswith(f'{run}_observed_') for o in names) == 1, names
            assert sum(o.startswith(f'{run}_feasible_') for o in names) == f[run]['band_slots'] - 1, names
        result = {'claims': ['E3-001', 'E3B-001'], 'facts': f, 'parameters': PARAMETERS, 'colours': COLOURS,
                  'build_script_sha256': determinism.file_sha256(Path(__file__)),
                  'render': determinism.receipt(HERE / 'frechet_slots.blend', paths, settings[0]),
                  'non_claims': NON_CLAIMS}
        receipt_path.write_text(json.dumps(result, indent=2) + '\n')
        (args.output / 'CAPTION.md').write_text(caption(f))
        print(json.dumps({run: {k: f[run][k] for k in ('n', 'miss_G1', 'miss_G2', 'band_counts', 'both_miss_observed')}
                          for run in RUNS}, indent=2))
        print('idat', check['idat_sha256'])


if __name__ == '__main__':
    main()
