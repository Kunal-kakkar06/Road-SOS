export default function FamilyStatusBanner({ familyResult }) {
  if (!familyResult) return null;

  const { sent, online, queued, session_id, contacts, sms_fallback } = familyResult;

  return (
    <div style={{
      background: online ? '#EAF3DE' : '#FAEEDA',
      borderRadius:8,padding:'10px 14px',
      display:'flex',flexDirection:'column',gap:4,
      marginBottom: 12
    }}>
      <div style={{display:'flex',alignItems:'center',gap:6}}>
        <span style={{
          width:8,height:8,borderRadius:'50%',flexShrink:0,
          background: online ? '#27AE60' : '#fca311',
        }}/>
        <p style={{fontSize:13,fontWeight:600,margin:0,
                   color: online ? '#27500A' : '#633806'}}>
          {online
            ? `Family notified — ${contacts} contact${contacts!==1?'s':''} alerted`
            : queued
            ? 'Family alert queued — will send SMS when signal returns'
            : 'SMS app opened — send manually to family'}
        </p>
      </div>

      {online && session_id && (
        <p style={{fontSize:11,color:'#534433',margin:0,paddingLeft:14}}>
          Tracking link sent · Session: {session_id}
        </p>
      )}

      {sms_fallback && !online && (
        <p style={{fontSize:11,color:'#633806',margin:0,paddingLeft:14}}>
          Tracking link will be sent automatically when connected
        </p>
      )}
    </div>
  );
}
