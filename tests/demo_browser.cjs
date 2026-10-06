// Run through run_browser.py --demo: disposable data only.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1440,height:1050}}),page=await context.newPage();
  const url=process.env.AULA_TEST_URL;
  const nav=async id=>page.locator(`.nav-button[data-id="${id}"]`).click();
  const click=async action=>page.locator(`[data-action="${action}"]`).first().click();
  const fill=async(name,value)=>page.locator(`dialog[open] [name="${name}"]`).fill(value);
  const submit=async()=>{await page.locator('dialog[open] button[type="submit"]').click();await page.waitForFunction(()=>!document.querySelector('dialog').open);};
  try{
    await page.goto(url);await page.getByRole('button',{name:/Entrar como administrador de prueba/}).click();
    await page.getByLabel('Bolívares por 1 USD').fill('100');await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();
    await page.locator('.layout').waitFor();assert.match(await page.locator('.demo-banner').innerText(),/Modo prueba/);
    const initial=await page.evaluate(async()=>await(await fetch('/api/state')).json());
    assert.equal(initial.user.role,'admin');assert.deepEqual(initial.students,[]);assert.deepEqual(initial.expenses,[]);
    await nav('settings');assert.equal(await page.locator('[name="backup_directory"]').count(),0);assert.equal(await page.locator('[data-action="reset-review"]').count(),0);
    await nav('employees');await click('positions');await fill('name','Docente');await submit();
    await click('employee');await fill('name','Ana Docente · Prueba');await fill('document','V-12345678');await fill('salary','120');
    await page.locator('dialog[open] [name="position_id"]').selectOption({label:'Docente'});await submit();
    await click('payroll');await fill('period_start',initial.today.slice(0,7)+'-01');await fill('period_end',initial.today);
    await fill('entry_time','07:00');await fill('exit_time','13:00');await page.locator('dialog[open] button[type="submit"]').click();
    await page.locator('dialog[open] .salary-document').waitFor();const text=await page.locator('dialog[open] .salary-document').innerText();
    assert.match(text,/PRUEBA SIN VALIDEZ/);assert.match(text,/12\.000,00/);assert.match(text,/Recibí conforme/);
    const download=page.waitForEvent('download');await page.getByRole('link',{name:'Descargar PDF'}).click();await(await download).saveAs('/tmp/aula-demo-salary.pdf');
    await page.screenshot({path:'/tmp/aula-demo-salary.png',fullPage:true});await click('close');
    await page.reload();await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();await page.locator('.layout').waitFor();
    assert.equal(await page.evaluate(async()=>(await(await fetch('/api/state')).json()).expenses.length),1,'Reload must preserve the running trial');
    await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
    await page.screenshot({path:'/tmp/aula-demo-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});
    const second=await context.newPage();await second.goto(url);await second.getByRole('button',{name:'Confirmar tasa y entrar'}).waitFor();
    await second.close();await page.waitForTimeout(6000);assert.equal(await page.evaluate(async()=>(await(await fetch('/api/state')).json()).expenses.length),1);
    await page.close(); // The runner checks shutdown and physical deletion after the last tab closes.
    console.log('PASS: trial administrator, empty isolated database, salary PDF marked as trial, reload, multiple tabs, mobile layout and automatic cleanup.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
