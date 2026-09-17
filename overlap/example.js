/* Fixed common pool, binary misses, either-check-catches rule. */
(function () {
  'use strict';
  function counts(q) {
    if (!Number.isInteger(q) || q < 0 || q > 10) throw new RangeError('Overlap must be an integer from 0 to 10.');
    return {bothMiss:q, aOnly:10-q, bOnly:10-q, bothCatch:80+q};
  }
  if (typeof module !== 'undefined') module.exports = {counts};
  if (typeof document === 'undefined') return;
  const slider = document.getElementById('overlap');
  function update() {
    const q = Number(slider.value), c = counts(q);
    for (const [id,value] of Object.entries({'overlap-value':q,'both-miss':c.bothMiss,'a-only':c.aOnly,'b-only':c.bOnly,'both-catch':c.bothCatch})) document.getElementById(id).textContent = value;
    document.getElementById('result').textContent = `Together they miss ${q} of 100. Adding B to A catches ${c.aOnly} additional faulty cases.`;
    document.getElementById('assumption').textContent = q === 1 ? 'This constructed table satisfies independence: 10% × 10% = 1%. Separate scores alone do not select it.' : q === 0 ? 'Disjoint misses: B catches all 10 faults A missed.' : q === 10 ? 'Identical misses: adding B catches none of the faults A missed.' : 'A possible overlap with the same two separate miss counts. It is not a measured failure rate.';
  }
  slider.addEventListener('input',update);
  for (const button of document.querySelectorAll('[data-overlap]')) button.addEventListener('click',function () {slider.value=this.dataset.overlap;update();});
  update();
}());
