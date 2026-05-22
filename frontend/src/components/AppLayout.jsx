import { NavLink, Outlet } from 'react-router-dom';
import useNetworkStatus from '../hooks/useNetworkStatus';

export default function AppLayout() {
  const isOnline = useNetworkStatus();

  return (
    <div className="app-shell">
      {/* ── HEADER ── */}
      <header className="dash-header">
        <div className="dash-header-inner">
          <NavLink to="/" className="dash-wordmark">RoadSOS</NavLink>
          <nav className="dash-nav-desktop">
            <NavLink to="/map" className="dash-nav-link">Live Map</NavLink>
            <NavLink to="/history" className="dash-nav-link">Incident History</NavLink>
            <NavLink to="/medical-profile" className="dash-nav-link">Medical ID</NavLink>
          </nav>
          <div className="dash-avatar">
            <span>AK</span>
          </div>
        </div>
      </header>

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
    </div>
  );
}
