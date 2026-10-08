'use strict';
(() => {
  const narrow = matchMedia('(max-width:700px)');
  const standalone = () => matchMedia('(display-mode:standalone)').matches || navigator.standalone === true;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const install = document.querySelector('#phone-install');
  let installPrompt;

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
  window.AulaMobile = {render() {
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
  const showInstall = () => { install.hidden = standalone() || !narrow.matches || (!installPrompt && !ios) || !window.isSecureContext; };
  narrow.addEventListener('change', showInstall);
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); installPrompt = event; showInstall();
  });
  window.addEventListener('appinstalled', () => { installPrompt = undefined; install.hidden = true; });
  install.addEventListener('click', async () => {
    if (installPrompt) {
      const prompt = installPrompt; installPrompt = undefined;
      await prompt.prompt(); await prompt.userChoice; showInstall();
    } else if (ios) {
      window.alert('En Safari, abre Compartir y elige «Añadir a pantalla de inicio». Activa «Abrir como app» si aparece. Usa el enlace privado del colegio con la conexión privada activa.');
    }
  });
  showInstall();
  // Native Windows and trial instances do not need a service worker.
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    navigator.serviceWorker.register('/service-worker.js', {updateViaCache:'none'})
      .catch(() => { /* Browser access still works when installation is unavailable. */ });
  }
})();
