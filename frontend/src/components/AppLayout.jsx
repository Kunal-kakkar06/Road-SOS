import { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import useNetworkStatus from '../hooks/useNetworkStatus';
import AntiGravity from './AntiGravity';
import {
  startCrashMonitoring, stopCrashMonitoring,
  requestMotionPermission, isSensorAvailable,
} from '../services/crashDetection';
import CrashAlert        from './CrashAlert';
import ManualCrashReport from './ManualCrashReport';

const CITIES = [
  { label: '📍 Browser GPS', value: 'gps', lat: null, lng: null },
  { label: '🇮🇳 Bengaluru', value: 'bengaluru', lat: 12.9716, lng: 77.5946 },
  { label: '🇬🇧 London', value: 'london', lat: 51.5074, lng: -0.1278 },
  { label: '🇺🇸 New York', value: 'newyork', lat: 40.7128, lng: -74.0060 },
  { label: '🇮🇳 Mysuru', value: 'mysuru', lat: 12.2958, lng: 76.6394 },
];

export default function AppLayout() {
  const isOnline = useNetworkStatus();
  const [showAntiGravity, setShowAntiGravity] = useState(false);
  const location = useLocation();
  const [initials, setInitials] = useState('AK');
  const [selectedCity, setSelectedCity] = useState('gps');

  // Crash detection states
  const [crash,      setCrash]      = useState(null);
  const [showManual, setShowManual] = useState(false);
  const [sensorOn,   setSensorOn]   = useState(false);

  useEffect(() => {
    try {
      const override = localStorage.getItem('userLocationOverride');
      if (override) {
        const parsed = JSON.parse(override);
        const matched = CITIES.find(c => c.lat === parsed.lat && c.lng === parsed.lng);
        if (matched) {
          setSelectedCity(matched.value);
          return;
        }
      }
    } catch (_) {}
    setSelectedCity('gps');
  }, []);

  const handleCityChange = (e) => {
    const val = e.target.value;
    setSelectedCity(val);
    if (val === 'gps') {
      localStorage.removeItem('userLocationOverride');
    } else {
      const city = CITIES.find(c => c.value === val);
      if (city) {
        localStorage.setItem('userLocationOverride', JSON.stringify({ lat: city.lat, lng: city.lng }));
      }
    }
    window.dispatchEvent(new Event('locationChanged'));
  };

  useEffect(() => {
    (async () => {
      const granted = await requestMotionPermission();
      if (granted) {
        const ok = startCrashMonitoring((c) => setCrash(c));
        setSensorOn(ok);
      }
    })();
    return () => stopCrashMonitoring();
  }, []);

  useEffect(() => {
    const updateInitials = () => {
      try {
        const cached = localStorage.getItem('medicalProfile');
        if (cached) {
          const profile = JSON.parse(cached);
          if (profile && profile.full_name) {
            const names = profile.full_name.trim().split(/\s+/);
            if (names.length > 1) {
              setInitials((names[0][0] + names[1][0]).toUpperCase());
            } else if (names[0]) {
              setInitials(names[0].substring(0, 2).toUpperCase());
            }
            return;
          }
        }
      } catch (_) {}
      setInitials('AK');
    };

    updateInitials();
    window.addEventListener('storage', updateInitials);
    // Trigger custom events inside the same tab if needed
    window.addEventListener('profileUpdated', updateInitials);
    
    return () => {
      window.removeEventListener('storage', updateInitials);
      window.removeEventListener('profileUpdated', updateInitials);
    };
  }, [location.pathname]);

  return (
    <div className="app-shell">
      {/* ── HEADER ── */}
      <header className="dash-header">
        <div className="dash-header-inner">
          <NavLink to="/" className="dash-wordmark">RoadSOS</NavLink>
          <nav className="dash-nav-desktop">
            <NavLink to="/map" className="dash-nav-link">Live Map</NavLink>
            <NavLink to="/history" className="dash-nav-link">History</NavLink>
            <NavLink to="/medical-profile" className="dash-nav-link">Medical ID</NavLink>
          </nav>
          
          {/* Location Selector Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 8, background: 'rgba(255,255,255,0.06)', padding: '5px 12px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#fca311' }}>location_on</span>
            <select 
              value={selectedCity} 
              onChange={handleCityChange}
              style={{
                background: 'none',
                border: 'none',
                color: '#fff',
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                outline: 'none',
                paddingRight: 4
              }}
            >
              {CITIES.map(c => (
                <option key={c.value} value={c.value} style={{ background: '#14213D', color: '#fff' }}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <button 
            className="anti-gravity-toggle"
            onClick={() => setShowAntiGravity(true)}
            style={{background:'none', border:'none', cursor:'pointer', display:'flex', alignItems:'center', gap:8}}
          >
            <span className="material-symbols-outlined" style={{fontSize:24, color:'#fca311'}}>paragliding</span>
            <span style={{fontFamily:'Space Grotesk,sans-serif', fontWeight:700, color:'#fff'}}>Anti-Gravity</span>
          </button>
          <div style={{
            fontSize:11,fontWeight:600,
            color: sensorOn ? '#27AE60' : '#ba1a1a',
            fontFamily:'Inter,sans-serif',
            marginRight: 12,
            background: sensorOn ? 'rgba(39,174,96,0.1)' : 'rgba(186,26,26,0.1)',
            padding: '4px 10px',
            borderRadius: 12,
            letterSpacing: '0.3px'
          }}>
            {sensorOn ? '● Crash Sensor Active' : '○ Manual Only'}
          </div>
          <div className="dash-avatar">
            <span>{initials}</span>
          </div>
        </div>
      </header>
      
      {showAntiGravity && <AntiGravity onClose={() => setShowAntiGravity(false)} />}

      {/* ── Offline Banner ── */}
      {!isOnline && (
        <div className="offline-banner">
          <span className="material-symbols-outlined" style={{fontSize:18}}>wifi_off</span>
          <span>You are offline — Emergency features are still available</span>
        </div>
      )}

      {/* ── PAGE CONTENT ── */}
      <main className="dash-main">
        <Outlet context={{ isOnline }} />
      </main>

      {/* ── BOTTOM NAV (mobile) ── */}
      <nav className="dash-bottom-nav">
        <NavLink to="/" end className={({isActive}) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
          <span className="material-symbols-outlined icon-fill" style={{fontSize:24}}>home</span>
          <span className="nav-label">Home</span>
        </NavLink>
        <NavLink to="/map" className={({isActive}) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
          <span className="material-symbols-outlined" style={{fontSize:24}}>map</span>
          <span className="nav-label">Map</span>
        </NavLink>
        <NavLink to="/" className="bottom-nav-sos-pill">
          <div className="sos-pill-circle">
            <span className="material-symbols-outlined icon-fill" style={{fontSize:28,color:'#663f00'}}>emergency</span>
          </div>
          <span className="sos-pill-label">SOS</span>
        </NavLink>
        <NavLink to="/history" className={({isActive}) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
          <span className="material-symbols-outlined" style={{fontSize:24}}>history</span>
          <span className="nav-label">History</span>
        </NavLink>
        <NavLink to="/medical-profile" className={({isActive}) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
          <span className="material-symbols-outlined" style={{fontSize:24}}>person</span>
          <span className="nav-label">Profile</span>
        </NavLink>
      </nav>

      {/* Manual report button — floating above mobile tabbar */}
      <button onClick={() => setShowManual(true)} style={{
        position:'fixed',bottom:80,right:20,zIndex:999,
        background:'#ba1a1a',color:'#fff',
        padding:'10px 16px',borderRadius:10,border:'none',
        fontSize:13,fontWeight:700,cursor:'pointer',
        fontFamily:'Space Grotesk,sans-serif',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        display: 'flex', alignItems: 'center', gap: 6
      }}>
        <span className="material-symbols-outlined" style={{fontSize:18}}>warning</span>
        Report Crash
      </button>

      {showManual && (
        <ManualCrashReport
          onResult={(r) => { setShowManual(false); if(r.isCrash) setCrash(r); }}
          onCancel={() => setShowManual(false)}
        />
      )}

      {crash && (
        <CrashAlert crash={crash} onDismiss={() => setCrash(null)} />
      )}
    </div>
  );
}
