export default function FatigueAlert({ fatigue, onDismiss, onTakeBreak }) {
  if(!fatigue||fatigue.score<60) return null;
  const severe = fatigue.score>=80;
  return (
    <div style={{position:'fixed',inset:0,zIndex:9000,
      background:'rgba(20,33,61,0.88)',display:'flex',
      alignItems:'center',justifyContent:'center',padding:20}}>
      <div style={{background:'#fff',borderRadius:16,padding:28,
        maxWidth:380,width:'100%',textAlign:'center',
        borderTop:`6px solid ${severe?'#ba1a1a':'#fca311'}`}}>
        <span className="material-symbols-outlined"
          style={{fontSize:48,color:severe?'#ba1a1a':'#fca311',
            fontVariationSettings:"'FILL' 1",marginBottom:12,display:'block'}}>
          {severe?'warning':'bedtime'}
        </span>
        <p style={{fontFamily:'Space Grotesk,sans-serif',fontSize:20,
          fontWeight:700,color:'#14213D',marginBottom:8}}>
          {severe?'Stop driving now':'Fatigue detected'}
        </p>
        <p style={{fontSize:14,color:'#534433',marginBottom:16,lineHeight:1.6}}>
          {severe
            ?'Critical fatigue. Pull over at the nearest safe location.'
            :'Signs of drowsiness detected. Consider taking a break.'}
        </p>
        <div style={{background:'#f5e5d7',borderRadius:10,padding:'10px 14px',
          display:'flex',justifyContent:'space-around',marginBottom:18}}>
          <div style={{textAlign:'center'}}>
            <p style={{fontSize:16,fontWeight:700,color:'#14213D',margin:0}}>{fatigue.score}/100</p>
            <p style={{fontSize:11,color:'#534433',margin:0}}>Fatigue score</p>
          </div>
          <div style={{textAlign:'center'}}>
            <p style={{fontSize:16,fontWeight:700,color:'#14213D',margin:0}}>{fatigue.blinksPerMin}</p>
            <p style={{fontSize:11,color:'#534433',margin:0}}>Blinks/min</p>
          </div>
          <div style={{textAlign:'center'}}>
            <p style={{fontSize:16,fontWeight:700,color:'#14213D',margin:0}}>{fatigue.headTilt}°</p>
            <p style={{fontSize:11,color:'#534433',margin:0}}>Head tilt</p>
          </div>
        </div>
        <div style={{display:'flex',gap:10}}>
          <button onClick={onTakeBreak} style={{flex:2,padding:'13px',borderRadius:10,
            border:'none',background:'#14213D',color:'#fff',fontSize:13,
            fontWeight:700,cursor:'pointer',fontFamily:'Space Grotesk,sans-serif'}}>
            Find rest stop →
          </button>
          <button onClick={onDismiss} style={{flex:1,padding:'13px',borderRadius:10,
            border:'1px solid #d9c3ad',background:'transparent',color:'#534433',
            fontSize:12,cursor:'pointer',fontFamily:'Inter,sans-serif'}}>
            I'm fine
          </button>
        </div>
      </div>
    </div>
  );
}
