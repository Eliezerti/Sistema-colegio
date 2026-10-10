'use strict';
// Keep only a public offline notice and the logo. No accounts, API responses,
// documents, payments or application pages are ever put in Cache Storage.
const CACHE = 'aula-mobile-public-v3';
const PUBLIC_FILES = ['/offline.html', '/icon-mobile-192.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PUBLIC_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('aula-mobile-public-') && key !== CACHE)
    .map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (PUBLIC_FILES.includes(url.pathname) && !url.search) {
    event.respondWith(fetch(request).catch(() => caches.match(url.pathname)));
    return;
  }
  if (request.mode === 'navigate' && url.pathname === '/') {
    event.respondWith(fetch(request)
      .then(response => response.status >= 500 ? caches.match('/offline.html') : response)
      .catch(() => caches.match('/offline.html')));
  }
});
