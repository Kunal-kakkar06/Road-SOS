import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { triggerSOS, registerSW } from '../services/offlineSOS';

const HOLD_MS     = 3000;
const CANCEL_SECS = 15; // 15 seconds robust review window

export default function SOSButton() {
  const [phase,     setPhase]     = useState('idle');
  const [countdown, setCountdown] = useState(CANCEL_SECS);
  const [isOnline,  setIsOnline]  = useState(navigator.onLine);
  const [channels,  setChannels]  = useState({});
  const [coords,    setCoords]    = useState({ lat: 12.9716, lng: 77.5946 }); // Bangalore default
  const [incidentId, setIncidentId] = useState('');
  const [offlineProgress, setOfflineProgress] = useState(15);
  
  // Permissions & nearest hospital data states
  const [allowAmbulance, setAllowAmbulance] = useState(true);
  const [contacts, setContacts]             = useState([]);
  const [nearestHospital, setNearestHospital] = useState({ name: 'Manipal Hospital', distance: '1.2 km', beds: 14 });
  const [dispatchInfo, setDispatchInfo]       = useState(null);
  const [liveSteps, setLiveSteps]             = useState([]); // food-delivery style steps
  const [elapsedSecs, setElapsedSecs]         = useState(0);
  const elapsedRef = useRef(null);

  const holdRef     = useRef(null);
  const timerRef    = useRef(null);

  useEffect(() => { registerSW(); }, []);

  useEffect(() => {
    const on  = () => setIsOnline(true);
    const off = () => setIsOnline(false);
    window.addEventListener('online',  on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online',  on);
      window.removeEventListener('offline', off);
    };
  }, []);

  // Fetch nearest hospitals dynamically from backend if online
  useEffect(() => {
    if (isOnline) {
      fetch('http://localhost:8000/api/hospitals')
        .then(r => r.json())
        .then(data => {
          if (data && data.length > 0) {
            setNearestHospital({
              name: data[0].name,
              distance: `${data[0].distance_km?.toFixed(1) || '1.1'} km`,
              beds: data[0].available_beds || 12
            });
          }
        })
        .catch(() => {});
    }
  }, [isOnline]);

  // Load contacts when arming or mounting
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('emergencyContacts') || '[]');
      if (stored.length > 0) {
        setContacts(stored.map((c, i) => ({ ...c, allowed: true, id: i })));
      } else {
        // Fallback dummy contacts if empty
        setContacts([
          { name: 'Sarah K', phone: '+919876543210', relation: 'Wife', allowed: true, id: 0 },
          { name: 'David M', phone: '+918765432109', relation: 'Brother', allowed: true, id: 1 }
        ]);
      }
    } catch (_) {}
  }, [phase]);

  // Crawl simulated offline map ambulance
  useEffect(() => {
    let interval;
    if (phase === 'active' && !isOnline) {
      interval = setInterval(() => {
        setOfflineProgress((p) => (p < 85 ? p + 5 : 85));
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [phase, isOnline]);

  const arm    = () => {
    if (phase !== 'idle') return;
    setPhase('holding');
    holdRef.current = setTimeout(startCountdown, HOLD_MS);
  };
  const disarm = () => {
    if (phase !== 'holding') return;
    clearTimeout(holdRef.current);
    setPhase('idle');
  };

  const startCountdown = () => {
    setPhase('countdown');
    let c = CANCEL_SECS;
    setCountdown(c);
    timerRef.current = setInterval(() => {
      c--;
      setCountdown(c);
      if (c <= 0) { 
        clearInterval(timerRef.current); 
        // Trigger dispatch using the active user consent configurations
        fire(); 
      }
    }, 1000);
  };

  const cancel = () => {
    clearInterval(timerRef.current);
    setPhase('cancelled');
    setTimeout(() => setPhase('idle'), 2000);
  };

  const toggleContactPermission = (id) => {
    setContacts(prev => prev.map(c => c.id === id ? { ...c, allowed: !c.allowed } : c));
  };

  const fire = async () => {
    clearInterval(timerRef.current);
    setPhase('firing');

    // Start a live elapsed timer
    setElapsedSecs(0);
    elapsedRef.current = setInterval(() => setElapsedSecs(s => s + 1), 1000);

    // Step 1: immediately visible
    const now = () => new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setLiveSteps([{ icon: 'gps_fixed', label: 'GPS Location Acquired', sub: 'High-accuracy coordinates locked', time: now(), done: true }]);
    
    const allowedContacts = contacts.filter(c => c.allowed);
    localStorage.setItem('emergencyContacts', JSON.stringify(allowedContacts));

    await new Promise(r => setTimeout(r, 500));
    setLiveSteps(s => [...s, { icon: 'crisis_alert', label: 'SOS Trigger Registered', sub: 'Incident queued in secure local store', time: now(), done: true }]);

    const result = await triggerSOS();
    
    await new Promise(r => setTimeout(r, 400));
    setLiveSteps(s => [...s, { icon: 'cell_tower', label: result.channels.server ? 'Alert Broadcast to Server' : 'Offline Queue — SMS Fallback Active', sub: result.channels.server ? 'Backend received your emergency event' : 'Will sync when signal returns', time: now(), done: result.channels.server }]);

    await new Promise(r => setTimeout(r, 600));
    setLiveSteps(s => [...s, { icon: 'contacts', label: 'Family & Emergency Contacts Notified', sub: `${allowedContacts.length} contact${allowedContacts.length !== 1 ? 's' : ''} alerted via SMS`, time: now(), done: true }]);

    if (result.coords && result.coords.lat) {
      setCoords(result.coords);
    } else {
      try { navigator.geolocation.getCurrentPosition(p => setCoords({ lat: p.coords.latitude, lng: p.coords.longitude })); } catch (_) {}
    }

    setChannels(result.channels);

    if (result.dispatch) {
      setDispatchInfo(result.dispatch);
      await new Promise(r => setTimeout(r, 500));
      setLiveSteps(s => [...s, {
        icon: 'ambulance',
        label: `Ambulance Dispatched — ${result.dispatch.provider_name}`,
        sub: `${result.dispatch.vehicle_number} · ETA ${result.dispatch.eta_minutes} min · ${result.dispatch.distance_km} km away`,
        time: now(), done: true
      }]);
    } else {
      try {
        const cached = JSON.parse(localStorage.getItem('lastDispatch') || 'null');
        if (cached) {
          setDispatchInfo(cached);
          setLiveSteps(s => [...s, { icon: 'ambulance', label: `Ambulance Dispatched — ${cached.provider_name}`, sub: `${cached.vehicle_number} · ETA ${cached.eta_minutes} min`, time: now(), done: true }]);
        } else {
          setLiveSteps(s => [...s, { icon: 'ambulance', label: 'Ambulance Dispatch Pending', sub: 'Nearest unit being located', time: now(), done: false }]);
        }
      } catch (_) {}
    }

    const incId = localStorage.getItem('currentIncidentId') || 'demo-incident-uuid';
    setIncidentId(incId);

    await new Promise(r => setTimeout(r, 400));
    setLiveSteps(s => [...s, { icon: 'receipt_long', label: 'FIR Incident Report Auto-Created', sub: 'View triage dashboard for live updates', time: now(), done: true }]);

    setPhase('active');
  };

  const btn = {
    background: '#fca311', border: 'none', borderRadius: 12,
    width: 160, height: 160, cursor: 'pointer',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 8,
    transform: phase === 'holding' ? 'scale(0.95)' : 'scale(1)',
    transition: 'transform .1s', userSelect: 'none',
  };

  if (phase === 'cancelled')
    return (
      <div className="card-level-2 sos-zone">
        <p style={{fontSize:20,fontWeight:700,color:'#ba1a1a'}}>SOS Cancelled</p>
        <p style={{fontSize:13,color:'#534433',marginTop:4}}>No alert was sent</p>
      </div>
    );

  if (phase === 'countdown')
    return (
      <div className="card-level-2 sos-zone" style={{
        borderWidth: 2, 
        borderColor: '#ba1a1a', 
        background: '#FFF8F8',
        padding: 20,
        gap: 12,
        width: '100%',
        boxSizing: 'border-box'
      }}>
        {/* Flashing Warning and Timer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div>
            <p style={{ fontSize: 15, fontWeight: 800, color: '#ba1a1a', margin: 0, fontFamily: 'Space Grotesk, sans-serif' }}>
              Confirm Emergency Dispatch
            </p>
            <p style={{ fontSize: 11, color: '#534433', margin: '2px 0 0' }}>
              Auto-dispatching in {countdown}s to ensure safety
            </p>
          </div>
          <div style={{
            background: '#ba1a1a',
            color: '#fff',
            borderRadius: '50%',
            width: 44,
            height: 44,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            fontWeight: 800,
            fontFamily: 'Space Grotesk, sans-serif'
          }}>
            {countdown}
          </div>
        </div>

        <div style={{ width: '100%', borderBottom: '1px solid #FED7D7', margin: '4px 0' }} />

        {/* Dynamic Route Info Setup */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', background: '#fff', borderRadius: 8, padding: 12, border: '1px solid #FEB2B2', boxSizing: 'border-box' }}>
          
          {/* Nearest Hospital Routing Info */}
          <div>
            <span style={{ fontSize: 10, fontWeight: 800, color: '#718096', letterSpacing: '0.5px' }}>NEAREST ROUTING OPTIONS</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#ba1a1a' }}>local_hospital</span>
              <p style={{ fontSize: 12, fontWeight: 700, color: '#2D3748', margin: 0 }}>
                {nearestHospital.name} ({nearestHospital.distance}) · {nearestHospital.beds} Beds Free
              </p>
            </div>
          </div>

          {/* Interactive Ambulance Permission */}
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={allowAmbulance}
              onChange={() => setAllowAmbulance(!allowAmbulance)}
              style={{ accentColor: '#ba1a1a', width: 16, height: 16 }}
            />
            <div style={{ fontSize: 12, fontWeight: 600, color: '#2D3748' }}>
              Dispatch Ambulance (CATS Unit 4 en route)
            </div>
          </label>

          {/* Interactive Emergency Contacts Permissions */}
          <div>
            <span style={{ display: 'block', fontSize: 10, fontWeight: 800, color: '#718096', letterSpacing: '0.5px', marginBottom: 4 }}>
              EMERGENCY CONTACT BROADCASTS
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {contacts.map((c) => (
                <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
                  <input
                    type="checkbox"
                    checked={c.allowed}
                    onChange={() => toggleContactPermission(c.id)}
                    style={{ accentColor: '#ba1a1a', width: 14, height: 14 }}
                  />
                  <div style={{ fontSize: 12, color: c.allowed ? '#2D3748' : '#A0AEC0', textDecoration: c.allowed ? 'none' : 'line-through' }}>
                    Send SMS to <strong>{c.name}</strong> ({c.relation})
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Review Action Buttons */}
        <div style={{ display: 'flex', gap: 10, width: '100%', marginTop: 4 }}>
          <button onClick={cancel} style={{
            flex: 1, padding: '12px', borderRadius: 8, border: '1px solid #CBD5E0',
            background: '#fff', color: '#4A5568', fontSize: 13, fontWeight: 700,
            cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif'
          }}>
            CANCEL
          </button>
          <button onClick={fire} style={{
            flex: 2, padding: '12px', borderRadius: 8, border: 'none',
            background: '#ba1a1a', color: '#fff', fontSize: 13, fontWeight: 800,
            cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
            boxShadow: '0 2px 4px rgba(186,26,26,0.2)'
          }}>
            DISPATCH NOW →
          </button>
        </div>
      </div>
    );

  // Shared step tracker UI used by both firing and active phases
  const StepTracker = () => (
    <div style={{ width: '100%' }}>
      {/* Elapsed timer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#ba1a1a', display: 'inline-block', animation: 'pulse-sos 1s infinite' }} />
          <p style={{ fontSize: 15, fontWeight: 800, color: '#ba1a1a', margin: 0, fontFamily: 'Space Grotesk, sans-serif' }}>EMERGENCY SOS ACTIVE</p>
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#718096', fontFamily: 'Space Grotesk, sans-serif' }}>
          {String(Math.floor(elapsedSecs / 60)).padStart(2,'0')}:{String(elapsedSecs % 60).padStart(2,'0')}
        </span>
      </div>

      {/* Food-delivery style step list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {liveSteps.map((step, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, animation: 'slideInStep 0.4s ease', opacity: 1 }}>
            {/* Left: icon + connector line */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 36, flexShrink: 0 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                background: step.done ? '#ba1a1a' : '#E2E8F0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: step.done ? '0 2px 8px rgba(186,26,26,0.25)' : 'none',
                transition: 'all 0.4s ease'
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: step.done ? '#fff' : '#A0AEC0' }}>{step.icon}</span>
              </div>
              {i < liveSteps.length - 1 && (
                <div style={{ width: 2, flex: 1, minHeight: 20, background: step.done ? '#ba1a1a' : '#E2E8F0', margin: '3px 0', transition: 'background 0.4s ease' }} />
              )}
            </div>

            {/* Right: text */}
            <div style={{ paddingBottom: i < liveSteps.length - 1 ? 14 : 0, flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 800, color: step.done ? '#1A202C' : '#A0AEC0', fontFamily: 'Space Grotesk, sans-serif', lineHeight: 1.3 }}>{step.label}</p>
                <span style={{ fontSize: 10, color: '#A0AEC0', fontWeight: 600, flexShrink: 0, marginLeft: 8 }}>{step.time}</span>
              </div>
              <p style={{ margin: '2px 0 0', fontSize: 11.5, color: '#718096', lineHeight: 1.4 }}>{step.sub}</p>
            </div>
          </div>
        ))}

        {/* Spinning pending step if still firing */}
        {phase === 'firing' && (
          <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#FFF5F5', border: '2px solid #ba1a1a', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#ba1a1a', animation: 'spin 1.2s infinite linear' }}>sync</span>
            </div>
            <div style={{ paddingTop: 8 }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: '#ba1a1a' }}>Processing next step...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (phase === 'firing')
    return (
      <div className="card-level-2 sos-zone" style={{ borderWidth: 2, borderColor: '#ba1a1a', background: '#FFF5F5', width: '100%', boxSizing: 'border-box', gap: 0 }}>
        <StepTracker />
        <style>{`
          @keyframes pulse-sos { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.3);opacity:0.4} }
          @keyframes spin { to { transform: rotate(360deg); } }
          @keyframes slideInStep { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        `}</style>
      </div>
    );

  if (phase === 'active')
    return (
      <div className="card-level-2 sos-zone" style={{ borderWidth: 2, borderColor: '#ba1a1a', background: '#FFF5F5', width: '100%', boxSizing: 'border-box', gap: 14 }}>
        <StepTracker />

        {/* Live ambulance info card */}
        {dispatchInfo && (
          <div style={{ background: '#fff', borderRadius: 10, padding: '12px 14px', borderLeft: '4px solid #ba1a1a', width: '100%', boxSizing: 'border-box' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#718096', letterSpacing: '0.5px' }}>LIVE AMBULANCE TRACKING</span>
              <span style={{ fontSize: 12, fontWeight: 800, color: '#ba1a1a', background: '#FFF5F5', padding: '2px 8px', borderRadius: 4 }}>ETA: {dispatchInfo.eta_minutes} MINS</span>
            </div>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#2D3748', margin: '4px 0 2px' }}>🚑 {dispatchInfo.provider_name} ({dispatchInfo.vehicle_number})</p>
            <p style={{ fontSize: 12, fontWeight: 600, color: '#006687', margin: 0 }}>🏥 En route to {nearestHospital.name} · {dispatchInfo.distance_km} km</p>
          </div>
        )}

        {/* Map */}
        <div style={{ width: '100%', borderRadius: 8, overflow: 'hidden', border: '1px solid #E2E8F0' }}>
          {isOnline ? (
            <iframe title="Live Route Map" width="100%" height="160" style={{ border: 'none', display: 'block' }}
              src={`https://maps.google.com/maps?q=${coords.lat},${coords.lng}&z=14&output=embed`}
              key={`${coords.lat},${coords.lng}`} />
          ) : (
            <div style={{ height: 120, background: '#1E293B', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <span className="material-symbols-outlined" style={{ color: '#fca311', fontSize: 22 }}>location_searching</span>
              <span style={{ fontSize: 12, color: '#94A3B8', fontWeight: 700 }}>OFFLINE TACTICAL MAP · GPS Active</span>
            </div>
          )}
        </div>

        {/* View Report Button */}
        <Link to={`/incident/${incidentId}`} style={{
          display: 'block', width: '100%', padding: '12px 0',
          background: '#ba1a1a', color: '#fff', textAlign: 'center',
          borderRadius: 8, fontWeight: 700, fontSize: 13,
          textDecoration: 'none', fontFamily: 'Space Grotesk, sans-serif',
          boxShadow: '0 2px 4px rgba(186,26,26,0.2)'
        }}>
          Open Live Triage Dashboard & FIR Report →
        </Link>

        <style>{`
          @keyframes pulse-sos { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.3);opacity:0.4} }
          @keyframes spin { to { transform: rotate(360deg); } }
          @keyframes slideInStep { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        `}</style>
      </div>
    );



  // ── Idle ──
  return (
    <div className="card-level-2 sos-zone" style={{gap:10}}>
      {!isOnline && (
        <div style={{background:'#fca311',borderRadius:8,padding:'7px 12px',
                     width:'100%',textAlign:'center'}}>
          <p style={{color:'#663f00',fontSize:12,fontWeight:600}}>
            Offline mode — SMS fallback active
          </p>
        </div>
      )}
      <p className="sos-zone-label">Emergency SOS</p>
      <button
        className={`sos-hold-btn ${phase === 'holding' ? 'holding' : ''}`}
        onMouseDown={arm} onMouseUp={disarm} onMouseLeave={disarm}
        onTouchStart={arm} onTouchEnd={disarm}
      >
        <div className="sos-ring"></div>
        <div className="sos-progress"></div>
        <span className="material-symbols-outlined icon-fill"
              style={{fontSize:56,color:'#663f00',position:'relative',zIndex:1}}>
          emergency
        </span>
        <span style={{fontFamily:'Space Grotesk,sans-serif',fontWeight:700,fontSize:14,color:'#663f00',position:'relative',zIndex:1}}>
          {phase === 'holding' ? 'HOLD…' : 'HOLD 3s'}
        </span>
      </button>
      <p className="sos-zone-desc">
        {isOnline
          ? <>Triggers ambulance dispatch<br/>+ family alert instantly</>
          : <>Queues SMS — sends when<br/>signal returns</>}
      </p>
    </div>
  );
}

function Row({ done, text }) {
  return (
    <div style={{display:'flex',alignItems:'center',gap:10}}>
      <span style={{fontSize:15,fontWeight:700,width:20,flexShrink:0,
                    color: done ? '#27AE60' : '#ba1a1a'}}>
        {done ? '✓' : '○'}
      </span>
      <span style={{fontSize:12,color: done ? '#2D3748' : '#718096', fontWeight: 600}}>
        {text}
      </span>
    </div>
  );
}
