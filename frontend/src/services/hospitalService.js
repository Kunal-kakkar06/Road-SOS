/**
 * Hospital Service — API calls + SSE live bed updates
 * Works both online (via backend API) and offline (cached fallback).
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Find nearest hospitals sorted by composite score.
 * @param {{ lat: number, lng: number, bloodType?: string, severity?: string }} params
 */
export const getNearestHospitals = async ({ lat, lng, bloodType, severity = 'P2' }) => {
  try {
    const params = new URLSearchParams({ lat, lng, severity });
    if (bloodType) params.append('blood_type', bloodType);

    const res = await fetch(`${API_BASE}/api/hospitals/nearest?${params}`, {
      method: 'POST',
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) throw new Error('Server error');
    const data = await res.json();

    // Cache for offline use
    try {
      localStorage.setItem('cached_hospitals', JSON.stringify(data));
      localStorage.setItem('cached_hospitals_ts', Date.now().toString());
    } catch (_) {}

    return data;
  } catch (e) {
    console.error('[Hospitals]', e);

    // Try offline cache (valid for 30 minutes)
    try {
      const cached = localStorage.getItem('cached_hospitals');
      const ts = parseInt(localStorage.getItem('cached_hospitals_ts') || '0');
      if (cached && Date.now() - ts < 30 * 60 * 1000) {
        return { ...JSON.parse(cached), fromCache: true };
      }
    } catch (_) {}

    return { hospitals: [], error: true };
  }
};

/**
 * Subscribe to live bed updates via Server-Sent Events.
 * @param {string} hospitalId
 * @param {function} onUpdate — callback receiving updated bed data
 * @returns {function} cleanup function to close the connection
 */
export const subscribeToLiveBeds = (hospitalId, onUpdate) => {
  try {
    const es = new EventSource(`${API_BASE}/api/hospitals/live/${hospitalId}`);

    es.onmessage = (e) => {
      try {
        onUpdate(JSON.parse(e.data));
      } catch (_) {}
    };

    es.onerror = () => {
      es.close();
    };

    return () => es.close();
  } catch (_) {
    return () => {}; // noop cleanup if SSE fails
  }
};

/**
 * Open Google Maps navigation to hospital.
 * @param {string} routeUrl
 */
export const openGoogleMapsRoute = (routeUrl) => {
  window.open(routeUrl, '_blank');
};

/**
 * List all hospitals (admin / map view).
 */
export const listAllHospitals = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/hospitals`);
    if (!res.ok) throw new Error('Server error');
    return await res.json();
  } catch (e) {
    console.error('[Hospitals] list error:', e);
    return [];
  }
};
