'use strict';
// Only RAM and server records. Fiscal drafts never use browser storage.
let invoiceBook=null, invoiceMonth='', invoiceOffset=0;
const invoiceURLs=new Set();
const invoiceVars=['fecha','numero_factura','numero_control','cliente','documento_cliente','direccion','concepto','forma_pago','referencia','tasa','exento','base','iva','igtf','total','observaciones','usuario','recibo','moneda','mes','año','grado','etiqueta_iva','etiqueta_igtf'];
const invoiceEndpoints=['invoice-config','invoice-batch','invoice-template','invoice-template-restore','invoice-import-template','invoice-profile','invoice-draft','invoice-edit-draft','invoice-issue','invoice-damaged','invoice-void','invoice-print','invoice-select-receipt'];
invoiceEndpoints.forEach(name=>draftEndpoints.add(name));
function clearInvoiceMemory(){invoiceBook=null;invoiceMonth='';invoiceOffset=0;invoiceDrag=null;invoiceURLs.forEach(url=>URL.revokeObjectURL(url));invoiceURLs.clear();}
const ib=(label,action,id='',style='')=>'<button type="button" class="btn '+style+'" data-inv-action="'+esc(action)+'" data-id="'+esc(id)+'">'+label+'</button>';
const icheck=(label,name,checked=false,extra='')=>'<label class="confirm-check"><input type="checkbox" name="'+esc(name)+'" '+(checked?'checked ':'')+extra+'> '+esc(label)+'</label>';
const ihidden=(name,value)=>'<input type="hidden" name="'+esc(name)+'" value="'+esc(value)+'">';
function invoiceForm(endpoint,body,submit,extra=''){return '<form data-endpoint="'+endpoint+'" '+extra+'>'+body+formFoot(submit)+'</form>';}
function invoiceAmount(cents,currency){return currency==='VES'?bs(cents):usd(cents);}
async function loadInvoicePage(){
  invoiceMonth ||=state.today.slice(0,7);
  invoiceBook=await api('invoice-book?month='+encodeURIComponent(invoiceMonth)+'&offset='+invoiceOffset);
}
async function ensureInvoiceBook(){await loadInvoicePage();return invoiceBook;}
function invoicesPage(){
  const d=invoiceBook;if(!d)return '<p>Cargando facturas…</p>';
  let html=heading('Facturas preimpresas','Datos variables sobre formularios de imprenta; los recibos de pago se conservan.',
    (writable()?ib('Desde un recibo','new')+ib('Hoja dañada','damaged'):'')+(admin()?ib('Configurar emisión','config'):''));
  html+='<p class="notice warning">'+esc(d.warning)+' Aula no se conecta al SENIAT ni calcula IVA o IGTF.</p>';
  if(d.restore_review_required)html+='<p class="notice warning">Después de restaurar, Administración debe revisar facturas excluidas y hojas disponibles. Los números usados conocidos siguen reservados.</p>';
  html+=card('Relación de ventas',field('Mes','invoice_month',d.period,'month','id="invoice-month"')+
    '<div class="actions">'+ib('CSV para Excel','sales-csv')+ib('PDF para contador','sales-pdf')+'</div>'+
    table(['Fecha','Factura / control','Cliente · representante','Total original','Estado / recibo',''],d.sales,r=>
      '<td>'+dateLabel(r.date)+'</td><td><b>'+esc(r.invoice)+'</b><span class="sub">'+esc(r.control)+'</span></td><td>'+esc(r.client)+'</td><td>'+invoiceAmount(r.total,r.currency)+'</td><td>'+esc(r.state_label)+'<span class="sub">'+esc(r.receipt)+'</span></td><td>'+(writable()?ib('Ver','detail',r.id,'small'):'')+'</td>','Sin facturas ni hojas contabilizadas en este mes')+
    '<div class="actions">'+(invoiceOffset?ib('Anterior','prev'):'')+(invoiceOffset+100<d.total_records?ib('Siguiente','next'):'')+'</div>');
  if(writable()){
    html+=card('Borradores',table(['Recibo','Fecha',''],d.drafts,r=>'<td>R-'+String(r.payment_id).padStart(6,'0')+'</td><td>'+dateLabel(r.issued_on)+'</td><td>'+ib('Revisar borrador','detail',r.id,'small')+'</td>','Sin borradores. Preparar uno no consume números.'));
    html+=card('Lotes preimpresos',table(['Lote','Factura','Control','Estado',''],d.batches,r=>
      '<td>'+esc(r.name)+'</td><td>'+esc(r.invoice_from)+' – '+esc(r.invoice_to)+'</td><td>'+esc(r.control_from)+' – '+esc(r.control_to)+'</td><td>'+badge(r.active?'Activo':'Inactivo')+'<span class="sub">'+esc(r.proposal.warning)+'</span></td><td>'+(admin()?ib('Editar','batch',r.id,'small'):'')+'</td>','Administración debe registrar el lote real.'),admin()?ib('Nuevo lote','batch'):'');
  }
  if(admin()){
    html+=card('Plantillas',table(['Plantilla','Versión','Calibración',''],d.templates,r=>
      '<td>'+esc(r.name)+'</td><td>'+r.revision+'</td><td>'+badge(r.calibrated?'Marcada como calibrada':'SIN CALIBRAR',r.calibrated?'':'red')+'</td><td>'+ib('Editar','template',r.current_version_id,'small')+'</td>','No hay plantillas guardadas. El ejemplo es editable.'),
      ib('Nuevo ejemplo','template')+ib('Importar JSON','import'));
    html+=card('Perfiles de impresora',table(['Impresora','Desplazamiento X / Y','Escala',''],d.profiles,r=>
      '<td>'+esc(r.name)+'</td><td>'+number(r.x_tenths/10)+' / '+number(r.y_tenths/10)+' mm</td><td>'+number(r.scale*100)+' %</td><td>'+ib('Editar','profile',r.id,'small')+'</td>','Sin perfiles guardados. El valor inicial es 100 % y margen 5 mm.'),ib('Nueva impresora','profile'));
  }
  return html;
}
function invoiceConfig(){
  const c=invoiceBook.config;
  let html='<p class="notice warning">'+esc(invoiceBook.warning)+'</p>'+
    icheck('Habilitar emisión sobre formularios preimpresos','enabled',c.enabled)+
    icheck('Revisé con mi contador el medio de emisión y los datos preimpresos','reviewed',c.reviewed)+
    field('Concepto predeterminado','concept_template',c.concept_template,'text','required maxlength="2000"','Variables: {mes}, {año}, {grado}. No uses el nombre del menor.')+
    '<p class="hint">Operaciones exentas. IVA e IGTF permanecen desactivados; Aula no calcula impuestos. Sus etiquetas y campos impresos se pueden editar.</p>'+
    field('Etiqueta IVA','iva_label',c.iva_label,'text','required maxlength="30"','Variable opcional {etiqueta_iva}.')+field('Etiqueta IGTF','igtf_label',c.igtf_label,'text','required maxlength="30"','Variable opcional {etiqueta_igtf}.');
  if(invoiceBook.restore_review_required)html+=icheck('Revisé facturas excluidas, anulaciones y hojas disponibles después de restaurar','restore_review_confirmed',false,'required');
  showModal('Configurar facturas','Administración. No es un sistema fiscal ni una conexión al SENIAT.',invoiceForm('invoice-config',html,'Guardar configuración'));
}
function invoiceBatch(id){
  const b=invoiceBook.batches.find(r=>r.id===Number(id))||{active:false,issuer:{}};
  let html=ihidden('id',id)+field('Nombre del lote','name',b.name||'','text','required maxlength="100"');
  html+='<div class="form-grid">'+field('Factura desde','invoice_from',b.invoice_from||'','text','required maxlength="40"')+field('Factura hasta','invoice_to',b.invoice_to||'','text','required maxlength="40"')+
    field('Control desde','control_from',b.control_from||'','text','required maxlength="40"')+field('Control hasta','control_to',b.control_to||'','text','required maxlength="40"')+'</div>';
  const labels={name:'Emisor preimpreso',rif:'RIF del emisor',address:'Domicilio preimpreso',printer_name:'Imprenta autorizada',printer_rif:'RIF de la imprenta',authorization:'Autorización o identificación preimpresa',printed_on:'Fecha preimpresa',notes:'Observaciones del lote'};
  html+='<h3>Datos que ya aparecen en el papel</h3><div class="form-grid">';
  Object.entries(labels).forEach(([key,label])=>{html+=field(label,'issuer_'+key,b.issuer[key]||'','text',['name','rif','printer_name'].includes(key)?'required':'');});
  html+='</div>'+icheck('Usar como único lote activo','active',Boolean(b.active));
  showModal('Lote de imprenta','Copia los rangos del lote real. Aula no crea números de factura ni de control.',invoiceForm('invoice-batch',html,'Guardar lote'));
}
function invoiceProfile(id){
  const p=invoiceBook.profiles.find(r=>r.id===Number(id))||{name:'',x_tenths:0,y_tenths:0,scale:1,margin_mm:5};
  const html=ihidden('id',id)+field('Nombre de la impresora','name',p.name,'text','required maxlength="100"')+
    '<div class="form-grid">'+field('Mover X · mm','x_mm',p.x_tenths/10,'number','required min="-50" max="50" step="0.1"')+
    field('Mover Y · mm (positivo baja)','y_mm',p.y_tenths/10,'number','required min="-50" max="50" step="0.1"')+
    field('Escala fina · %','scale_percent',p.scale*100,'number','required min="95" max="105" step="0.1"')+
    field('Margen no imprimible · mm','margin_mm',p.margin_mm,'number','required min="0" max="30" step="0.1"')+'</div>';
  showModal('Perfil de impresora','Calibra con fotocopias. PDF a tamaño real; al imprimir elige Tamaño real / 100 %, sin ajustar a la página.',invoiceForm('invoice-profile',html,'Guardar perfil'));
}
function invoiceSelect(){
  showModal('Factura desde un cobro','Usa el número R- del comprobante. No se registra otro pago.',
    invoiceForm('invoice-select-receipt',field('Número de recibo · sin R-','payment_id','','number','required min="1" step="1"'),'Revisar cobro'));
}
function invoiceLine(item,index){
  return '<tr data-invoice-item><td>'+field('Concepto '+(index+1),'concept_'+index,item.concept,'text','required maxlength="1000" data-invoice-concept')+'</td><td>'+
    field('Cantidad '+(index+1),'quantity_'+index,item.quantity,'number','required min="1" max="9999" step="1" data-invoice-quantity')+'</td><td>'+
    field('Precio original '+(index+1),'price_'+index,item.unit_price,'number','required min="0" max="999999999" step="0.01" data-invoice-price')+'</td><td>'+ib('Quitar','remove-item',index,'small')+'</td></tr>';
}
async function invoiceDraftForm(paymentId,existing){
  await ensureInvoiceBook();
  if(!invoiceBook.batches.length||!invoiceBook.templates.length)throw new Error('Administración debe configurar lote y plantilla antes de preparar facturas.');
  const source=existing?existing.snapshot:await api('invoice-source?payment_id='+Number(paymentId));
  const items=existing?source.items.map(r=>({concept:r.concept,quantity:r.quantity,unit_price:(r.unit_cents/100).toFixed(2)})):source.items;
  const lot=existing?.batch_id||invoiceBook.batches.find(r=>r.active)?.id||invoiceBook.batches[0].id;
  let html=ihidden('id',existing?.id||'')+ihidden('payment_id',source.payment_id)+ihidden('confirmed_hash',existing?.draft_hash||'')+
    '<p><b>'+esc(source.receipt)+'</b> · '+invoiceAmount(source.original_amount,source.currency)+'. Los conceptos deben sumar este importe; el cobro no cambia.</p>'+
    '<div class="form-grid">'+field('Fecha de factura','issued_on',source.issued_on,'date','required max="'+state.today+'"')+
    select('Lote','batch_id',invoiceBook.batches.map(r=>[r.id,r.name+(r.active?' · activo':' · inactivo')]),lot)+
    select('Plantilla y versión actual','template_version_id',invoiceBook.templates.map(r=>[r.current_version_id,r.name+' · V'+r.revision+(r.calibrated?'':' · SIN CALIBRAR')]),existing?.template_version_id||invoiceBook.templates[0].current_version_id)+
    select('Perfil de impresora','profile_id',[['','Inicial · 100 % · margen 5 mm'],...invoiceBook.profiles.map(r=>[r.id,r.name])],source.profile_id||'')+
    field('Cliente · representante','client_name',source.client.name,'text','required maxlength="150"')+
    field('Cédula o RIF del representante','client_document',source.client.document,'text','required maxlength="150"')+'</div>'+
    textarea('Dirección fiscal del representante','client_address',source.client.address,500)+
    '<p class="hint">Estos datos se guardan solo en esta factura. No escribas nombre ni documento del menor en los conceptos.</p>'+
    '<div class="table-wrap"><table><thead><tr><th>Concepto</th><th>Cantidad</th><th>Precio original</th><th></th></tr></thead><tbody id="invoice-items">'+items.map(invoiceLine).join('')+'</tbody></table></div>'+
    ib('Añadir concepto','add-item')+textarea('Observaciones de la factura','observations',source.observations||'',1000);
  showModal(existing?'Editar borrador':'Preparar factura','Guardar el borrador no consume números ni crea otro cobro.',invoiceForm(existing?'invoice-edit-draft':'invoice-draft',html,'Guardar borrador'));
  modal.classList.add('wide-modal');
}
async function invoiceDetail(id){
  const d=await api('invoice-detail?id='+Number(id)),s=d.snapshot;
  let html='<p><b>Estado: '+esc(({draft:'Borrador',issued:'Emitida',void:'Anulada',damaged:'Hoja dañada o inutilizada'})[d.state])+'</b></p>';
  if(d.state==='damaged')html+='<p>Factura '+esc(d.invoice_number)+' · Control '+esc(d.control_number)+'</p><p>'+esc(s.reason)+'</p>';
  else html+='<dl><dt>Recibo</dt><dd>'+esc(s.receipt)+'</dd><dt>Cliente</dt><dd>'+esc(s.client.name)+'</dd><dt>Documento fiscal</dt><dd>'+esc(s.client.document)+'</dd><dt>Total original</dt><dd>'+invoiceAmount(s.original_amount,s.currency)+'</dd><dt>Factura / control</dt><dd>'+esc(d.invoice_number||'Sin consumir')+' / '+esc(d.control_number||'Sin consumir')+'</dd></dl>'+
    '<p>'+esc(s.items.map(r=>r.concept).join('; '))+'</p><p class="hint">Versión de plantilla '+d.template_version_id+'. La emisión conserva su PDF exacto.</p>';
  if(d.state==='draft')html+='<div class="actions">'+ib('Editar borrador','edit',id)+ib('PDF de prueba','preview',id)+ib('Emitir con hoja preimpresa','issue',id,'primary')+'</div>';
  if(d.state==='issued')html+='<div class="actions">'+ib(d.prints.length?'Reimprimir PDF':'PDF / Imprimir','print',id,'primary')+(admin()?ib('Anular factura','void',id):'')+'</div>';
  if(d.void_reason)html+='<p class="notice warning">'+esc(d.void_reason)+'</p>';
  if(d.prints.length)html+=table(['PDF entregado','Motivo'],d.prints,p=>'<td>'+esc(p.printed_at)+'</td><td>'+esc(p.reason)+'</td>');
  showModal('Factura y formulario','La factura no sustituye ni modifica el recibo de pago.',html);
}
async function invoiceIssueForm(id){
  await ensureInvoiceBook();const d=await api('invoice-detail?id='+Number(id)),lot=invoiceBook.batches.find(r=>r.id===d.batch_id);
  if(!lot?.active)throw new Error('Edita el borrador y selecciona el lote activo.');
  const html=ihidden('id',id)+ihidden('confirmed_hash',d.draft_hash)+
    '<p>'+esc(d.snapshot.receipt)+' · '+esc(d.snapshot.client.name)+' · '+invoiceAmount(d.snapshot.original_amount,d.snapshot.currency)+'</p>'+
    '<p class="notice warning">'+esc(lot.proposal.warning||'Comprueba los números impresos en la hoja real.')+'</p>'+
    '<div class="form-grid">'+field('Factura preimpresa','invoice_number',lot.proposal.invoice,'text','required maxlength="40"')+
    field('Control preimpreso','control_number',lot.proposal.control,'text','required maxlength="40"')+'</div>'+
    icheck('Confirmo que ambos números coinciden con la hoja preimpresa','numbers_confirmed',false,'required')+
    '<details><summary>Solo si hay un salto de números</summary>'+icheck('Revisé el salto de numeración','gap_confirmed')+textarea('Motivo del salto','gap_reason','',1000)+'</details>'+
    '<p class="hint">La factura emitida queda inmutable. Ningún número se genera ni reserva al abrir esta ventana.</p>';
  showModal('Confirmar emisión','Usa únicamente el formulario de imprenta autorizado y revisado con el contador.',invoiceForm('invoice-issue',html,'Emitir factura'));
}
function invoiceDamaged(){
  const lots=invoiceBook.batches.filter(r=>r.active);if(!lots.length)throw new Error('Configura primero un lote activo.');
  const p=lots[0].proposal;
  const html=select('Lote activo','batch_id',lots.map(r=>[r.id,r.name]),lots[0].id)+field('Fecha','issued_on',state.today,'date','required max="'+state.today+'"')+
    '<div class="form-grid">'+field('Factura preimpresa','invoice_number',p.invoice,'text','required maxlength="40"')+field('Control preimpreso','control_number',p.control,'text','required maxlength="40"')+'</div>'+
    icheck('Confirmo ambos números de la hoja dañada o inutilizada','numbers_confirmed',false,'required')+
    textarea('Motivo y soporte','reason','',1000)+(admin()?icheck('Estoy regularizando una hoja anterior a la última usada','prior_gap_confirmed'):'')+
    '<details><summary>Si esta hoja también deja un salto</summary>'+icheck('Revisé el salto','gap_confirmed')+textarea('Motivo del salto','gap_reason','',1000)+'</details>';
  showModal('Contabilizar hoja dañada','Los números quedan ocupados. No registra un pago ni una venta.',invoiceForm('invoice-damaged',html,'Guardar hoja y motivo'));
}
function invoiceImport(){
  showModal('Importar plantilla JSON','La plantilla importada queda SIN CALIBRAR; revisa medidas y fondo antes de emitir.',
    invoiceForm('invoice-import-template','<label class="field">Archivo JSON<input type="file" id="invoice-json-file" accept=".json,application/json"></label>'+textarea('JSON editable de plantilla','json','',800000),'Importar sin calibrar'));
}
function invoicePDF(result){
  $('#print-area').replaceChildren();
  const bytes=Uint8Array.from(atob(result.pdf_base64),c=>c.charCodeAt(0)),url=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));invoiceURLs.add(url);
  showModal('PDF listo para imprimir','Tamaño real del formulario. En la ventana de impresión elige Tamaño real / 100 %, sin ajustar a carta.',
    '<p>Archivo: '+esc(result.filename)+'</p><div class="actions"><a class="btn primary" href="'+url+'" target="_blank" rel="noopener">Abrir PDF / Imprimir</a><a class="btn" href="'+url+'" download="'+esc(result.filename)+'">Descargar PDF</a></div>'+
    '<p class="hint">La solicitud del PDF quedó en la bitácora. Una reimpresión usa el mismo PDF; no consume otro número. No uses otra hoja numerada como si fuera una factura nueva.</p>');
}
async function invoiceAction(action,id,button){
  if(action==='new'){if(id)await invoiceDraftForm(id);else invoiceSelect();return;}
  if(action==='detail'){await invoiceDetail(id);return;}
  if(action==='edit'){await invoiceDraftForm(null,await api('invoice-detail?id='+Number(id)));return;}
  if(action==='issue'){await invoiceIssueForm(id);return;}
  if(action==='preview'){invoicePDF(await api('invoice-preview',{id:Number(id)}));return;}
  if(action==='print'){
    const d=await api('invoice-detail?id='+Number(id));
    if(d.prints.length)showModal('Reimprimir factura','Se conserva el PDF original. No consume otro número ni debe usarse otra hoja numerada como nueva factura.',
      invoiceForm('invoice-print',ihidden('id',id)+textarea('Motivo de reimpresión','reason','',1000)+icheck('Confirmo la reimpresión','reprint_confirmed',false,'required'),'Entregar el mismo PDF'));
    else invoicePDF(await api('invoice-print',{id:Number(id)}));return;
  }
  if(action==='void'){showModal('Anular factura','Solo Administración. No se anula el cobro ni se liberan los números.',invoiceForm('invoice-void',ihidden('id',id)+textarea('Motivo de anulación','reason','',1000),'Anular con motivo'));return;}
  if(action==='sales-csv'||action==='sales-pdf'){await binaryBackup('invoice-sales.'+(action==='sales-csv'?'csv':'pdf')+'?month='+encodeURIComponent(invoiceMonth));return;}
  if(action==='next'||action==='prev'){invoiceOffset=Math.max(0,invoiceOffset+(action==='next'?100:-100));await refresh();return;}
  if(action==='add-item'){
    const body=$('#invoice-items'),index=body.children.length;body.insertAdjacentHTML('beforeend',invoiceLine({concept:'',quantity:1,unit_price:'0.00'},index));return;
  }
  if(action==='remove-item'){const rows=$$('#invoice-items tr');if(rows.length<=1)throw new Error('La factura necesita al menos un concepto.');button?.closest('tr')?.remove();return;}
  if(action==='config'){await ensureInvoiceBook();invoiceConfig();return;}
  if(action==='batch'){await ensureInvoiceBook();invoiceBatch(id);return;}
  if(action==='profile'){await ensureInvoiceBook();invoiceProfile(id);return;}
  if(action==='damaged'){await ensureInvoiceBook();invoiceDamaged();return;}
  if(action==='import'){invoiceImport();return;}
  if(action==='template'){await openInvoiceEditor(id);return;}
  if(action==='test-template'){await testInvoiceEditor();return;}
  if(action==='export-template'){await binaryBackup('invoice-template.json?version_id='+Number(id));return;}
  if(action==='restore-template'){const result=await api('invoice-template-restore',{version_id:Number(id)});await refresh();await openInvoiceEditor(result.version_id);return;}
  if(action==='add-field'||action==='remove-field'){invoiceEditorField(action);return;}
}
function $$(selector,root=document){return Array.from(root.querySelectorAll(selector));}
async function invoiceSubmit(form){
  const endpoint=form.dataset.endpoint,data=Object.fromEntries(new FormData(form)),submit=form.querySelector('[type="submit"]'),error=$('.error',form);
  submit.disabled=true;error.textContent='';
  try{
    if(endpoint==='invoice-select-receipt'){await invoiceDraftForm(data.payment_id);return;}
    let payload=data;
    if(endpoint==='invoice-config')payload={config:{enabled:form.elements.enabled.checked,reviewed:form.elements.reviewed.checked,concept_template:data.concept_template,iva_enabled:false,igtf_enabled:false,iva_label:data.iva_label,igtf_label:data.igtf_label},restore_review_confirmed:Boolean(form.elements.restore_review_confirmed?.checked)};
    if(endpoint==='invoice-batch'){
      payload={...data,active:form.elements.active.checked,issuer:{}};['name','rif','address','printer_name','printer_rif','authorization','printed_on','notes'].forEach(key=>payload.issuer[key]=data['issuer_'+key]);
    }
    if(endpoint==='invoice-profile')payload={id:data.id,profile:{name:data.name,x_tenths:Math.round(Number(data.x_mm)*10),y_tenths:Math.round(Number(data.y_mm)*10),scale:Number(data.scale_percent)/100,margin_mm:Number(data.margin_mm)}};
    if(endpoint==='invoice-template')payload={id:data.id,layout:JSON.parse(data.layout_json)};
    if(endpoint==='invoice-draft'||endpoint==='invoice-edit-draft')payload={id:data.id,payment_id:data.payment_id,issued_on:data.issued_on,batch_id:data.batch_id,template_version_id:data.template_version_id,profile_id:data.profile_id,
      confirmed_hash:data.confirmed_hash,client:{name:data.client_name,document:data.client_document,address:data.client_address},observations:data.observations,
      items:$$('[data-invoice-item]',form).map(row=>({concept:$('[data-invoice-concept]',row).value,quantity:Number($('[data-invoice-quantity]',row).value),unit_price:$('[data-invoice-price]',row).value}))};
    for(const key of ['numbers_confirmed','gap_confirmed','prior_gap_confirmed','reprint_confirmed'])if(form.elements[key])payload[key]=form.elements[key].checked;
    const result=await api(endpoint,payload);
    if(result.pdf_base64){invoicePDF(result);return;}
    await refresh();modal.close();
    if(['invoice-draft','invoice-edit-draft','invoice-issue'].includes(endpoint)){await invoiceDetail(result.id);toast(endpoint==='invoice-issue'?'Factura emitida; números conservados.':'Borrador guardado; sin consumir números.');}
    else if(['invoice-template','invoice-import-template'].includes(endpoint)){await openInvoiceEditor(result.version_id);toast(endpoint==='invoice-import-template'?'Importada SIN CALIBRAR.':'Nueva versión guardada.');}
    else toast('Guardado en la bitácora.');
  }catch(e){error.textContent=e.message;}finally{submit.disabled=false;}
}
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-inv-action]');if(!button)return;
  invoiceAction(button.dataset.invAction,button.dataset.id,button).catch(e=>toast(e.message,true));
});

function readInvoiceEditor(form){return JSON.parse(form.elements.layout_json.value);}
function resumeInvoiceEditor(){
  const form=$('.invoice-editor-form',modal);if(!form)return;
  modal.classList.add('invoice-editor-modal');$('#invoice-test-download',form)?.remove();drawInvoiceEditor(form);invoiceEditorProperties(form);invoiceDetailProperties(form);
}
function writeInvoiceEditor(form,value){form.elements.layout_json.value=JSON.stringify(value);drawInvoiceEditor(form);}
function invoiceNeedsCalibration(form,value){value.calibrated=false;form.elements.template_calibrated.checked=false;}
function invoicePreset(name){
  const base={width_mm:139.7,height_mm:215.9,page_width_mm:139.7,page_height_mm:215.9,placement:'full',rotation:0,margin_mm:5};
  if(name==='media_horizontal')Object.assign(base,{width_mm:215.9,height_mm:139.7,page_width_mm:215.9,page_height_mm:139.7});
  if(name==='carta')Object.assign(base,{width_mm:215.9,height_mm:279.4,page_width_mm:215.9,page_height_mm:279.4});
  if(name==='carta_arriba'||name==='carta_abajo')Object.assign(base,{page_width_mm:215.9,page_height_mm:279.4,placement:name==='carta_arriba'?'top':'bottom',rotation:90});
  return base;
}
function invoiceEditorNumber(label,key,value,group,extra=''){
  return field(label,'editor_'+group+'_'+key,value,'number','data-inv-'+group+'="'+key+'" step="0.1" '+extra);
}
async function openInvoiceEditor(versionId){
  await ensureInvoiceBook();
  const v=versionId?await api('invoice-template?version_id='+Number(versionId)):null;
  const value=v?v.layout:await api('invoice-example'),p=value.paper;
  let controls=field('Nombre de plantilla','template_name',value.name,'text','required maxlength="100" data-inv-layout="name"')+
    icheck('Marcar como calibrada después de probar fotocopias','template_calibrated',value.calibrated,'data-inv-layout="calibrated"')+
    select('Tamaño y ubicación','paper_preset',[['custom','Personalizado / mantener'],['media_vertical','Media carta vertical · 396 × 612 pt'],['media_horizontal','Media carta horizontal'],['carta','Carta completa'],['carta_arriba','Carta · formulario arriba, girado 90°'],['carta_abajo','Carta · formulario abajo, girado 90°']],'custom','id="invoice-paper-preset"')+
    '<details><summary>Medidas de papel y margen · mm</summary><div class="form-grid">'+
    invoiceEditorNumber('Ancho formulario','width_mm',p.width_mm,'paper','min="50" max="1000"')+
    invoiceEditorNumber('Alto formulario','height_mm',p.height_mm,'paper','min="50" max="1000"')+
    invoiceEditorNumber('Ancho hoja','page_width_mm',p.page_width_mm,'paper','min="50" max="1000"')+
    invoiceEditorNumber('Alto hoja','page_height_mm',p.page_height_mm,'paper','min="50" max="1000"')+
    invoiceEditorNumber('Margen mínimo','margin_mm',p.margin_mm,'paper','min="0" max="30"')+
    select('Ubicación','paper_placement',[['full','Hoja completa'],['top','Mitad superior'],['bottom','Mitad inferior']],p.placement,'data-inv-paper="placement"')+
    select('Giro del formulario','paper_rotation',[[0,'Sin giro'],[90,'Girar 90°']],p.rotation,'data-inv-paper="rotation"')+'</div></details>'+
    '<div class="form-grid">'+invoiceEditorNumber('Cuadrícula · mm','grid_mm',value.grid_mm,'layout','min="0.1" max="20"')+
    icheck('Imán al arrastrar','template_snap',value.snap,'data-inv-layout="snap"')+'</div>'+
    '<label class="field">Fondo escaneado · PNG RGB/RGBA, máximo 500 KB<input type="file" id="invoice-scan-file" accept="image/png"></label>'+
    '<p class="hint">El fondo no se imprime al emitir. Carta arriba/abajo gira el formulario vertical, manteniendo tamaño real. Cambiar medidas no escala ni reubica tus campos.</p>'+
    '<div class="actions">'+ib('Añadir texto propio','add-field')+ib('Quitar campo seleccionado','remove-field')+'</div>';
  let html=ihidden('id',v?.id||'')+ihidden('editor_version_id',v?.version_id||'')+ihidden('layout_json',JSON.stringify(value))+ihidden('selected_field',value.fields[0]?.id||'')+
    '<input type="hidden" id="invoice-template-id" value="'+esc(v?.id||'')+'">'+
    '<p class="notice warning">'+esc(invoiceBook.warning)+' '+(value.calibrated?'La marca de calibración la declara Administración.':'SIN CALIBRAR · ejemplo genérico, no validado con tu formulario.')+'</p>'+
    '<div class="invoice-editor"><div class="invoice-editor-controls">'+controls+'</div><div class="invoice-editor-work"><div class="invoice-canvas-wrap"><svg id="invoice-editor-svg" aria-label="Editor de posiciones en milímetros"></svg></div>'+
    '<p class="hint">Selecciona un recuadro y arrástralo. Con foco en el recuadro: flechas = 0,1 mm; Mayús + flecha = 1 mm. Los rótulos identifican campos; revisa el texto exacto en el PDF de prueba.</p><div id="invoice-field-properties"></div></div></div>'+
    '<details><summary>Zona de líneas de detalle</summary><div id="invoice-detail-properties"></div></details>'+
    '<h3>Calibración antes de usar hojas numeradas</h3>'+select('Perfil para la prueba','test_profile_id',[['','Inicial · 100 %'],...invoiceBook.profiles.map(r=>[r.id,r.name])],'')+
    icheck('Incluir fondo únicamente en esta prueba','test_background')+
    '<div class="actions">'+ib('PDF de calibración / Prueba','test-template')+(v?ib('Exportar JSON','export-template',v.version_id):'')+'</div>';
  if(v)html+='<details><summary>Historial de versiones</summary>'+table(['Versión','Fecha',''],v.history,r=>'<td>'+r.revision+'</td><td>'+esc(r.saved_at)+'</td><td>'+ib('Restaurar como nueva versión','restore-template',r.id,'small')+'</td>')+'</details>';
  showModal('Editor de formulario preimpreso','X/Y y tamaños son recuadros en mm, desde arriba a la izquierda. El PDF respeta márgenes y detiene el texto que no cabe.',invoiceForm('invoice-template',html,'Guardar nueva versión','class="invoice-editor-form"'));
  modal.classList.add('invoice-editor-modal');drawInvoiceEditor($('.invoice-editor-form',modal));invoiceEditorProperties($('.invoice-editor-form',modal));invoiceDetailProperties($('.invoice-editor-form',modal));
}
function invoiceEditorProperties(form){
  const value=readInvoiceEditor(form),f=value.fields.find(r=>r.id===form.elements.selected_field.value),root=$('#invoice-field-properties',form);
  if(!f){root.innerHTML='<p>Selecciona un campo.</p>';return;}
  let html='<h3>Campo: '+esc(f.kind==='text'?'Texto propio':f.source)+'</h3><div class="form-grid">'+
    select('Contenido','field_kind',[['system','Dato del sistema'],['text','Texto fijo o con variables']],f.kind,'data-inv-prop="kind"')+
    select('Dato','field_source',invoiceVars.map(key=>[key,key]),f.source,'data-inv-prop="source"')+
    select('Fuente','field_font',[['sans','Helvetica'],['mono','Courier · monoespaciada']],f.font,'data-inv-prop="font"')+
    select('Alineación','field_align',[['left','Izquierda'],['center','Centro'],['right','Derecha']],f.align,'data-inv-prop="align"')+
    select('Si el texto es largo','field_overflow',[['wrap','Varias líneas'],['shrink','Reducir hasta mínimo 6 pt'],['error','Detener si no cabe']],f.overflow,'data-inv-prop="overflow"');
  for(const [key,label] of [['x_mm','X · mm'],['y_mm','Y · mm'],['width_mm','Ancho · mm'],['height_mm','Alto · mm'],['size_pt','Fuente · pt'],['leading','Interlineado'],['max_chars','Máximo de caracteres']]){
    html+=invoiceEditorNumber(label,key,f[key],'prop',key==='max_chars'?'min="1" max="3000"':'min="0" max="1000"');
  }
  html+='</div><div class="invoice-options">';
  for(const [key,label] of [['visible','Visible'],['bold','Negrita'],['italic','Cursiva'],['uppercase','Mayúsculas']])html+=icheck(label,'field_'+key,f[key],'data-inv-prop="'+key+'"');
  html+='</div><label class="field">Texto propio y variables<textarea data-inv-prop="text" name="field_text" maxlength="2000">'+esc(f.text)+'</textarea></label>'+
    '<p class="hint">Variables: '+invoiceVars.map(key=>'{'+key+'}').join(', ')+'. Las variables mal escritas impiden guardar.</p>';
  root.innerHTML=html;
}
function invoiceDetailProperties(form){
  const d=readInvoiceEditor(form).details;
  let html=icheck('Imprimir líneas de detalle','detail_visible',d.visible,'data-inv-detail="visible"')+'<div class="form-grid">'+
    invoiceEditorNumber('Y inicial · mm','y_mm',d.y_mm,'detail','min="0" max="1000"')+
    invoiceEditorNumber('Alto de línea · mm','line_height_mm',d.line_height_mm,'detail','min="2" max="100"')+
    invoiceEditorNumber('Máximo de líneas','max_lines',d.max_lines,'detail','min="1" max="100"')+
    invoiceEditorNumber('Fuente · pt','size_pt',d.size_pt,'detail','min="6" max="36"')+
    select('Fuente del detalle','detail_font',[['sans','Helvetica'],['mono','Courier']],d.font,'data-inv-detail="font"')+'</div>';
  d.columns.forEach((c,index)=>{
    html+='<div class="invoice-detail-column" data-inv-column="'+index+'">'+select('Columna','column_key_'+index,['concepto','cantidad','precio','exento','total'].map(key=>[key,key]),c.key,'data-inv-col-prop="key"')+
      field('X · mm','column_x_'+index,c.x_mm,'number','min="0" step="0.1" data-inv-col-prop="x_mm"')+
      field('Ancho · mm','column_width_'+index,c.width_mm,'number','min="0.1" step="0.1" data-inv-col-prop="width_mm"')+
      select('Alineación','column_align_'+index,[['left','Izquierda'],['center','Centro'],['right','Derecha']],c.align,'data-inv-col-prop="align"')+
      ib('Quitar columna','remove-column',index,'small')+'</div>';
  });
  html+=ib('Añadir columna','add-column');$('#invoice-detail-properties',form).innerHTML=html;
}
function svgNode(name,attrs,textValue){
  const node=document.createElementNS('http://www.w3.org/2000/svg',name);
  Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,String(value)));
  if(textValue!==undefined)node.textContent=textValue;return node;
}
function drawInvoiceEditor(form){
  const value=readInvoiceEditor(form),p=value.paper,svg=$('#invoice-editor-svg',form);
  if(!svg||!Number.isFinite(p.width_mm)||!Number.isFinite(p.height_mm)||p.width_mm<1||p.height_mm<1)return;
  svg.setAttribute('viewBox','-8 -8 '+(p.width_mm+8)+' '+(p.height_mm+8));svg.style.width=(p.width_mm+8)*3+'px';svg.style.height=(p.height_mm+8)*3+'px';svg.replaceChildren();
  const defs=svgNode('defs',{}),pattern=svgNode('pattern',{id:'invoice-grid',width:Math.max(.1,value.grid_mm),height:Math.max(.1,value.grid_mm),patternUnits:'userSpaceOnUse'});
  pattern.append(svgNode('path',{d:'M '+value.grid_mm+' 0 L 0 0 0 '+value.grid_mm,fill:'none',stroke:'#d9e2df','stroke-width':.08}));defs.append(pattern);svg.append(defs);
  svg.append(svgNode('rect',{x:0,y:0,width:p.width_mm,height:p.height_mm,fill:'white',stroke:'#71847e','stroke-width':.3}));
  if(value.background)svg.append(svgNode('image',{href:value.background,x:0,y:0,width:p.width_mm,height:p.height_mm,preserveAspectRatio:'none',opacity:.75}));
  svg.append(svgNode('rect',{x:0,y:0,width:p.width_mm,height:p.height_mm,fill:'url(#invoice-grid)'}));
  svg.append(svgNode('rect',{x:p.margin_mm,y:p.margin_mm,width:Math.max(0,p.width_mm-2*p.margin_mm),height:Math.max(0,p.height_mm-2*p.margin_mm),fill:'none',stroke:'#ba6c39','stroke-width':.25,'stroke-dasharray':'1 1'}));
  for(let x=0;x<=p.width_mm;x+=10){svg.append(svgNode('line',{x1:x,y1:-2,x2:x,y2:0,stroke:'#47625a','stroke-width':.2}));svg.append(svgNode('text',{x:x+.5,y:-3,'font-size':2.3,fill:'#36544a'},String(x)));}
  for(let y=0;y<=p.height_mm;y+=10){svg.append(svgNode('line',{x1:-2,y1:y,x2:0,y2:y,stroke:'#47625a','stroke-width':.2}));svg.append(svgNode('text',{x:-7,y:y+1,'font-size':2.3,fill:'#36544a'},String(y)));}
  if(value.details.visible){
    const d=value.details;for(const c of d.columns){
      svg.append(svgNode('rect',{x:c.x_mm,y:d.y_mm,width:c.width_mm,height:d.max_lines*d.line_height_mm,fill:'#d7e9e2','fill-opacity':.35,stroke:'#587d6e','stroke-width':.3}));
      svg.append(svgNode('text',{x:c.x_mm+1,y:d.y_mm+4,'font-size':2.6,fill:'#315547'},c.key));
      for(let line=1;line<d.max_lines;line++)svg.append(svgNode('line',{x1:c.x_mm,y1:d.y_mm+line*d.line_height_mm,x2:c.x_mm+c.width_mm,y2:d.y_mm+line*d.line_height_mm,stroke:'#86a696','stroke-width':.15}));
    }
  }
  for(const f of value.fields){
    const selected=f.id===form.elements.selected_field.value,g=svgNode('g',{'data-invoice-field':f.id,tabindex:0,role:'button','aria-label':'Mover campo '+f.source});
    g.append(svgNode('rect',{x:f.x_mm,y:f.y_mm,width:f.width_mm,height:f.height_mm,fill:selected?'#bfdbc8':'#e6eee9','fill-opacity':f.visible ? .65 : .2,stroke:selected?'#145d3b':'#7d9e8a','stroke-width':selected ? .6 : .25,'stroke-dasharray':f.visible?'none':'1 1'}));
    g.append(svgNode('text',{x:f.x_mm+1,y:f.y_mm+Math.min(4,f.height_mm-.5),'font-size':2.8,fill:'#174a33','pointer-events':'none'},f.kind==='text'?'Texto propio':f.source));
    svg.append(g);
  }
}
function invoiceEditorField(action){
  const form=$('.invoice-editor-form',modal),value=readInvoiceEditor(form);
  if(action==='add-field'){
    if(value.fields.length>=80)throw new Error('Máximo 80 campos.');
    let index=1;while(value.fields.some(f=>f.id==='propio_'+index))index++;
    const f={...value.fields[0],id:'propio_'+index,kind:'text',source:'concepto',text:'Texto {mes} {año}',visible:true,x_mm:10,y_mm:70,width_mm:60,height_mm:12};
    value.fields.push(f);form.elements.selected_field.value=f.id;
  }else{
    if(value.fields.length<=1)throw new Error('La plantilla necesita al menos un campo.');
    value.fields=value.fields.filter(f=>f.id!==form.elements.selected_field.value);form.elements.selected_field.value=value.fields[0].id;
  }
  invoiceNeedsCalibration(form,value);
  writeInvoiceEditor(form,value);invoiceEditorProperties(form);
}
async function testInvoiceEditor(){
  const form=$('.invoice-editor-form',modal),value=readInvoiceEditor(form),chosen=invoiceBook.profiles.find(p=>p.id===Number(form.elements.test_profile_id.value));
  const profile=chosen?{name:chosen.name,x_tenths:chosen.x_tenths,y_tenths:chosen.y_tenths,scale:chosen.scale,margin_mm:chosen.margin_mm}:{name:'Sin calibrar',x_tenths:0,y_tenths:0,scale:1,margin_mm:5};
  const result=await api('invoice-test',{layout:value,profile,include_background:form.elements.test_background.checked});
  // Keep the editor and unsaved changes open; the link contains only a test PDF.
  const url=URL.createObjectURL(new Blob([Uint8Array.from(atob(result.pdf_base64),c=>c.charCodeAt(0))],{type:'application/pdf'}));invoiceURLs.add(url);
  let link=$('#invoice-test-download',form);
  if(!link){link=document.createElement('a');link.id='invoice-test-download';link.className='btn primary';link.textContent='Descargar PDF de prueba · 100 %';link.target='_blank';link.rel='noopener';form.querySelector('.form-actions').before(link);}
  link.href=url;link.download=result.filename;toast('Prueba lista, sin consumir números. Imprime a tamaño real / 100 %.');
}
document.addEventListener('input',event=>{
  const target=event.target,form=target.closest('.invoice-editor-form');if(!form)return;
  const value=readInvoiceEditor(form),key=target.dataset.invProp,selected=value.fields.find(f=>f.id===form.elements.selected_field.value);
  const get=()=>target.type==='checkbox'?target.checked:target.type==='number'?Number(target.value):target.value;
  if(key&&selected)selected[key]=get();
  if(target.dataset.invLayout)value[target.dataset.invLayout]=get();
  if(target.dataset.invPaper)value.paper[target.dataset.invPaper]=target.dataset.invPaper==='rotation'?Number(target.value):get();
  if(target.dataset.invDetail)value.details[target.dataset.invDetail]=get();
  if(target.dataset.invColProp)value.details.columns[Number(target.closest('[data-inv-column]').dataset.invColumn)][target.dataset.invColProp]=get();
  if(key||target.dataset.invPaper||target.dataset.invDetail||target.dataset.invColProp)invoiceNeedsCalibration(form,value);
  writeInvoiceEditor(form,value);
});
document.addEventListener('change',async event=>{
  const target=event.target,form=target.closest('.invoice-editor-form');if(!form)return;
  try{
    if(target.id==='invoice-paper-preset'&&target.value!=='custom'){
      const value=readInvoiceEditor(form);value.paper=invoicePreset(target.value);invoiceNeedsCalibration(form,value);writeInvoiceEditor(form,value);
      $$('[data-inv-paper]',form).forEach(node=>{node.value=value.paper[node.dataset.invPaper];});
    }
    if(target.id==='invoice-scan-file'){
      const file=target.files[0],generation=sessionGeneration;
      if(!file||file.type!=='image/png'||file.size>500000)throw new Error('Usa PNG RGB/RGBA de hasta 500 KB.');
      const raw=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(new Error('No se leyó el fondo.'));r.readAsDataURL(file);});
      if(generation!==sessionGeneration)return;
      const value=readInvoiceEditor(form);value.background=raw;value.calibrated=false;writeInvoiceEditor(form,value);form.elements.template_calibrated.checked=false;
    }
  }catch(e){toast(e.message,true);}
});
let invoiceDrag=null;
document.addEventListener('pointerdown',event=>{
  const node=event.target.closest('[data-invoice-field]');if(!node)return;
  const form=node.closest('form'),value=readInvoiceEditor(form),f=value.fields.find(f=>f.id===node.dataset.invoiceField);
  form.elements.selected_field.value=f.id;invoiceEditorProperties(form);
  $$('[data-invoice-field]',form).forEach(item=>{const rect=item.querySelector('rect');rect.setAttribute('stroke',item.dataset.invoiceField===f.id?'#145d3b':'#7d9e8a');rect.setAttribute('stroke-width',item.dataset.invoiceField===f.id?'.6':'.25');});
  const svg=$('#invoice-editor-svg',form),scale=svg.getBoundingClientRect().width/(value.paper.width_mm+8);
  invoiceDrag={form,id:f.id,startX:event.clientX,startY:event.clientY,x:f.x_mm,y:f.y_mm,scale};
  $('[data-invoice-field="'+f.id+'"]',form)?.focus();event.preventDefault();
});
document.addEventListener('pointermove',event=>{
  if(!invoiceDrag)return;const drag=invoiceDrag,value=readInvoiceEditor(drag.form),f=value.fields.find(f=>f.id===drag.id);if(!f)return;
  const snap=n=>Math.round((value.snap?Math.round(n/value.grid_mm)*value.grid_mm:n)*10)/10;
  f.x_mm=snap(drag.x+(event.clientX-drag.startX)/drag.scale);f.y_mm=snap(drag.y+(event.clientY-drag.startY)/drag.scale);
  invoiceNeedsCalibration(drag.form,value);
  writeInvoiceEditor(drag.form,value);
  for(const key of ['x_mm','y_mm']){const input=$('[data-inv-prop="'+key+'"]',drag.form);if(input)input.value=f[key];}
});
document.addEventListener('pointerup',()=>{
  if(invoiceDrag)$('[data-invoice-field="'+invoiceDrag.id+'"]',invoiceDrag.form)?.focus();
  invoiceDrag=null;
});
document.addEventListener('keydown',event=>{
  const node=event.target.closest('[data-invoice-field]');if(!node||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;
  event.preventDefault();const form=node.closest('form'),value=readInvoiceEditor(form),f=value.fields.find(f=>f.id===node.dataset.invoiceField),step=event.shiftKey?1:.1;
  if(event.key==='ArrowLeft'||event.key==='ArrowRight')f.x_mm=Math.round((f.x_mm+(event.key==='ArrowLeft'?-step:step))*10)/10;
  else f.y_mm=Math.round((f.y_mm+(event.key==='ArrowUp'?-step:step))*10)/10;
  invoiceNeedsCalibration(form,value);
  writeInvoiceEditor(form,value);invoiceEditorProperties(form);$('[data-invoice-field="'+f.id+'"]',form)?.focus();
});
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-inv-action]');if(!button||!['add-column','remove-column'].includes(button.dataset.invAction))return;
  const form=button.closest('form'),value=readInvoiceEditor(form);
  if(button.dataset.invAction==='remove-column')value.details.columns.splice(Number(button.dataset.id),1);
  else{
    const key=['cantidad','precio','exento'].find(k=>!value.details.columns.some(c=>c.key===k));if(!key){toast('Ya están todas las columnas.',true);return;}
    value.details.columns.push({key,x_mm:10,width_mm:25,align:'left'});
  }
  invoiceNeedsCalibration(form,value);
  writeInvoiceEditor(form,value);invoiceDetailProperties(form);
});
document.addEventListener('submit',event=>{
  const form=event.target;if(!form.dataset.endpoint?.startsWith('invoice-'))return;
  event.preventDefault();invoiceSubmit(form);
});
document.addEventListener('change',async event=>{
  const target=event.target;
  try{
    if(target.id==='invoice-month'){invoiceMonth=target.value;invoiceOffset=0;await refresh();}
    if(target.id==='invoice-json-file'){
      const file=target.files[0],generation=sessionGeneration;if(!file||file.size>800000)throw new Error('Selecciona un JSON de hasta 800 KB.');
      const text=await file.text();if(generation!==sessionGeneration)return;$('textarea[name="json"]',target.form).value=text;
    }
  }catch(e){toast(e.message,true);}
});
