'use strict';
const $ = (s, root = document) => root.querySelector(s);
const app = $('#app'), modal = $('#modal');
let state, session, page = 'dashboard', filters = {}, reportFrom = '', reportTo = '';
let publicSchool = {};
let receiptPaper = 'half-letter';
let demoMode = false, demoToken = '', demoTimer;
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
 employees:'M3 7h18v14H3z M8 7V3h8v4 M3 12h18 M10 12v3h4v-3',
 expenses:'M4 8h16v12H4z M7 8V4h10v4 M8 12h8 M8 16h5',
 settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M9 3h6l1 3 3 1 2 5-2 4-3 1-1 4H9l-1-4-3-1-2-4 2-5 3-1z',
 plus:'M12 5v14 M5 12h14', arrow:'M5 12h14 M13 6l6 6-6 6', download:'M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4',
 logout:'M9 3H4v18h5 M10 12h11 M17 8l4 4-4 4', check:'M5 12l4 4L19 6', clock:'M12 8v4l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 search:'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0', print:'M6 9V3h12v6 M6 17H3V9h18v8h-3 M6 14h12v7H6z',
 shield:'M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7z M8 12l3 3 5-6', book:'M4 3h7c1 0 1 1 1 1s0-1 1-1h7v17h-7c-1 0-1 1-1 1s0-1-1-1H4z M12 4v17'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.book}"/></svg>`;
function schoolLogo(s = state?.settings || publicSchool) {
  const src = s?.logo === 'logo-colegio-v1.png' ? '/logo-colegio-v1.png' : /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(s?.logo || '') ? s.logo : '';
  return src ? `<img src="${esc(src)}" alt="Logo del colegio">` : `<span class="school-placeholder">${icon('book')}</span>`;
}
const btn = (label, action, style = '', id = '') => `<button type="button" class="btn ${style}" data-action="${action}" ${id !== '' ? `data-id="${esc(id)}"` : ''}>${label}</button>`;
const empty = (title, text = 'Los registros aparecerán aquí.', name = 'book') => `<div class="empty">${icon(name)}<b>${esc(title)}</b>${esc(text)}</div>`;
const badge = (label, kind = '') => `<span class="badge ${kind}">${esc(label)}</span>`;
const actionsCell = markup => `<div class="actions">${markup}</div>`;
const table = (headers, records, renderer, emptyTitle = 'Sin registros') => records.length ? `<div class="table-wrap"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${records.map(r => `<tr>${renderer(r)}</tr>`).join('')}</tbody></table></div>` : empty(emptyTitle);
const card = (title, body, action = '', subtitle = '') => `<section class="card"><div class="card-head"><div><h2>${title}</h2>${subtitle ? `<p>${subtitle}</p>` : ''}</div>${action}</div>${body}</section>`;
const stat = (label, value, note, name, style = '') => `<div class="stat ${style}"><div class="stat-label">${label}<span class="stat-icon">${icon(name)}</span></div><div class="stat-value">${value}</div><small>${note}</small></div>`;
const exportBtn = (type, label = 'Exportar Excel / CSV') => `<a class="btn" href="/api/export?type=${type}" download>${icon('download')}${label}</a>`;
const directoryReportBtn = type => btn(`${icon('print')} PDF / Imprimir`,'directory-report','',type);
const field = (label, name, value = '', type = 'text', extra = '', hint = '') => `<label class="field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}>${hint ? `<small>${esc(hint)}</small>` : ''}</label>`;
const select = (label, name, options, selected = '', extra = '') => `<label class="field">${esc(label)}<select name="${name}" ${extra}>${options.map(o => `<option value="${esc(o[0])}" ${String(o[0]) === String(selected) ? 'selected' : ''}>${esc(o[1])}</option>`).join('')}</select></label>`;
const textarea = (label, name, value = '', limit = 2000) => `<label class="field full">${esc(label)}<textarea name="${name}" aria-label="${esc(label)}" maxlength="${limit}">${esc(value)}</textarea></label>`;
const formFoot = label => `<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar', 'close')}<button class="btn primary" type="submit">${label}</button></div>`;
const statusOptions = [['active','Activo'],['inactive','Inactivo']];

async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':session?.csrf || ''}, body:JSON.stringify(data)};
  let response;
  try { response = await fetch('/api/' + path, options); }
  catch { throw new Error('No hay conexión con el colegio. Comprueba que Aula siga abierta en esta PC.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('El servidor no respondió. Comprueba que la ventana de Aula esté abierta.'); }
  if (!response.ok) {
    if(response.status===409&&result.requires_rate_confirmation&&data&&!data.rate_change_confirmed){if(window.confirm(result.error+' ¿Seguro que deseas usar esta tasa?'))return api(path,{...data,rate_change_confirmed:true});throw new Error('La tasa no se guardó. Revisa el importe.');}
    if (response.status === 428) { await openRateGate(); }
    if (response.status === 401 && path !== 'login') { state = undefined; await boot(); }
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
    session = result.user; publicSchool = result.school || {};
    configureDemo(result);
    if (!session) { auth(result.needs_setup); return; }
    await openRateGate();
  } catch (error) { app.innerHTML = `<div class="loading"><h2>No se pudo abrir Aula</h2><p>${esc(error.message)}</p>${btn('Reintentar','boot')}</div>`; }
}
async function openRateGate() {
  const gate = await api('rate-gate'); publicSchool = gate.school || publicSchool;
  state=undefined; modal.close(); $('#print-area').replaceChildren();
  app.innerHTML=demoBanner()+`<div class="rate-screen"><section class="card gate-card"><div class="brand">${schoolLogo(publicSchool)}<div><small>${esc(publicSchool.institution_type||'Administración escolar')}</small><b>${esc(publicSchool.school_name||'Aula')}</b><small>Tasas y respaldo</small></div></div><div class="eyebrow">${dateLabel(gate.today)}</div><h1>Confirma la tasa de hoy</h1><p>Antes de comenzar, revisa la tasa oficial vigente. Se usará para convertir los pagos y la nómina en bolívares.</p><form data-endpoint="confirm-rate"><input type="hidden" name="rate_date" value="${gate.today}">${field('Bolívares por 1 USD','rate',gate.rate,'number',`required min="0.000001" max="1000000" step="0.000001" ${gate.role==='reader'?'readonly':''}`)}<p class="hint">${gate.role==='reader'?'Consulta puede confirmar la tasa registrada. Si falta, administración o caja debe registrarla.':'Consulta bcv.org.ve y registra la tasa vigente, incluso en fines de semana y feriados. La actualización es manual.'}</p><div class="error" role="alert"></div><button class="btn primary" type="submit" ${gate.role==='reader'&&!gate.rate?'disabled':''}>Confirmar tasa y entrar</button></form><div class="gate-footer">${gate.role==='admin'&&!demoMode?'<a class="btn" href="/api/backup" download>Descargar respaldo</a>':''}${btn('Cerrar sesión','logout')}</div></section></div>`;
}
function auth(setup) {
  if(demoMode){demoAuth();return;}
  state=undefined;modal.close();$('#print-area').replaceChildren();
  app.innerHTML = `<div class="auth-screen"><section class="auth-story"><div class="brand">${schoolLogo(publicSchool)}<div><small>${esc(publicSchool.institution_type||'Administración escolar')}</small><b>${esc(publicSchool.school_name||'Aula')}</b><small>Administración escolar</small></div></div><h1>Tu colegio,<br>con las cuentas<br><em>en orden.</em></h1><p>Alumnos, mensualidades y cobranza en un mismo lugar. Pensado para el día a día de tu colegio en Venezuela.</p><p>${icon('shield')} Datos locales · USD y bolívares</p></section><section class="auth-form"><div class="eyebrow">${setup ? 'Empecemos' : 'Bienvenido de nuevo'}</div><h2>${setup ? 'Configura tu administrador' : 'Entrar a tu colegio'}</h2><p>${setup ? 'Esta cuenta gestionará el colegio y podrá crear usuarios de caja y consulta.' : 'Ingresa tus datos para continuar con la administración.'}</p><form data-endpoint="${setup ? 'setup' : 'login'}">${setup ? field('Nombre del colegio','school_name','','text','required maxlength="200" autocomplete="organization"')+field('Nombre del administrador','name','','text','required maxlength="200" autocomplete="name"') : ''}${field('Usuario','username','','text','required maxlength="80" autocomplete="username"')}${field('Contraseña','password','','password',`required ${setup ? 'minlength="10"' : ''} maxlength="256" autocomplete="${setup ? 'new-password' : 'current-password'}"`,setup ? 'Como mínimo 10 caracteres. Guárdala en un lugar seguro.' : '')}<div class="error" role="alert"></div><button class="btn primary" type="submit">${setup ? 'Crear mi cuenta' : 'Iniciar sesión'} ${icon('arrow')}</button></form><p class="recovery-link">${btn('Olvidé mi usuario o contraseña','recovery-help','ghost')}</p><div class="auth-note">Los datos se guardan en esta PC y puedes trabajar sin internet. La tasa BCV se registra manualmente por fecha. Usa siempre la misma cuenta de Windows.</div></section></div>`;
}
async function refresh() { state = await api('state'); render(); }
const navItems = [['dashboard','Resumen','dashboard'],['students','Alumnos y matrículas','students'],['guardians','Representantes','guardians'],['grades','Grados y secciones','grades'],['billing','Mensualidades y cargos','billing'],['payments','Caja y cobros','payments'],['cash','Cierre de caja','payments'],['arrears','Morosidad','arrears'],['employees','Personal','employees'],['expenses','Egresos y nómina','expenses'],['reports','Reportes','reports'],['settings','Configuración','settings']];
function render() {
  if (!state) return;
  if (page === 'settings' && !admin()) page = 'dashboard';
  document.title = (demoMode?"PRUEBA · ":"") + state.settings.school_name + " · Administración escolar";
  const rate = todayRate(), current = navItems.find(n => n[0] === page);
  app.innerHTML = `<div class="layout"><header class="mobile-header">${schoolLogo()}<div><small>Administración escolar</small><b>${current[1]}</b></div><button type="button" class="btn mobile-menu-toggle" data-action="mobile-menu" aria-controls="school-navigation" aria-expanded="false"><span aria-hidden="true">☰</span> Menú</button></header><button class="menu-backdrop" type="button" data-action="mobile-menu-close" aria-label="Cerrar menú" tabindex="-1" hidden></button><aside class="sidebar" id="school-navigation" aria-label="Navegación del colegio"><button type="button" class="btn mobile-menu-close" data-action="mobile-menu-close" aria-label="Cerrar menú">Cerrar ×</button><div class="brand">${schoolLogo()}<div><b>${esc(state.settings.school_name)}</b><small>Administración escolar</small></div></div><nav>${navItems.filter(n => n[0] !== 'settings' || admin()).map((n,i) => `${[0,4,8,10].includes(i) ? `<div class="nav-label">${({0:'Colegio',4:'Finanzas',8:'Administración',10:'Gestión'})[i]}</div>` : ''}<button class="nav-button ${page === n[0] ? 'active' : ''}" data-action="nav" data-id="${n[0]}">${icon(n[2])}${n[1]}${n[0] === 'arrears' && state.summary.debtors ? `<span class="count">${state.summary.debtors}</span>` : ''}</button>`).join('')}</nav><div class="sidebar-footer"><div class="local-pill"><span class="dot"></span>${state.access?.mode==='private-network'?'Base compartida · PC principal':'Una computadora · Datos locales'}</div><div class="profile"><div class="avatar">${esc(state.user.name.slice(0,1).toUpperCase())}</div><div class="profile-text"><b>${esc(state.user.name)}</b><small>${roleLabel(state.user.role)}</small></div><button class="logout" data-action="logout" title="Cerrar sesión" aria-label="Cerrar sesión">${icon('logout')}</button></div></div></aside><main class="main"><header class="topbar"><div class="breadcrumb">${esc(state.settings.school_name)} <span> / </span> <b>${current[1]}</b></div><div class="top-info"><span class="backup-status ${backupStale()?'text-red':''}" title="${esc(state.backup?.local_path||'')}">${backupLabel()}</span><span>${dateLabel(state.today)}</span><button class="rate-chip" data-action="rates">${rate ? `BCV · Bs ${number(Number(rate.rate))} / USD` : 'BCV · Tasa de hoy pendiente'}</button></div></header>${demoBanner()}<div id="page-content">${backupProblem()}${pageBody()}</div><div class="welcome-line"><span>${esc(state.settings.school_name)} · Administración escolar</span><span>Año escolar ${esc(state.settings.school_year)}–${Number(state.settings.school_year)+1} · Base USD</span></div></main></div>`;
  window.AulaMobile?.render();
}
function heading(title, description, actions = '') { return `<div class="page-heading"><div><div class="eyebrow">${esc(state.settings.school_name)}</div><h1>${title}</h1><p>${description}</p></div><div class="actions">${actions}</div></div>`; }
function pageBody() {
  return ({dashboard,students:studentsPage,guardians:guardiansPage,grades:gradesPage,billing:billingPage,payments:paymentsPage,arrears:arrearsPage,employees:employeesPage,expenses:expensesPage,cash:cashPage,reports:reportsPage,settings:settingsPage}[page])();
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
  return `${btn('Editar',kind,'small',record.id)}${record.archived?btn('Recuperar ficha','restore-'+kind,'small',record.id):btn('Eliminar del directorio','archive-'+kind,'small text-red',record.id)}`;
}
function openDirectoryAction(endpoint,id){
  if(endpoint==='delete-grade'){
    const grade=state.grades.find(g=>g.id===Number(id));if(!grade)return;
    showModal('Eliminar grado / sección',esc(grade.name),`<form data-endpoint="delete-grade"><input type="hidden" name="id" value="${grade.id}"><p>Solo se elimina si no tiene alumnos vinculados, incluidas fichas inactivas o archivadas. Los documentos ya emitidos se conservan. Se creará un respaldo previo.</p>${textarea('Motivo obligatorio','reason')}${field('Escribe ELIMINAR','confirmation','','text','required pattern="ELIMINAR" autocomplete="off"')}<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn danger">Eliminar grado / sección</button></div></form>`);$('textarea',modal).required=true;return;
  }
  const isStudent=endpoint.endsWith('student'),record=(isStudent?state.students:state.guardians).find(r=>r.id===Number(id)),archiving=endpoint.startsWith('archive-'),word=archiving?'ARCHIVAR':'RECUPERAR';
  if(!record)return;
  const message=archiving?(isStudent?'La ficha se archivará y dejará de generar nuevas mensualidades. Los cargos, deudas, pagos y recibos existentes se conservan. Para corregir una deuda creada por error, usa Corregir mensualidades.':'La ficha se archivará. Si tiene alumnos sin archivar, primero deberás reasignarlos o archivar sus fichas. Los documentos existentes se conservan.'):(isStudent?'La ficha volverá al directorio como inactiva. Revisa sus datos y el primer mes a cobrar antes de activarla.':'La ficha volverá al directorio de representantes.');
  showModal(archiving?'Eliminar del directorio':'Recuperar ficha',esc(record.name),`<form data-endpoint="${endpoint}"><input type="hidden" name="id" value="${record.id}"><p>${message}</p>${textarea('Motivo obligatorio','reason')}${field('Escribe '+word,'confirmation','','text',`required pattern="${word}" autocomplete="off"`)}<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button type="submit" class="btn ${archiving?'danger':'primary'}">${archiving?'Archivar ficha':'Recuperar ficha'}</button></div></form>`);
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
  return heading('Caja y cobros','Recibe dólares o bolívares y emite comprobantes de pago.',exportBtn('payments')+(writable()?btn(`${icon('plus')} Registrar pago`,'payment','primary'):'')) + card('Historial de recibos',searchToolbar('Buscar alumno, recibo o referencia…')+table(['Recibo / alumno','Fecha','Recibido','Tasa BCV','Equivalente USD','Método','Estado',''],records,p=>`<td><b>R-${String(p.id).padStart(6,'0')}</b><span class="sub">${esc(p.student_name)}</span></td><td>${dateLabel(p.paid_on)}</td><td class="money">${p.currency==='VES'?bs(p.received_amount):usd(p.amount)}</td><td>${p.currency==='VES'?number(Number(p.exchange_rate)):'—'}</td><td class="money">${usd(p.amount)}</td><td>${esc(p.method)}<span class="sub">${esc(p.reference)}</span></td><td>${badge(p.voided?'Anulado':'Válido',p.voided?'red':'')}</td><td>${actionsCell(btn('Recibo','receipt','small',p.id)+(admin()&&!p.voided?btn('Anular','void-payment','small',p.id):''))}</td>`,'Aún no hay pagos registrados'));
}
function arrearsPage() {
  const all = state.students.filter(s=>s.overdue>0), records = all.filter(matches);
  const sum = records.reduce((t,s)=>t+s.overdue,0);
  return heading('Morosidad y cobranza','Deuda vencida, antigüedad y seguimiento por alumno y representante.',exportBtn('arrears')) + `<div class="stats">${stat('Deuda vencida visible',usd(sum),'Total del filtro actual','arrears','alert')}${stat('Alumnos en mora',records.length,'Del filtro actual','students')}${stat('Equivalente en bolívares',todayRate()?bs(Math.round(sum*Number(todayRate().rate))):'—',todayRate()?'Referencia con tasa BCV de hoy':'Falta registrar la tasa BCV de hoy','payments')}${stat('Mayor atraso',Math.max(0,...state.charges.filter(c=>c.overdue && records.some(s=>s.id===c.student_id)).map(c=>c.days_overdue))+'<span>días</span>','Cargo vencido más antiguo del filtro','clock')}</div>`+card('Cuentas que requieren seguimiento',searchToolbar('Buscar alumno o representante…',true)+table(['Alumno / grado','Representante / contacto','Deuda vencida USD','Antigüedad','Acciones'],records,s=>{const days=Math.max(...state.charges.filter(c=>c.student_id===s.id&&c.overdue).map(c=>c.days_overdue));return `<td><b>${esc(s.name)}</b><span class="sub">${esc(s.grade_name)}</span></td><td>${esc(s.guardian_name)}<span class="sub">${esc(s.guardian_phone)||'Sin teléfono'}</span></td><td class="money text-red">${usd(s.overdue)}</td><td>${badge(days+' días',days>30?'red':'neutral')}</td><td class="row-actions">${actionsCell(btn('Cuenta','account','small',s.id)+btn('Aviso','collection','small',s.id)+(writable()?btn('Convenio','payment-plan','small',s.id)+btn('Registrar pago','payment','small primary',s.id):''))}</td>`;},'No hay deuda vencida con este filtro'));
}
function employeesPage() {
  const records = state.employees.filter(matches);
  return heading('Personal del colegio','Salarios en USD, pagos en Bs y datos bancarios del equipo.',(admin()?btn('Cargos','positions')+btn('Preparar nómina','payroll-plan'):'')+(admin()?btn(`${icon('plus')} Nuevo empleado`,'employee','primary'):''))+card('Equipo administrativo y docente',searchToolbar('Buscar empleado, documento o cargo…')+table(['Empleado','Cargo','Banco / cuenta','Salario USD / Bs','Estado',''],records,e=>`<td><b>${esc(e.name)}</b><span class="sub">${esc(e.document)}</span></td><td>${esc(e.position)}</td><td>${esc(e.bank)||'Pendiente'}<span class="sub">${esc(e.bank_account)||'Sin cuenta'}</span></td><td class="money">${usd(e.salary)}<span class="sub">${bs(Math.round(e.salary*Number(todayRate()?.rate||0)))}</span></td><td>${badge(e.status==='active'?'Activo':'Inactivo',e.status==='active'?'':'neutral')}</td><td>${actionsCell((admin()?btn('Editar','employee','small',e.id):'')+(writable()?btn('Pagar nómina','payroll','small',e.id):''))}</td>`,'Registra el personal del colegio'),directoryReportBtn('employees'))+card('Relaciones de pago guardadas',table(['Documento','Fecha / tasa','Total USD / Bs',''],state.payroll_plans,p=>`<td>${esc(p.name)}<span class="sub">N-${String(p.id).padStart(6,'0')}</span></td><td>${dateLabel(p.pay_date)}<span class="sub">Bs ${esc(p.rate)} / USD</span></td><td>${usd(p.total_usd)}<span class="sub">${bs(p.total_ves)}</span></td><td>${btn('Ver documento','payroll-document','small',p.id)}</td>`,'Aún no hay relaciones de pago'));
}
function expensesPage() {
  const records=state.expenses.filter(e=>[e.concept,e.category,e.reference,e.employee_name||''].some(v=>v.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Egresos y nómina','Registra gastos operativos y pagos al personal, en USD o Bs.',exportBtn('expenses')+(writable()?btn(`${icon('plus')} Registrar egreso`,'expense','primary'):''))+card('Libro de egresos',searchToolbar('Buscar concepto, categoría o empleado…')+table(['Concepto','Fecha','Categoría','Pagado','Equivalente USD','Estado',''],records,e=>`<td><b>${esc(e.concept)}</b><span class="sub">${esc(e.employee_name)||esc(e.reference)}</span></td><td>${dateLabel(e.spent_on)}</td><td>${esc(e.category)}</td><td class="money">${e.currency==='VES'?bs(e.received_amount):usd(e.amount)}<span class="sub">${e.currency==='VES'?'BCV: '+number(Number(e.exchange_rate)):'Dólares'}</span></td><td class="money">${usd(e.amount)}</td><td>${badge(e.voided?'Anulado':'Válido',e.voided?'red':'')}</td><td>${actionsCell((e.salary_receipt_id?btn('Recibo de sueldo','salary-document','small',e.salary_receipt_id):writable()&&!e.voided&&e.category==='Nómina'&&e.employee_id?btn('Emitir recibo','salary-receipt','small',e.id):'')+(admin()&&!e.voided?btn('Anular','void-expense','small',e.id):''))}</td>`,'Aún no hay egresos registrados'));
}
function reportsPage() {
  reportFrom ||= state.today.slice(0,7)+'-01'; reportTo ||= state.today;
  const payments=state.payments.filter(p=>!p.voided&&p.paid_on>=reportFrom&&p.paid_on<=reportTo), expenses=state.expenses.filter(e=>!e.voided&&e.spent_on>=reportFrom&&e.spent_on<=reportTo);
  const income=payments.reduce((a,p)=>a+p.amount,0), out=expenses.reduce((a,e)=>a+e.amount,0);
  return heading('Reportes administrativos','Consulta el flujo de caja y descarga los libros completos en CSV.',btn(`${icon('download')} Reporte diario PDF`,'daily-report','primary')+btn('Cierre de caja diario','nav','','cash')+btn(`${icon('print')} Imprimir resumen`,'print-report'))+`<div class="card"><div class="toolbar">${field('Desde','report-from',reportFrom,'date','id="report-from"')}${field('Hasta','report-to',reportTo,'date','id="report-to"')}<span class="table-count">${payments.length} cobros · ${expenses.length} egresos válidos</span></div></div><div class="stats">${stat('Ingresos del período',usd(income),'Equivalente USD','payments','featured')}${stat('Egresos del período',usd(out),'Equivalente USD','expenses')}${stat('Balance del período',usd(income-out),'Ingresos menos egresos','reports')}${stat('Deuda vencida actual',usd(state.summary.overdue),'Corte de hoy, independiente del filtro','arrears','alert')}</div><div class="grid-two">${card('Cobros por método',`<div class="card-body">${['Efectivo','Transferencia','Tarjeta','Otro'].map(method=>`<div class="list-line"><span>${method}</span><b>${usd(payments.filter(p=>p.method===method).reduce((t,p)=>t+p.amount,0))}</b></div>`).join('')}<div class="list-line"><span>Recibido en dólares <small>Importe original, sin conversión</small></span><b>${usd(payments.filter(p=>p.currency==='USD').reduce((t,p)=>t+p.received_amount,0))}</b></div><div class="list-line"><span>Recibido en bolívares <small>Importe original, sin conversión</small></span><b>${bs(payments.filter(p=>p.currency==='VES').reduce((t,p)=>t+p.received_amount,0))}</b></div><p class="hint">El equivalente USD usa la tasa conservada en cada operación; sumar bolívares no cambia los saldos históricos.</p></div>`)}${card('Exportación de libros',`<div class="card-body"><p class="muted">Descargas completas para abrir en Excel. Incluyen operaciones anuladas identificadas como tales.</p><div class="list-line"><span>Morosidad actual</span>${exportBtn('arrears','Descargar')}</div><div class="list-line"><span>Historial de pagos y tasas</span>${exportBtn('payments','Descargar')}</div><div class="list-line"><span>Alumnos y saldos</span>${exportBtn('students','Descargar')}</div><div class="list-line"><span>Egresos y nómina</span>${exportBtn('expenses','Descargar')}</div></div>`)}</div>`;
}
function settingsPage() {
  const s=state.settings;
  return heading('Tu colegio y tus datos','Personaliza la institución y mantén sus cuentas protegidas.') +
    `<div class="settings-intro"><div>${schoolLogo()}<div><b>${esc(s.school_name)}</b><span>${esc(s.legal_name||'Completa la razón social de tu colegio')}</span></div></div><span class="badge">Una PC · Base USD</span></div>`+
    card('Identidad y calendario',`<form class="card-body" data-endpoint="settings"><h3>Datos que aparecerán en los documentos</h3><p class="hint">Cada documento conserva la identidad que tenía al emitirse.</p><div class="form-grid">${field('Nombre del colegio','school_name',s.school_name,'text','required maxlength="200"')}${field('Tipo de institución','institution_type',s.institution_type||'','text','maxlength="100"')}${field('Razón social / nombre legal','legal_name',s.legal_name,'text','maxlength="200"')}${field('RIF del colegio','rif',s.rif,'text','maxlength="100"')}${textarea('Domicilio fiscal','fiscal_address',s.fiscal_address,500)}${field('Dirección de contacto','address',s.address,'text','maxlength="500"')}${field('Teléfono','phone',s.phone,'tel','maxlength="100"')}${field('Correo','email',s.email,'email','maxlength="200"')}${field('Sitio web','website',s.website,'text','maxlength="200"')}<div class="field full logo-editor"><div id="logo-preview">${schoolLogo()}</div><label>Logo del colegio · PNG o JPG<input id="school-logo-file" type="file" accept="image/png,image/jpeg"><small>Se ajusta sobre fondo blanco y se guarda en la base y sus respaldos.</small></label><input type="hidden" name="logo" value="${esc(s.logo||'')}">${btn('Quitar logo','remove-logo','small')}</div></div><details class="settings-disclosure"><summary>Calendario y reglas de mensualidades</summary><div class="form-grid">${field('Año de inicio del ciclo escolar','school_year',s.school_year,'number','required min="2000" max="2100"','2026 significa 2026–2027.')}${select('Mes de inicio del ciclo','start_month',Array.from({length:12},(_,i)=>[i+1,new Date(2020,i,1).toLocaleDateString('es-VE',{month:'long'})]),s.start_month)}${field('Día de vencimiento mensual','due_day',s.due_day,'number','required min="1" max="31"','En meses cortos se utiliza el último día.')}</div><p class="hint">Se cobra el mes completo, sin prorrateo por días. Los meses hasta hoy se generan automáticamente para matrículas activas. Las becas se aplican a cargos nuevos; los cargos existentes conservan su importe. El mes de inicio no se cambia con alumnos registrados. El cambio de año se hace en Alumnos → Pase de año / grados.</p></details><details class="settings-disclosure"><summary>Segunda copia de seguridad · USB o carpeta de Drive</summary>${demoMode?'<p>Los datos de prueba se eliminan al cerrar. No se copian a respaldos reales.</p>':field('Ruta completa de la carpeta de copias','backup_directory',s.backup_directory,'text','maxlength="500"','Ejemplo: E:\\RespaldosColegio. Se copian respaldos verificados, nunca la base activa.')}<p class="hint">Si el USB está desconectado o el disco falla, aparecerá un aviso. Una carpeta de Drive se sincroniza mediante su aplicación cuando hay conexión.</p></details><div class="error" role="alert"></div><div class="form-actions"><button class="btn primary" type="submit">Guardar cambios del colegio</button></div></form>`)+
    `<div class="grid-two">${card('Protección y mantenimiento',`<div class="card-body"><p class="maintenance-status">${icon('shield')} ${backupLabel()}</p><p class="data-path">${esc(state.backup?.data_path||'')}</p><p class="hint">La base real está en esta PC. No la muevas ni la reemplaces mientras Aula esté abierta.</p><div class="maintenance-actions">${demoMode?'':btn('Crear respaldo ahora','backup-now','primary')+'<a class="btn" href="/api/backup" download>Descargar copia</a>'}${btn('Verificar datos y cobros','maintenance-review')}${btn('Cómo actualizar o restaurar','maintenance-help')}</div><p class="hint">Respaldo después de cobros y cada cinco minutos. Conserva otra copia fuera de este disco. Una actualización del programa conserva la base.</p>${state.backup?.secondary_directory?`<p>Segundo destino: ${esc(state.backup.secondary_directory)}</p>`:demoMode?'':'<p class="text-red">Falta configurar una segunda carpeta de respaldos.</p>'}</div>`)}${card('Usuarios y acceso',table(['Nombre / usuario','Perfil',''],state.users,u=>`<td><b>${esc(u.name)}</b><span class="sub">${esc(u.username)}</span></td><td>${roleLabel(u.role)}</td><td>${btn('Cambiar clave','password','small',u.id)}</td>`),btn('Crear usuario','user','small'))}</div>`+
    `<details class="settings-disclosure audit-disclosure"><summary>Ver bitácora de operaciones · últimas 300</summary>${table(['Fecha','Usuario','Operación','Detalle'],state.audit,a=>`<td>${esc(new Date(a.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}</td><td>${esc(a.operator)||'Sistema'}</td><td>${esc(a.action)}</td><td class="audit-detail" title="${esc(a.details)}">${esc(a.details)}</td>`,'Sin operaciones')}</details>`+
    (demoMode?'':`<details class="reset-settings"><summary>Administración avanzada · vaciar registros</summary><p>Elimina registros administrativos y financieros. Exige contraseña, revisión y respaldo verificado. No se necesita para actualizar el programa ni para hacer pruebas.</p>${btn('Revisar vaciado de registros','reset-review','danger')}</details>`);
}

function showModal(title, subtitle, body) {
  modal.classList.remove('document-modal','wide-modal');
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
function openEmployee(id) {
  if(!state.positions.length){toast('Crea primero un cargo para el personal.');openPositions();return;}
  const r=state.employees.find(e=>e.id===Number(id))||{};
  showModal(r.id?'Editar empleado':'Nuevo empleado','Sueldo de referencia en dólares; los pagos se preparan en bolívares.',recordForm('employees',field('Nombre completo','name',r.name,'text','required maxlength="200"')+field('Cédula / documento','document',r.document,'text','required maxlength="200"')+select('Cargo','position_id',state.positions.map(p=>[p.id,p.name]),r.position_id||state.positions[0].id,'required')+field('Teléfono','phone',r.phone,'tel')+field('Salario de referencia · USD','salary',r.id?(r.salary/100).toFixed(2):'','number','required min="0" step="0.01" max="999999999"')+select('Estado','status',statusOptions,r.status||'active')+field('Banco','bank',r.bank,'text','maxlength="100"')+field('Número de cuenta bancaria','bank_account',r.bank_account,'text','inputmode="numeric" pattern="[0-9]{20}" maxlength="20"','20 dígitos. Se conservan los ceros iniciales.')+select('Tipo de cuenta','account_type',[['','Selecciona'],['Corriente','Corriente'],['Ahorro','Ahorro']],r.account_type)+field('Titular de la cuenta','account_holder',r.account_holder||r.name,'text','maxlength="200"')+field('Cédula del titular','holder_document',r.holder_document||r.document,'text','maxlength="200"'),r));
}
function openPositions(id) {
  const r=state.positions.find(p=>p.id===Number(id))||{};
  showModal('Cargos del personal','Los cargos se reutilizan; el salario se define para cada empleado.',recordForm('positions',field('Nombre del cargo','name',r.name,'text','required maxlength="200"'),r)+table(['Cargo',''],state.positions,p=>`<td>${esc(p.name)}</td><td>${btn('Editar','positions','small',p.id)}</td>`));
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
function openPayrollPlan() {
  const list=state.employees.filter(e=>e.status==='active');
  if(!list.length){toast('Registra empleados activos primero.',true);return;}
  showModal('Preparar nómina consolidada','Ajusta el monto de cada empleado. Generar el documento no registra pagos.',`<form data-endpoint="payroll-plans"><div class="form-grid">${field('Descripción / período','name','Nómina · '+monthLabel(state.today.slice(0,7)),'text','required maxlength="200"')}${field('Fecha de pago','pay_date',state.today,'date','required')}</div><p class="hint">Revisa las cuentas pendientes en Personal. Los montos propuestos pueden diferir del salario de referencia.</p>${table(['Empleado / banco','Cuenta','Monto USD','Monto Bs'],list,e=>`<td><b>${esc(e.name)}</b><span class="sub">${esc(e.document)} · ${esc(e.bank)||'BANCO PENDIENTE'}</span></td><td>${esc(e.bank_account)||'CUENTA PENDIENTE'}</td><td><input aria-label="Monto USD de ${esc(e.name)}" data-payroll-employee="${e.id}" type="number" min="0" max="999999999" step="0.01" required value="${(e.salary/100).toFixed(2)}"></td><td class="money" data-payroll-bs="${e.id}"></td>`)}<div class="conversion" id="payroll-total"></div>${formFoot('Generar relación de pago')}</form>`);
  updatePayroll();
}
function updatePayroll() {
  const form=$('form[data-endpoint="payroll-plans"]',modal);if(!form)return;
  const rate=state.rates.find(r=>r.rate_date===form.elements.pay_date.value);let total=0,totalBs=0;
  form.querySelectorAll('[data-payroll-employee]').forEach(input=>{const cents=Math.round(Number(input.value||0)*100), ves=Math.round(cents*Number(rate?.rate||0));total+=cents;totalBs+=ves;form.querySelector(`[data-payroll-bs="${input.dataset.payrollEmployee}"]`).textContent=rate?bs(ves):'Falta tasa';});
  $('#payroll-total').innerHTML=rate?`BCV: Bs ${esc(rate.rate)} por USD<strong>Total: ${usd(total)} · ${bs(totalBs)}</strong>`:'Registra primero la tasa para esta fecha en Tasas y respaldo.';
}
function openPayment(id) {
  const candidates=state.students.filter(s=>s.balance>0);
  if(!candidates.length) { showModal('Sin saldos pendientes','Las mensualidades hasta el mes actual ya están calculadas.',`<p>No hay deuda por cobrar en las matrículas registradas. Para un anticipo puedes preparar el mes futuro que corresponda, o crear un cargo de inscripción u otro concepto.</p><div class="form-actions">${btn('Crear cargo','charge','primary')}${btn('Preparar otro período','generate')}</div>`);return; }
  showModal('Registrar pago','El abono se aplica a los cargos pendientes más antiguos.',`<form data-endpoint="payments"><input type="hidden" name="request_key" value="${requestKey()}"><div class="form-grid">${select('Alumno','student_id',candidates.map(s=>[s.id,`${s.name} · ${usd(s.balance)}`]),id||candidates[0].id,'required')}${field('Fecha del pago','paid_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda recibida','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],'USD')}${field('Importe recibido','amount','','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',['Efectivo','Transferencia','Tarjeta','Otro'].map(m=>[m,m]),'Transferencia')}${field('Referencia bancaria / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div><div class="full" id="duplicate-reference"></div>${textarea('Observaciones','notes')}</div><div class="actions" style="margin-top:15px">${btn('Completar saldo','full-payment','small')}${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar y emitir recibo')}</form>`);
  updateConversion();
}
function updateConversion() {
  const form=$('form[data-endpoint="payments"]',modal)||$('form[data-endpoint="expenses"]',modal);
  if(!form)return;
  const data=Object.fromEntries(new FormData(form)), rate=state.rates.find(r=>r.rate_date===(data.paid_on||data.spent_on)), amount=Number(data.amount||0), student=state.students.find(s=>s.id===Number(data.student_id));
  const panel=$('#conversion',form);
  if(form.dataset.endpoint==='payments')checkReference(form);
  if(data.currency==='VES'&&!rate) {panel.innerHTML=`<span class="text-red">Falta la tasa BCV del ${dateLabel(data.paid_on||data.spent_on)}. Regístrala antes de guardar.</span>`;return;}
  const equivalent=data.currency==='VES'?Math.round(amount/Number(rate.rate)*100):Math.round(amount*100);
  panel.innerHTML=`${data.currency==='VES'?`BCV registrada: Bs ${esc(rate.rate)} por USD`:'Pago directo en dólares'}<strong>Equivalente: ${usd(equivalent)}</strong>${student?`Saldo antes del pago: ${usd(student.balance)} · Después: ${usd(student.balance-equivalent)}`:'El egreso se incluirá en reportes por su equivalente USD.'}`;
}
function openExpense(employeeId) {
  const emp=state.employees.find(e=>e.id===Number(employeeId));
  showModal(emp?'Registrar pago de nómina':'Registrar egreso','Conserva el importe original, su moneda y la tasa BCV de la fecha.',`<form data-endpoint="expenses"><div class="form-grid">${field('Concepto','concept',emp?`Nómina · ${emp.name}`:'','text','required maxlength="200"')}${select('Categoría','category',['Operación','Nómina','Servicios','Mantenimiento','Materiales','Otro'].map(x=>[x,x]),emp?'Nómina':'Operación')}${field('Fecha del egreso','spent_on',state.today,'date',`required max="${state.today}"`)}${select('Empleado asociado','employee_id',[['','No aplica'],...state.employees.map(e=>[e.id,e.name])],emp?.id||'')}${select('Moneda pagada','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],emp?'VES':'USD')}${field('Importe pagado','amount',emp?(Math.round(emp.salary*Number(todayRate()?.rate||0))/100).toFixed(2):'','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',['Efectivo','Transferencia','Tarjeta','Otro'].map(m=>[m,m]),'Transferencia')}${field('Referencia / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div><section id="salary-fields" class="field full">${salaryFields()}</section></div><div class="actions" style="margin-top:15px">${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar egreso')}</form>`);updateSalaryFields();updateConversion();
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
  if(kind!=='employees'&&filters.archived)query.set('archived','1');
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
  return `<div class="actions document-actions">${isReceipt?`<label class="receipt-paper-control">Tamaño del recibo<select id="receipt-paper"><option value="half-letter" ${receiptPaper==='half-letter'?'selected':''}>Media carta · horizontal</option><option value="a4" ${receiptPaper==='a4'?'selected':''}>A4 · vertical</option><option value="ticket-80" ${receiptPaper==='ticket-80'?'selected':''}>Ticket térmico · 80 mm</option><option value="ticket-58" ${receiptPaper==='ticket-58'?'selected':''}>Ticket térmico · 58 mm</option></select></label>`:''}<a class="btn primary" href="/api/${path}.pdf${isReceipt?'?paper='+receiptPaper:''}" download>${icon('download')} Descargar PDF</a>${btn(`${icon('print')} Imprimir`,'print-receipt')}</div>${isReceipt?'<p class="receipt-paper-help" id="receipt-paper-help"></p>':''}`;
}
function setReceiptPaper(paper) {
  receiptPaper=['a4','half-letter','ticket-58','ticket-80'].includes(paper)?paper:'half-letter';
  document.querySelectorAll('.payment-receipt').forEach(el=>{el.classList.toggle('receipt-half-letter',receiptPaper==='half-letter');el.classList.toggle('receipt-ticket',receiptPaper.startsWith('ticket-'));el.classList.toggle('receipt-ticket-58',receiptPaper==='ticket-58');el.classList.toggle('receipt-ticket-80',receiptPaper==='ticket-80');});
  const link=modal.querySelector('.document-actions a[download]');
  if(link){const url=new URL(link.href);url.searchParams.set('paper',receiptPaper);link.href=url.pathname+url.search;}
  const help=$('#receipt-paper-help');
  if(help)help.textContent=receiptPaper.startsWith('ticket-')?'Ticket de '+receiptPaper.slice(-2)+' mm. Selecciona la impresora térmica y usa escala 100 %. La impresión depende del controlador instalado en Windows.':receiptPaper==='half-letter'?'21,59 × 13,97 cm. Al imprimir, usa tamaño real (100 %) para que no se amplíe a toda la hoja.':'A4 vertical. Recomendado para muchos conceptos u observaciones extensas.';
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
async function payrollDocument(id) {
  const d=await api('payroll-plan/'+id);
  showDocument('Relación de pago consolidada','payroll-plan/'+id,`<article class="receipt school-document payroll-document">${schoolHeader(d.school,'Relación de pago','N-'+String(id).padStart(6,'0'),d.pay_date)}<h3>${esc(d.name)}</h3><p>BCV aplicada: Bs ${esc(d.rate)} por USD · ${dateLabel(d.pay_date)}</p><p class="hint">Preparación de nómina. Este documento no registra egresos ni acredita pagos realizados.</p>${table(['Empleado / cédula / cargo','Banco / tipo / cuenta','Titular / cédula','Monto USD','Monto Bs'],d.lines,r=>`<td>${esc(r.name)}<span class="sub">${esc(r.document)} · ${esc(r.position)}</span></td><td>${esc(r.bank)||'BANCO PENDIENTE'}<span class="sub">${esc(r.account_type)} · ${esc(r.bank_account)||'CUENTA PENDIENTE'}</span></td><td>${esc(r.account_holder||r.name)}<span class="sub">${esc(r.holder_document||r.document)}</span></td><td>${usd(r.amount_usd)}</td><td>${bs(r.amount_ves)}</td>`)}<div class="receipt-total">Total propuesto: <b>${usd(d.total_usd)} · ${bs(d.total_ves)}</b></div><div class="signature-row"><span>Preparado por ${esc(d.operator)}</span><span>Aprobado por</span></div></article>`);
}
async function receipt(id) {
  const r=await api('receipt/'+id), p=r.payment;
  const period = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value)?monthLabel(value):value;
  const markup=`<article class="receipt school-document payment-receipt">${schoolHeader(r.settings,'Comprobante de pago','R-'+String(p.id).padStart(6,'0'),p.paid_on)}${p.voided?`<div class="receipt-void"><b>COMPROBANTE ANULADO</b><p>${esc(p.void_reason)}</p></div>`:''}<div class="receipt-parties"><section><span class="receipt-label">Representante legal</span><h2>${esc(p.guardian_name)}</h2><p>Cédula: ${esc(p.guardian_document)}</p>${p.guardian_phone?`<p>${esc(p.guardian_phone)}</p>`:''}</section><section><span class="receipt-label">Alumno · Grado / sección</span><h2>${esc(p.student_name)}${p.grade_name?`<span class="receipt-student-grade"> · ${esc(p.grade_name)}</span>`:''}</h2>${p.grade_name?'':'<p>Grado no registrado</p>'}<p>Código: ${esc(p.student_code||p.student_document)}</p></section></div>${p.guardian_address?`<p class="receipt-address"><span>Dirección del representante</span>${esc(p.guardian_address)}</p>`:''}<section class="receipt-charges"><h3 class="receipt-label">Conceptos abonados</h3>${table(['Descripción','Período','Aplicado · USD','Pendiente · USD'],r.allocations,a=>`<td>${esc(a.concept)}</td><td>${esc(period(a.period))}</td><td class="money">${usd(a.amount)}</td><td class="money">${a.balance_after===undefined?'—':usd(a.balance_after)}</td>`)}</section><div class="receipt-payment"><section class="receipt-method"><span class="receipt-label">Método de pago</span><p class="receipt-method-name">${esc(p.method)}</p>${p.reference?`<span class="receipt-label">Referencia / comprobante</span><p>${esc(p.reference)}</p>`:''}</section><section class="receipt-amount"><span class="receipt-label">Importe recibido · ${p.currency==='VES'?'Bolívares':'USD'}</span><div class="receipt-amount-value">${p.currency==='VES'?bs(p.received_amount):usd(p.received_amount)}</div><div class="receipt-applied"><span>Total aplicado en USD</span><b>${usd(p.amount)}</b></div>${p.currency==='VES'?`<p class="receipt-rate">Tasa BCV aplicada: Bs ${esc(p.exchange_rate)} por USD</p>`:''}</section></div>${receiptBalance(p)}${p.notes?`<section class="receipt-notes"><span class="receipt-label">Observaciones</span><p>${esc(p.notes)}</p></section>`:''}<div class="signature-row"><span>Firma de administración</span><span>Firma del representante</span></div><footer class="receipt-bottom"><p>Registrado por: ${esc(p.operator)}</p><p>Comprobante administrativo · No sustituye una factura fiscal.</p></footer></article>`;
  showDocument('Comprobante de pago','receipt/'+id,markup);
}
function printReport() {
  const income=state.payments.filter(p=>!p.voided&&p.paid_on>=reportFrom&&p.paid_on<=reportTo).reduce((t,p)=>t+p.amount,0), expenses=state.expenses.filter(e=>!e.voided&&e.spent_on>=reportFrom&&e.spent_on<=reportTo).reduce((t,e)=>t+e.amount,0);
  $('#print-area').innerHTML=`<article class="receipt school-document">${schoolHeader(state.settings,'Resumen administrativo','',state.today)}<p>Período: ${dateLabel(reportFrom)} al ${dateLabel(reportTo)}</p><dl><dt>Ingresos USD</dt><dd>${usd(income)}</dd><dt>Egresos USD</dt><dd>${usd(expenses)}</dd><dt>Balance USD</dt><dd>${usd(income-expenses)}</dd><dt>Deuda vencida actual</dt><dd>${usd(state.summary.overdue)}</dd><dt>Alumnos activos</dt><dd>${state.summary.active_students}</dd></dl><p class="hint">Generado el ${dateLabel(state.today)}. Importes convertidos con la tasa almacenada en cada operación. El saldo vencido corresponde al corte actual.</p></article>`;window.print();
}
document.addEventListener('click',async event=>{
  const target=event.target.closest('[data-action]');if(!target)return;
  const {action,id}=target.dataset;
  try {
    switch(action) {
      case 'nav':page=id;filters={};render();break;
      case 'close':modal.close();break;
      case 'boot':await boot();break;
      case 'demo-exit':await closeDemo();break;
      case 'reset-review':await openResetRecords();break;
      case 'salary-document':await salaryDocument(id);break;
      case 'salary-receipt':openSalaryReceipt(id);break;
      case 'logout':await api('logout',{});modal.close();await boot();break;
      case 'year-transition':openYearTransition();break;case 'load-year':await loadYear();break;case 'preview-year':await previewYear();break;case 'confirm-year':await confirmYear();break;case 'year-document':await yearDocument(id);break;case 'payment-plan':openPaymentPlan(id);break;case 'plan-document':await planDocument(id);break;case 'cancel-plan':openVoid('cancel-plan',id);break;case 'import-roster':openImport();break;case 'import-guide':await openImportGuide();break;case 'recovery-help':recoveryHelp();break;case 'maintenance-help':maintenanceHelp();break;case 'maintenance-review':await maintenanceReview();break;case 'backup-now':await backupNow();break;case 'remove-logo':{const form=target.closest('form');form.elements.logo.value='';$('#logo-preview',form).innerHTML=schoolLogo({});break;}case 'preview-import':await previewImport();break;case 'confirm-import':await confirmImport();break;case 'guardian-account':await guardianAccount(id);break;case 'issue-account':await issueGuardian(id,'account');break;case 'issue-solvency':await issueGuardian(id,'solvency');break;case 'guardian-document':await guardianDocument(id);break;case 'open-cash':await openCash();break;case 'cash-document':await cashDocument(id);break;case 'reopen-cash':openVoid('reopen-cash',id);break;case 'guardian':openGuardian(id);break;case 'grade':openGrade(id);break;case 'student':openStudent(id);break;
      case 'positions':openPositions(id);break;case 'payroll-plan':openPayrollPlan();break;case 'payroll-document':await payrollDocument(id);break;case 'enrollment':await enrollmentDocument(id);break;case 'employee':openEmployee(id);break;case 'payment':openPayment(id);break;case 'expense':openExpense();break;
      case 'payroll':openExpense(id);break;case 'charge':openCharge(id);break;case 'generate':openGenerate();break;
      case 'rates':openRates();break;case 'account':account(id);break;case 'collection':collection(id);break;case 'followup':openFollowup(id);break;
      case 'delete-grade':case 'archive-student':case 'archive-guardian':case 'restore-student':case 'restore-guardian':openDirectoryAction(action,id);break;
      case 'correct-billing':openBillingCorrection(id);break;
      case 'void-payment':case 'void-expense':case 'cancel-charge':openVoid(action,id);break;
      case 'user':openUser();break;case 'password':openPassword(id);break;case 'receipt':await receipt(id);break;
      case 'daily-report':await openDailyReport();break;case 'directory-report':await openDirectoryReport(id);break;case 'print-receipt':window.print();break;case 'print-report':printReport();break;
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
  event.preventDefault();const endpoint=form.dataset.endpoint, data=Object.fromEntries(new FormData(form));
  if(endpoint==='correct-billing-start'){data.charge_ids=JSON.parse(data.charge_ids);data.confirmed=form.elements.confirmed.checked;}
  if(endpoint==='payment-plans'){data.expected_total=Number(data.expected_total);data.installments=Array.from(form.querySelectorAll('[data-plan-row]')).map(row=>({amount:row.querySelector('[data-plan-amount]').value,due_date:row.querySelector('[data-plan-date]').value}));}
  if(endpoint==='payroll-plans') data.lines=Array.from(form.querySelectorAll('[data-payroll-employee]')).map(input=>({employee_id:input.dataset.payrollEmployee,amount:input.value}));
  const submit=form.querySelector('[type="submit"]'), errorBox=$('.error',form);submit.disabled=true;errorBox.textContent='';
  try {
    const result=await api(endpoint,data);
    if(endpoint==='reset-records'){modal.close();await boot();toast('Registros vaciados. Respaldo previo: '+result.backup_path);return;}
    if(['login','setup','demo-login'].includes(endpoint)){await boot();return;}
    if(endpoint==='confirm-rate'){await refresh();return;}
    if(endpoint==='password'&&Number(data.user_id)===state.user.id){modal.close();await boot();return;}
    await refresh();if(endpoint!=='rates')modal.close();
    if(endpoint==='payment-plans'){toast('Convenio guardado.');await planDocument(result.id);}
    else if(endpoint==='close-cash'){toast('Caja cerrada.');await cashDocument(result.id);}
    else if(endpoint==='expenses'&&result.salary_receipt_id){toast('Pago de sueldo registrado.');await salaryDocument(result.salary_receipt_id);}
    else if(endpoint==='salary-receipts'){await salaryDocument(result.id);}
    else if(endpoint==='payments'){toast(result.duplicate?'El pago ya estaba registrado.':'Pago registrado correctamente.');await receipt(result.id);}
    else if(endpoint==='students'){toast(`Matrícula guardada · ${result.student_code}`);await enrollmentDocument(result.id,result.document_id);}
    else if(endpoint==='payroll-plans'){await payrollDocument(result.id);}
    else if(endpoint==='correct-billing-start'){toast(`${result.cancelled} mensualidades anuladas con motivo. Se conservaron los pagos.`);account(result.id);}
    else if(endpoint==='delete-grade')toast('Grado / sección eliminado.');
    else if(endpoint.startsWith('archive-'))toast('Ficha eliminada del directorio y archivada. El historial se conserva.');
    else if(endpoint.startsWith('restore-'))toast('Ficha recuperada. Revisa y activa la matrícula cuando corresponda.');
    else if(endpoint==='generate')toast(`${result.created} mensualidades creadas. Los cargos existentes no se duplicaron.`);
    else {toast('Registro guardado correctamente.');if(endpoint==='rates')openRates();}
    if(result.backup_warning)toast('Operación guardada. '+result.backup_warning,true);
  }catch(error){errorBox.textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.id==='collection-text'){const link=$('#wa-collection');if(link){const url=new URL(link.href);url.searchParams.set('text',el.value);link.href=url.href;}}
  if(el.id==='plan-count'){buildPlanRows();return;}
  if(el.closest('form[data-endpoint="correct-billing-start"]')&&el.name==='billing_start')updateBillingCorrection();
  if(el.id==='search'){
    const pos=el.selectionStart;filters.search=el.value;$('#page-content').innerHTML=pageBody();$('#search').focus();$('#search').setSelectionRange(pos,pos);
  }
  if(el.closest('form[data-endpoint="close-cash"]'))updateCashCount();
  if(el.id==='guardian-search')searchGuardian();
  if(el.closest('form[data-endpoint="students"]'))updateTuition();
  if(el.closest('form[data-endpoint="payroll-plans"]'))updatePayroll();
  if(el.closest('form[data-endpoint="payments"], form[data-endpoint="expenses"]'))updateConversion();
});
document.addEventListener('change',event=>{
  if(event.target.closest('form[data-endpoint="expenses"]')&&event.target.name==='category')updateSalaryFields();
  if(event.target.id==='show-archived'){filters.archived=event.target.checked;$('#page-content').innerHTML=pageBody();return;}
  if(event.target.id==='receipt-paper'){setReceiptPaper(event.target.value);return;}
  const el=event.target;
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
  if(el.closest('form[data-endpoint="payroll-plans"]'))updatePayroll();
  if(el.closest('form[data-endpoint="payments"], form[data-endpoint="expenses"]'))updateConversion();
});
modal.addEventListener('click',event=>{if(event.target===modal){const r=modal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)modal.close();}});
modal.addEventListener('close',()=>{if(!modal.open)$('#modal-content').replaceChildren();});
async function checkDay() {
  if(!state||document.hidden)return;
  try {const gate=await api('rate-gate');if(state&&gate.today!==state.today)await openRateGate();else if(state){state.backup=await api('backup-status');document.querySelectorAll('.backup-status').forEach(el=>{el.innerHTML=backupLabel();el.classList.toggle('text-red',backupStale());});}}catch(error){toast(error.message,true);}
}
setInterval(checkDay,60000);
document.addEventListener('visibilitychange',checkDay);
boot();

let rosterFile, rosterPreview, cashPreview, cashDate='';
function backupStale(){if(demoMode)return false;const time=Date.parse(state.backup?.local_at||'');return !Number.isFinite(time)||Date.now()-time>86400000||!!state.backup?.local_error;}
function backupLabel(){
  if(demoMode)return 'Pruebas · datos temporales';
  const b=state.backup||{};
  if(b.local_error)return esc(b.local_error);
  if(!Number.isFinite(Date.parse(b.local_at||'')))return 'Sin respaldo automático confirmado';
  const minutes=Math.max(0,Math.floor((Date.now()-Date.parse(b.local_at))/60000));
  return 'Último respaldo '+(minutes<1?'hace menos de un minuto':minutes<60?`hace ${minutes} min`:minutes<1440?`hace ${Math.floor(minutes/60)} h`:`hace ${Math.floor(minutes/1440)} días`);
}
function backupProblem(){if(demoMode)return '';const b=state.backup||{};return b.local_error||b.secondary_error?`<div class="notice backup-warning" role="alert"><div><b>Revisa los respaldos</b><p>${esc(b.local_error||b.secondary_error)}</p></div></div>`:'';}
function openImport(){
  rosterFile=rosterPreview=undefined;
  showModal('Importar alumnos y representantes','Carga inicial con vista previa. No modifica alumnos ni representantes existentes.',`<p>Descarga la plantilla, completa una fila por alumno y conserva los encabezados. Los hermanos pueden repetir los datos del mismo representante.</p><div class="actions"><a class="btn" href="/api/import-template?format=xlsx" download>Plantilla Excel (.xlsx)</a><a class="btn" href="/api/import-template" download>Plantilla CSV</a>${btn('Guía columna por columna','import-guide')}</div><p class="hint">Fechas: AAAA-MM-DD o fechas de Excel. Mensualidad base: dólares sin símbolos ni miles, hasta dos decimales; el descuento va aparte. Grado: nombre exacto del catálogo. Año escolar: año de inicio. Cédulas, teléfonos y códigos: texto. Sin fórmulas. Se admite .xlsx o CSV UTF-8, hasta 2 MB / 1000 alumnos.</p><label class="field">Archivo<input id="roster-file" type="file" accept=".csv,.xlsx"></label><div class="notice"><div><b>Revisa el primer mes a cobrar</b>Usa primer_mes_cobro en formato AAAA-MM. Si lo dejas vacío, comienza en el mes de carga (o al iniciar el período si es futuro), aunque el período académico empiece en septiembre. Las deudas anteriores se registran expresamente. Los períodos ya terminados requieren escoger un mes del ciclo.</div></div><div class="actions">${btn('Revisar archivo','preview-import','primary')}</div><div id="roster-preview" aria-live="polite"></div>`);
  modal.classList.add('wide-modal');
}
async function previewImport(){
  const file=$('#roster-file').files[0];if(!file)throw new Error('Selecciona el archivo primero.');
  if(file.size>2000000)throw new Error('El archivo supera 2 MB.');
  const button=modal.querySelector('[data-action="preview-import"]');button.disabled=true;
  try{
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
    for(let i=0;i<bytes.length;i+=4096)binary+=String.fromCharCode(...bytes.subarray(i,i+4096));
    rosterFile={filename:file.name,content:btoa(binary)};
    rosterPreview=await api('import-roster',{...rosterFile,preview:true});
    $('#roster-preview').innerHTML=`<h3>Vista previa · ${rosterPreview.rows} filas</h3><p>${rosterPreview.students} alumnos válidos · ${rosterPreview.guardians} representantes nuevos · cargos nuevos: <b>${usd(rosterPreview.new_balance)}</b>.</p>${rosterPreview.errors.length?`<p class="text-red">${rosterPreview.errors.length} errores. No se guardará ninguna fila hasta corregir el archivo.</p>${table(['Fila','Error'],rosterPreview.errors,e=>`<td>${e.row}</td><td class="wrap-cell">${esc(e.message)}</td>`)}`:`<p class="text-green">Sin errores de validación. Los códigos se asignarán al confirmar.</p>${table(['Fila','Alumno','Representante','Grado','Cobrar desde'],rosterPreview.lines,r=>`<td>${r.row}</td><td>${esc(r.student_name)}</td><td>${esc(r.guardian_name)}</td><td>${esc(r.grade_name)}</td><td>${esc(r.billing_start)}</td>`)}${rosterPreview.rows>100?'<p>Se muestran las primeras 100 filas; todas fueron validadas.</p>':''}<label class="confirm-check"><input id="import-reviewed" type="checkbox"> Revisé las fechas, las tarifas y los cargos que se crearán.</label><div class="form-actions">${btn('Confirmar importación','confirm-import','primary')}</div>`}`;
  }finally{button.disabled=false;}
}
async function confirmImport(){
  if(!rosterPreview||rosterPreview.errors.length||!$('#import-reviewed')?.checked)throw new Error('Revisa la vista previa y marca la confirmación.');
  const button=modal.querySelector('[data-action="confirm-import"]');button.disabled=true;
  try{const result=await api('import-roster',{...rosterFile,confirmed_hash:rosterPreview.hash,confirmed_month:rosterPreview.billing_default});modal.close();page='students';filters={};await refresh();toast(`${result.students} alumnos y ${result.guardians} representantes importados.`);if(result.backup_warning)toast('Importación guardada. '+result.backup_warning,true);}
  finally{button.disabled=false;}
}
function accountFamilyMarkup(d){
  return `<div class="mini-summary"><div><small>Saldo familiar USD</small><b>${usd(d.balance)}</b></div><div><small>Vencido USD</small><b class="text-red">${usd(d.overdue)}</b></div></div>${table(['Alumno / código','Grado','Año escolar'],d.students,s=>`<td>${esc(s.name)}<span class="sub">${esc(s.student_code)}</span></td><td>${esc(s.grade_name)}</td><td>${s.school_year}–${s.school_year+1}</td>`)}<h3>Cargos de la familia</h3>${table(['Alumno / concepto / período','Vence','Cargo','Abonado','Saldo'],d.charges,c=>`<td>${esc(c.student_name)}<span class="sub">${esc(c.concept)} · ${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td>${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}</td>`,'No hay cargos registrados')}<h3>Pagos registrados</h3>${table(['Recibo / alumno','Fecha','Recibido','Aplicado USD','Estado'],d.payments,p=>`<td>R-${String(p.id).padStart(6,'0')}<span class="sub">${esc(p.student_name)}</span></td><td>${dateLabel(p.paid_on)}</td><td>${p.currency==='VES'?bs(p.received_amount):usd(p.received_amount)}</td><td>${usd(p.amount)}</td><td>${p.voided?'Anulado':'Válido'}</td>`,'Sin pagos registrados')}`;
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
function cashBreakdown(d){return table(['Método','Moneda','Ingresos recibidos','Egresos pagados','Neto'],d.lines,r=>`<td>${esc(r.method)}</td><td>${esc(r.currency)}</td><td>${nativeAmount(r.income,r.currency)}</td><td>${nativeAmount(r.expense,r.currency)}</td><td>${nativeAmount(r.net,r.currency)}</td>`,'Sin movimientos en esta fecha');}
function cashPage(){
  cashDate ||=state.today;
  return heading('Cierre de caja diario','Corte guardado por método y moneda, con arqueo de efectivo.',writable()?btn('Revisar / cerrar caja','open-cash','primary'):'')+card('Seleccionar fecha',`<div class="card-body">${field('Fecha del cierre','closed_on',cashDate,'date',`id="cash-date" required max="${state.today}"`)}<p class="hint">Registra primero todos los cobros y egresos del día. Usa el método correcto en los egresos. Un cierre bloquea nuevos movimientos y anulaciones de esa fecha; administración puede reabrirlo con un motivo. Los cierres anteriores se conservan.</p></div>`)+card('Cierres guardados',table(['Fecha cerrada','Emitido','Estado',''],state.cash_closures,c=>`<td>${dateLabel(c.closed_on)}</td><td>${esc(new Date(c.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}</td><td>${badge(c.reopened_at?'Reabierto':'Cerrado',c.reopened_at?'neutral':'')}</td><td>${actionsCell(btn('Ver PDF','cash-document','small',c.id)+(admin()&&!c.reopened_at?btn('Reabrir','reopen-cash','small',c.id):''))}</td>`,'Todavía no hay cierres'));
}
async function openCash(){
  cashDate ||=state.today;
  cashPreview=await api('cash-preview?date='+encodeURIComponent(cashDate));
  if(cashPreview.active_id){await cashDocument(cashPreview.active_id);return;}
  showModal('Revisar y cerrar caja','Los importes reales se mantienen separados por moneda.',`<form data-endpoint="close-cash"><input type="hidden" name="preview_hash" value="${cashPreview.preview_hash}">${field('Fecha del cierre','closed_on',cashDate,'date',`id="cash-close-date" required max="${state.today}"`)}${cashBreakdown(cashPreview)}<p class="hint">Equivalente USD: ingresos ${usd(cashPreview.income_usd)} · egresos ${usd(cashPreview.expense_usd)}. El efectivo se cuenta aparte de transferencias y tarjetas. Los egresos antiguos sin método aparecen como «No especificado» y no descuentan efectivo.</p><h3>Arqueo de efectivo</h3><div class="form-grid">${field('Fondo inicial en USD','opening_USD','0.00','number','required min="0" max="999999999" step="0.01"')}${field('Efectivo contado en USD','counted_USD','','number','required min="0" max="999999999" step="0.01"')}${field('Fondo inicial en Bs','opening_VES','0.00','number','required min="0" max="999999999" step="0.01"')}${field('Efectivo contado en Bs','counted_VES','','number','required min="0" max="999999999" step="0.01"')}${textarea('Observaciones / explicación de diferencias','notes')}</div><div id="cash-count-preview" class="conversion" aria-live="polite"></div>${formFoot('Cerrar caja y emitir PDF')}</form>`);
  modal.classList.add('wide-modal');updateCashCount();
}
function updateCashCount(){
  const form=$('form[data-endpoint="close-cash"]',modal);if(!form||!cashPreview)return;
  $('#cash-count-preview').innerHTML=['USD','VES'].map(currency=>{const initial=Math.round(Number(form.elements['opening_'+currency].value||0)*100),expected=initial+cashPreview.lines.filter(r=>r.currency===currency&&r.method==='Efectivo').reduce((a,r)=>a+r.net,0),input=form.elements['counted_'+currency],counted=Math.round(Number(input.value||0)*100);return `<p>Efectivo esperado: <b>${nativeAmount(expected,currency)}</b> · Diferencia: ${input.value?nativeAmount(counted-expected,currency):'pendiente de contar'}</p>`;}).join('');
}
async function cashDocument(id){
  const d=await api('cash-close/'+id);
  showDocument('Cierre de caja','cash-close/'+id,`<article class="receipt school-document">${schoolHeader(d.school,'Cierre de caja','C-'+String(id).padStart(6,'0'),d.closed_on)}${d.reopened_at?`<div class="receipt-void"><b>CIERRE REABIERTO</b><p>${esc(d.reopen_reason)}</p></div>`:''}${cashBreakdown(d)}<h3>Arqueo de efectivo</h3>${table(['Moneda','Fondo inicial','Esperado','Contado','Diferencia'],d.counts,r=>`<td>${esc(r.currency)}</td><td>${nativeAmount(r.opening,r.currency)}</td><td>${nativeAmount(r.expected,r.currency)}</td><td>${nativeAmount(r.counted,r.currency)}</td><td>${nativeAmount(r.difference,r.currency)}</td>`)}<p>Equivalente USD: ingresos ${usd(d.income_usd)} · egresos ${usd(d.expense_usd)}.</p><p class="hint">Arqueo = fondo inicial + cobros en efectivo - egresos en efectivo. Transferencias, tarjetas y egresos sin método se presentan aparte.</p><p>Observaciones: ${esc(d.notes)||'Sin observaciones.'}</p><h3>Movimientos del corte</h3>${table(['Movimiento / referencia','Método','Recibido','Estado'],d.movements,r=>`<td>${r.type==='income'?'R':'E'}-${String(r.id).padStart(6,'0')}<span class="sub">${esc(r.reference)}</span></td><td>${esc(r.method)}</td><td>${nativeAmount(r.received_amount,r.currency)}</td><td>${r.voided?'Anulado':'Válido'}</td>`)}<div class="signature-row"><span>Firma de administración</span><span>Revisado por</span></div><p class="document-footer">Cerrado por ${esc(d.operator)} · Fecha de emisión: ${dateLabel(d.issued_on)}. Conserva el corte original.</p></article>`);
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
  const today=state.today,end=new Date(today+'T12:00:00'),start=new Date(today+'T12:00:00');end.setDate(end.getDate()+6);start.setDate(start.getDate()-7);
  const due=state.charges.filter(c=>c.balance>0&&c.due_date>=today&&c.due_date<=isoDay(end)).sort((a,b)=>a.due_date.localeCompare(b.due_date)||a.id-b.id);
  const newDebtors=state.students.filter(s=>{const overdue=state.charges.filter(c=>c.student_id===s.id&&c.overdue);return overdue.length&&overdue.every(c=>c.due_date>=isoDay(start));});
  const paid=state.payments.filter(p=>!p.voided&&p.paid_on===today);
  return {due,newDebtors,paid};
}
function dashboardOverview({due,newDebtors,paid}){
  const s=state.summary,amount=paid.reduce((sum,p)=>sum+p.amount,0);
  const dollars=paid.filter(p=>p.currency==='USD').reduce((sum,p)=>sum+p.received_amount,0);
  const bolivars=paid.filter(p=>p.currency==='VES').reduce((sum,p)=>sum+p.received_amount,0);
  return `<section class="dashboard-overview" aria-label="Resumen de cobros y deudas">
    <div class="dashboard-main-metrics">
      <div class="dashboard-collected">
        <div class="dashboard-metric-label">${icon('payments')}<h2>Cobrado hoy</h2><span class="dashboard-today-tag">Hoy</span></div>
        <div class="dashboard-amount" id="dashboard-today">${usd(amount)}</div>
        <p class="dashboard-unit">Equivalente en USD · ${paid.length} ${paid.length===1?'cobro':'cobros'}</p>
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
      ${icon('clock')}<span><b>Vencen en los próximos 7 días</b><small>${due.length ? `${due.length} ${due.length===1?'cargo pendiente':'cargos pendientes'} · ${usd(due.reduce((sum,c)=>sum+c.balance,0))} USD` : 'Sin vencimientos pendientes esta semana'}</small></span>${icon('arrow')}
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
  const params=new URLSearchParams(location.search),address=params.get('phone_url'),code=params.get('phone_code');
  const phone=address&&/^\d{6}$/.test(code||'')?`<aside class="demo-banner phone-demo-info"><div><b>Abre Aula en tu teléfono</b><p>Conecta ambos equipos al mismo Wi-Fi. En el navegador del teléfono escribe:</p><strong class="data-path">${esc(address)}</strong><p>Código de acceso: <strong class="phone-demo-code">${esc(code)}</strong></p><small>Mantén esta ventana abierta mientras pruebas en el teléfono. Al cerrar la ventana de la PC, la prueba termina y se borran sus datos.</small></div></aside>`:'';
  return phone+`<aside class="demo-banner" aria-label="Modo prueba"><div><b>Modo prueba · Datos temporales</b><p>Todo lo que registres aquí se elimina al cerrar. Los datos reales del colegio están separados.</p></div>${btn('Cerrar y borrar pruebas','demo-exit','small')}</aside>`;
}
function demoAuth(){
  state=undefined;modal.close();$('#print-area').replaceChildren();document.title='Modo prueba · Aula';
  app.innerHTML=demoBanner()+`<div class="rate-screen"><section class="card gate-card"><div class="brand"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>Tu colegio, en modo prueba</b><small>Datos temporales · acceso de administrador</small></div></div><h1>Prueba con tranquilidad</h1><p>Esta sesión empieza sin alumnos, cobros ni empleados. Puedes probar todos los módulos. Los documentos descargados se identifican como pruebas.</p><form data-endpoint="demo-login"><div class="error" role="alert"></div><button class="btn primary" type="submit">Entrar como administrador de prueba ${icon('arrow')}</button></form><p class="hint">Al cerrar la última pestaña de prueba, espera unos segundos: se cerrará la sesión y se eliminarán sus registros. Descargar un PDF guarda ese archivo en tu PC; puedes borrarlo después.</p></section></div>`;
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
  app.innerHTML=`<div class="rate-screen"><section class="card gate-card"><h1>Sesión de prueba terminada</h1><p>Se está cerrando el programa y eliminando sus datos temporales. Para empezar otra prueba vacía, vuelve a abrir <b>Iniciar-Pruebas.bat</b>.</p><p class="hint">Ya puedes cerrar esta pestaña. Los PDF o CSV que descargaste permanecen en tu carpeta de descargas.</p></section></div>`;
}
window.addEventListener('pagehide',()=>{
  if(demoToken)navigator.sendBeacon('/api/demo-presence',new Blob([JSON.stringify({token:demoToken,client:demoClient,action:'close'})],{type:'application/json'}));
});
window.addEventListener('pageshow',pulseDemo);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)pulseDemo();});

function salaryFields(){
  return `<h3>Período y horario del sueldo</h3><p class="hint">Indica el período cubierto y el horario informado. Estos datos se guardan en el recibo individual para la firma del empleado.</p><div class="form-grid">${field('Período pagado · desde','period_start','','date','required')}${field('Período pagado · hasta','period_end','','date','required')}${field('Hora de entrada','entry_time','','time','required')}${field('Hora de salida','exit_time','','time','required')}${textarea('Observaciones del recibo','salary_notes')}</div>`;
}
function updateSalaryFields(){
  const form=$('form[data-endpoint="expenses"]',modal);if(!form)return;
  const salary=form.elements.category.value==='Nómina',box=$('#salary-fields',form);
  box.hidden=!salary;box.querySelectorAll('input,textarea').forEach(el=>el.disabled=!salary);
  form.elements.employee_id.required=salary;
  form.querySelector('[type="submit"]').textContent=salary?'Registrar pago y emitir recibo':'Registrar egreso';
}
function openSalaryReceipt(id){
  const e=state.expenses.find(e=>e.id===Number(id));if(!e)return;
  showModal('Emitir recibo de sueldo',`${esc(e.employee_name)} · Pago ${dateLabel(e.spent_on)} · ${e.currency==='VES'?bs(e.received_amount):usd(e.received_amount)}`,`<form data-endpoint="salary-receipts"><input type="hidden" name="expense_id" value="${e.id}"><p class="hint">Completa el período y horario de este pago anterior. Se usarán los datos del empleado y del colegio disponibles al emitirlo. No se registra otro egreso.</p>${salaryFields()}${formFoot('Emitir recibo sin volver a pagar')}</form>`);
}
async function salaryDocument(id){
  const d=await api('salary-receipt/'+id),e=d.expense,employee=d.employee,paid=e.currency==='VES'?bs(e.received_amount):usd(e.received_amount);
  showDocument('Recibo de sueldo','salary-receipt/'+id,`<article class="receipt school-document salary-document">${schoolHeader(d.school,'Recibo de sueldo','E-'+String(e.id).padStart(6,'0'),e.spent_on)}${e.voided?`<div class="receipt-void"><b>RECIBO ANULADO</b><p>${esc(e.void_reason)}</p></div>`:''}<section class="document-section"><h3>${esc(employee.name)}</h3><p>Cédula: ${esc(employee.document)} · Cargo: ${esc(employee.position)}</p></section>${table(['Período pagado · desde','Hasta','Entrada','Salida'],[d],r=>`<td>${dateLabel(r.period_start)}</td><td>${dateLabel(r.period_end)}</td><td>${esc(r.entry_time)}</td><td>${esc(r.exit_time)}</td>`)}<p class="salary-concept">${esc(e.concept)}</p><div class="receipt-amount"><span class="receipt-label">Importe recibido · ${e.currency==='VES'?'Bolívares':'USD'}</span><div class="receipt-amount-value">${paid}</div><p>Equivalente USD: <b>${usd(e.amount)}</b>${e.currency==='VES'?` · BCV: Bs ${esc(e.exchange_rate)} por USD`:''}</p></div><section class="document-section"><p>Método: ${esc(e.method)} · Referencia: ${esc(e.reference)||'Sin referencia'}</p>${e.method==='Transferencia'?`<p>Banco registrado: ${esc(employee.bank)||'No registrado'} · Cuenta registrada: ${esc(employee.bank_account)||'No registrada'}</p><p>Titular: ${esc(employee.account_holder||employee.name)} · Cédula: ${esc(employee.holder_document||employee.document)}</p>`:''}</section><p class="salary-acknowledgement">Yo, <b>${esc(employee.name)}</b>, titular de la cédula <b>${esc(employee.document)}</b>, declaro haber recibido <b>${paid}</b> por el sueldo correspondiente al período del <b>${dateLabel(d.period_start)}</b> al <b>${dateLabel(d.period_end)}</b>. Horario informado: entrada <b>${esc(d.entry_time)}</b> y salida <b>${esc(d.exit_time)}</b>.</p>${d.notes?`<p class="salary-notes">Observaciones: ${esc(d.notes)}</p>`:''}<div class="signature-row"><span>Pagado por administración</span><span>Recibí conforme · Firma del empleado</span></div><p>Fecha de firma: ____________________ · Huella: ____________________</p><p class="document-footer">Registrado por: ${esc(d.operator)} · La conformidad de recepción se acredita con la firma del empleado.</p></article>`);
}

async function openResetRecords(){
  const preview=await api('reset-preview'),c=preview.counts;
  showModal('Vaciar los registros del colegio','Esta acción borra datos administrativos y financieros. Revisa el resumen antes de continuar.',`<form data-endpoint="reset-records"><input type="hidden" name="preview_hash" value="${esc(preview.preview_hash)}"><div class="reset-warning"><b>Se eliminarán estos registros y sus documentos</b>${table(['Registros','Cantidad'],[['Alumnos y matrículas',c.students],['Representantes',c.guardians],['Grados y cargos del personal',c.grades+c.positions],['Mensualidades y cargos',c.charges],['Cobros y recibos de alumnos',c.payments],['Empleados',c.employees],['Egresos y pagos de sueldo',c.expenses],['Cierres de caja',c.cash_closures]],r=>`<td>${esc(r[0])}</td><td>${r[1]}</td>`)}</div><p class="hint">También se eliminan tasas, convenios, seguimientos y documentos guardados. Se conservan el logo, los datos fiscales, la configuración y los usuarios. Todas las sesiones se cierran. Los números de cobros, egresos y alumnos continúan para evitar reutilizarlos.</p><p class="hint"><b>Antes de borrar:</b> el sistema crea un respaldo completo verificado, llamado «antes-vaciar-…», en la carpeta local de respaldos y también en el segundo destino si está configurado. Si falla alguna copia, no se vacía la base.</p>${field('Contraseña de tu administrador','password','','password','required maxlength="256" autocomplete="current-password"')}${field('Escribe VACIAR REGISTROS','confirmation','','text','required autocomplete="off"')}<label class="confirm-check"><input type="checkbox" required> Revisé el resumen y quiero borrar estos registros.</label><div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar','close')}<button class="btn danger" type="submit">Crear respaldo y vaciar registros</button></div></form>`);
}

function receiptBalance(p) {
  if(p.balance_after===null||p.balance_after===undefined)return '<p class="receipt-balance-note">Recibo histórico: no se guardó el saldo al emitirlo.</p>';
  return `<section class="receipt-balance"><div><b>${p.balance_after?'Abono recibido':'Pago completo de cargos registrados'}</b><span>Deuda anterior: ${usd(p.balance_before)} · Aplicado: ${usd(p.amount)}</span></div><div><span>Saldo pendiente del alumno</span><strong>${usd(p.balance_after)}</strong></div></section><p class="receipt-balance-note">Saldo al registrar este cobro. Puede incluir otros meses; no acredita solvencia ni cambia con pagos posteriores.</p>`;
}
function recoveryHelp(){showModal('Recuperar acceso','Sin borrar los registros del colegio.',`<ol class="help-steps"><li>Si otro administrador puede entrar, pídele cambiar tu contraseña en Configuración → Usuarios.</li><li>Si nadie puede entrar, cierra Aula completamente: menú junto al reloj → Salir y cerrar Aula.</li><li>En Inicio de Windows busca <b>Recuperar clave del administrador</b>. Se mostrarán los nombres y usuarios de administradores de esta base.</li><li>Elige tu usuario y escribe dos veces la nueva contraseña, con al menos 10 caracteres.</li><li>Se crea un respaldo previo y se cierran las sesiones de esa cuenta. Abre Aula de nuevo.</li></ol><p class="hint">La recuperación es local y requiere acceso a esta cuenta de Windows. Protege la cuenta y el equipo. Los administradores también pueden cambiar las claves de Caja y Consulta.</p>`);}
function maintenanceHelp(){showModal('Mantener Aula sin perder datos','Actualización, respaldo y restauración.',`<ol class="help-steps"><li>Antes de actualizar: crea y descarga un respaldo desde Configuración. Guarda una copia fuera de este disco.</li><li>Cierra Aula completamente desde su icono junto al reloj. Instala la nueva versión con la misma cuenta de Windows. No uses Vaciar registros para actualizar.</li><li>Abre Aula y verifica alumnos, saldos y cobros recientes. La actualización modifica el programa, conserva tus datos y realiza un respaldo previo.</li><li>Para recuperar datos: cierra Aula y abre <b>Restaurar respaldo</b> desde Inicio. Selecciona el archivo .sqlite3 de la fecha correcta y escribe RESTAURAR.</li><li>El respaldo reemplaza la base completa, incluidos usuarios. Los cobros posteriores a esa copia no estarán en ella. Se conserva el estado previo a la restauración cuando es recuperable.</li><li>Si aparece un error, conserva la carpeta de datos y los respaldos. No copies una base activa ni borres archivos SQLite, WAL o SHM para intentar arreglarlo.</li></ol><h3>Enviar información diaria</h3><p>Si solo necesitan consultar pagos y morosidad, usa Reportes → Reporte diario PDF → Descargar PDF y envíalo por correo. El colegio abre o imprime el documento sin restaurar datos. Vuelve a generarlo si registraste movimientos después; el corte es la fecha y hora del PDF. Conserva también los respaldos completos.</p><h3>Llevar datos a otra PC</h3><p>Configuración → Crear respaldo ahora → Descargar copia. Lleva el archivo .sqlite3 en un USB o envíalo por correo. Si llegó en ZIP, extráelo antes de restaurar. El instalador solo hace falta para instalar o actualizar el programa. En la otra PC instala la misma versión o una más reciente, cierra Aula y usa Inicio → Restaurar respaldo. Entra con el mismo usuario y contraseña de Aula; revisa saldos y la ruta de la segunda copia.</p><p><b>Las dos PC quedan independientes.</b> No se sincronizan ni se fusionan los cambios. Si trabajas desde casa y envías una copia cada 2 o 3 días, registra los cambios reales solo allí y utiliza un usuario Consulta en el colegio. Crea ese usuario en casa antes de descargar la copia. Restaurar reemplaza todos los datos de la PC de destino; guarda primero una copia de ellos.</p><p class="hint">Con cortes de electricidad, usa un UPS y configura la segunda carpeta de copias. Las pruebas son independientes: abre «Aula - Pruebas» para experimentar.</p>`);}
async function maintenanceReview(){const d=await api('maintenance-review');showModal('Verificación de datos',d.ok?'No se encontraron inconsistencias en los controles realizados.':'Se encontraron inconsistencias; conserva un respaldo y solicita revisión.',`<div class="verification-result ${d.ok?'ok':'problem'}">${icon(d.ok?'check':'arrears')}<b>${d.ok?'Comprobaciones correctas':'Requiere revisión'}</b></div>${d.errors.length?'<ul>'+d.errors.map(e=>'<li>'+esc(e)+'</li>').join('')+'</ul>':''}<p>Integridad SQLite, relaciones entre registros, aplicaciones de cobros y mensualidades.</p><p>Modo SQLite: <b>${esc(d.journal_mode)}</b> · Sincronización: <b>${d.synchronous===2?'FULL':esc(d.synchronous)}</b></p>${table(['Registro','Cantidad'],Object.entries(d.counts),r=>`<td>${esc(({students:'Alumnos',guardians:'Representantes',charges:'Cargos',payments:'Cobros',expenses:'Egresos',users:'Usuarios'})[r[0]])}</td><td>${r[1]}</td>`)}<p class="hint">${esc(d.message)}</p>`);}
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
