'use strict';
const $ = (s, root = document) => root.querySelector(s);
const app = $('#app'), modal = $('#modal');
let state, session, page = 'dashboard', filters = {}, reportFrom = '', reportTo = '';
let receiptPaper = 'half-letter';
let yearCohort, yearPreview, yearRequest;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = n => new Intl.NumberFormat('es-VE', {minimumFractionDigits:2, maximumFractionDigits:2}).format(n);
const usd = cents => `$ ${number(cents / 100)}`;
const bs = cents => `Bs ${number(cents / 100)}`;
const dateLabel = date => date ? new Date(date + 'T12:00:00').toLocaleDateString('es-VE', {day:'2-digit',month:'short',year:'numeric'}) : '—';
const monthLabel = month => new Date(month + '-01T12:00:00').toLocaleDateString('es-VE', {month:'long',year:'numeric'});
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
const btn = (label, action, style = '', id = '') => `<button type="button" class="btn ${style}" data-action="${action}" ${id !== '' ? `data-id="${esc(id)}"` : ''}>${label}</button>`;
const empty = (title, text = 'Los registros aparecerán aquí.', name = 'book') => `<div class="empty">${icon(name)}<b>${esc(title)}</b>${esc(text)}</div>`;
const badge = (label, kind = '') => `<span class="badge ${kind}">${esc(label)}</span>`;
const actionsCell = markup => `<div class="actions">${markup}</div>`;
const table = (headers, records, renderer, emptyTitle = 'Sin registros') => records.length ? `<div class="table-wrap"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${records.map(r => `<tr>${renderer(r)}</tr>`).join('')}</tbody></table></div>` : empty(emptyTitle);
const card = (title, body, action = '', subtitle = '') => `<section class="card"><div class="card-head"><div><h2>${title}</h2>${subtitle ? `<p>${subtitle}</p>` : ''}</div>${action}</div>${body}</section>`;
const stat = (label, value, note, name, style = '') => `<div class="stat ${style}"><div class="stat-label">${label}<span class="stat-icon">${icon(name)}</span></div><div class="stat-value">${value}</div><small>${note}</small></div>`;
const exportBtn = (type, label = 'Exportar Excel / CSV') => `<a class="btn" href="/api/export?type=${type}" download>${icon('download')}${label}</a>`;
const field = (label, name, value = '', type = 'text', extra = '', hint = '') => `<label class="field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}>${hint ? `<small>${esc(hint)}</small>` : ''}</label>`;
const select = (label, name, options, selected = '', extra = '') => `<label class="field">${esc(label)}<select name="${name}" ${extra}>${options.map(o => `<option value="${esc(o[0])}" ${String(o[0]) === String(selected) ? 'selected' : ''}>${esc(o[1])}</option>`).join('')}</select></label>`;
const textarea = (label, name, value = '', limit = 2000) => `<label class="field full">${esc(label)}<textarea name="${name}" aria-label="${esc(label)}" maxlength="${limit}">${esc(value)}</textarea></label>`;
const formFoot = label => `<div class="error" role="alert"></div><div class="form-actions">${btn('Cancelar', 'close')}<button class="btn primary" type="submit">${label}</button></div>`;
const statusOptions = [['active','Activo'],['inactive','Inactivo']];

async function api(path, data) {
  const options = data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':session?.csrf || ''}, body:JSON.stringify(data)};
  const response = await fetch('/api/' + path, options);
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
    session = result.user;
    if (!session) { auth(result.needs_setup); return; }
    await openRateGate();
  } catch (error) { app.innerHTML = `<div class="loading"><h2>No se pudo abrir Aula</h2><p>${esc(error.message)}</p>${btn('Reintentar','boot')}</div>`; }
}
async function openRateGate() {
  const gate = await api('rate-gate');
  state=undefined; modal.close(); $('#print-area').replaceChildren();
  app.innerHTML=`<div class="rate-screen"><section class="card gate-card"><div class="brand"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>Alejandro Von Humboldt</b><small>Tasas y respaldo</small></div></div><div class="eyebrow">${dateLabel(gate.today)}</div><h1>Confirma la tasa de hoy</h1><p>Antes de comenzar, revisa la tasa oficial vigente. Se usará para convertir los pagos y la nómina en bolívares.</p><form data-endpoint="confirm-rate"><input type="hidden" name="rate_date" value="${gate.today}">${field('Bolívares por 1 USD','rate',gate.rate,'number',`required min="0.000001" max="1000000" step="0.000001" ${gate.role==='reader'?'readonly':''}`)}<p class="hint">${gate.role==='reader'?'Consulta puede confirmar la tasa registrada. Si falta, administración o caja debe registrarla.':'Consulta bcv.org.ve y registra la tasa vigente, incluso en fines de semana y feriados. La actualización es manual.'}</p><div class="error" role="alert"></div><button class="btn primary" type="submit" ${gate.role==='reader'&&!gate.rate?'disabled':''}>Confirmar tasa y entrar</button></form><div class="gate-footer">${gate.role==='admin'?'<a class="btn" href="/api/backup" download>Descargar respaldo</a>':''}${btn('Cerrar sesión','logout')}</div></section></div>`;
}
function auth(setup) {
  state=undefined;modal.close();$('#print-area').replaceChildren();
  app.innerHTML = `<div class="auth-screen"><section class="auth-story"><div class="brand"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>Alejandro Von Humboldt</b><small>Administración escolar</small></div></div><h1>Tu colegio,<br>con las cuentas<br><em>en orden.</em></h1><p>Alumnos, mensualidades y cobranza en un mismo lugar. Pensado para el día a día de tu colegio en Venezuela.</p><p>${icon('shield')} Datos locales · USD y bolívares</p></section><section class="auth-form"><div class="eyebrow">${setup ? 'Empecemos' : 'Bienvenido de nuevo'}</div><h2>${setup ? 'Configura tu administrador' : 'Entrar a tu colegio'}</h2><p>${setup ? 'Esta cuenta gestionará el colegio y podrá crear usuarios de caja y consulta.' : 'Ingresa tus datos para continuar con la administración.'}</p><form data-endpoint="${setup ? 'setup' : 'login'}">${setup ? field('Nombre del administrador','name','','text','required maxlength="200" autocomplete="name"') : ''}${field('Usuario','username','','text','required maxlength="80" autocomplete="username"')}${field('Contraseña','password','','password',`required ${setup ? 'minlength="10"' : ''} maxlength="256" autocomplete="${setup ? 'new-password' : 'current-password'}"`,setup ? 'Como mínimo 10 caracteres. Guárdala en un lugar seguro.' : '')}<div class="error" role="alert"></div><button class="btn primary" type="submit">${setup ? 'Crear mi cuenta' : 'Iniciar sesión'} ${icon('arrow')}</button></form><div class="auth-note">El sistema funciona en esta computadora. No necesita internet para registrar cobros. La tasa BCV se registra manualmente por fecha.</div></section></div>`;
}
async function refresh() { state = await api('state'); render(); }
const navItems = [['dashboard','Resumen','dashboard'],['students','Alumnos y matrículas','students'],['guardians','Representantes','guardians'],['grades','Grados y secciones','grades'],['billing','Mensualidades y cargos','billing'],['payments','Caja y cobros','payments'],['cash','Cierre de caja','payments'],['arrears','Morosidad','arrears'],['employees','Personal','employees'],['expenses','Egresos y nómina','expenses'],['reports','Reportes','reports'],['settings','Configuración','settings']];
function render() {
  if (!state) return;
  if (page === 'settings' && !admin()) page = 'dashboard';
  document.title = state.settings.school_name + " · Administración escolar";
  const rate = todayRate(), current = navItems.find(n => n[0] === page);
  app.innerHTML = `<div class="layout"><aside class="sidebar"><div class="brand"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>${esc(state.settings.school_name)}</b><small>Administración escolar</small></div></div><nav>${navItems.filter(n => n[0] !== 'settings' || admin()).map((n,i) => `${[0,4,8,10].includes(i) ? `<div class="nav-label">${({0:'Colegio',4:'Finanzas',8:'Administración',10:'Gestión'})[i]}</div>` : ''}<button class="nav-button ${page === n[0] ? 'active' : ''}" data-action="nav" data-id="${n[0]}">${icon(n[2])}${n[1]}${n[0] === 'arrears' && state.summary.debtors ? `<span class="count">${state.summary.debtors}</span>` : ''}</button>`).join('')}</nav><div class="sidebar-footer"><div class="local-pill"><span class="dot"></span>Una computadora · Datos locales</div><div class="profile"><div class="avatar">${esc(state.user.name.slice(0,1).toUpperCase())}</div><div class="profile-text"><b>${esc(state.user.name)}</b><small>${roleLabel(state.user.role)}</small></div><button class="logout" data-action="logout" title="Cerrar sesión" aria-label="Cerrar sesión">${icon('logout')}</button></div></div></aside><main class="main"><header class="topbar"><div class="breadcrumb">${esc(state.settings.school_name)} <span> / </span> <b>${current[1]}</b></div><div class="top-info"><span class="backup-status ${backupStale()?'text-red':''}" title="${esc(state.backup?.local_path||'')}">${backupLabel()}</span><span>${dateLabel(state.today)}</span><button class="rate-chip" data-action="rates">${rate ? `BCV · Bs ${number(Number(rate.rate))} / USD` : 'BCV · Tasa de hoy pendiente'}</button></div></header><div id="page-content">${backupProblem()}${pageBody()}</div><div class="welcome-line"><span>${esc(state.settings.school_name)} · Administración escolar</span><span>Año escolar ${esc(state.settings.school_year)}–${Number(state.settings.school_year)+1} · Base USD</span></div></main></div>`;
}
function heading(title, description, actions = '') { return `<div class="page-heading"><div><div class="eyebrow">${esc(state.settings.school_name)}</div><h1>${title}</h1><p>${description}</p></div><div class="actions">${actions}</div></div>`; }
function pageBody() {
  return ({dashboard,students:studentsPage,guardians:guardiansPage,grades:gradesPage,billing:billingPage,payments:paymentsPage,arrears:arrearsPage,employees:employeesPage,expenses:expensesPage,cash:cashPage,reports:reportsPage,settings:settingsPage}[page])();
}
function dashboard() {
  const s = state.summary;
  const pending = state.students.filter(x => x.overdue > 0).sort((a,b) => b.overdue-a.overdue).slice(0,5);
  const recent = state.payments.filter(p => !p.voided).slice(0,5);
  const setup = !state.students.length && admin() ? `<div class="notice">${icon('book')}<div><b>Tu colegio empieza aquí</b>Configura tus datos, crea un grado y un representante; después matricula al primer alumno.<div class="steps"><button class="step" data-action="nav" data-id="settings">1. Datos del colegio</button><button class="step" data-action="grade">2. Grados</button><button class="step" data-action="guardian">3. Representantes</button><button class="step" data-action="student">4. Alumnos</button></div></div></div>` : '';
  return heading('Resumen de tu colegio', `Este es el estado de tu colegio · ${monthLabel(state.today.slice(0,7))}`, writable() ? btn(`${icon('plus')} Registrar pago`,'payment','primary') : '') + setup + dailyDashboard() +
    `<div class="stats">${stat('Cobrado este mes',usd(s.income), 'Equivalente USD de pagos válidos','payments','featured')}${stat('Saldo pendiente',usd(s.pending), 'Incluye cargos vencidos y por vencer','billing')}${stat('Deuda vencida',usd(s.overdue), `${s.debtors} alumnos con mensualidades o cargos vencidos`,'arrears','alert')}${stat('Alumnos activos',s.active_students, 'Matrículas activas registradas','students')}</div>` +
    `<div class="grid-two"><div>${card('Cobros recientes',table(['Alumno / recibo','Recibido','Fecha'],recent,p=>`<td><button class="btn ghost" data-action="receipt" data-id="${p.id}">${esc(p.student_name)}</button><span class="sub">R-${String(p.id).padStart(6,'0')} · ${esc(p.method)}</span></td><td class="money">${p.currency === 'VES' ? bs(p.received_amount) : usd(p.amount)}<span class="sub">${p.currency === 'VES' ? usd(p.amount) + ' · equivalente' : 'Dólares'}</span></td><td>${dateLabel(p.paid_on)}</td>`,'Tu primer cobro aparecerá aquí'),btn('Ver caja →','nav','ghost','payments'))}${card('Prioridad de cobranza',table(['Alumno / representante','Vencido',''],pending,x=>`<td><b>${esc(x.name)}</b><span class="sub">${esc(x.guardian_name)} · ${esc(x.grade_name)}</span></td><td class="money text-red">${usd(x.overdue)}</td><td>${btn('Ver cuenta','account','small',x.id)}</td>`,'No hay deuda vencida'),btn('Ver morosidad →','nav','ghost','arrears'))}</div><div>${card('Antigüedad de la deuda',`<div class="card-body"><div class="balance-hero"><small>Total vencido · USD</small><div class="total">${usd(s.overdue)}</div><small>${todayRate() ? `Referencia hoy: ${bs(Math.round(s.overdue * Number(todayRate().rate)))}` : 'Registra la tasa de hoy para consultar el equivalente en Bs'}</small></div>${['1–30 días','31–60 días','61–90 días','Más de 90'].map((label,i)=>`<div class="aging-row"><span>${label}</span><div class="bar-track"><div class="bar" style="width:${s.overdue ? s.aging[i]/s.overdue*100 : 0}%"></div></div><b>${usd(s.aging[i])}</b></div>`).join('')}<div class="collection-note">Los abonos se aplican al cargo pendiente más antiguo. La deuda se mantiene en USD y los pagos conservan su tasa original.</div></div>`,icon('clock'))}${card('Movimiento del mes',`<div class="card-body"><div class="list-line"><span>Ingresos por cobros</span><b class="text-green">${usd(s.income)}</b></div><div class="list-line"><span>Egresos registrados</span><b>${usd(s.expenses)}</b></div><div class="list-line"><span><b>Balance operativo</b><small>Ingresos menos egresos; equivalente USD</small></span><b>${usd(s.net)}</b></div></div>`,btn('Reportes →','nav','ghost','reports'))}</div></div>`;
}
function searchToolbar(placeholder, grade = false, extra = '') {
  return `<div class="toolbar"><input id="search" aria-label="Buscar" placeholder="${placeholder}" value="${esc(filters.search || '')}">${grade ? `<select id="grade-filter" aria-label="Filtrar por grado"><option value="">Todos los grados</option>${state.grades.map(g=>`<option value="${g.id}" ${String(g.id) === filters.grade ? 'selected' : ''}>${esc(g.name)}</option>`).join('')}</select>` : ''}${extra}<span class="table-count" id="table-count"></span></div>`;
}
function matches(s) { const q = (filters.search || '').toLocaleLowerCase(); return (!filters.grade || String(s.grade_id) === filters.grade) && [s.name,s.document,s.student_code,s.guardian_name,s.phone,s.position].some(v=>String(v||'').toLocaleLowerCase().includes(q)); }
function studentsPage() {
  const records = state.students.filter(matches);
  return heading('Alumnos y matrículas','Expedientes, representantes, mensualidades y becas por alumno.',`${exportBtn('students')}${admin()?btn('Pase de año / grados','year-transition')+btn('Importar Excel / CSV','import-roster')+btn(`${icon('plus')} Matricular alumno`,'student','primary'):''}`) + card('Directorio de alumnos', searchToolbar('Buscar alumno, documento o representante…',true) + table(['Alumno','Grado / año','Mensualidad USD','Estado','Saldo USD',''],records,s=>`<td><b>${esc(s.name)}</b><span class="sub">${esc(s.student_code)} · ${esc(s.guardian_name)}</span></td><td>${esc(s.grade_name)}<span class="sub">${s.school_year}–${s.school_year+1}</span></td><td class="money">${usd(Math.floor((s.monthly_fee*(100-s.discount)+50)/100))}<span class="sub">${s.discount ? `Beca / descuento: ${s.discount}%` : 'Tarifa sin descuento'}</span></td><td>${badge(s.status==='active'?'Activo':'Inactivo',s.status==='active'?'':'neutral')}</td><td class="money ${s.overdue?'text-red':''}">${usd(s.balance)}</td><td>${actionsCell(btn('Cuenta','account','small',s.id)+btn('Constancia','enrollment','small',s.id)+(admin()?btn('Editar','student','small',s.id):''))}</td>`,'Aún no hay alumnos matriculados'), `<span class="muted">${records.length} alumnos</span>`);
}
function guardiansPage() {
  const records = state.guardians.filter(matches);
  return heading('Representantes','Personas responsables de los alumnos y sus datos de contacto.',admin()?btn(`${icon('plus')} Nuevo representante`,'guardian','primary'):'') + card('Directorio de representantes',searchToolbar('Buscar representante o documento…')+table(['Representante','Contacto','Alumnos',''],records,g=>`<td><b>${esc(g.name)}</b><span class="sub">${esc(g.document)}</span></td><td>${esc(g.phone)||'—'}<span class="sub">${esc(g.email)}</span></td><td>${state.students.filter(s=>s.guardian_id===g.id).length}</td><td>${actionsCell(btn('Cuenta familiar','guardian-account','small',g.id)+(admin()?btn('Editar','guardian','small',g.id):''))}</td>`,'Registra al primer representante'));
}
function gradesPage() {
  return heading('Grados y secciones','Organiza las matrículas y controla la capacidad de cada sección.',admin()?btn(`${icon('plus')} Nuevo grado / sección`,'grade','primary'):'') + card('Oferta escolar',table(['Grado / sección','Capacidad','Alumnos del año actual','Cupos disponibles',''],state.grades,g=>{const count=state.students.filter(s=>s.grade_id===g.id && s.status==='active' && s.school_year===Number(state.settings.school_year)).length;return `<td><b>${esc(g.name)}</b></td><td>${g.capacity}</td><td>${count}</td><td>${badge(Math.max(0,g.capacity-count)+' cupos',count>=g.capacity?'red':'')}</td><td>${admin()?btn('Editar','grade','small',g.id):''}</td>`;},'Crea los grados o secciones de tu colegio'));
}
function billingPage() {
  const records = state.charges.filter(c => (!filters.grade || state.students.find(s=>s.id===c.student_id)?.grade_id===Number(filters.grade)) && [c.student_name,c.concept,c.period].some(x=>x.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Mensualidades y cargos','Las mensualidades se calculan automáticamente; aquí puedes revisar sus saldos y registrar otros cargos.',writable()?btn('Nuevo cargo','charge')+btn('Preparar otro período','generate','primary'):'') + `<div class="notice">${icon('billing')}<div><b>Mensualidades en USD · vencimiento el día ${esc(state.settings.due_day)}</b>Se incluyen automáticamente los meses desde el inicio de cada matrícula hasta el mes actual. Los meses vencidos sin pagar aparecen en Morosidad; los meses futuros se preparan solo si los necesitas.</div></div>` + card('Libro de cargos',searchToolbar('Buscar alumno, concepto o período…',true)+table(['Alumno','Concepto / período','Vencimiento','Cargo USD','Abonado USD','Saldo / estado',''],records,c=>`<td><b>${esc(c.student_name)}</b></td><td>${esc(c.concept)}<span class="sub">${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td class="money">${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}<span class="sub">${badge(c.balance===0?'Pagado':c.overdue?'Vencido':'Pendiente',c.overdue?'red':c.balance?'neutral':'')}</span></td><td>${actionsCell(btn('Cuenta','account','small',c.student_id)+(admin()&&!c.paid?btn('Anular','cancel-charge','small',c.id):''))}</td>`,'No hay cargos para las matrículas registradas.'));
}
function paymentsPage() {
  const records = state.payments.filter(p=>[p.student_name,p.reference,`R-${String(p.id).padStart(6,'0')}`].some(x=>x.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Caja y cobros','Recibe dólares o bolívares y emite comprobantes de pago.',exportBtn('payments')+(writable()?btn(`${icon('plus')} Registrar pago`,'payment','primary'):'')) + card('Historial de recibos',searchToolbar('Buscar alumno, recibo o referencia…')+table(['Recibo / alumno','Fecha','Recibido','Tasa BCV','Equivalente USD','Método','Estado',''],records,p=>`<td><b>R-${String(p.id).padStart(6,'0')}</b><span class="sub">${esc(p.student_name)}</span></td><td>${dateLabel(p.paid_on)}</td><td class="money">${p.currency==='VES'?bs(p.received_amount):usd(p.amount)}</td><td>${p.currency==='VES'?number(Number(p.exchange_rate)):'—'}</td><td class="money">${usd(p.amount)}</td><td>${esc(p.method)}<span class="sub">${esc(p.reference)}</span></td><td>${badge(p.voided?'Anulado':'Válido',p.voided?'red':'')}</td><td>${actionsCell(btn('Recibo','receipt','small',p.id)+(admin()&&!p.voided?btn('Anular','void-payment','small',p.id):''))}</td>`,'Aún no hay pagos registrados'));
}
function arrearsPage() {
  const all = state.students.filter(s=>s.overdue>0), records = all.filter(matches);
  const sum = records.reduce((t,s)=>t+s.overdue,0);
  return heading('Morosidad y cobranza','Deuda vencida, antigüedad y seguimiento por alumno y representante.',exportBtn('arrears')) + `<div class="stats">${stat('Deuda vencida visible',usd(sum),'Total del filtro actual','arrears','alert')}${stat('Alumnos en mora',records.length,'Del filtro actual','students')}${stat('Equivalente en bolívares',todayRate()?bs(Math.round(sum*Number(todayRate().rate))):'—',todayRate()?'Referencia con tasa BCV de hoy':'Falta registrar la tasa BCV de hoy','payments')}${stat('Mayor atraso',Math.max(0,...state.charges.filter(c=>c.overdue && records.some(s=>s.id===c.student_id)).map(c=>c.days_overdue))+'<span>días</span>','Cargo vencido más antiguo del filtro','clock')}</div>`+card('Cuentas que requieren seguimiento',searchToolbar('Buscar alumno o representante…',true)+table(['Alumno / grado','Representante / contacto','Deuda vencida USD','Antigüedad',''],records,s=>{const days=Math.max(...state.charges.filter(c=>c.student_id===s.id&&c.overdue).map(c=>c.days_overdue));return `<td><b>${esc(s.name)}</b><span class="sub">${esc(s.grade_name)}</span></td><td>${esc(s.guardian_name)}<span class="sub">${esc(s.guardian_phone)||'Sin teléfono'}</span></td><td class="money text-red">${usd(s.overdue)}</td><td>${badge(days+' días',days>30?'red':'neutral')}</td><td>${actionsCell(btn('Cuenta','account','small',s.id)+btn('Aviso','collection','small',s.id)+(writable()?btn('Convenio','payment-plan','small',s.id)+btn('Seguimiento','followup','small',s.id)+btn('Cobrar','payment','small primary',s.id):''))}</td>`;},'No hay deuda vencida con este filtro'));
}
function employeesPage() {
  const records = state.employees.filter(matches);
  return heading('Personal del colegio','Salarios en USD, pagos en Bs y datos bancarios del equipo.',(admin()?btn('Cargos','positions')+btn('Preparar nómina','payroll-plan'):'')+(admin()?btn(`${icon('plus')} Nuevo empleado`,'employee','primary'):''))+card('Equipo administrativo y docente',searchToolbar('Buscar empleado, documento o cargo…')+table(['Empleado','Cargo','Banco / cuenta','Salario USD / Bs','Estado',''],records,e=>`<td><b>${esc(e.name)}</b><span class="sub">${esc(e.document)}</span></td><td>${esc(e.position)}</td><td>${esc(e.bank)||'Pendiente'}<span class="sub">${esc(e.bank_account)||'Sin cuenta'}</span></td><td class="money">${usd(e.salary)}<span class="sub">${bs(Math.round(e.salary*Number(todayRate()?.rate||0)))}</span></td><td>${badge(e.status==='active'?'Activo':'Inactivo',e.status==='active'?'':'neutral')}</td><td>${actionsCell((admin()?btn('Editar','employee','small',e.id):'')+(writable()?btn('Pagar nómina','payroll','small',e.id):''))}</td>`,'Registra el personal del colegio'))+card('Relaciones de pago guardadas',table(['Documento','Fecha / tasa','Total USD / Bs',''],state.payroll_plans,p=>`<td>${esc(p.name)}<span class="sub">N-${String(p.id).padStart(6,'0')}</span></td><td>${dateLabel(p.pay_date)}<span class="sub">Bs ${esc(p.rate)} / USD</span></td><td>${usd(p.total_usd)}<span class="sub">${bs(p.total_ves)}</span></td><td>${btn('Ver documento','payroll-document','small',p.id)}</td>`,'Aún no hay relaciones de pago'));
}
function expensesPage() {
  const records=state.expenses.filter(e=>[e.concept,e.category,e.reference,e.employee_name||''].some(v=>v.toLowerCase().includes((filters.search||'').toLowerCase())));
  return heading('Egresos y nómina','Registra gastos operativos y pagos al personal, en USD o Bs.',exportBtn('expenses')+(writable()?btn(`${icon('plus')} Registrar egreso`,'expense','primary'):''))+card('Libro de egresos',searchToolbar('Buscar concepto, categoría o empleado…')+table(['Concepto','Fecha','Categoría','Pagado','Equivalente USD','Estado',''],records,e=>`<td><b>${esc(e.concept)}</b><span class="sub">${esc(e.employee_name)||esc(e.reference)}</span></td><td>${dateLabel(e.spent_on)}</td><td>${esc(e.category)}</td><td class="money">${e.currency==='VES'?bs(e.received_amount):usd(e.amount)}<span class="sub">${e.currency==='VES'?'BCV: '+number(Number(e.exchange_rate)):'Dólares'}</span></td><td class="money">${usd(e.amount)}</td><td>${badge(e.voided?'Anulado':'Válido',e.voided?'red':'')}</td><td>${admin()&&!e.voided?btn('Anular','void-expense','small',e.id):''}</td>`,'Aún no hay egresos registrados'));
}
function reportsPage() {
  reportFrom ||= state.today.slice(0,7)+'-01'; reportTo ||= state.today;
  const payments=state.payments.filter(p=>!p.voided&&p.paid_on>=reportFrom&&p.paid_on<=reportTo), expenses=state.expenses.filter(e=>!e.voided&&e.spent_on>=reportFrom&&e.spent_on<=reportTo);
  const income=payments.reduce((a,p)=>a+p.amount,0), out=expenses.reduce((a,e)=>a+e.amount,0);
  return heading('Reportes administrativos','Consulta el flujo de caja y descarga los libros completos en CSV.',btn('Cierre de caja diario','nav','','cash')+btn(`${icon('print')} Imprimir resumen`,'print-report'))+`<div class="card"><div class="toolbar">${field('Desde','report-from',reportFrom,'date','id="report-from"')}${field('Hasta','report-to',reportTo,'date','id="report-to"')}<span class="table-count">${payments.length} cobros · ${expenses.length} egresos válidos</span></div></div><div class="stats">${stat('Ingresos del período',usd(income),'Equivalente USD','payments','featured')}${stat('Egresos del período',usd(out),'Equivalente USD','expenses')}${stat('Balance del período',usd(income-out),'Ingresos menos egresos','reports')}${stat('Deuda vencida actual',usd(state.summary.overdue),'Corte de hoy, independiente del filtro','arrears','alert')}</div><div class="grid-two">${card('Cobros por método',`<div class="card-body">${['Efectivo','Transferencia','Tarjeta','Otro'].map(method=>`<div class="list-line"><span>${method}</span><b>${usd(payments.filter(p=>p.method===method).reduce((t,p)=>t+p.amount,0))}</b></div>`).join('')}<div class="list-line"><span>Recibido en dólares <small>Importe original, sin conversión</small></span><b>${usd(payments.filter(p=>p.currency==='USD').reduce((t,p)=>t+p.received_amount,0))}</b></div><div class="list-line"><span>Recibido en bolívares <small>Importe original, sin conversión</small></span><b>${bs(payments.filter(p=>p.currency==='VES').reduce((t,p)=>t+p.received_amount,0))}</b></div><p class="hint">El equivalente USD usa la tasa conservada en cada operación; sumar bolívares no cambia los saldos históricos.</p></div>`)}${card('Exportación de libros',`<div class="card-body"><p class="muted">Descargas completas para abrir en Excel. Incluyen operaciones anuladas identificadas como tales.</p><div class="list-line"><span>Morosidad actual</span>${exportBtn('arrears','Descargar')}</div><div class="list-line"><span>Historial de pagos y tasas</span>${exportBtn('payments','Descargar')}</div><div class="list-line"><span>Alumnos y saldos</span>${exportBtn('students','Descargar')}</div><div class="list-line"><span>Egresos y nómina</span>${exportBtn('expenses','Descargar')}</div></div>`)}</div>`;
}
function settingsPage() {
  const s=state.settings;
  return heading('Configuración','Datos del colegio, año escolar, usuarios y respaldos.')+card('Datos del colegio',`<div class="branding-preview"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>Identidad del colegio</b><p>El logo y los datos fiscales se incluyen en recibos, constancias, relaciones de nómina y reportes impresos.</p><a href="/logo-colegio-v1.png" download="Logo-Alejandro-Von-Humboldt.png">Descargar logo PNG</a></div></div><form class="card-body" data-endpoint="settings"><div class="form-grid">${field('Nombre del colegio','school_name',s.school_name,'text','required maxlength="200"')}${field('Razón social fiscal','legal_name',s.legal_name,'text','maxlength="200"','Nombre legal que aparecerá en los documentos.')}${field('RIF del colegio','rif',s.rif)}${field('Correo del colegio','email',s.email,'email')}${field('Sitio web','website',s.website)}${field('Teléfono','phone',s.phone)}${field('Dirección de contacto','address',s.address)}${textarea('Domicilio fiscal','fiscal_address',s.fiscal_address,500)}${field('Segunda carpeta de respaldos','backup_directory',s.backup_directory,'text','maxlength="500"','Ruta completa de un USB o una carpeta sincronizada con Drive. Se copian respaldos; nunca la base activa.')}${field('Año de inicio del año escolar','school_year',s.school_year,'number','required min="2000" max="2100"',`Ejemplo: 2026 para el año 2026–2027.`)}${select('Mes de inicio del año escolar','start_month',Array.from({length:12},(_,i)=>[i+1,new Date(2020,i,1).toLocaleDateString('es-VE',{month:'long'})]),s.start_month)}${field('Día de vencimiento mensual','due_day',s.due_day,'number','required min="1" max="31"','Si el mes tiene menos días, se usa el último día.')}</div><p class="hint">Moneda base: USD. Pagos y egresos: USD o bolívares. Los documentos nuevos utilizan estos datos. Los documentos ya emitidos conservan la información original. Cambiar la configuración no recalcula cargos ni pagos ya registrados.</p><div class="error" role="alert"></div><div class="form-actions"><button class="btn primary" type="submit">Guardar configuración</button></div></form>`)+`<div class="grid-two">${card('Usuarios y permisos',table(['Nombre / usuario','Perfil',''],state.users,u=>`<td><b>${esc(u.name)}</b><span class="sub">${esc(u.username)}</span></td><td>${roleLabel(u.role)}</td><td>${btn('Contraseña','password','small',u.id)}</td>`),btn('Crear usuario','user','small'))}${card('Tasas y respaldo',`<div class="card-body"><div class="list-line"><span>Tasas BCV por fecha<small>Registro manual; cada operación conserva su tasa.</small></span>${btn('Gestionar','rates','small')}</div><div class="list-line"><span>Base de datos completa<small>Incluye usuarios, cobros y expedientes.</small></span><a class="btn small" href="/api/backup" download>${icon('download')} Respaldo</a></div><p class="hint">Guarda respaldos periódicos en un dispositivo distinto. La restauración se realiza con el sistema cerrado; sigue las instrucciones del archivo README.</p></div>`)}</div>`+card('Ubicación y estado de los datos',`<div class="card-body"><p class="data-path">${esc(state.backup?.data_path||'')}</p><p>${backupLabel()}</p><p class="hint">Respaldo tras cobros, egresos y cierres, y cada cinco minutos con Aula abierto. Se conservan 90 copias recientes y 30 copias diarias locales. El segundo destino conserva 90 copias recientes. Una carpeta de Drive envía copias cuando su cliente tiene internet.</p>${state.backup?.secondary_directory?`<p>Segundo destino: ${esc(state.backup.secondary_directory)}</p>`:'<p class="text-red">Configura un segundo destino para protegerte ante una falla del disco.</p>'}${state.backup?.secondary_error?`<p class="text-red">${esc(state.backup.secondary_error)}</p>`:''}</div>`)+card('Bitácora de operaciones',table(['Fecha','Usuario','Operación','Detalle'],state.audit,a=>`<td>${esc(new Date(a.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}</td><td>${esc(a.operator)||'—'}</td><td>${esc(a.action)}</td><td class="audit-detail" title="${esc(a.details)}">${esc(a.details)}</td>`,'Sin operaciones'),'<small>Últimas 300 operaciones</small>');
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
  const r=state.students.find(s=>s.id===Number(id))||{}, year=Number(state.settings.school_year), startMonth=Number(state.settings.start_month);
  const start=`${year}-${String(startMonth).padStart(2,'0')}-01`;
  // Avoid locale-dependent ISO formatting on Windows browser installations.
  const endDate=new Date(year+1,startMonth-1,0,12), endISO=`${endDate.getFullYear()}-${String(endDate.getMonth()+1).padStart(2,'0')}-${String(endDate.getDate()).padStart(2,'0')}`;
  showModal(r.id?'Editar matrícula':'Matricular alumno','El descuento se aplica al generar cargos nuevos; los cargos existentes se conservan.',recordForm('students',field('Nombre completo','name',r.name,'text','required maxlength="200"')+field('Código único del alumno','student_code',r.student_code||'Se asignará al guardar','text','readonly', 'Cada hermano recibe su propio código.')+field('Cédula del alumno (si tiene)','document',r.document===r.student_code?'':r.document,'text','maxlength="200"', 'Opcional. No uses la cédula del representante.')+field('Fecha de nacimiento','birth_date',r.birth_date,'date',`required max="${state.today}"`)+field('Buscar representante por nombre o cédula','guardian_search','','search','id="guardian-search" autocomplete="off"')+select('Representante','guardian_id',[['','Selecciona un representante'],...state.guardians.map(g=>[g.id,`${g.document} · ${g.name}`])],r.guardian_id||'','required')+select('Grado / sección','grade_id',state.grades.map(g=>[g.id,g.name]),r.grade_id,'required')+field('Año de inicio del año escolar','school_year',r.school_year??year,'number','required min="2000" max="2100"')+field('Mensualidad base · USD','monthly_fee',r.id?(r.monthly_fee/100).toFixed(2):'','number','required min="0" max="999999999" step="0.01"')+field('Beca / descuento · %','discount',r.discount??0,'number','required min="0" max="100"')+`<div class="conversion full" id="tuition-preview" role="status"></div>`+field('Inicio de matrícula','enrollment_start',r.enrollment_start||(state.today>start?state.today:start),'date','required')+field('Fin de matrícula','enrollment_end',r.enrollment_end||endISO,'date','required')+select('Estado','status',statusOptions,r.status||'active')+textarea('Observaciones','notes',r.notes),r,'Guardar matrícula'));
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
  showModal('Registrar pago','El abono se aplica a los cargos pendientes más antiguos.',`<form data-endpoint="payments"><input type="hidden" name="request_key" value="${crypto.randomUUID()}"><div class="form-grid">${select('Alumno','student_id',candidates.map(s=>[s.id,`${s.name} · ${usd(s.balance)}`]),id||candidates[0].id,'required')}${field('Fecha del pago','paid_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda recibida','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],'USD')}${field('Importe recibido','amount','','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',['Efectivo','Transferencia','Tarjeta','Otro'].map(m=>[m,m]),'Transferencia')}${field('Referencia bancaria / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div><div class="full" id="duplicate-reference"></div>${textarea('Observaciones','notes')}</div><div class="actions" style="margin-top:15px">${btn('Completar saldo','full-payment','small')}${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar y emitir recibo')}</form>`);
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
  showModal(emp?'Registrar pago de nómina':'Registrar egreso','Conserva el importe original, su moneda y la tasa BCV de la fecha.',`<form data-endpoint="expenses"><div class="form-grid">${field('Concepto','concept',emp?`Nómina · ${emp.name}`:'','text','required maxlength="200"')}${select('Categoría','category',['Operación','Nómina','Servicios','Mantenimiento','Materiales','Otro'].map(x=>[x,x]),emp?'Nómina':'Operación')}${field('Fecha del egreso','spent_on',state.today,'date',`required max="${state.today}"`)}${select('Empleado asociado','employee_id',[['','No aplica'],...state.employees.map(e=>[e.id,e.name])],emp?.id||'')}${select('Moneda pagada','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],emp?'VES':'USD')}${field('Importe pagado','amount',emp?(Math.round(emp.salary*Number(todayRate()?.rate||0))/100).toFixed(2):'','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',['Efectivo','Transferencia','Tarjeta','Otro'].map(m=>[m,m]),'Transferencia')}${field('Referencia / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div></div><div class="actions" style="margin-top:15px">${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar egreso')}</form>`);updateConversion();
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
  showModal(esc(s.name),`${esc(s.grade_name)} · ${esc(s.guardian_name)} · ${esc(s.guardian_phone)}`,`<div class="mini-summary"><div><small>Saldo pendiente USD</small><b>${usd(s.balance)}</b></div><div><small>Deuda vencida USD</small><b class="text-red">${usd(s.overdue)}</b></div></div><div class="actions">${writable()?btn('Registrar pago','payment','primary',s.id)+btn('Crear cargo','charge','',s.id):''}${btn('Preparar aviso','collection','',s.id)}${writable()&&s.overdue?btn('Convenio de pago','payment-plan','',s.id):''}</div><h3 style="margin:22px 0 10px">Estado de cuenta</h3><div class="detail-table">${table(['Concepto / período','Vence','Cargo','Abono','Saldo'],list,c=>`<td>${esc(c.concept)}<span class="sub">${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td>${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}</td>`,'No hay cargos activos')}</div><h3 style="margin:22px 0 10px">Pagos</h3><div class="detail-table">${planLinks(s.id)}${table(['Recibo','Fecha','USD','Estado',''],payments,p=>`<td>R-${String(p.id).padStart(6,'0')}</td><td>${dateLabel(p.paid_on)}</td><td>${usd(p.amount)}</td><td>${badge(p.voided?'Anulado':'Válido',p.voided?'red':'')}</td><td>${btn('Ver','receipt','small',p.id)}</td>`,'Sin pagos')}</div>`);
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
function schoolHeader(s,title,code,on) {
  const logo=s.logo==='logo-colegio-v1.png'?`<img src="/logo-colegio-v1.png" alt="Logo del colegio" width="1215" height="1295">`:icon('book');
  const address=s.fiscal_address||s.address;
  return `<header class="document-header"><div class="school-emblem">${logo}</div><div class="school-info"><h1>${esc(s.legal_name||s.school_name)}</h1>${s.rif?`<p class="school-rif">RIF: ${esc(s.rif)}</p>`:''}${address?`<p class="fiscal-address"><b>Domicilio fiscal:</b> ${esc(address)}</p>`:''}${[s.phone,s.email,s.website].some(Boolean)?`<p class="school-contact">${[s.phone,s.email,s.website].filter(Boolean).map(esc).join(' · ')}</p>`:''}</div><div class="document-number"><span>${esc(title)}</span><b class="receipt-number">${esc(code)}</b><span>${dateLabel(on)}</span></div></header>`;
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
  showDocument('Constancia de matrícula','enrollment/'+id,`<article class="receipt school-document">${schoolHeader(d.school,'Constancia de matrícula','M-'+String(id).padStart(6,'0'),d.issued_on||d.created_at.slice(0,10))}<div class="document-section"><h3>Datos del alumno</h3><dl><dt>Nombre completo</dt><dd>${esc(s.name)}</dd><dt>Código único</dt><dd>${esc(s.student_code)}</dd><dt>Cédula / documento</dt><dd>${s.document===s.student_code?'Sin cédula propia':esc(s.document)}</dd><dt>Nacimiento</dt><dd>${dateLabel(s.birth_date)}</dd><dt>Grado / año escolar</dt><dd>${esc(s.grade_name)} · ${s.school_year}–${s.school_year+1}</dd><dt>Vigencia</dt><dd>${dateLabel(s.enrollment_start)} al ${dateLabel(s.enrollment_end)} · ${s.status==='active'?'Activo':'Inactivo'}</dd></dl></div><div class="document-section"><h3>Representante legal</h3><dl><dt>Nombre / cédula</dt><dd>${esc(s.guardian_name)} · ${esc(s.guardian_document)}</dd><dt>Contacto</dt><dd>${esc(s.guardian_phone)} · ${esc(s.guardian_email)}</dd><dt>Dirección</dt><dd>${esc(s.guardian_address)}</dd></dl></div>${table(['Mensualidad base USD','Beca / descuento','Mensualidad final USD'],[s],r=>`<td>${usd(r.monthly_fee)}</td><td>${r.discount} %</td><td><strong>${usd(r.net_fee)}</strong></td>`)}<p class="hint">La tarifa se aplica a cargos nuevos. Los cargos existentes conservan su importe.</p><p>Observaciones: ${esc(s.notes)||'—'}</p><div class="signature-row"><span>Administración</span><span>Representante legal</span></div><p class="document-footer">Registrado por ${esc(d.operator)} · Constancia administrativa de matrícula</p></article>`);
}
async function payrollDocument(id) {
  const d=await api('payroll-plan/'+id);
  showDocument('Relación de pago consolidada','payroll-plan/'+id,`<article class="receipt school-document payroll-document">${schoolHeader(d.school,'Relación de pago','N-'+String(id).padStart(6,'0'),d.pay_date)}<h3>${esc(d.name)}</h3><p>BCV aplicada: Bs ${esc(d.rate)} por USD · ${dateLabel(d.pay_date)}</p><p class="hint">Preparación de nómina. Este documento no registra egresos ni acredita pagos realizados.</p>${table(['Empleado / cédula / cargo','Banco / tipo / cuenta','Titular / cédula','Monto USD','Monto Bs'],d.lines,r=>`<td>${esc(r.name)}<span class="sub">${esc(r.document)} · ${esc(r.position)}</span></td><td>${esc(r.bank)||'BANCO PENDIENTE'}<span class="sub">${esc(r.account_type)} · ${esc(r.bank_account)||'CUENTA PENDIENTE'}</span></td><td>${esc(r.account_holder||r.name)}<span class="sub">${esc(r.holder_document||r.document)}</span></td><td>${usd(r.amount_usd)}</td><td>${bs(r.amount_ves)}</td>`)}<div class="receipt-total">Total propuesto: <b>${usd(d.total_usd)} · ${bs(d.total_ves)}</b></div><div class="signature-row"><span>Preparado por ${esc(d.operator)}</span><span>Aprobado por</span></div></article>`);
}
async function receipt(id) {
  const r=await api('receipt/'+id), p=r.payment;
  const period = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value)?monthLabel(value):value;
  const markup=`<article class="receipt school-document payment-receipt">${schoolHeader(r.settings,'Comprobante de pago','R-'+String(p.id).padStart(6,'0'),p.paid_on)}${p.voided?`<div class="receipt-void"><b>COMPROBANTE ANULADO</b><p>${esc(p.void_reason)}</p></div>`:''}<div class="receipt-parties"><section><span class="receipt-label">Representante legal</span><h2>${esc(p.guardian_name)}</h2><p>Cédula: ${esc(p.guardian_document)}</p>${p.guardian_phone?`<p>${esc(p.guardian_phone)}</p>`:''}</section><section><span class="receipt-label">Alumno · Grado / sección</span><h2>${esc(p.student_name)}${p.grade_name?`<span class="receipt-student-grade"> · ${esc(p.grade_name)}</span>`:''}</h2>${p.grade_name?'':'<p>Grado no registrado</p>'}<p>Código: ${esc(p.student_code||p.student_document)}</p></section></div>${p.guardian_address?`<p class="receipt-address"><span>Dirección del representante</span>${esc(p.guardian_address)}</p>`:''}<section class="receipt-charges"><h3 class="receipt-label">Conceptos abonados</h3>${table(['Descripción','Período','Aplicado · USD'],r.allocations,a=>`<td>${esc(a.concept)}</td><td>${esc(period(a.period))}</td><td class="money">${usd(a.amount)}</td>`)}</section><div class="receipt-payment"><section class="receipt-method"><span class="receipt-label">Método de pago</span><p class="receipt-method-name">${esc(p.method)}</p>${p.reference?`<span class="receipt-label">Referencia / comprobante</span><p>${esc(p.reference)}</p>`:''}</section><section class="receipt-amount"><span class="receipt-label">Importe recibido · ${p.currency==='VES'?'Bolívares':'USD'}</span><div class="receipt-amount-value">${p.currency==='VES'?bs(p.received_amount):usd(p.received_amount)}</div><div class="receipt-applied"><span>Total aplicado en USD</span><b>${usd(p.amount)}</b></div>${p.currency==='VES'?`<p class="receipt-rate">Tasa BCV aplicada: Bs ${esc(p.exchange_rate)} por USD</p>`:''}</section></div>${p.notes?`<section class="receipt-notes"><span class="receipt-label">Observaciones</span><p>${esc(p.notes)}</p></section>`:''}<div class="signature-row"><span>Firma de administración</span><span>Firma del representante</span></div><footer class="receipt-bottom"><p>Registrado por: ${esc(p.operator)}</p><p>Comprobante administrativo · No sustituye una factura fiscal.</p></footer></article>`;
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
      case 'logout':await api('logout',{});modal.close();await boot();break;
      case 'year-transition':openYearTransition();break;case 'load-year':await loadYear();break;case 'preview-year':await previewYear();break;case 'confirm-year':await confirmYear();break;case 'year-document':await yearDocument(id);break;case 'payment-plan':openPaymentPlan(id);break;case 'plan-document':await planDocument(id);break;case 'cancel-plan':openVoid('cancel-plan',id);break;case 'import-roster':openImport();break;case 'preview-import':await previewImport();break;case 'confirm-import':await confirmImport();break;case 'guardian-account':await guardianAccount(id);break;case 'issue-account':await issueGuardian(id,'account');break;case 'issue-solvency':await issueGuardian(id,'solvency');break;case 'guardian-document':await guardianDocument(id);break;case 'open-cash':await openCash();break;case 'cash-document':await cashDocument(id);break;case 'reopen-cash':openVoid('reopen-cash',id);break;case 'guardian':openGuardian(id);break;case 'grade':openGrade(id);break;case 'student':openStudent(id);break;
      case 'positions':openPositions(id);break;case 'payroll-plan':openPayrollPlan();break;case 'payroll-document':await payrollDocument(id);break;case 'enrollment':await enrollmentDocument(id);break;case 'employee':openEmployee(id);break;case 'payment':openPayment(id);break;case 'expense':openExpense();break;
      case 'payroll':openExpense(id);break;case 'charge':openCharge(id);break;case 'generate':openGenerate();break;
      case 'rates':openRates();break;case 'account':account(id);break;case 'collection':collection(id);break;case 'followup':openFollowup(id);break;
      case 'void-payment':case 'void-expense':case 'cancel-charge':openVoid(action,id);break;
      case 'user':openUser();break;case 'password':openPassword(id);break;case 'receipt':await receipt(id);break;
      case 'print-receipt':window.print();break;case 'print-report':printReport();break;
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
  if(endpoint==='payment-plans'){data.expected_total=Number(data.expected_total);data.installments=Array.from(form.querySelectorAll('[data-plan-row]')).map(row=>({amount:row.querySelector('[data-plan-amount]').value,due_date:row.querySelector('[data-plan-date]').value}));}
  if(endpoint==='payroll-plans') data.lines=Array.from(form.querySelectorAll('[data-payroll-employee]')).map(input=>({employee_id:input.dataset.payrollEmployee,amount:input.value}));
  const submit=form.querySelector('[type="submit"]'), errorBox=$('.error',form);submit.disabled=true;errorBox.textContent='';
  try {
    const result=await api(endpoint,data);
    if(['login','setup'].includes(endpoint)){await boot();return;}
    if(endpoint==='confirm-rate'){await refresh();return;}
    if(endpoint==='password'&&Number(data.user_id)===state.user.id){modal.close();await boot();return;}
    await refresh();if(endpoint!=='rates')modal.close();
    if(endpoint==='payment-plans'){toast('Convenio guardado.');await planDocument(result.id);}
    else if(endpoint==='close-cash'){toast('Caja cerrada.');await cashDocument(result.id);}
    else if(endpoint==='payments'){toast(result.duplicate?'El pago ya estaba registrado.':'Pago registrado correctamente.');await receipt(result.id);}
    else if(endpoint==='students'){toast(`Matrícula guardada · ${result.student_code}`);await enrollmentDocument(result.id,result.document_id);}
    else if(endpoint==='payroll-plans'){await payrollDocument(result.id);}
    else if(endpoint==='generate')toast(`${result.created} mensualidades creadas. Los cargos existentes no se duplicaron.`);
    else {toast('Registro guardado correctamente.');if(endpoint==='rates')openRates();}
    if(result.backup_warning)toast('Operación guardada. '+result.backup_warning,true);
  }catch(error){errorBox.textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.id==='collection-text'){const link=$('#wa-collection');if(link){const url=new URL(link.href);url.searchParams.set('text',el.value);link.href=url.href;}}
  if(el.id==='plan-count'){buildPlanRows();return;}
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
function backupStale(){const time=Date.parse(state.backup?.local_at||'');return !Number.isFinite(time)||Date.now()-time>86400000||!!state.backup?.local_error;}
function backupLabel(){
  const b=state.backup||{};
  if(b.local_error)return esc(b.local_error);
  if(!Number.isFinite(Date.parse(b.local_at||'')))return 'Sin respaldo automático confirmado';
  const minutes=Math.max(0,Math.floor((Date.now()-Date.parse(b.local_at))/60000));
  return 'Último respaldo '+(minutes<1?'hace menos de un minuto':minutes<60?`hace ${minutes} min`:minutes<1440?`hace ${Math.floor(minutes/60)} h`:`hace ${Math.floor(minutes/1440)} días`);
}
function backupProblem(){const b=state.backup||{};return b.local_error||b.secondary_error?`<div class="notice backup-warning" role="alert"><div><b>Revisa los respaldos</b><p>${esc(b.local_error||b.secondary_error)}</p></div></div>`:'';}
function openImport(){
  rosterFile=rosterPreview=undefined;
  showModal('Importar alumnos y representantes','Carga inicial con vista previa. No modifica alumnos ni representantes existentes.',`<p>Descarga la plantilla, completa una fila por alumno y conserva los encabezados. Los hermanos pueden repetir los datos del mismo representante.</p><div class="actions"><a class="btn" href="/api/import-template?format=xlsx" download>Plantilla Excel (.xlsx)</a><a class="btn" href="/api/import-template" download>Plantilla CSV</a></div><p class="hint">Fechas: AAAA-MM-DD o fechas de Excel. Mensualidad: dólares, sin símbolos y con punto decimal. Grado: nombre exacto del catálogo. Año escolar: año de inicio. Cédulas, teléfonos y códigos: texto. Sin fórmulas. Se admite .xlsx o CSV UTF-8, hasta 2 MB / 1000 alumnos.</p><label class="field">Archivo<input id="roster-file" type="file" accept=".csv,.xlsx"></label><div class="notice"><div><b>Revisa las fechas de matrícula</b>Se generarán mensualidades desde el inicio indicado hasta el mes actual. Esta importación no incorpora pagos anteriores: regístralos aparte para que los saldos reflejen la deuda real.</div></div><div class="actions">${btn('Revisar archivo','preview-import','primary')}</div><div id="roster-preview" aria-live="polite"></div>`);
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
    $('#roster-preview').innerHTML=`<h3>Vista previa · ${rosterPreview.rows} filas</h3><p>${rosterPreview.students} alumnos válidos · ${rosterPreview.guardians} representantes nuevos · cargos nuevos: <b>${usd(rosterPreview.new_balance)}</b>.</p>${rosterPreview.errors.length?`<p class="text-red">${rosterPreview.errors.length} errores. No se guardará ninguna fila hasta corregir el archivo.</p>${table(['Fila','Error'],rosterPreview.errors,e=>`<td>${e.row}</td><td class="wrap-cell">${esc(e.message)}</td>`)}`:`<p class="text-green">Sin errores de validación. Los códigos se asignarán al confirmar.</p>${table(['Fila','Alumno','Representante','Grado'],rosterPreview.lines,r=>`<td>${r.row}</td><td>${esc(r.student_name)}</td><td>${esc(r.guardian_name)}</td><td>${esc(r.grade_name)}</td>`)}${rosterPreview.rows>100?'<p>Se muestran las primeras 100 filas; todas fueron validadas.</p>':''}<label class="confirm-check"><input id="import-reviewed" type="checkbox"> Revisé las fechas, las tarifas y los cargos que se crearán.</label><div class="form-actions">${btn('Confirmar importación','confirm-import','primary')}</div>`}`;
  }finally{button.disabled=false;}
}
async function confirmImport(){
  if(!rosterPreview||rosterPreview.errors.length||!$('#import-reviewed')?.checked)throw new Error('Revisa la vista previa y marca la confirmación.');
  const button=modal.querySelector('[data-action="confirm-import"]');button.disabled=true;
  try{const result=await api('import-roster',{...rosterFile,confirmed_hash:rosterPreview.hash});modal.close();page='students';filters={};await refresh();toast(`${result.students} alumnos y ${result.guardians} representantes importados.`);if(result.backup_warning)toast('Importación guardada. '+result.backup_warning,true);}
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
function dailyDashboard(){
  const today=state.today,end=new Date(today+'T12:00:00'),start=new Date(today+'T12:00:00');end.setDate(end.getDate()+6);start.setDate(start.getDate()-7);
  const due=state.charges.filter(c=>c.balance>0&&c.due_date>=today&&c.due_date<=isoDay(end));
  const newDebtors=state.students.filter(s=>{const overdue=state.charges.filter(c=>c.student_id===s.id&&c.overdue);return overdue.length&&overdue.every(c=>c.due_date>=isoDay(start));});
  const paid=state.payments.filter(p=>!p.voided&&p.paid_on===today);
  return `<div class="stats daily-stats">${stat('Cobrado hoy',usd(paid.reduce((a,p)=>a+p.amount,0)),`${usd(paid.filter(p=>p.currency==='USD').reduce((a,p)=>a+p.received_amount,0))} recibidos · ${bs(paid.filter(p=>p.currency==='VES').reduce((a,p)=>a+p.received_amount,0))} recibidos`,'payments')}${stat('Vencen en los próximos 7 días',usd(due.reduce((a,c)=>a+c.balance,0)),`${due.length} cargos pendientes, desde hoy`,'clock')}${stat('Morosos nuevos · 7 días',newDebtors.length,'Primera deuda actualmente vencida en los últimos 7 días','arrears')}</div>${due.length?card('Vencimientos próximos',table(['Alumno / grado','Concepto / período','Vence','Saldo USD',''],due.slice(0,8),c=>`<td>${esc(c.student_name)}<span class="sub">${esc(c.grade_name)}</span></td><td>${esc(c.concept)}<span class="sub">${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td>${usd(c.balance)}</td><td>${btn('Cuenta','account','small',c.student_id)}</td>`),btn('Ver todos los cargos','nav','ghost','billing')):''}`;
}

function whatsappLink(phone,text){
  let digits=String(phone||'').replace(/\D/g,'');if(digits.length===11&&digits[0]==='0')digits='58'+digits.slice(1);else if(digits.length===10)digits='58'+digits;
  if(!/^58\d{10}$/.test(digits))return '<small>Completa un teléfono venezolano válido para abrir WhatsApp.</small>';
  return `<a id="wa-collection" class="btn" href="https://wa.me/${digits}?text=${encodeURIComponent(text)}" target="_blank" rel="noopener noreferrer">Abrir WhatsApp con el aviso</a>`;
}
