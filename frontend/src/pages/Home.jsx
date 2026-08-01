import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import MedicalIDCard from '../components/MedicalIDCard';
import TriageAssistant from '../components/TriageAssistant';
import SOSButton from '../components/SOSButton';
import VoiceGuidance from '../components/VoiceGuidance';
import useLocationCoords from '../hooks/useLocationCoords';

export default function Home() {
  const { isOnline } = useOutletContext();
  const [showTriage, setShowTriage] = useState(false);
  const [showVoiceGuidance, setShowVoiceGuidance] = useState(false);
  const [contacts, setContacts] = useState([]);
  const { coords } = useLocationCoords();
  const [locationName, setLocationName] = useState('Bengaluru, KA');

  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersGroupRef = useRef(null);

  // Dynamic Leaflet Map setup
  useEffect(() => {
    if (!coords || !window.L) return;

    if (!mapInstanceRef.current && mapRef.current) {
      const map = window.L.map(mapRef.current, {
        center: [coords.lat, coords.lng],
        zoom: 14,
        zoomControl: false,
        attributionControl: false
      });

      // Sleek Light Map Voyager tiles for premium Bento theme integration
      window.L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 20
      }).addTo(map);

      mapInstanceRef.current = map;
      markersGroupRef.current = window.L.layerGroup().addTo(map);
    }

    const map = mapInstanceRef.current;
    const group = markersGroupRef.current;

    if (map && group) {
      map.setView([coords.lat, coords.lng], 14);
      group.clearLayers();

      // Pulsing User blue location dot
      const userColor = '#006687';
      window.L.circle([coords.lat, coords.lng], {
        radius: 35,
        color: '#ffffff',
        weight: 3,
        fillColor: userColor,
        fillOpacity: 1
      }).addTo(group);

      window.L.circle([coords.lat, coords.lng], {
        radius: 200,
        color: userColor,
        weight: 1.5,
        fillColor: userColor,
        fillOpacity: 0.08,
        dashArray: '4, 4'
      }).addTo(group);

      // Generate dynamic local blackspots surrounding the user so they are always visible!
      const blackspots = [
        { lat: coords.lat + 0.0035, lng: coords.lng - 0.004, radius: 220, color: '#ba1a1a', label: 'CRITICAL: High-Risk Intersection' },
        { lat: coords.lat - 0.004, lng: coords.lng + 0.005, radius: 180, color: '#ba1a1a', label: 'CRITICAL: Sharp Turn Collision Zone' },
        { lat: coords.lat + 0.005, lng: coords.lng + 0.002, radius: 200, color: '#fca311', label: 'MODERATE: Heavy Traffic Merge Hazard' }
      ];

      blackspots.forEach(zone => {
        window.L.circle([zone.lat, zone.lng], {
          radius: zone.radius,
          color: zone.color,
          weight: 2,
          fillColor: zone.color,
          fillOpacity: 0.18
        }).bindPopup(`<b style="color: ${zone.color}; font-family: Space Grotesk">${zone.label}</b><br/>Proximity: approx. ${zone.radius}m`).addTo(group);
      });
    }
  }, [coords]);

  // Reverse-geocode coordinates to actual city names in real-time
  useEffect(() => {
    if (!isOnline) return;
    const fetchCity = async () => {
      try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${coords.lat}&lon=${coords.lng}&zoom=10`);
        if (res.ok) {
          const data = await res.json();
          const city = data.address.city || data.address.town || data.address.village || data.address.state || 'Unknown Location';
          const countryCode = data.address.country_code ? data.address.country_code.toUpperCase() : 'KA';
          setLocationName(`${city}, ${countryCode}`);
        }
      } catch (e) {
        setLocationName(`Lat: ${coords.lat.toFixed(4)}, Lng: ${coords.lng.toFixed(4)}`);
      }
    };
    fetchCity();
  }, [coords, isOnline]);

  useEffect(() => {
    try {
      const profile = JSON.parse(localStorage.getItem('medicalProfile') || '{}');
      let stored = [];
      if (profile.emergency_contacts && profile.emergency_contacts.length) {
        stored = profile.emergency_contacts;
      } else {
        stored = JSON.parse(localStorage.getItem('emergencyContacts') || '[]');
      }
      setContacts(stored);
    } catch (_) {}
  }, []);

  return (
    <div className="fade-in">

      {/* ── Offline Mode Banner ── */}
      {!isOnline && (
        <div className="offline-mode-banner">
          <div className="offline-mode-banner-icon">
            <span className="material-symbols-outlined icon-fill" style={{fontSize:28,color:'#fca311'}}>wifi_off</span>
          </div>
          <div>
            <p className="offline-mode-title">Offline Emergency Mode</p>
            <p className="offline-mode-subtitle">
              Network unavailable — SOS, Medical ID, and First Aid are still accessible
            </p>
          </div>
        </div>
      )}

      {/* ══════════════ TOP ROW ══════════════ */}
      <div className="dash-top-row">

        {/* SOS Hold Zone */}
        <SOSButton />

        {/* Right Panel */}
        <div className="dash-right-panel">
          {/* Status bar */}
          <div className="card-level-1 status-bar">
            <div className="pulse-dot"></div>
            <div className="status-bar-text">
              <p className="status-bar-title">
                {isOnline ? 'System Active' : 'Offline — Emergency Ready'}
              </p>
              <p className="status-bar-sub">
                {isOnline ? `Location: ${locationName} — GPS locked` : 'Using cached location data'}
              </p>
            </div>
            <span className="material-symbols-outlined" style={{fontSize:20,color:'#006687'}}>gps_fixed</span>
          </div>

          {/* Quick Actions */}
          <div className="card-level-1 quick-actions">
            <p className="quick-actions-label">Quick Actions</p>
            <div className="quick-actions-grid">
              <Link to="/triage" className="quick-action-item">
                <span className="material-symbols-outlined" style={{fontSize:28}}>psychology</span>
                <span className="quick-action-item-label">AI Triage</span>
              </Link>
              <Link to="/hospital" className="quick-action-item" style={{position:'relative'}}>
                <span className="material-symbols-outlined" style={{fontSize:28}}>local_hospital</span>
                <span className="quick-action-item-label">Find Hospital</span>
                {!isOnline && <span style={{position:'absolute',top:4,right:6,fontSize:8,background:'#fca311',color:'#14213D',padding:'2px 4px',borderRadius:4,fontWeight:800}}>CACHED</span>}
              </Link>
              <div className="quick-action-item" onClick={() => setShowVoiceGuidance(true)}>
                <span className="material-symbols-outlined" style={{fontSize:28}}>headphones</span>
                <span className="quick-action-item-label">Voice Aid</span>
              </div>
              <Link to="/ambulance" className="quick-action-item" style={{position:'relative'}}>
                <span className="material-symbols-outlined" style={{fontSize:28}}>ambulance</span>
                <span className="quick-action-item-label">Ambulance</span>
                {!isOnline && <span style={{position:'absolute',top:4,right:6,fontSize:8,background:'#ba1a1a',color:'#fff',padding:'2px 4px',borderRadius:4,fontWeight:800}}>SMS</span>}
              </Link>
              <Link to="/map" className="quick-action-item">
                <span className="material-symbols-outlined" style={{fontSize:28, color: '#27AE60'}}>shield_heart</span>
                <span className="quick-action-item-label">Safety Map</span>
              </Link>
              <Link to="/incident/demo-incident-uuid" className="quick-action-item">
                <span className="material-symbols-outlined" style={{fontSize:28}}>receipt_long</span>
                <span className="quick-action-item-label">Reports</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════ BENTO GRID ══════════════ */}
      <div className="bento-grid">

        {/* Blackspot Map — always visible */}
        <div className="card-level-1 span-2" style={{overflow:'hidden'}}>
          <div className="bento-card-header">
            <div className="bento-card-title">
              <span className="material-symbols-outlined" style={{color:'#14213D'}}>warning</span>
              <span className="bento-card-title-text">Blackspot Map</span>
            </div>
            <div style={{display:'flex',alignItems:'center',gap:8}}>
              <span style={{fontFamily:'Inter,sans-serif',fontSize:12,fontWeight:600,color:'#534433'}}>3 zones near you</span>
              <span className="bento-card-badge badge-danger">HIGH RISK</span>
            </div>
          </div>
          <div style={{ position: 'relative', height: '240px', background: '#e2e8f0' }}>
            <div ref={mapRef} style={{ width: '100%', height: '240px' }} />
            
            {/* Legend */}
            <div style={{
              position:'absolute', bottom: 12, left: 12, 
              background:'rgba(255,255,255,0.95)', borderRadius: 8, 
              padding:'8px 12px', display:'flex', gap:12, 
              boxShadow:'0 1px 4px rgba(0,0,0,0.15)', zIndex: 1000,
              pointerEvents: 'none'
            }}>
              <div style={{display:'flex',alignItems:'center',gap:8}}>
                <div style={{width:12,height:12,borderRadius:'50%',background:'#ba1a1a'}}></div>
                <span style={{fontFamily:'Inter,sans-serif',fontSize:12,fontWeight:600,color:'#221a11'}}>Blackspot</span>
              </div>
              <div style={{display:'flex',alignItems:'center',gap:8}}>
                <div style={{width:12,height:12,borderRadius:'50%',background:'#006687'}}></div>
                <span style={{fontFamily:'Inter,sans-serif',fontSize:12,fontWeight:600,color:'#221a11'}}>You</span>
              </div>
            </div>
          </div>
        </div>

        {/* Medical ID Card */}
        <MedicalIDCard />

        {/* Nearby Units — always visible */}
        <div className="card-level-1" style={{padding:16,display:'flex',flexDirection:'column',gap:12}}>
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <span className="material-symbols-outlined" style={{fontSize:20,color:'#006687'}}>ambulance</span>
            <span className="bento-card-title-text">Nearby Units</span>
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:8}}>
            <div className="nearby-unit-row">
              <div>
                <p className="nearby-unit-name">CATS Unit 4</p>
                <p className="nearby-unit-dist">1.2 km away</p>
              </div>
              <span className="nearby-unit-eta">4 min</span>
            </div>
            <div className="nearby-unit-divider"></div>
            <div className="nearby-unit-row">
              <div>
                <p className="nearby-unit-name">Apollo Reach</p>
                <p className="nearby-unit-dist">2.8 km away</p>
              </div>
              <span className="nearby-unit-eta">9 min</span>
            </div>
          </div>
          <Link to="/ambulance" className="link-tertiary">View all →</Link>
        </div>

        {/* Emergency Contacts Strip — always visible (offline-safe) */}
        <div className="card-level-1 span-2" style={{padding:16}}>
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:12}}>
            <span className="bento-card-title-text">Emergency Contacts</span>
            <Link to="/medical-profile" className="link-primary">Manage →</Link>
          </div>
          <div style={{display:'flex',flexWrap:'wrap',gap:8}}>
            {contacts.map((c, idx) => {
              const bgColors = ['#ffb95f', '#cdd9fe', '#ffccd5', '#e8f0fe', '#d8f3dc'];
              const textColors = ['#2a1700', '#0e1b37', '#5c0617', '#1a365d', '#1b4332'];
              const bg = bgColors[idx % bgColors.length];
              const tc = textColors[idx % textColors.length];
              return (
                <div key={idx} className="contact-pill">
                  <div className="contact-pill-avatar" style={{ background: bg, color: tc }}>
                    {c.name ? c.name[0].toUpperCase() : '?'}
                  </div>
                  <div>
                    <p className="contact-pill-name">{c.name || 'Anonymous'}</p>
                    <p className="contact-pill-phone">{c.phone || 'No phone'}</p>
                  </div>
                  <a href={`tel:${c.phone}`} style={{ background: 'none', border: 'none', cursor: 'pointer', marginLeft: 4, display: 'flex', alignItems: 'center' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#14213D' }}>call</span>
                  </a>
                </div>
              );
            })}
            {contacts.length === 0 && (
              <p style={{ fontSize: 13, color: '#534433', fontWeight: 600, margin: '4px 0' }}>
                No emergency contacts set up yet.
              </p>
            )}
            <Link to="/medical-profile" className="add-contact-btn" style={{ textDecoration: 'none' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#534433' }}>add</span>
              <span className="label" style={{ color: '#534433' }}>Add New</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Safety Tip — always visible */}
      <div className="card-level-1 safety-tip">
        <span className="material-symbols-outlined icon-fill" style={{fontSize:24,color:'#006687'}}>tips_and_updates</span>
        <div>
          <p className="safety-tip-title">Safety Tip</p>
          <p className="safety-tip-text">Move injured persons only if they're in immediate danger. Wait for trained help.</p>
        </div>
      </div>

      {/* AI Triage Modal */}
      {showTriage && <TriageAssistant 
        onClose={() => setShowTriage(false)} 
        onStartVoiceGuidance={() => {
          setShowTriage(false);
          setShowVoiceGuidance(true);
        }}
      />}
      {showVoiceGuidance && <VoiceGuidance onClose={() => setShowVoiceGuidance(false)} />}
    </div>
  );
}
