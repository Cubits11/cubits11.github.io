const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('../assets/check-status.js');
const now = Date.parse('2026-10-17T16:00:00Z');
const sha = 'f2249c113335feb8b2a3ccb9e4cd9951e002592a';
function run(id, day, conclusion, extra = {}) {
  return {id, created_at:`2026-10-${day}T13:00:00Z`, updated_at:`2026-10-${day}T13:05:00Z`,
    head_branch:'main', event:'schedule', status:'completed', conclusion, head_sha:sha,
    html_url:`https://github.com/Cubits11/cubits11.github.io/actions/runs/${id}`, ...extra};
}
class Element {
  constructor(doc) { this.ownerDocument=doc; this.children=[]; this.dataset={}; }
  replaceChildren() { this.children=[]; }
  appendChild(child) { this.children.push(child); return child; }
}
const doc = {createElement(){return new Element(doc)},createTextNode(text){return {textContent:text}}};
function text(node) { return (node.textContent || '') + (node.children || []).map(text).join(''); }
test('latest failure retains its exact revision/run and previous success', () => {
  const model=api.fromRuns({workflow_runs:[run(10,'10','success'),run(12,'12','failure')]},now);
  assert.equal(model.state,'FAILED'); assert.equal(model.revision,sha); assert.equal(model.lastSuccess,'2026-10-10');
  const target=new Element(doc); api.render(target,model);
  assert.match(text(target),/FAILED.*2026-10-12.*f2249c1/);
  assert.equal(target.children.find(x=>x.href).href,'https://github.com/Cubits11/cubits11.github.io/actions/runs/12');
});
test('unavailable requests and HTTP refusal become UNKNOWN, never a cached pass', async () => {
  for(const request of [async()=>{throw Error('offline')},async()=>({ok:false,status:403})]) {
    const target=new Element(doc); const model=await api.load(target,request,now);
    assert.equal(model.state,'UNKNOWN'); assert.match(text(target),/UNKNOWN/); assert.doesNotMatch(text(target),/PASSED/);
  }
});
test('malformed, cancelled, empty and stale observations are UNKNOWN', () => {
  for(const payload of [null,{}, {workflow_runs:[]}, {workflow_runs:[run(1,'12','cancelled')]},
    {workflow_runs:[run(1,'01','success')]}, {workflow_runs:[run(1,'12','success',{html_url:'https://evil.example/'})]}])
    assert.equal(api.fromRuns(payload,now).state,'UNKNOWN');
});
test('new running workflow displaces an earlier pass; PRs cannot masquerade as main checks', () => {
  assert.equal(api.fromRuns({workflow_runs:[run(1,'12','success'),run(2,'17',null,{status:'in_progress'})]},now).state,'RUNNING');
  assert.equal(api.fromRuns({workflow_runs:[run(1,'12','failure'),run(2,'17','success',{event:'pull_request'})]},now).state,'FAILED');
});
test('a request which returns invalid JSON is UNKNOWN',async()=>{
  const model=await api.load(new Element(doc),async()=>({ok:true,json:async()=>{throw Error('invalid JSON')}}),now);
  assert.equal(model.state,'UNKNOWN');
});
test('an unusable newest failure never falls back to an older pass',()=>{
  const payload={workflow_runs:[run(1,'10','success'),run(2,'12','failure',{html_url:null})]};
  assert.equal(api.fromRuns(payload,now).state,'UNKNOWN');
  payload.workflow_runs[1].created_at='not a date';
  assert.equal(api.fromRuns(payload,now).state,'UNKNOWN');
});
test('a truncated run history does not imply there has never been a success',()=>{
  const model=api.fromRuns({workflow_runs:[run(12,'12','failure')]},now);
  const target=new Element(doc); api.render(target,model);
  assert.match(text(target),/Last successful: not found in the 1 returned main-branch runs/);
});
test('an invalid repository comparison remains UNKNOWN',async()=>{
  const fs=require('node:fs'); const vm=require('node:vm');
  for (const status of [undefined,'unrecognized']) {
    const message={setAttribute(){}};
    const article={dataset:{publicationState:'Published — scoped result',draftRevision:sha},appendChild(){}};
    vm.runInNewContext(fs.readFileSync(require.resolve('../assets/draft-board.js'),'utf8'),{
      document:{querySelectorAll:()=>[article],createElement:()=>message},AbortSignal,
      fetch:async()=>({ok:true,json:async()=>({ahead_by:0,behind_by:0,status})})
    });
    await new Promise(resolve=>setImmediate(resolve));
    assert.match(message.textContent,/Current repository status: UNKNOWN/);
  }
});
