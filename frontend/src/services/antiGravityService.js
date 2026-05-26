let isMonitoring = false;
let lastImpact = 0;
let stillnessTimer = null;
let accelerationHistory = [];
const HISTORY_SIZE = 50; // 5 seconds at 100ms interval (approx)

export const startMonitoring = (onFallDetected) => {
  if (isMonitoring || !window.DeviceMotionEvent) return;
  isMonitoring = true;
  
  window.addEventListener('devicemotion', handleMotion);
  
  // We need to pass the callback to the handler
  window._antiGravityCallback = onFallDetected;
};

export const stopMonitoring = () => {
  isMonitoring = false;
  window.removeEventListener('devicemotion', handleMotion);
  if (stillnessTimer) clearTimeout(stillnessTimer);
};

const handleMotion = (event) => {
  if (!isMonitoring) return;
  
  const accel = event.accelerationIncludingGravity;
  if (!accel || accel.x === null) return;
  
  // Calculate total acceleration magnitude (in Gs, assuming m/s^2 input / 9.8)
  const magnitude = Math.sqrt(accel.x*accel.x + accel.y*accel.y + accel.z*accel.z) / 9.81;
  
  accelerationHistory.push(magnitude);
  if (accelerationHistory.length > HISTORY_SIZE) {
    accelerationHistory.shift();
  }
  
  // Simple Fall Detection Logic Prototype
  
  // 1. Detect Impact
  if (magnitude > 3.5 && Date.now() - lastImpact > 10000) {
    // Possible fall! Wait 5 seconds to check for stillness
    lastImpact = Date.now();
    
    if (stillnessTimer) clearTimeout(stillnessTimer);
    
    stillnessTimer = setTimeout(() => {
      // After 5 seconds, check variance of recent history
      if (accelerationHistory.length > 20) {
        const recent = accelerationHistory.slice(-20);
        const mean = recent.reduce((a, b) => a + b) / recent.length;
        const variance = recent.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / recent.length;
        
        // If variance is low, the device is still (user might be unconscious)
        if (variance < 0.2 && window._antiGravityCallback) {
          window._antiGravityCallback(magnitude);
        }
      }
    }, 5000);
  }
};

export const reportFallToBackend = async (impactForce, userId = "user123") => {
  try {
    const res = await fetch('http://localhost:8000/api/anti-gravity/fall-detected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        accelerometer_data: { x: 0, y: 0, z: 0, timestamp: Date.now() },
        impact_force: impactForce,
        user_id: userId
      })
    });
    return await res.json();
  } catch (e) {
    console.error("Failed to report fall to backend", e);
    // Offline fallback: still trigger UI locally
    return {
      is_fall: true,
      confidence: 90,
      severity: "high",
      auto_sos_triggered: true,
      countdown_seconds: 20,
      alert_id: "local_" + Date.now()
    };
  }
};

export const cancelFallAlert = async (alertId, userId = "user123") => {
  try {
    const res = await fetch('http://localhost:8000/api/anti-gravity/cancel-alert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alert_id: alertId, user_id: userId })
    });
    return await res.json();
  } catch (e) {
    console.error("Failed to cancel alert on backend", e);
    return { cancelled: true };
  }
};
