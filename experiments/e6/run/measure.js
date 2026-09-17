#!/usr/bin/env node
// E6 — how much of a scenario model's output is fixed by the marginals alone.
//
// Extracts the client-side model kernel that anthropic.com/institute/econ-scenarios
// ships, validates it against the twelve printed numbers of Table 3 of the companion
// technical report, and then evaluates it at parameter vectors built only from the
// five marginal quantiles the report prints in Table 2.
//
// Exit codes follow this repository's convention:
//   0  every gate passed and rows were written
//   1  a gate FAILED — a check ran and did not hold
//   2  a gate could NOT BE EVALUATED — the source was unreachable or the digest
//      did not match. This is NOT a pass and NOT a refutation. Nothing is recorded.
'use strict';
const fs=require('fs'), path=require('path'), crypto=require('crypto');

const E6   = path.resolve(__dirname,'..');
const SRC  = JSON.parse(fs.readFileSync(path.join(E6,'freeze/sources.json'),'utf8'));
const KERN = SRC.artifacts.find(a=>a.slot==='KERNEL');
const CACHE= path.join(E6,'freeze/cache/bundle-chunk.js');

const die =(code,msg)=>{ console.error(`E6 EXIT ${code}: ${msg}`); process.exit(code); };
const near=(a,b,tol)=>Math.abs(a-b)<=tol;

// ---------------------------------------------------------------- 1. the bytes
function loadKernelBytes(){
  if(!fs.existsSync(CACHE))
    die(2,`kernel bytes absent at ${path.relative(process.cwd(),CACHE)}. `+
          `Fetch ${KERN.url} (an ephemeral build-hashed path; see sources.json url_stability) `+
          `or restore the pinned bytes from an archive. A missing source is not a refutation.`);
  const buf=fs.readFileSync(CACHE);
  const got=crypto.createHash('sha256').update(buf).digest('hex');
  if(got!==KERN.sha256)
    die(2,`kernel digest mismatch.\n  expected ${KERN.sha256}\n  got      ${got}\n`+
          `These are different bytes from the ones E6 pinned. Re-pin deliberately and note that it is a different kernel.`);
  return buf.toString('utf8');
}

// ------------------------------------------------- 2. reach inside the closure
// The kernel is one minified Turbopack module. Its model functions are module
// locals, not exports, so we take the factory's own source, append a
// closure-scoped eval probe, and re-instantiate it. Nothing is patched or
// rewritten: the arithmetic that runs is the arithmetic Anthropic ships.
function extractKernel(src){
  const captured=[];
  const g=Function('return this')();
  g.TURBOPACK={push:(arr)=>{ for(let i=1;i<arr.length;i+=2) captured.push({id:arr[i],fn:arr[i+1]}); }};
  try{ (0,eval)(src); }catch(e){ die(2,`kernel bytes did not evaluate: ${e.message}`); }
  const target=captured.find(c=>String(c.id)===String(KERN.turbopack_module_id));
  if(!target) die(2,`Turbopack module ${KERN.turbopack_module_id} not present in these bytes`);
  let fsrc=target.fn.toString();
  const cut=fsrc.lastIndexOf('}');
  fsrc=fsrc.slice(0,cut)+';globalThis.__E6=function(x){return eval(x)};'+fsrc.slice(cut);
  const inert=new Proxy(function(){},{get:()=>inert,apply:()=>inert,construct:()=>inert});
  try{ (0,eval)('('+fsrc+')')({i:()=>inert,s:()=>{},v:()=>{},n:()=>{}}); }
  catch(e){ die(2,`module factory did not run: ${e.message}`); }
  if(!g.__E6) die(2,'closure probe not installed');
  return g.__E6;
}

// ------------------------------------------------------- 3. the model interface
const T_ANCHOR=2026.5;
function makeModel(P){
  const at=(series,t=2030)=>{ const r=series.filter(p=>Math.abs(p.t-t)<1e-9);
                              return r.length?r[0].v:series[series.length-1].v; };
  // Build the model's input object at an explicit five-vector, holding the four
  // parameters the note to Table 4 names at the substantial scenario's values.
  function inputsAt(v){
    const c=P('ev')('central');                 // 'central' is the substantial scenario
    const i=JSON.parse(JSON.stringify(c));
    i.production.w={x0:c.production.w.x0, x30:v.m2030, xb:c.production.w.xb};
    i.production.d={x0:c.production.d.x0, x30:v.d2030, xb:c.production.d.xb};
    i.production.a={x0:c.production.a.x0, g:(v.a2030-c.production.a.x0)/(2030-T_ANCHOR)};
    i.labor.phi ={x0:v.psi, xb:v.psi, k:P('eV')};
    i.labor.mu  = v.mu;
    return i;
  }
  function outcomes(inp){
    const gdp=P('sb')(inp), un=P('sT')(inp), unA=P('sL')(inp), cents=P('sM')(inp);
    return {
      gdp_pct_above_noAI: 100*(at(gdp.ai)/at(gdp.base)-1),
      unemp_all_pct:      at(un.rate),
      unemp_cognitive_pct:at(unA.affected),
      labor_share_pct:    at(cents),
    };
  }
  return {
    scenario:(k)=>outcomes(P('ev')(k)),
    at:(v)=>outcomes(inputsAt(v)),
  };
}

// --------------------------------------------------------------- 4. the gates
function gateTable3(M){
  const want=SRC.published_comparators.table3_2030;
  const map={modest:'conservative', substantial:'central', extreme:'fast'};
  const rows=[]; let fails=0;
  for(const [name,key] of Object.entries(map)){
    const got=M.scenario(key), w=want[name];
    for(const f of ['gdp_pct_above_noAI','unemp_all_pct','unemp_cognitive_pct','labor_share_pct']){
      // the report prints one decimal; agreement is to that precision
      const ok=near(Math.round(got[f]*10)/10, w[f], 0.05001);
      if(!ok) fails++;
      rows.push({scenario:name, field:f, kernel:+got[f].toFixed(4), printed:w[f], agrees:ok});
    }
  }
  if(fails) { console.error(JSON.stringify(rows.filter(r=>!r.agrees),null,1));
              die(1,`extracted kernel disagrees with ${fails} of 12 printed Table 3 numbers`); }
  return rows;
}

const Q=(()=>{const p=SRC.marginals.parameters; const o={};
  for(const k of Object.keys(p)) o[k]=[p[k].q25,p[k].q50,p[k].q75]; return o;})();
const KEYS=Object.keys(Q);
const MED=Object.fromEntries(KEYS.map(k=>[k,Q[k][1]]));

function gateMonotone(M){
  const rows=[]; let bad=0;
  for(const k of KEYS){
    const vals=Q[k].map(x=>M.at({...MED,[k]:x}).gdp_pct_above_noAI);
    const inc = vals[0]<vals[1] && vals[1]<vals[2];
    if(!inc) bad++;
    rows.push({parameter:k, at:Q[k], gdp:vals.map(v=>+v.toFixed(4)), increasing:inc});
  }
  if(bad) { console.error(JSON.stringify(rows,null,1));
            die(1,`GDP is not monotone increasing in ${bad} of ${KEYS.length} parameters; `+
                  `the comonotone quantile identity does not apply and no comonotone figure may be reported`); }
  return rows;
}

// ------------------------------------------------------------ 5. the couplings
const W=[0.25,0.50,0.25];
const quantile=(pairs,q)=>{ const s=[...pairs].sort((a,b)=>a.v-b.v); let acc=0;
  for(const p of s){ acc+=p.w; if(acc>=q-1e-12) return p.v; } return s[s.length-1].v; };
const permutations=(n)=>{ const out=[]; (function go(a,rest){ if(!rest.length) return void out.push(a);
  rest.forEach((x,i)=>go([...a,x],rest.filter((_,j)=>j!==i))); })([],[...Array(n).keys()]); return out; };

function main(){
  const P=extractKernel(loadKernelBytes());
  const M=makeModel(P);

  const table3   = gateTable3(M);
  const monotone = gateMonotone(M);

  // --- primary quantities: no discretionary choice anywhere in these
  const vecMedian = M.at(MED);
  const vecQ25    = M.at(Object.fromEntries(KEYS.map(k=>[k,Q[k][0]])));
  const vecQ75    = M.at(Object.fromEntries(KEYS.map(k=>[k,Q[k][2]])));

  // --- the 243 cells of the declared three-point discretisation
  const cells=[]; const idx=[0,1,2];
  for(const a of idx) for(const b of idx) for(const c of idx) for(const d of idx) for(const e of idx){
    const v={m2030:Q.m2030[a], d2030:Q.d2030[b], psi:Q.psi[c], a2030:Q.a2030[d], mu:Q.mu[e]};
    const o=M.at(v);
    cells.push({cell:[a,b,c,d,e], vector:v, weight_independent:[a,b,c,d,e].reduce((p,k)=>p*W[k],1), ...o});
  }
  const byCell=new Map(cells.map(c=>[c.cell.join(''),c]));
  const asPairs=(sel,f)=>sel.map(s=>({v:f(s.c), w:s.w}));

  const comonotone = idx.map(k=>({c:byCell.get([k,k,k,k,k].join('')), w:W[k]}));
  const independent= cells.map(c=>({c, w:c.weight_independent}));
  const G=x=>x.gdp_pct_above_noAI, U=x=>x.unemp_all_pct;

  // range of the median over every rank-permutation coupling of the same marginals
  const perms=permutations(3); let lo=Infinity, hi=-Infinity, nperm=0;
  for(const p1 of perms) for(const p2 of perms) for(const p3 of perms) for(const p4 of perms){
    const pairs=idx.map(k=>({v:G(byCell.get([k,p1[k],p2[k],p3[k],p4[k]].join(''))), w:W[k]}));
    const m=quantile(pairs,0.5); if(m<lo)lo=m; if(m>hi)hi=m; nperm++;
  }

  const r4=x=>+x.toFixed(4);
  const result={
    experiment:'E6',
    preregistered:false,
    generated:process.env.E6_STAMP||null,
    kernel_sha256:KERN.sha256,
    gates:{ table3_agreement:'PASS', monotonicity:'PASS' },
    table3_check:table3,
    monotonicity:monotone,
    primary:{
      note:'every input here is a numeral printed in the source artifacts; no discretionary choice enters',
      at_vector_of_published_medians:{ gdp_pct_above_noAI:r4(vecMedian.gdp_pct_above_noAI),
        unemp_all_pct:r4(vecMedian.unemp_all_pct), unemp_cognitive_pct:r4(vecMedian.unemp_cognitive_pct),
        labor_share_pct:r4(vecMedian.labor_share_pct) },
      published_joint_median:SRC.published_comparators.table4_survey_joint,
      comonotone_quartiles_gdp:[r4(vecQ25.gdp_pct_above_noAI), r4(vecQ75.gdp_pct_above_noAI)],
      published_joint_quartiles_gdp:[SRC.published_comparators.table4_survey_joint.gdp_pct_above_noAI.q25,
                                     SRC.published_comparators.table4_survey_joint.gdp_pct_above_noAI.q75],
    },
    secondary:{
      note:'these rest on the declared three-point discretisation in sources.json and are an INNER bound',
      cells:cells.length,
      median_gdp:{
        comonotone: r4(quantile(asPairs(comonotone,G),0.5)),
        independent:r4(quantile(asPairs(independent,G),0.5)),
        published_joint:SRC.published_comparators.table4_survey_joint.gdp_pct_above_noAI.q50,
      },
      median_unemp_all:{
        comonotone: r4(quantile(asPairs(comonotone,U),0.5)),
        independent:r4(quantile(asPairs(independent,U),0.5)),
        published_joint:SRC.published_comparators.table4_survey_joint.unemp_all_pct.q50,
      },
      mean_gdp:{
        comonotone: r4(comonotone.reduce((s,x)=>s+x.w*G(x.c),0)/comonotone.reduce((s,x)=>s+x.w,0)),
        independent:r4(independent.reduce((s,x)=>s+x.w*G(x.c),0)/independent.reduce((s,x)=>s+x.w,0)),
      },
      mean_unemp_all:{
        comonotone: r4(comonotone.reduce((s,x)=>s+x.w*U(x.c),0)/comonotone.reduce((s,x)=>s+x.w,0)),
        independent:r4(independent.reduce((s,x)=>s+x.w*U(x.c),0)/independent.reduce((s,x)=>s+x.w,0)),
      },
      median_gdp_over_rank_permutation_couplings:{ couplings:nperm, min:r4(lo), max:r4(hi) },
      support_gdp:[r4(Math.min(...cells.map(G))), r4(Math.max(...cells.map(G)))],
    },
  };

  fs.writeFileSync(path.join(E6,'results/e6_result.json'), JSON.stringify(result,null,1)+'\n');
  const out=fs.createWriteStream(path.join(E6,'results/observations.jsonl'));
  for(const c of cells) out.write(JSON.stringify({
    experiment:'E6', kernel_sha256:KERN.sha256, cell:c.cell.join(''),
    m2030:c.vector.m2030, d2030:c.vector.d2030, psi:c.vector.psi, a2030:c.vector.a2030, mu:c.vector.mu,
    weight_independent:c.weight_independent,
    gdp_pct_above_noAI:r4(c.gdp_pct_above_noAI), unemp_all_pct:r4(c.unemp_all_pct),
    unemp_cognitive_pct:r4(c.unemp_cognitive_pct), labor_share_pct:r4(c.labor_share_pct),
  })+'\n');
  out.end();

  console.log('E6 gates PASSED — Table 3 reproduced (12/12), GDP monotone in all five parameters\n');
  console.log('median 2030 GDP, pct above the no-AI path, from ONE set of five marginals:');
  console.log('  comonotone coupling  (perfect rank agreement) ', result.secondary.median_gdp.comonotone);
  console.log('  independent coupling                          ', result.secondary.median_gdp.independent);
  console.log('  the joint Anthropic measured (Table 4)        ', result.secondary.median_gdp.published_joint);
  console.log('  range over all', nperm, 'rank-permutation couplings [',
              result.secondary.median_gdp_over_rank_permutation_couplings.min, ',',
              result.secondary.median_gdp_over_rank_permutation_couplings.max, ']');
  console.log('\nat the vector of published medians:', result.primary.at_vector_of_published_medians.gdp_pct_above_noAI,
              'GDP /', result.primary.at_vector_of_published_medians.unemp_all_pct, 'unemployment');
  console.log('rows written:', cells.length);
}
main();
