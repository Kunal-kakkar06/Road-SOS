const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const CRASH_THRESHOLD = 15;    // m/s² — peak G-force to trigger analysis
const JERK_THRESHOLD  = 30;    // m/s³
const WINDOW_MS       = 500;   // rolling analysis window
const COOLDOWN_MS     = 10000; // gap between detections

let isListening   = false;
let lastEventTime = 0;
let buffer        = [];
let preBuffer     = [];
let onDetect      = null;


export const startCrashMonitoring = (callback) => {
  if (isListening) return true;
  if (!window.DeviceMotionEvent) {
    console.warn('[Crash] DeviceMotion not available');
    return false;
  }
  onDetect = callback;
  window.addEventListener('devicemotion', onMotion, { passive: true });
  isListening = true;
  console.log('[Crash] Monitoring started');
  return true;
};


export const stopCrashMonitoring = () => {
  window.removeEventListener('devicemotion', onMotion);
  isListening = false;
  buffer = []; preBuffer = [];
};


function onMotion(e) {
  const a = e.accelerationIncludingGravity;
  if (!a) return;
  const now = Date.now();
  const mag = Math.sqrt((a.x||0)**2 + (a.y||0)**2 + (a.z||0)**2);
  const reading = {
    ts: now, mag,
    rot: {
      a: e.rotationRate?.alpha || 0,
      b: e.rotationRate?.beta  || 0,
      g: e.rotationRate?.gamma || 0,
    }
  };

  preBuffer.push(reading);
  if (preBuffer.length > 40) preBuffer.shift();

  buffer.push(reading);
  const cutoff = now - WINDOW_MS;
  buffer = buffer.filter(r => r.ts > cutoff);

  if (mag < CRASH_THRESHOLD) return;
  if (now - lastEventTime < COOLDOWN_MS) return;

  analyseWindow([...buffer], [...preBuffer]);
}


async function analyseWindow(win, pre) {
  if (win.length < 2) return;

  const mags            = win.map(r => r.mag);
  const peak_acceleration = Math.max(...mags);
  const dt              = (win[win.length-1].ts - win[0].ts) / 1000 || 0.001;
  const delta_v         = peak_acceleration * dt;

  const jerks = [];
  for (let i=1; i<win.length; i++) {
    const dti = (win[i].ts - win[i-1].ts) / 1000 || 0.001;
    jerks.push(Math.abs(win[i].mag - win[i-1].mag) / dti);
  }
  const jerk = Math.max(...jerks);

  if (jerk < JERK_THRESHOLD) return;  // false positive filter

  const rotMags = win.map(r => Math.sqrt(r.rot.a**2 + r.rot.b**2 + r.rot.g**2));
  const rotation_rate = Math.max(...rotMags);

  const preMags = pre.slice(-10).map(r => r.mag);
  const pre_event_accel = preMags.length
    ? preMags.reduce((a,b)=>a+b,0)/preMags.length : 3.0;

  const above = win.filter(r => r.mag > CRASH_THRESHOLD);
  const impact_duration_ms = above.length > 1
    ? above[above.length-1].ts - above[0].ts : 50;

  lastEventTime = Date.now();

  const coords = await getCoords();
  const payload = {
    eventId: crypto.randomUUID(),
    userId:  JSON.parse(localStorage.getItem('medicalProfile')||'{}').userId || 'anon',
    latitude: coords.lat, longitude: coords.lng,
    timestamp: new Date().toLocaleString('en-IN',{timeZone:'Asia/Kolkata'}),
    peak_acceleration, delta_v, jerk,
    rotation_rate, impact_duration_ms, pre_event_accel,
  };

  try {
    const res = await fetch(`${API_BASE}/api/crash/analyse`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload), signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.is_crash && onDetect) onDetect({...result, eventId:payload.eventId, coords});
    }
  } catch(_) {
    // Offline fallback — threshold-only detection
    if (peak_acceleration > 25 && onDetect) {
      onDetect({
        eventId: payload.eventId, coords,
        crash_probability: 0.75, is_crash: true,
        severity: 'P2', severity_label: 'Significant impact (offline estimate)',
      });
    }
  }
}


const getCoords = () => new Promise(resolve => {
  if (!navigator.geolocation) return resolve({lat:0,lng:0});
  navigator.geolocation.getCurrentPosition(
    p => resolve({lat:p.coords.latitude, lng:p.coords.longitude}),
    () => resolve({lat:0,lng:0}),
    {enableHighAccuracy:true, timeout:5000}
  );
});


export const isSensorAvailable = () => !!window.DeviceMotionEvent;

export const requestMotionPermission = async () => {
  if (typeof DeviceMotionEvent?.requestPermission === 'function') {
    try {
      const r = await DeviceMotionEvent.requestPermission();
      localStorage.setItem('motionPermission', r);
      return r === 'granted';
    } catch(_) { return false; }
  }
  return true;
};
