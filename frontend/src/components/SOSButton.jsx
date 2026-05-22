import { useState, useRef, useEffect } from 'react';
import { triggerSOS, registerSW } from '../services/offlineSOS';

const HOLD_MS     = 3000;
const CANCEL_SECS = 10;

export default function SOSButton() {
  const [phase,     setPhase]     = useState('idle');
  const [countdown, setCountdown] = useState(CANCEL_SECS);
  const [isOnline,  setIsOnline]  = useState(navigator.onLine);
  const [channels,  setChannels]  = useState({});
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

  useEffect(() => {
    const onSync = () => setChannels((p) => ({ ...p, synced: true }));
    window.addEventListener('sos-synced', onSync);
    return () => window.removeEventListener('sos-synced', onSync);
  }, []);

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
      if (c <= 0) { clearInterval(timerRef.current); fire(); }
    }, 1000);
  };

  const cancel = () => {
    clearInterval(timerRef.current);
    setPhase('cancelled');
    setTimeout(() => setPhase('idle'), 2000);
  };

  const fire = async () => {
    setPhase('firing');
    const result = await triggerSOS();
    setChannels(result.channels);
    setPhase('active');
  };

  if (phase === 'cancelled')
    return (
      <div className="card-level-2 sos-zone">
        <p style={{fontSize:20,fontWeight:700,color:'#14213D'}}>SOS cancelled</p>
        <p style={{fontSize:13,color:'#534433',marginTop:4}}>No alert was sent</p>
      </div>
    );

  if (phase === 'countdown')
    return (
      <div className="card-level-2 sos-zone" style={{borderWidth:2, borderColor:'#14213D'}}>
        <p style={{fontSize:72,fontWeight:700,color:'#14213D',lineHeight:1}}>{countdown}</p>
        <p style={{fontSize:14,color:'#534433',margin:'6px 0 20px'}}>
          SOS fires in {countdown}s
        </p>
        <button onClick={cancel}
          style={{width:'100%',padding:'14px 0',borderRadius:10,border:'none',
                  background:'#14213D',color:'#fff',fontSize:16,
                  fontWeight:700,cursor:'pointer',fontFamily:'Space Grotesk,sans-serif'}}>
          CANCEL
        </button>
      </div>
    );

  if (phase === 'firing')
    return (
      <div className="card-level-2 sos-zone">
        <p style={{fontSize:18,fontWeight:700,color:'#14213D'}}>Sending SOS…</p>
        <p style={{fontSize:13,color:'#534433',marginTop:4}}>
          Alerting emergency contacts
        </p>
      </div>
    );

  if (phase === 'active')
    return (
      <div className="card-level-2 sos-zone" style={{borderWidth:2,borderColor:'#14213D',gap:12}}>
        <p style={{fontSize:20,fontWeight:700,color:'#14213D',textAlign:'center'}}>
          HELP IS ON THE WAY
        </p>
        <div style={{display:'flex',flexDirection:'column',gap:8,width:'100%'}}>
          <Row done={channels.server || channels.synced}
               text={channels.server ? 'SMS sent via FastAPI + Twilio'
                   : channels.synced ? 'SMS sent (synced when online)'
                   : 'SMS queued — sends when signal returns'} />
          <Row done={channels.queued}       text="Incident saved locally" />
          <Row done={!!channels.synced}     text="FastAPI server notified" />
          {channels.smsFallback &&
            <Row done text="SMS app opened on your device" />}
        </div>
        {!isOnline && (
          <div style={{background:'#fca311',borderRadius:8,padding:'8px 12px',
                       textAlign:'center',width:'100%'}}>
            <p style={{color:'#663f00',fontSize:12,fontWeight:600}}>
              Offline — auto-syncs when signal returns
            </p>
          </div>
        )}
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
                    color: done ? '#27AE60' : '#867461'}}>
        {done ? '✓' : '○'}
      </span>
      <span style={{fontSize:13,color: done ? '#221a11' : '#534433'}}>
        {text}
      </span>
    </div>
  );
}
