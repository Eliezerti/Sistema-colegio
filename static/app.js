'use strict';
const $ = (s, root = document) => root.querySelector(s);
const app = $('#app'), modal = $('#modal');
let state, session, page = 'dashboard', filters = {}, reportFrom = '', reportTo = '';
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
const navItems = [['dashboard','Resumen','dashboard'],['students','Alumnos y matrículas','students'],['guardians','Representantes','guardians'],['grades','Grados y secciones','grades'],['billing','Mensualidades y cargos','billing'],['payments','Caja y cobros','payments'],['arrears','Morosidad','arrears'],['employees','Personal','employees'],['expenses','Egresos y nómina','expenses'],['reports','Reportes','reports'],['settings','Configuración','settings']];
function render() {
  if (!state) return;
  if (page === 'settings' && !admin()) page = 'dashboard';
  document.title = state.settings.school_name + " · Administración escolar";
  const rate = todayRate(), current = navItems.find(n => n[0] === page);
  app.innerHTML = `<div class="layout"><aside class="sidebar"><div class="brand"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>${esc(state.settings.school_name)}</b><small>Administración escolar</small></div></div><nav>${navItems.filter(n => n[0] !== 'settings' || admin()).map((n,i) => `${[0,4,7,9].includes(i) ? `<div class="nav-label">${({0:'Colegio',4:'Finanzas',7:'Administración',9:'Gestión'})[i]}</div>` : ''}<button class="nav-button ${page === n[0] ? 'active' : ''}" data-action="nav" data-id="${n[0]}">${icon(n[2])}${n[1]}${n[0] === 'arrears' && state.summary.debtors ? `<span class="count">${state.summary.debtors}</span>` : ''}</button>`).join('')}</nav><div class="sidebar-footer"><div class="local-pill"><span class="dot"></span>Una computadora · Datos locales</div><div class="profile"><div class="avatar">${esc(state.user.name.slice(0,1).toUpperCase())}</div><div class="profile-text"><b>${esc(state.user.name)}</b><small>${roleLabel(state.user.role)}</small></div><button class="logout" data-action="logout" title="Cerrar sesión" aria-label="Cerrar sesión">${icon('logout')}</button></div></div></aside><main class="main"><header class="topbar"><div class="breadcrumb">${esc(state.settings.school_name)} <span> / </span> <b>${current[1]}</b></div><div class="top-info"><span>${dateLabel(state.today)}</span><button class="rate-chip" data-action="rates">${rate ? `BCV · Bs ${number(Number(rate.rate))} / USD` : 'BCV · Tasa de hoy pendiente'}</button></div></header><div id="page-content">${pageBody()}</div><div class="welcome-line"><span>${esc(state.settings.school_name)} · Administración escolar</span><span>Año escolar ${esc(state.settings.school_year)}–${Number(state.settings.school_year)+1} · Base USD</span></div></main></div>`;
}
function heading(title, description, actions = '') { return `<div class="page-heading"><div><div class="eyebrow">${esc(state.settings.school_name)}</div><h1>${title}</h1><p>${description}</p></div><div class="actions">${actions}</div></div>`; }
function pageBody() {
  return ({dashboard,students:studentsPage,guardians:guardiansPage,grades:gradesPage,billing:billingPage,payments:paymentsPage,arrears:arrearsPage,employees:employeesPage,expenses:expensesPage,reports:reportsPage,settings:settingsPage}[page])();
}
function dashboard() {
  const s = state.summary;
  const pending = state.students.filter(x => x.overdue > 0).sort((a,b) => b.overdue-a.overdue).slice(0,5);
  const recent = state.payments.filter(p => !p.voided).slice(0,5);
  const setup = !state.students.length && admin() ? `<div class="notice">${icon('book')}<div><b>Tu colegio empieza aquí</b>Configura tus datos, crea un grado y un representante; después matricula al primer alumno.<div class="steps"><button class="step" data-action="nav" data-id="settings">1. Datos del colegio</button><button class="step" data-action="grade">2. Grados</button><button class="step" data-action="guardian">3. Representantes</button><button class="step" data-action="student">4. Alumnos</button></div></div></div>` : '';
  return heading('Resumen de tu colegio', `Este es el estado de tu colegio · ${monthLabel(state.today.slice(0,7))}`, writable() ? btn(`${icon('plus')} Registrar pago`,'payment','primary') : '') + setup +
    `<div class="stats">${stat('Cobrado este mes',usd(s.income), 'Equivalente USD de pagos válidos','payments','featured')}${stat('Saldo pendiente',usd(s.pending), 'Incluye cargos vencidos y por vencer','billing')}${stat('Deuda vencida',usd(s.overdue), `${s.debtors} alumnos con mensualidades o cargos vencidos`,'arrears','alert')}${stat('Alumnos activos',s.active_students, 'Matrículas activas registradas','students')}</div>` +
    `<div class="grid-two"><div>${card('Cobros recientes',table(['Alumno / recibo','Recibido','Fecha'],recent,p=>`<td><button class="btn ghost" data-action="receipt" data-id="${p.id}">${esc(p.student_name)}</button><span class="sub">R-${String(p.id).padStart(6,'0')} · ${esc(p.method)}</span></td><td class="money">${p.currency === 'VES' ? bs(p.received_amount) : usd(p.amount)}<span class="sub">${p.currency === 'VES' ? usd(p.amount) + ' · equivalente' : 'Dólares'}</span></td><td>${dateLabel(p.paid_on)}</td>`,'Tu primer cobro aparecerá aquí'),btn('Ver caja →','nav','ghost','payments'))}${card('Prioridad de cobranza',table(['Alumno / representante','Vencido',''],pending,x=>`<td><b>${esc(x.name)}</b><span class="sub">${esc(x.guardian_name)} · ${esc(x.grade_name)}</span></td><td class="money text-red">${usd(x.overdue)}</td><td>${btn('Ver cuenta','account','small',x.id)}</td>`,'No hay deuda vencida'),btn('Ver morosidad →','nav','ghost','arrears'))}</div><div>${card('Antigüedad de la deuda',`<div class="card-body"><div class="balance-hero"><small>Total vencido · USD</small><div class="total">${usd(s.overdue)}</div><small>${todayRate() ? `Referencia hoy: ${bs(Math.round(s.overdue * Number(todayRate().rate)))}` : 'Registra la tasa de hoy para consultar el equivalente en Bs'}</small></div>${['1–30 días','31–60 días','61–90 días','Más de 90'].map((label,i)=>`<div class="aging-row"><span>${label}</span><div class="bar-track"><div class="bar" style="width:${s.overdue ? s.aging[i]/s.overdue*100 : 0}%"></div></div><b>${usd(s.aging[i])}</b></div>`).join('')}<div class="collection-note">Los abonos se aplican al cargo pendiente más antiguo. La deuda se mantiene en USD y los pagos conservan su tasa original.</div></div>`,icon('clock'))}${card('Movimiento del mes',`<div class="card-body"><div class="list-line"><span>Ingresos por cobros</span><b class="text-green">${usd(s.income)}</b></div><div class="list-line"><span>Egresos registrados</span><b>${usd(s.expenses)}</b></div><div class="list-line"><span><b>Balance operativo</b><small>Ingresos menos egresos; equivalente USD</small></span><b>${usd(s.net)}</b></div></div>`,btn('Reportes →','nav','ghost','reports'))}</div></div>`;
}
function searchToolbar(placeholder, grade = false, extra = '') {
  return `<div class="toolbar"><input id="search" aria-label="Buscar" placeholder="${placeholder}" value="${esc(filters.search || '')}">${grade ? `<select id="grade-filter" aria-label="Filtrar por grado"><option value="">Todos los grados</option>${state.grades.map(g=>`<option value="${g.id}" ${String(g.id) === filters.grade ? 'selected' : ''}>${esc(g.name)}</option>`).join('')}</select>` : ''}${extra}<span class="table-count" id="table-count"></span></div>`;
}
function matches(s) { const q = (filters.search || '').toLocaleLowerCase(); return (!filters.grade || String(s.grade_id) === filters.grade) && [s.name,s.document,s.student_code,s.guardian_name,s.phone,s.position].some(v=>String(v||'').toLocaleLowerCase().includes(q)); }
function studentsPage() {
  const records = state.students.filter(matches);
  return heading('Alumnos y matrículas','Expedientes, representantes, mensualidades y becas por alumno.',`${exportBtn('students')}${admin()?btn(`${icon('plus')} Matricular alumno`,'student','primary'):''}`) + card('Directorio de alumnos', searchToolbar('Buscar alumno, documento o representante…',true) + table(['Alumno','Grado / año','Mensualidad USD','Estado','Saldo USD',''],records,s=>`<td><b>${esc(s.name)}</b><span class="sub">${esc(s.student_code)} · ${esc(s.guardian_name)}</span></td><td>${esc(s.grade_name)}<span class="sub">${s.school_year}–${s.school_year+1}</span></td><td class="money">${usd(Math.floor((s.monthly_fee*(100-s.discount)+50)/100))}<span class="sub">${s.discount ? `Beca / descuento: ${s.discount}%` : 'Tarifa sin descuento'}</span></td><td>${badge(s.status==='active'?'Activo':'Inactivo',s.status==='active'?'':'neutral')}</td><td class="money ${s.overdue?'text-red':''}">${usd(s.balance)}</td><td>${actionsCell(btn('Cuenta','account','small',s.id)+btn('Constancia','enrollment','small',s.id)+(admin()?btn('Editar','student','small',s.id):''))}</td>`,'Aún no hay alumnos matriculados'), `<span class="muted">${records.length} alumnos</span>`);
}
function guardiansPage() {
  const records = state.guardians.filter(matches);
  return heading('Representantes','Personas responsables de los alumnos y sus datos de contacto.',admin()?btn(`${icon('plus')} Nuevo representante`,'guardian','primary'):'') + card('Directorio de representantes',searchToolbar('Buscar representante o documento…')+table(['Representante','Contacto','Alumnos',''],records,g=>`<td><b>${esc(g.name)}</b><span class="sub">${esc(g.document)}</span></td><td>${esc(g.phone)||'—'}<span class="sub">${esc(g.email)}</span></td><td>${state.students.filter(s=>s.guardian_id===g.id).length}</td><td>${admin()?btn('Editar','guardian','small',g.id):''}</td>`,'Registra al primer representante'));
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
  return heading('Morosidad y cobranza','Deuda vencida, antigüedad y seguimiento por alumno y representante.',exportBtn('arrears')) + `<div class="stats">${stat('Deuda vencida visible',usd(sum),'Total del filtro actual','arrears','alert')}${stat('Alumnos en mora',records.length,'Del filtro actual','students')}${stat('Equivalente en bolívares',todayRate()?bs(Math.round(sum*Number(todayRate().rate))):'—',todayRate()?'Referencia con tasa BCV de hoy':'Falta registrar la tasa BCV de hoy','payments')}${stat('Mayor atraso',Math.max(0,...state.charges.filter(c=>c.overdue && records.some(s=>s.id===c.student_id)).map(c=>c.days_overdue))+'<span>días</span>','Cargo vencido más antiguo del filtro','clock')}</div>`+card('Cuentas que requieren seguimiento',searchToolbar('Buscar alumno o representante…',true)+table(['Alumno / grado','Representante / contacto','Deuda vencida USD','Antigüedad',''],records,s=>{const days=Math.max(...state.charges.filter(c=>c.student_id===s.id&&c.overdue).map(c=>c.days_overdue));return `<td><b>${esc(s.name)}</b><span class="sub">${esc(s.grade_name)}</span></td><td>${esc(s.guardian_name)}<span class="sub">${esc(s.guardian_phone)||'Sin teléfono'}</span></td><td class="money text-red">${usd(s.overdue)}</td><td>${badge(days+' días',days>30?'red':'neutral')}</td><td>${actionsCell(btn('Cuenta','account','small',s.id)+btn('Aviso','collection','small',s.id)+(writable()?btn('Seguimiento','followup','small',s.id)+btn('Cobrar','payment','small primary',s.id):''))}</td>`;},'No hay deuda vencida con este filtro'));
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
  return heading('Reportes administrativos','Consulta el flujo de caja y descarga los libros completos en CSV.',btn(`${icon('print')} Imprimir resumen`,'print-report'))+`<div class="card"><div class="toolbar">${field('Desde','report-from',reportFrom,'date','id="report-from"')}${field('Hasta','report-to',reportTo,'date','id="report-to"')}<span class="table-count">${payments.length} cobros · ${expenses.length} egresos válidos</span></div></div><div class="stats">${stat('Ingresos del período',usd(income),'Equivalente USD','payments','featured')}${stat('Egresos del período',usd(out),'Equivalente USD','expenses')}${stat('Balance del período',usd(income-out),'Ingresos menos egresos','reports')}${stat('Deuda vencida actual',usd(state.summary.overdue),'Corte de hoy, independiente del filtro','arrears','alert')}</div><div class="grid-two">${card('Cobros por método',`<div class="card-body">${['Efectivo','Transferencia','Tarjeta','Otro'].map(method=>`<div class="list-line"><span>${method}</span><b>${usd(payments.filter(p=>p.method===method).reduce((t,p)=>t+p.amount,0))}</b></div>`).join('')}<div class="list-line"><span>Recibido en dólares <small>Importe original, sin conversión</small></span><b>${usd(payments.filter(p=>p.currency==='USD').reduce((t,p)=>t+p.received_amount,0))}</b></div><div class="list-line"><span>Recibido en bolívares <small>Importe original, sin conversión</small></span><b>${bs(payments.filter(p=>p.currency==='VES').reduce((t,p)=>t+p.received_amount,0))}</b></div><p class="hint">El equivalente USD usa la tasa conservada en cada operación; sumar bolívares no cambia los saldos históricos.</p></div>`)}${card('Exportación de libros',`<div class="card-body"><p class="muted">Descargas completas para abrir en Excel. Incluyen operaciones anuladas identificadas como tales.</p><div class="list-line"><span>Morosidad actual</span>${exportBtn('arrears','Descargar')}</div><div class="list-line"><span>Historial de pagos y tasas</span>${exportBtn('payments','Descargar')}</div><div class="list-line"><span>Alumnos y saldos</span>${exportBtn('students','Descargar')}</div><div class="list-line"><span>Egresos y nómina</span>${exportBtn('expenses','Descargar')}</div></div>`)}</div>`;
}
function settingsPage() {
  const s=state.settings;
  return heading('Configuración','Datos del colegio, año escolar, usuarios y respaldos.')+card('Datos del colegio',`<div class="branding-preview"><img src="/logo-colegio-v1.png" alt="Logo del colegio"><div><b>Identidad del colegio</b><p>El logo y los datos fiscales se incluyen en recibos, constancias, relaciones de nómina y reportes impresos.</p><a href="/logo-colegio-v1.png" download="Logo-Alejandro-Von-Humboldt.png">Descargar logo PNG</a></div></div><form class="card-body" data-endpoint="settings"><div class="form-grid">${field('Nombre del colegio','school_name',s.school_name,'text','required maxlength="200"')}${field('Razón social fiscal','legal_name',s.legal_name,'text','maxlength="200"','Nombre legal que aparecerá en los documentos.')}${field('RIF del colegio','rif',s.rif)}${field('Correo del colegio','email',s.email,'email')}${field('Sitio web','website',s.website)}${field('Teléfono','phone',s.phone)}${field('Dirección de contacto','address',s.address)}${textarea('Domicilio fiscal','fiscal_address',s.fiscal_address,500)}${field('Año de inicio del año escolar','school_year',s.school_year,'number','required min="2000" max="2100"',`Ejemplo: 2026 para el año 2026–2027.`)}${select('Mes de inicio del año escolar','start_month',Array.from({length:12},(_,i)=>[i+1,new Date(2020,i,1).toLocaleDateString('es-VE',{month:'long'})]),s.start_month)}${field('Día de vencimiento mensual','due_day',s.due_day,'number','required min="1" max="31"','Si el mes tiene menos días, se usa el último día.')}</div><p class="hint">Moneda base: USD. Pagos y egresos: USD o bolívares. Los documentos nuevos utilizan estos datos. Los documentos ya emitidos conservan la información original. Cambiar la configuración no recalcula cargos ni pagos ya registrados.</p><div class="error" role="alert"></div><div class="form-actions"><button class="btn primary" type="submit">Guardar configuración</button></div></form>`)+`<div class="grid-two">${card('Usuarios y permisos',table(['Nombre / usuario','Perfil',''],state.users,u=>`<td><b>${esc(u.name)}</b><span class="sub">${esc(u.username)}</span></td><td>${roleLabel(u.role)}</td><td>${btn('Contraseña','password','small',u.id)}</td>`),btn('Crear usuario','user','small'))}${card('Tasas y respaldo',`<div class="card-body"><div class="list-line"><span>Tasas BCV por fecha<small>Registro manual; cada operación conserva su tasa.</small></span>${btn('Gestionar','rates','small')}</div><div class="list-line"><span>Base de datos completa<small>Incluye usuarios, cobros y expedientes.</small></span><a class="btn small" href="/api/backup" download>${icon('download')} Respaldo</a></div><p class="hint">Guarda respaldos periódicos en un dispositivo distinto. La restauración se realiza con el sistema cerrado; sigue las instrucciones del archivo README.</p></div>`)}</div>`+card('Bitácora de operaciones',table(['Fecha','Usuario','Operación','Detalle'],state.audit,a=>`<td>${esc(new Date(a.created_at).toLocaleString('es-VE',{timeZone:'America/Caracas'}))}</td><td>${esc(a.operator)||'—'}</td><td>${esc(a.action)}</td><td class="audit-detail" title="${esc(a.details)}">${esc(a.details)}</td>`,'Sin operaciones'),'<small>Últimas 300 operaciones</small>');
}
function showModal(title, subtitle, body) {
  modal.classList.remove('document-modal');
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
  showModal('Registrar pago','El abono se aplica a los cargos pendientes más antiguos.',`<form data-endpoint="payments"><input type="hidden" name="request_key" value="${crypto.randomUUID()}"><div class="form-grid">${select('Alumno','student_id',candidates.map(s=>[s.id,`${s.name} · ${usd(s.balance)}`]),id||candidates[0].id,'required')}${field('Fecha del pago','paid_on',state.today,'date',`required max="${state.today}"`)}${select('Moneda recibida','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],'USD')}${field('Importe recibido','amount','','number','required min="0.01" step="0.01" max="999999999"')}${select('Método de pago','method',['Efectivo','Transferencia','Tarjeta','Otro'].map(m=>[m,m]),'Transferencia')}${field('Referencia bancaria / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div>${textarea('Observaciones','notes')}</div><div class="actions" style="margin-top:15px">${btn('Completar saldo','full-payment','small')}${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar y emitir recibo')}</form>`);
  updateConversion();
}
function updateConversion() {
  const form=$('form[data-endpoint="payments"]',modal)||$('form[data-endpoint="expenses"]',modal);
  if(!form)return;
  const data=Object.fromEntries(new FormData(form)), rate=state.rates.find(r=>r.rate_date===(data.paid_on||data.spent_on)), amount=Number(data.amount||0), student=state.students.find(s=>s.id===Number(data.student_id));
  const panel=$('#conversion',form);
  if(data.currency==='VES'&&!rate) {panel.innerHTML=`<span class="text-red">Falta la tasa BCV del ${dateLabel(data.paid_on||data.spent_on)}. Regístrala antes de guardar.</span>`;return;}
  const equivalent=data.currency==='VES'?Math.round(amount/Number(rate.rate)*100):Math.round(amount*100);
  panel.innerHTML=`${data.currency==='VES'?`BCV registrada: Bs ${esc(rate.rate)} por USD`:'Pago directo en dólares'}<strong>Equivalente: ${usd(equivalent)}</strong>${student?`Saldo antes del pago: ${usd(student.balance)} · Después: ${usd(student.balance-equivalent)}`:'El egreso se incluirá en reportes por su equivalente USD.'}`;
}
function openExpense(employeeId) {
  const emp=state.employees.find(e=>e.id===Number(employeeId));
  showModal(emp?'Registrar pago de nómina':'Registrar egreso','Conserva el importe original, su moneda y la tasa BCV de la fecha.',`<form data-endpoint="expenses"><div class="form-grid">${field('Concepto','concept',emp?`Nómina · ${emp.name}`:'','text','required maxlength="200"')}${select('Categoría','category',['Operación','Nómina','Servicios','Mantenimiento','Materiales','Otro'].map(x=>[x,x]),emp?'Nómina':'Operación')}${field('Fecha del egreso','spent_on',state.today,'date',`required max="${state.today}"`)}${select('Empleado asociado','employee_id',[['','No aplica'],...state.employees.map(e=>[e.id,e.name])],emp?.id||'')}${select('Moneda pagada','currency',[['USD','Dólares · USD'],['VES','Bolívares · Bs']],emp?'VES':'USD')}${field('Importe pagado','amount',emp?(Math.round(emp.salary*Number(todayRate()?.rate||0))/100).toFixed(2):'','number','required min="0.01" step="0.01" max="999999999"')}${field('Referencia / comprobante','reference','','text','maxlength="200"')}<div class="conversion" id="conversion"></div></div><div class="actions" style="margin-top:15px">${btn('Registrar tasa BCV','rate-inline','small')}</div>${formFoot('Registrar egreso')}</form>`);updateConversion();
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
  showModal(esc(s.name),`${esc(s.grade_name)} · ${esc(s.guardian_name)} · ${esc(s.guardian_phone)}`,`<div class="mini-summary"><div><small>Saldo pendiente USD</small><b>${usd(s.balance)}</b></div><div><small>Deuda vencida USD</small><b class="text-red">${usd(s.overdue)}</b></div></div><div class="actions">${writable()?btn('Registrar pago','payment','primary',s.id)+btn('Crear cargo','charge','',s.id):''}${btn('Preparar aviso','collection','',s.id)}</div><h3 style="margin:22px 0 10px">Estado de cuenta</h3><div class="detail-table">${table(['Concepto / período','Vence','Cargo','Abono','Saldo'],list,c=>`<td>${esc(c.concept)}<span class="sub">${esc(c.period)}</span></td><td>${dateLabel(c.due_date)}</td><td>${usd(c.amount)}</td><td>${usd(c.paid)}</td><td class="money ${c.overdue?'text-red':''}">${usd(c.balance)}</td>`,'No hay cargos activos')}</div><h3 style="margin:22px 0 10px">Pagos</h3><div class="detail-table">${table(['Recibo','Fecha','USD','Estado',''],payments,p=>`<td>R-${String(p.id).padStart(6,'0')}</td><td>${dateLabel(p.paid_on)}</td><td>${usd(p.amount)}</td><td>${badge(p.voided?'Anulado':'Válido',p.voided?'red':'')}</td><td>${btn('Ver','receipt','small',p.id)}</td>`,'Sin pagos')}</div>`);
}
function collection(id) {
  const s=state.students.find(s=>s.id===Number(id));
  const text=`Estimado/a ${s.guardian_name}: ${state.settings.school_name} le informa que ${s.name} presenta un saldo vencido de USD ${number(s.overdue/100)} al ${dateLabel(state.today)}.${todayRate()?` Su equivalente de referencia es Bs ${number(s.overdue/100*Number(todayRate().rate))}, a la tasa BCV registrada para hoy (Bs ${todayRate().rate}/USD). Al pagar se aplicará la tasa vigente de la fecha del pago.`:''} Por favor, comuníquese con administración para regularizar su cuenta. Gracias.`;
  showModal('Aviso de cobranza',`Representante: ${esc(s.guardian_name)} · ${esc(s.guardian_phone)||'Sin teléfono'}`,`<p class="hint">Revisa el texto antes de compartirlo. El sistema prepara el aviso; no envía mensajes.</p><label class="field"><textarea id="collection-text" rows="8">${esc(text)}</textarea></label><div class="form-actions">${btn('Copiar aviso','copy-collection','primary')}</div>`);
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
function documentActions(path) {return `<div class="actions document-actions"><a class="btn primary" href="/api/${path}.pdf" download>${icon('download')} Descargar PDF</a>${btn(`${icon('print')} Imprimir`,'print-receipt')}</div>`;}
function showDocument(title,path,markup) {
  showModal(title,'Documento listo para descargar o imprimir.',documentActions(path)+markup);modal.classList.toggle('document-modal',markup.includes('payment-receipt'));$('#print-area').innerHTML=markup;
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
  const markup=`<article class="receipt school-document payment-receipt">${schoolHeader(r.settings,'Comprobante de pago','R-'+String(p.id).padStart(6,'0'),p.paid_on)}${p.voided?`<div class="receipt-void"><b>COMPROBANTE ANULADO</b><p>${esc(p.void_reason)}</p></div>`:''}<div class="receipt-parties"><section><span class="receipt-label">Representante legal</span><h2>${esc(p.guardian_name)}</h2><p>Cédula: ${esc(p.guardian_document)}</p>${p.guardian_phone?`<p>${esc(p.guardian_phone)}</p>`:''}</section><section><span class="receipt-label">Alumno</span><h2>${esc(p.student_name)}</h2><p>Código: ${esc(p.student_code||p.student_document)}</p></section></div>${p.guardian_address?`<p class="receipt-address"><span>Dirección del representante</span>${esc(p.guardian_address)}</p>`:''}<section class="receipt-charges"><h3 class="receipt-label">Conceptos abonados</h3>${table(['Descripción','Período','Aplicado · USD'],r.allocations,a=>`<td>${esc(a.concept)}</td><td>${esc(period(a.period))}</td><td class="money">${usd(a.amount)}</td>`)}</section><div class="receipt-payment"><section class="receipt-method"><span class="receipt-label">Método de pago</span><p class="receipt-method-name">${esc(p.method)}</p>${p.reference?`<span class="receipt-label">Referencia / comprobante</span><p>${esc(p.reference)}</p>`:''}</section><section class="receipt-amount"><span class="receipt-label">Importe recibido · ${p.currency==='VES'?'Bolívares':'USD'}</span><div class="receipt-amount-value">${p.currency==='VES'?bs(p.received_amount):usd(p.received_amount)}</div><div class="receipt-applied"><span>Total aplicado en USD</span><b>${usd(p.amount)}</b></div>${p.currency==='VES'?`<p class="receipt-rate">Tasa BCV aplicada: Bs ${esc(p.exchange_rate)} por USD</p>`:''}</section></div>${p.notes?`<section class="receipt-notes"><span class="receipt-label">Observaciones</span><p>${esc(p.notes)}</p></section>`:''}<div class="signature-row"><span>Firma de administración</span><span>Firma del representante</span></div><footer class="receipt-bottom"><p>Registrado por: ${esc(p.operator)}</p><p>Comprobante administrativo · No sustituye una factura fiscal.</p></footer></article>`;
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
      case 'guardian':openGuardian(id);break;case 'grade':openGrade(id);break;case 'student':openStudent(id);break;
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
  if(endpoint==='payroll-plans') data.lines=Array.from(form.querySelectorAll('[data-payroll-employee]')).map(input=>({employee_id:input.dataset.payrollEmployee,amount:input.value}));
  const submit=form.querySelector('[type="submit"]'), errorBox=$('.error',form);submit.disabled=true;errorBox.textContent='';
  try {
    const result=await api(endpoint,data);
    if(['login','setup'].includes(endpoint)){await boot();return;}
    if(endpoint==='confirm-rate'){await refresh();return;}
    if(endpoint==='password'&&Number(data.user_id)===state.user.id){modal.close();await boot();return;}
    await refresh();if(endpoint!=='rates')modal.close();
    if(endpoint==='payments'){toast(result.duplicate?'El pago ya estaba registrado.':'Pago registrado correctamente.');await receipt(result.id);}
    else if(endpoint==='students'){toast(`Matrícula guardada · ${result.student_code}`);await enrollmentDocument(result.id,result.document_id);}
    else if(endpoint==='payroll-plans'){await payrollDocument(result.id);}
    else if(endpoint==='generate')toast(`${result.created} mensualidades creadas. Los cargos existentes no se duplicaron.`);
    else {toast('Registro guardado correctamente.');if(endpoint==='rates')openRates();}
  }catch(error){errorBox.textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.id==='search'){
    const pos=el.selectionStart;filters.search=el.value;$('#page-content').innerHTML=pageBody();$('#search').focus();$('#search').setSelectionRange(pos,pos);
  }
  if(el.id==='guardian-search')searchGuardian();
  if(el.closest('form[data-endpoint="students"]'))updateTuition();
  if(el.closest('form[data-endpoint="payroll-plans"]'))updatePayroll();
  if(el.closest('form[data-endpoint="payments"], form[data-endpoint="expenses"]'))updateConversion();
});
document.addEventListener('change',event=>{
  const el=event.target;
  if(el.id==='grade-filter'){filters.grade=el.value;$('#page-content').innerHTML=pageBody();}
  if(el.id==='report-from'||el.id==='report-to'){
    const from=$('#report-from').value,to=$('#report-to').value;
    if(!from||!to||from>to){toast('Elige un rango de fechas válido.',true);return;}
    reportFrom=from;reportTo=to;$('#page-content').innerHTML=pageBody();
  }
  if(el.id==='guardian-search')searchGuardian();
  if(el.closest('form[data-endpoint="students"]'))updateTuition();
  if(el.closest('form[data-endpoint="payroll-plans"]'))updatePayroll();
  if(el.closest('form[data-endpoint="payments"], form[data-endpoint="expenses"]'))updateConversion();
});
modal.addEventListener('click',event=>{if(event.target===modal){const r=modal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)modal.close();}});
modal.addEventListener('close',()=>{if(!modal.open)$('#modal-content').replaceChildren();});
async function checkDay() {
  if(!state||document.hidden)return;
  try {const gate=await api('rate-gate');if(state&&gate.today!==state.today)await openRateGate();}catch(error){toast(error.message,true);}
}
setInterval(checkDay,60000);
document.addEventListener('visibilitychange',checkDay);
boot();
