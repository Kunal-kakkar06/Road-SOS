import React, { useState, useEffect, useRef } from 'react';
import { submitAsyncTriage, getTriageJobStatus, uploadTriageImage, uploadTriageVoice } from '../services/triageService';
import { triggerSOS } from '../services/offlineSOS';

export default function TriageAssistant({ isOpen, onClose, onStartVoiceGuidance }) {
  // Form fields
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('Male');
  const [symptoms, setSymptoms] = useState('');
  const [consciousness, setConsciousness] = useState('Alert');
  const [breathing, setBreathing] = useState('Normal');
  const [imageLabel, setImageLabel] = useState('');
  const [voiceTranscript, setVoiceTranscript] = useState('');

  // UI States
  const [loading, setLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState('');
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [isRecordingVoice, setIsRecordingVoice] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // SOS Auto-trigger Confirmation States
  const [showSosConfirm, setShowSosConfirm] = useState(false);
  const [sosCountdown, setSosCountdown] = useState(5);
  const [sosTriggeredStatus, setSosTriggeredStatus] = useState(null); // 'sending' | 'success' | 'failed'

  const recordingIntervalRef = useRef(null);
  const countdownIntervalRef = useRef(null);

  // Reset form
  const handleReset = () => {
    setAge('');
    setGender('Male');
    setSymptoms('');
    setConsciousness('Alert');
    setBreathing('Normal');
    setImageLabel('');
    setVoiceTranscript('');
    setResult(null);
    setError(null);
    setShowSosConfirm(false);
    setSosTriggeredStatus(null);
    setPollingStatus('');
  };

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  const pollingIntervalRef = useRef(null);

  // Handle Voice Record Mock
  const handleRecordVoice = async () => {
    if (isRecordingVoice) return;
    setIsRecordingVoice(true);
    setRecordingSeconds(3);

    recordingIntervalRef.current = setInterval(() => {
      setRecordingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(recordingIntervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Mock 3 second delay then fetch stub
    setTimeout(async () => {
      try {
        const res = await uploadTriageVoice(null);
        setVoiceTranscript(res.transcript);
      } catch (err) {
        setVoiceTranscript('I need urgent help, chest pain and breathing issues.');
      } finally {
        setIsRecordingVoice(false);
      }
    }, 3000);
  };

  // Handle Image Upload Mock
  const handleImageChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploadingImage(true);
    try {
      const res = await uploadTriageImage(file);
      setImageLabel(`${res.label} (${Math.round(res.confidence * 100)}% confidence)`);
    } catch (err) {
      setImageLabel('Visible laceration/trauma detected');
    } finally {
      setIsUploadingImage(false);
    }
  };

  // Handle Form Submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPollingStatus('Submitting...');

    const payload = {
      age: age ? parseInt(age, 10) : null,
      gender,
      symptoms,
      consciousness,
      breathing,
      image_label: imageLabel || null,
      voice_transcript: voiceTranscript || null,
    };

    try {
      const { job_id } = await submitAsyncTriage(payload);
      setPollingStatus('Processing...');

      let attempts = 0;
      const maxAttempts = 30; // 30 seconds max polling

      pollingIntervalRef.current = setInterval(async () => {
        attempts++;
        if (attempts >= maxAttempts) {
          clearInterval(pollingIntervalRef.current);
          setLoading(false);
          setPollingStatus('');
          setError('Triage assessment timed out. Please try again.');
          return;
        }

        try {
          const statusRes = await getTriageJobStatus(job_id);
          if (statusRes.status === 'completed') {
            clearInterval(pollingIntervalRef.current);
            setResult(statusRes.result);
            setLoading(false);
            setPollingStatus('');

            if (statusRes.result.severity_level === 'Critical') {
              setShowSosConfirm(true);
              setSosCountdown(5);
              startSosCountdown(statusRes.result.assessment);
            }
          } else if (statusRes.status === 'failed') {
            clearInterval(pollingIntervalRef.current);
            setLoading(false);
            setPollingStatus('');
            setError(statusRes.error || 'Triage processing failed.');
          }
        } catch (pollErr) {
          console.warn("Polling error:", pollErr);
          // Don't fail immediately on network blips, keep trying until maxAttempts
        }
      }, 1000);

    } catch (err) {
      setError(err.message || 'Something went wrong. Please check your network.');
      setLoading(false);
      setPollingStatus('');
    }
  };

  // Start countdown for SOS auto-trigger
  const startSosCountdown = (assessmentText) => {
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    
    let currentCount = 5;
    countdownIntervalRef.current = setInterval(() => {
      currentCount--;
      setSosCountdown(currentCount);
      if (currentCount <= 0) {
        clearInterval(countdownIntervalRef.current);
        executeSosTrigger(assessmentText);
      }
    }, 1000);
  };

  // Cancel SOS auto-trigger
  const cancelSosTrigger = () => {
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    setShowSosConfirm(false);
  };

  // Fire SOS flow
  const executeSosTrigger = async (assessmentText) => {
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    setShowSosConfirm(false);
    setSosTriggeredStatus('sending');

    try {
      // Backup original medicalProfile
      const originalProfileStr = localStorage.getItem('medicalProfile');
      const profile = originalProfileStr ? JSON.parse(originalProfileStr) : {};

      // Append assessment to conditions
      const updatedProfile = {
        ...profile,
        conditions: [...(profile.conditions || []), `AI Triage: ${assessmentText}`],
      };
      localStorage.setItem('medicalProfile', JSON.stringify(updatedProfile));

      // Trigger standard SOS
      const result = await triggerSOS();
      setSosTriggeredStatus('success');

      // Restore profile
      if (originalProfileStr) {
        localStorage.setItem('medicalProfile', originalProfileStr);
      } else {
        localStorage.removeItem('medicalProfile');
      }
    } catch (err) {
      setSosTriggeredStatus('failed');
    }
  };

  if (!isOpen) return null;

  // Circular progress math
  const score = result ? result.severity_score : 0;
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Dynamic Color
  const getSeverityColor = (level) => {
    switch (level) {
      case 'Critical': return '#E63946';
      case 'High': return '#F4A261';
      case 'Moderate': return '#E9C46A';
      default: return '#2A9D8F';
    }
  };

  const severityColor = result ? getSeverityColor(result.severity_level) : '#ccc';

  return (
    <div style={modalOverlay}>
      <div style={modalCard}>
        {/* Header */}
        <div style={modalHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="material-symbols-outlined" style={{ color: '#fca311', fontSize: 28 }}>
              medical_services
            </span>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#fff', fontFamily: 'Space Grotesk, sans-serif' }}>
              AI Triage Assistant
            </h2>
          </div>
          <button onClick={onClose} style={closeBtn}>
            <span className="material-symbols-outlined" style={{ fontSize: 24 }}>close</span>
          </button>
        </div>

        {/* Content Body */}
        <div style={modalBody}>
          {error && (
            <div style={errorBanner}>
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>error</span>
              <span>{error}</span>
            </div>
          )}

          {sosTriggeredStatus && (
            <div style={{
              ...sosAlertBanner,
              background: sosTriggeredStatus === 'success' ? '#2A9D8F' : sosTriggeredStatus === 'failed' ? '#E63946' : '#14213D'
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 24, animation: 'spin 2s linear infinite' }}>
                {sosTriggeredStatus === 'sending' ? 'sync' : sosTriggeredStatus === 'success' ? 'check_circle' : 'error'}
              </span>
              <div>
                <strong style={{ display: 'block' }}>
                  {sosTriggeredStatus === 'sending' ? 'Triggering Emergency SOS...' : 
                   sosTriggeredStatus === 'success' ? 'SOS Triggered Successfully!' : 
                   'Failed to auto-trigger SOS.'}
                </strong>
                <span style={{ fontSize: 12 }}>
                  {sosTriggeredStatus === 'sending' ? 'Contacting emergency services and sending SMS alert...' :
                   sosTriggeredStatus === 'success' ? 'Paramedics and your emergency contacts have been notified.' :
                   'Please manually press the main SOS button.'}
                </span>
              </div>
            </div>
          )}

          {!result && !loading && (
            <form onSubmit={handleSubmit} style={formStyle}>
              <p style={{ margin: '0 0 16px', fontSize: 13, color: '#a0aab2' }}>
                Fill out the diagnostic form below or use our AI Voice & Photo tools to assess the patient's condition.
              </p>

              {/* Form Grid */}
              <div style={formRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Age</label>
                  <input
                    type="number"
                    required
                    placeholder="e.g. 34"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Gender</label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    style={inputStyle}
                  >
                    <option>Male</option>
                    <option>Female</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>

              {/* Symptoms Input */}
              <div>
                <label style={labelStyle}>Describe Symptoms / Incident</label>
                <textarea
                  required
                  placeholder="Describe patient's current symptoms, injuries, pain level, or cause of accident..."
                  value={symptoms}
                  onChange={(e) => setSymptoms(e.target.value)}
                  style={{ ...inputStyle, height: 90, resize: 'none' }}
                />
              </div>

              {/* Dropdowns */}
              <div style={formRow}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Consciousness Level</label>
                  <select
                    value={consciousness}
                    onChange={(e) => setConsciousness(e.target.value)}
                    style={inputStyle}
                  >
                    <option>Alert</option>
                    <option>Voice Response</option>
                    <option>Pain Response</option>
                    <option>Unresponsive</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Breathing Pattern</label>
                  <select
                    value={breathing}
                    onChange={(e) => setBreathing(e.target.value)}
                    style={inputStyle}
                  >
                    <option>Normal</option>
                    <option>Labored</option>
                    <option>Rapid</option>
                    <option>Absent</option>
                  </select>
                </div>
              </div>

              {/* Uploads and Stubs Grid */}
              <div style={formRow}>
                {/* Voice Stub */}
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Voice Note (AI Transcript)</label>
                  <button
                    type="button"
                    onClick={handleRecordVoice}
                    disabled={isRecordingVoice}
                    style={{
                      ...stubBtn,
                      border: isRecordingVoice ? '1px solid #e63946' : '1px solid rgba(255,255,255,0.1)'
                    }}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 18, color: isRecordingVoice ? '#e63946' : '#fca311' }}>
                      {isRecordingVoice ? 'fiber_manual_record' : 'mic'}
                    </span>
                    <span>
                      {isRecordingVoice ? `Recording... (${recordingSeconds}s)` : voiceTranscript ? 'Re-record Voice' : 'Record Voice (Stub)'}
                    </span>
                  </button>
                  {voiceTranscript && (
                    <div style={transcriptBox}>
                      <strong>AI Transcript:</strong> "{voiceTranscript}"
                    </div>
                  )}
                </div>

                {/* Photo Stub */}
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Injury Photo (AI Scanner)</label>
                  <label style={stubBtn}>
                    <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#fca311' }}>
                      upload_file
                    </span>
                    <span>{isUploadingImage ? 'Scanning Image...' : imageLabel ? 'Change Image' : 'Scan Image (Stub)'}</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageChange}
                      style={{ display: 'none' }}
                      disabled={isUploadingImage}
                    />
                  </label>
                  {imageLabel && (
                    <div style={transcriptBox}>
                      <strong>AI Image Tag:</strong> {imageLabel}
                    </div>
                  )}
                </div>
              </div>

              {/* Submit Form */}
              <button type="submit" style={submitBtn}>
                Run Diagnostic Assessment
              </button>
            </form>
          )}

          {/* Loading State */}
          {loading && (
            <div style={loadingContainer}>
              <div style={spinnerStyle}></div>
              <p style={{ fontWeight: 600, margin: '16px 0 4px' }}>{pollingStatus || 'Analyzing Medical Telemetry...'}</p>
              <p style={{ fontSize: 12, color: '#a0aab2' }}>Claude Clinical Model evaluating severity indicators</p>
            </div>
          )}

          {/* Results Screen */}
          {result && !loading && (
            <div style={resultStyle}>
              {/* Circular score ring & severity badge */}
              <div style={resultHeaderSection}>
                <div style={scoreRingContainer}>
                  <svg width="110" height="110" style={{ transform: 'rotate(-90deg)' }}>
                    <circle cx="55" cy="55" r={radius} fill="transparent" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                    <circle
                      cx="55"
                      cy="55"
                      r={radius}
                      fill="transparent"
                      stroke={severityColor}
                      strokeWidth="8"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                      style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
                    />
                  </svg>
                  <div style={scoreTextContainer}>
                    <span style={{ fontSize: 24, fontWeight: 800, color: '#fff' }}>{result.severity_score}</span>
                    <span style={{ fontSize: 9, textTransform: 'uppercase', color: '#a0aab2' }}>Severity</span>
                  </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ ...badgeStyle, background: severityColor }}>
                      {result.severity_level} Level
                    </span>
                    <span style={etaBadge}>
                      ETA: {result.eta_minutes} mins
                    </span>
                  </div>
                  <h3 style={{ margin: '4px 0 0', fontSize: 16, fontWeight: 700, color: '#fff' }}>Diagnostic Report</h3>
                  <p style={{ margin: 0, fontSize: 13, lineHeight: '1.4', color: '#cbd5e1' }}>
                    {result.assessment}
                  </p>
                </div>
              </div>

              {/* Symptom Tags */}
              <div style={sectionBox}>
                <h4 style={sectionTitle}>Extracted Symptoms</h4>
                <div style={tagContainer}>
                  {result.symptoms_extracted.map((tag, idx) => (
                    <span key={idx} style={tagStyle}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Numbered First Aid Actions */}
              <div style={sectionBox}>
                <h4 style={sectionTitle}>Recommended First Aid Actions</h4>
                <ol style={listStyle}>
                  {result.actions.map((act, idx) => (
                    <li key={idx} style={listItemStyle}>
                      <span style={{ fontWeight: 700, color: '#fca311' }}>{idx + 1}. </span>
                      {act}
                    </li>
                  ))}
                </ol>
              </div>

              {/* SHAP Explainability Bars */}
              <div style={sectionBox}>
                <h4 style={sectionTitle}>AI Factor Contribution (SHAP Explainability)</h4>
                <p style={{ fontSize: 11, color: '#a0aab2', margin: '-4px 0 12px' }}>
                  Features driving the classification (higher values indicate positive impact on severity)
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {Object.entries(result.shap_values).map(([key, val]) => {
                    const maxVal = 50;
                    const percentage = Math.min((Math.abs(val) / maxVal) * 100, 100);
                    const isPositive = val >= 0;

                    return (
                      <div key={key} style={shapRow}>
                        <span style={shapLabel}>{key}</span>
                        <div style={shapTrack}>
                          <div style={{
                            ...shapFill,
                            width: `${percentage}%`,
                            background: isPositive ? '#E63946' : '#2A9D8F',
                            marginLeft: isPositive ? '0' : 'auto',
                          }} />
                        </div>
                        <span style={{ ...shapValue, color: isPositive ? '#E63946' : '#2A9D8F' }}>
                          {isPositive ? `+${val.toFixed(1)}` : val.toFixed(1)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Actions Footer */}
              <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
                <button onClick={onStartVoiceGuidance} style={{ ...resetBtn, background: '#fca311', color: '#14213D', flex: 1 }}>
                  Get Voice Guidance
                </button>
                <button onClick={handleReset} style={{ ...resetBtn, flex: 1 }}>
                  New Patient
                </button>
                <button onClick={onClose} style={{ ...closePanelBtn, flex: 1 }}>
                  Return
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Auto-Trigger SOS confirmation Modal Overlay */}
      {showSosConfirm && (
        <div style={confirmOverlay}>
          <div style={confirmCard}>
            <span className="material-symbols-outlined" style={{ fontSize: 64, color: '#E63946', animation: 'pulse 1.5s infinite' }}>
              warning
            </span>
            <h3 style={{ margin: '12px 0 8px', fontSize: 20, fontWeight: 800, color: '#fff' }}>
              CRITICAL EMERGENCY DETECTED
            </h3>
            <p style={{ margin: 0, fontSize: 14, color: '#cbd5e1', textAlign: 'center', lineHeight: '1.5' }}>
              AI triage has evaluated this incident as <strong>CRITICAL</strong>. 
              The system will automatically trigger a main SOS event in <strong>{sosCountdown}s</strong>.
            </p>
            <div style={confirmAssessmentBox}>
              "{result?.assessment}"
            </div>
            <div style={{ display: 'flex', gap: 12, width: '100%', marginTop: 8 }}>
              <button onClick={cancelSosTrigger} style={cancelSosBtn}>
                CANCEL AUTO-SOS
              </button>
              <button onClick={() => executeSosTrigger(result?.assessment)} style={confirmSosBtn}>
                SEND SOS NOW
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── CSS STYLES ────────────────────────────────────────────────

const modalOverlay = {
  position: 'fixed',
  top: 0, left: 0, right: 0, bottom: 0,
  background: 'rgba(10, 17, 30, 0.85)',
  backdropFilter: 'blur(8px)',
  zIndex: 1000,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 16,
};

const modalCard = {
  background: '#14213D',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  borderRadius: 16,
  width: '100%',
  maxWidth: 580,
  maxHeight: '90vh',
  display: 'flex',
  flexDirection: 'column',
  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
  color: '#fff',
  fontFamily: 'Inter, sans-serif',
  overflow: 'hidden',
};

const modalHeader = {
  padding: '16px 20px',
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};

const closeBtn = {
  background: 'transparent',
  border: 'none',
  color: '#a0aab2',
  cursor: 'pointer',
  padding: 4,
  display: 'flex',
  alignItems: 'center',
  borderRadius: '50%',
  transition: 'background 0.2s',
  ':hover': {
    background: 'rgba(255,255,255,0.06)',
    color: '#fff',
  }
};

const modalBody = {
  padding: 24,
  overflowY: 'auto',
  flex: 1,
};

const formStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
};

const formRow = {
  display: 'flex',
  gap: 16,
};

const labelStyle = {
  display: 'block',
  fontSize: 12,
  fontWeight: 600,
  color: '#cbd5e1',
  marginBottom: 6,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const inputStyle = {
  width: '100%',
  padding: '12px 14px',
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: 8,
  color: '#fff',
  fontSize: 14,
  fontFamily: 'Inter, sans-serif',
  outline: 'none',
  transition: 'border-color 0.2s',
  boxSizing: 'border-box',
};

const stubBtn = {
  width: '100%',
  padding: '12px 14px',
  background: 'rgba(255, 255, 255, 0.04)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: 8,
  color: '#fff',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
  transition: 'background 0.2s, border-color 0.2s',
};

const transcriptBox = {
  marginTop: 8,
  padding: '8px 12px',
  background: 'rgba(252, 163, 17, 0.1)',
  borderLeft: '3px solid #fca311',
  borderRadius: '0 6px 6px 0',
  fontSize: 12,
  color: '#fca311',
  lineHeight: '1.4',
};

const submitBtn = {
  marginTop: 8,
  padding: '14px 20px',
  background: '#fca311',
  color: '#14213D',
  border: 'none',
  borderRadius: 8,
  fontSize: 15,
  fontWeight: 700,
  cursor: 'pointer',
  fontFamily: 'Space Grotesk, sans-serif',
  transition: 'transform 0.1s, opacity 0.2s',
};

const errorBanner = {
  padding: '12px 16px',
  background: 'rgba(230, 57, 70, 0.15)',
  border: '1px solid #E63946',
  borderRadius: 8,
  color: '#ff8a93',
  fontSize: 13,
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  marginBottom: 16,
};

const loadingContainer = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '40px 20px',
  color: '#fff',
};

const spinnerStyle = {
  width: 40,
  height: 40,
  border: '4px solid rgba(255,255,255,0.1)',
  borderTop: '4px solid #fca311',
  borderRadius: '50%',
  animation: 'spin 1s linear infinite',
};

const resultStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: 20,
};

const resultHeaderSection = {
  display: 'flex',
  alignItems: 'center',
  gap: 20,
  background: 'rgba(255, 255, 255, 0.03)',
  padding: 16,
  borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.06)',
};

const scoreRingContainer = {
  position: 'relative',
  width: 110,
  height: 110,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const scoreTextContainer = {
  position: 'absolute',
  top: 0, left: 0, right: 0, bottom: 0,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
};

const badgeStyle = {
  padding: '4px 10px',
  borderRadius: 20,
  fontSize: 11,
  fontWeight: 800,
  textTransform: 'uppercase',
  color: '#14213D',
};

const etaBadge = {
  padding: '4px 10px',
  borderRadius: 20,
  fontSize: 11,
  fontWeight: 700,
  background: 'rgba(255,255,255,0.08)',
  border: '1px solid rgba(255,255,255,0.1)',
  color: '#a0aab2',
};

const sectionBox = {
  background: 'rgba(255, 255, 255, 0.02)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
  borderRadius: 10,
  padding: 16,
};

const sectionTitle = {
  margin: '0 0 12px',
  fontSize: 12,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: '#fca311',
};

const tagContainer = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const tagStyle = {
  padding: '6px 12px',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 6,
  fontSize: 12,
  color: '#cbd5e1',
};

const listStyle = {
  margin: 0,
  padding: 0,
  listStyle: 'none',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
};

const listItemStyle = {
  fontSize: 13,
  lineHeight: '1.4',
  color: '#cbd5e1',
};

const shapRow = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  fontSize: 12,
};

const shapLabel = {
  width: 100,
  fontWeight: 600,
  color: '#cbd5e1',
  textTransform: 'capitalize',
};

const shapTrack = {
  flex: 1,
  height: 8,
  background: 'rgba(255, 255, 255, 0.05)',
  borderRadius: 4,
  overflow: 'hidden',
  display: 'flex',
};

const shapFill = {
  height: '100%',
  borderRadius: 4,
  transition: 'width 0.8s ease-in-out',
};

const shapValue = {
  width: 45,
  textAlign: 'right',
  fontWeight: 700,
};

const resetBtn = {
  flex: 1,
  padding: '12px 16px',
  background: 'rgba(255, 255, 255, 0.06)',
  color: '#fff',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: 8,
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'background 0.2s',
};

const closePanelBtn = {
  flex: 1,
  padding: '12px 16px',
  background: '#fca311',
  color: '#14213D',
  border: 'none',
  borderRadius: 8,
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
  fontFamily: 'Space Grotesk, sans-serif',
};

// Auto-SOS confirm styles
const confirmOverlay = {
  position: 'absolute',
  top: 0, left: 0, right: 0, bottom: 0,
  background: 'rgba(10, 17, 30, 0.93)',
  backdropFilter: 'blur(4px)',
  zIndex: 1100,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 20,
};

const confirmCard = {
  background: '#1d1b26',
  border: '2px solid #E63946',
  borderRadius: 16,
  width: '100%',
  maxWidth: 420,
  padding: 24,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  boxShadow: '0 25px 50px rgba(0, 0, 0, 0.8), 0 0 20px rgba(230, 57, 70, 0.2)',
};

const confirmAssessmentBox = {
  width: '100%',
  margin: '16px 0',
  padding: 12,
  background: 'rgba(255, 255, 255, 0.04)',
  borderRadius: 8,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  fontSize: 12,
  color: '#a0aab2',
  textAlign: 'center',
  fontStyle: 'italic',
  lineHeight: '1.4',
  boxSizing: 'border-box',
};

const cancelSosBtn = {
  flex: 1,
  padding: '12px 14px',
  background: 'rgba(255, 255, 255, 0.06)',
  color: '#fff',
  border: '1px solid rgba(255, 255, 255, 0.15)',
  borderRadius: 8,
  fontSize: 12,
  fontWeight: 700,
  cursor: 'pointer',
};

const confirmSosBtn = {
  flex: 1,
  padding: '12px 14px',
  background: '#E63946',
  color: '#fff',
  border: 'none',
  borderRadius: 8,
  fontSize: 12,
  fontWeight: 700,
  cursor: 'pointer',
};

const sosAlertBanner = {
  padding: '14px 18px',
  borderRadius: 10,
  display: 'flex',
  alignItems: 'center',
  gap: 14,
  marginBottom: 20,
  border: '1px solid rgba(255,255,255,0.1)',
  animation: 'slideDown 0.3s ease-out',
};
