'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {scratch}=require('./browser_paths.cjs');
module.exports=async function(page){
  const seeded=await page.evaluate(async()=>{
    const s=await api('state?history=1'),config=s.collection_notice_settings;
    const originals={settings:s.settings,notice:{emojis:config.emojis,cashea:config.cashea,payment_details:config.payment_details,templates:config.templates},rate:s.rates.find(r=>r.rate_date===s.today)};
    await api('settings',{...s.settings,school_name:'Colegio FICTICIO Avisos'});
    await api('rates',{rate_date:s.today,rate:'889.26',rate_change_confirmed:true});
    const grade=await api('grades',{name:'Grado FICTICIO Avisos',capacity:30}),guardian=await api('guardians',{name:'MARÍA DE PRUEBA FICTICIA',document:'V-FICTICIO-AVISOS',phone:'0424-000-0000'});
    const first=Number(s.today.slice(0,4))-2,startMonth=Number(s.settings.start_month),start=`${first}-${String(startMonth).padStart(2,'0')}-01`,end=`${first+1}-${String(startMonth===1?12:startMonth-1).padStart(2,'0')}-28`;
    const pupils=[];
    for(const [index,name] of ['ALUMNA FICTICIA AVISOS UNO','HERMANO VON PRUEBA FICTICIO'].entries()){
      const p=await api('students',{name,document:'',birth_date:'',guardian_id:guardian.id,grade_id:grade.id,school_year:first,
        monthly_fee:'40',discount:0,status:'inactive',billing_start:start.slice(0,7),enrollment_start:start,enrollment_end:end});
      pupils.push(p.id);
      for(let i=0;i<(index===0?8:1);i++){
        const d=new Date(first,startMonth-1+i,1,12),period=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
        await api('charges',{student_id:p.id,period,concept:'Mensualidad',amount:'40',due_date:period+'-10'});
      }
    }
    await refresh();return {originals,guardian:guardian.id,pupils,firstPeriod:start.slice(0,7)};
  });
  const nav=async name=>{await page.evaluate(()=>{window.noticeTestPreviousState=state;});await page.locator(`.nav-button[data-id="${name}"]`).click();await page.waitForFunction(()=>state!==window.noticeTestPreviousState);await page.evaluate(()=>{delete window.noticeTestPreviousState;});};
  const ready=()=>page.waitForFunction(()=>document.querySelector('[data-notice-form]')?.dataset.ready==='1'&&!document.querySelector('#collection-text')?.disabled);
  const open=async()=>{await page.evaluate(id=>collection(id),seeded.pupils[0]);await ready();};
  const close=async()=>page.locator('dialog[open] [data-action="close"]').first().click();
  const finance=()=>page.evaluate(async()=>{const s=await api('state?history=1');return {summary:s.summary,payments:s.payments,charges:s.charges,expenses:s.expenses,cashea_cash:s.cashea_cash,cash_closures:s.cash_closures};});
  const capture=async name=>{
    const text=await page.locator('#collection-text').inputValue();assert.match(text,/Fictici[oa]|FICTICIO/);
    const folder=process.env.AULA_NOTICE_CAPTURES;
    if(folder)fs.mkdirSync(folder,{recursive:true});
    await page.locator('dialog[open]').screenshot({path:folder?path.join(folder,name):scratch(name)});
  };
  let modal;
  try{
    const before=await finance();
    await nav('arrears');
    const row=page.locator('#page-content tr').filter({hasText:'ALUMNA FICTICIA AVISOS UNO'});
    await row.getByRole('button',{name:'Aviso',exact:true}).click();await ready();
    modal=page.locator('[data-notice-form]');
    assert.equal(await modal.locator('[name="notice_type"]').inputValue(),'late');
    assert.equal(await modal.locator('[name="notice_siblings"]').isChecked(),false);
    assert.equal(await modal.locator('[name="notice_cashea"]').isChecked(),true);
    assert.match(await page.locator('#collection-text').inputValue(),/y 2 meses más/);
    assert.match(await page.locator('#collection-text').inputValue(),/USD 320,00/);
    await modal.locator('[name="notice_type"]').selectOption('near');await ready();
    assert.match(await page.locator('#collection-text').inputValue(),/María de Prueba Ficticia/);
    await capture('aviso-cercano-ficticio.png');
    const initial=await page.locator('#collection-text').inputValue(),variants=[];
    for(let i=0;i<3;i++){await modal.getByRole('button',{name:'Otra versión',exact:true}).click();await ready();variants.push(await page.locator('#collection-text').inputValue());}
    assert.equal(new Set(variants).size,3);assert.equal(variants[2],initial);
    const edited='Aviso FICTICIO editado: María 👋\nSaldo & consulta, ñ y tildes.';
    await page.locator('#collection-text').fill(edited);
    await modal.locator('[name="notice_type"]').focus();
    assert.equal(await page.locator('#collection-text').inputValue(),edited,'Leaving the text field must preserve the manual edit');
    assert.equal(await modal.evaluate(f=>f.dataset.ready),'1');
    const href=await modal.locator('#wa-collection').getAttribute('href');assert.equal(new URL(href).searchParams.get('text'),edited);
    assert.match(href,/^https:\/\/wa.me\/584240000000\?/);
    await page.context().grantPermissions(['clipboard-read','clipboard-write']);
    await modal.getByRole('button',{name:'Copiar aviso',exact:true}).click();assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),edited);
    assert.equal((await page.evaluate(()=>api('state?history=1'))).collections.filter(n=>n.student_id===seeded.pupils[0]).length,0);
    await modal.getByRole('button',{name:'Restablecer texto',exact:true}).click();await ready();
    assert.equal(await page.locator('#collection-text').inputValue(),initial);
    await modal.locator('[name="notice_cashea"]').uncheck();await ready();assert.doesNotMatch(await page.locator('#collection-text').inputValue(),/Cashea/);
    await modal.locator('[name="notice_cashea"]').check();await ready();
    const markRequest=page.waitForRequest(r=>r.url().endsWith('/api/collection-notice-mark')&&r.method()==='POST');
    const markResponse=page.waitForResponse(r=>r.url().endsWith('/api/collection-notice-mark')&&r.request().method()==='POST');
    await modal.getByRole('button',{name:'Marcar como enviado',exact:true}).click();
    const request=(await markRequest).postDataJSON(),response=await markResponse;assert.equal(response.status(),200);
    const saved=await response.json();await modal.getByRole('button',{name:'Marcado como enviado',exact:true}).waitFor();
    assert.equal(await modal.getByRole('button',{name:'Marcado como enviado',exact:true}).isDisabled(),true);
    assert.match(await modal.locator('.notice-last').innerText(),/hace 0 días/);
    const repeat=await page.evaluate(data=>api('collection-notice-mark',data),request);
    assert.equal(repeat.duplicate,true);assert.deepEqual(repeat.note_ids,saved.note_ids);
    await close();await open();assert.match(await page.locator('.notice-last').innerText(),/hace 0 días/);
    modal=page.locator('[data-notice-form]');await modal.locator('[name="notice_siblings"]').check();await ready();
    assert.match(await page.locator('#collection-text').inputValue(),/Hermano von Prueba Ficticio/);assert.match(await page.locator('#collection-text').inputValue(),/USD 360,00/);
    await capture('aviso-hermanos-ficticio.png');
    await page.evaluate(async id=>{const g=(await api('state?history=1')).guardians.find(g=>g.id===id);await api('guardians',{...g,phone:'teléfono inválido FICTICIO'});},seeded.guardian);
    await modal.getByRole('button',{name:'Restablecer texto'}).click();await ready();
    assert.equal(await modal.getByRole('button',{name:'Abrir WhatsApp con el aviso',exact:true}).isDisabled(),true);
    assert.equal(await modal.getByRole('button',{name:'Copiar aviso',exact:true}).isEnabled(),true);assert.match(await modal.locator('.notice-phone-error').innerText(),/teléfono/);
    await page.evaluate(async id=>{const g=(await api('state?history=1')).guardians.find(g=>g.id===id);await api('guardians',{...g,phone:'0424-000-0000'});},seeded.guardian);
    await close();
    await nav('settings');await page.getByRole('tab',{name:'Avisos de cobranza',exact:true}).click();
    const settings=page.locator('.notice-settings-form');
    await settings.locator('[name="notice_payment_details"]').fill('Datos FICTICIOS para pagar: consulte con administración.');
    await settings.locator('[name="notice_emojis"]').selectOption('0');
    const original=await settings.locator('[name="notice_template_near_0"]').inputValue();
    await settings.locator('[name="notice_template_near_0"]').fill('Personalizado FICTICIO para {representante}\n{saludo}: {meses}\nTotal {total_usd}\n{total_bs}\n{cashea}\n{pago}');
    await page.getByRole('tab',{name:'Identidad y calendario',exact:true}).click();await page.getByRole('tab',{name:'Avisos de cobranza',exact:true}).click();
    assert.match(await settings.locator('[name="notice_template_near_0"]').inputValue(),/^Personalizado FICTICIO/);
    const previewResponse=page.waitForResponse(r=>r.url().endsWith('/api/collection-notice-template-preview'));
    await settings.getByRole('button',{name:'Vista previa con datos ficticios'}).click();assert.equal((await previewResponse).status(),200);
    await settings.locator('.notice-example:not([hidden])').waitFor();assert.match(await settings.locator('.notice-example textarea').inputValue(),/Fictici[oa]|FICTICIO/);
    assert.doesNotMatch(await settings.locator('.notice-example textarea').inputValue(),/👋/);
    const savedSettings=page.waitForResponse(r=>r.url().endsWith('/api/collection-notice-settings'));
    await settings.getByRole('button',{name:'Guardar ajustes de avisos'}).click();assert.equal((await savedSettings).status(),200);
    await page.waitForFunction(()=>state.collection_notice_settings.emojis===false);
    await open();modal=page.locator('[data-notice-form]');await modal.locator('[name="notice_type"]').selectOption('near');await ready();
    for(let i=0;i<3&&await modal.evaluate(f=>f.notice.variant)!==0;i++){await modal.getByRole('button',{name:'Otra versión'}).click();await ready();}
    assert.match(await page.locator('#collection-text').inputValue(),/^Personalizado FICTICIO/);
    await modal.locator('[name="notice_payment"]').check();await ready();assert.match(await page.locator('#collection-text').inputValue(),/Datos FICTICIOS para pagar/);
    assert.doesNotMatch(await page.locator('#collection-text').inputValue(),/👋/);await close();
    await page.getByRole('tab',{name:'Avisos de cobranza',exact:true}).click();
    await page.locator('.notice-settings-form').getByRole('button',{name:'Restaurar original'}).click();
    assert.equal(await page.locator('[name="notice_template_near_0"]').inputValue(),original);
    // A response obtained before session lock must never reopen a personal notice.
    let release,arrived;const held=new Promise(resolve=>release=resolve),received=new Promise(resolve=>arrived=resolve);
    const matcher='**/api/collection-notice?*',hold=async route=>{const response=await route.fetch();arrived();await held;await route.fulfill({response});};
    await page.route(matcher,hold);
    try{
      await page.evaluate(id=>{window.pendingNoticeTest=collection(id).then(()=>({completed:true}),error=>({error:error.message}));},seeded.pupils[0]);await received;
      await page.evaluate(()=>lockSession());release();const late=await page.evaluate(()=>window.pendingNoticeTest);
      assert.match(late.error,/La sesión cambió/,'The existing API must reject the response from the previous session');
      assert.equal(await page.locator('[data-notice-form]').count(),0,'Late notice response cannot reopen the locked session');
      assert.equal(await page.locator('.auth-form').isVisible(),true);
    }finally{release();await page.unroute(matcher,hold);await page.evaluate(()=>{delete window.pendingNoticeTest;});}
    await page.locator('.auth-form [name="username"]').fill('admin');await page.locator('.auth-form [name="password"]').fill('Prueba-segura-2026');
    await page.getByRole('button',{name:'Iniciar sesión',exact:true}).click();await page.getByRole('button',{name:'Confirmar tasa y entrar',exact:true}).click();await page.locator('.layout').waitFor();
    assert.deepEqual(await finance(),before,'Avisos and settings cannot change any financial ledger or summary');
    const state=await page.evaluate(()=>api('state?history=1'));
    assert.equal(state.collections.filter(n=>n.student_id===seeded.pupils[0]).length,1);
    assert.equal(state.collections.filter(n=>n.student_id===seeded.pupils[1]).length,0,'Including siblings in preview does not mark them');
    assert.equal((await page.evaluate(()=>api('maintenance-review'))).ok,true);
    console.log('PASS AVISOS: cinco tipos, meses y total completo, variantes, edición conservada al salir y URL actual, copiar sin registrar, marca manual idempotente, hermanos, teléfono inválido, ajustes/preview/restauración, respuesta tardía descartada al bloquear sesión y dinero intacto; capturas FICTICIAS.');
  }finally{
    await page.evaluate(async originals=>{if(!session)return;await api('collection-notice-settings',originals.notice);await api('settings',originals.settings);if(originals.rate)await api('rates',{rate_date:originals.rate.rate_date,rate:originals.rate.rate,rate_change_confirmed:true});await refresh();},seeded.originals);
  }
};
