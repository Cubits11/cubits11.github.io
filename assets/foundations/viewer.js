import * as THREE from 'three';
import { GLTFLoader } from './vendor/three/loaders/GLTFLoader.js';
import { DRACOLoader } from './vendor/three/loaders/DRACOLoader.js';
import { machine } from './machine.js';
let tablesPromise;
function tables() {
  return tablesPromise ||= fetch('/assets/foundations/states.json').then(r => {
    if (!r.ok) throw new Error('State table unavailable');
    return r.json();
  }).then(r => r.devices);
}
// Names identify meshes, not rules. All reachable values are supplied by T1.
function drawState(root, device, state) {
  const object = name => {
    const found = root.getObjectByName(name);
    if (!found) throw new Error(`Missing device mesh: ${name}`);
    return found;
  };
  if (device === 'D-007') state.forEach((p, i) => object(`bead_${i}`).position.set(p[0], p[2], -p[1]));
  if (device === 'D-002') {
    for (let i = 0; i < 10; i++) {
      // Shift the second strip: its overlap with the first is exactly state coins.
      object(`coin_1_${i}`).position.x = (i + 10 - state) * 0.22;
      object(`coin_1_${i}`).position.y = 0.06;
      object(`coin_1_${i}`).position.z = 0;
    }
  }
  if (device === 'D-003') object('link').visible = state === 'both-must-open';
  if (device === 'D-004') object('ruler').position.x = state.filter(n => n === 0).length * 0.16 - 0.08;
  if (device === 'D-005') {
    object('whole_page').visible = state === 'whole-page';
    object('slip').visible = state === 'slip';
  }
  if (device === 'D-006') object('selector').position.x = (state - 1) * 0.4;
}
export function describe(device, state) {
  if (device === 'D-002') return `Overlap ${state}/100; each reader misses 10/100. Integer coin grid only.`;
  if (device === 'D-004') return `Cut after ${state.filter(n => n === 0).length} of ${state.length} ordered objects; selected suffix ${state.join('')}.`;
  if (device === 'D-007') {
    const occupied = state.some(p => p.every(n => n === 1));
    return `Occupied corners: ${state.map(p => p.join('')).join(', ')}. Each face bin contains one bead. Corner 111: ${occupied ? '1/4' : '0/4'}. Constructed worlds only.`;
  }
  if (device === 'D-006') return `Selected local cell value: ${state}. Permitted set: {2, 3, 4}. Representative local constraints only.`;
  return `Configuration: ${state}.`;
}
export function setupPanel(panel) {
  panel.dataset.ready = "true";
  const trigger = panel.querySelector('.load-device');
  const status = panel.querySelector('.mesh-status');
  trigger.addEventListener('click', async () => {
    trigger.disabled = true;
    status.textContent = 'Opening device geometry…';
    let renderer, draco;
    try {
      const device = panel.dataset.device;
      const table = (await tables())[device];
      if (!table) throw new Error('No audited model for this device');
      const controller = machine(table);
      const view = panel.querySelector('.mesh-view');
      renderer = new THREE.WebGLRenderer({antialias:true, alpha:false});
      renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      view.hidden = false;
      view.append(renderer.domElement);
      const scene = new THREE.Scene();
      scene.background = new THREE.Color('#101a18');
      draco = new DRACOLoader();
      draco.setDecoderPath('/assets/foundations/vendor/three/draco/');
      const loader = new GLTFLoader().setDRACOLoader(draco);
      const gltf = await loader.loadAsync(`/assets/foundations/meshes/${device}.glb`);
      if (gltf.animations.length || gltf.cameras.length) throw new Error('Unexpected animation or camera in device mesh');
      scene.add(gltf.scene);
      // Frame the union of all permitted geometry poses, avoiding camera changes on moves.
      const bounds = new THREE.Box3();
      for (const state of table.states) {
        drawState(gltf.scene, device, state);
        gltf.scene.updateMatrixWorld(true);
        bounds.union(new THREE.Box3().setFromObject(gltf.scene));
      }
      drawState(gltf.scene, device, controller.state);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = Math.max(...bounds.getSize(new THREE.Vector3()).toArray(), 1);
      const camera = new THREE.PerspectiveCamera(38, 1, .01, 100);
      camera.position.copy(center).add(new THREE.Vector3(size*1.2, size*1.4, size*2));
      camera.lookAt(center);
      const render = () => {
        const width = Math.max(view.clientWidth, 1), height = Math.max(view.clientHeight, 1);
        renderer.setSize(width, height, false);
        camera.aspect = width/height; camera.updateProjectionMatrix();
        renderer.render(scene, camera);
      };
      const update = () => {
        drawState(gltf.scene, device, controller.state);
        panel.dataset.stateIndex = String(controller.index);
        panel.querySelector('.state-readout').textContent = describe(device, controller.state);
        const moves = panel.querySelector('.moves'); moves.replaceChildren();
        for (const next of controller.moves) {
          const button = document.createElement('button'); button.type = 'button';
          button.textContent = `Move to ${describe(device, table.states[next])}`;
          button.dataset.next = String(next);
          button.addEventListener('click', () => {controller.move(next); update();});
          moves.append(button);
        }
        render();
      };
      new ResizeObserver(render).observe(view);
      update();
      panel.dataset.loaded = 'true';
      status.textContent = 'Geometry loaded. Only audited moves are available.';
      trigger.hidden = true;
      draco.dispose();
    } catch (error) {
      renderer?.dispose(); draco?.dispose();
      panel.querySelector('.mesh-view').replaceChildren();
      panel.querySelector('.mesh-view').hidden = true;
      status.textContent = 'The mesh could not open. The full text exercise remains available.';
      panel.dataset.error = String(error);
      trigger.disabled = false;
    }
  });
}
