import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { getTriageHistory } from '../services/triageService';

export default function History() {
  const { isOnline } = useOutletContext();
  const [filter, setFilter] = useState('all');
  const [expanded, setExpanded] = useState({});
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  // Sync with local memory backup
  useEffect(() => {
    const fetchHistory = async () => {
      // Seed initial mock dataset for demonstration
      const initialRecords = [
      {
        id: 'r1',
        type: 'incident',
        date: '19 May',
        year: '2026',
        severity: 'P2',
        title: 'Outer Ring Road, BLR',
        description: 'Rear-end collision · CATS Unit 4 dispatched',
        downloadText: 'Rear-end collision details',
        steps: [
          { time: '08:14', text: 'Crash detected', done: true },
          { time: '08:14', text: 'SOS triggered', done: true },
          { time: '08:22', text: 'Ambulance en route', done: true },
          { time: '08:35', text: 'Hospital arrived — pending', done: false }
        ]
      },
      {
        id: 'r2',
        type: 'incident',
        date: '02 Apr',
        year: '2026',
        severity: 'P3',
        title: 'MG Road, Bengaluru',
        description: 'Side-swipe · Minor injuries',
        downloadText: 'Side-swipe details',
        steps: [
          { time: '14:32', text: 'Crash detected', done: true },
          { time: '14:33', text: 'SOS triggered', done: true },
          { time: '14:45', text: 'Hospital arrived', done: true }
        ]
      },
      {
        id: 'r3',
        type: 'trip',
        date: '28 Mar',
        year: '2026',
        severity: 'P4',
        title: 'BLR → Mysuru Highway',
        description: 'Trip · Risk score 32 · No incidents',
        downloadText: 'Highway Route 32 report',
        steps: [
          { time: '09:00', text: 'Highway navigation initiated', done: true },
          { time: '11:45', text: 'Arrived safety destination', done: true }
        ]
      }
    ];

    try {
      const triageEvents = await getTriageHistory();
      
      const mappedTriage = triageEvents.map(t => {
        const d = new Date(t.created_at);
        const dateStr = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
        const yearStr = d.getFullYear().toString();
        
        let sevCode = 'P4';
        if (t.final_severity === 'Critical') sevCode = 'P1';
        else if (t.final_severity === 'High') sevCode = 'P2';
        else if (t.final_severity === 'Moderate') sevCode = 'P3';
        
        return {
          id: t.id,
          type: 'triage',
          date: dateStr,
          year: yearStr,
          severity: sevCode,
          title: 'AI Triage Assessment',
          description: `Score: ${(t.final_score * 100).toFixed(0)}% · ${t.final_severity}`,
          downloadText: t.severity_label || 'View Details',
          status: t.status,
          processingMode: t.processing_mode,
          duration: t.processing_duration_ms,
          modelVersion: t.model_version,
          steps: [
            { time: d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}), text: 'Assessment Completed', done: true }
          ]
        };
      });
      
      setRecords([...mappedTriage, ...initialRecords]);
    } catch (e) {
      console.warn("Failed to fetch triage history", e);
      setRecords(initialRecords);
    } finally {
      setLoading(false);
    }
  };
  
  fetchHistory();
  }, []);

  const toggleRow = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const filtered = records.filter(r => {
    if (filter === 'all') return true;
    if (filter === 'inc') return r.type === 'incident';
    if (filter === 'trips') return r.type === 'trip';
    return true;
  });

  const getSeverityStyle = (sev) => {
    if (sev === 'P1') return { background: '#ffdad6', color: '#ba1a1a' };
    if (sev === 'P2') return { background: '#ffb95f', color: '#2a1700' };
    if (sev === 'P3') return { background: '#d9c3ad', color: '#534433' };
    return { background: '#f5e5d7', color: '#867461' };
  };

  return (
    <div className="fade-in" style={{ paddingBottom: 32 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="material-symbols-outlined icon-fill" style={{ fontSize: 28, color: '#fca311' }}>
            history
          </span>
          <div>
            <h1 style={{
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 22, fontWeight: 700, color: '#fff', margin: 0,
            }}>
              History
            </h1>
            <p style={{ fontSize: 12, color: '#a0aab2', margin: '2px 0 0' }}>
              Your past SOS events, crash reports, and triage assessments
            </p>
          </div>
        </div>
      </div>

      {/* Connection State Banner */}
      {!isOnline && (
        <div style={{
          background: 'rgba(252,163,17,0.1)',
          border: '1px solid rgba(252,163,17,0.25)',
          borderRadius: 10, padding: '10px 16px',
          marginBottom: 14,
          display: 'flex', alignItems: 'center', gap: 10,
          fontSize: 12, color: '#fca311',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>wifi_off</span>
          <span>Showing locally cached offline history</span>
        </div>
      )}

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {[
          { key: 'all', label: 'All records', icon: 'list' },
          { key: 'inc', label: 'Incidents Only', icon: 'emergency' },
          { key: 'trips', label: 'Trips Only', icon: 'route' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: '8px 18px', borderRadius: 24,
              border: filter === f.key ? '1px solid #fca311' : '1px solid rgba(15,23,42,0.15)',
              cursor: 'pointer', fontSize: 12, fontWeight: 700,
              fontFamily: 'Inter, sans-serif',
              background: filter === f.key ? '#fca311' : 'rgba(15,23,42,0.04)',
              color: filter === f.key ? '#14213D' : '#334155',
              transition: 'all .2s ease',
              display: 'flex', alignItems: 'center', gap: 6,
              boxShadow: '0 2px 5px rgba(0,0,0,0.02)'
            }}
            onMouseEnter={e => {
              if (filter !== f.key) {
                e.currentTarget.style.background = 'rgba(15,23,42,0.08)';
                e.currentTarget.style.color = '#0f172a';
              }
            }}
            onMouseLeave={e => {
              if (filter !== f.key) {
                e.currentTarget.style.background = 'rgba(15,23,42,0.04)';
                e.currentTarget.style.color = '#334155';
              }
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{f.icon}</span>
            {f.label}
          </button>
        ))}
      </div>

      {/* History Rows List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filtered.map(r => {
          const isExpanded = expanded[r.id];
          const sevStyle = getSeverityStyle(r.severity);

          return (
            <div key={r.id} style={{
              background: '#14213D',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 12,
              overflow: 'hidden'
            }}>
              <div
                onClick={() => toggleRow(r.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '16px 18px', cursor: 'pointer',
                  userSelect: 'none'
                }}
              >
                <div style={{ minWidth: 56 }}>
                  <p style={{ fontSize: 13, color: '#a0aab2', fontWeight: 600, margin: 0 }}>{r.date}</p>
                  <p style={{ fontSize: 11, color: '#6b7280', margin: 0 }}>{r.year}</p>
                </div>

                <span style={{
                  padding: '3px 8px', borderRadius: 6,
                  fontSize: 12, fontWeight: 800,
                  fontFamily: 'Space Grotesk, sans-serif',
                  ...sevStyle
                }}>
                  {r.severity}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    fontFamily: 'Space Grotesk, sans-serif',
                    fontSize: 15, fontWeight: 700, color: '#fff', margin: 0
                  }}>
                    {r.title}
                  </p>
                  <p style={{ fontSize: 12, color: '#a0aab2', margin: '2px 0 0', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {r.description}
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      alert(`Downloading report: ${r.downloadText}`);
                    }}
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: 'none', borderRadius: 8,
                      width: 32, height: 32,
                      display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center',
                      cursor: 'pointer', color: '#fca311'
                    }}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>download</span>
                  </button>
                  <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#a0aab2' }}>
                    {isExpanded ? 'expand_less' : 'expand_more'}
                  </span>
                </div>
              </div>

              {isExpanded && (
                <div style={{
                  background: 'rgba(255,255,255,0.02)',
                  borderTop: '1px dashed rgba(255,255,255,0.08)',
                  padding: '16px 18px',
                  display: 'flex', flexDirection: 'column', gap: 8
                }}>
                  {/* Audit Details */}
                  {r.type === 'triage' && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 8, fontSize: 11, color: '#a0aab2' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>memory</span>
                        {r.status === 'failed' ? 'Failed' : `${r.modelVersion ? 'v' + r.modelVersion : 'Unknown'} (${r.processingMode || 'sync'})`}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>timer</span>
                        {r.duration ? `${r.duration}ms` : '—'}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>fingerprint</span>
                        {r.id ? r.id.split('-')[0] : '—'}
                      </span>
                    </div>
                  )}

                  {r.steps.map((step, sIdx) => (
                    <div key={sIdx} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: step.done ? '#27AE60' : '#ffb95f'
                      }} />
                      <span style={{ fontSize: 12, color: '#cbd5e1', fontWeight: 600 }}>{step.time} —</span>
                      <span style={{ fontSize: 12, color: step.done ? '#cbd5e1' : '#a0aab2' }}>{step.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
