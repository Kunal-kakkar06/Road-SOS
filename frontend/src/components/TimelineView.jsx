import React from 'react';

const EVENT_META = {
  crash_detected:      {icon:'crisis_alert',  color:'#ba1a1a', label:'Crash detected'},
  sos_triggered:       {icon:'emergency',      color:'#fca311', label:'SOS triggered'},
  ambulance_dispatched:{icon:'ambulance',      color:'#006687', label:'Ambulance dispatched'},
  ambulance_arrived:   {icon:'check_circle',   color:'#27AE60', label:'Ambulance arrived'},
  hospital_admitted:   {icon:'local_hospital', color:'#14213D', label:'Arrived at hospital'},
  report_generated:    {icon:'description',    color:'#534433', label:'Report generated'},
  incident_created:    {icon:'folder_open',    color:'#534433', label:'Incident opened'},
};

export default function TimelineView({ events }) {
  if (!events?.length)
    return <p style={{fontSize:13,color:'#867461'}}>No events logged yet</p>;

  return (
    <div style={{position:'relative',paddingLeft:32}}>
      {/* Vertical connector line */}
      <div style={{
        position:'absolute',left:11,top:16,
        width:2,height:'calc(100% - 32px)',
        background:'#f0e0d1',
      }}/>

      {events.map((event, i) => {
        const meta = EVENT_META[event.event_type] || {
          icon:'radio_button_checked',color:'#534433',
          label: event.event_type.replace(/_/g,' '),
        };
        return (
          <div key={i} style={{display:'flex',alignItems:'flex-start',
                               gap:12,marginBottom:14,position:'relative'}}>
            {/* Circle node */}
            <div style={{
              position:'absolute',left:-32,
              width:22,height:22,borderRadius:'50%',
              background:meta.color,flexShrink:0,
              display:'flex',alignItems:'center',justifyContent:'center',
            }}>
              <span className="material-symbols-outlined"
                style={{fontSize:12,color:'#fff',
                        fontVariationSettings:"'FILL' 1"}}>
                {meta.icon}
              </span>
            </div>

            {/* Event card */}
            <div style={{background:'#f5e5d7',borderRadius:8,
                         padding:'8px 12px',flex:1}}>
              <p style={{fontSize:12,fontWeight:600,
                         color:'#14213D',margin:'0 0 2px'}}>
                {meta.label}
              </p>
              {event.description &&
               event.description !== event.event_type && (
                <p style={{fontSize:12,color:'#534433',margin:'0 0 2px'}}>
                  {event.description}
                </p>
              )}
              <p style={{fontSize:11,color:'#867461',margin:0}}>
                {event.timestamp?.slice(0,16)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
