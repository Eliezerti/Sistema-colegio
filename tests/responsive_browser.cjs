// An isolated server is started by run_browser.py --responsive. No real records.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined),headless:true,args:['--no-sandbox']});
  const context = await browser.newContext({viewport:{width:375,height:812},isMobile:true,hasTouch:true});
  const page = await context.newPage(), errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const click = action => page.locator(`[data-action="${action}"]`).first().click();
  const nav = async id => { await click('mobile-menu'); await page.locator(`.nav-button[data-id="${id}"]`).click(); };
  const fit = async label => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, label);
  const fill = (name,value) => page.locator(`dialog[open] [name="${name}"]`).fill(value);
  const save = async () => { await page.locator('dialog[open] button[type="submit"]').click(); await page.waitForFunction(() => !document.querySelector('dialog').open); };
  try {
    await page.goto(process.env.AULA_TEST_URL);
    await page.getByLabel('Nombre del colegio',{exact:true}).fill('Colegio móvil de prueba');
    await page.getByLabel('Nombre del administrador').fill('Administradora móvil');
    await fit('Mobile first setup fits');
    await page.getByLabel('Usuario',{exact:true}).fill('admin');
    await page.getByLabel(/^Contraseña/).fill('Pruebas-movil-2026');
    await page.getByRole('button',{name:'Crear mi cuenta'}).click();
    await page.locator('form[data-endpoint="confirm-rate"] [name="rate"]').fill('100');
    await fit('Mobile rate gate fits');
    await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();
    await page.locator('.layout').waitFor();
    assert.equal(await page.locator('.sidebar').evaluate(el => el.inert), true);
    await click('mobile-menu');
    assert.equal(await page.locator('.sidebar-footer').isVisible(), true, 'Phone exposes profile and logout');
    assert.equal(await page.locator('.main').evaluate(el => el.inert), true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('[data-action="mobile-menu"]').evaluate(el => el === document.activeElement), true);
    await nav('grades'); await click('grade'); await fill('name','Primaria A'); await save();
    await nav('guardians'); await click('guardian'); await fill('name','Representante de prueba'); await fill('document','V-123'); await save();
    await nav('students'); await click('student'); await fill('name','Alumno móvil'); await fill('birth_date','2015-02-10'); await fill('monthly_fee','100');
    await page.locator('dialog[open] [name="guardian_id"]').selectOption({label:'V-123 · Representante de prueba'});
    await fit('Enrollment modal fits');
    await page.locator('dialog[open] button[type="submit"]').click();
    await page.locator('dialog[open] .receipt-number').waitFor();
    await click('close');
    await nav('payments'); await click('payment');
    await page.locator('dialog[open] [name="currency"]').selectOption('VES');
    await fill('amount','1000'); await fill('reference','MOVIL-001');
    await page.locator('dialog[open] button[type="submit"]').click();
    await page.locator('dialog[open] .receipt-number').waitFor();
    await fit('Receipt on phone fits');
    const download = page.waitForEvent('download');
    await page.getByRole('link',{name:'Descargar PDF'}).click();
    const file = await download;
    assert.ok(fs.readFileSync(await file.path()).subarray(0,5).equals(Buffer.from('%PDF-')));
    await click('close');
    for (const id of ['dashboard','students','guardians','grades','billing','payments','cash','arrears','employees','expenses','reports','settings']) {
      await nav(id); await fit(`Phone section ${id} fits`);
    }
    await page.setViewportSize({width:320,height:740}); await fit('Small phone fits');
    await page.setViewportSize({width:820,height:1180});
    assert.equal(await page.locator('.sidebar').evaluate(el => el.inert), false, 'Tablet preserves desktop menu');
    await fit('Tablet fits');
    await page.setViewportSize({width:375,height:812});
    assert.equal(await page.locator('link[rel="manifest"],#phone-install').count(),0);
    const removed = await context.request.get(process.env.AULA_TEST_URL+'/manifest.webmanifest');
    assert.equal(removed.status(),404);
    await page.evaluate(async () => {
      await caches.open('aula-mobile-public-v3'); await caches.open('unrelated-app');
    });
    await page.addScriptTag({url:process.env.AULA_TEST_URL+'/responsive.js'});
    await page.waitForFunction(async () => !(await caches.keys()).includes('aula-mobile-public-v3'));
    assert.equal(await page.evaluate(async () => (await caches.keys()).includes('unrelated-app')),true);
    await context.setOffline(true);
    await page.locator('#connection-status').waitFor({state:'visible'});
    assert.equal(await page.evaluate(async () => { try { await fetch('/api/state'); return true; } catch { return false; } }),false);
    await context.setOffline(false);
    await page.locator('#connection-status').waitFor({state:'hidden'});
    await click('mobile-menu'); await click('logout');
    await page.getByRole('button',{name:'Iniciar sesión'}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('PASS: narrow-window menu, forms, payment PDF, all sections, logout, offline indication and retirement of former Aula cache without touching another cache.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
