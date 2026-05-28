/**
 * Ambulance Service — API calls + SSE live tracking
 * Works with the backend endpoints in backend/routers/ambulance.py.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Find nearest verified ambulances sorted by distance.
 */
export const findNearestAmbulances = async ({ lat, lng, type }) => {
  try {
    const params = new URLSearchParams({ lat, lng });
    if (type) params.append('type', type);

    const res = await fetch(`${API_BASE}/api/ambulance/nearest?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error('Server error');
    return await res.json();
  } catch (e) {
    console.error('[Ambulance nearest fetch failed]', e);
    return { providers: [], error: true };
  }
};

/**
 * Dispatch nearest ambulance — sends SMS to driver.
 */
export const dispatchAmbulance = async ({
  patientLat, patientLng, patientUserId, sosEventId, severity, bloodType
}) => {
  const res = await fetch(`${API_BASE}/api/ambulance/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      patient_lat: patientLat,
      patient_lng: patientLng,
      patient_user_id: patientUserId || 'anonymous',
      sos_event_id: sosEventId || null,
      severity: severity || 'P2',
      blood_type: bloodType || null,
    }),
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Dispatch failed');
  }
  return res.json();
};

/**
 * SSE — subscribe to live driver location updates.
 * @param {string} dispatchId
 * @param {function} onLocation — called with { dispatch_id, driver_lat, driver_lng, timestamp, status }
 * @param {function} onComplete — called when dispatch arrives/completes
 * @returns {function} cleanup function to close the connection
 */
export const trackAmbulance = (dispatchId, onLocation, onComplete) => {
  try {
    const es = new EventSource(`${API_BASE}/api/ambulance/track/${dispatchId}`);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.done) {
          if (onComplete) onComplete(data.status);
          es.close();
        } else {
          if (onLocation) onLocation(data);
          if (data.status === 'completed' || data.status === 'cancelled') {
            if (onComplete) onComplete(data.status);
            es.close();
          }
        }
      } catch (err) {
        console.error('Error parsing SSE message', err);
      }
    };

    es.onerror = (err) => {
      console.error('SSE connection error, closing EventSource', err);
      es.close();
    };

    return () => es.close();
  } catch (err) {
    console.error('Error starting SSE EventSource', err);
    return () => {};
  }
};

/**
 * Get dispatch details.
 */
export const getDispatch = async (dispatchId) => {
  try {
    const res = await fetch(`${API_BASE}/api/ambulance/dispatch/${dispatchId}`);
    return res.ok ? await res.json() : null;
  } catch (e) {
    console.error('[Ambulance dispatch query failed]', e);
    return null;
  }
};

/**
 * Update dispatch status (e.g. cancelled/completed)
 */
export const updateDispatchStatus = async (dispatchId, status) => {
  try {
    const res = await fetch(`${API_BASE}/api/ambulance/dispatch/${dispatchId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    return res.ok ? await res.json() : null;
  } catch (e) {
    console.error('[Ambulance status patch failed]', e);
    return null;
  }
};

