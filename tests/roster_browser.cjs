const {scratch}=require('./browser_paths.cjs');
// Run through run_browser.py --roster; both schools are isolated fixtures.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||(fs.existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),headless:true,args:['--no-sandbox']});
  const context=await browser.newContext({viewport:{width:1440,height:1050}}),source=await context.newPage();
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'aula-roster-trial-'));let child,trial;
  const click=(p,a)=>p.locator(`[data-action="${a}"]`).first().click();
  const fill=(p,n,v)=>p.locator(`dialog[open] [name="${n}"]`).fill(v);
  const nav=async(p,n)=>{await p.locator(`.nav-button[data-id="${n}"]`).click();await p.locator(`.nav-button.active[data-id="${n}"]`).waitFor();};
  const state=p=>p.evaluate(async()=>await(await fetch('/api/state?history=1')).json());
  try{
    await source.goto(process.env.AULA_TEST_URL);
    await source.getByLabel('Nombre del colegio',{exact:true}).fill('Colegio ficticio');
    await source.getByLabel('Nombre del administrador').fill('Administración de prueba');
    await source.getByLabel('Usuario',{exact:true}).fill('admin');await source.getByLabel(/^Contraseña/).fill('Prueba-segura-2026');
    await source.getByRole('button',{name:'Crear mi cuenta'}).click();await source.getByLabel('Bolívares por 1 USD').fill('100');await source.getByRole('button',{name:'Confirmar tasa y entrar'}).click();await source.locator('.layout').waitFor();
    await nav(source,'grades');await click(source,'grade');await fill(source,'name','Primero A');await source.locator('dialog[open] button[type=submit]').click();await source.waitForFunction(()=>!document.querySelector('dialog').open);
    await nav(source,'guardians');await click(source,'guardian');await fill(source,'name','Ana Representante');await fill(source,'document','V-12345678');await fill(source,'phone','04121234567');await source.locator('dialog[open] button[type=submit]').click();await source.waitForFunction(()=>!document.querySelector('dialog').open);
    await nav(source,'students');
    for(const [name,status] of [['Alumno activo','active'],['Alumno inactivo','inactive']]){
      await click(source,'student');await fill(source,'name',name);await fill(source,'monthly_fee','100');await fill(source,'discount','10');await source.locator('dialog[open] [name=guardian_id]').selectOption({label:'V-12345678 · Ana Representante'});await source.locator('dialog[open] [name=status]').selectOption(status);await source.locator('dialog[open] button[type=submit]').click();await source.locator('dialog[open] .receipt-number').waitFor();await click(source,'close');
    }
    await nav(source,'payments');await click(source,'payment');await fill(source,'amount','10');await source.locator('dialog[open] button[type=submit]').click();await source.locator('dialog[open] .receipt-number').waitFor();await click(source,'close');
    const original=await state(source);assert.equal(original.students.length,2);assert.equal(original.payments.length,1);
    await nav(source,'students');await click(source,'export-students');
    for(const [extension,label] of [['xlsx','Exportar Excel (.xlsx)'],['csv','Exportar CSV']]){
      const pending=source.waitForEvent('download');await source.getByRole('link',{name:label,exact:true}).click();await(await pending).saveAs(scratch('aula-roster-export.')+extension);
    }
    await click(source,'close');
    let output='';child=spawn(process.env.AULA_TEST_PYTHON||'python',['-u','-m','colegio.server','--demo','--port','0'],{env:{...process.env,TMPDIR:temp,TEMP:temp,TMP:temp},stdio:['ignore','pipe','pipe']});
    const trialUrl=await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('Trial server did not start')),15000);child.stdout.on('data',chunk=>{output+=chunk;const found=output.match(/MODO PRUEBA abierto en (http:\/\/127\.0\.0\.1:\d+)/);if(found){clearTimeout(timeout);resolve(found[1]);}});child.once('exit',()=>{clearTimeout(timeout);reject(new Error('Trial server exited before startup'));});});
    trial=await context.newPage();await trial.goto(trialUrl);await trial.getByRole('button',{name:/Entrar como administrador de prueba/}).click();await trial.getByLabel('Bolívares por 1 USD').fill('100');await trial.getByRole('button',{name:'Confirmar tasa y entrar'}).click();await trial.locator('.layout').waitFor();
    await nav(trial,'students');await click(trial,'import-roster');
    const old='Alumno;Codigo;Documento;Grado;Ano escolar;Representante;Telefono;Estado;Saldo USD\nAlumno;AL-000001;AL-000001;Primero;2026;Ana;04121234567;active;100.00\n';
    await trial.locator('#roster-file').setInputFiles({name:'old.csv',mimeType:'text/csv',buffer:Buffer.from(old)});await click(trial,'preview-import');await trial.getByText(/listado antiguo de 9 columnas/).waitFor();assert.equal((await state(trial)).students.length,0);
    await trial.locator('#roster-file').setInputFiles(scratch('aula-roster-export.xlsx'));await click(trial,'preview-import');await trial.getByText('Exportación completa reconocida',{exact:true}).waitFor();
    assert.match(await trial.locator('#roster-preview').innerText(),/2 alumnos válidos · 1 representante nuevo · 1 grado nuevo/);assert.match(await trial.locator('#roster-preview').innerText(),/Inactivo/);assert.equal((await state(trial)).students.length,0);assert.equal((await state(trial)).grades.length,0);
    await trial.screenshot({path:scratch('aula-import-preview.png'),fullPage:true});
    // Selecting another file invalidates a previously checked preview.
    await trial.locator('#import-reviewed').check();await trial.locator('#roster-file').setInputFiles(scratch('aula-roster-export.csv'));assert.equal(await trial.locator('#import-reviewed').count(),0);
    await click(trial,'preview-import');await trial.getByText('Exportación completa reconocida',{exact:true}).waitFor();await trial.locator('#import-reviewed').check();await click(trial,'confirm-import');await trial.locator('#page-content').getByText('Alumno activo',{exact:true}).waitFor();
    const imported=await state(trial);assert.equal(imported.students.length,2);assert.equal(imported.guardians.length,1);assert.equal(imported.grades.length,1);assert.equal(imported.guardians[0].phone,'04121234567');assert.equal(imported.payments.length,0);
    for(const student of original.students){const loaded=imported.students.find(s=>s.student_code===student.student_code);for(const key of ['name','monthly_fee','discount','status','billing_start','enrollment_start','enrollment_end'])assert.equal(loaded[key],student[key],key);}
    assert.equal(imported.students.find(s=>s.status==='active').balance,9000);assert.equal(original.students.find(s=>s.status==='active').balance,8000);assert.equal(imported.students.find(s=>s.status==='inactive').balance,0);
    await nav(trial,'guardians');await click(trial,'directory-report');await trial.locator('dialog[open] .directory-report').waitFor();assert.match(await trial.locator('dialog[open] .directory-report').innerText(),/Alumno activo · Primero A \(Activo\)/);assert.match(await trial.locator('dialog[open] .directory-report').innerText(),/Alumno inactivo · Primero A \(Inactivo\)/);
    const pdf=trial.waitForEvent('download');await trial.getByRole('link',{name:'Descargar PDF'}).click();await(await pdf).saveAs(scratch('aula-guardians-states.pdf'));await trial.screenshot({path:scratch('aula-guardians-states.png'),fullPage:true});
    assert.equal((await state(source)).payments.length,1);assert.equal((await state(source)).students.find(s=>s.status==='active').balance,8000);
    await trial.close();await new Promise((resolve,reject)=>{if(child.exitCode!==null)return resolve();const timer=setTimeout(()=>reject(new Error('Trial did not shut down')),15000);child.once('exit',()=>{clearTimeout(timer);resolve();});});
    console.log('PASS: actual Excel and CSV downloads, import into empty trial, automatic grades, preserved codes/phones/fees/statuses, preview invalidation, old listing explanation, no copied payments or altered source ledger, guardian PDF states and trial cleanup.');
  }finally{
    await browser.close();if(child&&child.exitCode===null){child.kill('SIGTERM');await new Promise(resolve=>child.once('exit',resolve));}fs.rmSync(temp,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
