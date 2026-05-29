const CACHE     = 'roadsos-v1';
const DB_NAME   = 'roadsos-db';
const QUEUE_KEY = 'sos-queue';

// ── Install: cache app shell ──────────────────────────────────
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(['/', '/index.html']))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

// ── Fetch: serve cached page when offline (bypass on localhost dev server) ──
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  
  const url = new URL(e.request.url);
  if(e.request.url.includes('openweathermap.org/img/wn/')){
    e.respondWith(
      caches.open('wx-icons').then(c=>
        c.match(e.request).then(hit=>
          hit||fetch(e.request).then(r=>{c.put(e.request,r.clone());return r;})
        )
      )
    );
    return;
  }

  if (url.port === '5173' || url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
    // Let browser request dev resources directly from Vite dev server without cache interception
    return;
  }

  e.respondWith(
    caches.match(e.request).then((hit) => {
      if (hit) return hit;
      return fetch(e.request).then((res) => {
        // Dynamically cache successfully loaded frontend resources (app scripts, stylesheets, fonts)
        if (res.ok && !url.pathname.startsWith('/api/') && !url.pathname.startsWith('/docs')) {
          const resClone = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, resClone));
        }
        return res;
      }).catch(() => {
        // Fallback for navigation requests (HTML page loads) when offline
        if (e.request.headers.get('accept')?.includes('text/html')) {
          return caches.match('/index.html') || caches.match('/');
        }
      });
    })
  );
});

// ── Background Sync: fires automatically when back online ─────
self.addEventListener('sync', (e) => {
  if (e.tag === 'sos-sync') e.waitUntil(flushQueue());
  if (e.tag === 'family-alert-sync') e.waitUntil(flushFamilyAlerts()); // ADD
});

async function flushQueue() {
  const queue    = await dbGet(QUEUE_KEY);
  const unsynced = queue.filter((e) => !e.synced);
  if (!unsynced.length) return;

  try {
    const res = await fetch('http://localhost:8000/api/sos/sync', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ events: unsynced }),
    });
    if (!res.ok) return;

    const { results } = await res.json();
    const done = new Set(results.filter((r) => r.synced).map((r) => r.eventId));
    await dbSet(QUEUE_KEY, queue.map((e) =>
      done.has(e.eventId) ? { ...e, synced: true } : e
    ));

    // Tell all open tabs the sync happened
    const clients = await self.clients.matchAll({ includeUncontrolled: true });
    clients.forEach((c) =>
      c.postMessage({ type: 'SOS_SYNCED', count: done.size })
    );
  } catch (_) {
    // Still offline — browser retries sync automatically
  }
}

// ── IndexedDB helpers (SW scope) ─────────────────────────────
function openDB() {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open(DB_NAME, 1);
    r.onupgradeneeded = (e) => e.target.result.createObjectStore('kv');
    r.onsuccess = (e) => resolve(e.target.result);
    r.onerror   = () => reject(r.error);
  });
}
async function dbGet(key) {
  const db = await openDB();
  return new Promise((res) => {
    const r = db.transaction('kv','readonly').objectStore('kv').get(key);
    r.onsuccess = () => res(r.result ?? []);
    r.onerror   = () => res([]);
  });
}
async function dbSet(key, val) {
  const db = await openDB();
  return new Promise((res, rej) => {
    const tx = db.transaction('kv','readwrite');
    tx.objectStore('kv').put(val, key);
    tx.oncomplete = res;
    tx.onerror    = () => rej(tx.error);
  });
}

// ── ADD: flushFamilyAlerts ─────────────────────────────────────
async function flushFamilyAlerts() {
  const ALERT_QUEUE = 'family-alert-queue';
  const queue       = await dbGet(ALERT_QUEUE);
  const unsynced    = queue.filter(a => !a.synced);
  if (!unsynced.length) return;

  try {
    const res = await fetch('http://localhost:8000/api/family/sync-offline', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ alerts: unsynced }),
    });
    if (!res.ok) return;

    const { results } = await res.json();
    const syncedIds = new Set(
      results.filter(r => r.synced).map(r => r.session_id)
    );

    // Mark synced in queue
    const updated = queue.map((a, i) =>
      i < unsynced.length ? { ...a, synced: true } : a
    );
    await dbSet(ALERT_QUEUE, updated);

    // Notify open tabs
    const clients = await self.clients.matchAll({ includeUncontrolled: true });
    clients.forEach(c =>
      c.postMessage({
        type:  'FAMILY_ALERT_SYNCED',
        count: syncedIds.size,
      })
    );
  } catch(_) {
    // Still offline — will retry on next sync
  }
}
