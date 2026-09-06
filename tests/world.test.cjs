const {test} = require('node:test');
const assert = require('node:assert/strict');
const {solve} = require('../assets/world.js');
const near = (actual, expected) => assert.ok(Math.abs(actual-expected)<1e-10, `${actual} != ${expected}`);

test('every witness is a normalized joint distribution with the requested marginals', () => {
  for(let ai=0;ai<=100;ai++) for(let bi=0;bi<=100;bi++) {
    const a=ai/100,b=bi/100;
    for(const position of [0,.25,.5,.75,1]) {
      const r=solve(a,b,'marginals',0,1,position);
      assert.ok(r.valid);
      r.cells.forEach(x=>assert.ok(x>=0&&x<=1+1e-12));
      near(r.cells.reduce((s,x)=>s+x,0),1);
      near(r.cells[1]+r.cells[3],a);near(r.cells[2]+r.cells[3],b);
      if(position===0) assert.ok(Math.min(...r.cells)<1e-10);
      if(position===1) assert.ok(Math.min(...r.cells)<1e-10);
      const flipped=solve(b,a,'marginals',0,1,position);
      near(flipped.q,r.q);near(flipped.cells[1],r.cells[2]);
    }
    const independent=solve(a,b,'independence',0,1,.5);
    near(independent.q,a*b);near(independent.l,independent.u);
    near(independent.cells[0],(1-a)*(1-b));
  }
});

test('finite ten-item worlds attain exactly the feasible overlap counts',()=>{
  for(let a=0;a<=10;a++)for(let b=0;b<=10;b++){
    const possible=[];
    for(let mask=0;mask<1024;mask++){
      const selected=Array.from({length:10},(_,i)=>(mask>>i)&1);
      if(selected.reduce((s,v)=>s+v,0)!==b)continue;
      possible.push(selected.slice(0,a).reduce((s,v)=>s+v,0));
    }
    const r=solve(a/10,b/10,'marginals',0,1,0);
    near(r.l,Math.min(...possible)/10);near(r.u,Math.max(...possible)/10);
  }
});

test('additional constraints intersect rather than silently replace the marginal set',()=>{
  const r=solve(.1,.1,'interval',.02,.06,.5);
  near(r.l,.02);near(r.u,.06);near(r.q,.04);
  assert.equal(solve(.1,.1,'interval',.2,.3,.5).valid,false);
  assert.equal(solve(.1,.1,'interval',.06,.02,.5).valid,false);
  assert.equal(solve(.1,.1,'interval',NaN,.02,.5).valid,false);
  assert.equal(solve(.8,.8,'interval',0,.5,.5).valid,false);
  const touching=solve(.8,.8,'interval',.6,.6,.5);
  assert.ok(touching.valid);near(touching.q,.6);
});

test('invalid probabilities and modes are refused',()=>{
  for(const x of [-.1,1.1,NaN,Infinity])assert.throws(()=>solve(x,.1,'marginals',0,1,.5),RangeError);
  assert.throws(()=>solve(.1,.1,'unrecognized',0,1,.5),RangeError);
});
