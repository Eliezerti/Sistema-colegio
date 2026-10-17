const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
module.exports=async(page,expectedMonthError)=>{
  const get=route=>page.evaluate(async route=>{const r=await fetch('/api/'+route);if(!r.ok)throw new Error(await r.text());return r.json();},route);
  const before=await get('state?history=1'),pid=before.payments.find(p=>!p.voided).id;
  const click=action=>page.locator(`[data-action="${action}"]`).first().click();
  const save=async()=>{await page.locator('#modal button[type="submit"]').click();await page.waitForFunction(()=>!document.querySelector('#modal').open);};
  await page.locator(`[data-action="month-annotation"][data-id="P${pid}"]`).click();await page.locator('#modal [name="foreign_currency"]').check();await save();
  await click('month-close');const confirmation=page.locator('#modal [name="confirmed_pending"]');if(await confirmation.count())await confirmation.check();await save();
  const closed=await get('accounting-report');assert.equal(closed.closed,true);assert.equal(closed.income.find(r=>r.source==='P'+pid).foreign_currency,true);
  expectedMonthError.active=true;
  const deniedConsole=page.waitForEvent('console',{predicate:msg=>msg.type()==='error'&&msg.location().url.endsWith('/api/payments')&&msg.text().includes('400 (Bad Request)')});
  const blocked=await page.evaluate(async({today,student,account})=>{const session=await(await fetch('/api/session')).json();const r=await fetch('/api/payments',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.user.csrf},body:JSON.stringify({student_id:student,paid_on:today,amount:'1',currency:'USD',method:'Transferencia',account_id:account,request_key:'blocked-month-browser'})});return {status:r.status,body:await r.json()};},{today:before.today,student:before.students.find(s=>s.status==='active'&&!s.archived).id,account:before.school_accounts.find(a=>a.kind==='bank'&&a.currency==='USD').id});
  await deniedConsole;assert.equal(expectedMonthError.count,1,'Only the intentional closed-month payment may return 400');expectedMonthError.active=false;
  assert.equal(blocked.status,400);assert.match(blocked.body.error,/mes está cerrado/);
  for(const [action,signature] of [['accounting-csv',Buffer.from([239,187,191])],['accounting-pdf',Buffer.from('%PDF')]]){
    const download=page.waitForEvent('download');await click(action);const file=await download;const bytes=await fs.readFile(await file.path());assert.ok(bytes.subarray(0,signature.length).equals(signature));
  }
  await click('month-reopen');await page.locator('#modal [name="reason"]').fill('Revisión ficticia del cierre de navegador');await save();assert.equal((await get('accounting-report')).closed,false);
  const after=await get('state?history=1');assert.deepEqual(after.summary,before.summary);assert.equal(after.audit_status.ok,true);
  console.log('PASS: opciones informativas, cierre mensual con pendientes revisados, cobro rechazado por servidor, CSV con BOM y PDF descargados, reapertura con motivo y totales intactos.');
};
