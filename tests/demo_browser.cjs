const {scratch}=require('./browser_paths.cjs');
// Run through run_browser.py --demo: disposable data only.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),headless:true,args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1440,height:1050}}),page=await context.newPage();
  const url=process.env.AULA_TEST_URL;
  const nav=async id=>{await page.locator(`.nav-button[data-id="${id}"]`).click();await page.locator(`.nav-button.active[data-id="${id}"]`).waitFor();};
  const click=async action=>page.locator(`[data-action="${action}"]`).first().click();
  const fill=async(name,value)=>page.locator(`dialog[open] [name="${name}"]`).fill(value);
  const submit=async()=>{await page.locator('dialog[open] button[type="submit"]').click();await page.waitForFunction(()=>!document.querySelector('dialog').open);};
  try{
    await page.goto(url);await page.getByRole('button',{name:/Entrar como administrador de prueba/}).click();
    await page.getByLabel('Bolívares por 1 USD').fill('100');await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();
    await page.locator('.layout').waitFor();assert.match(await page.locator('.demo-banner').innerText(),/Modo prueba/);
    assert.equal(await page.locator('.backup-persistent').count(),0,'Trial must not show real backup warnings');
    const initial=await page.evaluate(async()=>await(await fetch('/api/state?history=1')).json());
    assert.equal(initial.user.role,'admin');assert.deepEqual(initial.students,[]);assert.deepEqual(initial.expenses,[]);
    await nav('reports');await click('daily-report');await page.locator('dialog[open] .daily-report').waitFor();assert.match(await page.locator('dialog[open] .daily-report').innerText(),/PRUEBA SIN VALIDEZ/);
    const reportPdf=await page.evaluate(async()=>await(await fetch('/api/daily-report.pdf')).text());assert.ok(reportPdf.includes('PRUEBA SIN VALIDEZ'));await click('close');
    await nav('settings');assert.equal(await page.locator('[name="backup_directory"]').count(),0);assert.equal(await page.locator('[data-action="reset-review"]').count(),0);
    await nav('guardians');await click('guardian');await fill('name','Representante temporal');await fill('document','V-temporal');await submit();
    await nav('archive');await page.locator('[data-action="archive-kind"][data-id="guardian"]').click();
    await click('archive-review');await click('archive-guardian');await fill('reason','Ficha temporal sin alumnos');await fill('confirmation','ARCHIVAR');await submit();
    await click('archive-review');await click('delete-unused-review');
    assert.equal(await page.locator('dialog[open] [name="password"]').count(),0);
    await fill('reason','Borrar prueba ficticia');await fill('confirmation','BORRAR FICHA');await submit();
    assert.deepEqual(await page.evaluate(async()=>(await(await fetch('/api/state?history=1')).json()).guardians),[]);
    assert.equal(await page.locator('.backup-persistent').count(),0);
    await nav('expenses');await click('expense');await fill('concept','Gasto temporal');await fill('amount','10');await submit();
    assert.equal(await page.locator('[data-action="salary-document"]').count(),0);
    await page.evaluate(async()=>{
      const s=await api('state?history=1'),today=s.today,year=Number(today.slice(0,4))-(Number(today.slice(5,7))<9?1:0);
      const g=await api('grades',{name:'Grado FICTICIO Cashea',capacity:10});
      const r=await api('guardians',{name:'Representante FICTICIO Cashea',document:'V-FICTICIO-CASHEA'});
      const pupil=await api('students',{name:'Alumno FICTICIO Cashea',document:'',birth_date:'',guardian_id:r.id,grade_id:g.id,school_year:year,monthly_fee:'10',discount:0,status:'active',billing_start:today.slice(0,7),enrollment_start:`${year}-09-01`,enrollment_end:`${year+1}-08-31`});
      const data={student_id:pupil.id,ordered_on:today,total:'10',initial_received:'0',initial_percent:'0',invoice_number:'F-FICTICIA-DEMO-001',request_key:'cashea-demo-ficticia-001'};
      data.preview_hash=(await api('cashea-preview',data)).preview_hash;await api('cashea-order',data);
    });
    const casheaPdf=await page.evaluate(async()=>await(await fetch('/api/cashea-order/1.pdf')).text());
    assert.ok(casheaPdf.includes('PRUEBA SIN VALIDEZ'));
    const casheaCsv=await page.evaluate(async()=>await(await fetch('/api/cashea-report.csv?type=sales')).text());
    assert.ok(casheaCsv.includes('PRUEBA SIN VALIDEZ'));
    await page.reload();await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();await page.locator('.layout').waitFor();
    assert.equal(await page.evaluate(async()=>(await(await fetch('/api/state?history=1')).json()).expenses.length),1,'Reload must preserve the running trial');
    await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
    await page.screenshot({path:scratch('aula-demo-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1050});
    const second=await context.newPage();await second.goto(url);await second.getByRole('button',{name:'Confirmar tasa y entrar'}).waitFor();
    await second.close();await page.waitForTimeout(6000);assert.equal(await page.evaluate(async()=>(await(await fetch('/api/state?history=1')).json()).expenses.length),1);
    await page.close(); // The runner checks shutdown and physical deletion after the last tab closes.
    console.log('PASS: trial administrator, empty isolated database, simplified expense, reload, multiple tabs, mobile layout and automatic cleanup.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
