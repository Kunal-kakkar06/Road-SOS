import { useState, useEffect } from 'react';
import { startMonitoring, stopMonitoring, cancelFallAlert, reportFallToBackend } from '../services/antiGravityService';

export default function AntiGravity({ onClose }) {
  const [isEnabled, setIsEnabled] = useState(false);
  const [status, setStatus] = useState('Idle'); // Idle, Monitoring, FallDetected
  const [countdown, setCountdown] = useState(null);
  const [activeAlertId, setActiveAlertId] = useState(null);
  const [logs, setLogs] = useState([]);
  
  const [settings, setSettings] = useState({
    sensitivity: 'medium',
    countdownDuration: 30
  });

  useEffect(() => {
    if (isEnabled) {
      setStatus('Monitoring');
      startMonitoring(handleFallDetected);
    } else {
      setStatus('Idle');
      stopMonitoring();
    }
    
    return () => stopMonitoring();
  }, [isEnabled]);

  const handleFallDetected = async (impactForce) => {
    setStatus('FallDetected');
    
    // Play audio alert (mocked here, should be actual audio)
    const utterance = new SpeechSynthesisUtterance(`Fall detected. Emergency services will be contacted in ${settings.countdownDuration} seconds. Tap screen to cancel.`);
    window.speechSynthesis.speak(utterance);
    
    setCountdown(settings.countdownDuration);
    
    // Call backend
    const res = await reportFallToBackend(impactForce);
    setActiveAlertId(res.alert_id);
    
    // Start countdown
    let count = settings.countdownDuration;
    const timer = setInterval(() => {
      count--;
      setCountdown(count);
      if (count <= 0) {
        clearInterval(timer);
        triggerAutoSOS();
      }
    }, 1000);
    
    // Store timer so we can clear it on cancel
    window._fallTimer = timer;
  };

  const cancelAlert = async () => {
    if (window._fallTimer) clearInterval(window._fallTimer);
    window.speechSynthesis.cancel();
    
    setStatus('Monitoring');
    setCountdown(null);
    
    if (activeAlertId) {
      await cancelFallAlert(activeAlertId);
      setActiveAlertId(null);
    }
    
    setLogs(prev => [{ time: new Date().toLocaleTimeString(), msg: 'Fall alert cancelled by user' }, ...prev]);
  };

  const triggerAutoSOS = () => {
    setStatus('AutoSOS');
    alert('AUTO SOS TRIGGERED: Dispatching emergency services to your location.');
    setLogs(prev => [{ time: new Date().toLocaleTimeString(), msg: 'Auto-SOS dispatched' }, ...prev]);
  };

  const simulateFall = () => {
    if (!isEnabled) {
      alert("Please enable Anti-Gravity first");
      return;
    }
    handleFallDetected(6.5); // Simulate 6.5G impact
  };

  const overlay = {
    position: 'fixed', inset: 0, zIndex: 10001, background: 'rgba(186, 26, 26, 0.95)',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    padding: 24, color: '#fff', textAlign: 'center'
  };

  const card = {
    background: '#fff', borderRadius: 16, padding: 24, margin: 20,
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontFamily: 'Space Grotesk, sans-serif'
  };

  return (
    <div style={{position: 'fixed', inset: 0, zIndex: 10000, background: '#f8f9fa', overflowY: 'auto'}}>
      <div style={{background: '#14213D', color: '#fff', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontWeight: 700, fontSize: 18}}>
        <span>🪂 Anti-Gravity (Fall Detection)</span>
        <span className="material-symbols-outlined" style={{cursor:'pointer'}} onClick={onClose}>close</span>
      </div>

      {status === 'FallDetected' && (
        <div style={overlay}>
          <span className="material-symbols-outlined" style={{fontSize: 80, marginBottom: 20}}>warning</span>
          <p style={{fontSize: 32, fontWeight: 700, marginBottom: 8}}>FALL DETECTED</p>
          <p style={{fontSize: 18, opacity: 0.9, marginBottom: 40}}>Emergency services will be contacted in:</p>
          
          <div style={{fontSize: 96, fontWeight: 700, lineHeight: 1, marginBottom: 40}}>
            {countdown}s
          </div>
          
          <button 
            onClick={cancelAlert}
            style={{
              padding: 24, width: '100%', borderRadius: 12, border: 'none',
              background: '#fff', color: '#ba1a1a', fontSize: 20, fontWeight: 700, cursor: 'pointer'
            }}
          >
            I'M OK - CANCEL ALERT
          </button>
        </div>
      )}

      <div style={card}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20}}>
          <div>
            <p style={{fontSize: 18, fontWeight: 700, color: '#14213D'}}>Enable Protection</p>
            <p style={{fontSize: 13, color: '#534433', marginTop: 4}}>Uses motion sensors to detect crashes/falls</p>
          </div>
          {/* Simple toggle switch UI */}
          <div 
            onClick={() => {
              if (!isEnabled && typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
                // iOS 13+ requires user permission
                DeviceMotionEvent.requestPermission()
                  .then(response => {
                    if (response === 'granted') setIsEnabled(true);
                  })
                  .catch(console.error);
              } else {
                setIsEnabled(!isEnabled);
              }
            }}
            style={{
              width: 50, height: 28, borderRadius: 14, background: isEnabled ? '#27AE60' : '#ddd',
              position: 'relative', cursor: 'pointer', transition: '0.2s'
            }}
          >
            <div style={{
              width: 24, height: 24, borderRadius: '50%', background: '#fff',
              position: 'absolute', top: 2, left: isEnabled ? 24 : 2, transition: '0.2s'
            }} />
          </div>
        </div>

        <div style={{display:'flex', alignItems:'center', gap:10, padding: 12, background: isEnabled ? 'rgba(39, 174, 96, 0.1)' : '#f0f0f0', borderRadius: 8}}>
          <div style={{
            width: 12, height: 12, borderRadius: '50%', background: isEnabled ? '#27AE60' : '#888',
            animation: isEnabled ? 'pulse 2s infinite' : 'none'
          }} />
          <span style={{fontWeight: 700, fontSize: 14, color: isEnabled ? '#27AE60' : '#888'}}>
            Status: {status}
          </span>
        </div>
      </div>

      <div style={card}>
        <p style={{fontSize: 16, fontWeight: 700, color: '#14213D', marginBottom: 16}}>Settings</p>
        
        <div style={{marginBottom: 20}}>
          <p style={{fontSize: 14, fontWeight: 700, marginBottom: 8}}>Sensitivity</p>
          <select 
            value={settings.sensitivity} 
            onChange={e => setSettings({...settings, sensitivity: e.target.value})}
            style={{width: '100%', padding: 12, borderRadius: 8, border: '1px solid #ddd', fontSize: 14}}
          >
            <option value="high">High (Detects minor impacts)</option>
            <option value="medium">Medium (Recommended)</option>
            <option value="low">Low (Only severe impacts)</option>
          </select>
        </div>

        <div>
          <p style={{fontSize: 14, fontWeight: 700, marginBottom: 8}}>Auto-SOS Countdown</p>
          <select 
            value={settings.countdownDuration} 
            onChange={e => setSettings({...settings, countdownDuration: parseInt(e.target.value)})}
            style={{width: '100%', padding: 12, borderRadius: 8, border: '1px solid #ddd', fontSize: 14}}
          >
            <option value={10}>10 Seconds (Fastest)</option>
            <option value={20}>20 Seconds</option>
            <option value={30}>30 Seconds (Recommended)</option>
            <option value={60}>60 Seconds</option>
          </select>
        </div>
      </div>

      <div style={card}>
        <p style={{fontSize: 16, fontWeight: 700, color: '#14213D', marginBottom: 16}}>Testing</p>
        <button 
          onClick={simulateFall}
          style={{
            width: '100%', padding: 16, borderRadius: 8, border: '2px dashed #ba1a1a',
            background: 'transparent', color: '#ba1a1a', fontSize: 14, fontWeight: 700, cursor: 'pointer'
          }}
        >
          Simulate Crash / Fall
        </button>
      </div>

      <div style={card}>
        <p style={{fontSize: 16, fontWeight: 700, color: '#14213D', marginBottom: 16}}>Activity Log</p>
        {logs.length === 0 ? (
          <p style={{fontSize: 13, color: '#888'}}>No recent activity</p>
        ) : (
          logs.map((log, i) => (
            <div key={i} style={{padding: '8px 0', borderBottom: '1px solid #eee', fontSize: 13}}>
              <span style={{color: '#888', marginRight: 8}}>{log.time}</span>
              <span style={{color: '#14213D'}}>{log.msg}</span>
            </div>
          ))
        )}
      </div>

    </div>
  );
}
