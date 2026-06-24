/* ─── NITI Learn Service Worker ──────────────────────────────────────────── */
const CACHE_NAME    = 'niti-learn-v1';
const OFFLINE_URL   = '/offline';

// Assets to cache on install
const PRECACHE = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
];

// ── Install ──────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// ── Activate ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch — Network first, fallback to cache ─────────────────────────────────
self.addEventListener('fetch', event => {
  // Skip non-GET and API/socket requests
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/chat/') && url.pathname.includes('/messages')) return;
  if (url.pathname.startsWith('/live/') && url.pathname.includes('/signal')) return;
  if (url.pathname.startsWith('/notifications/')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cache successful responses for static assets
        if (response.ok && (
          url.pathname.startsWith('/static/') ||
          url.pathname === '/'
        )) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Offline fallback
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          // For navigation requests, return cached homepage
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
        });
      })
  );
});
