#!/usr/bin/env node
// Run against a local static server. PLAYWRIGHT_MODULE can select the bundled runtime.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const base = process.env.FOUNDATIONS_BASE_URL || 'http://127.0.0.1:8765';
const tables = JSON.parse(fs.readFileSync(path.join(root, 'assets/foundations/states.json'))).devices;
const output = path.join(root, '_private/foundations-browser');
fs.mkdirSync(output, {recursive:true});
(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const context = await browser.newContext({viewport:{width:1280,height:900}});
  const page = await context.newPage();
  const errors = [];
  const requests = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('request', r => requests.push(r.url()));
  await page.goto(base+'/foundations/');
  await page.waitForFunction(() => document.documentElement.classList.contains('enhanced'));
  assert.equal(await page.locator('#after-answer').isVisible(), false);
  assert.equal(requests.some(url => /\.glb|three\.module|states\.json/.test(url)), false);
  assert.equal(await page.locator('canvas').count(), 0);
  await page.screenshot({path:path.join(output, 'desktop-before.png')});
  await page.locator('input[value="0"]').check();
  await page.locator('.submit').click();
  assert.equal(await page.locator('.readout:visible').count(), 1);
  assert.match(await page.locator('.readout:visible').innerText(), /odd-parity world/);
  await page.locator('.load-device').click();
  await page.waitForFunction(() => document.querySelector('.device-panel').dataset.loaded || document.querySelector('.device-panel').dataset.error);
  assert.equal(await page.locator('.device-panel').getAttribute('data-error'), null);
  const before = await page.locator('.state-readout').innerText();
  await page.locator('.moves button').first().click();
  const after = await page.locator('.state-readout').innerText();
  assert.notEqual(before, after);
  await page.locator('.device-panel').screenshot({path:path.join(output, 'bead-device.png')});
  await page.locator('.projection-proof').screenshot({path:path.join(output, 'projection-proof.png')});
  await page.locator('input[value="1"]').check();
  await page.locator('.submit').click();
  assert.equal(await page.evaluate(() => document.activeElement.id), 'non-claim');
  assert.equal(await page.locator('.readout:visible').count(), 1);
  await page.goto(base+'/foundations/meshes/');
  const results = [];
  for (const [device, table] of Object.entries(tables)) {
    const panel = page.locator(`[data-device="${device}"]`);
    await panel.locator('.load-device').click();
    await page.waitForFunction(id => {
      const p = document.querySelector(`[data-device="${id}"]`);
      return p.dataset.loaded || p.dataset.error;
    }, device);
    assert.equal(await panel.getAttribute('data-error'), null, device);
    assert.equal(await panel.locator('canvas').count(), 1);
    // Walk actual buttons to every state using BFS paths on the Python table.
    for (let goal = 0; goal < table.states.length; goal++) {
      const start = Number(await panel.getAttribute('data-state-index'));
      const queue = [[start, []]], visited = new Set([start]);
      let route;
      while (queue.length) {
        const [node, steps] = queue.shift();
        if (node === goal) {route = steps; break;}
        for (const next of table.moves[node]) if (!visited.has(next)) {
          visited.add(next); queue.push([next, [...steps, next]]);
        }
      }
      assert.ok(route, device);
      for (const next of route) {
        await panel.locator(`button[data-next="${next}"]`).click();
        assert.equal(Number(await panel.getAttribute('data-state-index')), next);
      }
      const allowed = await panel.locator('.moves button').evaluateAll(bs => bs.map(b => Number(b.dataset.next)));
      assert.deepEqual(allowed, table.moves[goal]);
    }
    await panel.screenshot({path:path.join(output, device+'.png')});
    results.push({device, loaded:true, reachable_states:table.states.length, locator:`assets/foundations/states.json:devices.${device}`});
  }
  // Exercise interpreter rejection independently of the visible controls.
  const rejected = await page.evaluate(async () => {
    const {machine} = await import('/assets/foundations/machine.js');
    const {devices} = await (await fetch('/assets/foundations/states.json')).json();
    return Object.values(devices).every(table => {
      const m = machine(table);
      try {m.move(-1); return false;} catch {return m.index === table.initial;}
    });
  });
  assert.ok(rejected);
  const mobile = await context.newPage();
  await mobile.setViewportSize({width:390,height:844});
  await mobile.goto(base+'/foundations/');
  assert.ok(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await mobile.screenshot({path:path.join(output, 'mobile-before.png')});
  const nojs = await browser.newContext({javaScriptEnabled:false, viewport:{width:1280,height:900}});
  const staticPage = await nojs.newPage();
  for (let i=1; i<=10; i++) {
    const id = `d-${String(i).padStart(3,'0')}`;
    await staticPage.goto(base+`/foundations/${id}/`);
    assert.equal(await staticPage.locator('.option:visible').count(), 4, id);
    assert.equal(await staticPage.locator('.readout:visible').count(), 4, id);
    assert.equal(await staticPage.locator('.readout .excluded:visible').count(), 4, id);
    assert.ok(await staticPage.locator('#non-claim').isVisible(), id);
    assert.ok(await staticPage.locator('.claim-exit').isVisible(), id);
    assert.equal(await staticPage.locator('canvas').count(), 0, id);
  }
  await staticPage.goto(base+'/foundations/');
  await staticPage.screenshot({path:path.join(output, 'no-js.png'), fullPage:true});
  assert.deepEqual(errors, []);
  assert.equal(requests.some(url => !url.startsWith(base) && !url.startsWith('blob:')), false);
  const sources = ['assets/foundations/viewer.js', 'assets/foundations/machine.js',
    'assets/foundations/foundations.js', 'assets/foundations/foundations.css',
    'assets/foundations/states.json', 'assets/foundations/meshes/receipt.json',
    'scripts/test_foundations_browser.cjs', 'scripts/generate_foundations.py', 'docs/foundations/devices.yaml'];
  const sourceHashes = Object.fromEntries(sources.map(file => [file,
    crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex')]));
  const receipt = {browser:await browser.version(), source_sha256:sourceHashes, exports:results, no_js_nodes:10,
    no_js_locator:'docs/foundations/devices.yaml:devices',
    checks:['answer gating', 'branch selection', 'skip repair', 'all mesh loads', 'all reachable UI states', 'illegal move rejected', 'no external requests', 'mobile overflow', 'no-JS readouts'],
    non_claims:['One local Chrome build only; no cross-browser or assistive-technology certification.',
      'No learner outcome, physical device fidelity, or independent audit is established.']};
  fs.writeFileSync(path.join(output, 'receipt.json'), JSON.stringify(receipt,null,2)+'\n');
  fs.writeFileSync(path.join(root, 'assets/foundations/meshes/browser.receipt.json'), JSON.stringify(receipt,null,2)+'\n');
  console.log(JSON.stringify(receipt,null,2));
  await browser.close();
})().catch(e => {console.error(e); process.exitCode=1;});
