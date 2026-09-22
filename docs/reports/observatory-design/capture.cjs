/* Observational capture, not a release policy. Install playwright and axe-core
   outside the repository, expose them through NODE_PATH, serve repo at 8765.
   Usage: node capture.cjs baseline|after */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const stage=process.argv[2];
if(!['baseline','after'].includes(stage))throw Error('Expected baseline or after');
const dir=__dirname;
(async()=>{
 const browser=await chromium.launch(); const results=[];
 for(const route of ['/','/explore/'])for(const theme of ['light','dark'])for(const width of [360,1440]){
  const page=await browser.newPage({viewport:{width,height:1000},colorScheme:theme,reducedMotion:'no-preference'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765'+route);await page.evaluate(()=>document.fonts.ready);
  await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
  const scan=()=>page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'rule',values:['color-contrast']}});return {violations:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))};});
  const initial=await scan();
  // Reveal every section by visiting it, then explicitly wait for opacity one.
  for(const el of await page.locator('.reveal').all()){await el.scrollIntoViewIfNeeded();await page.waitForTimeout(30);}
  await page.waitForTimeout(1800);
  await page.waitForFunction(()=>[...document.querySelectorAll('.reveal')].every(e=>Number(getComputedStyle(e).opacity)===1));
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));await page.waitForTimeout(200);
  const settled=await scan();
  const geometry=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,reveals:[...document.querySelectorAll('.reveal')].map(e=>({opacity:getComputedStyle(e).opacity}))}));
  const name=`${stage}-${route==='/'?'home':'explore'}-${theme}-${width}.png`;
  await page.screenshot({path:path.join(dir,'screenshots',name),fullPage:true});
  results.push({route,theme,width,initial,settled,geometry,errors,screenshot:name,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,'screenshots',name))).digest('hex')});
  console.log(name,'contrast',settled.violations.length,'overflow',geometry.scrollWidth-width);await page.close();
 }
 fs.writeFileSync(path.join(dir,stage+'.json'),JSON.stringify({capturedAt:new Date().toISOString(),browser:browser.version(),axe:require('axe-core/package.json').version,results},null,2)+'\n');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
