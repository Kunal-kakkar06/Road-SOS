import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function ManualCrashReport({ onResult, onCancel }) {
  const [step,   setStep]   = useState(1);
  const [speed,  setSpeed]  = useState('');
  const [airbag, setAirbag] = useState(null);
  const [move,   setMove]   = useState(null);
  const [loading,setLoading]= useState(false);

  const submit = async () => {
    if (!speed || airbag===null || move===null) return;
    setLoading(true);
    const coords = await getCoords();
    const payload = {
      eventId:  crypto.randomUUID(),
      userId:   JSON.parse(localStorage.getItem('medicalProfile')||'{}').userId||'anon',
      latitude: coords.lat, longitude: coords.lng,
      timestamp: new Date().toLocaleString('en-IN',{timeZone:'Asia/Kolkata'}),
      vehicle_speed: parseFloat(speed),
      airbag_deployed: airbag,
      can_move: move,
    };
    try {
      const res = await fetch(`${API_BASE}/api/crash/manual`,{
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload), signal:AbortSignal.timeout(6000),
      });
      if (res.ok) {
        const result = await res.json();
        // Persist for FIR auto-fill
        localStorage.setItem('lastCrashReport', JSON.stringify({
          eventId:         payload.eventId,
          vehicle_speed:   payload.vehicle_speed,
          airbag_deployed: payload.airbag_deployed,
          can_move:        payload.can_move,
          latitude:        payload.latitude,
          longitude:       payload.longitude,
          timestamp:       payload.timestamp,
          severity:        result.severity,
          severity_label:  result.severity_label,
          crash_probability: result.crash_probability,
        }));
        onResult(result);
        return;
      }
    } catch(_) {}
    // Offline fallback
    const fallback = {
      eventId:payload.eventId, isCrash:true,
      crash_probability:0.80, severity:'P2',
      severity_label:'Serious crash (offline estimate)',
    };
    localStorage.setItem('lastCrashReport', JSON.stringify({
      eventId:         payload.eventId,
      vehicle_speed:   payload.vehicle_speed,
      airbag_deployed: payload.airbag_deployed,
      can_move:        payload.can_move,
      latitude:        payload.latitude,
      longitude:       payload.longitude,
      timestamp:       payload.timestamp,
      severity:        fallback.severity,
      severity_label:  fallback.severity_label,
      crash_probability: fallback.crash_probability,
    }));
    onResult(fallback);
    setLoading(false);
  };

  const card={background:'#fff',borderRadius:14,padding:24,
    maxWidth:400,width:'100%',display:'flex',flexDirection:'column',gap:14};
  const choiceBtn=(active)=>({
    flex:1,padding:'12px 0',borderRadius:8,border:'none',
    background:active?'#14213D':'#f0e0d1',
    color:active?'#fff':'#221a11',
    fontSize:14,fontWeight:600,cursor:'pointer',
    fontFamily:'Inter,sans-serif',transition:'all .15s',
  });
  const nextBtn={width:'100%',padding:'13px 0',borderRadius:8,border:'none',
    background:'#14213D',color:'#fff',fontSize:14,fontWeight:700,
    cursor:'pointer',fontFamily:'Space Grotesk,sans-serif'};

  return(
    <div style={{position:'fixed',inset:0,zIndex:9000,
      background:'rgba(20,33,61,0.88)',
      display:'flex',alignItems:'center',justifyContent:'center',padding:20}}>
      <div style={card}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <p style={{fontSize:17,fontWeight:700,color:'#14213D'}}>Report a crash</p>
          <span style={{fontSize:12,color:'#534433'}}>Step {step}/3</span>
        </div>

        {step===1&&<>
          <p style={{fontSize:14,fontWeight:600,color:'#221a11'}}>Approximate speed at impact (km/h)?</p>
          <input type="number" placeholder="e.g. 60" value={speed}
            onChange={e=>setSpeed(e.target.value)}
            style={{padding:'12px',borderRadius:8,fontSize:16,
              border:'2px solid #14213D',width:'100%',fontFamily:'Inter,sans-serif'}}/>
          <button style={nextBtn} onClick={()=>speed&&setStep(2)}>Next →</button>
        </>}

        {step===2&&<>
          <p style={{fontSize:14,fontWeight:600,color:'#221a11'}}>Did any airbags deploy?</p>
          <div style={{display:'flex',gap:10}}>
            {[['Yes',true],['No',false]].map(([l,v])=>(
              <button key={l} style={choiceBtn(airbag===v)}
                onClick={()=>{setAirbag(v);setStep(3)}}>{l}</button>
            ))}
          </div>
          <button onClick={()=>setStep(1)} style={{...nextBtn,background:'transparent',
            color:'#534433',fontSize:13,fontWeight:400}}>← Back</button>
        </>}

        {step===3&&<>
          <p style={{fontSize:14,fontWeight:600,color:'#221a11'}}>Can the person move / exit vehicle?</p>
          <div style={{display:'flex',gap:10}}>
            {[['Yes',true],['No / unsure',false]].map(([l,v])=>(
              <button key={l} style={choiceBtn(move===v)}
                onClick={()=>setMove(v)}>{l}</button>
            ))}
          </div>
          <button style={{...nextBtn,opacity:move===null||loading?.5:1}}
            disabled={move===null||loading} onClick={submit}>
            {loading?'Assessing…':'Assess severity →'}
          </button>
          <button onClick={()=>setStep(2)} style={{...nextBtn,background:'transparent',
            color:'#534433',fontSize:13,fontWeight:400}}>← Back</button>
        </>}

        <button onClick={onCancel}
          style={{fontSize:13,color:'#867461',background:'none',
            border:'none',cursor:'pointer',textDecoration:'underline'}}>
          Cancel — no crash
        </button>
      </div>
    </div>
  );
}

const getCoords=()=>new Promise(resolve=>{
  if(!navigator.geolocation)return resolve({lat:0,lng:0});
  navigator.geolocation.getCurrentPosition(
    p=>resolve({lat:p.coords.latitude,lng:p.coords.longitude}),
    ()=>resolve({lat:0,lng:0}),
    {enableHighAccuracy:true,timeout:5000}
  );
});
