'use strict';
(() => {
  const narrow = matchMedia('(max-width:700px)');

  function menu(open, restoreFocus = false) {
    const layout = document.querySelector('.layout'), sidebar = document.querySelector('.sidebar');
    if (!layout || !sidebar) return;
    const visible = open && narrow.matches;
    layout.classList.toggle('menu-open', visible);
    document.body.classList.toggle('mobile-menu-open', visible);
    sidebar.inert = narrow.matches && !visible;
    document.querySelector('.main').inert = visible;
    document.querySelector('.mobile-header').inert = visible;
    document.querySelector('.menu-backdrop').hidden = !visible;
    document.querySelector('[data-action="mobile-menu"]').setAttribute('aria-expanded', String(visible));
    if (visible) document.querySelector('.mobile-menu-close').focus();
    else if (restoreFocus) document.querySelector('[data-action="mobile-menu"]').focus();
  }
  window.AulaResponsive = {render() {
    menu(false);
    document.querySelectorAll('.table-wrap').forEach(table => {
      table.tabIndex = 0;
      table.setAttribute('role', 'region');
      table.setAttribute('aria-label', 'Tabla de registros. Desliza hacia los lados para ver todas las columnas.');
    });
  }};
  narrow.addEventListener('change', () => menu(false));
  document.addEventListener('click', event => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'mobile-menu') menu(true);
    if (action === 'mobile-menu-close') menu(false, true);
    if (action === 'logout') menu(false);
  });
  document.addEventListener('keydown', event => {
    if (!document.querySelector('.menu-open')) return;
    if (event.key === 'Escape') { event.preventDefault(); menu(false, true); }
    if (event.key === 'Tab') {
      const controls = [...document.querySelector('.sidebar').querySelectorAll('button, a[href]')]
        .filter(element => element.getClientRects().length && !element.disabled);
      if (event.shiftKey && document.activeElement === controls[0]) {
        event.preventDefault(); controls.at(-1).focus();
      } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
        event.preventDefault(); controls[0].focus();
      }
    }
  });
  menu(false);
  const connection = () => { document.querySelector('#connection-status').hidden = navigator.onLine; };
  window.addEventListener('offline', connection);
  window.addEventListener('online', connection);
  connection();
  // Retire only Aula's former worker/cache; do not touch other applications.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => Promise.all(
      registrations.filter(registration => {
        const worker = registration.active || registration.waiting || registration.installing;
        return worker && worker.scriptURL === new URL('/service-worker.js', location.origin).href;
      }).map(registration => registration.unregister())
    )).catch(() => {});
  }
  if ('caches' in window) {
    caches.keys().then(names => Promise.all(names.filter(name => name.startsWith('aula-mobile-public-'))
      .map(name => caches.delete(name)))).catch(() => {});
  }
})();
