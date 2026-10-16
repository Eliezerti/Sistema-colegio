const {scratch}=require('./browser_paths.cjs');
// Called by the normal browser suite, with fictional admin/caja/consulta users.
const assert=require('node:assert/strict');
module.exports=async function checkSessions(page,expected){
  const click=async action=>page.locator(`[data-action="${action}"]`).first().click();
  const login=async(username,password)=>{
    await page.locator('.auth-form [name="username"]').fill(username);
    await page.locator('.auth-form [name="password"]').fill(password);
    await page.getByRole('button',{name:'Iniciar sesión'}).click();
    await page.getByRole('button',{name:'Confirmar tasa y entrar'}).click();
    await page.locator('.layout').waitFor();
  };
  const expire=async()=>{
    // Revoke at the real server; the Python tests separately advance monotonic
    // time to prove inactivity. Accelerate only the visual countdown here.
    await page.waitForFunction(()=>!sessionCheckPending);
    expected.active=true;
    const denied=page.waitForResponse(response=>response.url().endsWith('/api/session-status')&&response.status()===401);
    const deniedConsole=page.waitForEvent('console',{predicate:message=>message.type()==='error'&&message.location().url.endsWith('/api/session-status')&&message.text().includes('401 (Unauthorized)')});
    await page.evaluate(async()=>{await api('logout',{});sessionDeadline=performance.now()-1;sessionTick();});
    await page.locator('.session-lock-note').waitFor();
    // Chromium can deliver its console event after rendering the locked view.
    // Match the real rejected response and its console event before ending the expectation.
    await Promise.all([denied,deniedConsole]);
    expected.active=false;
  };
  await page.locator('.nav-button[data-id="settings"]').click();
  await page.getByRole('tab',{name:'Usuarios y acceso',exact:true}).click();
  await page.locator('form[data-endpoint="session-preferences"] [name="idle_minutes"]').fill('5');
  await page.locator('form[data-endpoint="session-preferences"] button[type="submit"]').click();
  await page.waitForFunction(()=>state.settings.session_idle_minutes==='5');
  // Unsaved preferences survive changing configuration tabs.
  await page.locator('form[data-endpoint="session-preferences"] [name="idle_minutes"]').fill('10');
  await page.getByRole('tab',{name:'Identidad y calendario',exact:true}).click();
  await page.getByRole('tab',{name:'Usuarios y acceso',exact:true}).click();
  assert.equal(await page.locator('[name="idle_minutes"]').inputValue(),'10');
  await page.locator('.nav-button[data-id="guardians"]').click();await click('guardian');
  await page.locator('#modal [name="name"]').fill('Borrador ficticio de recuperación');
  let pulses=0;const count=request=>{if(request.url().endsWith('/api/session-activity'))pulses++;};
  page.on('request',count);
  await page.evaluate(async()=>{await checkDay();await sessionCheck();});
  assert.equal(pulses,0,'Automatic queries never renew the session');
  await page.evaluate(()=>{sessionDeadline=performance.now()+45000;sessionCheckedAt=performance.now();sessionTick();});
  await page.locator('#session-warning[open]').waitFor();
  await page.screenshot({path:scratch('aula-aviso-sesion.png')});
  assert.match(await page.locator('#session-countdown').innerText(),/segundos/);
  await page.keyboard.press('Escape');assert.equal(await page.locator('#session-warning').evaluate(node=>node.open),true);
  await page.locator('#session-continue').click();
  await page.waitForFunction(()=>!document.querySelector('#session-warning').open);
  assert.ok(pulses>0);page.off('request',count);
  assert.equal(await page.locator('#modal [name="name"]').inputValue(),'Borrador ficticio de recuperación');
  const before=await page.evaluate(async()=>await api('state'));
  await expire();
  await page.screenshot({path:scratch('aula-cierre-sesion.png')});
  assert.equal(await page.locator('#modal-content').innerText(),'');
  assert.equal(await page.locator('#print-area').innerText(),'');
  assert.equal(await page.locator('.layout').count(),0,'Data must be hidden after expiration');
  assert.equal(await page.evaluate(()=>JSON.stringify(sessionDraft).includes('Borrador ficticio')),true);
  const stores=await page.evaluate(()=>JSON.stringify({local:{...localStorage},session:{...sessionStorage}}));
  assert.ok(!stores.includes('Borrador ficticio'));
  await login('admin','Prueba-segura-2026');
  await page.locator('#modal[open]').waitFor();
  assert.equal(await page.locator('#modal [name="name"]').inputValue(),'Borrador ficticio de recuperación');
  const after=await page.evaluate(async()=>await api('state'));
  for(const table of ['students','guardians','payments','charges'])assert.deepEqual(after[table],before[table],'Resuming cannot submit a draft');
  await click('close');
  await page.locator('.nav-button[data-id="settings"]').click();await page.getByRole('tab',{name:'Usuarios y acceso',exact:true}).click();
  await click('user');await page.locator('#modal [name="name"]').fill('Usuario pendiente ficticio');
  await page.locator('#modal [name="password"]').fill('Secreto-no-conservar-2026');
  await expire();
  assert.ok(!(await page.evaluate(()=>JSON.stringify(sessionDraft))).includes('Secreto-no-conservar-2026'));
  await login('admin','Prueba-segura-2026');await page.locator('#modal[open]').waitFor();
  assert.equal(await page.locator('#modal [name="password"]').inputValue(),'');
  await click('close');
  await page.locator('.nav-button[data-id="guardians"]').click();await click('guardian');
  await page.locator('#modal [name="name"]').fill('Solo pertenece al administrador');
  await expire();await login('consulta','Consulta-segura');
  assert.equal(await page.locator('#modal[open]').count(),0,'Another user cannot recover the previous draft');
  assert.equal(await page.evaluate(()=>sessionDraft),null);
  await click('logout');await login('admin','Prueba-segura-2026');
  // A fixture only for presenting/acknowledging the administrative notice;
  // persistent per-admin notice handling is exercised against SQLite in Python.
  let pending=true;
  await page.route('**/api/session-status',async route=>{
    const response=await route.fetch(),json=await response.json();
    json.recovery_notice=pending?{id:'fictional-notice',username:'admin',occurred_at:'2026-10-12T10:00:00-04:00'}:null;
    await route.fulfill({response,json});
  });
  await page.route('**/api/recovery-notice-ack',async route=>{pending=false;await route.fulfill({status:200,contentType:'application/json',body:'{"ok":true}'});});
  await page.evaluate(()=>sessionCheck());await page.locator('.recovery-session-notice').waitFor();
  assert.match(await page.locator('.recovery-session-notice').innerText(),/Se cerraron todas las sesiones/);
  await click('recovery-notice-ack');await page.waitForFunction(()=>!document.querySelector('.recovery-session-notice'));
  await page.unroute('**/api/session-status');await page.unroute('**/api/recovery-notice-ack');
  await page.locator('.nav-button[data-id="guardians"]').click();await click('guardian');
  await page.locator('#modal [name="name"]').fill('Privado aunque falle el borrador');
  // Also work in older WebView2 without structuredClone. Draft data consists of JSON strings.
  await page.evaluate(()=>{window.structuredClone=undefined;});
  await expire();await login('admin','Prueba-segura-2026');await page.locator('#modal[open]').waitFor();
  assert.equal(await page.locator('#modal [name="name"]').inputValue(),'Privado aunque falle el borrador');
  await page.evaluate(()=>{window.originalCaptureForTest=captureSessionDraft;captureSessionDraft=()=>{throw new Error('Fallo ficticio del borrador');};});
  await expire();
  assert.equal(await page.locator('#modal-content').innerText(),'');assert.equal(await page.locator('.layout').count(),0);
  assert.match(await page.locator('.session-lock-note').innerText(),/No se pudo conservar/);
  assert.equal(await page.evaluate(()=>sessionDraft),null);
  await page.evaluate(()=>{captureSessionDraft=window.originalCaptureForTest;delete window.originalCaptureForTest;});
  await login('admin','Prueba-segura-2026');
  console.log('PASS: A3 warning, activity without background renewal, configurable timeout, RAM-only drafts, same-user recovery, different-user discard, password clearing, administrative notice.');
};
