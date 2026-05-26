import { useState, useRef, useCallback } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import MedicalIDCard from '../components/MedicalIDCard';
import TriageAssistant from '../components/TriageAssistant';
import SOSButton from '../components/SOSButton';
import VoiceGuidance from '../components/VoiceGuidance';

export default function Home() {
  const { isOnline } = useOutletContext();
  const [showTriage, setShowTriage] = useState(false);
  const [showVoiceGuidance, setShowVoiceGuidance] = useState(false);

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
                {isOnline ? 'Location: Bengaluru, KA — GPS locked' : 'Using cached location data'}
              </p>
            </div>
            <span className="material-symbols-outlined" style={{fontSize:20,color:'#006687'}}>gps_fixed</span>
          </div>

          {/* Quick Actions */}
          <div className="card-level-1 quick-actions">
            <p className="quick-actions-label">Quick Actions</p>
            <div className="quick-actions-grid">
              <div className="quick-action-item" onClick={() => setShowTriage(true)}>
                <span className="material-symbols-outlined" style={{fontSize:28}}>psychology</span>
                <span className="quick-action-item-label">AI Triage</span>
              </div>
              {isOnline ? (
                <Link to="/hospital" className="quick-action-item">
                  <span className="material-symbols-outlined" style={{fontSize:28}}>local_hospital</span>
                  <span className="quick-action-item-label">Find Hospital</span>
                </Link>
              ) : (
                <div className="quick-action-item" style={{opacity:0.4,cursor:'not-allowed'}}>
                  <span className="material-symbols-outlined" style={{fontSize:28}}>local_hospital</span>
                  <span className="quick-action-item-label">Find Hospital</span>
                </div>
              )}
              <div className="quick-action-item" onClick={() => setShowVoiceGuidance(true)}>
                <span className="material-symbols-outlined" style={{fontSize:28}}>headphones</span>
                <span className="quick-action-item-label">Voice Aid</span>
              </div>
              {isOnline ? (
                <Link to="/ambulance" className="quick-action-item">
                  <span className="material-symbols-outlined" style={{fontSize:28}}>ambulance</span>
                  <span className="quick-action-item-label">Ambulance</span>
                </Link>
              ) : (
                <div className="quick-action-item" style={{opacity:0.4,cursor:'not-allowed'}}>
                  <span className="material-symbols-outlined" style={{fontSize:28}}>ambulance</span>
                  <span className="quick-action-item-label">Ambulance</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════ BENTO GRID ══════════════ */}
      <div className="bento-grid">

        {/* Blackspot Map — only show online */}
        {isOnline && (
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
            <div className="map-placeholder">
              <div className="map-road h" style={{top:'40%'}}></div>
              <div className="map-road h" style={{top:'65%'}}></div>
              <div className="map-road v" style={{left:'30%'}}></div>
              <div className="map-road v" style={{left:'70%'}}></div>
              {/* Blackspot overlays */}
              <div style={{position:'absolute',borderRadius:'50%',background:'rgba(186,26,26,0.2)',border:'2px solid #ba1a1a',width:60,height:60,top:'25%',left:'25%',transform:'translate(-50%,-50%)'}}></div>
              <div style={{position:'absolute',borderRadius:'50%',background:'rgba(186,26,26,0.15)',border:'1px solid rgba(186,26,26,0.5)',width:48,height:48,top:'55%',left:'65%',transform:'translate(-50%,-50%)'}}></div>
              <div style={{position:'absolute',borderRadius:'50%',background:'rgba(252,163,17,0.3)',border:'1px solid rgba(20,33,61,0.4)',width:40,height:40,top:'70%',left:'40%',transform:'translate(-50%,-50%)'}}></div>
              {/* User dot */}
              <div style={{position:'absolute',top:'50%',left:'50%',transform:'translate(-50%,-50%)'}}>
                <div style={{width:16,height:16,background:'#006687',borderRadius:'50%',border:'2px solid #fff',boxShadow:'0 1px 3px rgba(0,0,0,0.2)',position:'relative'}}>
                  <div style={{position:'absolute',inset:-6,borderRadius:'50%',border:'2px solid rgba(0,102,135,0.4)',animation:'ping 1s cubic-bezier(0,0,0.2,1) infinite'}}></div>
                </div>
              </div>
              {/* Legend */}
              <div style={{position:'absolute',bottom:12,left:12,background:'rgba(255,248,244,0.9)',borderRadius:8,padding:'8px 12px',display:'flex',gap:12}}>
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
        )}

        {/* Medical ID Card */}
        <MedicalIDCard />

        {/* Nearby Units — only show online */}
        {isOnline && (
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
        )}

        {/* Emergency Contacts Strip — always visible (offline-safe) */}
        <div className="card-level-1 span-2" style={{padding:16}}>
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:12}}>
            <span className="bento-card-title-text">Emergency Contacts</span>
            <Link to="/medical-profile" className="link-primary">Manage →</Link>
          </div>
          <div style={{display:'flex',flexWrap:'wrap',gap:8}}>
            <div className="contact-pill">
              <div className="contact-pill-avatar" style={{background:'#ffb95f',color:'#2a1700'}}>S</div>
              <div>
                <p className="contact-pill-name">Sarah K</p>
                <p className="contact-pill-phone">+91 98765 43210</p>
              </div>
              <button style={{background:'none',border:'none',cursor:'pointer',marginLeft:4}}>
                <span className="material-symbols-outlined" style={{fontSize:20,color:'#14213D'}}>call</span>
              </button>
            </div>
            <div className="contact-pill">
              <div className="contact-pill-avatar" style={{background:'#cdd9fe',color:'#0e1b37'}}>D</div>
              <div>
                <p className="contact-pill-name">David M</p>
                <p className="contact-pill-phone">+91 87654 32109</p>
              </div>
              <button style={{background:'none',border:'none',cursor:'pointer',marginLeft:4}}>
                <span className="material-symbols-outlined" style={{fontSize:20,color:'#14213D'}}>call</span>
              </button>
            </div>
            <button className="add-contact-btn">
              <span className="material-symbols-outlined" style={{fontSize:18,color:'#534433'}}>add</span>
              <span className="label">Add New</span>
            </button>
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
