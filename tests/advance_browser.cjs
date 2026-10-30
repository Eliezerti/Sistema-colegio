'use strict';
const assert=require('node:assert/strict');
module.exports=async function(page){
  const sample=await page.evaluate(async()=>{
    const s=await api('state?history=1'),year=Number(s.today.slice(0,4))-(Number(s.today.slice(5,7))<Number(s.settings.start_month)?1:0);
    const original={...s.settings};
    await api('settings',{...s.settings,school_year:year,advance_months_limit:3});
    const g=await api('grades',{name:'Grado FICTICIO anticipos',capacity:30});
    const r=await api('guardians',{name:'Representante FICTICIO anticipos',document:'V-FICTICIO-ANTICIPOS'});
    const pupil=await api('students',{name:'Alumno FICTICIO anticipo',document:'',birth_date:'',guardian_id:r.id,grade_id:g.id,school_year:year,monthly_fee:'40',discount:0,status:'active',billing_start:s.today.slice(0,7),enrollment_start:`${year}-${String(s.settings.start_month).padStart(2,'0')}-01`,enrollment_end:`${year+1}-${String(Number(s.settings.start_month)-1||12).padStart(2,'0')}-28`});
    const now=await api('state?history=1'),p=now.students.find(p=>p.id===pupil.id);
    if(p.balance)await api('payments',{student_id:pupil.id,amount:(p.balance/100).toFixed(2),currency:'USD',paid_on:s.today,method:'Efectivo',request_key:requestKey()});
    await refresh();return {id:pupil.id,original,guardian:r.id};
  });
  try{
    await page.evaluate(id=>openPayment(id),sample.id);
    let form=page.locator('form[data-endpoint="payments"]');await form.locator('[data-month-choice]').first().waitFor();
    const future=form.locator('[data-future="true"]');
    assert.ok(await future.count()>0,'Alumno al día puede elegir un mes futuro');
    assert.match(await form.locator('#payment-charges').innerText(),/Por adelantado/);
    assert.match(await form.locator('#payment-charges').innerText(),/Se cobrará con la tarifa actual/);
    assert.equal(await form.locator('[name="amount"]').inputValue(),'40.00');
    await form.locator('[name="currency"]').selectOption('VES');
    assert.equal(await form.locator('[name="amount"]').inputValue(),'4000.00');
    assert.match(await form.locator('#conversion').innerText(),/40,00/);
    await form.locator('[name="amount"]').fill('2000.00');
    await form.locator('[name="currency"]').selectOption('USD');
    assert.equal(await form.locator('[name="amount"]').inputValue(),'20.00','Conserva un abono real al cambiar moneda');
    await form.locator('[name="amount"]').fill('40.00');
    const period=await future.first().getAttribute('data-period');
    await form.getByRole('button',{name:'Registrar y emitir recibo'}).click();
    await page.locator('dialog[open] .payment-receipt').waitFor();
    assert.match(await page.locator('dialog[open] .payment-receipt').innerText(),/pagada por adelantado/);
    const checked=await page.evaluate(async({id,period})=>{
      const s=await api('state?history=1'),p=s.students.find(s=>s.id===id),c=s.charges.filter(c=>c.student_id===id&&c.period===period);
      return {balance:p.balance,overdue:p.overdue,count:c.length,label:c[0].advance_label,advance:s.advance_income_usd};
    },{id:sample.id,period});
    assert.deepEqual([checked.balance,checked.overdue,checked.count],[0,0,1]);assert.equal(checked.label,'Pagado por adelantado');assert.ok(checked.advance>=4000);
    await page.locator('dialog[open] [data-action="close"]').first().click();
    // Same shared choices in Cashea; preview must not create the next month's charge.
    await page.evaluate(id=>openCasheaOrder(id),sample.id);
    form=page.locator('form[data-endpoint="cashea-order"]');await form.locator('[data-future="true"]').first().waitFor();
    assert.equal(await form.locator('[name="total"]').inputValue(),'40.00');
    await form.locator('[name="initial_percent"]').fill('40');
    await form.getByRole('button',{name:'Calcular inicial'}).click();
    assert.equal(await form.locator('[name="initial_received"]').inputValue(),'16.00');
    const nextPeriod=await form.locator('[data-future="true"]').first().getAttribute('data-period');
    await form.getByRole('button',{name:'Revisar venta'}).click();await form.getByRole('button',{name:'Confirmar registro'}).waitFor();
    assert.equal(await page.evaluate(async({id,period})=>(await api('state?history=1')).charges.filter(c=>c.student_id===id&&c.period===period).length,{id:sample.id,period:nextPeriod}),0);
    await form.getByRole('button',{name:'Confirmar registro'}).click();await page.locator('dialog[open] .cashea-invoice-number').waitFor();
    assert.match(await page.locator('dialog[open] .cashea-invoice-number').innerText(),/^R-/);
    assert.equal(await page.evaluate(async id=>(await api('state?history=1')).students.find(s=>s.id===id).balance,sample.id),0);
    await page.locator('dialog[open] [data-action="close"]').first().click();
    // Zero scholarship: a visible action assesses without a payment or a number.
    await page.evaluate(async id=>{const s=(await api('state?history=1')).students.find(s=>s.id===id);await api('students',{...s,monthly_fee:(s.monthly_fee/100).toFixed(2),discount:100});await refresh();},sample.id);
    const before=await page.evaluate(()=>api('cashea'));
    await page.evaluate(id=>openPayment(id),sample.id);
    form=page.locator('form[data-endpoint="payments"]');await form.getByRole('button',{name:'Registrar evaluación sin cobro'}).waitFor();
    await form.getByRole('button',{name:'Registrar evaluación sin cobro'}).click();await page.locator('dialog[open]').waitFor({state:'hidden'});
    const after=await page.evaluate(()=>api('cashea'));assert.equal(after.next_receipt_number,before.next_receipt_number);
    assert.equal(await page.evaluate(async()=>(await api('maintenance-review')).ok),true);
    console.log('PASS ANTICIPOS: alumno al día, lista compartida, tarifa, cobro futuro y recibo, saldo/mora cero, Cashea 40/16/24 con revisión sin crear cargo, beca completa sin consumir R-.');
  }finally{
    await page.evaluate(async original=>{await api('settings',original);await refresh();},sample.original);
  }
};
