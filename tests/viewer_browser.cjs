'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();await page.goto(process.env.AULA_VIEW_URL);
  await page.locator('.layout').waitFor();
  assert.match(await page.locator('#readonly-banner').innerText(),/Copia del .*solo lectura/);
  assert.equal(await page.locator('form[data-endpoint="confirm-rate"]').count(),0);
  assert.equal(await page.getByRole('button',{name:'Registrar pago',exact:true}).count(),0);
  const before=await page.evaluate(async()=>await(await fetch('/api/state?history=1')).json());
  assert.equal(before.payments.length,1);assert.equal(before.user.role,'reader');
  for(const id of ['billing','payments','reports','students']){
   await page.locator(`.nav-button[data-id="${id}"]`).click();
   await page.locator(`.nav-button.active[data-id="${id}"]`).waitFor();
   assert.equal(await page.locator('#readonly-banner').isVisible(),true);
  }
  const blocked=await page.evaluate(async()=>{
   const routes=['payments','expenses','confirm-rate','generate','restore','settings','backup-now','import-roster','transition-year','crypto-confirm'];
   return await Promise.all(routes.map(async route=>{const r=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});return r.status;}));
  });assert.ok(blocked.every(status=>status===403));
  const after=await page.evaluate(async()=>await(await fetch('/api/state?history=1')).json());
  assert.deepEqual(after.charges,before.charges);assert.deepEqual(after.summary,before.summary);
  console.log('PASS: copy viewer banner, no rate confirmation, history navigation, server write rejection and unchanged ledger.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
