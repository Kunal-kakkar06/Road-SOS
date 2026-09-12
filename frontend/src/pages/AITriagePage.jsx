import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { runTriage } from '../services/triageService';
import SeverityResult from '../components/SeverityResult';
import PhotoCapture   from '../components/PhotoCapture';

const API_BASE = import.meta.env.VITE_API_URL || '';

/* ── Shared card style ─────────────────────────────────────── */
const card = {
  background: '#fff', borderRadius: 12,
  padding: '16px 18px', marginBottom: 12,
  border: '0.5px solid rgba(0,0,0,0.1)',
};

/* ── Section header sub-component ──────────────────────────── */
function SectionHead({ icon, title, badge, badgeColor = '#534433' }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      marginBottom: 12, paddingBottom: 10,
      borderBottom: '1px solid #f0e0d1',
    }}>
      <span
        className="material-symbols-outlined icon-fill"
        style={{ fontSize: 18, color: '#14213D' }}
      >
        {icon}
      </span>
      <p style={{
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 14,
        fontWeight: 600, color: '#14213D', margin: 0, flex: 1,
      }}>
        {title}
      </p>
      {badge && (
        <span style={{ fontSize: 11, color: badgeColor, fontWeight: 700 }}>
          {badge}
        </span>
      )}
    </div>
  );
}

/* ── Yes/No toggle sub-component ────────────────────────────── */
function YesNo({ label, value, onChange }) {
  return (
    <div>
      <p style={{ fontSize: 12, fontWeight: 600, color: '#534433', marginBottom: 7 }}>
        {label}
      </p>
      <div style={{ display: 'flex', gap: 8 }}>
        {[['Yes', true], ['No', false]].map(([l, v]) => (
          <button
            key={l}
            onClick={() => onChange(v)}
            style={{
              flex: 1, padding: '10px', borderRadius: 8, border: 'none',
              cursor: 'pointer', fontWeight: 600, fontSize: 13,
              fontFamily: 'Inter, sans-serif',
              background: value === v ? '#14213D' : '#f0e0d1',
              color:      value === v ? '#fff'    : '#221a11',
              transition: 'all .15s',
            }}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   MAIN PAGE
   ══════════════════════════════════════════════════════════════ */
export default function AITriagePage() {
  const navigate = useNavigate();

  /* ── State ─────────────────────────────────────────────────── */
  const [phase,      setPhase]      = useState('input');   // input | analysing | result
  const [result,     setResult]     = useState(null);
  const [imageFile,  setImageFile]  = useState(null);
  const [audioBlob,  setAudioBlob]  = useState(null);
  const [textInput,  setTextInput]  = useState('');
  const [recording,  setRecording]  = useState(false);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [isOnline,   setIsOnline]   = useState(navigator.onLine);
  const [showManual, setShowManual] = useState(false);
  const [manual,     setManual]     = useState({
    conscious: true, visible_bleeding: false,
    can_move:  true, pain_level: 5, speed_at_crash: '',
  });

  /* ── Refs ───────────────────────────────────────────────────── */
  const mediaRef  = useRef(null);
  const chunksRef = useRef([]);

  /* ── Auto-load crash sensor data from localStorage ─────────── */
  const sensorData = (() => {
    try {
      return JSON.parse(localStorage.getItem('lastCrashData') || 'null');
    } catch { return null; }
  })();

  const incidentId = localStorage.getItem('currentIncidentId');
  const profile    = (() => {
    try { return JSON.parse(localStorage.getItem('medicalProfile') || '{}'); }
    catch { return {}; }
  })();

  /* ── Online/offline detection ──────────────────────────────── */
  useEffect(() => {
    const on  = () => setIsOnline(true);
    const off = () => setIsOnline(false);
    window.addEventListener('online',  on);
    window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);

  /* ── Voice recording ───────────────────────────────────────── */
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRef.current  = new MediaRecorder(stream);
      chunksRef.current = [];
      mediaRef.current.ondataavailable = e => chunksRef.current.push(e.data);
      mediaRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        setIsProcessingAudio(false);
        stream.getTracks().forEach(t => t.stop());
      };
      mediaRef.current.start();
      setRecording(true);
    } catch {
      alert('Microphone access denied. Please allow microphone access in browser settings.');
    }
  };

  const stopRecording = () => {
    if (mediaRef.current && mediaRef.current.state !== 'inactive') {
      try {
        setIsProcessingAudio(true);
        mediaRef.current.stop();
      } catch (err) {
        console.error("Error stopping recorder:", err);
        setIsProcessingAudio(false);
      }
    }
    setRecording(false);
  };

  /* ── Run triage ─────────────────────────────────────────────── */
  const analyse = async () => {
    setPhase('analysing');
    try {
      const res = await runTriage({
        imageFile,
        audioBlob,
        sensorData,
        textInput:     textInput.trim() || null,
        manualAnswers: showManual ? {
          ...manual,
          speed_at_crash: manual.speed_at_crash ? parseFloat(manual.speed_at_crash) : null,
        } : null,
        incidentId,
        userId: profile.userId,
      });

      setResult(res);
      setPhase('result');

      // Auto-log to incident timeline
      if (incidentId && navigator.onLine && res.event_id) {
        fetch(`${API_BASE}/api/incident/${incidentId}/event`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_id:  incidentId,
            event_type:   'triage_completed',
            description:  `AI Triage: ${res.severity} — ${res.severity_label}`,
            metadata:     { triage_event_id: res.event_id, severity: res.severity },
          }),
        }).catch(() => {});
      }
    } catch {
      alert('Triage failed. Please try the manual assessment.');
      setPhase('input');
    }
  };

  const hasAnyInput = imageFile || audioBlob || textInput.trim() || showManual || !isOnline;
  const canAnalyse = hasAnyInput && !isProcessingAudio;

  /* ══ RESULT VIEW ════════════════════════════════════════════ */
  if (phase === 'result' && result) {
    return (
      <div style={{
        maxWidth: 800, margin: '0 auto',
        padding: '24px 16px 80px',
        background: '#E5E5E5', minHeight: '100vh',
      }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#534433', fontSize: 13, fontWeight: 600,
            fontFamily: 'Inter, sans-serif', marginBottom: 16, padding: 0,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_back</span>
          Back
        </button>

        <SeverityResult
          result={result}
          onRetry={() => {
            setPhase('input');
            setResult(null);
            setImageFile(null);
            setAudioBlob(null);
            setTextInput('');
          }}
        />
      </div>
    );
  }

  /* ══ ANALYSING VIEW ════════════════════════════════════════ */
  if (phase === 'analysing') {
    const inputDesc =
      imageFile && audioBlob ? 'Running image + voice AI analysis' :
      imageFile              ? 'Analysing injury photo…'           :
      audioBlob              ? 'Processing voice description…'     :
      sensorData             ? 'Fusing crash sensor data…'         :
                               'Running severity assessment…';

    return (
      <div style={{
        maxWidth: 800, margin: '0 auto',
        padding: '80px 16px', background: '#E5E5E5',
        minHeight: '100vh', textAlign: 'center',
      }}>
        <div style={{
          width: 80, height: 80, borderRadius: '50%',
          background: '#fff', margin: '0 auto 20px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '2px solid rgba(0,0,0,0.08)',
          animation: 'spin 2s linear infinite',
        }}>
          <span
            className="material-symbols-outlined icon-fill"
            style={{ fontSize: 40, color: '#14213D' }}
          >
            psychology
          </span>
        </div>
        <p style={{
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: 20, fontWeight: 700, color: '#14213D', marginBottom: 8,
        }}>
          Analysing injury severity…
        </p>
        <p style={{ fontSize: 13, color: '#534433' }}>{inputDesc}</p>

        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to   { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  /* ══ INPUT VIEW ════════════════════════════════════════════ */
  return (
    <div style={{
      maxWidth: 800, margin: '0 auto',
      padding: '20px 16px 100px',
      background: '#E5E5E5', minHeight: '100vh',
    }}>

      {/* ── Offline banner ──────────────────────────────────── */}
      {!isOnline && (
        <div style={{
          background: '#FAEEDA', borderRadius: 10,
          padding: '10px 14px', marginBottom: 14,
          display: 'flex', alignItems: 'center', gap: 10,
          border: '1px solid #fca311',
        }}>
          <span
            className="material-symbols-outlined icon-fill"
            style={{ fontSize: 18, color: '#854F0B', flexShrink: 0 }}
          >
            wifi_off
          </span>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#633806', margin: 0 }}>
            Offline — manual assessment only (reduced accuracy)
          </p>
        </div>
      )}

      {/* ── Crash sensor auto-detected ───────────────────────── */}
      {sensorData && (
        <div style={{
          background: '#E6F1FB', borderRadius: 10,
          padding: '10px 14px', marginBottom: 14,
          display: 'flex', alignItems: 'center', gap: 10,
          border: '1px solid #006687',
        }}>
          <span
            className="material-symbols-outlined icon-fill"
            style={{ fontSize: 18, color: '#006687', flexShrink: 0 }}
          >
            sensors
          </span>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#0C447C', margin: 0 }}>
            Crash sensor data detected — will be used automatically
          </p>
        </div>
      )}

      {/* ── Page header ─────────────────────────────────────── */}
      <h1 style={{
        fontFamily: 'Space Grotesk, sans-serif',
        fontSize: 22, fontWeight: 700, color: '#14213D', marginBottom: 4,
      }}>
        AI Triage
      </h1>
      <p style={{ fontSize: 13, color: '#534433', marginBottom: 18, lineHeight: 1.5 }}>
        Add any available inputs — more signals = more accurate result
      </p>

      {/* ── Photo capture ────────────────────────────────────── */}
      {isOnline && (
        <div style={card}>
          <SectionHead
            icon="photo_camera"
            title="Injury photo"
            badge={imageFile ? '✓ Photo ready' : 'Optional'}
            badgeColor={imageFile ? '#27AE60' : '#867461'}
          />
          <PhotoCapture
            onCapture={file => setImageFile(file)}
            captured={imageFile}
            onClear={() => setImageFile(null)}
          />
        </div>
      )}

      {/* ── Voice recording ──────────────────────────────────── */}
      {isOnline && (
        <div style={card}>
          <SectionHead
            icon="mic"
            title="Describe symptoms (voice)"
            badge={audioBlob ? '✓ Recording ready' : 'Optional'}
            badgeColor={audioBlob ? '#27AE60' : '#867461'}
          />
          <p style={{ fontSize: 12, color: '#534433', marginBottom: 12, lineHeight: 1.5 }}>
            Speak clearly: "He is unconscious, there is heavy bleeding from the head…"
          </p>

          {!audioBlob ? (
            <button
              id="triage-voice-btn"
              onClick={recording ? stopRecording : startRecording}
              style={{
                width: '100%', padding: '14px', borderRadius: 10,
                border: 'none', cursor: 'pointer',
                background:  recording ? '#ba1a1a' : '#14213D',
                color: '#fff', fontSize: 14, fontWeight: 700,
                fontFamily: 'Space Grotesk, sans-serif',
                transition: 'background .15s',
                display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: 8,
              }}
            >
              <span className="material-symbols-outlined icon-fill" style={{ fontSize: 20 }}>
                {recording ? 'stop_circle' : 'mic'}
              </span>
              {recording ? '🔴 Recording… Tap to stop' : 'Tap to record'}
            </button>
          ) : (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div style={{
                flex: 1, background: '#EAF3DE', borderRadius: 8,
                padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span
                  className="material-symbols-outlined icon-fill"
                  style={{ color: '#27AE60', fontSize: 18 }}
                >
                  check_circle
                </span>
                <p style={{ fontSize: 13, fontWeight: 600, color: '#27500A', margin: 0 }}>
                  Voice recorded ({Math.round(audioBlob.size / 1024)}KB)
                </p>
              </div>
              <button
                onClick={() => setAudioBlob(null)}
                style={{
                  padding: '10px 14px', borderRadius: 8,
                  border: 'none', background: '#f0e0d1',
                  color: '#221a11', cursor: 'pointer',
                  fontSize: 12, fontWeight: 600,
                  fontFamily: 'Inter, sans-serif',
                }}
              >
                Re-record
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Text description ─────────────────────────────────── */}
      {isOnline && (
        <div style={card}>
          <SectionHead
            icon="edit_note"
            title="Type symptoms (text)"
            badge={textInput.trim() ? '✓ Text added' : 'Optional'}
            badgeColor={textInput.trim() ? '#27AE60' : '#867461'}
          />
          <textarea
            id="triage-text-input"
            value={textInput}
            onChange={e => setTextInput(e.target.value)}
            placeholder="Describe the injuries or symptoms in text…"
            rows={3}
            style={{
              width: '100%', padding: '10px 12px',
              borderRadius: 8, border: '1px solid #d9c3ad',
              fontSize: 13, fontFamily: 'Inter, sans-serif',
              color: '#221a11', resize: 'vertical', outline: 'none',
              lineHeight: 1.6,
            }}
          />
        </div>
      )}

      {/* ── Manual assessment ────────────────────────────────── */}
      <div style={card}>
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: (showManual || !isOnline) ? 14 : 0,
        }}>
          <SectionHead
            icon="fact_check"
            title={isOnline ? 'Manual assessment (optional)' : 'Manual assessment'}
            badge={
              showManual       ? '✓ Filled'              :
              !isOnline        ? 'Required offline'      :
                                 'Adds more accuracy'
            }
            badgeColor={
              showManual ? '#27AE60' :
              !isOnline  ? '#854F0B' :
                           '#867461'
            }
          />
          {isOnline && !showManual && (
            <button
              onClick={() => setShowManual(true)}
              style={{
                padding: '6px 14px', borderRadius: 8,
                border: 'none', background: '#f0e0d1',
                color: '#221a11', cursor: 'pointer',
                fontSize: 12, fontWeight: 600,
                fontFamily: 'Inter, sans-serif', flexShrink: 0,
              }}
            >
              Add
            </button>
          )}
        </div>

        {(showManual || !isOnline) && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <YesNo
              label="Is the person conscious and responsive?"
              value={manual.conscious}
              onChange={v => setManual(p => ({ ...p, conscious: v }))}
            />
            <YesNo
              label="Is there visible bleeding?"
              value={manual.visible_bleeding}
              onChange={v => setManual(p => ({ ...p, visible_bleeding: v }))}
            />
            <YesNo
              label="Can the person move / exit the vehicle?"
              value={manual.can_move}
              onChange={v => setManual(p => ({ ...p, can_move: v }))}
            />

            {/* Pain slider */}
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#534433', marginBottom: 7 }}>
                Pain level: <strong style={{ color: '#14213D' }}>{manual.pain_level}/10</strong>
              </p>
              <input
                type="range" min={1} max={10}
                value={manual.pain_level}
                onChange={e => setManual(p => ({ ...p, pain_level: parseInt(e.target.value) }))}
                style={{ width: '100%', accentColor: '#14213D' }}
              />
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                fontSize: 10, color: '#867461', marginTop: 2,
              }}>
                <span>Mild</span><span>Moderate</span><span>Severe</span>
              </div>
            </div>

            {/* Speed at crash */}
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: '#534433', marginBottom: 5 }}>
                Estimated speed at crash (km/h) <span style={{ fontWeight: 400 }}>— optional</span>
              </p>
              <input
                type="number"
                placeholder="e.g. 60"
                value={manual.speed_at_crash}
                onChange={e => setManual(p => ({ ...p, speed_at_crash: e.target.value }))}
                style={{
                  width: '100%', padding: '10px 12px',
                  borderRadius: 8, border: '1px solid #d9c3ad',
                  fontSize: 13, fontFamily: 'Inter, sans-serif',
                  color: '#221a11', outline: 'none',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Sticky analyse button ─────────────────────────────── */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: '#fff8f4', borderTop: '1px solid #d9c3ad',
        padding: '12px 20px', zIndex: 100,
      }}>
        <button
          id="triage-analyse-btn"
          onClick={analyse}
          disabled={!canAnalyse}
          style={{
            width: '100%', padding: '15px', borderRadius: 10,
            border: 'none',
            background: canAnalyse ? '#14213D' : '#d9c3ad',
            color: '#fff', fontSize: 15, fontWeight: 700,
            cursor: canAnalyse ? 'pointer' : 'default',
            fontFamily: 'Space Grotesk, sans-serif',
            boxShadow: canAnalyse ? '0 4px 0 rgba(0,0,0,0.2)' : 'none',
            transition: 'all .15s',
          }}
        >
          {isProcessingAudio ? 'Processing voice recording...' : isOnline ? 'Assess injury severity →' : 'Get offline estimate →'}
        </button>
        {!hasAnyInput && isOnline && (
          <p style={{
            fontSize: 11, color: '#867461', textAlign: 'center',
            marginTop: 6, fontFamily: 'Inter, sans-serif',
          }}>
            Add at least one input above to continue
          </p>
        )}
      </div>
    </div>
  );
}
