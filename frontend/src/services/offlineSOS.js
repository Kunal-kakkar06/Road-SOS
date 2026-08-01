// ── IndexedDB helpers ────────────────────────────────────────
import { sendFamilyAlert } from './familyAlertService';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DB_NAME   = 'roadsos-db';
const QUEUE_KEY = 'sos-queue';

const openDB = () =>
  new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => e.target.result.createObjectStore('kv');
    req.onsuccess       = (e) => resolve(e.target.result);
    req.onerror         = () => reject(req.error);
  });

const dbGet = async (key) => {
  const db = await openDB();
  return new Promise((res) => {
    const req = db.transaction('kv','readonly').objectStore('kv').get(key);
    req.onsuccess = () => res(req.result ?? []);
    req.onerror   = () => res([]);
  });
};

const dbSet = async (key, value) => {
  const db = await openDB();
  return new Promise((res, rej) => {
    const tx = db.transaction('kv','readwrite');
    tx.objectStore('kv').put(value, key);
    tx.oncomplete = res;
    tx.onerror    = () => rej(tx.error);
  });
};

// ── Register Service Worker ──────────────────────────────────
export const registerSW = async () => {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register('/sw.js');
    console.log('[SW] Registered:', reg.scope);

    // Listen for sync confirmation from SW
    navigator.serviceWorker.addEventListener('message', (e) => {
      if (e.data?.type === 'SOS_SYNCED') {
        window.dispatchEvent(
          new CustomEvent('sos-synced', { detail: { count: e.data.count } })
        );
      }
    });
  } catch (err) {
    console.error('[SW] Registration failed:', err);
  }
};

// ── Get GPS coordinates ──────────────────────────────────────
// Returns real device GPS, or a user-saved location override, or null (caller handles null).
export const getCoords = () =>
  new Promise((resolve) => {
    // Check for a user-saved location override first (e.g. set by a city selector)
    const savedLocation = (() => {
      try { return JSON.parse(localStorage.getItem('userLocationOverride') || 'null'); } catch { return null; }
    })();

    if (savedLocation) {
      resolve(savedLocation);
      return;
    }

    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null), // GPS denied
      { enableHighAccuracy: true, timeout: 8000 }
    );
  });

// ── Queue SOS in IndexedDB ───────────────────────────────────
export const queueSOSEvent = async (event) => {
  const queue = await dbGet(QUEUE_KEY);
  queue.push({ ...event, synced: false, queuedAt: Date.now() });
  await dbSet(QUEUE_KEY, queue);
};

// ── Request Background Sync from Service Worker ──────────────
const requestBgSync = async () => {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    if ('sync' in reg) await reg.sync.register('sos-sync');
  } catch (_) {}
};

// ── Mobile SMS fallback (opens native SMS app) ───────────────
export const openSMSFallback = (contacts, coords, profile) => {
  const mapsUrl = `https://maps.google.com/?q=${coords.lat},${coords.lng}`;
  const body = [
    '🚨 ROADSOS EMERGENCY',
    `${profile.name || 'Someone'} needs help!`,
    `Location: ${mapsUrl}`,
    `Blood type: ${profile.bloodType || 'Unknown'}`,
    `Allergies: ${profile.allergies?.join(', ') || 'None'}`,
  ].join('\n');

  const phones  = contacts.map((c) => c.phone).join(',');
  const encoded = encodeURIComponent(body);
  const isIOS   = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const sep     = isIOS ? '&' : '?';
  window.open(`sms:${phones}${sep}body=${encoded}`);
};

// ── MAIN FUNCTION — call this on SOS trigger ─────────────────
export const triggerSOS = async () => {
  const result = {
    eventId: crypto.randomUUID(),
    channels: { server: false, queued: false, smsFallback: false },
    error: null,
  };

  // 1. Get GPS (works offline — hardware)
  const coords = await getCoords();
  if (!coords) {
    result.error = 'GPS unavailable and no location override set. Enable location permission or set a city in Settings.';
    return { ...result, coords: null };
  }
  result.coords = coords;

  // 2. Load data from localStorage
  const profile  = JSON.parse(localStorage.getItem('medicalProfile')  || '{}');
  let contacts = JSON.parse(localStorage.getItem('emergencyContacts')|| '[]');
  if (!contacts.length && profile.emergency_contacts) {
    contacts = profile.emergency_contacts;
  }
  if (!contacts.length) {
    contacts = [
      { name: 'Sarah K (Emergency Wife)', phone: '+919876543210', relation: 'Wife' },
      { name: 'On-Duty Paramedic Coordinator', phone: '+918765432109', relation: 'Paramedic' }
    ];
    localStorage.setItem('emergencyContacts', JSON.stringify(contacts));
  }
  const timestamp = new Date().toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const event = {
    eventId: result.eventId,
    profile, contacts, coords, timestamp,
  };

  // 3. Always queue locally first (instant, no network needed)
  await queueSOSEvent(event);
  result.channels.queued = true;

  // 4. Try server if online
  if (navigator.onLine) {
    try {
      const res = await fetch(`${API_BASE}/api/sos/trigger`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(event),
        signal:  AbortSignal.timeout(6000),
      });

      if (res.ok) {
        result.channels.server = true;
        // Mark as synced in local queue
        const queue = await dbGet(QUEUE_KEY);
        await dbSet(
          QUEUE_KEY,
          queue.map((e) =>
            e.eventId === result.eventId ? { ...e, synced: true } : e
          )
        );
      }
    } catch (_) {
      // Server unreachable even though online — BG sync will handle it
    }
  }

  // ── Auto-create incident + timeline log after SOS fires ──
  if (navigator.onLine) {
    try {
      const incidentRes = await fetch(`${API_BASE}/api/incident/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id:        profile.userId || 'anonymous',
          sos_event_id:   result.eventId,
          latitude:       coords.lat,
          longitude:      coords.lng,
          severity:       'P2',
          medical_profile:profile,
          fir_state:      'Karnataka',
        }),
      });
      if (incidentRes.ok) {
        const incData = await incidentRes.json();
        const incident_id = incData.incident_id;
        localStorage.setItem('currentIncidentId', incident_id);
        
        // Log SOS event
        await fetch(`${API_BASE}/api/incident/${incident_id}/event`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_id,
            event_type:  'sos_triggered',
            description: 'SOS alert sent to emergency contacts',
            metadata:    { sos_event_id: result.eventId },
          }),
        });
      }
    } catch (err) {
      console.error('[SOS] Failed to auto-create incident:', err);
    }
  }

  // 5. If server failed or offline — register background sync
  if (!result.channels.server) {
    await requestBgSync();

    // 6. Open native SMS app on mobile as last resort
    if (contacts.length) {
      openSMSFallback(contacts, coords, profile);
      result.channels.smsFallback = true;
    }
  }

  // ── Auto-dispatch nearest ambulance + send family alert in parallel ──
  // Both run simultaneously so total wait = max(ambulance, family) not sum
  const [familyResult, ambulanceResult] = await Promise.allSettled([
    sendFamilyAlert(result.eventId, coords),
    navigator.onLine
      ? fetch(`${API_BASE}/api/ambulance/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            patient_lat:      coords.lat,
            patient_lng:      coords.lng,
            patient_user_id:  profile.userId || 'anonymous',
            sos_event_id:     result.eventId,
            severity:         'P2',
            blood_type:       profile.bloodType || null,
          }),
          signal: AbortSignal.timeout(8000),
        }).then(r => r.ok ? r.json() : null).catch(() => null)
      : Promise.resolve(null),
  ]);

  const dispatch = ambulanceResult.status === 'fulfilled' ? ambulanceResult.value : null;

  // Cache dispatch info locally so SOS dashboard can read it immediately
  if (dispatch) {
    localStorage.setItem('lastDispatch', JSON.stringify({
      dispatch_id:    dispatch.dispatch_id,
      provider_name:  dispatch.provider_name,
      vehicle_number: dispatch.vehicle_number,
      eta_minutes:    dispatch.eta_minutes,
      distance_km:    dispatch.distance_km,
    }));
  }

  return {
    ...result,
    coords,
    family:   familyResult.status === 'fulfilled' ? familyResult.value : null,
    dispatch,
  };
};

/**
 * Save a manual location override (e.g. from a city selector dropdown).
 * This is used as the GPS fallback when browser geolocation is unavailable.
 * @param {{ lat: number, lng: number, city?: string }} location
 */
export const setUserLocationOverride = (location) => {
  try {
    localStorage.setItem('userLocationOverride', JSON.stringify(location));
  } catch (_) {}
};

/**
 * Clear a previously saved location override (returns to GPS-only mode).
 */
export const clearUserLocationOverride = () => {
  localStorage.removeItem('userLocationOverride');
};
