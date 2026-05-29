
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DB_NAME     = 'roadsos-db';
const ALERT_QUEUE = 'family-alert-queue';

// ── IndexedDB helpers ────────────────────────────────────────
const openDB = () => new Promise((resolve, reject) => {
  const r = indexedDB.open(DB_NAME, 1);
  r.onupgradeneeded = e => e.target.result.createObjectStore('kv');
  r.onsuccess = e => resolve(e.target.result);
  r.onerror   = () => reject(r.error);
});

const dbGet = async (key) => {
  const db = await openDB();
  return new Promise(res => {
    const r = db.transaction('kv','readonly').objectStore('kv').get(key);
    r.onsuccess = () => res(r.result ?? []);
    r.onerror   = () => res([]);
  });
};

const dbSet = async (key, val) => {
  const db = await openDB();
  return new Promise((res, rej) => {
    const tx = db.transaction('kv','readwrite');
    tx.objectStore('kv').put(val, key);
    tx.oncomplete = res;
    tx.onerror    = () => rej(tx.error);
  });
};


// ── Build offline SMS body (mobile browser fallback) ──────────
const buildOfflineSMS = (profile, coords) => {
  const url = `https://maps.google.com/?q=${coords.lat},${coords.lng}`;
  return [
    '🚨 ROADSOS EMERGENCY',
    `${profile.full_name || profile.name || 'Someone'} was in a road accident!`,
    `Location: ${url}`,
    `Blood type: ${profile.blood_type || profile.bloodType || 'Unknown'}`,
    'Please call 112 immediately.',
  ].join('\n');
};


// ── Open native SMS app on mobile (offline fallback) ──────────
const openNativeSMS = (contacts, profile, coords) => {
  const body    = buildOfflineSMS(profile, coords);
  const phones  = contacts.map(c => c.phone).join(',');
  const encoded = encodeURIComponent(body);
  const isIOS   = /iPad|iPhone|iPod/.test(navigator.userAgent);
  window.open(`sms:${phones}${isIOS ? '&' : '?'}body=${encoded}`);
};


// ── Queue alert for background sync (offline) ─────────────────
const queueFamilyAlert = async (alertData) => {
  const queue = await dbGet(ALERT_QUEUE);
  queue.push({ ...alertData, queued: true, synced: false, queuedAt: Date.now() });
  await dbSet(ALERT_QUEUE, queue);
};


// ── Register background sync for family alerts ────────────────
const requestAlertSync = async () => {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    if ('sync' in reg) await reg.sync.register('family-alert-sync');
  } catch(_) {}
};


// ── Start posting GPS to FastAPI every 5 seconds ─────────────
let gpsInterval = null;

export const startLocationSharing = (sessionId, onStop) => {
  if (gpsInterval) clearInterval(gpsInterval);

  gpsInterval = setInterval(async () => {
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(async (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;

      if (navigator.onLine) {
        try {
          await fetch(`${API_BASE}/api/family/location`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ session_id: sessionId, latitude: lat, longitude: lng }),
            signal:  AbortSignal.timeout(4000),
          });
        } catch(_) {
          // GPS post failed — will retry next interval
        }
      }
      // Cache locally for offline display
      localStorage.setItem('lastKnownPosition', JSON.stringify({ lat, lng }));
    });
  }, 5000);

  // Return cleanup function
  return () => {
    clearInterval(gpsInterval);
    gpsInterval = null;
  };
};

export const stopLocationSharing = (sessionId) => {
  clearInterval(gpsInterval);
  gpsInterval = null;
  // Close session on server
  fetch(`${API_BASE}/api/family/session/${sessionId}`, { method: 'DELETE' }).catch(() => {});
};


// ── MAIN FUNCTION — sendFamilyAlert() ─────────────────────────
// Call this alongside triggerSOS() when SOS fires
export const sendFamilyAlert = async (sosEventId, coords) => {
  const profile  = JSON.parse(localStorage.getItem('medicalProfile')   || '{}');
  let contacts = JSON.parse(localStorage.getItem('emergencyContacts') || '[]');
  if (!contacts.length && profile.emergency_contacts) {
    contacts = profile.emergency_contacts;
  }

  if (!contacts.length) {
    return { sent: false, reason: 'no_contacts' };
  }

  const alertData = {
    user_id:      profile.userId || 'anonymous',
    sos_event_id: sosEventId,
    patient_name: profile.full_name || profile.name,
    severity:     'P2',
    latitude:     coords.lat,
    longitude:    coords.lng,
    contacts,
  };

  // ── ONLINE PATH ──────────────────────────────────────────
  if (navigator.onLine) {
    try {
      const res = await fetch(`${API_BASE}/api/family/alert`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(alertData),
        signal:  AbortSignal.timeout(6000),
      });

      if (res.ok) {
        const data = await res.json();
        // Save session ID — used for GPS streaming and status updates
        localStorage.setItem('activeTrackingSession', data.session_id);
        // Start streaming GPS to server
        startLocationSharing(data.session_id);
        return {
          sent:         true,
          online:       true,
          session_id:   data.session_id,
          tracking_url: data.tracking_url,
          contacts:     data.contacts,
        };
      }
    } catch(_) {
      // Server failed — fall through to offline path
    }
  }

  // ── OFFLINE PATH ─────────────────────────────────────────
  // 1. Open native SMS app on mobile
  openNativeSMS(contacts, profile, coords);

  // 2. Queue for background sync — will send tracking link when online
  await queueFamilyAlert(alertData);
  await requestAlertSync();

  return {
    sent:      true,
    online:    false,
    queued:    true,
    sms_fallback: true,
  };
};


// ── Subscribe to live location updates (family view) ──────────
export const subscribeToTracking = (sessionId, onUpdate, onEnd) => {
  const es = new EventSource(`${API_BASE}/api/family/track/${sessionId}`);
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.done) { onEnd?.(data.reason); es.close(); }
      else onUpdate(data);
    } catch(_) {}
  };
  es.onerror = () => es.close();
  return () => es.close();
};

// ── Update session when hospital/ambulance confirmed ──────────
export const updateTrackingStatus = async (sessionId, { hospitalName, ambulanceName, severity }) => {
  if (!sessionId || !navigator.onLine) return;
  await fetch(`${API_BASE}/api/family/session/${sessionId}/status`, {
    method:  'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      hospital_name:  hospitalName,
      ambulance_name: ambulanceName,
      severity,
    }),
  }).catch(() => {});
};
