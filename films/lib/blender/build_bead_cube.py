#!/usr/bin/env python3
"""Build actual bead geometry and compare independently rendered projections."""
from pathlib import Path
import argparse
import hashlib
from itertools import product
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import determinism

# Design parameters, locators for receipts. Unit lattice is the CC-003 encoding.
PARAMETERS = {'radius': 0.18, 'resolution': 256, 'samples': 48, 'ortho_scale': 1.6,
              'corner_scale': 0.6, 'camera_distance': 6, 'corner_clip_end': 5.4,
              'segments': 32, 'rings': 16, 'frame': 0}
ARRANGEMENTS = {name: [p for p in product((0, 1), repeat=3) if sum(p) % 2 == parity]
                for parity, name in enumerate(('even', 'odd'))}
NON_CLAIMS = [
    'CC-003 constructed finite-world witness, not observed vendor behavior or a typical gap estimate.',
    'Projection equality is for bead silhouettes under orthographic rendering, not arbitrary lighting or perspective.',
    'The lattice scaffold is hidden for face and corner measurements; no geometry is projected or drawn in Python.',
    'The corner view clips away the opposite depth layer; it measures occupancy of corner 111 only.',
    'One host and Blender build only; no cross-version, GPU, physical-device, independent-review or learning claim.']


def material(name, color):
    import bpy
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*color, 1)
    output = nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
    return m


def configure(scene):
    scene.render.engine = 'BLENDER_EEVEE'
    assert scene.render.engine == 'BLENDER_EEVEE'
    scene.render.resolution_x = scene.render.resolution_y = PARAMETERS['resolution']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_depth = '8'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.eevee.taa_render_samples = PARAMETERS['samples']
    scene.eevee.use_taa_reprojection = True
    scene.eevee.use_raytracing = False
    scene.eevee.use_shadows = False
    scene.world.color = (0, 0, 0)
    scene.frame_set(PARAMETERS['frame'])


def build():
    import bpy
    from mathutils import Matrix, Vector
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    configure(scene)
    bead_mat = material('Bead silhouette', (0.3, 0.8, 0.65))
    lattice_mat = material('Lattice', (0.1, 0.2, 0.18))
    for i, point in enumerate(ARRANGEMENTS['even']):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=PARAMETERS['segments'],
            ring_count=PARAMETERS['rings'], radius=PARAMETERS['radius'], location=point)
        bead = bpy.context.object
        bead.name = f'bead_{i}'
        bead.data.materials.append(bead_mat)
    # Twelve rods are mesh geometry, no particles, physics or geometry nodes.
    corners = list(product((0, 1), repeat=3))
    for a in corners:
        for b in corners:
            if a < b and sum(x != y for x, y in zip(a, b)) == 1:
                start, end = Vector(a), Vector(b)
                bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.008, depth=(end-start).length,
                                                    location=(start+end)/2)
                obj = bpy.context.object
                obj.name = 'lattice_' + ''.join(map(str, a)) + '_' + ''.join(map(str, b))
                obj.rotation_euler = (end-start).to_track_quat('Z', 'Y').to_euler()
                obj.data.materials.append(lattice_mat)
    # Exact axis-permutation matrices avoid trigonometric projection drift.
    bases = {'xy': ((1,0,0), (0,1,0), (0,0,1)),
             'xz': ((1,0,0), (0,0,1), (0,-1,0)),
             'yz': ((0,1,0), (0,0,1), (1,0,0))}
    for arrangement in ARRANGEMENTS:
        for face, (right, up, back) in bases.items():
            data = bpy.data.cameras.new(f'{arrangement}_{face}')
            camera = bpy.data.objects.new(f'Camera_{arrangement}_{face}', data)
            scene.collection.objects.link(camera)
            data.type = 'ORTHO'
            data.ortho_scale = PARAMETERS['ortho_scale']
            matrix = Matrix((right, up, back)).transposed().to_4x4()
            matrix.translation = Vector((0.5, 0.5, 0.5)) + Vector(back) * PARAMETERS['camera_distance']
            camera.matrix_world = matrix
    scene.camera = bpy.data.objects['Camera_even_xy']
    assert len([o for o in scene.objects if o.type == 'CAMERA']) == 6
    assert not any(g.bl_idname == 'GeometryNodeTree' for g in bpy.data.node_groups)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'bead_cube.blend'))


def render_all(out):
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'bead_cube.blend'))
    scene = bpy.context.scene
    configure(scene)
    for obj in scene.objects:
        if obj.name.startswith('lattice_'):
            obj.hide_render = True
    for arrangement, points in ARRANGEMENTS.items():
        for i, point in enumerate(points):
            bpy.data.objects[f'bead_{i}'].location = point
        for face in ('xy', 'xz', 'yz', 'corner'):
            camera = bpy.data.objects[f'Camera_{arrangement}_{"xy" if face == "corner" else face}']
            if face == 'corner':
                camera.location = (1, 1, PARAMETERS['camera_distance'])
                camera.data.ortho_scale = PARAMETERS['corner_scale']
                camera.data.clip_end = PARAMETERS['corner_clip_end']
            scene.camera = camera
            stem = f'{arrangement}-{face}'
            scene.render.filepath = str(out / (stem + '.png'))
            bpy.ops.render.render(write_still=True)
            settings = {'engine': scene.render.engine, 'res_x': scene.render.resolution_x,
                'res_y': scene.render.resolution_y, 'res_percentage': scene.render.resolution_percentage,
                'format': scene.render.image_settings.file_format, 'color_depth': scene.render.image_settings.color_depth,
                'color_mode': scene.render.image_settings.color_mode, 'view_transform': scene.view_settings.view_transform,
                'look': scene.view_settings.look, 'frame': scene.frame_current, 'camera': camera.name,
                'camera_type': camera.data.type,
                'camera_matrix': [list(row) for row in camera.matrix_world], 'ortho_scale': camera.data.ortho_scale,
                'clip_start': camera.data.clip_start, 'clip_end': camera.data.clip_end,
                'sampling': {k: getattr(scene.eevee, k) for k in ('taa_render_samples', 'use_taa_reprojection', 'use_raytracing', 'use_shadows')},
                'arrangement': points, 'scaffold_hidden': True,
                'parameter_locator': 'films/lib/blender/build_bead_cube.py:PARAMETERS', 'claim': 'CC-003'}
            (out / (stem + '.settings.json')).write_text(json.dumps(settings, indent=2)+'\n')


def run_blender(*args):
    subprocess.run([determinism.BLENDER, '-b', '--factory-startup', '-noaudio', '--python-exit-code', '1',
                    '-P', str(Path(__file__).resolve()), '--', *args], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker', choices=['build', 'render'])
    p.add_argument('--output', type=Path, default=HERE / 'bead-cube-renders')
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.worker == 'build':
        build()
    elif args.worker == 'render':
        args.output.mkdir(parents=True, exist_ok=True)
        render_all(args.output)
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        receipt_path = args.output / 'receipt.json'
        receipt_path.unlink(missing_ok=True)
        run_blender('--worker', 'build')
        for run in ('first', 'repeat'):
            run_blender('--worker', 'render', '--output', str(args.output / run))
        receipts = {}
        for arrangement in ARRANGEMENTS:
            for face in ('xy', 'xz', 'yz', 'corner'):
                stem = f'{arrangement}-{face}'
                paths = [args.output / run / (stem+'.png') for run in ('first', 'repeat')]
                check = determinism.compare(*paths)
                if check['unexpected'] or not check['identical_pixels']:
                    raise RuntimeError(f'Non-deterministic {stem}: {check}')
                settings = [json.loads((args.output/run/(stem+'.settings.json')).read_text()) for run in ('first', 'repeat')]
                assert settings[0] == settings[1]
                receipts[stem] = determinism.receipt(HERE/'bead_cube.blend', paths, settings[0])
        comparisons = {face: determinism.compare(args.output/'first'/f'even-{face}.png',
                                                args.output/'first'/f'odd-{face}.png')
                       for face in ('xy', 'xz', 'yz', 'corner')}
        for face in ('xy', 'xz', 'yz'):
            assert comparisons[face]['identical_pixels'] and not comparisons[face]['unexpected'], (face, comparisons[face])
        assert not comparisons['corner']['identical_pixels'], 'Corner occupancy must differ'
        result = {'claim': 'CC-003', 'arrangement_locator': 'docs/foundations/devices.yaml:devices[id=D-007].action',
                  'parameters': PARAMETERS, 'build_script_sha256': determinism.file_sha256(Path(__file__)),
                  'comparisons': comparisons, 'renders': receipts, 'non_claims': NON_CLAIMS}
        receipt_path.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(comparisons, indent=2))


if __name__ == '__main__':
    main()
