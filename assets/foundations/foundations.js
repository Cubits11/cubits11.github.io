// Content exists in the generated HTML; this only selects an answer branch.
const form = document.querySelector('.hinge-form');
const readouts = document.querySelector('#readouts');
const branches = [...document.querySelectorAll('.readout')];
const panel = document.querySelector('.device-panel');
const proof = document.querySelector('.projection-proof');
if (form && readouts) {
  document.documentElement.classList.add('enhanced');
  const after = document.querySelector('#after-answer');
  after.hidden = true;
  readouts.hidden = true;
  if (panel) panel.hidden = true;
  if (proof) proof.hidden = true;
  let viewerReady = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const selected = new FormData(form).get('answer');
    const branch = branches.find(b => b.dataset.answer === selected);
    if (!branch) return;
    branches.forEach(b => {b.hidden = b !== branch;});
    after.hidden = false;
    readouts.hidden = false;
    if (panel) panel.hidden = false;
    if (proof) proof.hidden = false;
    history.replaceState(null, '', `#${branch.id}`);
    // A held concept bypasses repair. Its excluded-world readout remains available.
    const target = branch.dataset.skip === 'true' ? document.querySelector('#non-claim') : readouts;
    target.focus(); target.scrollIntoView({behavior:'instant', block:'start'});
    if (panel && !viewerReady) {
      try {
        const {setupPanel} = await import('./viewer.js');
        setupPanel(panel); viewerReady = true;
      } catch {
        panel.querySelector('.mesh-status').textContent = 'The mesh is unavailable. The text exercise remains available.';
      }
    }
  });
}
