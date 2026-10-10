// An isolated server is started by run_browser.py --mobile. No real records.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined),headless:true,args:['--no-sandbox', ...(process.env.AULA_TEST_PIN ? ['--no-proxy-server'] : [])]});
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
    if (process.env.AULA_TEST_PIN) {
      assert.match(await page.locator('body').innerText(),/Prueba Aula en tu teléfono/);
      await page.getByLabel('Código de 6 dígitos').fill(process.env.AULA_TEST_PIN);
      await page.getByRole('button',{name:'Entrar a la prueba',exact:true}).click();
      await page.getByRole('button',{name:/Entrar como administrador de prueba/}).click();
    } else {
    await page.getByLabel('Nombre del colegio',{exact:true}).fill('Colegio móvil de prueba');
    await page.getByLabel('Nombre del administrador').fill('Administradora móvil');
    await fit('Mobile first setup fits');
    await page.getByLabel('Usuario',{exact:true}).fill('admin');
    await page.getByLabel(/^Contraseña/).fill('Pruebas-movil-2026');
    await page.getByRole('button',{name:'Crear mi cuenta'}).click();
    }
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
    const manifestResponse = await context.request.get(process.env.AULA_TEST_URL+'/manifest.webmanifest');
    assert.match(manifestResponse.headers()['content-type'], /application\/manifest\+json/);
    const manifest = await manifestResponse.json(); assert.equal(manifest.display,'standalone');
    for (const size of [192,512]) {
      const dimensions = await page.evaluate(src => new Promise(resolve => { const img = new Image(); img.onload = () => resolve([img.naturalWidth,img.naturalHeight]); img.src = src; }), `/icon-mobile-${size}.png`);
      assert.deepEqual(dimensions,[size,size]);
    }
    if (process.env.AULA_TEST_PIN) {
      assert.equal(await page.evaluate(() => isSecureContext),false,'Actual LAN HTTP context exercises crypto UUID fallback');
      assert.match(await page.evaluate(() => requestKey()),/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/);
      assert.equal(await page.locator('#phone-install').isVisible(),false,'Wi-Fi trial is browser access');
      assert.match(await page.locator('.demo-banner').innerText(),/Modo prueba/);
    } else {
    // Loopback is a browser-trusted context: register explicitly for this test.
    // Production registration is restricted to the private HTTPS origin.
    await page.evaluate(async () => { await navigator.serviceWorker.register('/service-worker.js'); await navigator.serviceWorker.ready; });
    await page.waitForFunction(() => navigator.serviceWorker.controller !== null);
    const cached = await page.evaluate(async () => { const cache = await caches.open('aula-mobile-public-v3'); return (await cache.keys()).map(r => new URL(r.url).pathname).sort(); });
    assert.deepEqual(cached,['/icon-mobile-192.png','/offline.html'],'No account or financial data is cached');
    await context.setOffline(true);
    await page.locator('#connection-status').waitFor({state:'visible'});
    assert.equal(await page.evaluate(async () => { try { await fetch('/api/state'); return true; } catch { return false; } }),false,'API cannot return stale cached balances offline');
    await page.reload(); await page.getByRole('heading',{name:'No hay conexión al colegio'}).waitFor();
    assert.equal(await page.locator('.layout').count(),0);
    await context.setOffline(false); await page.getByRole('link',{name:'Volver a intentar'}).click();
    await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click(); await page.locator('.layout').waitFor();
    }
    await click('mobile-menu'); await click('logout');
    await page.getByRole('button',{name:process.env.AULA_TEST_PIN ? /Entrar como administrador de prueba/ : 'Iniciar sesión'}).waitFor();
    if(process.env.AULA_TEST_PIN)await click('demo-exit');
    assert.deepEqual(errors,[]);
    console.log(process.env.AULA_TEST_PIN
      ? 'Wi-Fi verificado: código de acceso, administrador de prueba, matrícula, cobro, PDF, 12 secciones, teléfono/tablet, UUID en HTTP, cierre y eliminación de datos temporales.'
      : 'Móvil verificado: matrícula, cobro, PDF, 12 secciones, menú y cierre de sesión, teléfono/tablet, manifiesto, pérdida de conexión y caché sin datos financieros.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
