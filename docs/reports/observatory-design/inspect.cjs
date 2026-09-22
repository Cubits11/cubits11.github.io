/* One-session browser observations, not a new release gate. See REPORT.md. */
const {chromium}=require('playwright');const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch();const results={browser:browser.version(),layout:[],checks:[]};
 const page=await browser.newPage({viewport:{width:360,height:900},reducedMotion:'reduce'});
 const routes=[...fs.readFileSync('sitemap.xml','utf8').matchAll(/<loc>https:\/\/cubits11.github.io([^<]*)<\/loc>/g)].map(m=>m[1]);
 for(const width of [360,390,768,1280]){
  await page.setViewportSize({width,height:900});
  for(const route of routes){
   await page.goto('http://127.0.0.1:8765'+route);await page.evaluate(()=>document.fonts.ready);
   const geometry=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
   results.layout.push({route,...geometry});
  }
  console.log('layout completed',width);
 }
 await page.setViewportSize({width:360,height:900});await page.goto('http://127.0.0.1:8765/explore/');
 await page.locator('.nav-toggle').focus();await page.keyboard.press('Enter');assert.equal(await page.locator('.nav-toggle').getAttribute('aria-expanded'),'true');
 await page.keyboard.press('Escape');assert.equal(await page.locator('.nav-toggle').getAttribute('aria-expanded'),'false');assert.equal(await page.locator('.nav-toggle').evaluate(e=>document.activeElement===e),true);results.checks.push('Menu opens by keyboard; Escape closes and restores focus');
 await page.locator('#rate-a').focus();await page.keyboard.press('ArrowRight');assert.equal(await page.locator('#a-value').textContent(),'11%');results.checks.push('Range responds to keyboard and updates output');
 await page.locator('input[value=independence]').check();assert.equal(await page.locator('#world-range').textContent(),'1.1%');assert.equal(await page.locator('#world-position').isDisabled(),true);results.checks.push('Independence produces point and disables unavailable movement');
 await page.locator('input[value=interval]').check();await page.locator('#joint-low').fill('80');await page.locator('#joint-high').fill('90');assert.equal(await page.locator('#world-range').textContent(),'Empty set');assert.equal(await page.locator('#world-witness').isVisible(),false);results.checks.push('Contradictory interval shows Empty set and hides witness');
 await page.locator('#bench-reset').click();assert.equal(await page.locator('#world-range').textContent(),'0%–10%');results.checks.push('Reset restores original construction');
 await page.locator('#themeToggle').click();assert.equal(await page.locator('#themeToggle').getAttribute('aria-pressed'),'true');await page.reload();assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');results.checks.push('Theme persists across reload');
 await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
 results.exploreAccessibility=await page.evaluate(async()=>{const r=await axe.run();return {violations:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),incomplete:r.incomplete.map(v=>v.id)};});
 const nojs=await browser.newPage({javaScriptEnabled:false,viewport:{width:360,height:900}});
 for(const route of ['/','/explore/']){await nojs.goto('http://127.0.0.1:8765'+route);assert.equal(await nojs.locator('h1').isVisible(),true);}
 assert.equal(await nojs.locator('#world-range').textContent(),'0%–10%');results.checks.push('No-JavaScript homepage and static instrument remain readable');
 results.overflow=results.layout.filter(r=>r.scrollWidth>r.width);
 fs.writeFileSync(__dirname+'/interaction-layout.json',JSON.stringify(results,null,2)+'\n');console.log('overflow',results.overflow.length,'checks',results.checks.length);await browser.close();
 if(results.overflow.length||results.exploreAccessibility.violations.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
