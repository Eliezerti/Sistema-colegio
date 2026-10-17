// Confidential fictional statement, real mapping/preview/commit and links through UI.
const assert=require('node:assert/strict');
module.exports=async page=>{
  const get=route=>page.evaluate(async route=>{const r=await fetch('/api/'+route);if(!r.ok)throw new Error(await r.text());return r.json();},route);
  const post=(route,data)=>page.evaluate(async({route,data})=>{const s=await(await fetch('/api/session')).json();const r=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':s.user.csrf},body:JSON.stringify(data)});if(!r.ok)throw new Error(await r.text());return r.json();},{route,data});
  const state=await get('state?history=1'),pupil=state.students.find(s=>s.status==='active'&&!s.archived),bank=state.school_accounts.find(a=>a.kind==='bank'&&a.currency==='USD');
  await post('charges',{student_id:pupil.id,concept:'Ficticio conciliación',period:state.today,amount:'1',due_date:state.today});
  const paid=await post('payments',{student_id:pupil.id,paid_on:state.today,amount:'1',currency:'USD',method:'Transferencia',reference:'00000123123',request_key:'browser-bank-ficticio',account_id:bank.id});
  const before=await get('state?history=1');
  const click=action=>page.locator(`[data-action="${action}"]`).first().click();
  await click('bank-profile');await page.locator('dialog [name="name"]').fill('Provincial ficticio NO VERIFICADO');
  await page.locator('dialog button[type="submit"]').click();await page.waitForFunction(()=>!document.querySelector('dialog').open);
  await click('bank-import');await page.locator('dialog [name="account_id"]').selectOption(String(bank.id));
  await page.locator('dialog [name="profile_id"]').selectOption({label:'Provincial ficticio NO VERIFICADO'});
  const buffer=Buffer.from(`Fecha;Importe;Referencia;Descripción\n${state.today};1.00;123123;Extracto ficticio confidencial ñ\n`,'utf8');
  await page.locator('dialog [name="statement_file"]').setInputFiles({name:'extracto-ficticio.csv',mimeType:'text/csv',buffer});
  await page.locator('dialog button[type="submit"]').click();await page.locator('dialog [data-action="bank-commit"]').waitFor();
  assert.match(await page.locator('#modal').innerText(),/Extracto ficticio confidencial ñ/);
  await click('bank-commit');await page.waitForFunction(()=>!document.querySelector('dialog').open);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/bank-auto')&&r.request().method()==='POST');await click('bank-auto');assert.equal((await response).status(),200);
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('Cruces únicos'));
  const book=await get('bank-book'),after=await get('state?history=1');assert.equal(book.links.filter(l=>!l.voided&&l.payment_id===paid.id).length,1);
  assert.deepEqual(after.summary,before.summary);assert.equal(after.audit_status.ok,true);
  assert.equal(book.profiles[0].status,'NO VERIFICADO');
  console.log('PASS: perfil editable NO VERIFICADO, CSV ficticio con ñ, vista previa y confirmación por interfaz, cruce único de ceros a la izquierda y totales sin cambios.');
};
