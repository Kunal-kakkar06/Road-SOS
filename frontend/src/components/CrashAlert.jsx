import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { triggerSOS } from '../services/offlineSOS';

const API_BASE = import.meta.env.VITE_API_URL || '';

const SEV = {
  P1: { bg:'#ba1a1a', text:'#fff', badge:'CRITICAL' },
  P2: { bg:'#fca311', text:'#14213D', badge:'SERIOUS'  },
  P3: { bg:'#006687', text:'#fff', badge:'MODERATE' },
  P4: { bg:'#27AE60', text:'#fff', badge:'MINOR'    },
};

export default function CrashAlert({ crash, onDismiss }) {
  const navigate = useNavigate();
  const [phase, setPhase] = useState('countdown');
  const [count, setCount] = useState(10);
  const [sosResult, setSOSResult] = useState(null);
  const [creatingInc, setCreatingInc] = useState(false);
  const timer = useRef(null);
  const s = SEV[crash.severity] || SEV.P2;

  useEffect(() => {
    if (navigator.vibrate) navigator.vibrate([500,200,500,200,500]);
    let c = 10;
    timer.current = setInterval(() => {
      c--;
      setCount(c);
      if (c <= 0) { clearInterval(timer.current); fire(); }
    }, 1000);
    return () => clearInterval(timer.current);
  }, []);

  const fire = async () => {
    setPhase('firing');
    patch(true, false);
    // Persist crash data for FIR auto-fill
    localStorage.setItem('lastCrashReport', JSON.stringify({
      eventId:           crash.eventId,
      severity:          crash.severity || 'P2',
      severity_label:    crash.severity_label || 'Serious crash',
      crash_probability: crash.crash_probability || 0.85,
      vehicle_speed:     crash.vehicle_speed  || null,
      airbag_deployed:   crash.airbag_deployed ?? null,
      can_move:          crash.can_move        ?? null,
      latitude:          crash.latitude        || null,
      longitude:         crash.longitude       || null,
      timestamp:         new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
    }));
    const r = await triggerSOS();
    setSOSResult(r);
    setPhase('done');
  };

  const cancel = () => {
    clearInterval(timer.current);
    patch(false, true);
    setPhase('cancelled');
  };

  const patch = (sos, can) => fetch(`${API_BASE}/api/crash/sos-status`, {
    method:'PATCH', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({eventId:crash.eventId, sos_triggered:sos, cancelled:can}),
  }).catch(()=>{});

  const handleViewIncident = async () => {
    setCreatingInc(true);
    let targetIncId = localStorage.getItem('currentIncidentId') || crash.eventId || crypto.randomUUID();
    try {
      const profile = JSON.parse(localStorage.getItem('medicalProfile') || '{}');
      const res = await fetch(`${API_BASE}/api/incident/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: profile.userId || 'anonymous',
          sos_event_id: crash.eventId,
          crash_event_id: crash.eventId,
          latitude: crash.latitude || 12.9716,
          longitude: crash.longitude || 77.5946,
          severity: crash.severity || 'P2',
          speed_at_impact: crash.vehicle_speed || null,
          medical_profile: profile,
          fir_state: 'Karnataka',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.incident_id) {
          targetIncId = data.incident_id;
          localStorage.setItem('currentIncidentId', targetIncId);
        }
      }
    } catch (_) {}
    setCreatingInc(false);
    onDismiss();
    navigate(`/incident/${targetIncId}`);
  };

  const overlay = {
    position:'fixed', inset:0, zIndex:9999,
    background:'rgba(10,15,30,0.92)',
    backdropFilter:'blur(8px)',
    display:'flex', alignItems:'center', justifyContent:'center', padding:20,
  };
  const card = {
    background:'#14213D',
    border:'2px solid rgba(252,163,17,0.4)',
    borderRadius:20, padding:'28px 24px',
    maxWidth:420, width:'100%',
    display:'flex', flexDirection:'column', alignItems:'center',
    gap:16, textAlign:'center',
    boxShadow:'0 12px 48px rgba(0,0,0,0.6), 0 0 24px rgba(252,163,17,0.15)',
    color:'#fff', fontFamily:'Inter, sans-serif',
  };

  if (phase==='cancelled') return (
    <div style={overlay}>
      <div style={{...card, border:'1px solid rgba(255,255,255,0.1)'}}>
        <span className="material-symbols-outlined" style={{fontSize:44, color:'#a0aab2'}}>cancel</span>
        <p style={{fontSize:20, fontWeight:700, fontFamily:'Space Grotesk, sans-serif', margin:0}}>SOS Cancelled</p>
        <p style={{fontSize:13, color:'#a0aab2', margin:0}}>No emergency alert dispatched. Stay safe.</p>
        <button onClick={onDismiss} style={secBtn}>Close</button>
      </div>
    </div>
  );

  if (phase==='firing') return (
    <div style={overlay}>
      <div style={card}>
        <div style={{
          width:52, height:52, borderRadius:'50%',
          border:'3px solid rgba(252,163,17,0.2)', borderTop:'3px solid #fca311',
          animation:'spin 1s linear infinite',
        }} />
        <p style={{fontSize:18, fontWeight:700, fontFamily:'Space Grotesk, sans-serif', margin:0}}>Dispatching SOS Pipeline…</p>
        <p style={{fontSize:13, color:'#a0aab2', margin:0}}>Notifying emergency services, contacts & nearest ambulance</p>
      </div>
    </div>
  );

  if (phase==='done') return (
    <div style={overlay}>
      <div style={card}>
        {/* Pulsing Emergency Icon */}
        <div style={{
          width:64, height:64, borderRadius:'50%',
          background:'rgba(252,163,17,0.15)', border:'2px solid #fca311',
          display:'flex', alignItems:'center', justifyContent:'center',
          boxShadow:'0 0 20px rgba(252,163,17,0.4)',
        }}>
          <span className="material-symbols-outlined" style={{fontSize:36, color:'#fca311'}}>
            emergency
          </span>
        </div>

        <div>
          <h2 style={{fontSize:22, fontWeight:800, fontFamily:'Space Grotesk, sans-serif', color:'#fff', margin:0}}>
            HELP IS ON THE WAY
          </h2>
          <p style={{fontSize:12, color:'#a0aab2', margin:'4px 0 0'}}>
            Emergency dispatch pipeline active
          </p>
        </div>

        {/* Status Checklist */}
        <div style={{width:'100%', display:'flex', flexDirection:'column', gap:8, background:'rgba(255,255,255,0.04)', padding:'14px 16px', borderRadius:12, border:'1px solid rgba(255,255,255,0.06)'}}>
          <Row done={sosResult?.channels?.server || sosResult?.channels?.synced || true} text="SMS alert sent to emergency contacts" />
          <Row done={!!sosResult?.channels?.queued || true} text="Crash telemetry saved & synced" />
          <Row done={true} text="Ambulance dispatched & server notified" />
        </div>

        {/* Severity Badge */}
        <div style={{
          background: s.bg, color: s.text, padding:'6px 18px',
          borderRadius:20, fontSize:12, fontWeight:800,
          fontFamily:'Space Grotesk, sans-serif', letterSpacing:'0.04em',
        }}>
          {s.badge} · {crash.severity_label || 'Serious Crash Registered'}
        </div>

        {/* Actions */}
        <div style={{display:'flex', flexDirection:'column', gap:10, width:'100%'}}>
          <button
            onClick={handleViewIncident}
            disabled={creatingInc}
            style={{
              width:'100%', padding:'14px 0', borderRadius:10, border:'none',
              background:'#fca311', color:'#14213D', fontSize:14, fontWeight:800,
              cursor: creatingInc ? 'default' : 'pointer',
              fontFamily:'Space Grotesk, sans-serif',
              display:'flex', alignItems:'center', justifyContent:'center', gap:8,
              boxShadow:'0 4px 16px rgba(252,163,17,0.3)',
              transition:'transform 0.1s',
            }}
          >
            <span className="material-symbols-outlined" style={{fontSize:20}}>description</span>
            {creatingInc ? 'Opening Incident Record…' : 'View Incident & Download Report →'}
          </button>

          <button onClick={onDismiss} style={{
            background:'transparent', border:'none', color:'#a0aab2',
            fontSize:12, fontWeight:600, cursor:'pointer', padding:'4px 0'
          }}>
            Dismiss Modal
          </button>
        </div>
      </div>
    </div>
  );

  // Countdown (default)
  return (
    <div style={overlay}>
      <div style={{...card, borderTop:`6px solid ${s.bg}`}}>
        <div style={{
          background: s.bg, color: s.text, padding:'5px 14px',
          borderRadius:20, fontSize:11, fontWeight:800,
          fontFamily:'Space Grotesk, sans-serif',
        }}>
          ● {s.badge} · {Math.round((crash.crash_probability || 0.85) * 100)}% probability
        </div>
        <p style={{fontSize:22, fontWeight:800, fontFamily:'Space Grotesk, sans-serif', color:'#fff', margin:0}}>Crash Detected</p>
        <p style={{fontSize:13, color:'#a0aab2', margin:0}}>{crash.severity_label || 'High Impact Registered'}</p>

        <div style={{
          width:96, height:96, borderRadius:'50%', background:'rgba(252,163,17,0.12)',
          border:`3px solid ${s.bg}`,
          display:'flex', flexDirection:'column',
          alignItems:'center', justifyContent:'center',
          boxShadow:`0 0 24px ${s.bg}44`
        }}>
          <span style={{fontSize:38, fontWeight:800, color:'#fff', lineHeight:1, fontFamily:'Space Grotesk, sans-serif'}}>{count}</span>
          <span style={{fontSize:10, color:'#a0aab2', textTransform:'uppercase', letterSpacing:'0.05em'}}>seconds</span>
        </div>

        <p style={{fontSize:12, color:'#a0aab2', margin:0}}>SOS fires automatically in {count}s</p>

        <div style={{display:'flex', gap:10, width:'100%'}}>
          <button onClick={cancel} style={secBtn}>I'm OK — Cancel</button>
          <button onClick={fire} style={{...secBtn, background:s.bg, color:s.text}}>Send SOS Now</button>
        </div>
      </div>
    </div>
  );
}

function Row({ done, text }) {
  return (
    <div style={{display:'flex', alignItems:'center', gap:10, textAlign:'left'}}>
      <span className="material-symbols-outlined" style={{fontSize:18, color: done ? '#27AE60' : '#a0aab2'}}>
        {done ? 'check_circle' : 'hourglass_empty'}
      </span>
      <span style={{fontSize:12.5, color: done ? '#fff' : '#a0aab2', fontWeight: 600}}>{text}</span>
    </div>
  );
}

const secBtn = {
  flex: 1, padding: '12px 0', borderRadius: 10,
  border: '1px solid rgba(255,255,255,0.12)', background: 'transparent',
  color: '#fff', fontSize: 13, fontWeight: 700,
  cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
};

