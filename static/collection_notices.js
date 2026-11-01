'use strict';
// Context and editable text belong to the modal DOM, which session lock clears.
async function openCollectionNotice(id){
  const generation=sessionGeneration;
  const value=await api('collection-notice?student_id='+Number(id));
  if(!session||generation!==sessionGeneration)return;
  showModal('Aviso de cobranza',`Representante: ${esc(value.guardian_name)}`,
    `<form class="collection-notice-form" data-notice-form data-student-id="${Number(id)}"><p class="hint">Revisa el texto antes de compartirlo. Aula prepara el aviso; tú decides cuándo copiarlo o abrir WhatsApp. Marcarlo es un registro manual.</p>`+
    select('Tipo de mensaje','notice_type',Object.entries(value.types),value.type)+
    `<div class="notice-options"><label><input type="checkbox" name="notice_siblings"> Incluir a los hermanos con deuda</label>`+
    `<label><input type="checkbox" name="notice_cashea" ${value.cashea?'checked':''} ${value.cashea_available?'':'disabled'}> Mencionar Cashea</label>`+
    `<label><input type="checkbox" name="notice_payment"> Incluir datos de pago</label></div>`+
    `<p class="notice-last" aria-live="polite"></p><label class="field">Texto del aviso<textarea id="collection-text" rows="12" maxlength="1000000">${esc(value.text)}</textarea></label>`+
    `<div class="notice-variants"><button type="button" class="btn small" data-notice-action="version">Otra versión</button><button type="button" class="btn small" data-notice-action="reset">Restablecer texto</button><span class="muted notice-version"></span></div>`+
    `<div class="error" role="alert"></div><div class="form-actions">${btn('Copiar aviso','copy-collection','primary')}<span class="notice-whatsapp"></span>`+
    `<button type="button" class="btn" data-notice-action="mark" ${writable()&&value.eligible?'':'disabled'}>Marcar como enviado</button></div></form>`);
  const form=modal.querySelector('[data-notice-form]');form.notice=value;form.noticeKey=requestKey();form.dataset.ready='1';
  form.addEventListener('submit',event=>event.preventDefault());updateNoticeLinks(form);
}
function updateNoticeLinks(form){
  if(!form?.isConnected)return;
  const value=form.notice,text=$('#collection-text',form).value;
  $('.notice-version',form).textContent=`Versión ${value.variant+1} de 3`;
  $('.notice-last',form).textContent=value.last_notice?`Último aviso: hace ${value.last_notice.days} ${value.last_notice.days===1?'día':'días'} (${value.last_notice.type}).`:'Último aviso: todavía no hay un aviso marcado como enviado.';
  $('.notice-whatsapp',form).innerHTML=value.eligible?whatsappLink(value.phone,text):'<button type="button" class="btn" disabled>Abrir WhatsApp con el aviso</button>';
  if(!value.phone){const hint=document.createElement('small');hint.className='notice-phone-error';hint.textContent=value.phone_error;$('.notice-whatsapp',form).append(hint);}
  const mark=$('[data-notice-action="mark"]',form);mark.disabled=!writable()||!value.eligible||form.dataset.ready!=='1'||form.dataset.marked==='1';
  mark.textContent=form.dataset.marked==='1'?'Marcado como enviado':'Marcar como enviado';
}
async function regenerateNotice(form,next=false){
  const generation=(form.noticeGeneration||0)+1;form.noticeGeneration=generation;form.dataset.ready='0';
  const current=form.notice;
  const query=new URLSearchParams({student_id:form.dataset.studentId,type:form.elements.notice_type.value,
    variant:String(next?(current.variant+1)%3:current.variant),siblings:form.elements.notice_siblings.checked?'1':'0',
    cashea:form.elements.notice_cashea.checked?'1':'0',payment:form.elements.notice_payment.checked?'1':'0'});
  const text=$('#collection-text',form);text.disabled=true;$('.error',form).textContent='';updateNoticeLinks(form);
  try{
    const value=await api('collection-notice?'+query);
    if(!form.isConnected||form.noticeGeneration!==generation)return;
    form.notice=value;text.value=value.text;form.noticeKey=requestKey();form.dataset.marked='0';form.dataset.ready='1';
  }catch(error){if(form.isConnected&&form.noticeGeneration===generation)$('.error',form).textContent=error.message;}
  finally{if(form.isConnected&&form.noticeGeneration===generation){text.disabled=false;updateNoticeLinks(form);}}
}
async function markCollectionNotice(form){
  if(form.dataset.ready!=='1'||form.dataset.marked==='1'||form.dataset.marking==='1')return;
  form.dataset.marking='1';const button=$('[data-notice-action="mark"]',form);button.disabled=true;
  $('.error',form).textContent='';
  const value=form.notice;
  const data={student_id:Number(form.dataset.studentId),type:value.type,variant:value.variant,
    siblings:value.siblings,student_ids:value.student_ids,message:$('#collection-text',form).value,request_key:form.noticeKey};
  const inputs=Array.from(form.querySelectorAll('input,select,textarea,[data-notice-action]')).map(node=>[node,node.disabled]);
  for(const [node] of inputs)node.disabled=true;
  try{
    const result=await api('collection-notice-mark',data);
    if(!form.isConnected)return;
    form.dataset.marked='1';
    form.notice.last_notice={days:0,type:value.types[value.type]};
    toast(result.duplicate?'El aviso ya estaba registrado.':'Aviso marcado manualmente como enviado.');
    if(result.backup_warning)toast(result.backup_warning,true);
  }catch(error){if(form.isConnected)$('.error',form).textContent=error.message;}
  finally{if(form.isConnected){for(const [node,disabled] of inputs)node.disabled=disabled;form.dataset.marking='0';updateNoticeLinks(form);}}
}
function noticeSettingValue(name){
  const v=state.collection_notice_settings;if(!v)return '';
  if(name==='notice_emojis')return v.emojis?'1':'0';
  if(name==='notice_cashea_default')return v.cashea?'1':'0';
  if(name==='notice_payment_details')return v.payment_details;
  const match=/^notice_template_([a-z]+)_([0-2])$/.exec(name);
  return match?v.templates[match[1]][Number(match[2])]:'';
}
function noticeSettingsPanel(){
  const v=state.collection_notice_settings;if(!v)return '';
  const draft=settingsDrafts['collection-notice-settings']||{},val=name=>draft[name]??noticeSettingValue(name);
  return card('Avisos de cobranza',`<form class="card-body notice-settings-form" data-endpoint="collection-notice-settings"><p class="hint">Aula prepara un aviso por familia; no envía mensajes. Los originales están disponibles aunque nunca guardes estos ajustes.</p><div class="form-grid">`+
    select('Emojis en los avisos','notice_emojis',[['1','Activados · máximo dos'],['0','Desactivados']],val('notice_emojis'))+
    select('Mencionar Cashea por defecto','notice_cashea_default',[['1','Sí'],['0','No']],val('notice_cashea_default'),v.cashea_available?'':'disabled')+
    textarea('Datos para pagar (opcional)','notice_payment_details',val('notice_payment_details'),2000)+
    `<p class="hint full">Texto libre del colegio. No se valida ni interpreta su contenido. Solo se incluye cuando la persona marca Incluir datos de pago.</p>`+
    `<label class="field">Plantilla a editar<select data-notice-editor-type>${Object.entries(v.types).map(([key,label])=>`<option value="${key}">${esc(label)}</option>`).join('')}</select></label>`+
    `<label class="field">Versión<select data-notice-editor-version>${[0,1,2].map(i=>`<option value="${i}">Versión ${i+1}</option>`).join('')}</select></label>`+
    Object.keys(v.types).map(key=>[0,1,2].map(i=>`<div class="field full notice-template-slot" data-notice-slot="${key}:${i}" ${key==='near'&&i===0?'':'hidden'}>${textarea('Texto de la plantilla',`notice_template_${key}_${i}`,val(`notice_template_${key}_${i}`),4000)}</div>`).join('')).join('')+
    `<p class="hint full">Marcadores: ${v.markers.map(m=>`{${esc(m)}}`).join(', ')}. Conserva {meses} y {total_usd}. La vista previa usa datos ficticios.</p></div>`+
    `<div class="actions"><button type="button" class="btn" data-notice-setting="restore">Restaurar original</button><button type="button" class="btn" data-notice-setting="preview">Vista previa con datos ficticios</button></div>`+
    `<label class="field notice-example" hidden>Vista previa FICTICIA<textarea rows="11" readonly></textarea></label><p class="hint">Restaurar cambia solo la versión seleccionada; pulsa Guardar para aplicarlo.</p>`+
    `<div class="error" role="alert"></div><div class="form-actions"><button type="submit" class="btn primary">Guardar ajustes de avisos</button></div></form>`);
}
function noticeSettingsPayload(form){
  const templates={};for(const key of Object.keys(state.collection_notice_settings.types))templates[key]=[0,1,2].map(i=>form.elements[`notice_template_${key}_${i}`].value);
  return {emojis:form.elements.notice_emojis.value==='1',cashea:form.elements.notice_cashea_default.value==='1',
    payment_details:form.elements.notice_payment_details.value,templates};
}
function noticeEditorSelection(form){return {type:$('[data-notice-editor-type]',form).value,variant:Number($('[data-notice-editor-version]',form).value)};}
function showNoticeEditor(form){
  const selected=noticeEditorSelection(form);for(const slot of form.querySelectorAll('[data-notice-slot]'))slot.hidden=slot.dataset.noticeSlot!==`${selected.type}:${selected.variant}`;
}
document.addEventListener('change',event=>{
  const notice=event.target.closest('[data-notice-form]');
  if(notice&&event.target.matches('select,input[type="checkbox"]')){regenerateNotice(notice);return;}
  const settings=event.target.closest('.notice-settings-form');if(settings&&event.target.matches('[data-notice-editor-type],[data-notice-editor-version]'))showNoticeEditor(settings);
});
document.addEventListener('input',event=>{
  const form=event.target.closest('[data-notice-form]');if(!form||event.target.id!=='collection-text')return;
  if(form.dataset.marked==='1'){form.dataset.marked='0';form.noticeKey=requestKey();}
  updateNoticeLinks(form);
});
document.addEventListener('click',async event=>{
  const action=event.target.closest('[data-notice-action]');
  if(action){const form=action.closest('[data-notice-form]');if(action.dataset.noticeAction==='mark')await markCollectionNotice(form);else await regenerateNotice(form,action.dataset.noticeAction==='version');return;}
  const setting=event.target.closest('[data-notice-setting]');if(!setting)return;
  const form=setting.closest('.notice-settings-form'),selected=noticeEditorSelection(form);$('.error',form).textContent='';
  if(setting.dataset.noticeSetting==='restore'){
    form.elements[`notice_template_${selected.type}_${selected.variant}`].value=state.collection_notice_settings.defaults[selected.type][selected.variant];return;
  }
  setting.disabled=true;
  try{const result=await api('collection-notice-template-preview',{...noticeSettingsPayload(form),...selected});if(form.isConnected){const preview=$('.notice-example',form);preview.hidden=false;$('textarea',preview).value=result.text;}}
  catch(error){if(form.isConnected)$('.error',form).textContent=error.message;}
  finally{if(form.isConnected)setting.disabled=false;}
});
// This form saves only its own preferences. Other settings continue using their existing handler.
document.addEventListener('submit',async event=>{
  const form=event.target;if(!form.matches('.notice-settings-form'))return;
  event.preventDefault();event.stopImmediatePropagation();
  const selected=noticeEditorSelection(form),button=form.querySelector('[type="submit"]');button.disabled=true;$('.error',form).textContent='';
  try{
    await api('collection-notice-settings',noticeSettingsPayload(form));await refresh('collection-notice-settings');
    const fresh=document.querySelector('.notice-settings-form');if(fresh){$('[data-notice-editor-type]',fresh).value=selected.type;$('[data-notice-editor-version]',fresh).value=String(selected.variant);showNoticeEditor(fresh);}
    toast('Ajustes de avisos guardados.');
  }catch(error){if(form.isConnected)$('.error',form).textContent=error.message;}
  finally{if(form.isConnected)button.disabled=false;}
},true);
