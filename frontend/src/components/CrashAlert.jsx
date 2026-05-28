import { useState, useEffect, useRef } from 'react';
import { triggerSOS } from '../services/offlineSOS';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const SEV = {
  P1: { bg:'#ba1a1a', text:'#fff',    badge:'CRITICAL' },
  P2: { bg:'#fca311', text:'#663f00', badge:'SERIOUS'  },
  P3: { bg:'#006687', text:'#fff',    badge:'MODERATE' },
  P4: { bg:'#27AE60', text:'#fff',    badge:'MINOR'    },
};

export default function CrashAlert({ crash, onDismiss }) {
  const [phase,    setPhase]   = useState('countdown');
  const [count,    setCount]   = useState(10);
  const [sosResult,setSOSResult]= useState(null);
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
      severity:          crash.severity,
      severity_label:    crash.severity_label,
      crash_probability: crash.crash_probability,
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

  const overlay = {
    position:'fixed',inset:0,zIndex:9999,
    background:'rgba(20,33,61,0.93)',
    display:'flex',alignItems:'center',justifyContent:'center',padding:20,
  };
  const card = {
    background:'#fff',borderRadius:16,padding:28,
    maxWidth:400,width:'100%',
    display:'flex',flexDirection:'column',alignItems:'center',
    gap:14,textAlign:'center',
  };

  if (phase==='cancelled') return (
    <div style={overlay}>
      <div style={card}>
        <p style={{fontSize:20,fontWeight:700,color:'#14213D'}}>SOS cancelled</p>
        <p style={{fontSize:14,color:'#534433'}}>No alert sent. Stay safe.</p>
        <button onClick={onDismiss} style={secBtn}>Close</button>
      </div>
    </div>
  );

  if (phase==='firing') return (
    <div style={overlay}>
      <div style={card}>
        <p style={{fontSize:18,fontWeight:700,color:'#14213D'}}>Sending alert…</p>
        <p style={{fontSize:13,color:'#534433'}}>Contacting emergency services</p>
      </div>
    </div>
  );

  if (phase==='done') return (
    <div style={overlay}>
      <div style={card}>
        <p style={{fontSize:22,fontWeight:700,color:'#14213D'}}>HELP IS ON THE WAY</p>
        <div style={{width:'100%',display:'flex',flexDirection:'column',gap:8}}>
          <Row done={sosResult?.channels?.server||sosResult?.channels?.synced} text="SMS sent to contacts"/>
          <Row done={!!sosResult?.channels?.queued} text="Incident saved locally"/>
          <Row done={!!sosResult?.channels?.synced} text="Server notified"/>
        </div>
        <div style={{background:s.bg,color:s.text,padding:'6px 18px',
                     borderRadius:20,fontSize:12,fontWeight:700}}>
          {s.badge} · {crash.severity_label}
        </div>
        <button onClick={onDismiss} style={secBtn}>View incident</button>
      </div>
    </div>
  );

  // Countdown (default)
  return (
    <div style={overlay}>
      <div style={{...card,borderTop:`6px solid ${s.bg}`}}>
        <div style={{background:s.bg,color:s.text,padding:'5px 14px',
                     borderRadius:20,fontSize:11,fontWeight:700}}>
          ● {s.badge} · {Math.round(crash.crash_probability*100)}% probability
        </div>
        <p style={{fontSize:20,fontWeight:700,color:'#14213D'}}>Crash detected</p>
        <p style={{fontSize:13,color:'#534433'}}>{crash.severity_label}</p>
        <div style={{width:96,height:96,borderRadius:'50%',background:s.bg,
                     display:'flex',flexDirection:'column',
                     alignItems:'center',justifyContent:'center'}}>
          <span style={{fontSize:38,fontWeight:700,color:s.text,lineHeight:1}}>{count}</span>
          <span style={{fontSize:10,color:s.text,opacity:.8}}>seconds</span>
        </div>
        <p style={{fontSize:13,color:'#534433'}}>SOS fires automatically in {count}s</p>
        <div style={{display:'flex',gap:10,width:'100%'}}>
          <button onClick={cancel} style={secBtn}>I'm OK — Cancel</button>
          <button onClick={fire} style={{...secBtn,background:s.bg,color:s.text}}>Send SOS now</button>
        </div>
      </div>
    </div>
  );
}

function Row({done,text}){
  return(
    <div style={{display:'flex',alignItems:'center',gap:10}}>
      <span style={{fontSize:15,fontWeight:700,color:done?'#27AE60':'#867461',width:20}}>{done?'✓':'○'}</span>
      <span style={{fontSize:13,color:done?'#221a11':'#534433'}}>{text}</span>
    </div>
  );
}
const secBtn={flex:1,padding:'12px 0',borderRadius:8,border:'none',
  background:'#f0e0d1',color:'#14213D',fontSize:13,fontWeight:700,
  cursor:'pointer',fontFamily:'Space Grotesk,sans-serif'};
