'use strict';
// Only RAM. Server totals and previews are authoritative; no connection to Cashea.
let casheaView;
function casheaReceiptBlock(v){return v?`<div class="receipt-balance"><b>Pago con Cashea · ${esc(v.code)}</b><p>Total ${usd(v.total_amount)} · Inicial ${usd(v.initial_amount)} · Financiado ${usd(v.financed_amount)}</p></div>`:'';}
function casheaCashBlock(v){return v?`<div class="notice"><div><b>Cashea</b><p>Financiado del día: ${usd(v.financed)} (no es caja). Liquidaciones recibidas: ${usd(v.received)}. La inicial está en su método real.</p></div></div>`:'';}
function casheaSettingsPanel(s){return card('Cashea',`<form class="card-body" data-endpoint="cashea-settings"><input type="hidden" name="request_key" value="${requestKey()}"><div class="form-grid">${select('Día de liquidación','cashea_settlement_day',['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'].map((v,i)=>[i,v]),s.cashea_settlement_day)}${select('Origen del número de factura','cashea_invoice_origin',[['recibo','Recibo'],['manual','Manual']],s.cashea_invoice_origin||'recibo')}${field('Comisión por defecto (%)','cashea_commission_percent',s.cashea_commission_percent,'number','required min="0" max="100" step="0.01"')}${field('Días de gracia para la alerta','cashea_grace_days',s.cashea_grace_days,'number','required min="0" max="365" step="1"')}</div><p class="hint">El recibo de Aula no es una factura fiscal; valida con Cashea y tu contador el uso de ese número. Los cambios se aplican a ventas nuevas. No cambian la comisión ni la fecha de las órdenes anteriores. Valida las comisiones con tu contador; no se crea un egreso automático.</p><div class="error" role="alert"></div><div class="form-actions"><button class="btn primary" type="submit">Guardar ajustes Cashea</button></div></form>`);}
function casheaPage(){
  const v=casheaView;if(!v)return heading('Cashea por liquidar','Carga las ventas desde el colegio.')+btn('Actualizar','cashea-refresh');
  const exports=kind=>['pdf','csv','xlsx'].map(ext=>`<a class="btn small" href="/api/cashea-report.${ext}?type=${kind}" download>${ext.toUpperCase()}</a>`).join('');
  return heading('Cashea por liquidar','La mensualidad queda cubierta; lo financiado es una cuenta por cobrar a Cashea.',writable()?btn('Registrar venta','cashea-sale','primary')+btn('Registrar liquidación','cashea-settle'):'')+
    `<div class="stats">${stat('Financiado por liquidar',usd(v.pending),'No es dinero recibido','payments','featured')}${stat('Órdenes vencidas',v.overdue_count,'Según fecha esperada y días de gracia','arrears')}</div>`+
    card('Semanas de liquidación',table(['Semana desde','Órdenes','Financiado','Neto esperado','Vencidas'],v.weeks,w=>`<td>${dateLabel(w.week)}</td><td>${w.count}</td><td>${usd(w.financed)}</td><td>${usd(w.expected)}</td><td>${w.overdue}</td>`,'No hay liquidaciones pendientes'),exports('pending'))+
    card('Órdenes Cashea',table(['Orden / alumno','Factura / venta','Esperada','Inicial','Financiado','Estado',''],v.orders,o=>`<td><b>${esc(o.code)}</b><span class="sub">${esc(o.student_name)}</span></td><td><b class="cashea-invoice-number">${esc(o.invoice_number)}</b> ${btn('Copiar','cashea-copy','small',o.invoice_number)}<span class="sub">${dateLabel(o.ordered_on)}</span></td><td>${dateLabel(o.expected_on)}${o.overdue?badge('Vencida','red'):''}</td><td>${usd(o.initial_amount)}</td><td>${usd(o.financed_amount)}</td><td>${esc(o.state.replaceAll('_',' '))}</td><td>${btn('Ver','cashea-order','',''+o.id)}</td>`,'Aún no hay ventas Cashea'),exports('sales'))+
    card('Liquidaciones recibidas',table(['Liquidación / fecha','Referencia','Recibido','Diferencia neto / bruto','Estado',''],v.settlements,s=>`<td>${esc(s.code)}<span class="sub">${dateLabel(s.received_on)}</span></td><td>${esc(s.reference)}</td><td>${nativeAmount(s.received_amount,s.currency)}</td><td>${usd(s.difference)} / ${usd(s.gross_difference)}</td><td>${s.voided?'Anulada':'Válida'}</td><td>${btn('Ver','cashea-settlement','',s.id)}</td>`,'Aún no se han recibido liquidaciones'),exports('settlements'))+`<p class="hint">${esc(v.note)}</p>`;
}
function casheaReviewForm(endpoint,body,label){return `<form data-endpoint="${endpoint}"><input type="hidden" name="request_key" value="${requestKey()}"><input type="hidden" name="preview_hash" value=""><div class="form-grid">${body}</div><section class="cashea-preview" aria-live="polite"></section>${formFoot(label)}</form>`;}
async function openCasheaOrder(id){
  const pupils=state.students.filter(s=>s.balance>0);if(!pupils.length){toast('No hay mensualidades pendientes.',true);return;}
  const sid=Number(id)||pupils[0].id;
  try{casheaView=await api('cashea');}catch(error){toast(error.message,true);return;}
  const manual=casheaView.settings.cashea_invoice_origin==='manual';
  showModal('Registrar venta Cashea','Solo mensualidades. La inicial se cobra por su método real.',casheaReviewForm('cashea-order',
    select('Alumno','student_id',pupils.map(s=>[s.id,s.name]),sid,'required')+field('Fecha de la venta','ordered_on',state.today,'date',`required max="${state.today}"`)+
    `<div class="field full" id="cashea-charges"></div>`+field('Total de mensualidades · USD','total','','number','required min="0.01" step="0.01"')+
    field('Inicial (%) · calculadora','initial_percent','60','number','required min="0" max="100" step="0.01"')+
    `<div class="field">${btn('Calcular inicial','cashea-calculate','small')}<small>No cambia el total ni confirma un cobro.</small></div>`+
    field('Inicial recibida (USD)','initial_received','','number','required min="0" step="0.01"')+select('Moneda de la inicial','initial_currency',[['USD','USD'],['VES','Bolívares']], 'USD')+`<div class="field full" id="cashea-initial-info" aria-live="polite"></div>`+
    select('Método real de la inicial','initial_method',paymentMethods.map(m=>[m,m]),'Efectivo')+field('Referencia de la inicial','initial_reference','','text','maxlength="200"')+
    `<details class="full"><summary>Revisar una referencia de inicial repetida</summary><label><input type="checkbox" name="duplicate_reference_confirmed"> Revisé el comprobante bancario repetido.</label>${field('Motivo de referencia repetida','duplicate_reason','','text','maxlength="500"')}</details>`+
    (manual?field('Número de factura','invoice_number','','text','required maxlength="100"'):`<div class="field full" id="cashea-invoice-preview" data-next-receipt="${esc(casheaView.next_receipt_number)}" data-next-order="${esc(casheaView.next_order_number)}" aria-live="polite"></div>`)+field('Referencia Cashea (opcional)','reference','','text','maxlength="200"')+
    field('Liquidación esperada (opcional)','expected_on','','date','', 'Vacío: siguiente día configurado, estrictamente posterior a la venta.')+
    (manual?`<details class="full"><summary>Revisar una factura duplicada</summary><label><input type="checkbox" name="invoice_duplicate_confirmed"> Revisé que esta factura ya está en otra orden.</label>${field('Motivo del duplicado','invoice_reason','','text','maxlength="500"')}</details>`:''),'Revisar venta'));
  casheaChargeChoices(sid);casheaUpdateInitial();
}
function casheaChargeChoices(sid){
  const box=$('#cashea-charges');if(!box)return;
  const charges=state.charges.filter(c=>c.student_id===Number(sid)&&c.balance>0).sort((a,b)=>a.due_date.localeCompare(b.due_date)||a.id-b.id);
  box.innerHTML='<label>Mensualidades · desde la más antigua</label>'+charges.map((c,i)=>`<label><input type="checkbox" data-cashea-charge="${i}" value="${c.id}" data-balance="${c.balance}" ${i===0?'checked':''}> ${esc(c.concept)} · ${esc(c.period)} · ${usd(c.balance)}</label>`).join('')+'<small>Selecciona un grupo consecutivo desde el cargo más antiguo; también puedes ajustar el total para un abono parcial.</small>';
  casheaChargeTotal();
}
function casheaChargeTotal(){const form=$('form[data-endpoint="cashea-order"]');if(!form)return;let total=0;for(const el of form.querySelectorAll('[data-cashea-charge]:checked'))total+=Number(el.dataset.balance);form.elements.total.value=(total/100).toFixed(2);}
// Integer cents and six-decimal rates; same HALF_UP convention as the server.
function casheaCents(value){
  if(!/^\d+(\.\d{1,2})?$/.test(value))throw new Error('Escribe un importe o porcentaje con hasta dos decimales.');
  const [a,b='']=value.split('.');return BigInt(a)*100n+BigInt(b.padEnd(2,'0'));
}
const casheaDecimal=cents=>`${cents/100n}.${String(cents%100n).padStart(2,'0')}`;
const casheaRound=(n,d)=>(n+d/2n)/d;
function casheaRate(form){
  const row=state.rates.find(r=>r.rate_date===form.elements.ordered_on.value);
  if(!row)return null;
  const [a,b='']=String(row.rate).split('.');return {text:row.rate,units:BigInt(a)*1000000n+BigInt(b.padEnd(6,'0'))};
}
function casheaResetReview(form){
  form.elements.preview_hash.value='';form.querySelector('[type="submit"]').textContent='Revisar venta';$('.cashea-preview',form).replaceChildren();
}
function casheaUpdateInitial(convertCurrency=false){
  const form=$('form[data-endpoint="cashea-order"]');if(!form)return;
  const input=form.elements.initial_received,currency=form.elements.initial_currency.value,rate=casheaRate(form),old=input.dataset.currency||'USD';
  if(convertCurrency&&old!==currency&&input.value!==''){
    try{
      const received=casheaCents(input.value),oldRate=BigInt(input.dataset.rate||'0');
      if((currency==='VES'&&!rate)||(old==='VES'&&!oldRate))input.value='';
      else{
        const usdCents=old==='VES'?casheaRound(received*1000000n,oldRate):received;
        input.value=casheaDecimal(currency==='VES'?casheaRound(usdCents*rate.units,1000000n):usdCents);
      }
    }catch{input.value='';}
  }
  input.dataset.currency=currency;input.dataset.rate=rate?String(rate.units):'';
  input.closest('label').firstChild.textContent=`Inicial recibida (${currency==='VES'?'Bs':'USD'})`;
  let info=currency==='VES'?(rate?`Tasa confirmada del día: Bs ${esc(rate.text)} por USD.`:'Confirma primero la tasa BCV de la fecha de la venta. Vuelve a calcular la inicial después de confirmarla.'):'Importe recibido en dólares.';
  try{
    if(input.value!==''){
      const received=casheaCents(input.value);
      if(currency==='USD'||rate){
        const equivalent=currency==='VES'?casheaRound(received*1000000n,rate.units):received;
        if(currency==='VES')info+=` Equivalente: ${usd(Number(equivalent))}.`;
        const calculated=casheaRound(casheaCents(form.elements.total.value)*casheaCents(form.elements.initial_percent.value),10000n);
        if((equivalent>calculated?equivalent-calculated:calculated-equivalent)*100n>calculated)info+='<p class="text-red" role="alert">La inicial recibida difiere más de 1 % del cálculo por porcentaje. Se registrará lo realmente recibido.</p>';
      }
    }
  }catch{/* Incomplete editable fields are validated before review. */}
  $('#cashea-initial-info',form).innerHTML=info;
  const invoice=$('#cashea-invoice-preview',form);
  if(invoice){
    const zero=input.value!==''&&Number(input.value)===0,number=zero?invoice.dataset.nextOrder:invoice.dataset.nextReceipt;
    invoice.textContent=`${zero?'N.º de orden':'Número de factura'}: se asignará ${number} al confirmar. El número previsto se confirma al guardar.`;
  }
}
function casheaCalculate(){
  const form=$('form[data-endpoint="cashea-order"]'),bps=casheaCents(form.elements.initial_percent.value);
  if(bps>10000n)throw new Error('El porcentaje no puede superar 100.');
  const initial=casheaRound(casheaCents(form.elements.total.value)*bps,10000n),ves=form.elements.initial_currency.value==='VES',rate=casheaRate(form);
  if(ves&&!rate){form.elements.initial_received.value='';casheaUpdateInitial();casheaResetReview(form);throw new Error('Confirma primero la tasa BCV de la fecha de la venta.');}
  form.elements.initial_received.value=casheaDecimal(ves?casheaRound(initial*rate.units,1000000n):initial);
  casheaUpdateInitial();casheaResetReview(form);
}
async function openCasheaSettlement(){
  const v=await api('cashea'),pending=v.orders.filter(o=>o.state==='por_liquidar');
  if(!pending.length){toast('No hay órdenes por liquidar.');return;}
  showModal('Registrar liquidación Cashea','Marca únicamente las ventas que cubre este depósito. No forma parte del efectivo físico.',casheaReviewForm('cashea-settlement',
    `<div class="full">${pending.map(o=>`<label class="confirm-check"><input type="checkbox" name="order_ids" value="${o.id}"> ${esc(o.code)} · ${esc(o.invoice_number)} · ${esc(o.student_name)} · neto ${usd(o.expected_amount)}</label>`).join('')}</div>`+
    field('Fecha de recepción','received_on',state.today,'date',`required max="${state.today}"`)+select('Moneda recibida','currency',[['USD','USD'],['VES','Bolívares']],'USD')+
    field('Importe realmente recibido','amount','','number','required min="0" step="0.01"')+field('Referencia bancaria','reference','','text','required maxlength="200"')+
    textarea('Motivo de la diferencia o comisión','reason','',500),'Revisar liquidación'));
}
async function submitCashea(form){
  const submit=form.querySelector('[type="submit"]'),errors=$('.error',form);submit.disabled=true;errors.textContent='';
  try{
    const endpoint=form.dataset.endpoint,data=Object.fromEntries(new FormData(form));
    if(endpoint==='cashea-order'){
      data.invoice_duplicate_confirmed=!!form.elements.invoice_duplicate_confirmed?.checked;
      data.duplicate_reference_confirmed=form.elements.duplicate_reference_confirmed.checked;
      data.charge_ids=Array.from(form.querySelectorAll('[data-cashea-charge]:checked'),el=>Number(el.value));
    }
    if(endpoint==='cashea-settlement')data.order_ids=Array.from(form.querySelectorAll('[name="order_ids"]:checked'),el=>Number(el.value));
    if(['cashea-order','cashea-settlement'].includes(endpoint)&&!data.preview_hash){
      const value=await api(endpoint==='cashea-order'?'cashea-preview':'cashea-settlement-preview',data);
      form.elements.preview_hash.value=value.preview_hash;
      $('.cashea-preview',form).innerHTML=endpoint==='cashea-order'?`<div class="notice"><div><b>Revisa antes de confirmar</b><p><b>${esc(value.invoice_label)}: ${esc(value.invoice_number)}</b> · previsto, se confirma al guardar.</p><p>Total ${usd(value.total_amount)} · Inicial ${usd(value.initial_amount)} · Financiado ${usd(value.financed_amount)}</p><p>Inicial original: ${nativeAmount(value.initial_received,value.initial_currency)} · Tasa ${esc(value.initial_rate)} · Equivalente ${usd(value.initial_amount)}</p>${value.initial_warning?`<p class="text-red" role="alert">${esc(value.initial_warning)}</p>`:''}<p>Neto esperado ${usd(value.expected_amount)} · Fecha ${dateLabel(value.expected_on)}</p><p>Saldo del alumno después: ${usd(value.student_balance_after)}</p></div></div>`:
        `<div class="notice"><div><b>Revisa el depósito</b><p>Bruto ${usd(value.gross_amount)} · Neto esperado ${usd(value.expected_amount)} · Recibido ${usd(value.amount)}</p><p>Diferencia neto ${usd(value.difference)} · Diferencia bruto ${usd(value.gross_difference)}</p><p>Las diferencias necesitan motivo, incluida una comisión.</p></div></div>`;
      submit.textContent='Confirmar registro';return;
    }
    const result=await api(endpoint,data);modal.close();await refresh(endpoint);toast('Registro Cashea guardado.');
    if(endpoint==='cashea-order')await showCasheaDocument('order',result.id);
    if(endpoint==='cashea-settlement')await showCasheaDocument('settlement',result.id);
  }catch(error){errors.textContent=error.message;}finally{submit.disabled=false;}
}
async function showCasheaDocument(kind,id){
  const route='cashea-'+kind+'/'+id,d=await api(route);
  let content=kind==='order'?`<h3>${esc(d.student.name)} · ${esc(d.student.grade_name)}</h3><div class="actions"><div><span>${esc(d.invoice_label)}</span><h2 class="cashea-invoice-number">${esc(d.invoice_number)}</h2></div>${btn('Copiar','cashea-copy','',d.invoice_number)}</div>${table(['Mensualidad','Período','Cubierto'],d.charges,c=>`<td>${esc(c.concept)}</td><td>${esc(c.period)}</td><td>${usd(c.amount)}</td>`)}${casheaReceiptBlock(d)}<p>Liquidación esperada: ${dateLabel(d.expected_on)}</p>${d.payment_id?btn('Recibo de inicial','receipt','',d.payment_id):'<p>Inicial cero: no se emitió recibo R-.</p>'}`:
    `<p>Referencia: ${esc(d.reference)} · Recibido: ${nativeAmount(d.received_amount,d.currency)}</p><p>Bruto ${usd(d.gross_amount)} · Neto esperado ${usd(d.expected_amount)} · Diferencias neto ${usd(d.difference)} / bruto ${usd(d.gross_difference)}</p><p>${esc(d.reason)}</p>${table(['Orden','Factura','Esperado'],d.orders,o=>`<td>${esc(o.code)}</td><td>${esc(o.invoice_number)}</td><td>${usd(o.expected_amount)}</td>`)}`;
  showDocument(d.code,route,`<article class="receipt school-document">${schoolHeader(d.school,'Cashea',d.code,d.ordered_on||d.received_on)}<p><b>${esc(d.state==='anulada'&&kind==='order'?'Anulada: anular también en el portal de Cashea':d.state.replaceAll('_',' '))}</b> ${esc(d.void_reason)}</p>${content}<p class="hint">${esc(d.note||'Valida comisiones con tu contador.')}</p></article>`);
  if(admin()&&!readOnlyInfo&&d.state!=='anulada'){
    const box=document.createElement('div');box.className='actions';box.innerHTML=(kind==='order'&&d.state==='por_liquidar'?btn('Editar fecha esperada','cashea-date','',id):'')+btn('Anular con motivo',kind==='order'?'cashea-void-order':'cashea-void-settlement','danger',id);$('.modal-body',modal).append(box);
  }
}
function openCasheaVoid(endpoint,id){showModal('Anular registro Cashea','Se conserva el historial y se revierte su efecto. Una orden liquidada exige anular primero su liquidación.',`<form data-endpoint="${endpoint}"><input type="hidden" name="id" value="${Number(id)}"><input type="hidden" name="request_key" value="${requestKey()}">${textarea('Motivo obligatorio','reason','','500')}${formFoot('Confirmar anulación')}</form>`);}
async function openCasheaDate(id){const d=await api('cashea-order/'+id);showModal('Editar fecha esperada','No cambia el comprobante original; el ajuste queda en la bitácora.',`<form data-endpoint="cashea-order-date"><input type="hidden" name="id" value="${Number(id)}"><input type="hidden" name="request_key" value="${requestKey()}">${field('Fecha esperada','expected_on',d.expected_on,'date','required')}${textarea('Motivo obligatorio','reason','',500)}${formFoot('Guardar fecha')}</form>`);}
document.addEventListener('change',event=>{
  const form=event.target.closest('form');if(!form)return;
  if(form.dataset.endpoint==='payments'&&event.target.name==='method'&&event.target.value==='Cashea'){openCasheaOrder(form.elements.student_id.value);return;}
  if(form.dataset.endpoint==='cashea-order'){
    if(event.target.name==='student_id')casheaChargeChoices(event.target.value);
    if(event.target.hasAttribute('data-cashea-charge'))casheaChargeTotal();
    casheaUpdateInitial(event.target.name==='initial_currency');casheaResetReview(form);
  }
});
document.addEventListener('input',event=>{
  const form=event.target.closest('form');if(!form?.dataset.endpoint?.startsWith('cashea-')||!form.elements.preview_hash)return;
  if(form.dataset.endpoint==='cashea-order')casheaUpdateInitial(event.target.name==='initial_currency');
  form.elements.preview_hash.value='';const button=form.querySelector('[type="submit"]');button.textContent=form.dataset.endpoint==='cashea-order'?'Revisar venta':'Revisar liquidación';$('.cashea-preview',form).replaceChildren();
});
