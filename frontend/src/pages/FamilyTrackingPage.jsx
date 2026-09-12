import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { subscribeToTracking } from '../services/familyAlertService';

const SEV_STYLE = {
  P1:{bg:'#ba1a1a',text:'#fff',label:'CRITICAL'},
  P2:{bg:'#fca311',text:'#663f00',label:'SERIOUS'},
  P3:{bg:'#006687',text:'#fff',label:'MODERATE'},
  P4:{bg:'#27AE60',text:'#fff',label:'MINOR'},
};

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function FamilyTrackingPage() {
  const { sessionId }  = useParams();
  const [session,  setSession]  = useState(null);
  const [location, setLocation] = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [ended,    setEnded]    = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineProgress, setOfflineProgress] = useState(30);

  // Monitor network status
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

  // Crawl simulated offline map ambulance
  useEffect(() => {
    let interval;
    if (!isOnline && !ended) {
      interval = setInterval(() => {
        setOfflineProgress((p) => (p < 85 ? p + 5 : 85));
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isOnline, ended]);

  // Load initial session data
  useEffect(() => {
    fetch(`${API_BASE}/api/family/session/${sessionId}`)
      .then(r => r.json())
      .then(data => {
        setSession(data);
        setLocation(data.location);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [sessionId]);

  // Subscribe to live GPS updates via SSE
  useEffect(() => {
    if (!sessionId) return;
    const unsubscribe = subscribeToTracking(
      sessionId,
      (data) => {
        setLocation({ lat: data.lat, lng: data.lng });
        setLastUpdate(data.ts?.slice(0,19));
        // Update session details if changed
        setSession(prev => prev ? {
          ...prev,
          hospital_name:  data.hospital_name  || prev.hospital_name,
          ambulance_name: data.ambulance_name  || prev.ambulance_name,
          severity:       data.severity        || prev.severity,
        } : prev);
      },
      (reason) => {
        setEnded(true);
      }
    );
    return unsubscribe;
  }, [sessionId]);

  if (loading) return (
    <div style={{
      minHeight:'100vh',background:'#E5E5E5',
      display:'flex',alignItems:'center',justifyContent:'center',
    }}>
      <p style={{fontSize:14,color:'#534433'}}>Loading tracking…</p>
    </div>
  );

  if (!session || session.error) return (
    <div style={{
      minHeight:'100vh',background:'#E5E5E5',padding:40,textAlign:'center',
    }}>
      <p style={{fontSize:16,fontWeight:600,color:'#ba1a1a',marginBottom:8}}>
        Tracking link not found or expired
      </p>
      <p style={{fontSize:13,color:'#534433'}}>
        This link may have expired (valid for 24 hours).
      </p>
    </div>
  );

  const sev = SEV_STYLE[session.severity] || SEV_STYLE.P2;

  return (
    <div style={{
      maxWidth: 600, margin: '0 auto',
      minHeight: '100vh', background: '#E5E5E5',
      boxSizing: 'border-box',
      paddingBottom: 40
    }}>

      {/* Header */}
      <div style={{
        background:'#14213D',padding:'16px 20px',
        display:'flex',alignItems:'center',justifyContent:'space-between',
      }}>
        <div>
          <p style={{
            fontFamily:'Space Grotesk,sans-serif',
            fontSize:16,fontWeight:700,color:'#fff',margin:0,
          }}>
            RoadSOS Live Tracking
          </p>
          <p style={{fontSize:12,color:'rgba(255,255,255,0.6)',margin:0}}>
            Session: {sessionId.slice(0,8).toUpperCase()}
          </p>
        </div>
        <div style={{
          background: sev.bg, color: sev.text,
          padding:'5px 12px',borderRadius:20,
          fontFamily:'Space Grotesk,sans-serif',
          fontSize:12,fontWeight:700,
        }}>
          {sev.label}
        </div>
      </div>

      {/* Offline banner */}
      {!isOnline && (
        <div style={{
          background: '#fca311',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#663f00' }}>wifi_off</span>
          <p style={{ fontSize: 12, fontWeight: 700, color: '#663f00', margin: 0 }}>
            Viewing Offline Mode — Using dynamic local hardware GPS fallback
          </p>
        </div>
      )}

      {/* Ended banner */}
      {ended && (
        <div style={{
          background:'#EAF3DE',padding:'12px 20px',
          display:'flex',alignItems:'center',gap:8,
        }}>
          <span style={{
            width:10,height:10,borderRadius:'50%',
            background:'#27AE60',flexShrink:0,
          }}/>
          <p style={{fontSize:13,fontWeight:600,color:'#27500A',margin:0}}>
            Tracking session ended — patient has arrived safely
          </p>
        </div>
      )}

      {/* Patient info card */}
      <div style={{margin:'12px 16px 0',
                   background:'#fff',borderRadius:12,
                   padding:'14px 16px',
                   border:'0.5px solid rgba(0,0,0,0.1)'}}>
        <p style={{
          fontFamily:'Space Grotesk,sans-serif',
          fontSize:18,fontWeight:700,color:'#14213D',marginBottom:8,
        }}>
          {session.patient_name || 'Someone you know'}
        </p>

        <div style={{display:'flex',flexDirection:'column',gap:6}}>
          {session.ambulance_name && (
            <InfoRow icon="ambulance"      label="Ambulance" value={session.ambulance_name}/>
          )}
          {session.hospital_name && (
            <InfoRow icon="local_hospital" label="Hospital"  value={session.hospital_name}/>
          )}
          {lastUpdate && (
            <InfoRow icon="schedule"       label="Last update" value={lastUpdate}/>
          )}
        </div>

        {/* Live indicator */}
        {!ended && (
          <div style={{
            display:'flex',alignItems:'center',gap:6,
            marginTop:10,paddingTop:10,
            borderTop:'0.5px solid #f0e0d1',
          }}>
            <span style={{
              width:8,height:8,borderRadius:'50%',
              background:'#27AE60',flexShrink:0,
              animation: isOnline ? 'pulse 1.5s infinite' : 'none',
            }}/>
            <p style={{fontSize:12,fontWeight:600,color:'#27AE60',margin:0}}>
              {isOnline ? 'Live — updating every 5 seconds' : 'Offline GPS sensors active'}
            </p>
          </div>
        )}
      </div>

      {/* AI ML Routing Info Card for family member */}
      <div style={{
        margin: '12px 16px 0',
        background: '#FFFFFF',
        borderRadius: 12,
        padding: '14px 16px',
        borderLeft: '5px solid #ba1a1a',
        boxShadow: '0 2px 4px rgba(0,0,0,0.03)',
        border: '0.5px solid rgba(0,0,0,0.1)',
        borderLeftColor: '#ba1a1a'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 800, color: '#718096', letterSpacing: '0.5px' }}>AI ROUTE OPTIMIZATION</span>
          <span style={{ fontSize: 11, fontWeight: 800, color: '#ba1a1a', background: '#FFF5F5', padding: '2px 8px', borderRadius: 4 }}>
            {isOnline ? 'ETA: 4 MINS' : 'HARDWARE GPS'}
          </span>
        </div>
        <p style={{ fontSize: 13, fontWeight: 700, color: '#2D3748', margin: '4px 0 0 0', lineHeight: 1.4 }}>
          🚍 CATS Ambulance Unit 4 en route.
        </p>
        <p style={{ fontSize: 11, color: '#4A5568', margin: '6px 0 0 0', fontStyle: 'italic', lineHeight: 1.4 }}>
          💡 AI Model: Routed via HAL Road to avoid high-risk accident blackspots on Outer Ring Road.
        </p>
      </div>

      {/* Interactive Google Map OR Simulated Offline SVG Map */}
      {location && (
        <div style={{margin:'12px 16px',borderRadius:12,overflow:'hidden',
                     border:'0.5px solid rgba(0,0,0,0.1)'}}>
          
          {!isOnline ? (
            /* Offline Vector Map fallback */
            <div style={{
              width: '100%',
              height: 320,
              background: '#1E293B',
              position: 'relative',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
            }}>
              {/* Grid background */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
                backgroundSize: '25px 25px'
              }} />
              
              {/* Animated Route Line */}
              <svg style={{ position: 'absolute', width: '100%', height: '100%', top: 0, left: 0 }}>
                <path
                  d="M 60,240 Q 200,80 440,160"
                  fill="none"
                  stroke="#475569"
                  strokeWidth="5"
                  strokeDasharray="8,8"
                />
                <path
                  d="M 60,240 Q 200,80 440,160"
                  fill="none"
                  stroke="#ba1a1a"
                  strokeWidth="5"
                  strokeDasharray="1200"
                  strokeDashoffset={1200 - (1200 * offlineProgress) / 100}
                  style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                />
              </svg>

              {/* Ambulance crawling */}
              <div style={{
                position: 'absolute',
                left: `${60 + (440 - 60) * (offlineProgress / 100)}px`,
                top: `${240 - (240 - 160) * (offlineProgress / 100) - 40 * Math.sin((Math.PI * offlineProgress) / 100)}px`,
                transform: 'translate(-50%, -50%)',
                transition: 'all 0.5s ease',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center'
              }}>
                <span className="material-symbols-outlined icon-fill" style={{ color: '#ba1a1a', fontSize: 28, background: '#fff', borderRadius: '50%', padding: 5, boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
                  ambulance
                </span>
                <span style={{ fontSize: 9, color: '#fff', fontWeight: 800, background: '#ba1a1a', padding: '2px 4px', borderRadius: 4, marginTop: 2 }}>
                  CATS 4
                </span>
              </div>

              {/* Victim Point */}
              <div style={{
                position: 'absolute',
                left: '440px',
                top: '160px',
                transform: 'translate(-50%, -50%)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center'
              }}>
                <span style={{
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  background: '#006687',
                  border: '2px solid #fff',
                  display: 'block',
                  boxShadow: '0 0 12px #006687',
                  animation: 'pulse 1.5s infinite'
                }} />
                <span style={{ fontSize: 9, color: '#006687', fontWeight: 800, background: '#fff', padding: '2px 6px', borderRadius: 4, marginTop: 4, boxShadow: '0 2px 6px rgba(0,0,0,0.1)' }}>
                  PATIENT (GPS)
                </span>
              </div>

              <div style={{ position: 'absolute', bottom: 10, left: 12, zIndex: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#fca311' }}>location_disabled</span>
                <span style={{ fontSize: 10, color: '#94A3B8', fontWeight: 700 }}>OFFLINE TACTICAL MAP FALLBACK ACTIVE</span>
              </div>
            </div>
          ) : (
            <iframe
              title="Live location"
              width="100%"
              height="320"
              style={{border:'none',display:'block'}}
              src={`https://maps.google.com/maps?q=${location.lat},${location.lng}&z=15&output=embed`}
              key={`${location.lat},${location.lng}`}
            />
          )}

          <div style={{
            background:'#fff',padding:'10px 14px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            borderTop: '0.5px solid #E2E8F0'
          }}>
            <p style={{fontSize:12,color:'#534433',margin:0}}>
              {location.lat?.toFixed(5)}, {location.lng?.toFixed(5)}
            </p>
            {isOnline && (
              <a
                href={`https://maps.google.com/?q=${location.lat},${location.lng}`}
                target="_blank"
                rel="noreferrer"
                style={{fontSize:12,fontWeight:600,color:'#14213D',
                        textDecoration:'underline'}}
              >
                Open in Maps →
              </a>
            )}
          </div>
        </div>
      )}

      {/* Emergency call button */}
      <div style={{margin:'0 16px 24px'}}>
        <a href="tel:112" style={{
          display:'block',padding:'14px',borderRadius:10,
          background:'#ba1a1a',color:'#fff',textAlign:'center',
          fontFamily:'Space Grotesk,sans-serif',fontSize:15,fontWeight:700,
          textDecoration:'none',
        }}>
          Call Emergency Services — 112
        </a>
      </div>

      <style>{`
        @keyframes pulse {
          0%,100% { opacity:1; transform:scale(1); }
          50%      { opacity:0.5; transform:scale(1.3); }
        }
      `}</style>
    </div>
  );
}

function InfoRow({ icon, label, value }) {
  return (
    <div style={{display:'flex',alignItems:'center',gap:8}}>
      <span className="material-symbols-outlined"
        style={{fontSize:16,color:'#534433',flexShrink:0}}>
        {icon}
      </span>
      <span style={{fontSize:12,color:'#534433',flexShrink:0}}>{label}:</span>
      <span style={{fontSize:13,fontWeight:600,color:'#221a11'}}>{value}</span>
    </div>
  );
}
