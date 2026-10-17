'use strict';
const $ = (s, root = document) => root.querySelector(s);
const app = $('#app'), modal = $('#modal');
let state, session, page = 'dashboard', filters = {}, reportFrom = '', reportTo = '';
let publicSchool = {}, setupToday, readOnlyInfo;
let receiptPaper = 'half-letter';
const paymentMethods=['Efectivo','Transferencia','Pago móvil','Tarjeta','Otro'];
let demoMode = false, demoToken = '', demoTimer;
let gateBackup, gateRole;
let settingsSection='identity', settingsDrafts={};
let archiveKind='student';
function requestKey() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(b => b.toString(16).padStart(2,'0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
const demoClient = requestKey();
let yearCohort, yearPreview, yearRequest;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = n => new Intl.NumberFormat('es-VE', {minimumFractionDigits:2, maximumFractionDigits:2}).format(n);
const usd = cents => `$ ${number(cents / 100)}`;
const bs = cents => `Bs ${number(cents / 100)}`;
const dateLabel = date => date ? new Date(date + 'T12:00:00').toLocaleDateString('es-VE', {day:'2-digit',month:'short',year:'numeric'}) : '—';
const monthLabel = month => new Date(month + '-01T12:00:00').toLocaleDateString('es-VE', {month:'long',year:'numeric'});
const shortMonths = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];
const schoolMonth = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value||'') ? `${shortMonths[Number(value.slice(5))-1]}. ${value.slice(0,4)}` : 'Pendiente';
const schoolBirth = value => value&&value>='1900-01-01' ? `${value.slice(8,10)} ${schoolMonth(value.slice(0,7))}` : 'Pendiente';
const roleLabel = role => ({admin:'Administrador',cashier:'Caja',reader:'Consulta'}[role] || role);
const admin = () => state?.user.role === 'admin';
const writable = () => state?.user.role !== 'reader';
const todayRate = () => state.rates.find(r => r.rate_date === state.today);
const icons = {
 dashboard:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
 students:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M16 3a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
 payments:'M2 6h20v12H2z M2 10h20 M6 14h3',
 billing:'M6 3h12v18l-3-2-3 2-3-2-3 2z M9 8h6 M9 12h6',
 arrears:'M12 8v4 M12 16h.01 M10.3 3.8 1.8 18.5A1.7 1.7 0 0 0 3.3 21h17.4a1.7 1.7 0 0 0 1.5-2.5L13.7 3.8a2 2 0 0 0-3.4 0',
 reports:'M4 20h16 M7 16V9 M12 16V4 M17 16v-5',
 guardians:'M3 21v-2a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v2 M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
 grades:'M3 10 12 4l9 6v10H3z M9 20v-7h6v7',
 expenses:'M4 8h16v12H4z M7 8V4h10v4 M8 12h8 M8 16h5',
 settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M9 3h6l1 3 3 1 2 5-2 4-3 1-1 4H9l-1-4-3-1-2-4 2-5 3-1z',
 plus:'M12 5v14 M5 12h14', arrow:'M5 12h14 M13 6l6 6-6 6', download:'M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4',
 logout:'M9 3H4v18h5 M10 12h11 M17 8l4 4-4 4', check:'M5 12l4 4L19 6', clock:'M12 8v4l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 search:'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0', print:'M6 9V3h12v6 M6 17H3V9h18v8h-3 M6 14h12v7H6z',
 shield:'M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7z M8 12l3 3 5-6', book:'M4 3h7c1 0 1 1 1 1s0-1 1-1h7v17h-7c-1 0-1 1-1 1s0-1-1-1H4z M12 4v17'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.book}"/></svg>`;
function schoolLogo(s = state?.settings || publicSchool) {
  const src = s?.logo === 'aula-app.png' ? '/aula-app.png' : /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(s?.logo || '') ? s.logo : '';
  return src ? `<img src="${esc(src)}" alt="Logo del colegio">` : `<span class="school-placeholder">${icon('book')}</span>`;
}
const btn = (label, action, style = '', id = '') => `<button type="button" class="btn ${style}" data-action="${action}" ${id !== '' ? `data-id="${esc(id)}"` : ''}>${label}</button>`;
const empty = (title, text = 'Los registros aparecerán aquí.', name = 'book') => `<div class="empty">${icon(name)}<b>${esc(title)}</b>${esc(text)}</div>`;
const badge = (label, kind = '') => `<span class="badge ${kind}">${esc(label)}</span>`;
const actionsCell = markup => `<div class="actions">${markup}</div>`;
const table = (headers, records, renderer, emptyTitle = 'Sin registros') => records.length ? `<div class="table-wrap"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${records.map(r => `<tr>${renderer(r)}</tr>`).join('')}</tbody></table></div>` : empty(emptyTitle);
const card = (title, body, action = '', subtitle = '') => `<section class="card"><div class="card-head"><div><h2>${title}</h2>${subtitle ? `<p>${subtitle}</p>` : ''}</div>${action}</div>${body}</section>`;
const stat = (label, value, note, name, style = '') => `<div class="stat ${style}"><div class="stat-label">${label}<span class="stat-icon">${icon(name)}</span></div><div class="stat-value">${value}</div><small>${note}</small></div>`;
const exportBtn = (type, label = 'Exportar Excel / CSV') => type==='students'?btn(`${icon('download')}${label}`,'export-students'):`<a class="btn" href="/api/export?type=${type}" download>${icon('download')}${label}</a>`;
const directoryReportBtn = type => btn(`${icon('print')} PDF / Imprimir`,'directory-report','',type);
const field = (label, name, value = '', type = 'text', extra = '', hint = '') => `<label class="field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}>${hint ? `<small>${esc(hint)}</small>` : ''}</label>`;
const select = (label, name, options, selected = '', extra = '') => `<label class="field">${esc(label)}<select name="${name}" ${extra}>${options.map(o => `<option value="${esc(o[0])}" ${String(o[0]) === String(selected) ? 'selected' : ''}>${esc(o[1])}</option>`).join('')}</select></label>`;
const textarea = (label, name, value = '', limit = 2000) => `<label class="field full">${esc(label)}<textarea name="${name}" aria-label="${esc(label)}" maxlength="${limit}">${esc(value)}</textarea></label>`;
const formFoot = label => `<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar', 'close')}<button class="btn primary" type="submit">${label}</button></div>`;
const statusOptions = [['active','Activo'],['inactive','Inactivo']];

async function api(path, data) {
  const generation=sessionGeneration, started=performance.now();
  const options = data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':session?.csrf || ''}, body:JSON.stringify(data)};
  let response;
  try { response = await fetch('/api/' + path, options); }
  catch { throw new Error('No hay conexión con el colegio. Comprueba que Aula siga abierta en esta PC.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('El servidor no respondió. Comprueba que la ventana de Aula esté abierta.'); }
  if(generation!==sessionGeneration)throw new Error('La sesión cambió. Comprueba el estado antes de continuar.');
  sessionHeaders(response,started);
  if (!response.ok) {
    if(response.status===409&&result.requires_rate_confirmation&&data&&!data.rate_change_confirmed){if(window.confirm(result.error+' ¿Seguro que deseas usar esta tasa?'))return api(path,{...data,rate_change_confirmed:true});throw new Error('La tasa no se guardó. Revisa el importe.');}
    if (response.status === 428) { if(result.requires_clock_confirmation)await openClockGate();else await openRateGate(); }
    if (response.status === 401 && path !== 'login') lockSession();
    throw new Error(result.error || 'No se pudo completar la operación.');
  }
  return result;
}
function toast(text, failure = false) {
  const el = $('#toast'); el.textContent = text; el.className = 'show' + (failure ? ' failure' : '');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => el.className = '', 5000);
}
async function boot() {
  try {
    const result = await api('session');
    readOnlyInfo=result.read_only;setupToday=result.today; session = result.user; publicSchool = result.school || {};
    if(readOnlyInfo){
      let banner=$('#readonly-banner');if(!banner){banner=document.createElement('div');banner.id='readonly-banner';document.body.prepend(banner);}
      banner.textContent=readOnlyInfo.message;document.body.classList.add('readonly-copy');
      if(!session){app.innerHTML='<div class="loading"><h2>La consulta terminó</h2><p>Abre la copia nuevamente desde Windows para continuar.</p></div>';return;}
      await sessionCheck();await refresh();return;
    }
    configureDemo(result);
    if (!session) { settingsSection='identity';settingsDrafts={};auth(result.needs_setup); return; }
    await sessionCheck();await openRateGate();
  } catch (error) { app.innerHTML = `<div class="loading"><h2>No se pudo abrir Aula</h2><p>${esc(error.message)}</p>${btn('Reintentar','boot')}</div>`; }
}
async function openRateGate() {
  if(readOnlyInfo){await refresh();return;}
  const clock=await api('clock-status');if(clock.blocked){await openClockGate(clock);return;}
  const gate = await api('rate-gate'); publicSchool = gate.school || publicSchool;
  gateBackup=gate.backup;gateRole=gate.role;
  if(gate.audit_status&&!gate.audit_status.ok){await refresh();return;}
  state=undefined; modal.close(); $('#print-area').replaceChildren();
  app.innerHTML=demoBanner()+`<div class="rate-screen"><section class="card gate-card"><div id="backup-alerts" class="backup-alerts">${backupProblem()}</div><div class="brand">${schoolLogo(publicSchool)}<div><small>${esc(publicSchool.institution_type||'Administración escolar')}</small><b>${esc(publicSchool.school_name||'Aula')}</b><small>Tasas y respaldo</small></div></div><div class="eyebrow">${dateLabel(gate.today)}</div><h1>Confirma la tasa de hoy</h1><p>Antes de comenzar, revisa la tasa oficial vigente. Se usará para convertir los cobros y egresos en bolívares.</p><form data-endpoint="confirm-rate"><input type="hidden" name="rate_date" value="${gate.today}">${field('Bolívares por 1 USD','rate',gate.rate,'number',`required min="0.000001" max="1000000" step="0.000001" ${gate.role==='reader'?'readonly':''}`)}<p class="hint">${gate.role==='reader'?'Consulta puede confirmar la tasa registrada. Si falta, administración o caja debe registrarla.':'Consulta bcv.org.ve y registra la tasa vigente, incluso en fines de semana y feriados. La actualización es manual.'}</p><div class="error" role="alert"></div><button class="btn primary" type="submit" ${gate.role==='reader'&&!gate.rate?'disabled':''}>Confirmar tasa y entrar</button></form><div class="gate-footer">${gate.role==='admin'&&!demoMode?btn('Descargar respaldo cifrado','download-encrypted-backup'):''}${btn('Cerrar sesión','logout')}</div></section></div>`;
  showRecoveryNotice();
}
function clockTime(value){return value?new Date(value).toLocaleString('es-VE',{timeZone:'America/Caracas',dateStyle:'long',timeStyle:'medium'}):'No disponible';}
async function openClockGate(given){
  const clock=given||await api('clock-status');
  if(!clock.blocked){await openRateGate();return;}
  const gate=await api('rate-gate');gateBackup=gate.backup;gateRole=gate.role;publicSchool=gate.school||publicSchool;
  bankDraft=null;bankView=null;accountingView=null;state=undefined;modal.close();$('#print-area').replaceChildren();
  const p=clock.pending||{},isAdmin=(clock.role||session?.role)==='admin';
  app.innerHTML=`<div class="rate-screen"><section class="card gate-card clock-gate"><div id="backup-alerts" class="backup-alerts">${backupProblem()}</div><div class="brand">${schoolLogo(publicSchool)}<div><b>${esc(publicSchool.school_name||'Aula')}</b><small>Revisión de fecha y hora</small></div></div><h1>Revisa el reloj de esta PC</h1><p>Por seguridad, están detenidos los cobros, la generación de mensualidades y la emisión de documentos.</p><dl><dt>Última fecha y hora registrada</dt><dd>${esc(clockTime(p.previous_time||clock.last_seen))}</dd><dt>Fecha y hora actuales de Windows</dt><dd>${esc(clockTime(clock.current_time))}</dd></dl><p class="notice warning">${p.reason==='backwards'?'El reloj retrocedió.':p.reason==='forward'?'El reloj avanzó más de lo esperado.':p.reason==='initial_review'?'Esta base tiene actividad anterior, pero falta el control del reloj. Revisa la fecha antes de comenzar.':'No se pudo comprobar o guardar el control del reloj.'}</p><p>Comprueba la fecha y hora de Windows y corrígelas si hace falta. Aula no las cambia automáticamente.</p>${isAdmin?`<form data-endpoint="clock-confirm"><input type="hidden" name="pending_id" value="${esc(p.id)}"><input type="hidden" name="observed_at" value="${esc(clock.current_time)}"><label class="confirm-check"><input name="reviewed" type="checkbox" required> Revisé Windows y confirmo que esta fecha y hora son correctas.</label><div class="error" role="alert"></div><button class="btn primary" type="submit">Confirmar fecha y hora</button></form>`:'<p class="text-red">Pide al administrador de Aula que revise y confirme el reloj. Caja y Consulta no pueden confirmar.</p>'}<div class="gate-footer">${btn('Volver a comprobar','clock-check')}${isAdmin&&!demoMode?btn('Descargar respaldo cifrado','download-encrypted-backup'):''}${btn('Cerrar sesión','logout')}</div><p class="hint">La confirmación deja constancia del administrador y la fecha en la bitácora.</p></section></div>`;
  showRecoveryNotice();
}
async function checkedPrint(report=false){
  const clock=await api('clock-status');if(clock.blocked){await openClockGate(clock);return;}
  if(report)printReport();else window.print();
}
function auth(setup) {
  clearInvoiceMemory();
  if(readOnlyInfo){app.innerHTML='<div class="loading"><h2>La consulta terminó</h2><p>Abre la copia nuevamente desde Windows para continuar.</p></div>';return;}
  if(demoMode){demoAuth();return;}
  state=undefined;modal.close();$('#print-area').replaceChildren();
  app.innerHTML = `<div class="auth-screen"><section class="auth-story"><div class="brand">${schoolLogo(publicSchool)}<div><small>${esc(publicSchool.institution_type||'Administración escolar')}</small><b>${esc(publicSchool.school_name||'Aula')}</b><small>Administración escolar</small></div></div><h1>Tu colegio,<br>con las cuentas<br><em>en orden.</em></h1><p>Alumnos, mensualidades y cobranza en un mismo lugar. Pensado para el día a día de tu colegio en Venezuela.</p><p>${icon('shield')} Datos locales · USD y bolívares</p></section><section class="auth-form"><div class="eyebrow">${setup ? 'Empecemos' : 'Bienvenido de nuevo'}</div><h2>${setup ? 'Configura tu administrador' : 'Entrar a tu colegio'}</h2><p>${setup ? 'Esta cuenta gestionará el colegio y podrá crear usuarios de caja y consulta.' : 'Ingresa tus datos para continuar con la administración.'}</p><form data-endpoint="${setup ? 'setup' : 'login'}">${setup ? field('Nombre del colegio','school_name','','text','required maxlength="200" autocomplete="organization"')+field('Año de inicio del ciclo escolar','school_year',Number(setupToday.slice(0,4))-(Number(setupToday.slice(5,7))<9),'number','required min="2000" max="2100"','Ejemplo: 2027 corresponde al ciclo 2027–2028.')+select('Mes de inicio del ciclo','start_month',Array.from({length:12},(_,i)=>[i+1,new Date(2020,i,1).toLocaleDateString('es-VE',{month:'long'})]),9)+field('Día de vencimiento mensual','due_day',10,'number','required min="1" max="31"','En meses cortos se utiliza el último día.')+field('Nombre del administrador','name','','text','required maxlength="200" autocomplete="name"') : ''}${field('Usuario','username','','text','required maxlength="80" autocomplete="username"')}${field('Contraseña','password','','password',`required ${setup ? 'minlength="10"' : ''} maxlength="256" autocomplete="${setup ? 'new-password' : 'current-password'}"`,setup ? 'Como mínimo 10 caracteres. Guárdala en un lugar seguro.' : '')}${setup?'':`<details><summary>Acceso bloqueado por intentos</summary><p class="hint">En esta PC abre Inicio → Aula → Desbloquear acceso local. Genera un código con tu contraseña actual y úsalo aquí antes de dos minutos.</p>${field('Código de acceso local','local_unlock_code','','password','maxlength="32" autocomplete="off"')}</details>`}<div class="error" role="alert"></div><button class="btn primary" type="submit">${setup ? 'Crear mi cuenta' : 'Iniciar sesión'} ${icon('arrow')}</button></form><p class="recovery-link">${btn('Olvidé mi usuario o contraseña','recovery-help','ghost')}</p><div class="auth-note">Los datos se guardan en esta PC y puedes trabajar sin internet. La tasa BCV se registra manualmente por fecha. Usa siempre la misma cuenta de Windows.</div></section></div>`;
}
async function refresh(savedEndpoint) { rememberSettingsDrafts(savedEndpoint);state = await api(['dashboard','invoices'].includes(page)?'state':'state?history=1');if(page==='income'){incomeMonth ||=state.today.slice(0,7);incomeView=await api('income-book?month='+encodeURIComponent(incomeMonth)+'&offset='+incomeOffset);bankView=await api('bank-book?month='+encodeURIComponent(incomeMonth)+'&offset='+incomeOffset+'&days='+bankDays);accountingView=await api('accounting-report?month='+encodeURIComponent(incomeMonth));}if(page==='invoices')await loadInvoicePage(); auditView=null; render(); }
const navItems = [['dashboard','Resumen','dashboard'],['students','Alumnos y matrículas','students'],['guardians','Representantes','guardians'],['grades','Grados y secciones','grades'],['billing','Mensualidades y cargos','billing'],['payments','Caja y cobros','payments'],['income','Control de ingresos','payments'],['invoices','Facturas preimpresas','billing'],['cash','Cierre de caja','payments'],['arrears','Morosidad','arrears'],['expenses','Egresos','expenses'],['archive','Archivo de la institución','students'],['reports','Reportes','reports'],['settings','Configuración','settings']];
function render() {
  if (!state) return;
  if (['settings','archive'].includes(page) && !admin()) page = 'dashboard';
  document.title = (demoMode?"PRUEBA · ":"") + state.settings.school_name + " · Administración escolar";
  const rate = todayRate(), current = navItems.find(n => n[0] === page);
  app.innerHTML = `<div class="layout"><header class="mobile-header">${schoolLogo()}<div><small>Administración escolar</small><b>${current[1]}</b></div><button type="button" class="btn mobile-menu-toggle" data-action="mobile-menu" aria-controls="school-navigation" aria-expanded="false"><span aria-hidden="true">☰</span> Menú</button></header><button class="menu-backdrop" type="button" data-action="mobile-menu-close" aria-label="Cerrar menú" tabindex="-1" hidden></button><aside class="sidebar" id="school-navigation" aria-label="Navegación del colegio"><button type="button" class="btn mobile-menu-close" data-action="mobile-menu-close" aria-label="Cerrar menú">Cerrar ×</button><div class="brand">${schoolLogo()}<div><b>${esc(state.settings.school_name)}</b><small>Administración escolar</small></div></div><nav>${navItems.filter(n => !['settings','archive'].includes(n[0]) || admin()).map(n => `${({dashboard:'Colegio',billing:'Finanzas',expenses:'Administración',reports:'Gestión'})[n[0]] ? `<div class="nav-label">${({dashboard:'Colegio',billing:'Finanzas',expenses:'Administración',reports:'Gestión'})[n[0]]}</div>` : ''}<button class="nav-button ${page === n[0] ? 'active' : ''}" data-action="nav" data-id="${n[0]}">${icon(n[2])}${n[1]}${n[0] === 'arrears' && state.summary.debtors ? `<span class="count">${state.summary.debtors}</span>` : ''}</button>`).join('')}</nav><div class="sidebar-footer"><div class="local-pill"><span class="dot"></span>${state.access?.mode==='private-network'?'Base compartida · PC principal':'Una computadora · Datos locales'}</div><div class="profile"><div class="avatar">${esc(state.user.name.slice(0,1).toUpperCase())}</div><div class="profile-text"><b>${esc(state.user.name)}</b><small>${roleLabel(state.user.role)}</small></div><button class="logout" data-action="logout" title="Cerrar sesión" aria-label="Cerrar sesión">${icon('logout')}</button></div></div></aside><main class="main"><header class="topbar"><div class="breadcrumb">${esc(state.settings.school_name)} <span> / </span> <b>${current[1]}</b></div><div class="top-info"><span class="backup-status ${backupStale()?'text-red':''}" title="${esc(state.backup?.local_path||'')}">${backupLabel()}</span><span>${dateLabel(state.today)}</span><button class="rate-chip" data-action="rates">${rate ? `BCV · Bs ${number(Number(rate.rate))} / USD` : 'BCV · Tasa de hoy pendiente'}</button></div></header>${demoBanner()}${auditWarning()}<div id="backup-alerts" class="backup-alerts">${backupProblem()}</div><div id="page-content">${pageBody()}</div><div class="welcome-line"><span>${esc(state.settings.school_name)} · Administración escolar</span><span>Año escolar ${esc(state.settings.school_year)}–${Number(state.settings.school_year)+1} · Base USD</span></div></main></div>`;
  showRecoveryNotice();
  window.AulaResponsive?.render();
  resumeSessionDraft().then(()=>resumeInvoiceEditor()).catch(error=>toast(error.message,true));
}
function heading(title, description, actions = '') { return `<div class="page-heading"><div><div class="eyebrow">${esc(state.settings.school_name)}</div><h1>${title}</h1><p>${description}</p></div><div class="actions">${actions}</div></div>`; }
function pageBody() {
  return ({dashboard,students:studentsPage,guardians:guardiansPage,grades:gradesPage,billing:billingPage,payments:paymentsPage,income:incomePage,invoices:invoicesPage,arrears:arrearsPage,expenses:expensesPage,cash:cashPage,reports:reportsPage,archive:archivePage,settings:settingsPage}[page])();
}
function dashboard() {
  const s = state.summary;
  const activity = dashboardActivity();
  const pending = state.students.filter(x => x.overdue > 0).sort((a,b) => b.overdue-a.overdue).slice(0,5);
  const recent = state.payments.filter(p => !p.voided).slice(0,5);
  const setup = !state.students.length && admin() ? `<div class="notice">${icon('book')}<div><b>Tu colegio empieza aquí</b>Configura tus datos, crea un grado y un representante; después matricula al primer alumno.<div class="steps"><button class="step" data-action="nav" data-id="settings">1. Datos del colegio</button><button class="step" data-action="grade">2. Grados</button><button class="step" data-action="guardian">3. Representantes</button><button class="step" data-action="student">4. Alumnos</button></div></div></div>` : '';
  return heading('Resumen de tu colegio', `Cobros y cuentas por atender · ${dateLabel(state.today)}`, writable() ? btn(`${icon('plus')} Registrar pago`,'payment','primary') : '') + setup + dashboardOverview(activity) +
    `<div class="grid-two"><div>${card('Cobros recientes',table(['Alumno / recibo','Recibido','Fecha'],recent,p=>`<td><button class="btn ghost" data-action="receipt" data-id="${p.id}">${esc(p.student_name)}</button><span class="sub">R-${String(p.id).padStart(6,'0')} · ${esc(p.method)}</span></td><td class="money">${p.currency === 'VES' ? bs(p.received_amount) : usd(p.amount)}<span class="sub">${p.currency === 'VES' ? usd(p.amount) + ' · equivalente' : 'Dólares'}</span></td><td>${dateLabel(p.paid_on)}</td>`,'Tu primer cobro aparecerá aquí'),btn('Ver caja →','nav','ghost','payments'))}${card('Pagos por atender',table(['Alumno / representante','Vencido',''],pending,x=>`<td><b>${esc(x.name)}</b><span class="sub">${esc(x.guardian_name)} · ${esc(x.grade_name)}</span></td><td class="money text-red">${usd(x.overdue)}</td><td>${btn('Ver cuenta','account','small',x.id)}</td>`,'No hay deuda vencida'),btn('Ver morosidad →','nav','ghost','arrears'))}</div><div>${dashboardUpcoming(activity.due)}${card('Antigüedad de la deuda',`<div class="card-body">${s.overdue ? `<p class="dashboard-aging-note">${todayRate() ? `Deuda vencida a la tasa de hoy: <b>${bs(Math.round(s.overdue * Number(todayRate().rate)))}</b>` : 'Registra la tasa de hoy para consultar el equivalente en Bs'}</p>${['1–30 días','31–60 días','61–90 días','Más de 90'].map((label,i)=>`<div class="aging-row"><span>${label}</span><div class="bar-track"><div class="bar" style="width:${s.overdue ? s.aging[i]/s.overdue*100 : 0}%"></div></div><b>${usd(s.aging[i])}</b></div>`).join('')}<div class="collection-note">Los abonos se aplican al cargo pendiente más antiguo. La deuda se mantiene en USD y los pagos conservan su tasa original.</div>` : `<div class="dashboard-clear">${icon('check')}<div><b>No hay deudas vencidas</b><p>Las cuentas están al día. Aquí verás los atrasos cuando existan.</p></div></div>`}</div>`,icon('clock'))}${card('Movimiento del mes',`<div class="card-body"><div class="list-line"><span>Ingresos por cobros</span><b class="text-green">${usd(s.income)}</b></div><div class="list-line"><span>Egresos registrados</span><b>${usd(s.expenses)}</b></div><div class="list-line"><span><b>Balance operativo</b><small>Ingresos menos egresos; equivalente USD</small></span><b>${usd(s.net)}</b></div></div>`,btn('Reportes →','nav','ghost','reports'))}</div></div>`;
}
function searchToolbar(placeholder, grade = false, extra = '') {
  return `<div class="toolbar"><input id="search" aria-label="Buscar" placeholder="${placeholder}" value="${esc(filters.search || '')}">${grade ? `<select id="grade-filter" aria-label="Filtrar por grado"><option value="">Todos los grados</option>${state.grades.map(g=>`<option value="${g.id}" ${String(g.id) === filters.grade ? 'selected' : ''}>${esc(g.name)}</option>`).join('')}</select>` : ''}${extra}<span class="table-count" id="table-count"></span></div>`;
}
function matches(s) { const q = (filters.search || '').toLocaleLowerCase(); return (!filters.grade || String(s.grade_id) === filters.grade) && [s.name,s.document,s.student_code,s.guardian_name,s.phone,s.position].some(v=>String(v||'').toLocaleLowerCase().includes(q)); }
function directoryFilter(){return `<label class="directory-filter"><input id="show-archived" type="checkbox" ${filters.archived?'checked':''}> Mostrar archivados</label>`;}
function directoryButtons(record,kind){
  if(!admin())return '';
  return btn('Editar',kind,'small',record.id);
}
function openDirectoryAction(endpoint,id){
  if(endpoint==='delete-grade'){
    const grade=state.grades.find(g=>g.id===Number(id));if(!grade)return;
    showModal('Eliminar grado / sección',esc(grade.name),`<form data-endpoint="delete-grade"><input type="hidden" name="id" value="${grade.id}"><p>Solo se elimina si no tiene alumnos vinculados, incluidas fichas inactivas o archivadas. Los documentos ya emitidos se conservan. Se creará un respaldo previo.</p>${textarea('Motivo obligatorio','reason')}${field('Escribe ELIMINAR','confirmation','','text','required pattern="ELIMINAR" autocomplete="off"')}<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn danger">Eliminar grado / sección</button></div></form>`);$('textarea',modal).required=true;return;
  }
  const isStudent=endpoint.endsWith('student'),record=(isStudent?state.students:state.guardians).find(r=>r.id===Number(id)),archiving=endpoint.startsWith('archive-'),word=archiving?'ARCHIVAR':'RECUPERAR';
  if(!record)return;
  const message=archiving?(isStudent?'La ficha se archivará y dejará de generar nuevas mensualidades. Los cargos, deudas, pagos y recibos existentes se conservan. Para corregir una deuda creada por error, usa Corregir mensualidades.':'La ficha se archivará. Si tiene alumnos sin archivar, primero deberás reasignarlos o archivar sus fichas. Los documentos existentes se conservan.'):(isStudent?'La ficha volverá al directorio como inactiva. Revisa sus datos y el primer mes a cobrar antes de activarla.':'La ficha volverá al directorio de representantes.');
  showModal(archiving?'Archivar ficha':'Recuperar ficha',esc(record.name),`<form data-endpoint="${endpoint}"><input type="hidden" name="id" value="${record.id}"><p>${message}</p>${textarea('Motivo obligatorio','reason')}${field('Escribe '+word,'confirmation','','text',`required pattern="${word}" autocomplete="off"`)}<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn ${archiving?'danger':'primary'}">${archiving?'Archivar ficha':'Recuperar ficha'}</button></div></form>`);
  $('textarea',modal).required=true;
}
function openBillingCorrection(id){
  const s=state.students.find(s=>s.id===Number(id));if(!s)return;
  const prior=s.billing_start||s.enrollment_start.slice(0,7),[year,month]=prior.split('-').map(Number),next=new Date(year,month,1,12),suggested=`${next.getFullYear()}-${String(next.getMonth()+1).padStart(2,'0')}`;
  const earlier=state.charges.some(c=>c.student_id===s.id&&c.concept==='Mensualidad'&&s.enrollment_start.slice(0,7)<=c.period&&c.period<prior);
  showModal('Corregir mensualidades',esc(s.name),`<form data-endpoint="correct-billing-start"><input type="hidden" name="id" value="${s.id}"><input type="hidden" name="previous_start" value="${esc(prior)}"><input type="hidden" name="charge_ids" value="[]"><p>Primer mes registrado: <b>${esc(schoolMonth(prior))}</b>. Elige el primer mes correcto y revisa las mensualidades anteriores que se anularán. No se borran pagos ni recibos.</p>${field('Primer mes correcto a cobrar','billing_start',earlier?prior:suggested,'month',`required min="${prior}" max="${s.enrollment_end.slice(0,7)}"`)}<div id="billing-correction-preview" aria-live="polite"></div>${textarea('Motivo obligatorio de la corrección','reason')}<label class="confirm-check"><input type="checkbox" name="confirmed" required> Revisé los meses y confirmo esta corrección.</label><div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn primary">Corregir y anular cargos indicados</button></div></form>`);
  $('textarea',modal).required=true;updateBillingCorrection();
}
function updateBillingCorrection(){
  const form=$('form[data-endpoint="correct-billing-start"]',modal);if(!form)return;
  const s=state.students.find(s=>s.id===Number(form.elements.id.value)),first=form.elements.billing_start.value;
  const list=state.charges.filter(c=>c.student_id===s.id&&c.concept==='Mensualidad'&&s.enrollment_start.slice(0,7)<=c.period&&c.period<first);
  const paid=list.some(c=>c.paid>0);form.elements.charge_ids.value=JSON.stringify(list.map(c=>c.id).sort((a,b)=>a-b));form.elements.confirmed.checked=false;
  $('#billing-correction-preview').innerHTML=list.length?`${table(['Mes a anular','Cargo USD','Abonado USD'],list,c=>`<td>${esc(schoolMonth(c.period))}</td><td>${usd(c.amount)}</td><td>${usd(c.paid)}</td>`)}<p><b>Total a anular: ${usd(list.reduce((total,c)=>total+c.amount,0))}</b></p>${paid?'<p class="text-red">Hay pagos aplicados. Esta corrección está bloqueada para conservarlos; revisa esos movimientos con administración.</p>':''}`:'<p>No hay mensualidades anteriores activas que anular. Solo se corregirá el primer mes a cobrar.</p>';
  form.querySelector('[type="submit"]').disabled=paid;
}
function archivePage(){
  const tableName={student:'students',guardian:'guardians'}[archiveKind];
  const inArchive=r=>Boolean(r.archived);
  const records=state[tableName].filter(r=>matches(r)&&(!filters.archiveState||(filters.archiveState==='archived')===inArchive(r)));
  const tabs=Object.entries({student:'Alumnos',guardian:'Representantes'}).map(([kind,label])=>`<button type="button" class="btn ${archiveKind===kind?'primary':''}" data-action="archive-kind" data-id="${kind}" aria-pressed="${archiveKind===kind}">${label}</button>`).join('');
  return heading('Archivo de la institución','Gestiona retiros y fichas creadas por error. Solo Administración puede hacer cambios.')+card('Fichas y su historial',`<div class="archive-controls"><div class="actions" aria-label="Tipo de ficha">${tabs}</div><p class="muted">Archivar conserva pagos y documentos. Un saldo de $0 no significa que la ficha esté vacía.</p></div>`+searchToolbar('Buscar ficha por nombre o documento…',false,`<label class="field">Estado<select id="archive-state"><option value="">Todas las fichas</option><option value="archived" ${filters.archiveState==='archived'?'selected':''}>En archivo</option><option value="directory" ${filters.archiveState==='directory'?'selected':''}>En directorio</option></select></label>`)+table(['Ficha','Estado','Referencia','Acción'],records,r=>`<td><b>${esc(r.name)}</b><span class="sub">${esc(r.student_code||r.document)}</span></td><td>${badge(inArchive(r)?'En archivo':'En directorio',inArchive(r)?'neutral':'')}</td><td>${archiveKind==='student'?esc(r.grade_name)+`<span class="sub">Saldo: ${usd(r.balance)}</span>`:archiveKind==='guardian'?state.students.filter(s=>s.guardian_id===r.id).length+' alumnos vinculados':esc(r.position)}</td><td>${btn('Revisar ficha','archive-review','small',r.id)}</td>`,'No hay fichas con este filtro'));
}
async function openArchiveReview(kind,id){
  const d=await api(`archive-preview/${kind}/${id}`);
  const detail=table(['Historial o vínculo','Cantidad'],Object.entries(d.counts).filter(([,n])=>n>0),r=>`<td>${esc(r[0])}</td><td>${r[1]}</td>`,'Sin movimientos ni documentos vinculados.');
  showModal('Revisar ficha',esc(d.name),`<p>Estado: <b>${d.archived?'En archivo':'En directorio'}</b>${d.balance!==null?` · Saldo pendiente: <b>${usd(d.balance)}</b>`:''}</p>${detail}<p class="hint">Archivar no borra deudas, recibos ni egresos. Una ficha con movimientos se conserva, aunque su saldo sea $0.</p>${d.blockers.length?`<p class="hint"><b>Borrado definitivo bloqueado:</b> ${d.blockers.map(esc).join(' · ')}.</p>`:'<p class="hint">Esta ficha admite borrado definitivo. La siguiente pantalla pedirá motivo y confirmación (y contraseña en el sistema real); primero se creará un respaldo verificado.</p>'}<div class="form-actions">${btn('Cerrar','close')}${btn(d.archived?'Recuperar ficha':'Archivar ficha',(d.archived?'restore-':'archive-')+kind,'primary',id)}${d.can_delete?btn('Borrar definitivamente','delete-unused-review','text-red',kind+':'+id):''}</div>`);
}
async function openUnusedDelete(kind,id){
  const d=await api(`archive-preview/${kind}/${id}`);
  if(!d.can_delete)throw new Error('La ficha tiene historial o vínculos. Vuelve a revisarla y usa Archivar.');
  showModal('Borrar ficha sin movimientos',esc(d.name),`<form data-endpoint="delete-unused-record"><input type="hidden" name="kind" value="${esc(kind)}"><input type="hidden" name="id" value="${d.id}"><input type="hidden" name="preview_hash" value="${esc(d.preview_hash)}"><p>Se borrará únicamente esta ficha${kind==='student'?` y sus ${d.counts['Constancias de matrícula']} constancias de matrícula sin movimientos financieros`:''}. No se puede deshacer desde el directorio. Se creará una copia local verificada y otra en el segundo destino, si está configurado; si falla una copia, no se borra.</p><p class="hint">Los archivos ya descargados y los respaldos anteriores conservan sus datos. Esto no elimina copias fuera de Aula ni otros registros de la bitácora.</p>${textarea('Motivo obligatorio','reason')}${demoMode?'<p class="hint">Modo Pruebas: no se pide contraseña porque estas fichas son temporales. El respaldo previo queda en la carpeta temporal y se elimina al cerrar las pruebas.</p>':field('Contraseña de tu Administrador','password','','password','required maxlength="256" autocomplete="current-password"')}${field('Escribe BORRAR FICHA','confirmation','','text','required pattern="BORRAR FICHA" autocomplete="off"')}<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn danger">Crear respaldo y borrar ficha</button></div></form>`);
  $('textarea',modal).required=true;
}
function studentsPage() {
  const records = state.students.filter(s=>matches(s)&&(!s.archived||filters.archived));
  return heading('Alumnos y matrículas','Expedientes, representantes, mensualidades y becas por alumno.',`${exportBtn('students')}${admin()?btn('Pase de año / grados','year-transition')+btn('Importar Excel / CSV','import-roster')+btn(`${icon('plus')} Matricular alumno`,'student','primary'):''}`) + card('Directorio de alumnos', searchToolbar('Buscar alumno, documento o representante…',true,directoryFilter()) + table(['Alumno','Grado / año','Mensualidad USD','Estado','Saldo USD','Acciones'],records,s=>`<td><b>${esc(s.name)}</b><span class="sub">${esc(s.student_code)} · ${esc(s.guardian_name)}</span></td><td>${esc(s.grade_name)}<span class="sub">${s.school_year}–${s.school_year+1}</span></td><td class="money">${usd(Math.floor((s.monthly_fee*(100-s.discount)+50)/100))}<span class="sub">${s.discount ? `Beca / descuento: ${s.discount}%` : 'Tarifa sin descuento'}</span><span class="sub">Cobrar desde: ${esc(schoolMonth(s.billing_start||s.enrollment_start.slice(0,7)))}</span></td><td>${badge(s.status==='active'?'Activo':'Inactivo',s.status==='active'?'':'neutral')}</td><td class="money ${s.overdue?'text-red':''}">${usd(s.balance)}</td><td class="row-actions">${actionsCell(btn('Cuenta','account','small',s.id)+btn('Constancia','enrollment','small',s.id)+directoryButtons(s,'student'))}</td>`,'Aún no hay alumnos matriculados'), `<div class="actions"><span class="muted">${records.length} alumnos</span>${directoryReportBtn('students')}</div>`);
}
function guardiansPage() {
  const records = state.guardians.filter(g=>matches(g)&&(!g.archived||filters.archived));
  return heading('Representantes','Personas responsables de los alumnos y sus datos de contacto.',admin()?btn(`${icon('plus')} Nuevo representante`,'guardian','primary'):'') + card('Directorio de representantes',searchToolbar('Buscar representante o documento…',false,directoryFilter())+table(['Representante','Contacto','Alumnos','Acciones'],records,g=>`<td><b>${esc(g.name)}</b><span class="sub">${esc(g.document)}</span></td><td>${esc(g.phone)||'—'}<span class="sub">${esc(g.email)}</span></td><td>${state.students.filter(s=>s.guardian_id===g.id).length}</td><td class="row-actions">${actionsCell(btn('Cuenta familiar','guardian-account','small',g.id)+directoryButtons(g,'guardian'))}</td>`,'Registra al primer representante'),directoryReportBtn('guardians'));
}
function gradesPage() {
  return heading('Grados y secciones','Organiza las matrículas y controla la capacidad de cada sección.',admin()?btn(`${icon('plus')} Nuevo grado / sección`,'grade','primary'):'') + card('Oferta escolar',table(['Grado / sección','Capacidad','Alumnos del año actual','Cupos disponibles','Acciones'],state.grades,g=>{const count=state.students.filter(s=>s.grade_id===g.id && s.status==='active' && s.school_year===Number(state.settings.school_year)).length;return `<td><b>${esc(g.name)}</b></td><td>${g.capacity}</td><td>${count}</td><td>${badge(Math.max(0,g.capacity-count)+' cupos',count>=g.capacity?'red':'')}</td><td class="row-actions">${actionsCell(admin()?btn('Editar','grade','small',g.id)+btn('Eliminar','delete-grade','small text-red',g.id):'')}</td>`;},'Crea los grados o secciones de tu colegio'));
}
function billingPage() {
  const records = state.charges.filter(c => (!filters.grade || state.students.find(s=>s.id===c.student_id)?.grade_id===Number(filters.grade)) && [c.student_name,c.concept,c.period].some(x=>x.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Mensualidades y cargos','Las mensualidades se calculan automáticamente; aquí puedes revisar sus saldos y registrar otros cargos.',writable()?btn('Nuevo cargo','charge')+btn('Preparar otro período','generate','primary'):'') + `<div class="notice">${icon('billing')}<div><b>Mensualidades en USD · vencimiento el día ${esc(state.settings.due_day)}</b>Se incluyen automáticamente los meses desde el primer mes a cobrar de cada alumno hasta el mes actual. El inicio del período académico no genera deudas de meses anteriores. Los meses vencidos sin pagar aparecen en Morosidad; los meses futuros se preparan solo si los necesitas.</div></div>` + card('Libro de cargos',searchToolbar('Buscar alumno, concepto o período…',true)+table(['Alumno','Concepto / período','Vencimiento','Cargo USD','Abonado USD','Saldo / estado',''],records,c=>`<td><b>${esc(c.student_name)}</b></td><td>${esc(c.concept)}<span class="sub">${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td class="money">${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}<span class="sub">${badge(c.balance===0?'Pagado':c.overdue?'Vencido':'Pendiente',c.overdue?'red':c.balance?'neutral':'')}</span></td><td>${actionsCell(btn('Cuenta','account','small',c.student_id)+(admin()&&!c.paid?btn('Anular','cancel-charge','small',c.id):''))}</td>`,'No hay cargos para las matrículas registradas.'));
}
function paymentsPage() {
  const records = state.payments.filter(p=>[p.student_name,p.reference,`R-${String(p.id).padStart(6,'0')}`].some(x=>x.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Caja y cobros','Recibe dólares o bolívares y emite comprobantes de pago.',exportBtn('payments')+(writable()?btn(`${icon('plus')} Registrar pago`,'payment','primary'):'')) + card('Historial de recibos',searchToolbar('Buscar alumno, recibo o referencia…')+table(['Recibo / alumno','Fecha','Recibido','Tasa BCV','Equivalente USD','Método','Cuenta','Estado',''],records,p=>`<td><b>R-${String(p.id).padStart(6,'0')}</b><span class="sub">${esc(p.student_name)}</span></td><td>${dateLabel(p.paid_on)}</td><td class="money">${p.currency==='VES'?bs(p.received_amount):usd(p.amount)}</td><td>${p.currency==='VES'?number(Number(p.exchange_rate)):'—'}</td><td class="money">${usd(p.amount)}</td><td>${esc(p.method)}<span class="sub">${esc(p.reference)}</span></td><td>${esc(state.school_accounts.find(a=>a.id===p.account_id)?.name||'Sin cuenta asignada')}</td><td>${badge(p.voided?'Anulado':'Válido',p.voided?'red':'')}</td><td>${actionsCell(btn('Recibo','receipt','small',p.id)+(writable()&&!p.voided?ib('Factura','new',p.id,'small'):'')+(admin()&&!p.voided?btn('Anular','void-payment','small',p.id):''))}</td>`,'Aún no hay pagos registrados'));
}
function arrearsPage() {
  const all = state.students.filter(s=>s.overdue>0), records = all.filter(matches);
  const sum = records.reduce((t,s)=>t+s.overdue,0);
  return heading('Morosidad y cobranza','Deuda vencida, antigüedad y seguimiento por alumno y representante.',exportBtn('arrears')) + `<div class="stats">${stat('Deuda vencida visible',usd(sum),'Total del filtro actual','arrears','alert')}${stat('Alumnos en mora',records.length,'Del filtro actual','students')}${stat('Equivalente en bolívares',todayRate()?bs(Math.round(sum*Number(todayRate().rate))):'—',todayRate()?'Referencia con tasa BCV de hoy':'Falta registrar la tasa BCV de hoy','payments')}${stat('Mayor atraso',Math.max(0,...state.charges.filter(c=>c.overdue && records.some(s=>s.id===c.student_id)).map(c=>c.days_overdue))+'<span>días</span>','Cargo vencido más antiguo del filtro','clock')}</div>`+card('Cuentas que requieren seguimiento',searchToolbar('Buscar alumno o representante…',true)+table(['Alumno / grado','Representante / contacto','Deuda vencida USD','Antigüedad','Acciones'],records,s=>{const days=Math.max(...state.charges.filter(c=>c.student_id===s.id&&c.overdue).map(c=>c.days_overdue));return `<td><b>${esc(s.name)}</b><span class="sub">${esc(s.grade_name)}</span></td><td>${esc(s.guardian_name)}<span class="sub">${esc(s.guardian_phone)||'Sin teléfono'}</span></td><td class="money text-red">${usd(s.overdue)}</td><td>${badge(days+' días',days>30?'red':'neutral')}</td><td class="row-actions">${actionsCell(btn('Cuenta','account','small',s.id)+btn('Aviso','collection','small',s.id)+(writable()?btn('Convenio','payment-plan','small',s.id)+btn('Registrar pago','payment','small primary',s.id):''))}</td>`;},'No hay deuda vencida con este filtro'));
}
function expensesPage() {
  const records=state.expenses.filter(e=>[e.concept,e.category,e.reference,''].some(v=>v.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Egresos','Registra gastos en USD o bolívares.',exportBtn('expenses')+(writable()?btn(`${icon('plus')} Registrar egreso`,'expense','primary'):''))+card('Libro de egresos',searchToolbar('Buscar concepto, categoría o referencia…')+table(['Concepto','Fecha','Categoría','Cuenta','Pagado','Equivalente USD','Estado',''],records,e=>`<td><b>${esc(e.concept)}</b><span class="sub">E-${String(e.id).padStart(6,'0')}</span><span class="sub">${esc(e.reference)}</span></td><td>${dateLabel(e.spent_on)}</td><td>${esc(e.category)}</td><td>${esc(state.school_accounts.find(a=>a.id===e.account_id)?.name||'Sin cuenta asignada')}</td><td class="money">${e.currency==='VES'?bs(e.received_amount):usd(e.amount)}<span class="sub">${e.currency==='VES'?'BCV: '+number(Number(e.exchange_rate)):'Dólares'}</span></td><td class="money">${usd(e.amount)}</td><td>${badge(e.voided?'Anulado':'Válido',e.voided?'red':'')}</td><td>${actionsCell((admin()&&!e.voided?btn('Anular','void-expense','small',e.id):''))}</td>`,'Aún no hay egresos registrados'));
}
function reportsPage() {
  reportFrom ||= state.today.slice(0,7)+'-01'; reportTo ||= state.today;
  const payments=state.payments.filter(p=>!p.voided&&p.paid_on>=reportFrom&&p.paid_on<=reportTo), expenses=state.expenses.filter(e=>!e.voided&&e.spent_on>=reportFrom&&e.spent_on<=reportTo);
  const other=(state.other_income||[]).filter(r=>!r.voided&&r.received_on>=reportFrom&&r.received_on<=reportTo),allIncome=payments.concat(other);
  const income=allIncome.reduce((a,p)=>a+p.amount,0), out=expenses.reduce((a,e)=>a+e.amount,0);
  return heading('Reportes administrativos','Consulta el flujo de caja y descarga los libros completos en CSV.',btn(`${icon('download')} Reporte diario PDF`,'daily-report','primary')+btn('Cierre de caja diario','nav','','cash')+btn(`${icon('print')} Imprimir resumen`,'print-report'))+`<div class="card"><div class="toolbar">${field('Desde','report-from',reportFrom,'date','id="report-from"')}${field('Hasta','report-to',reportTo,'date','id="report-to"')}<span class="table-count">${payments.length} cobros${other.length?' · '+other.length+' otros ingresos':''} · ${expenses.length} egresos válidos</span></div></div><div class="stats">${stat('Ingresos del período',usd(income),'Equivalente USD','payments','featured')}${stat('Egresos del período',usd(out),'Equivalente USD','expenses')}${stat('Balance del período',usd(income-out),'Ingresos menos egresos','reports')}${stat('Deuda vencida actual',usd(state.summary.overdue),'Corte de hoy, independiente del filtro','arrears','alert')}</div><div class="grid-two">${card('Cobros por método',`<div class="card-body">${paymentMethods.map(method=>`<div class="list-line"><span>${method}</span><b>${usd(allIncome.filter(p=>p.method===method).reduce((t,p)=>t+p.amount,0))}</b></div>`).join('')}<div class="list-line"><span>Recibido en dólares <small>Importe original, sin conversión</small></span><b>${usd(allIncome.filter(p=>p.currency==='USD').reduce((t,p)=>t+p.received_amount,0))}</b></div><div class="list-line"><span>Recibido en bolívares <small>Importe original, sin conversión</small></span><b>${bs(allIncome.filter(p=>p.currency==='VES').reduce((t,p)=>t+p.received_amount,0))}</b></div><p class="hint">El equivalente USD usa la tasa conservada en cada operación; sumar bolívares no cambia los saldos históricos.</p></div>`)}${card('Cierre mensual',`<div class="card-body">${field('Mes del cierre','closing_month',state.today.slice(0,7),'month',`id="closing-month" max="${state.today.slice(0,7)}"`)}<p class="hint">Monedas, métodos, egresos, saldos, pendiente por grado y anulaciones del mes. Sin datos personales de alumnos.</p>${btn('PDF mensual','monthly-pdf')}${btn('CSV mensual','monthly-csv')}</div>`)}${card('Exportación de libros',`<div class="card-body"><p class="muted">Descargas completas para abrir en Excel. Incluyen operaciones anuladas identificadas como tales.</p><div class="list-line"><span>Morosidad actual</span>${exportBtn('arrears','Descargar')}</div><div class="list-line"><span>Historial de pagos y tasas</span>${exportBtn('payments','Descargar')}</div><div class="list-line"><span>Alumnos y saldos</span>${exportBtn('students','Descargar')}</div><div class="list-line"><span>Egresos</span>${exportBtn('expenses','Descargar')}</div></div>`)}</div>`;
}
const settingsSections = [
  ['identity','Identidad y calendario','settings'],
  ['maintenance','Protección y mantenimiento','shield'],
  ['users','Usuarios y acceso','guardians'],
  ['audit','Bitácora','book']
];
function selectSettingsSection(id, focus=false){
  if(!settingsSections.some(section=>section[0]===id))return;
  settingsSection=id;
  for(const [key] of settingsSections){
    const tab=$('#settings-tab-'+key),panel=$('#settings-panel-'+key);
    if(tab){tab.setAttribute('aria-selected',String(key===id));tab.tabIndex=key===id?0:-1;}
    if(panel)panel.hidden=key!==id;
  }
  if(focus)$('#settings-tab-'+id)?.focus();
}
document.addEventListener('keydown',event=>{
  const tab=event.target.closest?.('.settings-sections [role="tab"]');
  if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  const index=settingsSections.findIndex(([id])=>id===tab.dataset.id);
  const next=event.key==='Home'?0:event.key==='End'?settingsSections.length-1:
    (index+(event.key==='ArrowRight'?1:-1)+settingsSections.length)%settingsSections.length;
  selectSettingsSection(settingsSections[next][0],true);
});
function rememberSettingsDrafts(savedEndpoint){
  if(page!=='settings'||!state?.settings)return;
  for(const form of document.querySelectorAll('form[data-endpoint="settings"],form[data-endpoint="backup-directory"],form[data-endpoint="session-preferences"]')){
    const endpoint=form.dataset.endpoint;
    if(endpoint===savedEndpoint){delete settingsDrafts[endpoint];continue;}
    const values={};
    for(const input of form.querySelectorAll('input[name],select[name],textarea[name]')){
      const stored=endpoint==='session-preferences'?(state.settings.session_idle_minutes||15):state.settings[input.name];
      if(input.value!==String(stored??''))values[input.name]=input.value;
    }
    settingsDrafts[endpoint]=values;
  }
}
function settingsPage(){
  const s=state.settings;
  const panels={identity:settingsIdentity({...s,...settingsDrafts.settings}),
    maintenance:settingsMaintenance({...s,...settingsDrafts['backup-directory']}),
    users:settingsUsers(),audit:settingsAudit()};
  return heading('Configuración','Elige un apartado para trabajar con orden.')+
    `<div class="settings-intro"><div>${schoolLogo()}<div><b>${esc(s.school_name)}</b><span>${esc(s.legal_name||'Completa la razón social de tu colegio')}</span></div></div><span class="badge">Una PC · Base USD</span></div>`+
    `<div class="settings-sections" role="tablist" aria-label="Apartados de configuración">${settingsSections.map(([id,label,name])=>`<button type="button" role="tab" id="settings-tab-${id}" aria-controls="settings-panel-${id}" aria-selected="${settingsSection===id}" tabindex="${settingsSection===id?0:-1}" data-action="settings-section" data-id="${id}">${icon(name)}<span>${label}</span></button>`).join('')}</div>`+
    settingsSections.map(([id])=>`<section class="settings-panel" id="settings-panel-${id}" role="tabpanel" aria-labelledby="settings-tab-${id}" ${settingsSection!==id?'hidden':''}>${panels[id]}</section>`).join('');
}
function settingsIdentity(s){
  return card('Identidad y calendario',`<form class="card-body" data-endpoint="settings"><h3>Datos que aparecerán en los documentos</h3><p class="hint">Cada documento conserva la identidad que tenía al emitirse.</p><div class="form-grid">${field('Nombre del colegio','school_name',s.school_name,'text','required maxlength="200"')}${field('Tipo de institución','institution_type',s.institution_type||'','text','maxlength="100"')}${field('Razón social / nombre legal','legal_name',s.legal_name,'text','maxlength="200"')}${field('RIF del colegio','rif',s.rif,'text','maxlength="100"')}${textarea('Domicilio fiscal','fiscal_address',s.fiscal_address,500)}${field('Dirección de contacto','address',s.address,'text','maxlength="500"')}${field('Teléfono','phone',s.phone,'tel','maxlength="100"')}${field('Correo','email',s.email,'email','maxlength="200"')}${field('Sitio web','website',s.website,'text','maxlength="200"')}<div class="field full logo-editor"><div id="logo-preview">${schoolLogo(s)}</div><label>Logo del colegio · PNG o JPG<input id="school-logo-file" type="file" accept="image/png,image/jpeg"><small>Se ajusta sobre fondo blanco y se guarda en la base y sus respaldos.</small></label><input type="hidden" name="logo" value="${esc(s.logo||'')}">${btn('Quitar logo','remove-logo','small')}</div></div><details class="settings-disclosure"><summary>Calendario y reglas de mensualidades</summary><div class="form-grid">${field('Año de inicio del ciclo escolar','school_year',s.school_year,'number','required min="2000" max="2100"','Indica el año en que comienza el ciclo escolar.')}${select('Mes de inicio del ciclo','start_month',Array.from({length:12},(_,i)=>[i+1,new Date(2020,i,1).toLocaleDateString('es-VE',{month:'long'})]),s.start_month)}${field('Día de vencimiento mensual','due_day',s.due_day,'number','required min="1" max="31"','En meses cortos se utiliza el último día.')}</div><p class="hint">Se cobra el mes completo, sin prorrateo por días. Los meses hasta hoy se generan automáticamente para matrículas activas. Las becas se aplican a cargos nuevos; los cargos existentes conservan su importe. El mes de inicio no se cambia con alumnos registrados. El cambio de año se hace en Alumnos → Pase de año / grados.</p></details><div class="error" role="alert"></div><div class="form-actions"><button class="btn primary" type="submit">Guardar cambios del colegio</button></div></form>`);
}
function settingsMaintenance(s){
  const destination=card('Segunda copia de seguridad · USB o carpeta de Drive',
    demoMode?'<div class="card-body"><p>Pruebas usa datos temporales y no configura respaldos reales.</p></div>':
    `<form class="card-body" data-endpoint="backup-directory"><p class="hint">Elige dónde guardar la segunda copia. Aquí solo se modifica el destino de los respaldos.</p>${field('Ruta completa de la carpeta de copias','backup_directory',s.backup_directory,'text','maxlength="500"','Ejemplo: E:\\Mi unidad\\Respaldos Aula. Nunca copies la base activa a esta carpeta.')}<p class="hint">Aula confirma la escritura, no la subida a la nube. Revisa Drive u otro servicio; una carpeta del mismo disco no protege frente a su falla.</p><div class="error" role="alert"></div><div class="form-actions"><button type="submit" class="btn primary">Guardar destino de respaldos</button></div></form>`);
  return destination+(demoMode?'':cryptoSettingsCard())+card('Protección y mantenimiento',`<div class="card-body"><p class="maintenance-status">${icon('shield')} ${backupLabel()}</p><p class="data-path">${esc(state.backup?.data_path||'')}</p><p class="hint">La base real está en esta PC. No la muevas ni la reemplaces mientras Aula esté abierta.</p><div id="protection-status">${protectionStatus()}</div><div class="maintenance-actions">${demoMode?'':btn('Crear respaldo ahora','backup-now','primary')+btn('Descargar copia cifrada','download-encrypted-backup')}${btn('Probar respaldo','probe-backup')}${btn('Verificar datos y cobros','maintenance-review')}${btn('Cómo actualizar o restaurar','maintenance-help')}</div><p class="hint">Respaldo después de cobros y cada cinco minutos. Conserva otra copia fuera de este disco. Una actualización del programa conserva la base.</p>${state.backup?.secondary_directory?`<p>${esc(externalEncryptionLabel(state.backup))}</p><p>Segundo destino: ${esc(state.backup.secondary_directory)}</p>`:demoMode?'':'<p class="text-red">Falta configurar una segunda carpeta de respaldos.</p>'}</div>`);
}
function settingsUsers(){
  return card('Cierre por inactividad',`<div class="card-body"><form data-endpoint="session-preferences">${field('Minutos sin actividad','idle_minutes',settingsDrafts['session-preferences']?.idle_minutes||state.settings.session_idle_minutes||15,'number','required min="5" max="60" step="1"','Entre 5 y 60 minutos. Aula avisa un minuto antes; las revisiones automáticas no cuentan como actividad.')}<div class="error" role="alert"></div><div class="form-actions"><button class="btn primary" type="submit">Guardar tiempo de cierre</button></div></form></div>`)+card('Usuarios y acceso',table(['Nombre / usuario','Perfil',''],state.users,u=>`<td><b>${esc(u.name)}</b><span class="sub">${esc(u.username)}</span></td><td>${roleLabel(u.role)}</td><td>${btn('Cambiar clave','password','small',u.id)}</td>`),btn('Crear usuario','user','small'));
}
let auditFilters={from:'',to:'',search:''},auditView=null;
function auditWarning(){return state.audit_status?.ok===false?`<div class="notice" role="alert"><div><b>Solo consulta: revisa la bitácora</b><p>${esc(state.audit_status.message)}</p><p>No se guardarán cambios ni se generarán mensualidades. Puedes consultar y respaldar los datos. Conserva la carpeta completa y solicita revisión técnica.</p></div></div>`:'';}
function settingsAudit(){
  const view=auditView,entries=view?.entries||state.audit,status=view?.status||state.audit_status;
  return card('Bitácora de operaciones',`<div class="card-body"><p class="${status?.ok?'hint':'text-red'}">${esc(status?.message||'No se pudo comprobar')}</p><p class="hint">No hay una función de vaciado global en producción. Las huellas detectan cambios; no impiden alteraciones de quien controle Windows. Después de restaurar, la historia posterior permanece en la copia previa indicada en el registro de restauración.</p><div class="filters">${field('Desde','audit_from',auditFilters.from,'date')}${field('Hasta','audit_to',auditFilters.to,'date')}${field('Buscar usuario, operación o detalle','audit_search',auditFilters.search,'search','maxlength="200"')}${btn('Buscar','audit-filter')}${btn('PDF','audit-pdf')}${btn('CSV','audit-csv')}</div><p class="hint">${view?`${entries.length} operaciones con estos filtros.`:'Últimas 300 operaciones. Buscar y exportar incluyen toda la bitácora.'}</p></div>`+table(['N.º','Fecha','Usuario','Operación','Detalle'],entries,a=>`<td>${a.id}</td><td>${esc(new Date(a.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}</td><td>${esc(a.operator)||'Sistema'}</td><td>${esc(a.operation||a.action)}</td><td class="audit-detail"><details><summary>Ver detalle</summary><pre>${esc(a.details)}</pre></details></td>`,'Sin operaciones'));

}

function showModal(title, subtitle, body) {
  if(modal.dataset.recoveryPrint){$('#print-area').replaceChildren();delete modal.dataset.recoveryPrint;}
  modal.classList.remove('document-modal','wide-modal','invoice-editor-modal');
  $('#modal-content').innerHTML=`<header class="modal-header"><div><h2>${title}</h2>${subtitle?`<p>${subtitle}</p>`:''}</div><button class="close" data-action="close" aria-label="Cerrar">×</button></header><div class="modal-body">${body}</div>`;
  if(!modal.open)modal.showModal();
}
function recordForm(endpoint, fields, record, label='Guardar') { return `<form data-endpoint="${endpoint}">${record?.id?`<input type="hidden" name="id" value="${record.id}">`:''}<div class="form-grid">${fields}</div>${formFoot(label)}</form>`; }
function openGuardian(id) {
  const r=state.guardians.find(g=>g.id===Number(id))||{};
  showModal(r.id?'Editar representante':'Nuevo representante','El mismo representante puede estar vinculado con varios alumnos.',recordForm('guardians',field('Nombre completo','name',r.name,'text','required maxlength="200"')+field('Cédula / documento','document',r.document,'text','required maxlength="200"')+field('Teléfono','phone',r.phone,'tel','maxlength="100"')+field('Correo electrónico','email',r.email,'email','maxlength="200"')+textarea('Dirección','address',r.address),r));
}
function openGrade(id) {
  const r=state.grades.find(g=>g.id===Number(id))||{};
  showModal(r.id?'Editar grado / sección':'Nuevo grado / sección','Ejemplo: 3.º de primaria · Sección A.',recordForm('grades',field('Nombre del grado / sección','name',r.name,'text','required maxlength="200"')+field('Capacidad de alumnos','capacity',r.capacity??30,'number','required min="1" max="500"'),r));
}
function openStudent(id) {
  if(!state.grades.length || !state.guardians.length) { showModal('Antes de matricular','Necesitas al menos un grado y un representante.',`<p>Registra estos datos para vincular correctamente el expediente del alumno.</p><div class="form-actions">${btn('Crear grado','grade','primary')}${btn('Crear representante','guardian')}</div>`);return; }
  const r=state.students.find(s=>s.id===Number(id))||{}, year=Number(r.school_year??state.settings.school_year), startMonth=Number(state.settings.start_month);
  const start=`${year}-${String(startMonth).padStart(2,'0')}-01`;
  // Avoid locale-dependent ISO formatting on Windows browser installations.
  const endDate=new Date(year+1,startMonth-1,0,12), endISO=`${endDate.getFullYear()}-${String(endDate.getMonth()+1).padStart(2,'0')}-${String(endDate.getDate()).padStart(2,'0')}`;
  showModal(r.id?'Editar matrícula':'Matricular alumno','Elige el primer mes a cobrar. El inicio académico puede ser septiembre sin generar deudas de meses anteriores.',recordForm('students',field('Nombre completo','name',r.name,'text','required maxlength="200"')+field('Código único del alumno','student_code',r.student_code||'Se asignará al guardar','text','readonly', 'Cada hermano recibe su propio código.')+field('Cédula del alumno (si tiene)','document',r.document===r.student_code?'':r.document,'text','maxlength="200"', 'Opcional. No uses la cédula del representante.')+field('Fecha de nacimiento (opcional)','birth_date',r.birth_date>='1900-01-01'?r.birth_date:'','date',`min="1900-01-01" max="${state.today}"`,'Si no la tienes, déjala vacía; la constancia dirá Pendiente.')+field('Buscar representante por nombre o cédula','guardian_search','','search','id="guardian-search" autocomplete="off"')+select('Representante','guardian_id',[['','Selecciona un representante'],...state.guardians.filter(g=>!g.archived||g.id===r.guardian_id).map(g=>[g.id,`${g.document} · ${g.name}`])],r.guardian_id||'','required')+select('Grado / sección','grade_id',state.grades.map(g=>[g.id,g.name]),r.grade_id,'required')+field('Año de inicio del año escolar','school_year',r.school_year??year,'number','required min="2000" max="2100"')+field('Mensualidad base · USD','monthly_fee',r.id?(r.monthly_fee/100).toFixed(2):'','number','required min="0" max="999999999" step="0.01"')+field('Beca / descuento · %','discount',r.discount??0,'number','required min="0" max="100"')+`<div class="conversion full" id="tuition-preview" role="status"></div>`+field('Primer mes a cobrar','billing_start',r.billing_start||(r.id?r.enrollment_start.slice(0,7):(state.today.slice(0,7)>start.slice(0,7)?state.today.slice(0,7):start.slice(0,7))),'month','required','No se generan mensualidades anteriores a este mes.')+`<div class="hint full" id="billing-start-preview" role="status"></div>`+field('Inicio del período académico','enrollment_start',r.enrollment_start||start,'date','','Referencia del ciclo escolar. No necesitas la fecha exacta de inscripción; vacío usa el inicio del ciclo.')+field('Fin del período / matrícula','enrollment_end',r.enrollment_end||endISO,'date','required')+select('Estado','status',statusOptions,r.status||'active')+(r.archived?'<input type="hidden" name="status" value="inactive">':'')+textarea('Observaciones','notes',r.notes),r,'Guardar matrícula'));
  if(r.id&&r.archived)$('form[data-endpoint="students"] [name="status"]').disabled=true;
  updateTuition();
}
function updateTuition() {
  const form=$('form[data-endpoint="students"]',modal);if(!form)return;
  const base=Math.round(Number(form.elements.monthly_fee.value||0)*100), discount=Number(form.elements.discount.value||0), fee=Math.floor((base*(100-discount)+50)/100);
  $('#tuition-preview').innerHTML=`Mensualidad base: ${usd(base)} · Descuento: ${esc(discount)} %<strong>Mensualidad final del alumno: ${usd(fee)}</strong>`;
  const first=form.elements.billing_start;first.min=form.elements.enrollment_start.value.slice(0,7);first.max=form.elements.enrollment_end.value.slice(0,7);
  let warning=$('#earlier-billing-warning',form);const existing=state.students.find(s=>s.id===Number(form.elements.id?.value));
  if(existing&&first.value<(existing.billing_start||existing.enrollment_start.slice(0,7))){if(!warning){warning=document.createElement('div');warning.id='earlier-billing-warning';warning.className='notice full';warning.innerHTML='<label class="confirm-check"><input type="checkbox" name="billing_change_confirmed" required> Elegí un mes anterior y confirmo que deben generarse mensualidades adicionales.</label>';$('#billing-start-preview').after(warning);}}else if(warning)warning.remove();
  $('#billing-start-preview').innerHTML=first.value?`Se cobrarán mensualidades desde <b>${esc(new Date(first.value+'-01T12:00:00').toLocaleDateString('es-VE',{month:'long',year:'numeric'}))}</b>. Los cargos, pagos y recibos ya registrados se conservan; cambiar este mes no borra deudas existentes.`:'Selecciona el primer mes a cobrar.';
}
function searchGuardian() {
  const form=$('form[data-endpoint="students"]',modal), select=form.elements.guardian_id, previous=select.value;
  const norm=v=>String(v).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(), query=norm($('#guardian-search').value).trim();
  const list=state.guardians.filter(g=>norm(g.name).includes(query)||norm(g.document).replace(/[^a-z0-9]/g,'').includes(query.replace(/[^a-z0-9]/g,'')));
  select.innerHTML=`<option value="">${list.length?'Selecciona un representante':'Sin coincidencias'}</option>`+list.map(g=>`<option value="${g.id}">${esc(g.document)} · ${esc(g.name)}</option>`).join('');
  if(list.some(g=>String(g.id)===previous))select.value=previous;
}
function openPayment(id) {
  const candidates=state.students.filter(s=>s.balance>0);
  if(!candidates.length) { showModal('Sin saldos pendientes','Las mensualidades hasta el mes actual ya están calculadas.',`<p>No hay deuda por cobrar en las matrículas registradas. Para un anticipo puedes preparar el mes futuro que corresponda, o crear un cargo de inscripción u otro concepto.</p><div class="form-actions">${btn('Crear cargo','charge','primary')}${btn('Preparar otro período','generate')}</div>`);return; }
  showModal('Registrar pago','El abono se aplica a los cargos pendientes más antiguos.',`<form data-endpoint="payments"><input type="hidden" name="request_key" value="${requestKey()}"><div class="form-grid">${select('Alumno','student_id',candidates.map(s=>[s.id,`${s.name} · ${usd(s.balance)}`]),id||candidates[0].id,'required')}${field('Fecha del pago','paid_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda recibida','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],'USD')}${field('Importe recibido','amount','','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',paymentMethods.map(m=>[m,m]),'Transferencia')}${select('Cuenta destino','account_id',accountOptions(true),'','required')}${field('Referencia bancaria / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div><div class="full" id="duplicate-reference"></div>${textarea('Observaciones','notes')}</div><div class="actions" style="margin-top:15px">${btn('Completar saldo','full-payment','small')}${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar y emitir recibo')}</form>`);
  updateConversion();
}
function updateConversion() {
  const form=$('form[data-endpoint="payments"]',modal)||$('form[data-endpoint="expenses"]',modal)||$('form[data-endpoint="income-other"]',modal);
  if(!form)return;
  const data=Object.fromEntries(new FormData(form)), rate=state.rates.find(r=>r.rate_date===(data.paid_on||data.spent_on||data.received_on)), amount=Number(data.amount||0), student=state.students.find(s=>s.id===Number(data.student_id));
  updateDestination(form,data);
  const panel=$('#conversion',form);
  if(form.dataset.endpoint==='payments')checkReference(form);
  if(data.currency==='VES'&&!rate) {panel.innerHTML=`<span class="text-red">Falta la tasa BCV del ${dateLabel(data.paid_on||data.spent_on)}. Regístrala antes de guardar.</span>`;return;}
  const equivalent=data.currency==='VES'?Math.round(amount/Number(rate.rate)*100):Math.round(amount*100);
  panel.innerHTML=`${data.currency==='VES'?`BCV registrada: Bs ${esc(rate.rate)} por USD`:'Pago directo en dólares'}<strong>Equivalente: ${usd(equivalent)}</strong>${student?`Saldo antes del pago: ${usd(student.balance)} · Después: ${usd(student.balance-equivalent)}`:'El egreso se incluirá en reportes por su equivalente USD.'}`;
}
function openExpense() {
  showModal('Registrar egreso','Conserva el importe original, su moneda y la tasa BCV de la fecha.',`<form data-endpoint="expenses"><div class="form-grid">${field('Concepto','concept','','text','required maxlength="200"')}${select('Categoría','category',['Operación','Servicios','Mantenimiento','Materiales','Otro'].map(x=>[x,x]),'Operación')}${field('Fecha del egreso','spent_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda pagada','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],'USD')}${field('Importe pagado','amount','','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',['Efectivo','Transferencia','Tarjeta','Otro'].map(m=>[m,m]),'Transferencia')}${select('Cuenta del egreso','account_id',accountOptions(),'')}${field('Referencia / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div></div><div class="actions" style="margin-top:15px">${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar egreso')}</form>`);updateConversion();
}

function openCharge(id) {
  if(!state.students.length) {toast('Matricula al menos un alumno primero.',true);return;}
  showModal('Nuevo cargo en USD','Para inscripción, matrícula, transporte, actividades u otros conceptos.',recordForm('charges',select('Alumno','student_id',state.students.map(s=>[s.id,s.name]),id||state.students[0].id,'required')+field('Concepto','concept','','text','required maxlength="200"', 'Usa un concepto distinto de Mensualidad para cargos adicionales.')+field('Período / referencia','period',state.today.slice(0,7),'text','required maxlength="40"')+field('Importe · USD','amount','','number','required min="0.01" step="0.01" max="999999999"')+field('Vencimiento','due_date',state.today,'date','required'),{},'Crear cargo'));
}
function openGenerate() {
  const [year,month]=state.today.split('-').map(Number), next=new Date(year,month,1,12), period=`${next.getFullYear()}-${String(next.getMonth()+1).padStart(2,'0')}`, schoolYear=next.getFullYear()-(next.getMonth()+1<Number(state.settings.start_month)?1:0);
  showModal('Preparar otro período','Opcional, para cobrar meses futuros por adelantado. Los meses hasta hoy se calculan solos.',recordForm('generate',field('Período mensual','period',period,'month','required')+field('Año de inicio del año escolar','school_year',schoolYear,'number','required min="2000" max="2100"'),{},'Preparar mensualidades'));
}
function openRates() {
  showModal('Tasas de cambio BCV','Registra la tasa oficial vigente para cada fecha. La carga es manual.',`${writable()?`<form data-endpoint="rates"><div class="form-grid">${field('Fecha de aplicación','rate_date',state.today,'date','required')}${field('Bolívares por 1 USD','rate',todayRate()?.rate||'','number','required min="0.000001" max="1000000" step="0.000001"')}</div><p class="hint">Consulta la tasa en bcv.org.ve. Si corriges una tasa, los pagos registrados conservan su valor original.</p>${formFoot('Guardar tasa')}</form>`:''}<div style="margin-top:24px">${table(['Fecha','Bs por USD','Origen'],state.rates.slice(0,40),r=>`<td>${dateLabel(r.rate_date)}</td><td class="money">${esc(r.rate)}</td><td>${esc(r.source)}</td>`,'No hay tasas registradas')}</div>`);
}
async function rateInline() {
  const form=$('form',modal), on=form.elements.paid_on?.value||form.elements.spent_on?.value;
  const box=$('#inline-rate',form);
  if(box){box.remove();return;}
  const el=document.createElement('div');el.id='inline-rate';el.className='conversion';el.innerHTML=`<label class="field">BCV para ${dateLabel(on)} · Bs por 1 USD<input id="inline-rate-value" type="number" min="0.000001" step="0.000001" placeholder="Tasa oficial BCV"></label><p class="hint">La fecha será la del pago o egreso que estás registrando.</p>${btn('Guardar tasa y continuar','save-inline-rate','small primary')}`;
  form.querySelector('.form-actions').before(el);$('#inline-rate-value').focus();
}
function account(id) {
  const s=state.students.find(s=>s.id===Number(id));if(!s)return;
  const list=state.charges.filter(c=>c.student_id===s.id), payments=state.payments.filter(p=>p.student_id===s.id);
  showModal(esc(s.name),`${esc(s.grade_name)} · ${esc(s.guardian_name)} · ${esc(s.guardian_phone)}`,`<div class="mini-summary"><div><small>Saldo pendiente USD</small><b>${usd(s.balance)}</b></div><div><small>Deuda vencida USD</small><b class="text-red">${usd(s.overdue)}</b></div></div><div class="actions">${writable()?btn('Registrar pago','payment','primary',s.id)+btn('Crear cargo','charge','',s.id):''}${admin()?btn('Editar matrícula','student','',s.id)+btn('Corregir mensualidades','correct-billing','',s.id):''}${btn('Preparar aviso','collection','',s.id)}${writable()&&s.overdue?btn('Convenio de pago','payment-plan','',s.id):''}${writable()?btn('Seguimiento','followup','',s.id):''}</div><h3 style="margin:22px 0 10px">Estado de cuenta</h3><div class="detail-table">${table(['Concepto / período','Vence','Cargo','Abono','Saldo',''],list,c=>`<td>${esc(c.concept)}<span class="sub">${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td>${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}</td><td>${admin()&&!c.paid?btn('Anular cargo','cancel-charge','small',c.id):''}</td>`,'No hay cargos activos')}</div><h3 style="margin:22px 0 10px">Pagos</h3><div class="detail-table">${planLinks(s.id)}${table(['Recibo','Fecha','USD','Estado',''],payments,p=>`<td>R-${String(p.id).padStart(6,'0')}</td><td>${dateLabel(p.paid_on)}</td><td>${usd(p.amount)}</td><td>${badge(p.voided?'Anulado':'Válido',p.voided?'red':'')}</td><td>${btn('Ver','receipt','small',p.id)}</td>`,'Sin pagos')}</div>`);
}
function collection(id) {
  const s=state.students.find(s=>s.id===Number(id));
  const text=`Estimado/a ${s.guardian_name}: ${state.settings.school_name} le informa que ${s.name} presenta un saldo vencido de USD ${number(s.overdue/100)} al ${dateLabel(state.today)}.${todayRate()?` Su equivalente de referencia es Bs ${number(s.overdue/100*Number(todayRate().rate))}, a la tasa BCV registrada para hoy (Bs ${todayRate().rate}/USD). Al pagar se aplicará la tasa vigente de la fecha del pago.`:''} Por favor, comuníquese con administración para regularizar su cuenta. Gracias.`;
  showModal('Aviso de cobranza',`Representante: ${esc(s.guardian_name)} · ${esc(s.guardian_phone)||'Sin teléfono'}`,`<p class="hint">Revisa el texto antes de compartirlo. El sistema prepara el aviso; no envía mensajes.</p><label class="field"><textarea id="collection-text" rows="8">${esc(text)}</textarea></label><div class="form-actions">${btn('Copiar aviso','copy-collection','primary')}${whatsappLink(s.guardian_phone,text)}</div>`);
}
function openVoid(endpoint,id) {
  showModal(endpoint==='cancel-charge'?'Anular cargo':'Anular operación','La anulación conserva el registro y su motivo en la bitácora.',recordForm(endpoint,`<input type="hidden" name="id" value="${Number(id)}">${textarea('Motivo obligatorio','reason')}`,{},'Confirmar anulación'));
  $('textarea',modal).required=true;
}
function openFollowup(id) {
  const s=state.students.find(s=>s.id===Number(id)), notes=state.collections.filter(n=>n.student_id===s.id);
  showModal('Seguimiento de cobranza',esc(s.name)+' · '+esc(s.guardian_name),`<form data-endpoint="collections"><input type="hidden" name="student_id" value="${s.id}"><div class="form-grid">${textarea('Nota del contacto / acuerdo','note')}${field('Fecha prometida de pago (opcional)','promised_on','','date')}</div>${formFoot('Registrar seguimiento')}</form><h3 style="margin:22px 0 10px">Historial de contactos</h3>${table(['Fecha / usuario','Nota','Promesa de pago'],notes,n=>`<td>${esc(new Date(n.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}<span class="sub">${esc(n.operator)}</span></td><td style="white-space:normal">${esc(n.note)}</td><td>${dateLabel(n.promised_on)}</td>`,'Sin contactos registrados')}`);
  $('textarea',modal).required=true;
}
function openUser() {
  showModal('Crear usuario','Administración: gestión completa. Caja: cobros y egresos. Consulta: lectura.',recordForm('users',field('Nombre completo','name','','text','required maxlength="200"')+field('Usuario','username','','text','required maxlength="80" autocomplete="off"')+field('Contraseña','password','','password','required minlength="10" maxlength="256" autocomplete="new-password"')+select('Perfil','role',[['cashier','Caja'],['reader','Consulta'],['admin','Administrador']],'cashier'),{}));
}
function openPassword(id) {
  const user=state.users.find(u=>u.id===Number(id));
  showModal('Cambiar contraseña',`Usuario: ${esc(user.name)}. Sus sesiones se cerrarán.`,recordForm('password',`<input type="hidden" name="user_id" value="${user.id}">`+field('Nueva contraseña','password','','password','required minlength="10" maxlength="256" autocomplete="new-password"'),{},'Cambiar contraseña'));
}
function directoryTableMarkup(d) {
  return `<div class="table-wrap"><table><colgroup>${d.widths.map(w=>`<col style="width:${w/758*100}%">`).join('')}</colgroup><thead><tr>${d.headings.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${d.lines.length?d.lines.map(row=>`<tr>${row.map(cell=>`<td>${esc(cell).replaceAll('\n','<br>')}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${d.headings.length}">${esc(d.empty_message||'No hay registros con los filtros seleccionados.')}</td></tr>`}</tbody></table></div>`;
}
async function openDailyReport() {
  const d=await api('daily-report');
  const markup=`<article class="receipt school-document directory-report daily-report">${schoolHeader(d.school,'Reporte diario','',d.issued_on)}<h2>${esc(d.title)}</h2><div class="directory-report-meta"><b>${esc(d.count_label)}</b><span>Emitido: ${esc(d.issued_at)}</span></div><p class="directory-report-filter">${esc(d.filter_label)}</p><div class="daily-report-totals">${d.summaries.map(([label,value])=>`<div><span>${esc(label)}</span><b>${esc(value)}</b></div>`).join('')}</div>${d.sections.map(section=>`<section><h3>${esc(section.title)}</h3>${directoryTableMarkup(section)}</section>`).join('')}<footer><p>${esc(d.note)}</p><p>Generado por: ${esc(d.operator)}</p></footer></article>`;
  showDocument('Reporte diario','daily-report',markup);modal.classList.add('wide-modal');
}

async function openDirectoryReport(kind) {
  const query=new URLSearchParams();
  if(filters.search)query.set('search',filters.search);
  if(kind==='students'&&filters.grade)query.set('grade',filters.grade);
  if(filters.archived)query.set('archived','1');
  const suffix=query.size?'?'+query.toString():'';
  const d=await api('directory/'+kind+suffix);
  const markup=`<article class="receipt school-document directory-report">${schoolHeader(d.school,'Listado administrativo','',d.issued_on)}<h2>${esc(d.title)}</h2><div class="directory-report-meta"><b>${esc(d.count_label)}</b><span>Emitido: ${esc(d.issued_at)}</span></div><p class="directory-report-filter">${esc(d.filter_label)}</p>${directoryTableMarkup(d)}<footer><p>${esc(d.note)}</p><p>Generado por: ${esc(d.operator)}</p></footer></article>`;
  showModal(d.title,'El listado respeta la búsqueda y los filtros del directorio.',`<div class="actions document-actions"><a class="btn primary" href="/api/directory/${kind}.pdf${suffix}" download>${icon('download')} Descargar PDF</a>${btn(`${icon('print')} Imprimir`,'print-receipt')}</div>${markup}`);
  modal.classList.add('wide-modal');$('#print-area').innerHTML=markup;
}

function schoolHeader(s,title,code,on) {
  if(demoMode&&!String(s.legal_name||'').startsWith('PRUEBA SIN VALIDEZ - '))s={...s,legal_name:'PRUEBA SIN VALIDEZ - '+(s.legal_name||s.school_name)};
  const logo=schoolLogo(s);
  const address=s.fiscal_address||s.address;
  return `<header class="document-header"><div class="school-emblem">${logo}</div><div class="school-info">${s.institution_type?`<p class="institution-type">${esc(s.institution_type)}</p>`:''}<h1>${esc(s.legal_name||s.school_name)}</h1>${s.rif?`<p class="school-rif">RIF: ${esc(s.rif)}</p>`:''}${address?`<p class="fiscal-address"><b>Domicilio fiscal:</b> ${esc(address)}</p>`:''}${[s.phone,s.email,s.website].some(Boolean)?`<p class="school-contact">${[s.phone,s.email,s.website].filter(Boolean).map(esc).join(' · ')}</p>`:''}</div><div class="document-number"><span>${esc(title)}</span><b class="receipt-number">${esc(code)}</b><span>${dateLabel(on)}</span></div></header>`;
}
function documentActions(path) {
  const isReceipt=path.startsWith('receipt/');
  return `<div class="actions document-actions">${isReceipt?`<label class="receipt-paper-control">Tamaño del recibo<select id="receipt-paper"><option value="half-letter" ${receiptPaper==='half-letter'?'selected':''}>Media carta · vertical</option><option value="letter-pair" ${receiptPaper==='letter-pair'?'selected':''}>Carta horizontal · 2 copias verticales</option><option value="a4" ${receiptPaper==='a4'?'selected':''}>A4 · vertical</option><option value="ticket-80" ${receiptPaper==='ticket-80'?'selected':''}>Ticket térmico · 80 mm</option><option value="ticket-58" ${receiptPaper==='ticket-58'?'selected':''}>Ticket térmico · 58 mm</option></select></label>`:''}<a class="btn primary" href="/api/${path}.pdf${isReceipt?'?paper='+receiptPaper:''}" download>${icon('download')} Descargar PDF</a>${btn(`${icon('print')} Imprimir`,'print-receipt')}</div>${isReceipt?'<p class="receipt-paper-help" id="receipt-paper-help"></p>':''}`;
}
function setReceiptPaper(paper) {
  receiptPaper=['a4','half-letter','letter-pair','ticket-58','ticket-80'].includes(paper)?paper:'half-letter';
  const area=$('#print-area'),previous=area.querySelector('.receipt-print-pair');
  if(previous)area.replaceChildren(previous.querySelector('.payment-receipt'));
  area.querySelectorAll('.receipt-copy-label').forEach(el=>el.remove());
  const half=receiptPaper==='half-letter'||receiptPaper==='letter-pair';
  document.querySelectorAll('.payment-receipt').forEach(el=>{el.classList.toggle('receipt-half-letter',half);el.classList.toggle('receipt-ticket',receiptPaper.startsWith('ticket-'));el.classList.toggle('receipt-ticket-58',receiptPaper==='ticket-58');el.classList.toggle('receipt-ticket-80',receiptPaper==='ticket-80');});
  if(receiptPaper==='letter-pair'){
    const receipt=area.querySelector('.payment-receipt');
    if(receipt){
      const sheet=document.createElement('section'),copy=receipt.cloneNode(true);sheet.className='receipt-print-pair';
      for(const [item,label] of [[receipt,'ORIGINAL'],[copy,'COPIA']]){
        const badge=document.createElement('span');badge.className='receipt-copy-label';badge.textContent=label;item.querySelector('.document-number').append(badge);
      }
      sheet.append(receipt,copy);area.replaceChildren(sheet);
    }
  }
  const link=modal.querySelector('.document-actions a[download]');
  if(link){const url=new URL(link.href);url.searchParams.set('paper',receiptPaper);link.href=url.pathname+url.search;}
  const help=$('#receipt-paper-help');
  if(help)help.textContent=receiptPaper==='letter-pair'?'Original para el representante y copia para el colegio, con el mismo número R-, en carta horizontal. Usa la configuración normal de impresión. Desactiva encabezados y pies del navegador; ambas copias dejan espacio para firmar.':receiptPaper.startsWith('ticket-')?'Ticket de '+receiptPaper.slice(-2)+' mm. Selecciona la impresora térmica y usa escala 100 %. La impresión depende del controlador instalado en Windows.':receiptPaper==='half-letter'?'13,97 × 21,59 cm. Selecciona media carta o una hoja carta y usa la configuración normal de impresión. Sin encabezados ni pies del navegador. Para dos copias en una hoja, elige Carta horizontal · 2 copias verticales.':'A4 vertical. Recomendado para muchos conceptos u observaciones extensas.';
}
function showDocument(title,path,markup) {
  showModal(title,'Documento listo para descargar o imprimir.',documentActions(path)+markup);modal.classList.toggle('document-modal',markup.includes('payment-receipt'));$('#print-area').innerHTML=markup;
  if(path.startsWith('receipt/'))setReceiptPaper(receiptPaper);
}
async function enrollmentDocument(studentId,documentId) {
  const id=documentId||state.enrollments.find(e=>e.student_id===Number(studentId))?.id;
  if(!id){toast('Guarda la matrícula para generar su primera constancia.',true);return;}
  const d=await api('enrollment/'+id),s=d.student;
  showDocument('Constancia de matrícula','enrollment/'+id,`<article class="receipt school-document">${schoolHeader(d.school,'Constancia de matrícula','M-'+String(id).padStart(6,'0'),d.issued_on||d.created_at.slice(0,10))}<div class="document-section"><h3>Datos del alumno</h3><dl><dt>Nombre completo</dt><dd>${esc(s.name)}</dd><dt>Código único</dt><dd>${esc(s.student_code)}</dd><dt>Cédula / documento</dt><dd>${s.document===s.student_code?'Sin cédula propia':esc(s.document)}</dd><dt>Fecha de nacimiento</dt><dd>${esc(schoolBirth(s.birth_date))}</dd><dt>Grado / año escolar</dt><dd>${esc(s.grade_name)} · ${s.school_year}–${s.school_year+1}</dd><dt>Período académico</dt><dd>${dateLabel(s.enrollment_start)} al ${dateLabel(s.enrollment_end)} · ${s.status==='active'?'Activo':'Inactivo'}</dd><dt>Mensualidades desde</dt><dd>${esc(schoolMonth(s.billing_start||s.enrollment_start.slice(0,7)))}</dd></dl></div><div class="document-section"><h3>Representante legal</h3><dl><dt>Nombre / cédula</dt><dd>${esc(s.guardian_name)} · ${esc(s.guardian_document)}</dd><dt>Contacto</dt><dd>${[s.guardian_phone,s.guardian_email].filter(Boolean).map(esc).join(' · ')||'—'}</dd><dt>Dirección</dt><dd>${esc(s.guardian_address)||'—'}</dd></dl></div>${table(['Mensualidad base USD','Beca / descuento','Mensualidad final USD'],[s],r=>`<td>${usd(r.monthly_fee)}</td><td>${r.discount} %</td><td><strong>${usd(r.net_fee)}</strong></td>`)}<p>Observaciones: ${esc(s.notes)||'—'}</p><div class="signature-row"><span>Administración</span><span>Representante legal</span></div><p class="document-footer">Registrado por ${esc(d.operator)} · Constancia administrativa de matrícula</p></article>`);
}
function paymentReceiptMarkup(r) {
  const p=r.payment;
  const period = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value)?monthLabel(value):value;
  const markup=`<article class="receipt school-document payment-receipt">${schoolHeader(r.settings,'Comprobante de pago','R-'+String(p.id).padStart(6,'0'),p.paid_on)}${p.voided?`<div class="receipt-void"><b>COMPROBANTE ANULADO</b><p>${esc(p.void_reason)}</p></div>`:''}<div class="receipt-parties"><section><span class="receipt-label">Representante legal</span><h2>${esc(p.guardian_name)}</h2><p>Cédula: ${esc(p.guardian_document)}</p>${p.guardian_phone?`<p>${esc(p.guardian_phone)}</p>`:''}</section><section><span class="receipt-label">Alumno · Grado / sección</span><h2>${esc(p.student_name)}${p.grade_name?`<span class="receipt-student-grade"> · ${esc(p.grade_name)}</span>`:''}</h2>${p.grade_name?'':'<p>Grado no registrado</p>'}</section></div>${p.guardian_address?`<p class="receipt-address"><span>Dirección del representante</span>${esc(p.guardian_address)}</p>`:''}<section class="receipt-charges"><h3 class="receipt-label">Conceptos abonados</h3>${table(['Descripción','Período','Aplicado · USD','Pendiente · USD'],r.allocations,a=>`<td>${esc(a.concept)}</td><td>${esc(period(a.period))}</td><td class="money">${usd(a.amount)}</td><td class="money">${a.balance_after===undefined?'—':usd(a.balance_after)}</td>`)}</section><div class="receipt-payment"><section class="receipt-method"><span class="receipt-label">Método de pago</span><p class="receipt-method-name">${esc(p.method)}</p>${p.reference?`<span class="receipt-label">Referencia / comprobante</span><p>${esc(p.reference)}</p>`:''}</section><section class="receipt-amount"><span class="receipt-label">Importe recibido · ${p.currency==='VES'?'Bolívares':'USD'}</span><div class="receipt-amount-value">${p.currency==='VES'?bs(p.received_amount):usd(p.received_amount)}</div><div class="receipt-applied"><span>Total aplicado en USD</span><b>${usd(p.amount)}</b></div>${p.currency==='VES'?`<p class="receipt-rate">Tasa BCV aplicada: Bs ${esc(p.exchange_rate)} por USD</p>`:''}</section></div>${receiptBalance(p)}${p.notes?`<section class="receipt-notes"><span class="receipt-label">Observaciones</span><p>${esc(p.notes)}</p></section>`:''}<div class="signature-row"><span>Firma de administración</span><span>Firma del representante</span></div><footer class="receipt-bottom"><p>Registrado por: ${esc(p.operator)}</p><p>Comprobante administrativo · No sustituye una factura fiscal.</p></footer></article>`;
  return markup;
}
async function receipt(id) {
  const r=await api('receipt/'+id);
  showDocument('Comprobante de pago','receipt/'+id,paymentReceiptMarkup(r));
}
function printReport() {
  const income=state.payments.filter(p=>!p.voided&&p.paid_on>=reportFrom&&p.paid_on<=reportTo).reduce((t,p)=>t+p.amount,0), expenses=state.expenses.filter(e=>!e.voided&&e.spent_on>=reportFrom&&e.spent_on<=reportTo).reduce((t,e)=>t+e.amount,0);
  $('#print-area').innerHTML=`<article class="receipt school-document">${schoolHeader(state.settings,'Resumen administrativo','',state.today)}<p>Período: ${dateLabel(reportFrom)} al ${dateLabel(reportTo)}</p><dl><dt>Ingresos USD</dt><dd>${usd(income)}</dd><dt>Egresos USD</dt><dd>${usd(expenses)}</dd><dt>Balance USD</dt><dd>${usd(income-expenses)}</dd><dt>Deuda vencida actual</dt><dd>${usd(state.summary.overdue)}</dd><dt>Alumnos activos</dt><dd>${state.summary.active_students}</dd></dl><p class="hint">Generado el ${dateLabel(state.today)}. Importes convertidos con la tasa almacenada en cada operación. El saldo vencido corresponde al corte actual.</p></article>`;window.print();
}
document.addEventListener('click',async event=>{
  const target=event.target.closest('[data-action]');if(!target)return;
  const {action,id}=target.dataset;
  try {
    if(state&&!state.history_loaded&&!['nav','boot','logout','close','mobile-menu','mobile-menu-close'].includes(action)){state=await api('state?history=1');}
    switch(action) {
      case 'income-account':openIncomeAccount(id);break;case 'income-categories':openIncomeCategories();break;case 'income-category':openIncomeCategory(id);break;case 'income-other':openOtherIncome();break;case 'income-assign':openIncomeAssign();break;case 'income-deposit':openIncomeDeposit();break;
      case 'month-close':openMonthClose();break;case 'month-reopen':showModal('Reabrir mes','Solo Administración. La reapertura conserva el cierre anterior.',`<form data-endpoint="month-reopen"><input type="hidden" name="id" value="${Number(id)}">${textarea('Motivo','reason')}${formFoot('Reabrir con motivo')}</form>`);break;
      case 'month-annotation':openMonthAnnotation(id);break;
      case 'accounting-csv':case 'accounting-pdf':await binaryBackup('accounting-report.'+(action==='accounting-csv'?'csv':'pdf')+'?month='+encodeURIComponent(incomeMonth));break;
      case 'bank-profile':openBankProfile(id);break;case 'bank-import':openBankImport();break;case 'bank-link':openBankLink();break;case 'bank-classify':openBankClassify(id);break;
      case 'bank-auto':await api('bank-auto',{month:incomeMonth});await refresh();toast('Cruces únicos revisados y guardados; los ambiguos siguen pendientes.');break;
      case 'bank-unlink':case 'bank-unclassify':showModal('Retirar vínculo o clasificación','No se borra el historial.',`<form data-endpoint="${action}"><input type="hidden" name="id" value="${Number(id)}">${textarea('Motivo','reason')}${formFoot('Retirar con motivo')}</form>`);break;
      case 'bank-commit':await commitBankImport();break;
      case 'income-next':incomeOffset+=100;await refresh();break;case 'income-prev':incomeOffset=Math.max(0,incomeOffset-100);await refresh();break;
      case 'income-void-other':case 'income-void-deposit':showModal('Anular movimiento','La historia se conserva.',`<form data-endpoint="${action}"><input type="hidden" name="id" value="${Number(id)}">${textarea('Motivo de anulación','reason')}${formFoot('Anular con motivo')}</form>`);break;
      case 'clock-check':await openClockGate();break;
      case 'windows-protection-help':windowsProtectionHelp();break;
      case 'backup-cloud-declare':openCloudDeclaration();break;
      case 'backup-cloud-revoke':await api('backup-cloud-declare',{directory:state.backup.secondary_directory,declared:false});await refresh();toast('Se quitó la declaración de carpeta de nube.');break;
      case 'archive-kind':archiveKind=id;filters={};$('#page-content').innerHTML=pageBody();break;
      case 'archive-review':await openArchiveReview(archiveKind,id);break;
      case 'delete-unused-review':{const [kind,target]=id.split(':');await openUnusedDelete(kind,target);break;}
      case 'settings-section':selectSettingsSection(id);break;
      case 'open-maintenance':rememberSettingsDrafts();page='settings';settingsSection='maintenance';render();break;
      case 'nav':rememberSettingsDrafts();page=id;filters={};await refresh();break;
      case 'close':modal.close();break;
      case 'boot':await boot();break;
      case 'demo-exit':await closeDemo();break;
      case 'logout':await api('logout',{});forgetSessionDraft();modal.close();await boot();break;
      case 'recovery-notice-ack':await acknowledgeRecoveryNotice();break;
      case 'year-transition':openYearTransition();break;case 'load-year':await loadYear();break;case 'preview-year':await previewYear();break;case 'confirm-year':await confirmYear();break;case 'year-document':await yearDocument(id);break;case 'payment-plan':openPaymentPlan(id);break;case 'plan-document':await planDocument(id);break;case 'cancel-plan':openVoid('cancel-plan',id);break;case 'import-roster':openImport();break;case 'import-guide':await openImportGuide();break;case 'recovery-help':recoveryHelp();break;case 'crypto-open':openCryptoSetup();break;case 'crypto-prepare':await prepareCrypto();break;case 'crypto-confirm':await confirmCrypto();break;case 'crypto-unlock':await unlockCrypto();break;case 'crypto-print':printRecovery();break;case 'download-encrypted-backup':await downloadEncryptedBackup();break;case 'convert-backup':await convertBackup();break;case 'snooze-backup-reminder':snoozeBackupReminder();break;case 'probe-backup':openProbeBackup();break;case 'run-probe-backup':await runProbeBackup();break;case 'maintenance-help':maintenanceHelp();break;case 'maintenance-review':await maintenanceReview();break;case 'audit-filter':await filterAudit();break;case 'audit-pdf':await exportAudit('pdf');break;case 'audit-csv':await exportAudit('csv');break;case 'backup-now':await backupNow();break;case 'remove-logo':{const form=target.closest('form');form.elements.logo.value='';$('#logo-preview',form).innerHTML=schoolLogo({});break;}case 'preview-import':await previewImport();break;case 'confirm-import':await confirmImport();break;case 'guardian-account':await guardianAccount(id);break;case 'issue-account':await issueGuardian(id,'account');break;case 'issue-solvency':await issueGuardian(id,'solvency');break;case 'guardian-document':await guardianDocument(id);break;case 'open-cash':await openCash();break;case 'cash-document':await cashDocument(id);break;case 'reopen-cash':openVoid('reopen-cash',id);break;case 'guardian':openGuardian(id);break;case 'grade':openGrade(id);break;case 'student':openStudent(id);break;
      case 'enrollment':await enrollmentDocument(id);break;case 'payment':openPayment(id);break;case 'expense':openExpense();break;
      case 'charge':openCharge(id);break;case 'generate':openGenerate();break;
      case 'rates':openRates();break;case 'account':account(id);break;case 'collection':collection(id);break;case 'followup':openFollowup(id);break;
      case 'delete-grade':case 'archive-student':case 'archive-guardian':case 'restore-student':case 'restore-guardian':openDirectoryAction(action,id);break;
      case 'correct-billing':openBillingCorrection(id);break;
      case 'void-payment':case 'void-expense':case 'cancel-charge':openVoid(action,id);break;
      case 'user':openUser();break;case 'password':openPassword(id);break;case 'receipt':await receipt(id);break;
      case 'monthly-pdf':case 'monthly-csv':{const month=$('#closing-month').value;if(!month)throw new Error('Selecciona el mes.');await binaryBackup('monthly-report.'+(action==='monthly-pdf'?'pdf':'csv')+'?month='+encodeURIComponent(month));break;}
      case 'daily-report':await openDailyReport();break;case 'directory-report':await openDirectoryReport(id);break;case 'print-receipt':await checkedPrint();break;case 'print-report':await checkedPrint(true);break;
      case 'export-students':openStudentExport();break;
      case 'copy-collection':await navigator.clipboard.writeText($('#collection-text').value);toast('Aviso copiado.');break;
      case 'rate-inline':await rateInline();break;
      case 'save-inline-rate':{
        const form=$('form',modal), on=form.elements.paid_on?.value||form.elements.spent_on?.value;
        await api('rates',{rate_date:on,rate:$('#inline-rate-value').value});state=await api('state');$('#inline-rate').remove();updateConversion();render();toast('Tasa BCV guardada.');break;
      }
      case 'full-payment':{
        const form=$('form[data-endpoint="payments"]',modal), s=state.students.find(s=>s.id===Number(form.elements.student_id.value)), rate=state.rates.find(r=>r.rate_date===form.elements.paid_on.value);
        if(form.elements.currency.value==='VES'&&!rate)throw new Error('Registra la tasa BCV de la fecha del pago primero.');
        form.elements.amount.value=(s.balance/100*(form.elements.currency.value==='VES'?Number(rate.rate):1)).toFixed(2);updateConversion();break;
      }
    }
  }catch(error){toast(error.message,true);}
});
document.addEventListener('submit',async event=>{
  const form=event.target;if(!form.dataset.endpoint)return;
  if(form.dataset.endpoint.startsWith('invoice-'))return;
  event.preventDefault();const endpoint=form.dataset.endpoint, data=Object.fromEntries(new FormData(form));
  if(['clock-confirm','backup-cloud-declare'].includes(endpoint))data.reviewed=form.elements.reviewed.checked;
  if(endpoint==='correct-billing-start'){data.charge_ids=JSON.parse(data.charge_ids);data.confirmed=form.elements.confirmed.checked;}
  if(endpoint==='payment-plans'){data.expected_total=Number(data.expected_total);data.installments=Array.from(form.querySelectorAll('[data-plan-row]')).map(row=>({amount:row.querySelector('[data-plan-amount]').value,due_date:row.querySelector('[data-plan-date]').value}));}
  if(endpoint==='month-close')data.confirmed_pending=Boolean(form.elements.confirmed_pending?.checked);
  if(endpoint==='month-annotation'){data.special_taxpayer=form.elements.special_taxpayer.checked;data.foreign_currency=form.elements.foreign_currency.checked;}
  if(endpoint==='income-assign')data.ids=data.ids.split(',').map(v=>v.trim()).filter(Boolean);
  if(endpoint==='income-deposit')data.payments=data.allocations.split(/\r?\n/).filter(v=>v.trim()).map(line=>{const pair=line.split('=');return {payment_id:pair[0]?.trim(),amount:pair[1]?.trim()};});
  const submit=form.querySelector('[type="submit"]'), errorBox=$('.error',form);submit.disabled=true;errorBox.textContent='';
  try {
    if(endpoint==='bank-profile')data.profile=bankMapping(form);
    if(endpoint==='bank-link')data.links=data.allocations.split(/\r?\n/).filter(line=>line.trim()).map(line=>{const pair=line.trim().split(/\s+/);return {movement_id:pair[0],source:pair[1],amount:pair[2]};});
    if(endpoint==='bank-preview'){const file=form.elements.statement_file.files[0];if(!file||file.size>2000000)throw new Error('Elige un CSV o XLSX de hasta 2 MB.');data.filename=file.name;data.file_base64=await readBankFile(file);data.profile=bankMapping(form);delete data.statement_file;bankDraft=data;}
    const result=await api(endpoint,data);
    if(endpoint==='bank-preview'){showBankPreview(result);return;}
    if(endpoint==='clock-confirm'){await openRateGate();toast('Fecha y hora confirmadas. La revisión quedó en la bitácora.');return;}
    if(endpoint==='backup-cloud-declare'){await refresh();modal.close();toast('Carpeta de nube declarada. Sigue revisando la sincronización en Drive.');return;}
    if(['login','setup','demo-login'].includes(endpoint)){await boot();return;}
    if(endpoint==='confirm-rate'){await refresh();return;}
    if(endpoint==='password'&&Number(data.user_id)===state.user.id){modal.close();await boot();return;}
    await refresh(endpoint);if(endpoint!=='rates')modal.close();
    if(endpoint==='payment-plans'){toast('Convenio guardado.');await planDocument(result.id);}
    else if(endpoint==='close-cash'){toast('Caja cerrada.');await cashDocument(result.id);}
    else if(endpoint==='payments'){toast(result.duplicate?'El pago ya estaba registrado.':'Pago registrado correctamente.');await receipt(result.id);}
    else if(endpoint==='students'){toast(`Matrícula guardada · ${result.student_code}`);await enrollmentDocument(result.id,result.document_id);}
    else if(endpoint==='correct-billing-start'){toast(`${result.cancelled} mensualidades anuladas con motivo. Se conservaron los pagos.`);account(result.id);}
    else if(endpoint==='delete-unused-record')toast('Ficha sin movimientos borrada. Se conservó un respaldo previo.');
    else if(endpoint==='delete-grade')toast('Grado / sección eliminado.');
    else if(endpoint.startsWith('archive-'))toast('Ficha eliminada del directorio y archivada. El historial se conserva.');
    else if(endpoint.startsWith('restore-'))toast('Ficha recuperada. Revisa sus datos antes de utilizarla.');
    else if(endpoint==='generate')toast(`${result.created} mensualidades creadas. Los cargos existentes no se duplicaron.`);
    else {toast('Registro guardado correctamente.');if(endpoint==='rates')openRates();}
    if(result.backup_warning)toast('Operación guardada. '+result.backup_warning,true);
  }catch(error){errorBox.textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.name==='school_year'&&el.closest('form[data-endpoint="setup"]'))el.dataset.manual='true';
  if(el.id==='collection-text'){const link=$('#wa-collection');if(link){const url=new URL(link.href);url.searchParams.set('text',el.value);link.href=url.href;}}
  if(el.id==='plan-count'){buildPlanRows();return;}
  if(el.closest('form[data-endpoint="correct-billing-start"]')&&el.name==='billing_start')updateBillingCorrection();
  if(el.id==='search'){
    const pos=el.selectionStart;filters.search=el.value;$('#page-content').innerHTML=pageBody();$('#search').focus();$('#search').setSelectionRange(pos,pos);
  }
  if(el.closest('form[data-endpoint="close-cash"]'))updateCashCount();
  if(el.id==='guardian-search')searchGuardian();
  if(el.closest('form[data-endpoint="students"]'))updateTuition();
  if(el.closest('form[data-endpoint="payments"], form[data-endpoint="expenses"], form[data-endpoint="income-other"]'))updateConversion();
});
document.addEventListener('change',event=>{
  const calendarForm=event.target.closest('form[data-endpoint="setup"]');
  if(calendarForm&&event.target.name==='start_month'&&!calendarForm.elements.school_year.dataset.manual){
    calendarForm.elements.school_year.value=Number(setupToday.slice(0,4))-(Number(setupToday.slice(5,7))<Number(event.target.value));
  }
  if(event.target.id==='roster-file'){rosterFile=rosterPreview=undefined;$('#roster-preview').innerHTML='';}

  if(event.target.closest('form[data-endpoint="expenses"]')&&event.target.name==='category')
  if(event.target.id==='archive-state'){filters.archiveState=event.target.value;$('#page-content').innerHTML=pageBody();return;}
  if(event.target.id==='show-archived'){filters.archived=event.target.checked;$('#page-content').innerHTML=pageBody();return;}
  if(event.target.id==='receipt-paper'){setReceiptPaper(event.target.value);return;}
  const el=event.target;
  if(el.id==='bank-days'){bankDays=Math.min(3650,Math.max(1,Number(el.value)||7));refresh().catch(e=>toast(e.message,true));return;}
  if(el.id==='income-month'){incomeMonth=el.value;incomeOffset=0;refresh().catch(e=>toast(e.message,true));return;}
  if(el.id==='cash-date'){cashDate=el.value;return;}
  if(el.id==='cash-close-date'){cashDate=el.value;openCash().catch(e=>toast(e.message,true));return;}
  if(el.id==='grade-filter'){filters.grade=el.value;$('#page-content').innerHTML=pageBody();}
  if(el.id==='report-from'||el.id==='report-to'){
    const from=$('#report-from').value,to=$('#report-to').value;
    if(!from||!to||from>to){toast('Elige un rango de fechas válido.',true);return;}
    reportFrom=from;reportTo=to;$('#page-content').innerHTML=pageBody();
  }
  if(el.closest('form[data-endpoint="close-cash"]'))updateCashCount();
  if(el.id==='guardian-search')searchGuardian();
  if(el.closest('form[data-endpoint="students"]'))updateTuition();
  if(el.closest('form[data-endpoint="payments"], form[data-endpoint="expenses"], form[data-endpoint="income-other"]'))updateConversion();
});
modal.addEventListener('click',event=>{if(event.target===modal){const r=modal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)modal.close();}});
modal.addEventListener('close',()=>{if(!modal.open){$('#modal-content').replaceChildren();if(modal.dataset.recoveryPrint){$('#print-area').replaceChildren();delete modal.dataset.recoveryPrint;}}});
async function checkDay() {
  if(readOnlyInfo)return;
  if(!session||document.hidden)return;
  try {
    const gate=await api('rate-gate');
    if(gate.clock?.blocked){gateBackup=gate.backup;gateRole=gate.role;updateBackupWarnings();if(!$('.clock-gate'))await openClockGate({...gate.clock,role:gate.role});return;}
    if(state&&gate.today!==state.today){await openRateGate();return;}
    if(state){
      state.backup=await api('backup-status');
      document.querySelectorAll('.backup-status').forEach(el=>{el.innerHTML=backupLabel();el.classList.toggle('text-red',backupStale());});
    }else{gateBackup=gate.backup;gateRole=gate.role;}
    updateBackupWarnings();
  }catch(error){toast(error.message,true);}
}
setInterval(checkDay,30000);
document.addEventListener('visibilitychange',checkDay);
sessionInit();
boot();

let rosterFile, rosterPreview, cashPreview, cashDate='';
function openStudentExport(){
  showModal('Exportar alumnos y matrículas','Archivo completo compatible con Importar Excel / CSV.',`<p>Incluye representantes vinculados, cédulas, contactos, grados, cupos, códigos de alumnos, tarifas, descuentos, fechas y estados activos, inactivos y archivados.</p><div class="actions"><a class="btn primary" href="/api/export?type=students&format=xlsx" download>${icon('download')} Exportar Excel (.xlsx)</a><a class="btn" href="/api/export?type=students&format=csv" download>${icon('download')} Exportar CSV</a></div><p class="hint">Excel conserva teléfonos y cédulas como texto. Puedes importar el archivo directamente en Aula - Pruebas; los grados que falten se crearán con sus cupos. La vista previa no guarda datos.</p><div class="notice"><div><b>Alumnos y matrículas, no el historial de caja</b>No incluye pagos, recibos, convenios ni saldos históricos para restaurar. Saldo USD informativo es solo una referencia; al importar se generan cargos según las fechas y tarifas. Para llevar toda la base al colegio usa un respaldo completo y Restaurar respaldo.</div></div><p>Para un documento presentable, usa <b>PDF / Imprimir</b> en el directorio de alumnos.</p>`);
}
function backupStale(){if(demoMode)return false;const time=Date.parse(state.backup?.local_at||'');return !Number.isFinite(time)||Date.now()-time>86400000||!!state.backup?.local_error;}
function backupLabel(){
  if(demoMode)return 'Pruebas · datos temporales';
  const b=state.backup||{};
  if(b.local_error)return esc(b.local_error);
  if(!Number.isFinite(Date.parse(b.local_at||'')))return 'Sin respaldo automático confirmado';
  const minutes=Math.max(0,Math.floor((Date.now()-Date.parse(b.local_at))/60000));
  return 'Último respaldo '+(minutes<1?'hace menos de un minuto':minutes<60?`hace ${minutes} min`:minutes<1440?`hace ${Math.floor(minutes/60)} h`:`hace ${Math.floor(minutes/1440)} días`);
}
function backupReminderHidden(now=Date.now()){
  try{const saved=JSON.parse(localStorage.getItem('aula-backup-reminder-snooze')||'null');
    return saved&&Number.isFinite(saved.at)&&now>=saved.at&&now-saved.at<7*86400000;
  }catch{return false;}
}
function snoozeBackupReminder(){
  try{localStorage.setItem('aula-backup-reminder-snooze',JSON.stringify({at:Date.now()}));}
  catch{throw new Error('No se pudo guardar la preferencia en este navegador.');}
  updateBackupWarnings();toast('Recordatorio oculto durante 7 días en este navegador. Los avisos de errores siguen activos.');
}
function backupProblem(){
  const b=state?.backup||gateBackup||{},role=state?.user.role||gateRole;
  if(demoMode||!['admin','cashier'].includes(role))return '';
  const reminder=b.external_probe_reminder?.due&&!backupReminderHidden()?`<p class="hint backup-probe-reminder">${esc(b.external_probe_reminder.message)} ${role==='admin'&&state?btn('Probar respaldo','probe-backup','small'):''} ${btn('Ocultar por 7 días','snooze-backup-reminder','small')}</p>`:'';
  if(!b.alerts?.length)return reminder; // El estado detallado se consulta en Protección y mantenimiento.
  const action=role==='admin'&&state?btn('Revisar en Configuración','open-maintenance','small'):'<p class="backup-next-step">Pide al administrador que revise las copias de seguridad.</p>';
  return reminder+`<section class="notice backup-warning backup-persistent" role="alert" aria-label="Aviso de respaldos">${icon('shield')}<div><b>Revisa la protección de tus respaldos</b><ul>${b.alerts.map(a=>`<li>${esc(a.message)}</li>`).join('')}</ul><p class="hint">Aula confirma la escritura en la carpeta, no la subida a Drive u otra nube. Revisa la sincronización en su aplicación.</p><p class="hint backup-encryption-status">${esc(externalEncryptionLabel(b))}</p>${action}</div></section>`;
}
function updateBackupWarnings(){
  const host=$('#backup-alerts');if(!host)return;
  const markup=backupProblem();if(host.innerHTML!==markup)host.innerHTML=markup;
  const protection=$('#protection-status');if(protection)protection.innerHTML=protectionStatus();
}
function protectionStatus(){
  if(demoMode)return '<p class="hint">Pruebas usa datos temporales. Esta revisión corresponde a la aplicación real.</p>';
  const b=state?.backup||{},p=b.protection||{};
  const cloud=b.secondary_directory?`<div class="protection-check"><b>Carpeta sincronizada con una nube</b><p>${b.cloud_declared?'Declarada por administración. Aula no comprueba si los archivos llegaron a la nube. Revisa periódicamente su aplicación.':'Si usas Drive, OneDrive o Dropbox, revisa la copia en su web antes de declarar esta carpeta. La declaración solo sustituye el aviso de disco desconocido.'}</p>${b.cloud_declared?btn('Quitar declaración de nube','backup-cloud-revoke','small'):btn('Declarar carpeta de nube','backup-cloud-declare','small')}</div>`:'';
  return `${cloud}<h3>Protección de esta PC</h3><p class="hint">Se consulta con los permisos de tu cuenta de Windows. BitLocker puede requerir un administrador para comprobar su estado.</p>${[['bitlocker','BitLocker · disco de los datos'],['acl','Permisos de la carpeta de datos']].map(([key,title])=>{
    const check=p[key]||{status:'unknown',label:'No se pudo comprobar',detail:'La revisión está pendiente.'};
    return `<div class="protection-check"><b>${title}</b><span class="${['active','restricted'].includes(check.status)?'text-green':check.status==='unknown'?'text-amber':'text-red'}">${esc(check.label)}</span><p>${esc(check.detail)}</p></div>`;
  }).join('')}<p class="hint">Revisión de solo lectura cada cinco minutos. Aula no activa BitLocker ni cambia permisos. ${p.checked_at?'Última revisión: '+esc(new Date(p.checked_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))+'.':''}</p>${btn('Cómo comprobarlo desde Windows','windows-protection-help','small')}`;
}
function openCloudDeclaration(){
  const directory=state?.backup?.secondary_directory;
  if(!admin()||demoMode||!directory)throw new Error('Configura primero la segunda carpeta con el Administrador.');
  showModal('Declarar carpeta de nube','Esta revisión es manual; Aula no consulta tu cuenta de Drive.',`<p>Carpeta: <b>${esc(directory)}</b></p><ol><li>Abre Drive, OneDrive o Dropbox y comprueba que la sincronización esté al día.</li><li>Entra en su web y verifica que existe un respaldo reciente de esta carpeta.</li></ol><p class="hint">La declaración sustituye el aviso de disco desconocido por un recordatorio discreto. No indica que Aula verificó la nube. Los fallos de copia, copias antiguas y avisos de mismo disco siguen visibles. Si cambias la ruta, debes revisarla otra vez.</p><form data-endpoint="backup-cloud-declare"><input type="hidden" name="directory" value="${esc(directory)}"><label class="confirm-check"><input type="checkbox" name="reviewed" required> Revisé la subida de una copia reciente y esta carpeta está configurada para sincronizarse con la nube.</label><div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn primary">Confirmar carpeta de nube</button></div></form>`);
}
function windowsProtectionHelp(){
  const drive=(state?.backup?.data_path||'').match(/^([A-Za-z]:)/)?.[1]||'';
  showModal('Comprobar la protección desde Windows','La revisión manual no cambia los permisos de Aula.',`<ol class="help-steps"><li><b>Comprueba BitLocker:</b> busca «Administrar BitLocker» en Inicio. Revisa ${drive?`la unidad ${esc(drive)}`:'la unidad que contiene la carpeta de datos'}. Si está activado, Aula puede seguir mostrando «No se pudo comprobar» porque Windows limita la consulta. Si está cifrándose, espera a que termine.</li><li><b>Guarda la clave de recuperación:</b> si BitLocker está activo, pulsa «Hacer una copia de seguridad de la clave de recuperación» junto a la unidad. Es un número de 48 dígitos. Imprímelo o guárdalo en un USB fuera de esta PC. Si lo guardaste en tu cuenta Microsoft, revisa <a href="https://aka.ms/myrecoverykey" target="_blank" rel="noopener noreferrer">tus claves de recuperación</a>. Si la cuenta aparece vacía, comprueba otra cuenta o vuelve a sacar una copia desde Windows mientras la unidad esté desbloqueada.</li><li><b>Si está desactivado:</b> comprueba primero tu respaldo de Aula. Al activar BitLocker, Windows te pedirá guardar la clave; verifica esa copia antes de continuar. En Windows con cifrado de dispositivo, busca «Cifrado del dispositivo» en Configuración. Si la opción no aparece o pide permisos, solicita ayuda a un técnico.</li><li><b>Permisos de la carpeta:</b> abre la carpeta de datos desde Inicio de Windows → Abrir carpeta de datos. Propiedades → Seguridad muestra las cuentas con acceso. Pide a un técnico que revise permisos de carpeta y archivos.</li></ol><p class="hint">La comprobación manual no cambia el resultado automático de Aula: un estado desconocido nunca se presenta como activo. BitLocker protege ese disco; las copias del USB o de Drive requieren su propia protección.</p>`);
}

function openImport(){
  rosterFile=rosterPreview=undefined;
  showModal('Importar alumnos y representantes','Carga inicial con vista previa. No modifica alumnos ni representantes existentes.',`<p>Puedes seleccionar directamente un Excel o CSV exportado por esta versión de Aula. Si estás cargando datos a mano, descarga la plantilla y completa una fila por alumno. Los hermanos repiten los datos del representante.</p><div class="actions"><a class="btn" href="/api/import-template?format=xlsx" download>Plantilla Excel (.xlsx)</a><a class="btn" href="/api/import-template" download>Plantilla CSV</a>${btn('Guía columna por columna','import-guide')}</div><p class="hint">Fechas: AAAA-MM-DD o fechas de Excel. Mensualidad base: dólares sin símbolos ni miles, hasta dos decimales; el descuento va aparte. Grado: nombre exacto del catálogo. Año escolar: año de inicio. Cédulas, teléfonos y códigos: texto. Sin fórmulas. Se admite .xlsx o CSV UTF-8, hasta 2 MB / 1000 alumnos.</p><label class="field">Archivo<input id="roster-file" type="file" accept=".csv,.xlsx"></label><div class="notice"><div><b>Revisa el primer mes a cobrar</b>Usa primer_mes_cobro en formato AAAA-MM. Si lo dejas vacío, comienza en el mes de carga (o al iniciar el período si es futuro), aunque el período académico empiece en septiembre. Las deudas anteriores se registran expresamente. Los períodos ya terminados requieren escoger un mes del ciclo.</div></div><div class="actions">${btn('Revisar archivo','preview-import','primary')}</div><div id="roster-preview" aria-live="polite"></div>`);
  modal.classList.add('wide-modal');
}
async function previewImport(){
  rosterPreview=undefined;$('#roster-preview').innerHTML='';
  const file=$('#roster-file').files[0];if(!file)throw new Error('Selecciona el archivo primero.');
  if(file.size>2000000)throw new Error('El archivo supera 2 MB.');
  const button=modal.querySelector('[data-action="preview-import"]');button.disabled=true;
  try{
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
    for(let i=0;i<bytes.length;i+=4096)binary+=String.fromCharCode(...bytes.subarray(i,i+4096));
    rosterFile={filename:file.name,content:btoa(binary)};
    const preview=await api('import-roster',{...rosterFile,preview:true});
    if($('#roster-file').files[0]!==file)return;
    rosterPreview=preview;
    $('#roster-preview').innerHTML=`<h3>Vista previa · ${rosterPreview.rows} filas</h3><p>${rosterPreview.students} ${rosterPreview.students===1?'alumno válido':'alumnos válidos'} · ${rosterPreview.guardians} ${rosterPreview.guardians===1?'representante nuevo':'representantes nuevos'} · ${rosterPreview.grades} ${rosterPreview.grades===1?'grado nuevo':'grados nuevos'} · cargos nuevos: <b>${usd(rosterPreview.new_balance)}</b>.</p>${rosterPreview.source==='export'?`<div class="notice"><div><b>Exportación completa reconocida</b>Se conservarán códigos, tarifas, fechas y estados. No se importan pagos ni se restaura el saldo anterior. Saldo de origen informativo: ${usd(rosterPreview.source_balance)}; cargos generados aquí: ${usd(rosterPreview.new_balance)}. Revisa el ciclo y las reglas de cobro de esta aplicación.</div></div>`:''}${rosterPreview.errors.length?`<p class="text-red">${rosterPreview.errors.length} errores. No se guardará ninguna fila hasta corregir el archivo.</p>${table(['Fila','Error'],rosterPreview.errors,e=>`<td>${e.row}</td><td class="wrap-cell">${esc(e.message)}</td>`)}`:`<p class="text-green">Sin errores de validación. ${rosterPreview.source==='export'?'Se conservarán los códigos del archivo.':'Los códigos se asignarán al confirmar.'}</p>${table(['Fila','Alumno / código','Representante','Grado','Estado','Cobrar desde'],rosterPreview.lines,r=>`<td>${r.row}</td><td>${esc(r.student_name)}<span class="sub">${esc(r.student_code)}</span></td><td>${esc(r.guardian_name)}</td><td>${esc(r.grade_name)}</td><td>${r.archived?'Inactivo · Archivado':['active','activo'].includes(r.status)?'Activo':'Inactivo'}</td><td>${esc(schoolMonth(r.billing_start))}</td>`)}${rosterPreview.rows>100?'<p>Se muestran las primeras 100 filas; todas fueron validadas.</p>':''}<label class="confirm-check"><input id="import-reviewed" type="checkbox"> Revisé las fechas, las tarifas y los cargos que se crearán.</label><div class="form-actions">${btn('Confirmar importación','confirm-import','primary')}</div>`}`;
  }catch(error){$('#roster-preview').innerHTML=`<div class="notice" role="alert"><div><b>No se importaron datos</b>${esc(error.message)}</div></div>`;}finally{button.disabled=false;}
}
async function confirmImport(){
  if(!rosterPreview||rosterPreview.errors.length||!$('#import-reviewed')?.checked)throw new Error('Revisa la vista previa y marca la confirmación.');
  const button=modal.querySelector('[data-action="confirm-import"]');button.disabled=true;
  try{const result=await api('import-roster',{...rosterFile,confirmed_hash:rosterPreview.hash,confirmed_month:rosterPreview.billing_default});modal.close();page='students';filters={};await refresh();toast(`${result.students} alumnos y ${result.guardians} representantes importados.`);if(result.backup_warning)toast('Importación guardada. '+result.backup_warning,true);}
  finally{button.disabled=false;}
}
function accountFamilyMarkup(d){
  return `<div class="mini-summary"><div><small>Saldo familiar USD</small><b>${usd(d.balance)}</b></div><div><small>Vencido USD</small><b class="text-red">${usd(d.overdue)}</b></div></div>${table(['Alumno / código','Grado','Año escolar','Estado'],d.students,s=>`<td>${esc(s.name)}<span class="sub">${esc(s.student_code)}</span></td><td>${esc(s.grade_name)}</td><td>${s.school_year}–${s.school_year+1}</td><td>${s.archived?'Inactivo · Archivado':s.status==='active'?'Activo':s.status==='inactive'?'Inactivo':'Estado no registrado'}</td>`)}<h3>Cargos de la familia</h3>${table(['Alumno / concepto / período','Vence','Cargo','Abonado','Saldo'],d.charges,c=>`<td>${esc(c.student_name)}<span class="sub">${esc(c.concept)} · ${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td>${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}</td>`,'No hay cargos registrados')}<h3>Pagos registrados</h3>${table(['Recibo / alumno','Fecha','Recibido','Aplicado USD','Estado'],d.payments,p=>`<td>R-${String(p.id).padStart(6,'0')}<span class="sub">${esc(p.student_name)}</span></td><td>${dateLabel(p.paid_on)}</td><td>${p.currency==='VES'?bs(p.received_amount):usd(p.received_amount)}</td><td>${usd(p.amount)}</td><td>${p.voided?'Anulado':'Válido'}</td>`,'Sin pagos registrados')}`;
}
async function guardianAccount(id){
  const d=await api('guardian-account/'+id);
  showModal('Cuenta por representante',`${esc(d.guardian.name)} · ${esc(d.guardian.document)}`,`<div class="actions">${writable()?btn('Emitir estado de cuenta PDF','issue-account','primary',id)+btn('Emitir constancia de solvencia','issue-solvency','',id):''}</div><p class="hint">Incluye todos los alumnos vinculados, incluso inactivos. La solvencia exige saldo cero en todos los cargos registrados, incluidos períodos futuros ya preparados. Los documentos emitidos conservan su corte.</p>${accountFamilyMarkup(d)}<h3>Documentos emitidos</h3>${table(['Documento','Fecha',''],state.guardian_documents.filter(r=>r.guardian_id===Number(id)),r=>`<td>${r.kind==='solvency'?'Solvencia':'Estado de cuenta'} · D-${String(r.id).padStart(6,'0')}</td><td>${dateLabel(r.issued_on)}</td><td>${btn('Ver PDF','guardian-document','small',r.id)}</td>`,'Sin documentos emitidos')}`);
  modal.classList.add('wide-modal');
}
async function issueGuardian(id,kind){
  const button=modal.querySelector(`[data-action="issue-${kind==='account'?'account':'solvency'}"]`);if(button)button.disabled=true;
  try{const r=await api('guardian-documents',{guardian_id:id,kind});await refresh();await guardianDocument(r.id);if(r.backup_warning)toast('Documento guardado. '+r.backup_warning,true);}
  finally{if(button)button.disabled=false;}
}
async function guardianDocument(id){
  const d=await api('guardian-document/'+id),solvent=d.kind==='solvency';
  showDocument(solvent?'Constancia de solvencia':'Estado de cuenta familiar','guardian-document/'+id,`<article class="receipt school-document">${schoolHeader(d.school,solvent?'Constancia de solvencia':'Estado de cuenta','D-'+String(id).padStart(6,'0'),d.issued_on)}<h3>${esc(d.guardian.name)} · ${esc(d.guardian.document)}</h3>${solvent?`<p>Se hace constar que los alumnos vinculados a este representante no presentan saldo pendiente en los cargos registrados al emitir este documento.</p>${table(['Alumno / código','Grado / sección','Año escolar'],d.students,s=>`<td>${esc(s.name)}<span class="sub">${esc(s.student_code)}</span></td><td>${esc(s.grade_name)}</td><td>${s.school_year}–${s.school_year+1}</td>`)}<div class="receipt-total">Saldo pendiente: <b>${usd(d.balance)}</b></div><p class="hint">Incluye mensualidades hasta el mes de emisión y cargos futuros ya registrados. No acredita períodos futuros aún no cargados ni pagos externos sin registrar.</p>`:accountFamilyMarkup(d)}<div class="signature-row"><span>Firma de administración</span><span>Sello del colegio</span></div><p class="document-footer">Emitido por: ${esc(d.operator)} · Corte al ${dateLabel(d.issued_on)}. Conserva los datos de su fecha de emisión.</p></article>`);
  modal.classList.add('wide-modal');
}
const nativeAmount=(c,currency)=>currency==='VES'?bs(c):usd(c);
function cashBreakdown(d){return (d.movements?.some(r=>r.type==='transfer')?'<p class="hint">Los depósitos trasladan efectivo a banco: afectan el neto por método, sin ser ingresos ni egresos nuevos.</p>':'')+table(['Método','Moneda','Ingresos recibidos','Egresos pagados','Neto'],d.lines,r=>`<td>${esc(r.method)}</td><td>${esc(r.currency)}</td><td>${nativeAmount(r.income,r.currency)}</td><td>${nativeAmount(r.expense,r.currency)}</td><td>${nativeAmount(r.net,r.currency)}</td>`,'Sin movimientos en esta fecha');}
function cashPage(){
  cashDate ||=state.today;
  return heading('Cierre de caja diario','Corte guardado por método y moneda, con arqueo de efectivo.',writable()?btn('Revisar / cerrar caja','open-cash','primary'):'')+card('Seleccionar fecha',`<div class="card-body">${field('Fecha del cierre','closed_on',cashDate,'date',`id="cash-date" required max="${state.today}"`)}<p class="hint">Registra primero todos los cobros y egresos del día. Usa el método correcto en los egresos. Un cierre bloquea nuevos movimientos y anulaciones de esa fecha; administración puede reabrirlo con un motivo. Los cierres anteriores se conservan.</p></div>`)+card('Cierres guardados',table(['Fecha cerrada','Emitido','Estado',''],state.cash_closures,c=>`<td>${dateLabel(c.closed_on)}</td><td>${esc(new Date(c.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}</td><td>${badge(c.reopened_at?'Reabierto':'Cerrado',c.reopened_at?'neutral':'')}</td><td>${actionsCell(btn('Ver PDF','cash-document','small',c.id)+(admin()&&!c.reopened_at?btn('Reabrir','reopen-cash','small',c.id):''))}</td>`,'Todavía no hay cierres'));
}
async function openCash(){
  cashDate ||=state.today;
  cashPreview=await api('cash-preview?date='+encodeURIComponent(cashDate));
  if(cashPreview.active_id){await cashDocument(cashPreview.active_id);return;}
  showModal('Revisar y cerrar caja','Los importes reales se mantienen separados por moneda.',`<form data-endpoint="close-cash"><input type="hidden" name="preview_hash" value="${cashPreview.preview_hash}">${field('Fecha del cierre','closed_on',cashDate,'date',`id="cash-close-date" required max="${state.today}"`)}${cashBreakdown(cashPreview)}<p class="hint">Equivalente USD: ingresos ${usd(cashPreview.income_usd)} · egresos ${usd(cashPreview.expense_usd)}. El efectivo se cuenta aparte de pagos móviles, transferencias y tarjetas. Los egresos antiguos sin método aparecen como «No especificado» y no descuentan efectivo.</p><h3>Arqueo de efectivo</h3><p class="hint">El efectivo inicial es el dinero físico que había en caja al comenzar el día, por ejemplo para dar vuelto. No es el saldo de la cuenta bancaria. Al cerrar, cuenta los billetes y monedas. Si no hubo efectivo, registra 0 en ambos campos de esa moneda.</p><div class="form-grid">${field('Efectivo inicial en caja · USD','opening_USD','0.00','number','required min="0" max="999999999" step="0.01"')}${field('Efectivo contado en USD','counted_USD','','number','required min="0" max="999999999" step="0.01"')}${field('Efectivo inicial en caja · Bs','opening_VES','0.00','number','required min="0" max="999999999" step="0.01"')}${field('Efectivo contado en Bs','counted_VES','','number','required min="0" max="999999999" step="0.01"')}${textarea('Observaciones / explicación de diferencias','notes')}</div><div id="cash-count-preview" class="conversion" aria-live="polite"></div>${formFoot('Cerrar caja y emitir PDF')}</form>`);
  modal.classList.add('wide-modal');updateCashCount();
}
function updateCashCount(){
  const form=$('form[data-endpoint="close-cash"]',modal);if(!form||!cashPreview)return;
  $('#cash-count-preview').innerHTML=['USD','VES'].map(currency=>{const initial=Math.round(Number(form.elements['opening_'+currency].value||0)*100),expected=initial+cashPreview.lines.filter(r=>r.currency===currency&&r.method==='Efectivo').reduce((a,r)=>a+r.net,0),input=form.elements['counted_'+currency],counted=Math.round(Number(input.value||0)*100);return `<p>Efectivo esperado: <b>${nativeAmount(expected,currency)}</b> · Diferencia: ${input.value?nativeAmount(counted-expected,currency):'pendiente de contar'}</p>`;}).join('');
}
async function cashDocument(id){
  const d=await api('cash-close/'+id);
  showDocument('Cierre de caja','cash-close/'+id,`<article class="receipt school-document">${schoolHeader(d.school,'Cierre de caja','C-'+String(id).padStart(6,'0'),d.closed_on)}${d.reopened_at?`<div class="receipt-void"><b>CIERRE REABIERTO</b><p>${esc(d.reopen_reason)}</p></div>`:''}${cashBreakdown(d)}<h3>Arqueo de efectivo</h3>${table(['Moneda','Efectivo inicial','Esperado','Contado','Diferencia'],d.counts,r=>`<td>${esc(r.currency)}</td><td>${nativeAmount(r.opening,r.currency)}</td><td>${nativeAmount(r.expected,r.currency)}</td><td>${nativeAmount(r.counted,r.currency)}</td><td>${nativeAmount(r.difference,r.currency)}</td>`)}<p>Equivalente USD: ingresos ${usd(d.income_usd)} · egresos ${usd(d.expense_usd)}.</p><p class="hint">Arqueo = efectivo inicial + cobros en efectivo - egresos en efectivo. El saldo bancario, pagos móviles, transferencias, tarjetas y egresos sin método se presentan aparte.</p><p>Observaciones: ${esc(d.notes)||'Sin observaciones.'}</p><h3>Movimientos del corte</h3>${table(['Movimiento / referencia','Método','Recibido','Estado'],d.movements,r=>`<td>${r.type==='income'?'R':'E'}-${String(r.id).padStart(6,'0')}<span class="sub">${esc(r.reference)}</span></td><td>${esc(r.method)}</td><td>${nativeAmount(r.received_amount,r.currency)}</td><td>${r.voided?'Anulado':'Válido'}</td>`)}<div class="signature-row"><span>Firma de administración</span><span>Revisado por</span></div><p class="document-footer">Cerrado por ${esc(d.operator)} · Fecha de emisión: ${dateLabel(d.issued_on)}. Conserva el corte original.</p></article>`);
  modal.classList.add('wide-modal');
}
function checkReference(form){
  const panel=$('#duplicate-reference',form);if(!panel)return;
  const key=form.elements.reference.value.toUpperCase().replace(/\s/g,''),current=panel.dataset.reference;
  if(current===key)return;panel.dataset.reference=key;
  const matches=state.payments.filter(p=>!p.voided&&key&&p.reference.toUpperCase().replace(/\s/g,'')===key);
  panel.innerHTML=matches.length?`<div class="notice backup-warning"><div><b>Referencia ya registrada</b><p>${matches.map(p=>`R-${String(p.id).padStart(6,'0')} · ${esc(p.student_name)} · ${dateLabel(p.paid_on)}`).join('<br>')}</p><label class="confirm-check"><input name="duplicate_reference_confirmed" type="checkbox" required> Revisé los recibos y corresponde registrar esta referencia otra vez.</label>${field('Motivo de referencia repetida','duplicate_reason','','text','required maxlength="500"')}</div></div>`:'';
}
function schoolPeriod(year){
  const month=Number(state.settings.start_month),last=new Date(year+1,month-1,0,12);
  return {start:`${year}-${String(month).padStart(2,'0')}-01`,end:`${last.getFullYear()}-${String(last.getMonth()+1).padStart(2,'0')}-${String(last.getDate()).padStart(2,'0')}`};
}
function openYearTransition(){
  yearCohort=yearPreview=yearRequest=undefined;
  showModal('Pase masivo de año y grados','Administración revisa cada destino. Se conservan cargos, pagos, recibos y constancias anteriores.',`${field('Año de origen (año de inicio)','source_year',Number(state.settings.school_year),'number','id="source-year" required min="2000" max="2099"')}<div class="actions">${btn('Cargar alumnos del año','load-year','primary')}</div><div id="year-roster"></div><h3>Pases guardados</h3>${table(['Origen','Destino','Fecha',''],state.year_transitions,r=>`<td>${r.source_year}–${r.source_year+1}</td><td>${r.target_year}–${r.target_year+1}</td><td>${dateLabel(r.issued_on)}</td><td>${btn('Ver acta','year-document','small',r.id)}</td>`,'Sin pases de año registrados')}`);
  modal.classList.add('wide-modal');
}
async function loadYear(){
  const year=Number($('#source-year').value);yearCohort=await api('year-roster?year='+year);yearPreview=undefined;
  if(!yearCohort.students.length){$('#year-roster').innerHTML=empty('No hay alumnos en ese año');return;}
  const target=year+1,period=schoolPeriod(target),old=schoolPeriod(year),gradeIds=[...new Set(yearCohort.students.map(s=>s.grade_id))];
  $('#year-roster').innerHTML=`<h3>Del año ${year}–${target} al ${target}–${target+1}</h3><div class="form-grid">${field('Fecha real de cierre del curso','closed_on',old.end,'date',`id="year-closed" required max="${state.today}"`)}${field('Inicio de nueva matrícula','enrollment_start',period.start,'date','id="year-start" required')}${field('Fin de nueva matrícula','enrollment_end',period.end,'date','id="year-end" required')}</div><h3>Destinos por grado</h3><p class="hint">Crea los grados de destino antes del pase. La selección se aplica a quienes avanzan; puedes cambiar el destino individual. Los repitentes se matriculan en el nuevo año en su mismo grado. Los retirados permanecen en su año anterior y quedan inactivos.</p><div class="form-grid">${gradeIds.map(gid=>select(state.grades.find(g=>g.id===gid).name,'map-'+gid,[['','Elige el siguiente grado'],...state.grades.map(g=>[g.id,g.name])],'',`data-map-grade="${gid}"`)).join('')}</div>${table(['Alumno / grado actual','Decisión','Destino individual','Nueva base USD'],yearCohort.students,s=>`<td>${esc(s.name)}<span class="sub">${esc(s.student_code)} · ${esc(s.grade_name)}</span></td><td><select data-year-action="${s.id}" aria-label="Decisión de ${esc(s.name)}">${[['promote','Avanza'],['repeat','Repite'],['withdraw','Retirado'],['skip','Sin cambios']].map(o=>`<option value="${o[0]}" ${s.status==='inactive'&&o[0]==='withdraw'?'selected':''}>${o[1]}</option>`).join('')}</select></td><td><select data-year-grade="${s.id}" aria-label="Destino de ${esc(s.name)}"><option value="">Usar destino del grado</option>${state.grades.map(g=>`<option value="${g.id}">${esc(g.name)}</option>`).join('')}</select></td><td><input data-year-fee="${s.id}" aria-label="Nueva mensualidad de ${esc(s.name)}" type="number" min="0" max="999999999" step="0.01" value="${(s.monthly_fee/100).toFixed(2)}"></td>`)}<div class="notice"><div><b>El cierre afecta matrículas nuevas, no borra deudas</b>Las mensualidades del año anterior ya registradas se mantienen. Al avanzar o repetir se termina su matrícula anterior y se dejan de generar meses posteriores de ese año. Revisa la fecha real de cierre y las mensualidades antes de confirmar.</div></div><div class="actions">${btn('Revisar pase de año','preview-year','primary')}</div><div id="year-preview" aria-live="polite"></div>`;
}
function collectYearRequest(){
  if(!yearCohort)throw new Error('Carga primero los alumnos.');
  return {source_year:yearCohort.source_year,target_year:yearCohort.source_year+1,roster_hash:yearCohort.preview_hash,
    closed_on:$('#year-closed').value,enrollment_start:$('#year-start').value,enrollment_end:$('#year-end').value,
    lines:yearCohort.students.map(s=>{const action=$(`[data-year-action="${s.id}"]`).value,grade=$(`[data-year-grade="${s.id}"]`).value||$(`[data-map-grade="${s.grade_id}"]`).value;
      if(action==='promote'&&!grade)throw new Error('Selecciona el grado de destino para '+s.name);
      return {student_id:s.id,action,grade_id:action==='promote'?grade:s.grade_id,monthly_fee:$(`[data-year-fee="${s.id}"]`).value};})};
}
async function previewYear(){
  yearRequest=collectYearRequest();yearPreview=await api('transition-year',{...yearRequest,preview:true});
  const labels={promote:'Avanza',repeat:'Repite',withdraw:'Retirado',skip:'Sin cambios'};
  $('#year-preview').innerHTML=`<h3>Vista previa del pase</h3>${yearPreview.errors.length?`<div class="text-red">${yearPreview.errors.map(esc).join('<br>')}</div>`:`${table(['Alumno','Decisión','Grado anterior','Nuevo grado'],yearPreview.lines,r=>`<td>${esc(r.student_name)}</td><td>${labels[r.action]}</td><td>${esc(r.source_grade)}</td><td>${r.action==='promote'||r.action==='repeat'?esc(r.target_grade):'—'}</td>`)}<label class="confirm-check"><input id="year-reviewed" type="checkbox"> Confirmo los destinos, repitentes, retirados, fechas y tarifas. El año anterior terminó.</label><div class="form-actions">${btn('Aplicar pase de año','confirm-year','primary')}</div>`}`;
}
async function confirmYear(){
  if(!yearPreview||yearPreview.errors.length||!$('#year-reviewed')?.checked)throw new Error('Revisa el pase y marca la confirmación.');
  const latest=collectYearRequest();if(JSON.stringify(latest)!==JSON.stringify(yearRequest))throw new Error('Cambiaste la selección. Revisa de nuevo la vista previa.');
  const button=modal.querySelector('[data-action="confirm-year"]');button.disabled=true;
  try{const r=await api('transition-year',{...latest,confirmed_hash:yearPreview.hash});await refresh();toast(`${r.changed} matrículas actualizadas. Se conservaron los movimientos anteriores.`);await yearDocument(r.id);if(r.backup_warning)toast(r.backup_warning,true);}
  finally{button.disabled=false;}
}
async function yearDocument(id){
  const d=await api('year-transition/'+id),labels={promote:'Avanza',repeat:'Repite',withdraw:'Retirado',skip:'Sin cambios'};
  showDocument('Acta de pase de año','year-transition/'+id,`<article class="receipt school-document">${schoolHeader(d.school,'Pase de año','A-'+String(id).padStart(6,'0'),d.issued_on)}<h3>Año ${d.source_year}–${d.source_year+1} → ${d.target_year}–${d.target_year+1}</h3><p>Fecha de cierre del curso: ${dateLabel(d.closed_on)} · Matrícula nueva: ${dateLabel(d.enrollment_start)} al ${dateLabel(d.enrollment_end)}</p>${table(['Alumno / código','Decisión','Origen','Destino / base USD'],d.lines,r=>`<td>${esc(r.student_name)}<span class="sub">${esc(r.source.student_code)}</span></td><td>${labels[r.action]}</td><td>${esc(r.source_grade)}</td><td>${r.action==='promote'||r.action==='repeat'?esc(r.target_grade)+'<span class="sub">'+usd(r.monthly_fee)+'</span>':'—'}</td>`)}<p class="hint">El acta conserva el destino aprobado y la matrícula anterior. Se mantienen los cargos, abonos, pagos, recibos y constancias ya emitidos.</p><div class="signature-row"><span>Administración</span><span>Dirección</span></div><p>Emitido por: ${esc(d.operator)}</p></article>`);modal.classList.add('wide-modal');
}
function planLinks(studentId){
  const plans=state.payment_plans.filter(p=>p.student.id===Number(studentId));
  return plans.length?`<h3>Convenios</h3>${table(['Convenio','Deuda convenida','Pendiente','Estado',''],plans,p=>`<td>P-${String(p.id).padStart(6,'0')}</td><td>${usd(p.total)}</td><td>${usd(p.balance)}</td><td>${p.cancelled?'Cancelado':p.balance?'En curso':'Cumplido'}</td><td>${btn('Ver','plan-document','small',p.id)+(admin()&&!p.cancelled?btn('Cancelar','cancel-plan','small',p.id):'')}</td>`)}`:'';
}
function openPaymentPlan(id){
  const s=state.students.find(s=>s.id===Number(id));if(!s?.overdue)throw new Error('El alumno no tiene deuda vencida.');
  showModal('Convenio de pago',`${esc(s.name)} · ${esc(s.guardian_name)}`,`<form data-endpoint="payment-plans"><input type="hidden" name="student_id" value="${s.id}"><input type="hidden" name="expected_total" value="${s.overdue}"><p>Deuda vencida a convenir: <b>${usd(s.overdue)}</b>.</p><p class="hint">El convenio organiza la deuda existente; no crea cargos nuevos ni borra la mora. Los cobros habituales se aplican a la deuda más antigua y actualizan el cumplimiento de las cuotas. Anular un pago vuelve a mostrar la cuota pendiente.</p>${field('Cantidad de cuotas','count','3','number','id="plan-count" min="1" max="60" required')}<div id="plan-rows"></div>${textarea('Condiciones / observaciones','notes')}${formFoot('Guardar convenio y emitir PDF')}</form>`);buildPlanRows();
}
function buildPlanRows(){
  const form=$('form[data-endpoint="payment-plans"]',modal);if(!form)return;
  const count=Number($('#plan-count').value),total=Number(form.elements.expected_total.value);
  if(!Number.isInteger(count)||count<1||count>60)return;
  const base=Math.floor(total/count);let remaining=total;
  $('#plan-rows').innerHTML=Array.from({length:count},(_,i)=>{const value=i===count-1?remaining:base;remaining-=value;const date=new Date(state.today+'T12:00:00');date.setDate(date.getDate()+30*i);const iso=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;return `<div class="form-grid" data-plan-row>${field(`Cuota ${i+1} · fecha`,'date-'+i,iso,'date',`data-plan-date required min="${state.today}"`)}${field(`Cuota ${i+1} · USD`,'amount-'+i,(value/100).toFixed(2),'number','data-plan-amount required min="0.01" max="999999999" step="0.01"')}</div>`;}).join('');
}
async function planDocument(id){
  const d=await api('payment-plan/'+id),live=state.payment_plans.find(p=>p.id===Number(id));
  showDocument('Convenio de pago','payment-plan/'+id,`<article class="receipt school-document">${schoolHeader(d.school,'Convenio de pago','P-'+String(id).padStart(6,'0'),d.issued_on)}${d.cancelled?`<div class="receipt-void"><b>CONVENIO CANCELADO</b><p>${esc(d.cancel_reason)}</p></div>`:''}<h3>${esc(d.student.name)} · ${esc(d.student.grade_name)}</h3><p>Representante: ${esc(d.student.guardian_name)} · ${esc(d.student.guardian_document)}</p><div class="receipt-total">Deuda original convenida: <b>${usd(d.total)}</b></div>${table(['Cuota','Vencimiento','Monto USD'],d.installments,r=>`<td>${r.number}</td><td>${dateLabel(r.due_date)}</td><td>${usd(r.amount)}</td>`)}<p>${esc(d.notes)}</p><p class="hint">Este acuerdo organiza cargos existentes, no registra pagos ni genera deuda adicional. Conserva sus condiciones originales. La mora se mantiene según los cargos hasta saldarlos.</p><div class="signature-row"><span>Administración</span><span>Representante legal</span></div><p>Emitido por ${esc(d.operator)}</p></article>`);
  if(live&&!live.cancelled){const box=document.createElement('section');box.innerHTML=`<h3>Cumplimiento actual · pendiente ${usd(live.balance)}</h3>${table(['Cuota','Fecha','Pagado','Pendiente','Estado'],live.installments,r=>`<td>${r.number}</td><td>${dateLabel(r.due_date)}</td><td>${usd(r.paid)}</td><td>${usd(r.balance)}</td><td>${r.balance?(r.overdue?'Vencida':'Pendiente'):'Pagada'}</td>`)}`;modal.querySelector('.modal-body').append(box);}
}

function isoDay(date){return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;}
function dashboardActivity(){
  if(state.dashboard&&!state.history_loaded)return {due:state.dashboard.due,newDebtors:{length:state.dashboard.new_debtors},paid:[]};
  const today=state.today,end=new Date(today+'T12:00:00'),start=new Date(today+'T12:00:00');end.setDate(end.getDate()+6);start.setDate(start.getDate()-7);
  const due=state.charges.filter(c=>c.balance>0&&c.due_date>=today&&c.due_date<=isoDay(end)).sort((a,b)=>a.due_date.localeCompare(b.due_date)||a.id-b.id);
  const newDebtors=state.students.filter(s=>{const overdue=state.charges.filter(c=>c.student_id===s.id&&c.overdue);return overdue.length&&overdue.every(c=>c.due_date>=isoDay(start));});
  const paid=state.payments.filter(p=>!p.voided&&p.paid_on===today);
  return {due,newDebtors,paid};
}
function dashboardOverview({due,newDebtors,paid}){
  const otherToday=(state.other_income||[]).filter(r=>!r.voided&&r.received_on===state.today),allToday=paid.concat(otherToday);
  const s=state.summary,amount=state.dashboard&&!state.history_loaded?state.dashboard.income:allToday.reduce((sum,p)=>sum+p.amount,0);
  const paidCount=state.dashboard&&!state.history_loaded?state.dashboard.payment_count:paid.length;
  const dueCount=state.dashboard&&!state.history_loaded?state.dashboard.due_count:due.length;
  const dueTotal=state.dashboard&&!state.history_loaded?state.dashboard.due_total:due.reduce((sum,c)=>sum+c.balance,0);
  const dollars=state.dashboard&&!state.history_loaded?state.dashboard.dollars:allToday.filter(p=>p.currency==='USD').reduce((sum,p)=>sum+p.received_amount,0);
  const bolivars=state.dashboard&&!state.history_loaded?state.dashboard.bolivars:allToday.filter(p=>p.currency==='VES').reduce((sum,p)=>sum+p.received_amount,0);
  return `<section class="dashboard-overview" aria-label="Resumen de cobros y deudas">
    <div class="dashboard-main-metrics">
      <div class="dashboard-collected">
        <div class="dashboard-metric-label">${icon('payments')}<h2>Cobrado hoy</h2><span class="dashboard-today-tag">Hoy</span></div>
        <div class="dashboard-amount" id="dashboard-today">${usd(amount)}</div>
        <p class="dashboard-unit">Equivalente en USD · ${paidCount} ${paidCount===1?'cobro':'cobros'}</p>
        <p class="dashboard-received">Recibido: <b>${usd(dollars)}</b> y <b>${bs(bolivars)}</b></p>
      </div>
      <div class="dashboard-overdue">
        <div class="dashboard-metric-label">${icon(s.overdue?'arrears':'check')}<h2>Deuda vencida</h2></div>
        <div class="dashboard-amount ${s.overdue?'text-red':''}">${usd(s.overdue)}</div>
        <p class="dashboard-unit">${s.debtors ? `${s.debtors} ${s.debtors===1?'alumno con pagos atrasados':'alumnos con pagos atrasados'}` : 'No hay pagos atrasados'}</p>
        ${btn(s.overdue?'Ver cuentas por atender →':'Consultar morosidad →','nav','ghost dashboard-link','arrears')}
      </div>
    </div>
    <dl class="dashboard-context">
      <div><dt>Cobrado este mes</dt><dd>${usd(s.income)} <small>USD · ${monthLabel(state.today.slice(0,7))}</small></dd></div>
      <div><dt>Saldo pendiente total</dt><dd>${usd(s.pending)} <small>USD · vencido y por vencer</small></dd></div>
      <div><dt>Alumnos activos</dt><dd>${s.active_students} <small>matrículas activas</small></dd></div>
    </dl>
  </section>
  <div class="dashboard-alerts" aria-label="Seguimiento de la semana">
    <button type="button" class="dashboard-alert" data-action="nav" data-id="billing">
      ${icon('clock')}<span><b>Vencen en los próximos 7 días</b><small>${dueCount ? `${dueCount} ${dueCount===1?'cargo pendiente':'cargos pendientes'} · ${usd(dueTotal)} USD` : 'Sin vencimientos pendientes esta semana'}</small></span>${icon('arrow')}
    </button>
    <button type="button" class="dashboard-alert" data-action="nav" data-id="arrears" title="Alumnos cuya primera deuda actualmente vencida corresponde a los últimos 7 días">
      ${icon('arrears')}<span><b>Morosos nuevos</b><small>${newDebtors.length ? `${newDebtors.length} ${newDebtors.length===1?'alumno nuevo':'alumnos nuevos'} en mora en los últimos 7 días` : 'Sin nuevos alumnos en mora en los últimos 7 días'}</small></span>${icon('arrow')}
    </button>
  </div>`;
}
function dashboardUpcoming(due){
  return due.length ? card('Vencimientos de esta semana',`<div class="dashboard-upcoming">${table(['Alumno / grado','Vence','Saldo USD'],due.slice(0,5),c=>`<td><button class="btn ghost" data-action="account" data-id="${c.student_id}">${esc(c.student_name)}</button><span class="sub">${esc(c.grade_name)} · ${esc(c.concept)} · ${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td class="money">${usd(c.balance)}</td>`)}</div>`,btn('Ver cargos →','nav','ghost','billing')) : '';
}

function whatsappLink(phone,text){
  let digits=String(phone||'').replace(/\D/g,'');if(digits.length===11&&digits[0]==='0')digits='58'+digits.slice(1);else if(digits.length===10)digits='58'+digits;
  if(!/^58\d{10}$/.test(digits))return '<small>Completa un teléfono venezolano válido para abrir WhatsApp.</small>';
  return `<a id="wa-collection" class="btn" href="https://wa.me/${digits}?text=${encodeURIComponent(text)}" target="_blank" rel="noopener noreferrer">Abrir WhatsApp con el aviso</a>`;
}

function demoBanner(){
  if(!demoMode)return '';
  return `<aside class="demo-banner" aria-label="Modo prueba"><div><b>Modo prueba · Datos temporales</b><p>Todo lo que registres aquí se elimina al cerrar. Los datos reales del colegio están separados.</p></div>${btn('Cerrar y borrar pruebas','demo-exit','small')}</aside>`;
}
function demoAuth(){
  state=undefined;modal.close();$('#print-area').replaceChildren();document.title='Modo prueba · Aula';
  app.innerHTML=demoBanner()+`<div class="rate-screen"><section class="card gate-card"><div id="backup-alerts" class="backup-alerts">${backupProblem()}</div><div class="brand"><img src="/aula-app.png" alt="Logo del colegio"><div><b>Tu colegio, en modo prueba</b><small>Datos temporales · acceso de administrador</small></div></div><h1>Prueba con tranquilidad</h1><p>Esta sesión empieza sin alumnos, cobros ni egresos. Puedes probar todos los módulos. Los documentos descargados se identifican como pruebas.</p><form data-endpoint="demo-login"><div class="error" role="alert"></div><button class="btn primary" type="submit">Entrar como administrador de prueba ${icon('arrow')}</button></form><p class="hint">Al cerrar la última pestaña de prueba, espera unos segundos: se cerrará la sesión y se eliminarán sus registros. Descargar un PDF guarda ese archivo en tu PC; puedes borrarlo después.</p></section></div>`;
}
function configureDemo(result){
  demoMode=!!result.demo;demoToken=result.demo_token||'';
  if(demoMode&&!demoTimer){pulseDemo();demoTimer=setInterval(pulseDemo,15000);}
}
function pulseDemo(){
  if(demoToken)fetch('/api/demo-presence',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:demoToken,client:demoClient,action:'alive'})}).catch(()=>{});
}
async function closeDemo(){
  if(!demoMode)return;
  if(session)await api('demo-exit',{});
  else await api('demo-presence',{token:demoToken,client:demoClient,action:'close'});
  clearInterval(demoTimer);demoTimer=undefined;demoToken='';state=undefined;session=undefined;modal.close();$('#print-area').replaceChildren();
  app.innerHTML=`<div class="rate-screen"><section class="card gate-card"><h1>Sesión de prueba terminada</h1><p>Se está cerrando el programa y eliminando sus datos temporales. Para empezar otra prueba vacía, vuelve a abrir <b>Aula - Pruebas</b>. Si usas el ZIP de código fuente, ejecuta <b>Iniciar-Pruebas.bat</b>.</p><p class="hint">Ya puedes cerrar esta pestaña. Los PDF o CSV que descargaste permanecen en tu carpeta de descargas.</p></section></div>`;
}
window.addEventListener('pagehide',()=>{
  if(demoToken)navigator.sendBeacon('/api/demo-presence',new Blob([JSON.stringify({token:demoToken,client:demoClient,action:'close'})],{type:'application/json'}));
});
window.addEventListener('pageshow',pulseDemo);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)pulseDemo();});

function receiptBalance(p) {
  if(p.balance_after===null||p.balance_after===undefined)return '<p class="receipt-balance-note">Recibo histórico: no se guardó el saldo al emitirlo.</p>';
  return `<section class="receipt-balance"><div><b>${p.balance_after?'Abono recibido':'Pago completo de cargos registrados'}</b><span>Deuda anterior: ${usd(p.balance_before)} · Aplicado: ${usd(p.amount)}</span></div><div><span>Saldo pendiente del alumno</span><strong>${usd(p.balance_after)}</strong></div></section><p class="receipt-balance-note">Saldo al registrar este cobro. Puede incluir otros meses; no acredita solvencia ni cambia con pagos posteriores.</p>`;
}
function recoveryHelp(){showModal('Recuperar acceso','Sin borrar los registros del colegio.',`<ol class="help-steps"><li>Si otro administrador puede entrar, pídele cambiar tu contraseña en Configuración → Usuarios.</li><li>Si nadie puede entrar, cierra Aula completamente: menú junto al reloj → Salir y cerrar Aula.</li><li>En Inicio de Windows busca <b>Recuperar clave del administrador</b>. Se mostrarán los nombres y usuarios de administradores de esta base.</li><li>Elige tu usuario y escribe dos veces la nueva contraseña, con al menos 10 caracteres.</li><li>Se crea un respaldo previo y se cierran todas las sesiones. Los administradores verán un aviso al entrar. Abre Aula de nuevo.</li></ol><p class="hint">La recuperación es local y requiere acceso a esta cuenta de Windows. Protege la cuenta y el equipo. Los administradores también pueden cambiar las claves de Caja y Consulta.</p>`);}
function maintenanceHelp(){showModal('Mantener Aula sin perder datos','Actualización, respaldo y restauración.',`<ol class="help-steps"><li>Antes de actualizar: crea y descarga un respaldo desde Configuración. Guarda una copia fuera de este disco.</li><li>Cierra Aula completamente desde su icono junto al reloj. Instala la nueva versión con la misma cuenta de Windows. No uses Vaciar registros para actualizar.</li><li>Abre Aula y verifica alumnos, saldos y cobros recientes. La actualización modifica el programa, conserva tus datos y realiza un respaldo previo.</li><li>Para recuperar datos: cierra Aula y abre <b>Restaurar respaldo</b> desde Inicio. Selecciona el archivo .aulabak (o .sqlite3 antiguo). Si está cifrado, usa su contraseña o clave de recuperación; revisa la comparación y escribe la confirmación indicada.</li><li>El respaldo reemplaza la base completa, incluidos usuarios. Los cobros posteriores a esa copia no estarán en ella. Se conserva el estado previo a la restauración cuando es recuperable.</li><li>Si aparece un error, conserva la carpeta de datos y los respaldos. No copies una base activa ni borres archivos SQLite, WAL o SHM para intentar arreglarlo.</li></ol><h3>Enviar información diaria</h3><p>Si solo necesitan consultar pagos y morosidad, usa Reportes → Reporte diario PDF → Descargar PDF y envíalo por correo. El colegio abre o imprime el documento sin restaurar datos. Vuelve a generarlo si registraste movimientos después; el corte es la fecha y hora del PDF. Conserva también los respaldos completos.</p><h3>Llevar datos a otra PC</h3><p>Configuración → Crear respaldo ahora → Descargar copia. Lleva el archivo cifrado .aulabak en un USB o envíalo por correo. Necesitarás su contraseña o clave de recuperación para abrirlo. Nunca copies los respaldos locales .sqlite3 sin cifrar al USB o la nube. Si llegó en ZIP, extráelo antes de restaurar. El instalador solo hace falta para instalar o actualizar el programa. En la otra PC instala la misma versión o una más reciente, cierra Aula y usa Inicio → Restaurar respaldo. Entra con el mismo usuario y contraseña de Aula; revisa saldos y la ruta de la segunda copia.</p><p><b>Las dos PC quedan independientes.</b> No se sincronizan ni se fusionan los cambios. Si trabajas desde casa y envías una copia cada 2 o 3 días, registra los cambios reales solo allí y utiliza un usuario Consulta en el colegio. Crea ese usuario en casa antes de descargar la copia. Restaurar reemplaza todos los datos de la PC de destino; guarda primero una copia de ellos.</p><p class="hint">Con cortes de electricidad, usa un UPS y configura la segunda carpeta de copias. Las pruebas son independientes: abre «Aula - Pruebas» para experimentar.</p>`);}
async function maintenanceReview(){const d=await api('maintenance-review');showModal('Verificación de datos',d.ok?'No se encontraron inconsistencias en los controles realizados.':'Se encontraron inconsistencias; conserva un respaldo y solicita revisión.',`<div class="verification-result ${d.ok?'ok':'problem'}">${icon(d.ok?'check':'arrears')}<b>${d.ok?'Comprobaciones correctas':'Requiere revisión'}</b></div>${d.errors.length?'<ul>'+d.errors.map(e=>'<li>'+esc(e)+'</li>').join('')+'</ul>':''}<p>Integridad SQLite, relaciones entre registros, aplicaciones de cobros válidos, saldos, cargos repetidos, numeración reservada, mensualidades y cadena de la bitácora.</p><p>Modo SQLite: <b>${esc(d.journal_mode)}</b> · Sincronización: <b>${d.synchronous===2?'FULL':esc(d.synchronous)}</b></p>${table(['Registro','Cantidad'],Object.entries(d.counts),r=>`<td>${esc(({students:'Alumnos',guardians:'Representantes',charges:'Cargos',payments:'Cobros',expenses:'Egresos',users:'Usuarios'})[r[0]])}</td><td>${r[1]}</td>`)}<p class="hint">${esc(d.message)}</p>`);}
async function backupNow(){const d=await api('backup-now',{});await refresh();if(d.local_error||d.secondary_error)throw new Error(d.local_error||d.secondary_error);toast('Respaldo verificado creado'+(d.secondary_at?' y copiado al segundo destino.':'.'));}
async function openImportGuide(){const g=await api('import-guide');showModal('Cómo llenar la plantilla de alumnos','Una fila por alumno. Importa solo la hoja Alumnos.',`<ol class="help-steps">${g.steps.map(t=>'<li>'+esc(t)+'</li>').join('')}</ol>${table(['Columna','Obligatoria','Qué escribir','Ejemplo'],g.fields,r=>`<td><b>${esc(r[0])}</b></td><td>${esc(r[1])}</td><td class="wrap-cell">${esc(r[2])}</td><td class="wrap-cell">${esc(r[3])||'Dejar vacío'}</td>`)}<div class="form-actions">${btn('Volver a la importación','import-roster','primary')}</div>`);modal.classList.add('wide-modal');}
document.addEventListener('change',async event=>{
  if(event.target.id!=='school-logo-file')return;
  const file=event.target.files[0],form=event.target.closest('form');if(!file)return;
  try{
    if(!['image/png','image/jpeg'].includes(file.type)||file.size>5000000)throw new Error('Selecciona un PNG o JPG de hasta 5 MB.');
    const image=await createImageBitmap(file),scale=Math.min(1,512/Math.max(image.width,image.height));
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.width*scale));canvas.height=Math.max(1,Math.round(image.height*scale));
    const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);image.close();
    const logo=canvas.toDataURL('image/png');if(logo.length>700000)throw new Error('La imagen es demasiado compleja; utiliza un logo más pequeño.');
    form.elements.logo.value=logo;$('#logo-preview',form).innerHTML=schoolLogo({logo});
    toast('Logo preparado. Pulsa Guardar cambios del colegio para aplicarlo.');
  }catch(e){toast(e.message,true);}
});

function openProbeBackup(){
  showModal('Probar respaldo','Revisión en una copia temporal. No restaura ni genera mensualidades.',`<p>Selecciona una copia .aulabak o una antigua .sqlite3. El original no se modifica. Convertir crea otra copia cifrada y conserva el archivo anterior.</p><label class="field">Respaldo<input id="probe-backup-file" type="file" accept=".sqlite3,.aulabak"></label><div class="form-grid">${select('Abrir copia con','probe_kind',[['password','Contraseña del respaldo'],['recovery','Clave de recuperación']],'password')}${field('Contraseña o clave de la copia seleccionada','probe_credential','','password','autocomplete="off" maxlength="256"','Déjala vacía si seleccionaste un respaldo antiguo sin cifrar.')} </div><p class="hint">Hasta 32 MB aquí. Para una copia mayor, usa Probar respaldo desde Inicio de Windows.</p><div class="actions">${btn('Comprobar copia','run-probe-backup','primary')}${demoMode?'':btn('Convertir y descargar cifrado','convert-backup')}</div><label class="confirm-check"><input type="checkbox" id="probe-external"> Seleccioné una copia del segundo destino, USB o nube.</label><div id="probe-result" role="status"></div>`);
}
function externalEncryptionLabel(b){
  if(!b?.secondary_at)return 'Última copia externa: sin copia confirmada.';
  return 'Última copia externa: '+(b.secondary_encrypted===true?'cifrada y verificada.':b.secondary_encrypted===false?'sin cifrar.':'no se pudo comprobar el cifrado de esta copia anterior.');
}
function cryptoSettingsCard(){
  const c=state.backup?.crypto||{};
  return card('Cifrado de respaldos',`<div class="card-body"><p><b>${esc(c.message||'Cifrado pendiente de configurar.')}</b></p><p>Protege las copias que salen de esta PC. Las copias locales siguen sin cifrar y dependen de BitLocker y de los permisos de Windows.</p><p class="hint">La contraseña nueva afecta solo a las copias nuevas. Las anteriores necesitan su contraseña de entonces o la clave de recuperación.</p><div class="actions">${btn(c.configured?'Cambiar contraseña de respaldos':'Configurar cifrado','crypto-open','primary')}${c.configured&&!c.ready?btn('Desbloquear cifrado','crypto-unlock'):''}</div>${c.recovery_id?`<p class="hint">Identificador de recuperación: ${esc(c.recovery_id)}. La clave no se puede volver a mostrar.</p>`:''}</div>`);
}
function openCryptoSetup(){
  showModal('Cifrado de respaldos','Una contraseña distinta de la de entrar a Aula y de BitLocker.',`<div class="form-grid">${field('Nueva contraseña de respaldos','crypto_password','','password','minlength="12" maxlength="256" autocomplete="new-password"')}${field('Repetir contraseña de respaldos','crypto_repeat','','password','minlength="12" maxlength="256" autocomplete="new-password"')}</div><p>Mínimo 12 caracteres. Usa una frase larga y guárdala en tu gestor de contraseñas.</p><p class="hint">Cambiarla protege solo copias nuevas. La clave de recuperación existente se conserva.</p><p class="text-red">Si pierdes la contraseña y la clave de recuperación de una copia, esa copia NO podrá recuperarse.</p><div class="actions">${btn('Preparar protección','crypto-prepare','primary')}</div>`);
}
async function prepareCrypto(){
  const password=modal.querySelector('[name=crypto_password]').value,repeat=modal.querySelector('[name=crypto_repeat]').value;
  const button=$('[data-action="crypto-prepare"]',modal);button.disabled=true;
  try{
    const p=await api('crypto-prepare',{password,repeat});
    showModal(p.changing?'Confirmar cambio de contraseña':'Guarda tu clave de recuperación','La protección no cambia hasta confirmar.',`<div id="crypto-pending" data-token="${esc(p.token)}"></div>${p.recovery?`<p>Esta clave se muestra <b>una sola vez</b>. Imprímela o guárdala fuera de esta PC y separada del respaldo.</p><div class="notice"><div><b>Clave de recuperación de Aula</b><p id="crypto-recovery" style="font:18px/1.8 monospace;overflow-wrap:anywhere">${esc(p.recovery)}</p></div></div><p class="hint">Imprimir usa la cola de Windows. No guardes un PDF de esta clave en esta PC ni en la carpeta de respaldos.</p>${btn('Imprimir clave','crypto-print')}${field('Últimos 4 caracteres de la clave','crypto_confirmation','','text','maxlength="4" autocomplete="off"')}`:`<p>La contraseña nueva afecta solo copias nuevas. Las anteriores mantienen su contraseña de entonces; la clave de recuperación existente sigue sirviendo.</p>${field('Escribe CAMBIAR CONTRASEÑA DE RESPALDOS','crypto_confirmation','','text','autocomplete="off"')}`}<p class="text-red">Sin contraseña ni clave de recuperación, esos respaldos NO se pueden recuperar.</p><div class="actions">${btn(p.changing?'Confirmar cambio':'Guardé la clave · activar cifrado','crypto-confirm','primary')}</div>`);
  }finally{button.disabled=false;}
}
async function confirmCrypto(){
  const button=$('[data-action="crypto-confirm"]',modal);button.disabled=true;
  try{await api('crypto-confirm',{token:$('#crypto-pending').dataset.token,confirmation:modal.querySelector('[name=crypto_confirmation]').value});modal.close();await refresh();toast('Protección activada para las copias nuevas.');}finally{button.disabled=false;}
}
async function unlockCrypto(){
  const input=modal.querySelector('[name=crypto_unlock]');
  if(!input){showModal('Desbloquear cifrado','En Windows se abre automáticamente con esta cuenta.',`${field('Contraseña de respaldos','crypto_unlock','','password','autocomplete="off"')}${btn('Desbloquear','crypto-unlock','primary')}`);return;}
  await api('crypto-unlock',{password:input.value});modal.close();await refresh();toast('Copias externas desbloqueadas.');
}
function printRecovery(){
  const key=$('#crypto-recovery',modal)?.textContent;if(!key)throw new Error('No hay una clave pendiente de guardar.');
  modal.dataset.recoveryPrint='yes';
  $('#print-area').innerHTML=`<article class="school-document"><h1>Aula · clave de recuperación de respaldos</h1><p style="font:24px/2 monospace;overflow-wrap:anywhere">${esc(key)}</p><p>Guárdala fuera de la PC y separada del respaldo. No es la contraseña de Aula ni la clave de BitLocker.</p><p>Si pierdes la contraseña y esta clave, las copias NO pueden recuperarse.</p></article>`;
  window.print();
}
async function binaryBackup(path,data){
  const generation=sessionGeneration,started=performance.now();
  const response=await fetch('/api/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf},body:JSON.stringify(data)});
  if(generation!==sessionGeneration)throw new Error('La sesión cambió. Comprueba el estado antes de continuar.');
  sessionHeaders(response,started);
  if(!response.ok){const error=await response.json();if(response.status===401)lockSession();throw new Error(error.error||'No se pudo crear la copia cifrada.');}
  const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=(response.headers.get('Content-Disposition')||'').match(/filename="([^"]+)"/)?.[1]||'respaldo.aulabak';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function downloadEncryptedBackup(){await binaryBackup('backup');toast('Copia cifrada y verificada descargada. Conserva su contraseña o clave de recuperación.');}
async function convertBackup(){
  const file=$('#probe-backup-file').files[0];if(!file)throw new Error('Selecciona una copia para convertir.');
  if(file.size>32*1024*1024+16384+60)throw new Error('La copia supera 32 MB.');
  const button=$('[data-action="convert-backup"]',modal);button.disabled=true;
  try{
    const content=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(new Error('No se pudo leer la copia.'));r.readAsDataURL(file);});
    await binaryBackup('export-encrypted-backup',{content,credential:modal.querySelector('[name=probe_credential]').value,credential_kind:modal.querySelector('[name=probe_kind]').value});
    toast('Nueva copia cifrada descargada. El archivo anterior se conserva intacto.');
  }finally{button.disabled=false;}
}
async function runProbeBackup(){
  const file=$('#probe-backup-file').files[0];if(!file)throw new Error('Selecciona un respaldo primero.');
  if(file.size>32*1024*1024+16384+60)throw new Error('La copia supera 32 MB. Usa Probar respaldo desde Inicio de Windows.');
  const button=$('[data-action="run-probe-backup"]',modal);button.disabled=true;
  try{
    const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('No se pudo leer la copia.'));reader.readAsDataURL(file);});
    const external=$('#probe-external').checked;
    const s=await api('probe-backup',{content,external_copy:external,credential:modal.querySelector('[name=probe_credential]').value,credential_kind:modal.querySelector('[name=probe_kind]').value});
    state.backup=await api('backup-status');updateBackupWarnings();
    $('#probe-result').innerHTML=`<h3>Respaldo comprobado</h3><p>${external?'Prueba externa registrada. El recordatorio se reiniciará a los 35 días.':'Para reiniciar el recordatorio, marca que seleccionaste una copia del USB o la nube y vuelve a probarla.'}</p><p>Integridad y referencias correctas · esquema ${s.schema}.</p><p>${esc(s.audit?.message||'Bitácora antigua sin cadena de huellas.')}</p><p>${s.students} alumnos · ${s.payments} pagos (${s.voided_payments} anulados).</p><p>Último recibo: ${s.last_payment?esc(s.last_payment.receipt)+' · '+dateLabel(s.last_payment.paid_on):'Sin pagos'}.</p><p>Saldo pendiente registrado: <b>${usd(s.balance_usd)}</b>.</p><p class="hint">${esc(s.creation_note)} No se modificaron ni restauraron datos. ${s.unencrypted?'Advertencia: respaldo antiguo sin cifrar.':'Cifrado autenticado y comprobado.'}</p>`;
  }catch(error){$('#probe-result').innerHTML=`<p class="text-red">${esc(error.message)}</p>`;}finally{button.disabled=false;}
}

function auditQuery(){for(const key of ['from','to','search'])auditFilters[key]=document.querySelector(`[name="audit_${key}"]`)?.value||'';return new URLSearchParams(auditFilters).toString();}
async function filterAudit(){rememberSettingsDrafts();auditView=await api('audit?'+auditQuery());$('#page-content').innerHTML=settingsPage();}
async function exportAudit(format){await binaryBackup('audit.'+format+'?'+auditQuery());toast('Bitácora exportada.');}

let incomeView=null,incomeMonth='',incomeOffset=0;
function accountOptions(requiredChoice=false){return [['',requiredChoice?'Selecciona una cuenta':'Sin cuenta asignada'],...(state.school_accounts||[]).filter(a=>a.active).map(a=>[a.id,`${a.name} · ${a.currency}${a.last4?' · …'+a.last4:''}`])];}
function incomePage(){
  const d=incomeView;if(!d)return '<p>Cargando control de ingresos…</p>';
  const accountName=id=>d.accounts.find(a=>a.id===id)?.name||'Sin cuenta asignada';
  const controls=admin()?btn('Nueva cuenta','income-account','primary')+btn('Categorías','income-categories')+btn('Otro ingreso','income-other')+btn('Asignar históricos','income-assign'):'';
  let content=heading('Control de ingresos','Cuentas del colegio, ingresos separados de mensualidades y depósitos de efectivo.',controls+(writable()?btn('Depósito de efectivo','income-deposit'):''));
  content+=card('Resumen del mes',`<div class="card-body">${field('Mes','income_month',d.period,'month','id="income-month"')}<p class="hint">Importes originales por moneda. Los depósitos son traslados internos; no se suman otra vez como ingreso.</p></div>`+table(['Moneda','Mensualidades y cargos','Otros ingresos','Egresos','Neto'],d.totals,r=>`<td>${esc(r.currency)}</td><td>${nativeAmount(r.income,r.currency)}</td><td>${nativeAmount(r.other,r.currency)}</td><td>${nativeAmount(r.expense,r.currency)}</td><td>${nativeAmount(r.income+r.other-r.expense,r.currency)}</td>`,'Sin movimientos en este mes'));
  content+=card('Cuentas del colegio',table(['Cuenta','Tipo / moneda',...(admin()?['Banco / últimos 4 dígitos']:[]),'Estado',...(admin()?['']:[])],d.accounts,a=>`<td>${esc(a.name)}</td><td>${a.kind==='cash'?'Caja efectivo':'Banco'} · ${esc(a.currency)}</td>${admin()?`<td>${esc(a.bank)} ${a.last4?'…'+esc(a.last4):''}</td>`:''}<td>${badge(a.active?'Activa':'Inactiva',a.active?'':'neutral')}</td>${admin()?`<td>${btn('Editar','income-account','small',a.id)}</td>`:''}`,'Administración debe crear las cuentas antes del primer cobro. No hay números de cuenta completos.'));
  if(d.other){
    content+=card('Otros ingresos',table(['Fecha','Concepto / categoría','Cuenta','Importe','Soporte / estado',''],d.other,r=>`<td>${dateLabel(r.received_on)}</td><td>${esc(r.concept)}<span class="sub">${esc(d.categories.find(c=>c.id===r.category_id)?.name)}</span></td><td>${esc(accountName(r.account_id))}</td><td>${nativeAmount(r.received_amount,r.currency)}</td><td><details><summary>${r.voided?'Anulado':'Ver soporte'}</summary>${esc(r.support)} ${esc(r.void_reason)}</details></td><td>${admin()&&!r.voided?btn('Anular','income-void-other','small',r.id):''}</td>`,'Sin otros ingresos en este mes'));
    content+=card('Depósitos de efectivo',table(['Fecha','Planilla / referencia','Cuenta','Importe','Diferencia',''],d.deposits,r=>`<td>${dateLabel(r.deposited_on)}</td><td>${esc(r.reference)}<span class="sub">${r.voided?'Anulado':''}</span></td><td>${esc(accountName(r.account_id))}</td><td>${nativeAmount(r.amount,r.currency)}</td><td>${nativeAmount(r.difference,r.currency)}<span class="sub">${esc(r.difference_reason)}</span></td><td>${admin()&&!r.voided?btn('Anular','income-void-deposit','small',r.id):''}</td>`,'Sin depósitos en este mes'));
    content+=card('Revisión de cobros anteriores',`<p class="hint">Sin cuenta: ${d.unassigned.payments} cobros y ${d.unassigned.expenses} egresos. No se asignan automáticamente. La revisión no cambia recibos, importes ni saldos.</p>`+table(['Recibo','Fecha','Método','Moneda / recibido'],d.unassigned_payments,r=>`<td>R-${String(r.id).padStart(6,'0')}</td><td>${dateLabel(r.paid_on)}</td><td>${esc(r.method)}</td><td>${nativeAmount(r.received_amount,r.currency)}</td>`,'No quedan cobros sin cuenta en esta página'));
    content+=`<div class="actions">${incomeOffset?btn('Página anterior','income-prev'):''}${btn('Página siguiente','income-next')}<span class="hint">Hasta 100 registros por listado · desde ${incomeOffset+1}</span></div>`;
  }
  return content+bankPanel()+accountingPanel();
}
function openIncomeAccount(id){
  const a=incomeView.accounts.find(a=>a.id===Number(id))||{currency:'USD',kind:'bank',active:1};
  showModal(id?'Editar cuenta del colegio':'Nueva cuenta del colegio','Solo últimos cuatro dígitos. La moneda y el tipo se conservan al editar.',`<form data-endpoint="income-account">${id?`<input type="hidden" name="id" value="${a.id}">`:''}<div class="form-grid">${field('Nombre de la cuenta','name',a.name||'','','required maxlength="200"')}${id?field('Moneda','currency',a.currency,'text','readonly')+field('Tipo','kind',a.kind,'text','readonly'):select('Moneda','currency',[['USD','USD'],['VES','Bolívares · VES']],'USD')+select('Tipo','kind',[['bank','Banco'],['cash','Caja efectivo']],'bank')}${field('Banco · vacío para efectivo','bank',a.bank||'','text','maxlength="200"')}${field('Últimos cuatro dígitos · vacío para efectivo','last4',a.last4||'','text','maxlength="4" pattern="[0-9]{4}|"')}${select('Estado','active',[['1','Activa'],['0','Inactiva']],String(a.active))}</div>${formFoot('Guardar cuenta')}</form>`);
}
function openIncomeCategories(){
  showModal('Categorías de otros ingresos','Desactiva una categoría para conservar su historia.',table(['Categoría','Estado',''],incomeView.categories,c=>`<td>${esc(c.name)}</td><td>${c.active?'Activa':'Inactiva'}</td><td>${btn('Editar','income-category','small',c.id)}</td>`)+btn('Nueva categoría','income-category','primary'));
}
function openIncomeCategory(id){const c=incomeView.categories.find(c=>c.id===Number(id))||{active:1};showModal('Categoría de ingreso','No altera mensualidades ni conceptos de recibos.',`<form data-endpoint="income-category">${id?`<input type="hidden" name="id" value="${c.id}">`:''}${field('Nombre','name',c.name||'','text','required maxlength="200"')}${select('Estado','active',[['1','Activa'],['0','Inactiva']],String(c.active))}${formFoot('Guardar categoría')}</form>`);}
function openOtherIncome(){
  showModal('Otro ingreso','Registra el soporte del ingreso; no se aplica a la deuda de un alumno.',`<form data-endpoint="income-other"><input type="hidden" name="request_key" value="${requestKey()}"><div class="form-grid">${field('Concepto','concept','','text','required maxlength="200"')}${select('Categoría','category_id',[['','Selecciona una categoría'],...incomeView.categories.filter(c=>c.active).map(c=>[c.id,c.name])],'','required')}${field('Fecha','received_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda','currency',[['USD','USD'],['VES','Bolívares · VES']],'USD')}${field('Importe','amount','','number','required min="0.01" step="0.01"')}${select('Método','method',paymentMethods.map(m=>[m,m]),'Transferencia')}${select('Cuenta destino','account_id',accountOptions(true),'','required')}${field('Referencia','reference','','text','maxlength="200"')}${textarea('Soporte · descripción o ubicación del documento','support')}<div class="conversion" id="conversion"></div></div>${formFoot('Registrar otro ingreso')}</form>`);updateConversion();
}
function openIncomeAssign(){showModal('Asignar cuenta a históricos','Administración revisa los registros y deja el motivo en la bitácora.',`<form data-endpoint="income-assign"><div class="form-grid">${select('Registros','kind',[['payments','Cobros'],['expenses','Egresos']],'payments')}${field('Números internos separados por coma · sin R- ni E-','ids','','text','required placeholder="1, 2, 3"')}${select('Cuenta','account_id',accountOptions(true),'','required')}${textarea('Motivo de la revisión','reason')}</div>${formFoot('Asignar cuenta revisada')}</form>`);}
function openIncomeDeposit(){showModal('Depósito de efectivo','Vincula importes originales. No se registra otro cobro ni se convierte la moneda.',`<form data-endpoint="income-deposit"><input type="hidden" name="request_key" value="${requestKey()}"><div class="form-grid">${field('Fecha del depósito','deposited_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda','currency',[['USD','USD'],['VES','Bolívares · VES']],'USD')}${select('Cuenta bancaria destino','account_id',[['','Selecciona una cuenta'],...incomeView.accounts.filter(a=>a.active&&a.kind==='bank').map(a=>[a.id,`${a.name} · ${a.currency}`])],'','required')}${field('Importe depositado','amount','','number','required min="0.01" step="0.01"')}${field('Planilla / referencia','reference','','text','required maxlength="200"')}${textarea('Soporte · ubicación del documento','support')}${textarea('Cobros cubiertos · un recibo e importe por línea (ejemplo: 1=10.00)','allocations')}${textarea('Motivo de diferencia · obligatorio si no coincide','difference_reason')}</div>${table(['Recibo en efectivo','Fecha','Disponible'],incomeView.cash_available,r=>`<td>R-${String(r.id).padStart(6,'0')}</td><td>${dateLabel(r.paid_on)}</td><td>${nativeAmount(r.available,r.currency)}</td>`,'No hay cobros en efectivo disponibles en esta página')}${formFoot('Registrar depósito')}</form>`);}
function updateDestination(form,data){
  const field=form.elements.account_id;if(!field||form.dataset.endpoint==='income-deposit')return;
  const current=field.value,choices=(state.school_accounts||[]).filter(a=>a.active&&a.currency===data.currency&&((data.method==='Efectivo')===(a.kind==='cash')));
  let preferred=data.method==='Efectivo'&&choices.length===1?choices[0].id:state.income_preferences?.[data.currency+'|'+data.method];
  field.innerHTML='<option value="">'+(form.dataset.endpoint==='expenses'?'Sin cuenta asignada':'Selecciona una cuenta')+'</option>'+choices.map(a=>`<option value="${a.id}">${esc(a.name)} · ${a.currency}${a.last4?' · …'+a.last4:''}</option>`).join('');
  field.value=choices.some(a=>String(a.id)===current)?current:choices.some(a=>a.id===preferred)?String(preferred):'';
}

let bankView=null,bankDraft=null,bankDays=7;
const bankClasses=['Mensualidad no registrada','Otro ingreso','Entre cuentas propias','Préstamo o aporte','Reintegro','Otro'];
function bankPanel(){
  const d=bankView;if(!d)return '';
  let html=card('Conciliación bancaria',`<p class="hint">Extractos confidenciales. Solo Administración importa y vincula; Aula no se conecta al banco ni al SENIAT. Los vínculos no crean cobros ni cambian deuda.</p>`+table(['Moneda','Créditos del extracto','Débitos del extracto','Importe vinculado','Pendiente de explicar'],d.totals,r=>`<td>${esc(r.currency)}</td><td>${nativeAmount(r.bank_credit,r.currency)}</td><td>${nativeAmount(r.bank_debit,r.currency)}</td><td>${nativeAmount(r.linked,r.currency)}</td><td>${nativeAmount(r.unexplained,r.currency)}</td>`));
  if(!admin())return html;
  html+=card('Extractos y perfiles',`<div class="card-body actions">${btn('Importar extracto','bank-import','primary')}${btn('Nuevo perfil de banco','bank-profile')}${btn('Cruzar candidatos únicos','bank-auto')}${btn('Vincular importes revisados','bank-link')}</div>`+table(['Perfil','Estado',''],d.profiles,p=>`<td>${esc(p.name)}</td><td>${esc(p.status)}</td><td>${btn('Editar','bank-profile','small',p.id)}</td>`,'Sin perfiles guardados. La plantilla Provincial es editable y NO VERIFICADA.')+table(['Importación','Cuenta','Movimientos','Huella SHA-256'],d.imports,r=>`<td>${r.id}</td><td>${esc(incomeView.accounts.find(a=>a.id===r.account_id)?.name)}</td><td>${r.rows_count}</td><td><details><summary>Ver huella</summary>${esc(r.file_sha256)}</details></td>`,'Sin extractos importados'));
  html+=card('Depósitos y débitos sin recibo o egreso',table(['Banco ID','Fecha','Referencia / descripción','Pendiente','Candidatos',''],d.bank_pending,b=>`<td>${b.id}</td><td>${dateLabel(b.on)}</td><td>${esc(b.reference)}<span class="sub">${esc(b.description)} · ${b.direction==='credit'?'Crédito':'Débito'}</span></td><td>${nativeAmount(b.remaining,b.currency)}</td><td>${esc(b.proposal.candidates.join(', ')||'Ninguno')}<span class="sub">${esc(b.proposal.reason)}</span></td><td>${b.direction==='credit'?btn('Clasificar','bank-classify','small',b.id):''}</td>`,'Sin pendientes de banco en este mes'));
  html+=card('Recibos y egresos sin depósito',`<p class="hint">P = recibo; E = egreso; O = otro ingreso; D = planilla de efectivo. Los recibos de efectivo se vinculan a su planilla, no se duplican en el cruce bancario.</p>`+table(['Libro ID','Fecha','Referencia','Pendiente'],d.ledger_pending,l=>`<td>${esc(l.id)}</td><td>${dateLabel(l.on)}</td><td>${esc(l.reference)}</td><td>${nativeAmount(l.remaining,l.currency)}</td>`,'Sin pendientes del libro en este mes'));
  html+=card('Diferencias de monto',table(['Banco ID','Libro ID','Banco','Libro','Motivo'],d.differences,r=>`<td>${r.movement_id}</td><td>${esc(r.source)}</td><td>${nativeAmount(r.bank_amount,r.currency)}</td><td>${nativeAmount(r.ledger_amount,r.currency)}</td><td>${esc(r.reason)}</td>`,'Sin diferencias propuestas · hasta 100 casos'));
  html+=card(`Pendientes de más de ${bankDays} días`,`<div class="card-body">${field('Días de antigüedad','bank_days',bankDays,'number','id="bank-days" min="1" max="3650"')}</div>`+table(['Origen / ID','Fecha','Pendiente','Motivo'],d.older,r=>`<td>${esc(r.source)} ${esc(r.id)}</td><td>${dateLabel(r.on)}</td><td>${nativeAmount(r.remaining,r.currency)}</td><td>${esc(r.reason)}</td>`,'Sin pendientes antiguos'));
  html+=card('Vínculos e historial',table(['ID','Banco','Libro','Importe original','Estado',''],d.links,r=>`<td>${r.id}</td><td>${r.movement_id}</td><td>${r.payment_id?'P'+r.payment_id:r.expense_id?'E'+r.expense_id:r.other_id?'O'+r.other_id:'D'+r.deposit_id}</td><td>${number(r.amount/100)}</td><td>${r.voided?'Retirado':'Activo'}</td><td>${!r.voided?btn('Retirar','bank-unlink','small',r.id):''}</td>`,'Sin vínculos'));
  html+=card('Depósitos clasificados',table(['Banco','Clasificación','Soporte / motivo','Estado',''],d.classifications,r=>`<td>${r.movement_id}</td><td>${esc(r.category)}</td><td>${esc(r.support)}<span class="sub">${esc(r.reason)}</span></td><td>${r.voided?'Retirada':'Activa'}</td><td>${!r.voided?btn('Retirar','bank-unclassify','small',r.id):''}</td>`,'Sin clasificaciones'));
  return html;
}
function bankMappingFields(profile={}){
  const p={delimiter:';',encoding:'utf-8-sig',date_format:'%Y-%m-%d',decimal:'.',columns:{date:'Fecha',amount:'Importe',reference:'Referencia',description:'Descripción'},...profile};
  return `<div class="form-grid">${select('Separador CSV','delimiter',[[';','Punto y coma'],[',','Coma'],['\t','Tabulación']],p.delimiter)}${select('Codificación CSV','encoding',[['utf-8-sig','UTF-8'],['cp1252','Windows-1252']],p.encoding)}${select('Formato de fecha','date_format',[['%Y-%m-%d','Año-mes-día'],['%d/%m/%Y','Día/mes/año']],p.date_format)}${select('Separador decimal','decimal',[['.','Punto'],[',','Coma']],p.decimal)}${[['date','Fecha'],['amount','Importe con signo (+ ingreso, − egreso)'],['reference','Referencia'],['description','Descripción'],['bank_id','ID único del banco · opcional']].map(([key,label])=>field('Columna: '+label,'column_'+key,p.columns[key]||'','text',key==='bank_id'?'maxlength="100"':'required maxlength="100"')).join('')}</div><p class="hint">Escribe los encabezados exactos. Sin separadores de miles. Excel: primera hoja; referencias e ID como texto, sin fórmulas. Provincial: plantilla editable NO VERIFICADA; contrasta el mapeo con tu extracto.</p>`;
}
function bankMapping(form){const value=Object.fromEntries(new FormData(form));return {delimiter:value.delimiter,encoding:value.encoding,date_format:value.date_format,decimal:value.decimal,columns:Object.fromEntries(['date','amount','reference','description','bank_id'].filter(k=>value['column_'+k]).map(k=>[k,value['column_'+k]]))};}
function openBankProfile(id){const p=bankView.profiles.find(p=>p.id===Number(id));showModal('Perfil de importación','El formato del banco requiere revisión real.',`<form data-endpoint="bank-profile">${p?`<input type="hidden" name="id" value="${p.id}">`:''}${field('Nombre','name',p?.name||'BBVA Provincial · plantilla NO VERIFICADA','text','required maxlength="200"')}${bankMappingFields(p?.profile)}${formFoot('Guardar perfil')}</form>`);}
function openBankImport(){bankDraft=null;showModal('Importar extracto','Archivo confidencial. Primero revisa la vista previa; no se crean pagos.',`<form data-endpoint="bank-preview">${select('Cuenta bancaria','account_id',[['','Selecciona una cuenta'],...incomeView.accounts.filter(a=>a.kind==='bank'&&a.active).map(a=>[a.id,a.name+' · '+a.currency])],'','required')}${select('Perfil guardado · o mapeo de abajo','profile_id',[['','Mapeo editable de abajo'],...bankView.profiles.map(p=>[p.id,p.name])])}${field('Archivo CSV o Excel','statement_file','','file','required accept=".csv,.xlsx"')}${bankMappingFields()}${formFoot('Revisar vista previa')}</form>`);}
function readBankFile(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('No se pudo leer el archivo.'));reader.readAsDataURL(file);});}
function showBankPreview(p){bankDraft.confirmed_hash=p.file_sha256;const possible=[...new Set([...p.duplicates.map(d=>d.row),...p.overlaps.filter(d=>!d.definite).map(d=>d.row)])];showModal('Vista previa del extracto',`${p.rows_count} movimientos; se muestran hasta 100. NO VERIFICADO con un extracto real.`, `<p class="hint">Huella ${esc(p.file_sha256)}. ${p.already_imported?'Este archivo ya se importó; repetir no duplica movimientos.':''}</p>`+table(['Fila','Fecha','Referencia','Importe','Descripción'],p.rows,r=>`<td>${r.row}</td><td>${dateLabel(r.on)}</td><td>${esc(r.reference)}</td><td>${r.direction==='debit'?'−':''}${nativeAmount(r.amount,r.currency)}</td><td>${esc(r.description)}</td>`)+`<p>${p.overlaps.filter(d=>d.definite).length} ID bancarios ya importados: se omiten al confirmar.</p>${possible.length?`<p class="notice warning">Posibles duplicados en filas: ${esc(possible.join(', '))}. Si son operaciones distintas legítimas, escribe esos números y explica por qué; de lo contrario revisa el archivo.</p>${field('Filas confirmadas como distintas, separadas por coma','accepted_duplicate_rows')}${textarea('Motivo de la revisión','duplicate_reason')}`:''}<div class="actions">${btn('Cancelar','close')}${btn('Confirmar importación revisada','bank-commit','primary')}</div>`);}
async function commitBankImport(){if(!bankDraft)throw new Error('Selecciona el archivo y revisa la vista previa otra vez.');const button=$('[data-action="bank-commit"]',modal);button.disabled=true;try{const rows=$('[name="accepted_duplicate_rows"]',modal)?.value||'';const result=await api('bank-import',{...bankDraft,accepted_duplicate_rows:rows.split(',').map(v=>v.trim()).filter(Boolean),reason:$('[name="duplicate_reason"]',modal)?.value||''});bankDraft=null;modal.close();await refresh();toast(result.duplicate?'El archivo ya estaba importado.':`${result.imported} movimientos importados; no se registraron cobros.`);}finally{button.disabled=false;}}
function openBankLink(){showModal('Vincular importes revisados','Mis­ma cuenta y moneda; se permiten partes de varios recibos y movimientos. Revisa fecha y referencia.',`<form data-endpoint="bank-link">${textarea('Un vínculo por línea: BancoID LibroID Importe (ejemplo: 1 P2 10.00)','allocations')}${textarea('Motivo de la revisión','reason')}${formFoot('Guardar vínculos')}</form>`);}
function openBankClassify(id){showModal('Clasificar depósito sin recibo','No registra una mensualidad ni modifica saldos del alumno.',`<form data-endpoint="bank-classify"><input type="hidden" name="movement_id" value="${Number(id)}">${select('Clasificación','category',bankClasses.map(c=>[c,c]))}${textarea('Soporte del depósito','support')}${textarea('Motivo','reason')}${formFoot('Guardar clasificación')}</form>`);}

let accountingView=null;
const monthPendingLabels={unassigned:'Movimientos sin cuenta',missing_rates:'Sin tasa BCV histórica',bank_unlinked:'Banco sin explicar',book_unlinked:'Libro sin depósito',unrecorded_tuition:'Clasificados como mensualidad sin registrar',invoice_drafts:'Borradores de factura',invoice_unbilled:'Cobros sin factura (si está habilitada)',invoice_numbers:'Números con salto por regularizar'};
function accountingPanel(){
  const d=accountingView;if(!d)return '';
  return card('Relación para el contador y cierre mensual',`<div class="card-body"><p class="notice ${d.closed?'warning':''}">${esc(d.period)} · ${d.closed?'MES CERRADO. Se conserva la foto del cierre. Los movimientos del período están bloqueados en el servidor.':'Mes abierto. Revisa los pendientes antes de cerrar.'}</p><p class="hint">Sin impuestos calculados ni datos personales de menores. La columna factura muestra los números preimpresos asociados; permanece vacía si no se emitió. Las opciones fiscales son solo informativas.</p><div class="actions">${btn('CSV para Excel','accounting-csv')}${btn('PDF para contador','accounting-pdf')}${admin()?(d.closed?btn('Reabrir con motivo','month-reopen','',d.closure.id):btn('Revisar y cerrar mes','month-close','primary')):''}</div></div>`+table(['Resumen','USD conservado'],[{label:'Ingresos válidos',amount:d.totals.income_usd},{label:'Egresos válidos',amount:d.totals.expenses_usd},{label:'Neto',amount:d.totals.net_usd}],r=>`<td>${esc(r.label)}</td><td>${usd(r.amount)}</td>`)+table(['Pendiente','Cantidad'],Object.entries(d.pending),r=>`<td>${esc(monthPendingLabels[r[0]]||r[0])}</td><td>${r[1]}</td>`)+table(['Ingreso','Fecha / concepto','Cuenta','Original','Estado / opciones',''],d.income.slice(0,100),r=>`<td>${esc(r.receipt||r.source)}</td><td>${dateLabel(r.date)}<span class="sub">${esc(r.concept)}</span></td><td>${esc(r.account)}</td><td>${nativeAmount(r.original_amount,r.currency)}</td><td>${r.voided?'Anulado':'Válido'}${r.special_taxpayer?' · Especial':''}${r.foreign_currency?' · Divisas':''}<span class="sub">${esc(r.verification)}</span></td><td>${admin()&&!d.closed?btn('Opciones informativas','month-annotation','small',r.source):''}</td>`,'Sin ingresos en este mes')+`<p class="hint">La pantalla muestra hasta 100 ingresos; las exportaciones incluyen todos los del mes. ${esc(d.note)}</p>`);
}
function openMonthClose(){const d=accountingView;showModal('Revisar cierre mensual','La foto conserva el libro y sus opciones. La reapertura requiere Administración y motivo.',`<form data-endpoint="month-close"><input type="hidden" name="period" value="${esc(d.period)}"><input type="hidden" name="confirmed_hash" value="${esc(d.preview_hash)}">${table(['Pendiente','Cantidad'],Object.entries(d.pending),r=>`<td>${esc(monthPendingLabels[r[0]]||r[0])}</td><td>${r[1]}</td>`)}${Object.values(d.pending).some(n=>n)?'<label class="confirm-check"><input type="checkbox" name="confirmed_pending" required> Revisé estos pendientes y autorizo conservarlos en el cierre.</label>':''}<p>Ingresos ${usd(d.totals.income_usd)} · Egresos ${usd(d.totals.expenses_usd)} · Neto ${usd(d.totals.net_usd)}.</p>${formFoot('Cerrar mes revisado')}</form>`);}
function openMonthAnnotation(source){const r=accountingView.income.find(r=>r.source===source);if(!r)return;showModal('Opciones informativas','No calcula IVA ni IGTF y no modifica el comprobante.',`<form data-endpoint="month-annotation"><input type="hidden" name="source" value="${esc(source)}"><label class="confirm-check"><input type="checkbox" name="special_taxpayer" ${r.special_taxpayer?'checked':''}> Sujeto pasivo especial · solo informativo</label><label class="confirm-check"><input type="checkbox" name="foreign_currency" ${r.foreign_currency?'checked':''}> Pagado en divisas · solo informativo</label>${formFoot('Guardar opciones')}</form>`);}
