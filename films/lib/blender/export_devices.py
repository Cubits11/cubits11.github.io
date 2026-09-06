#!/usr/bin/env python3
"""Build and export only finite device meshes, never the external world."""
from pathlib import Path
import json
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import determinism
OUT = ROOT / 'assets/foundations/meshes'
DEVICES = ('D-002', 'D-003', 'D-004', 'D-005', 'D-006', 'D-007')
# Design dimensions, not empirical quantities. Public numeric readouts use T1.
PARAMETERS = {'max_glb_bytes': 2_000_000, 'coin_count_per_reader': 10,
              'sorted_objects': 20, 'cell_symbols': 4, 'draco_level': 6}


def glb_json(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and length == len(data)
    size, kind = struct.unpack_from('<I4s', data, 12)
    assert kind == b'JSON'
    return json.loads(data[20:20+size])


def export():
    import bpy
    sys.path.insert(0, str(HERE))
    from build_bead_cube import build, material
    OUT.mkdir(parents=True, exist_ok=True)

    def box(name, location, scale, mat):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.name = name
        obj.scale = scale
        obj.data.materials.append(mat)
        return obj

    for device in DEVICES:
        # Local factory scene only. The separate repository is never opened.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        jade = material('Jade', (0.28, 0.75, 0.60))
        ochre = material('Ochre', (0.80, 0.48, 0.20))
        neutral = material('Neutral', (0.18, 0.24, 0.22))
        if device == 'D-007':
            # Use the actual proof scene geometry, not a web re-drawing.
            bpy.ops.wm.open_mainfile(filepath=str(HERE/'bead_cube.blend'))
        elif device == 'D-002':
            for row, mat in enumerate((jade, ochre)):
                for i in range(PARAMETERS['coin_count_per_reader']):
                    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.09, depth=0.035,
                        location=(i*0.22, row*0.25, 0))
                    obj = bpy.context.object
                    obj.name = f'coin_{row}_{i}'
                    obj.data.materials.append(mat)
        elif device == 'D-003':
            box('box', (0,0,0), (1.6,0.8,0.5), neutral)
            for i in range(2):
                box(f'hasp_{i}', (-0.4+i*0.8,0,0.32), (0.18,0.5,0.08), jade)
            box('link', (0,0,0.42), (1,0.08,0.08), ochre)
        elif device == 'D-004':
            for i in range(PARAMETERS['sorted_objects']):
                height = 0.1 + i*0.025
                box(f'item_{i}', (i*0.16, 0, height/2), (0.11,0.2,height), jade)
            box('ruler', (-0.08,0,0.35), (0.025,0.7,0.8), ochre)
        elif device == 'D-005':
            box('whole_page', (0,0,0), (1,1.4,0.025), jade)
            box('slip', (0,0,0.04), (1,0.25,0.025), ochre)
        elif device == 'D-006':
            for symbol in range(1, PARAMETERS['cell_symbols']+1):
                box(f'cell_{symbol}', ((symbol-1)*0.4,0,0), (0.34,0.34,0.04), neutral)
            box('selector', (0.4,0,0.07), (0.25,0.25,0.05), jade)
        bpy.ops.object.select_all(action='DESELECT')
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        for obj in meshes:
            obj.hide_set(False)
            obj.hide_viewport = False
            obj.hide_render = False
            obj.select_set(True)
        assert meshes and not any(g.bl_idname == 'GeometryNodeTree' for g in bpy.data.node_groups)
        path = OUT / f'{device}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
            export_cameras=False, export_animations=False, export_extras=False,
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=PARAMETERS['draco_level'])
        document = glb_json(path)
        assert not document.get('cameras') and not document.get('animations')
        assert not document.get('skins')
        assert all('KHR_draco_mesh_compression' in primitive.get('extensions', {})
                   for mesh in document['meshes'] for primitive in mesh['primitives'])
        assert path.stat().st_size < PARAMETERS['max_glb_bytes']
        print(device, path.stat().st_size, 'bytes')


def main():
    if '--worker' in sys.argv:
        export()
        return
    receipt_path = OUT/'receipt.json'
    receipt_path.unlink(missing_ok=True)
    subprocess.run([determinism.BLENDER, '-b', '--factory-startup', '-noaudio', '--python-exit-code', '1',
                    '-P', str(Path(__file__).resolve()), '--', '--worker'], check=True)
    result = {'blender': determinism.blender_build(), 'parameters': PARAMETERS,
              'parameter_locator': 'films/lib/blender/export_devices.py:PARAMETERS',
              'source_sha256': determinism.file_sha256(Path(__file__)),
              'bead_cube_sha256': determinism.file_sha256(HERE/'bead_cube.blend'),
              'exports': {device: {'path': str((OUT/f'{device}.glb').relative_to(ROOT)),
                  'bytes': (OUT/f'{device}.glb').stat().st_size,
                  'sha256': determinism.file_sha256(OUT/f'{device}.glb'),
                  'draco': True, 'cameras': False, 'animations': False,
                  'state_machine': 'scripts/audit_device.py:models'} for device in DEVICES},
              'non_claims': ['Geometry only: permitted moves come from generated T1 transition tables.',
                  'No whole-world export; no external world file was opened.',
                  'Browser loading is separately tested; byte size alone does not establish loading or fidelity.',
                  'Only the bounded digital models have meshes; no physical or learner outcome is asserted.']}
    receipt_path.write_text(json.dumps(result, indent=2)+'\n')

if __name__ == '__main__':
    main()
