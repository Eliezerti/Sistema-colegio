// Run with tests/run_browser.py --directory, always against its temporary database.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),headless:true,args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1100,height:960}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const nav=async id=>{await page.locator(`.nav-button[data-id="${id}"]`).click();};
  const click=async action=>{await page.locator(`[data-action="${action}"]`).first().click();};
  const fill=async(name,value)=>{await page.locator(`dialog[open] [name="${name}"]`).fill(value);};
  const submit=async()=>{await page.locator('dialog[open] button[type="submit"]').click();};
  const close=async()=>{await page.locator('dialog[open] [data-action="close"]').first().click();};
  const state=async()=>await page.evaluate(async()=>await(await fetch('/api/state')).json());
  try{
    await page.goto(process.env.AULA_TEST_URL);
    await page.getByLabel('Nombre del colegio',{exact:true}).fill('Colegio de prueba');
    await page.getByLabel('Nombre del administrador').fill('Administración');
    await page.getByLabel('Usuario',{exact:true}).fill('admin');
    await page.getByLabel(/^Contraseña/).fill('Prueba-segura-2026');
    await page.getByRole('button',{name:'Crear mi cuenta'}).click();
    await page.locator('form[data-endpoint="confirm-rate"] [name="rate"]').fill('100');
    await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();
    await page.locator('.layout').waitFor();
    await nav('grades');await click('grade');await fill('name','Maternal A');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);
    await click('grade');await fill('name','Grado sobrante');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);
    const extra=page.locator('tr').filter({hasText:'Grado sobrante'});await extra.locator('[data-action="delete-grade"]').click();await fill('reason','Grado cargado por error');await fill('confirmation','ELIMINAR');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);assert.equal((await state()).grades.length,1);
    await nav('guardians');await click('guardian');await fill('name','Ana Representante');await fill('document','V-123');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);
    await nav('students');await click('student');await fill('name','Alumno de prueba');await fill('monthly_fee','130');await page.locator('dialog[open] [name="guardian_id"]').selectOption({label:'V-123 · Ana Representante'});
    assert.equal(await page.locator('dialog[open] [name="birth_date"]').getAttribute('required'),null);await submit();await page.locator('dialog[open] .receipt-number').waitFor();
    const text=await page.locator('dialog[open] .receipt').innerText();assert.match(text,/Fecha de nacimiento\s+Pendiente/);assert.doesNotMatch(text,/La tarifa se aplica/);assert.match(text,/Mensualidades desde\s+[A-Z]{3}\. \d{4}/);
    await page.screenshot({path:'/tmp/aula-constancia-limpia.png',fullPage:true});await close();
    const row=page.locator('tr').filter({hasText:'Alumno de prueba'});assert.ok(await row.locator('.directory-actions [data-action="student"]').isVisible());
    await row.locator('.directory-actions [data-action="student"]').click();const old=(await state()).students[0];const first=old.enrollment_start.slice(0,7);
    await fill('billing_start',first);if(first<old.billing_start){await page.locator('dialog[open] [name="billing_change_confirmed"]').check();}await submit();await page.locator('dialog[open] .receipt-number').waitFor();await close();
    await nav('arrears');await page.locator('[data-action="correct-billing"]').first().click();assert.match(await page.locator('#billing-correction-preview').innerText(),/SEP\. \d{4}/);await fill('reason','Inscrito en octubre; septiembre cargado por error');await page.locator('dialog[open] [name="confirmed"]').check();await page.screenshot({path:'/tmp/aula-corregir-mensualidades.png',fullPage:true});await submit();await page.locator('dialog[open] h3').filter({hasText:'Estado de cuenta'}).waitFor();await close();
    const corrected=await state();assert.ok(corrected.charges.every(c=>c.period!==first));assert.equal(corrected.students[0].billing_start,`${old.school_year}-10`);
    await nav('grades');await click('delete-grade');await fill('reason','Prueba de protección');await fill('confirmation','ELIMINAR');await submit();await page.locator('dialog[open] .error').getByText(/alumnos vinculados/).waitFor();await close();
    await nav('guardians');await click('archive-guardian');await fill('reason','Prueba de protección');await fill('confirmation','ARCHIVAR');await submit();await page.locator('dialog[open] .error').getByText(/alumnos vinculados/).waitFor();await close();
    await nav('students');await click('archive-student');await fill('reason','Fin de la prueba');await fill('confirmation','ARCHIVAR');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);assert.equal(await page.locator('.directory-actions [data-action="student"]').count(),0);
    await page.locator('#show-archived').check();await click('restore-student');await fill('reason','Recuperar ficha');await fill('confirmation','RECUPERAR');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);assert.equal((await state()).students[0].status,'inactive');
    await nav('guardians');await click('guardian');await fill('name','Representante sobrante');await fill('document','V-456');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);
    const guardian=page.locator('tr').filter({hasText:'Representante sobrante'});await guardian.locator('[data-action="archive-guardian"]').click();await fill('reason','Duplicado de prueba');await fill('confirmation','ARCHIVAR');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);assert.equal(await guardian.count(),0);
    await page.locator('#show-archived').check();await guardian.locator('[data-action="restore-guardian"]').click();await fill('reason','Recuperar representante');await fill('confirmation','RECUPERAR');await submit();await page.waitForFunction(()=>!document.querySelector('dialog').open);assert.equal((await state()).guardians.find(g=>g.document==='V-456').archived,0);
    assert.equal(errors.length,0,errors.join('\n'));console.log('PASS: optional birth, clean enrollment, visible editing, guarded earlier months, correction with preview, unused-grade deletion, linked records protected, reversible pupil and guardian archive.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
