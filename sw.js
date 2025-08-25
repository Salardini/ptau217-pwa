
const CACHE='amyloid-helper-v209';
const ASSETS=['./','./index.html','./styles.css','./app.js','./manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.map(k=>k!==CACHE?caches.delete(k):null))));self.clients.claim();});
// ===== BEGIN: Safe fetch handler (injected) =====
self.addEventListener('fetch', function(event) {
  try {
    const url = new URL(event.request.url);
    const isHTTP = (url.protocol === 'http:' || url.protocol === 'https:');
    const sameOrigin = (url.origin === self.origin || url.origin === self.location.origin);
    if (event.request.method !== 'GET' || !isHTTP || !sameOrigin) {
      return; // Don't intercept non-GET, non-http(s), or cross-origin (e.g., chrome-extension://)
    }
    event.respondWith(
      caches.match(event.request).then(function(resp) {
        if (resp) return resp;
        return fetch(event.request).then(function(networkResp) {
          try {
            const copy = networkResp.clone();
            // Try to detect an existing cache name; fallback if undefined.
            const CACHE_NAME = (typeof CACHE !== 'undefined' && CACHE) ? CACHE : 'ptau217-cache-v1';
            caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, copy); });
          } catch (e) {
            // swallow
          }
          return networkResp;
        });
      })
    );
  } catch (e) {
    // noop
  }
});
// ===== END: Safe fetch handler (injected) =====
\n
// ===== BEGIN: SW lifecycle helpers (injected) =====
self.addEventListener('install', (event) => {{
  try {{ self.skipWaiting(); }} catch(e) {{ /* noop */ }}
}});
self.addEventListener('activate', (event) => {{
  try {{ event.waitUntil((async () => {{ await self.clients.claim(); }})()); }} catch(e) {{ /* noop */ }}
}});
// ===== END: SW lifecycle helpers (injected) =====
\n
// ===== BEGIN: Safe fetch handler (injected) =====
const __CACHE_SUFFIX = '20250825201742';
const __CACHE_FALLBACK = 'ptau217-cache-v1-' + __CACHE_SUFFIX;
self.addEventListener('fetch', function(event) {{
  try {{
    const url = new URL(event.request.url);
    const isHTTP = (url.protocol === 'http:' || url.protocol === 'https:');
    const sameOrigin = (url.origin === self.origin || url.origin === self.location.origin);
    if (event.request.method !== 'GET' || !isHTTP || !sameOrigin) {{
      return; // avoid chrome-extension:// and cross-origin
    }}
    event.respondWith(
      caches.match(event.request).then(function(resp) {{
        if (resp) return resp;
        return fetch(event.request).then(function(networkResp) {{
          try {{
            const copy = networkResp.clone();
            const CACHE_NAME = (typeof CACHE !== 'undefined' && CACHE) ? (CACHE + '-' + __CACHE_SUFFIX) : __CACHE_FALLBACK;
            caches.open(CACHE_NAME).then(function(cache) {{ cache.put(event.request, copy); }});
          }} catch (e) {{ /* noop */ }}
          return networkResp;
        }});
      }})
    );
  }} catch (e) {{ /* noop */ }}
}});
// ===== END: Safe fetch handler (injected) =====
