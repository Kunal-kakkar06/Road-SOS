import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import TimelineView  from '../components/TimelineView';
import PhotoUploader from '../components/PhotoUploader';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function IncidentReportPage() {
  const { incidentId }  = useParams();
  const [incident,  setIncident]  = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [genPDF,    setGenPDF]    = useState(false);
  const [pdfReady,  setPDFReady]  = useState(false);
  const [firGuide,  setFIRGuide]  = useState(null);
  const [showFIR,   setShowFIR]   = useState(false);

  // Edit Mode States
  const [isEditing, setIsEditing] = useState(false);
  const [editAddress, setEditAddress] = useState('');
  const [editSpeed, setEditSpeed] = useState('');
  const [editAmbulance, setEditAmbulance] = useState('');
  const [editHospital, setEditHospital] = useState('');
  const [editSeverity, setEditSeverity] = useState('P2');
  const [saving, setSaving] = useState(false);

  const fetchIncidentDetails = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/incident/${incidentId}`);
      if (res.ok) {
        const data = await res.json();
        setIncident(data);
        setEditAddress(data.address || '');
        setEditSpeed(data.speed_at_impact || '');
        setEditAmbulance(data.ambulance_name || '');
        setEditHospital(data.hospital_name || '');
        setEditSeverity(data.severity || 'P2');
      }
    } catch (_) {}
    setLoading(false);
  };

  useEffect(() => {
    fetchIncidentDetails();
  }, [incidentId]);

  const generatePDF = async () => {
    setGenPDF(true);
    try {
      const res = await fetch(`${API_BASE}/api/incident/${incidentId}/generate-pdf`, { method:'POST' });
      if (res.ok) setPDFReady(true);
    } catch (_) {}
    setGenPDF(false);
  };

  const downloadPDF = () =>
    window.open(`${API_BASE}/api/incident/${incidentId}/download-pdf`, '_blank');

  const sharePDF = async () => {
    const url = API_BASE ? `${API_BASE}/api/incident/${incidentId}/download-pdf` : `${window.location.origin}/api/incident/${incidentId}/download-pdf`;
    if (navigator.share) {
      try {
        await navigator.share({ title:'RoadSOS Incident Report', url });
      } catch (_) {}
    } else {
      navigator.clipboard.writeText(url);
      alert('PDF link copied to clipboard');
    }
  };

  const handleSaveChanges = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/incident/${incidentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: editAddress,
          speed_at_impact: editSpeed ? parseFloat(editSpeed) : null,
          ambulance_name: editAmbulance,
          hospital_name: editHospital,
          severity: editSeverity,
        })
      });
      if (res.ok) {
        await fetchIncidentDetails();
        setIsEditing(false);
      }
    } catch (_) {}
    setSaving(false);
  };

  const handleCancelEdits = () => {
    if (incident) {
      setEditAddress(incident.address || '');
      setEditSpeed(incident.speed_at_impact || '');
      setEditAmbulance(incident.ambulance_name || '');
      setEditHospital(incident.hospital_name || '');
      setEditSeverity(incident.severity || 'P2');
    }
    setIsEditing(false);
  };

  const loadFIRGuide = async () => {
    setFIRGuide({
      state: incident?.fir_state || "Karnataka",
      steps: [
        {
          step_number: 1,
          title: "Download RoadSOS Official Telemetry Report",
          description: "Generate and download the official PDF report below. It contains encrypted telemetry logs, GPS stamps, and verified crash timestamps signed by the browser APIs to serve as concrete proof.",
          documents: ["RoadSOS Telemetry PDF Report", "Proof of Identity (Aadhaar / ABHA Card)"],
          tip: "Submit both the physical printout and email the PDF to your jurisdiction station."
        },
        {
          step_number: 2,
          title: "Visit Nearest Jurisdiction Police Station",
          description: "File the First Information Report (FIR) at the local police station representing your incident coordinates.",
          documents: ["Driving License", "Vehicle RC Card"],
          tip: "Legally, any police station must accept an emergency FIR under the Zero-FIR protocol."
        },
        {
          step_number: 3,
          title: "Obtain Verified Signature & Copy",
          description: "Verify that all details on the official FIR log book match the RoadSOS telemetry. Demand your free copy of the signed and stamped FIR.",
          documents: ["Signed copy of FIR (Form 1)"],
          tip: "This signed copy is mandatory to unlock immediate insurance settlement processes."
        }
      ]
    });
    setShowFIR(true);
  };

  if (loading) return (
    <div style={{
      minHeight:'100vh', background:'#f8fafc',
      display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
      fontFamily:'Inter, sans-serif'
    }}>
      <div style={{
        width: 48, height: 48, border: '3px solid rgba(15,23,42,0.08)',
        borderTop: '3px solid #fca311', borderRadius: '50%',
        animation: 'spin 1s linear infinite', marginBottom: 16
      }} />
      <p style={{fontSize:14, fontWeight:600, color:'#475569'}}>Assembling telemetry matrices…</p>
      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (!incident || incident.error) return (
    <div style={{
      minHeight:'100vh', background:'#f8fafc',
      display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
      fontFamily:'Inter, sans-serif', padding: 24, textAlign: 'center'
    }}>
      <span className="material-symbols-outlined" style={{ fontSize: 48, color: '#94a3b8', marginBottom: 16 }}>receipt_long</span>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', margin: '0 0 8px' }}>Incident Report Not Found</h2>
      <p style={{ fontSize: 13, color: '#64748b', maxWidth: 360, margin: '0 0 20px', lineHeight: 1.5 }}>
        We could not locate this incident reference code in the database. Ensure a crash SOS trigger has been registered first.
      </p>
      <Link to="/" style={{
        textDecoration: 'none', background: '#0f172a', color: '#fff',
        padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 700,
        fontFamily: 'Space Grotesk, sans-serif'
      }}>
        ← Return to Dashboard
      </Link>
    </div>
  );

  const SEV = {
    P1: { bg: '#ba1a1a', text: '#fff', label: 'CRITICAL (P1)' },
    P2: { bg: '#fca311', text: '#14213D', label: 'SERIOUS (P2)' },
    P3: { bg: '#006687', text: '#fff', label: 'MODERATE (P3)' },
    P4: { bg: '#27AE60', text: '#fff', label: 'MINOR (P4)' }
  };
  const sev = SEV[incident.severity] || { bg: 'rgba(15,23,42,0.06)', text: '#475569', label: 'PENDING' };

  return (
    <div style={{
      maxWidth: 800, margin: '0 auto', padding: '28px 16px 100px',
      background: '#f8fafc', minHeight: '100vh', fontFamily: 'Inter, sans-serif'
    }}>

      {/* Header */}
      <div style={{
        background: '#fff', borderRadius: 16, padding: '20px 24px',
        boxShadow: '0 4px 20px rgba(15,23,42,0.04)', border: '1px solid rgba(15,23,42,0.06)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 20
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Link to="/" style={{
              textDecoration: 'none', width: 36, height: 36, borderRadius: '50%',
              background: 'rgba(15,23,42,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#0f172a', transition: 'background 0.2s'
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>arrow_back</span>
            </Link>
            <div>
              <h1 style={{
                fontFamily: 'Space Grotesk, sans-serif',
                fontSize: 22, fontWeight: 800, color: '#0f172a', margin: 0
              }}>
                Crash & Incident Audit
              </h1>
              <p style={{ fontSize: 12, color: '#64748b', margin: '2px 0 0' }}>
                Incident ID: <strong style={{ color: '#0f172a' }}>{incidentId.slice(0,8).toUpperCase()}</strong>
              </p>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              style={{
                background: 'rgba(15,23,42,0.04)', border: 'none', borderRadius: 20,
                padding: '6px 14px', fontSize: 12, fontWeight: 700, color: '#0f172a',
                cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
                display: 'flex', alignItems: 'center', gap: 4
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>edit</span>
              Edit Details
            </button>
          )}
          <div style={{
            background: sev.bg, color: sev.text, padding: '8px 16px',
            borderRadius: 24, fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 12, fontWeight: 800, letterSpacing: '0.04em'
          }}>
            {sev.label}
          </div>
        </div>
      </div>

      {/* Details Sections */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        
        {/* Crash Telemetry Summary */}
        <Section icon="crisis_alert" title="Crash Telemetry Summary">
          {isEditing ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 0' }}>
              <div style={inputGroupStyle}>
                <label style={labelStyle}>Collision Spot Address</label>
                <input 
                  type="text" 
                  value={editAddress} 
                  onChange={e => setEditAddress(e.target.value)} 
                  placeholder="e.g. HAL Old Airport Road, Bengaluru"
                  style={inputStyle}
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Estimated Impact Speed (km/h)</label>
                <input 
                  type="number" 
                  value={editSpeed} 
                  onChange={e => setEditSpeed(e.target.value)} 
                  placeholder="e.g. 65"
                  style={inputStyle}
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Ambulance Responder Details</label>
                <input 
                  type="text" 
                  value={editAmbulance} 
                  onChange={e => setEditAmbulance(e.target.value)} 
                  placeholder="e.g. CATS Ambulance Unit 4"
                  style={inputStyle}
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Destination Medical Facility</label>
                <input 
                  type="text" 
                  value={editHospital} 
                  onChange={e => setEditHospital(e.target.value)} 
                  placeholder="e.g. Manipal Hospital, Bengaluru"
                  style={inputStyle}
                />
              </div>

              <div style={inputGroupStyle}>
                <label style={labelStyle}>Crash Severity Tier</label>
                <select 
                  value={editSeverity} 
                  onChange={e => setEditSeverity(e.target.value)} 
                  style={inputStyle}
                >
                  <option value="P1">Critical (P1)</option>
                  <option value="P2">Serious (P2)</option>
                  <option value="P3">Moderate (P3)</option>
                  <option value="P4">Minor (P4)</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
                <button 
                  onClick={handleSaveChanges} 
                  disabled={saving}
                  style={{
                    flex: 1, padding: '12px', borderRadius: 8, border: 'none',
                    background: '#27AE60', color: '#fff', fontSize: 13, fontWeight: 700,
                    cursor: saving ? 'default' : 'pointer', fontFamily: 'Space Grotesk, sans-serif'
                  }}
                >
                  {saving ? 'Saving...' : '✓ Save Changes'}
                </button>
                <button 
                  onClick={handleCancelEdits}
                  style={{
                    flex: 1, padding: '12px', borderRadius: 8, border: '1px solid #cbd5e1',
                    background: '#fff', color: '#475569', fontSize: 13, fontWeight: 700,
                    cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <InfoRow 
                label="Telemetry Date & Time" 
                value={incident.crash_timestamp && incident.crash_timestamp !== 'None' ? `${incident.crash_timestamp.slice(0,10)} at ${incident.crash_timestamp.slice(11,16)}` : null} 
                placeholder="Pending sensor synchronization"
              />
              <InfoRow 
                label="Incident Coordinates" 
                value={incident.latitude || incident.longitude ? `${incident.latitude?.toFixed(5)}, ${incident.longitude?.toFixed(5)}` : null} 
                placeholder="Awaiting GPS satellite lock"
              />
              <InfoRow 
                label="Accident Spot Address" 
                value={incident.address} 
                placeholder="No address logged yet (Click Edit)"
              />
              <InfoRow 
                label="Estimated Impact Speed" 
                value={incident.speed_at_impact ? `${incident.speed_at_impact} km/h` : null} 
                placeholder="No telemetry metrics registered"
              />
              <InfoRow 
                label="Assigned Responder" 
                value={incident.ambulance_name} 
                placeholder="No ambulance dispatched"
              />
              <InfoRow 
                label="Destination Facility" 
                value={incident.hospital_name} 
                placeholder="No hospital admission logged"
              />
            </div>
          )}
        </Section>

        {/* Medical Snapshot */}
        <Section icon="medical_services" title="Patient Clinical Snapshot">
          {incident.medical_profile ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <InfoRow label="Registered Patient" value={incident.medical_profile.full_name || incident.medical_profile.name} />
              <InfoRow label="Blood Type Matrix" value={incident.medical_profile.blood_type || incident.medical_profile.bloodType} />
              <InfoRow label="Emergency Allergies" value={incident.medical_profile.allergies?.join(', ')} placeholder="None reported" />
              <InfoRow label="Chronic Illness History" value={incident.medical_profile.conditions?.join(', ')} placeholder="None declared" />
              <div style={{
                marginTop: 14, background: 'rgba(42,157,143,0.08)', border: '1px solid rgba(42,157,143,0.25)',
                borderRadius: 8, padding: '10px 14px', fontSize: 11, color: '#1b4d3e',
                display: 'flex', alignItems: 'center', gap: 8
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#2A9D8F' }}>health_and_safety</span>
                <span>Synced directly from verified government DigiLocker/ABHA sandbox records.</span>
              </div>
            </div>
          ) : (
            <div style={{
              background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: 12,
              padding: '24px 16px', textAlign: 'center'
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 32, color: '#94a3b8', display: 'block', marginBottom: 8 }}>no_accounts</span>
              <p style={{ fontSize: 13, fontWeight: 700, color: '#475569', margin: '0 0 4px' }}>No Clinical ID Linked</p>
              <p style={{ fontSize: 11, color: '#64748b', margin: '0 0 14px' }}>Link your ABHA medical profile via DigiLocker to sync records instantly during dispatches.</p>
              <Link to="/medical-profile" style={{
                textDecoration: 'none', background: '#fff', border: '1px solid #cbd5e1',
                padding: '6px 16px', borderRadius: 8, fontSize: 12, fontWeight: 700,
                color: '#0f172a', display: 'inline-block'
              }}>
                Setup Medical ID
              </Link>
            </div>
          )}
        </Section>

        {/* Timeline Section */}
        <Section icon="timeline" title="Emergency Timeline Progression">
          {incident.timeline && incident.timeline.length > 0 ? (
            <div style={{ padding: '8px 4px' }}>
              <TimelineView events={incident.timeline} />
            </div>
          ) : (
            <div style={{
              background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: 12,
              padding: '32px 16px', textAlign: 'center'
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 32, color: '#94a3b8', display: 'block', marginBottom: 8 }}>hourglass_empty</span>
              <p style={{ fontSize: 13, fontWeight: 700, color: '#475569', margin: '0 0 4px' }}>No Incident Logs Active</p>
              <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>Timeline metrics will update dynamically when active SOS dispatches are triggered.</p>
            </div>
          )}
        </Section>

        {/* Photos evidence */}
        <Section icon="photo_camera" title="Photographic Collision Evidence">
          <p style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
            Attach high-resolution photos of vehicle damage, road indicators, or surroundings. These will be bound directly to your insurance audit PDF.
          </p>
          <PhotoUploader
            incidentId={incidentId}
            existingPhotos={incident.photo_urls || []}
            onUploadSuccess={photos => setIncident(prev => ({ ...prev, photo_urls: photos }))}
          />
        </Section>

        {/* Police FIR guide */}
        <Section icon="gavel" title="First Information Report (FIR) Legal Portal">
          <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, marginBottom: 16 }}>
            Below is your dynamic legal filing pathway for your local jurisdiction (**{incident.fir_state || 'Karnataka State'}**). Follow these instructions to lodge an official report.
          </p>
          
          {!showFIR ? (
            <button
              onClick={loadFIRGuide}
              style={{
                padding: '12px 24px', borderRadius: 10, border: '1px solid #cbd5e1',
                background: '#fff', color: '#0f172a', fontWeight: 700, fontSize: 13,
                cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
                display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s'
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>gavel</span>
              Access Step-by-Step FIR Protocol
            </button>
          ) : firGuide && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, animation: 'fadeIn 0.3s ease-out' }}>
              {firGuide.steps.map(step => (
                <div key={step.step_number} style={{
                  background: '#fff', borderRadius: 12, padding: '16px 18px',
                  border: '1px solid rgba(15,23,42,0.08)',
                  boxShadow: '0 2px 8px rgba(15,23,42,0.02)',
                  borderLeft: '4px solid #14213D'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifycontent: 'space-between', marginBottom: 6 }}>
                    <h4 style={{ fontSize: 14, fontWeight: 800, color: '#0f172a', margin: 0 }}>
                      Step {step.step_number}: {step.title}
                    </h4>
                    <span style={{
                      background: 'rgba(15,23,42,0.05)', padding: '2px 8px', borderRadius: 12,
                      fontSize: 10, fontWeight: 700, color: '#475569'
                    }}>
                      ACTION
                    </span>
                  </div>
                  <p style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.5, margin: '0 0 10px' }}>
                    {step.description}
                  </p>
                  {step.documents?.length > 0 && (
                    <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 8, marginBottom: 8 }}>
                      <p style={{ fontSize: 11, fontWeight: 700, color: '#475569', margin: '0 0 4px' }}>
                        REQUIRED DOCUMENTATION:
                      </p>
                      {step.documents.map((d, i) => (
                        <p key={i} style={{ fontSize: 11.5, color: '#334155', margin: '2px 0 0', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ color: '#27AE60', fontWeight: 'bold' }}>✓</span> {d}
                        </p>
                      ))}
                    </div>
                  )}
                  {step.tip && (
                    <p style={{ fontSize: 11, color: '#006687', margin: '6px 0 0', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14 }}>info</span>
                      {step.tip}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

      {/* Sticky PDF actions */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: '#fff', borderTop: '1px solid rgba(15,23,42,0.08)',
        padding: '14px 20px', display: 'flex', gap: 12, zIndex: 100,
        boxShadow: '0 -4px 20px rgba(15,23,42,0.05)'
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto', width: '100%', display: 'flex', gap: 12 }}>
          {!pdfReady && !incident.pdf_url ? (
            <button
              onClick={generatePDF}
              disabled={genPDF}
              style={{
                flex: 1, padding: '14px', borderRadius: 10, border: 'none',
                background: genPDF ? '#cbd5e1' : '#14213D', color: '#fff',
                fontSize: 14, fontWeight: 800, cursor: genPDF ? 'default' : 'pointer',
                fontFamily: 'Space Grotesk, sans-serif',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                transition: 'all 0.2s'
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>picture_as_pdf</span>
              {genPDF ? 'Compiling PDF matrices…' : 'Generate Verified Audit Report PDF'}
            </button>
          ) : (
            <>
              <button
                onClick={downloadPDF}
                style={{
                  ...primaryBtn, flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>download</span>
                Download Official PDF
              </button>
              <button
                onClick={sharePDF}
                style={{
                  ...secBtn, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>share</span>
                Share Link
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ icon, title, children }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 16, padding: '20px 24px',
      marginBottom: 16, border: '1px solid rgba(15,23,42,0.06)',
      boxShadow: '0 4px 16px rgba(15,23,42,0.02)'
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        marginBottom: 16, paddingBottom: 10, borderBottom: '1px solid rgba(15,23,42,0.06)'
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%', background: 'rgba(252,163,17,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <span className="material-symbols-outlined icon-fill"
            style={{ fontSize: 18, color: '#fca311' }}>{icon}</span>
        </div>
        <p style={{
          fontFamily: 'Space Grotesk, sans-serif', fontSize: 15,
          fontWeight: 800, color: '#0f172a', margin: 0
        }}>{title}</p>
      </div>
      {children}
    </div>
  );
}

function InfoRow({ label, value, placeholder = '—' }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px 0', borderBottom: '1px solid rgba(15,23,42,0.04)', gap: 24
    }}>
      <span style={{ fontSize: 12.5, fontWeight: 600, color: '#64748b', flexShrink: 0 }}>{label}</span>
      {value ? (
        <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b', textAlign: 'right' }}>{value}</span>
      ) : (
        <span style={{ fontSize: 12, fontWeight: 500, color: '#94a3b8', fontStyle: 'italic', textAlign: 'right' }}>
          {placeholder}
        </span>
      )}
    </div>
  );
}

const inputGroupStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6
};

const labelStyle = {
  fontSize: 12,
  fontWeight: 700,
  color: '#475569',
  fontFamily: 'Space Grotesk, sans-serif'
};

const inputStyle = {
  padding: '10px 14px',
  borderRadius: 8,
  border: '1px solid #cbd5e1',
  background: '#fff',
  fontSize: 13,
  color: '#0f172a',
  fontFamily: 'Inter, sans-serif',
  outline: 'none'
};

const primaryBtn = {
  flex: 1, padding: '14px', borderRadius: 10, border: 'none',
  background: '#14213D', color: '#fff', fontSize: 13.5, fontWeight: 800,
  cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
};
const secBtn = {
  flex: 1, padding: '14px', borderRadius: 10,
  border: '1px solid #cbd5e1', background: '#fff',
  color: '#1e293b', fontSize: 13.5, fontWeight: 700,
  cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
};
