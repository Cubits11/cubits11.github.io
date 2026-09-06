/* An illustrative two-event probability model; never measured system data.
 * Order of witness cells: neither, A only, B only, both.
 * The pure kernel is exported for numerical tests and the browser renderer.
 */
(function (root) {
  'use strict';
  function solve(a, b, mode, low, high, position) {
    if (![a, b, position].every(Number.isFinite) || a < 0 || a > 1 || b < 0 || b > 1 || position < 0 || position > 1) throw new RangeError('Invalid probability');
    if (!['marginals', 'independence', 'interval'].includes(mode)) throw new RangeError('Unknown assumption');
    const lower = Math.max(0, a + b - 1), upper = Math.min(a, b);
    let l = lower, u = upper;
    if (mode === 'independence') l = u = a * b;
    if (mode === 'interval') {
      if (![low, high].every(Number.isFinite) || low < 0 || high > 1 || low > high) return {valid:false, lower, upper, reason:'Enter an ordered interval between 0% and 100%.'};
      l = Math.max(lower, low); u = Math.min(upper, high);
    }
    if (l > u + 1e-12) return {valid:false, lower, upper, reason:'No compatible world. This joint constraint contradicts the marginal rates.'};
    // Round-off at touching interval endpoints must not create negative cells.
    u = Math.max(l, u);
    const q = l + position * (u - l);
    const cells = [1 - a - b + q, a - q, b - q, q].map(x => Math.max(0, x));
    return {valid:true, lower, upper, l, u, q, cells, independence:a*b};
  }
  root.CubitsWorld = Object.freeze({solve});
  if (typeof module !== 'undefined') module.exports = {solve};
  if (typeof document === 'undefined' || !document.getElementById('world-bench')) return;
  const $ = id => document.getElementById(id);
  const themeButton = $('themeToggle');
  const darkPreference = window.matchMedia('(prefers-color-scheme: dark)');
  const theme = () => document.documentElement.dataset.theme || (darkPreference.matches ? 'dark' : 'light');
  const syncTheme = () => {themeButton.setAttribute('aria-pressed',String(theme()==='dark'));document.querySelector('meta[name="theme-color"]').content=theme()==='dark'?'#0B0F0A':'#F1EDE2';};
  themeButton.addEventListener('click',()=>{const next=theme()==='dark'?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('theme',next);}catch(e){}syncTheme();});
  darkPreference.addEventListener('change',syncTheme);
  syncTheme();
  const pct = n => (n * 100).toFixed(2).replace(/\.00$/, '').replace(/(\.\d)0$/, '$1') + '%';
  const controls = ['rate-a','rate-b','world-position','joint-low','joint-high'];
  const fieldsets = document.querySelectorAll('#world-bench fieldset');
  fieldsets.forEach(el => {el.disabled = false;});
  $('bench-reset').disabled = false;
  $('bench-nojs').hidden = true;
  function draw() {
    const a = Number($('rate-a').value)/100, b = Number($('rate-b').value)/100;
    const mode = document.querySelector('input[name=world-mode]:checked').value;
    const low = $('joint-low').value === '' ? NaN : Number($('joint-low').value)/100;
    const high = $('joint-high').value === '' ? NaN : Number($('joint-high').value)/100;
    const result = solve(a, b, mode, low, high, Number($('world-position').value)/100);
    $('a-value').textContent = pct(a); $('b-value').textContent = pct(b);
    $('joint-inputs').hidden = mode !== 'interval';
    $('world-witness').hidden = !result.valid;
    $('world-position').disabled = !result.valid || result.u === result.l;
    document.querySelectorAll('[data-world-position]').forEach(el => {el.disabled = !result.valid || result.u === result.l;});
    $('bench-status').dataset.invalid = String(!result.valid);
    $('world-constraint').textContent = mode === 'independence' ? 'ASSUMPTION · independence' : mode === 'interval' ? 'CONSTRUCTION · hypothetical joint constraint' : 'DERIVED · marginals alone';
    $('world-range').textContent = result.valid ? (result.u-result.l < 1e-12 ? pct(result.l) : pct(result.l)+'–'+pct(result.u)) : 'Empty set';
    $('world-band').hidden = !result.valid;
    if (result.valid) {
      $('world-band').style.left = result.l*100+'%'; $('world-band').style.width = (result.u-result.l)*100+'%';
    }
    $('world-independence').style.left = a*b*100+'%';
    $('independence-value').textContent = pct(a*b);
    $('world-position').setAttribute('aria-valuetext', result.valid ? pct(result.q)+' both miss' : 'No compatible world');
    if (!result.valid) {$('selected-value').textContent = 'None';$('bench-status').textContent = result.reason; return;}
    const [neither, onlyA, onlyB, both] = result.cells;
    ['neither','only-a','only-b','both'].forEach((name,i) => {$('cell-'+name).textContent = pct(result.cells[i]);});
    $('selected-value').textContent = pct(both);
    const leftHeight = a > 0 ? qSafe(both/a)*200 : 0;
    const rightHeight = a < 1 ? qSafe(onlyB/(1-a))*200 : 0;
    setRect('rect-both',0,0,a*200,leftHeight);
    setRect('rect-only-a',0,leftHeight,a*200,200-leftHeight);
    setRect('rect-only-b',a*200,0,(1-a)*200,rightHeight);
    setRect('rect-neither',a*200,rightHeight,(1-a)*200,200-rightHeight);
    $('world-svg-desc').textContent = 'An area-one square. Neither misses: '+pct(neither)+'. A only: '+pct(onlyA)+'. B only: '+pct(onlyB)+'. Both: '+pct(both)+'. Constructed probability distribution.';
    $('bench-status').textContent = mode === 'independence'
      ? 'One world selected by an assumption. You have added no observations.'
      : mode === 'interval' ? 'The interval is your hypothetical input, not a measurement. Only its intersection with the marginal bounds survives.'
      : (result.u-result.l < 1e-12 ? 'These boundary marginals determine the joint rate exactly.' : 'Every point in this interval has a compatible joint distribution. Move through them; the two marginal scores stay fixed.');
  }
  function qSafe(x){return Math.max(0,Math.min(1,x));}
  function setRect(id,x,y,w,h){const el=$(id);Object.entries({x,y,width:w,height:h}).forEach(([key,value])=>el.setAttribute(key,value));}
  controls.forEach(id => $(id).addEventListener('input',draw));
  document.querySelectorAll('input[name=world-mode]').forEach(el=>el.addEventListener('change',draw));
  document.querySelectorAll('[data-world-position]').forEach(el=>el.addEventListener('click',()=>{$('world-position').value=el.dataset.worldPosition;draw();}));
  $('bench-reset').addEventListener('click',()=>{$('rate-a').value=10;$('rate-b').value=10;$('world-position').value=50;$('joint-low').value=2;$('joint-high').value=6;$('mode-marginals').checked=true;draw();});
  draw();
})(typeof globalThis !== 'undefined' ? globalThis : this);
