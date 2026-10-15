'use strict';
// Authentication drafts and deadlines stay in RAM, never in browser storage.
let sessionDeadline=0, sessionGeneration=0, sessionPulseAt=-Infinity;
let sessionPulsePending=false, sessionCheckPending=false, sessionCheckedAt=-Infinity;
let sessionDraft=null, recoveryNotice=null, sessionWarning;
const draftEndpoints=new Set(['students','guardians','grades','payments','expenses','charges',
  'close-cash','rates','settings','backup-directory','session-preferences','users','password',
  'payment-plans','collections','generate','correct-billing-start']);

function sessionHeaders(response, started){
  const remaining=Number(response.headers.get('X-Aula-Idle-Remaining'));
  if(response.headers.has('X-Aula-Idle-Remaining')&&Number.isFinite(remaining)){
    // Subtract the full request duration rather than treating an old response as activity.
    sessionDeadline=performance.now()+Math.max(0,remaining*1000-(performance.now()-started));
    if(remaining>60)sessionWarning?.close();
  }
}

function sessionInit(){
  sessionWarning=document.createElement('dialog');sessionWarning.id='session-warning';
  sessionWarning.innerHTML='<div class="session-warning-body"><h2>Tu sesión está por cerrarse</h2><p>Por tu seguridad, Aula cierra la sesión cuando no hay actividad.</p><p>Tiempo restante: <strong id="session-countdown"></strong></p><p class="hint">Si estabas llenando un formulario, puedes seguir trabajando.</p><button type="button" class="btn primary" id="session-continue">Seguir trabajando</button><p class="error" role="alert"></p></div>';
  document.body.append(sessionWarning);
  sessionWarning.addEventListener('cancel',event=>event.preventDefault());
  $('#session-continue').addEventListener('click',()=>sessionPulse(true).catch(error=>{
    $('.error',sessionWarning).textContent=error.message;
  }));
  for(const name of ['pointerdown','keydown','input','wheel'])document.addEventListener(name,event=>{
    if(event.isTrusted&&session&&!sessionWarning.open)sessionPulse().catch(()=>{});
  },{passive:true});
  setInterval(sessionTick,1000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)sessionCheck().catch(()=>{});});
}

async function sessionPulse(force=false){
  if(!session||sessionPulsePending||(!force&&performance.now()-sessionPulseAt<15000&&sessionDeadline-performance.now()>60000))return;
  sessionPulsePending=true;
  try{
    await api('session-activity',{});
    sessionPulseAt=performance.now();sessionWarning.close();
  }finally{sessionPulsePending=false;}
}

async function sessionCheck(){
  if(!session||sessionCheckPending)return;
  sessionCheckPending=true;
  try{
    const result=await api('session-status');recoveryNotice=result.recovery_notice;
    showRecoveryNotice();sessionCheckedAt=performance.now();
  }finally{sessionCheckPending=false;}
}

function sessionTick(){
  if(!session||!sessionDeadline)return;
  const left=Math.ceil((sessionDeadline-performance.now())/1000);
  if(left<=60&&performance.now()-sessionCheckedAt>15000)sessionCheck().catch(()=>{
    if(session&&sessionDeadline<=performance.now())lockSession();
  });
  if(left<=0){
    // Another tab may have registered activity. Verify without renewing; while
    // disconnected, hide the interface rather than leave an unattended form open.
    sessionCheck().then(()=>{if(session&&sessionDeadline<=performance.now())lockSession();}).catch(()=>{if(session)lockSession();});
    if(!sessionWarning.open&&!document.hidden)sessionWarning.showModal();
    $('#session-countdown').textContent='Comprobando sesión…';
    const generation=sessionGeneration;
    setTimeout(()=>{if(session&&generation===sessionGeneration&&sessionDeadline<=performance.now())lockSession();},1500);
    return;
  }
  if(left<=60&&!document.hidden){
    $('#session-countdown').textContent=`${left} segundos`;
    if(!sessionWarning.open)sessionWarning.showModal();
  }
}

function captureSessionDraft(){
  if(!state||!session)return;
  rememberSettingsDrafts();
  const content=$('#modal-content'),form=content.querySelector('form[data-endpoint]');
  let markup='';
  if(modal.open&&form&&draftEndpoints.has(form.dataset.endpoint)){
    const copy=content.cloneNode(true),originals=content.querySelectorAll('input,textarea,select');
    copy.querySelectorAll('input,textarea,select').forEach((node,index)=>{
      const original=originals[index];
      if(node.type==='password'||node.type==='file'){
        node.value='';node.removeAttribute('value');return;
      }
      if(node.tagName==='TEXTAREA')node.textContent=original.value;
      else if(node.tagName==='SELECT')Array.from(node.options).forEach((option,i)=>option.toggleAttribute('selected',original.options[i].selected));
      else{node.setAttribute('value',original.value);node.toggleAttribute('checked',original.checked);}
      node.disabled=false;
    });
    copy.querySelectorAll('button[type="submit"]').forEach(button=>button.disabled=false);
    copy.querySelectorAll('.error').forEach(node=>node.textContent='');
    markup=copy.innerHTML;
  }
  sessionDraft={id:session.id,role:session.role,username:session.username,page,
                section:settingsSection,drafts:JSON.parse(JSON.stringify(settingsDrafts)),markup};
}

function lockSession(){
  let captureFailed=false;
  if(session){
    try{captureSessionDraft();}catch{sessionDraft=null;captureFailed=true;}
    publicSchool=state?.settings||publicSchool;
  }
  sessionGeneration++;sessionDeadline=0;sessionWarning?.close();recoveryNotice=null;
  yearCohort=yearPreview=yearRequest=rosterFile=rosterPreview=cashPreview=undefined;
  gateBackup=gateRole=undefined;filters={};
  session=undefined;state=undefined;settingsDrafts={};modal.close();
  $('#modal-content').replaceChildren();$('#print-area').replaceChildren();app.replaceChildren();auth(false);
  const message=document.createElement('p');message.className='notice warning session-lock-note';
  message.textContent='Tu sesión terminó. Entra nuevamente para continuar.'+
    (captureFailed?' No se pudo conservar el borrador. Revisa los registros antes de volver a llenarlo.':sessionDraft?' Tu borrador está guardado solo en esta ventana. Al entrar con el mismo usuario podrás retomarlo; todavía no se ha guardado en la base.':'');
  app.prepend(message);
  const username=app.querySelector('[name="username"]');if(username&&sessionDraft)username.value=sessionDraft.username;
}

async function resumeSessionDraft(){
  if(!state||!sessionDraft)return;
  const saved=sessionDraft;sessionDraft=null;
  if(saved.id!==state.user.id||saved.role!==state.user.role){
    toast('Se descartó el borrador de la sesión anterior porque cambió el usuario o su perfil.');return;
  }
  page=saved.page;settingsSection=saved.section;settingsDrafts=saved.drafts;
  render();
  if(saved.markup){
    modal.classList.remove('document-modal','wide-modal');$('#modal-content').innerHTML=saved.markup;modal.showModal();
    updateConversion();if($('form[data-endpoint="students"]',modal))updateTuition();
    const cash=$('form[data-endpoint="close-cash"]',modal);
    if(cash){
      const values=Object.fromEntries(new FormData(cash));cashDate=values.closed_on;
      await openCash();const fresh=$('form[data-endpoint="close-cash"]',modal);
      for(const name of ['opening_USD','opening_VES','counted_USD','counted_VES','notes'])fresh.elements[name].value=values[name];
      updateCashCount();
    }
  }
  toast('Borrador recuperado. Revisa los datos y saldos antes de guardar. No se envió automáticamente.');
}

function forgetSessionDraft(){
  sessionDraft=null;settingsDrafts={};recoveryNotice=null;sessionGeneration++;
  yearCohort=yearPreview=yearRequest=rosterFile=rosterPreview=cashPreview=undefined;
  sessionDeadline=0;sessionWarning?.close();
}

function showRecoveryNotice(){
  document.querySelectorAll('.recovery-session-notice').forEach(node=>node.remove());
  if(!session||session.role!=='admin'||!recoveryNotice)return;
  const box=document.createElement('aside');box.className='notice warning recovery-session-notice';box.setAttribute('role','alert');
  if(recoveryNotice.unreadable){box.textContent='No se pudo leer el aviso de recuperación de acceso. Pide una revisión técnica.';}
  else{
    box.innerHTML=`<b>Se recuperó una contraseña de administrador</b><p>Cuenta: ${esc(recoveryNotice.username)} · ${esc(clockTime(recoveryNotice.occurred_at))}. Se cerraron todas las sesiones. Si no reconoces esta recuperación, revisa quién tiene acceso a Windows.</p>${btn('Ya revisé este aviso','recovery-notice-ack','small')}`;
  }
  const main=app.querySelector('.main');if(main)main.querySelector('.topbar').after(box);else app.prepend(box);
}

async function acknowledgeRecoveryNotice(){
  await api('recovery-notice-ack',{notice_id:recoveryNotice.id});recoveryNotice=null;showRecoveryNotice();
}
