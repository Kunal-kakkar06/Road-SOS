import { useState, useEffect } from 'react';

export default function ResponderQueue() {
  const [queue, setQueue] = useState([]);
  const [assigned, setAssigned] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actioningId, setActioningId] = useState(null);
  const [notes, setNotes] = useState({});

  useEffect(() => {
    fetchEmergencies();
    const interval = setInterval(fetchEmergencies, 10000); // Auto-refresh queue every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchEmergencies = async () => {
    try {
      const queueRes = await fetch('/api/responder/queue');
      const assignedRes = await fetch('/api/responder/assigned');

      if (!queueRes.ok || !assignedRes.ok) {
        throw new Error('Failed to retrieve emergency queue.');
      }

      setQueue(await queueRes.json());
      setAssigned(await assignedRes.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (incidentId, newStatus) => {
    setActioningId(incidentId);
    try {
      const res = await fetch(`/api/responder/emergency/${incidentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: newStatus,
          notes: notes[incidentId] || ''
        })
      });
      if (!res.ok) throw new Error('Failed to update incident status.');
      
      // Reset notes field
      setNotes(prev => ({ ...prev, [incidentId]: '' }));
      await fetchEmergencies();
    } catch (err) {
      alert(err.message);
    } finally {
      setActioningId(null);
    }
  };

  const getSeverityColor = (sev) => {
    switch (sev?.toUpperCase()) {
      case 'P1': case 'CRITICAL': return '#e63946';
      case 'P2': case 'HIGH': return '#fca311';
      case 'P3': case 'MODERATE': return '#3a86c8';
      default: return '#27ae60';
    }
  };

  if (loading && queue.length === 0 && assigned.length === 0) {
    return (
      <div style={{ padding: '40px', color: '#fff', textAlign: 'center', fontFamily: 'Space Grotesk, sans-serif' }}>
        <span className="material-symbols-outlined" style={{ fontSize: '48px', animation: 'spin 1.5s infinite linear' }}>radar</span>
        <p style={{ marginTop: '12px' }}>Scanning active dispatch channels...</p>
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', fontFamily: 'Inter, sans-serif', color: '#fff' }}>
      <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: 12 }}>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: '28px', fontWeight: 700, color: '#e63946', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="material-symbols-outlined" style={{ animation: 'pulse 1.5s infinite' }}>emergency</span>
          Live Dispatch Queue
        </h1>
        <button onClick={fetchEmergencies} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: 8, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>refresh</span>
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(230,57,70,0.1)', border: '1px solid rgba(230,57,70,0.2)', borderRadius: '8px', color: '#ff4d4d', marginBottom: '20px' }}>
          {error}
        </div>
      )}

      {/* ── SECTION 1: ASSIGNED TO ME ── */}
      <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: '18px', fontWeight: 600, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: 6, color: '#27ae60' }}>
        <span className="material-symbols-outlined">assignment_turned_in</span>
        My Assignments ({assigned.length})
      </h2>

      {assigned.length === 0 ? (
        <div style={{ padding: '24px', background: 'rgba(255, 255, 255, 0.02)', border: '1px dotted rgba(255,255,255,0.1)', borderRadius: '12px', textAlign: 'center', color: '#a0a0b0', fontSize: '14px', marginBottom: '32px' }}>
          You have no active emergency dispatches assigned at this time.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '32px' }}>
          {assigned.map(item => (
            <div key={item.id} style={{
              background: 'rgba(39, 174, 96, 0.03)',
              border: '1px solid rgba(39, 174, 96, 0.25)',
              borderRadius: '16px',
              padding: '20px',
              boxShadow: '0 4px 15px rgba(0,0,0,0.1)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <span style={{ fontSize: '11px', color: '#a0a0b0', fontFamily: 'monospace' }}>ID: {item.incident_id.substring(0, 8)}...</span>
                <span style={{
                  color: getSeverityColor(item.severity),
                  background: `${getSeverityColor(item.severity)}15`,
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: 700
                }}>{item.severity || 'P2'}</span>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <p style={{ fontSize: '14px', margin: '4px 0', color: '#fff', fontWeight: 600 }}>📍 {item.address || `Lat: ${item.latitude}, Lng: ${item.longitude}`}</p>
                {item.speed_at_impact && <p style={{ fontSize: '12px', color: '#ff4d4d', margin: '4px 0' }}>⚡ Speed at Impact: {item.speed_at_impact} km/h</p>}
                <p style={{ fontSize: '12px', color: '#fca311', margin: '4px 0', textTransform: 'capitalize' }}>🏷️ Current Status: <strong>{item.status}</strong></p>
              </div>

              {/* Patient Details */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontSize: '12px' }}>
                <p style={{ margin: '0 0 6px 0', fontWeight: 700, color: '#fca311' }}>📋 Patient Health Profile</p>
                <p style={{ margin: '3px 0' }}>Name: {item.medical_profile?.full_name || 'Unknown'}</p>
                <p style={{ margin: '3px 0' }}>Blood Group: {item.medical_profile?.blood_type || 'Unknown'}</p>
                <p style={{ margin: '3px 0' }}>Allergies: {item.medical_profile?.allergies?.join(', ') || 'None'}</p>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {item.status === 'assigned' && (
                  <button onClick={() => handleUpdateStatus(item.incident_id, 'dispatched')} disabled={actioningId === item.incident_id} style={{ background: '#3a86c8', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
                    Depart Dispatch
                  </button>
                )}
                {item.status === 'dispatched' && (
                  <button onClick={() => handleUpdateStatus(item.incident_id, 'arrived')} disabled={actioningId === item.incident_id} style={{ background: '#fca311', border: 'none', color: '#000', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}>
                    Confirm Arrival
                  </button>
                )}
                {item.status === 'arrived' && (
                  <button onClick={() => handleUpdateStatus(item.incident_id, 'resolved')} disabled={actioningId === item.incident_id} style={{ background: '#27ae60', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
                    Resolve & Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── SECTION 2: OPEN DISPATCH QUEUE ── */}
      <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: '18px', fontWeight: 600, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: 6, color: '#fca311' }}>
        <span className="material-symbols-outlined">queue</span>
        Active Emergencies Queue ({queue.length})
      </h2>

      {queue.length === 0 ? (
        <div style={{ padding: '24px', background: 'rgba(255, 255, 255, 0.02)', border: '1px dotted rgba(255,255,255,0.1)', borderRadius: '12px', textAlign: 'center', color: '#a0a0b0', fontSize: '14px' }}>
          No active emergency alerts currently reported on network.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          {queue.map(item => (
            <div key={item.id} style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '16px',
              padding: '20px',
              boxShadow: '0 4px 15px rgba(0,0,0,0.15)',
              position: 'relative'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <span style={{ fontSize: '11px', color: '#a0a0b0', fontFamily: 'monospace' }}>ID: {item.incident_id.substring(0, 8)}...</span>
                <span style={{
                  color: getSeverityColor(item.severity),
                  background: `${getSeverityColor(item.severity)}15`,
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: 700
                }}>{item.severity || 'P2'}</span>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <p style={{ fontSize: '14px', margin: '4px 0', color: '#fff', fontWeight: 600 }}>📍 {item.address || `Lat: ${item.latitude}, Lng: ${item.longitude}`}</p>
                {item.speed_at_impact && <p style={{ fontSize: '12px', color: '#ff4d4d', margin: '4px 0' }}>⚡ Speed at Impact: {item.speed_at_impact} km/h</p>}
                <p style={{ fontSize: '12px', color: '#a0a0b0', margin: '4px 0', textTransform: 'capitalize' }}>🏷️ Status: <strong>{item.status}</strong></p>
              </div>

              {/* Responder Notes Input */}
              <div style={{ marginBottom: '16px' }}>
                <input
                  type="text"
                  placeholder="Responder/Ambulance notes..."
                  value={notes[item.incident_id] || ''}
                  onChange={(e) => setNotes({ ...notes, [item.incident_id]: e.target.value })}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#14213d',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '6px',
                    padding: '8px',
                    color: '#fff',
                    fontSize: '12px',
                    outline: 'none'
                  }}
                />
              </div>

              {/* Action */}
              <button
                onClick={() => handleUpdateStatus(item.incident_id, 'assigned')}
                disabled={actioningId === item.incident_id}
                style={{
                  width: '100%',
                  background: 'linear-gradient(135deg, #e63946 0%, #ba1a1a 100%)',
                  border: 'none',
                  color: '#fff',
                  padding: '10px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: '0 4px 10px rgba(230,57,70,0.15)'
                }}
              >
                Accept & Dispatch Units
              </button>
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.4; }
          100% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
