import { useNavigate } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || '';

const SEV_BG    = { P1: '#FCEBEB', P2: '#FFF3CD', P3: '#E6F1FB', P4: '#EAF3DE' };
const SEV_NAME  = { P1: 'Critical', P2: 'Serious', P3: 'Moderate', P4: 'Minor' };

export default function SeverityResult({ result, onRetry }) {
  const navigate = useNavigate();
  const {
    severity, severity_label, severity_color,
    confidence, shap_factors, signals_used,
    transcript, was_offline,
  } = result;

  const pct = Math.round((confidence || 0) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

      {/* ── Main severity card ─────────────────────────────── */}
      <div style={{
        background: '#fff', borderRadius: 14,
        padding: '20px 20px',
        border: `2.5px solid ${severity_color}`,
        boxShadow: `0 6px 0 ${severity_color}33`,
        animation: 'fadeUp .35s ease',
      }}>
        {/* Header row */}
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', marginBottom: 14,
        }}>
          <p style={{
            fontFamily: 'Space Grotesk, sans-serif', fontSize: 11,
            fontWeight: 700, color: '#534433', margin: 0,
            textTransform: 'uppercase', letterSpacing: '.08em',
          }}>
            Injury Severity Assessment
          </p>
          {was_offline && (
            <span style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 20,
              background: '#FAEEDA', color: '#633806', fontWeight: 700,
            }}>
              ⚡ Offline estimate
            </span>
          )}
        </div>

        {/* Big severity badge */}
        <div style={{
          background: SEV_BG[severity] || '#f0e0d1',
          borderRadius: 12, padding: '16px 18px',
          display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16,
        }}>
          <div style={{
            width: 60, height: 60, borderRadius: '50%',
            background: severity_color, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 4px 0 ${severity_color}55`,
          }}>
            <span style={{
              fontSize: 20, fontWeight: 900, color: '#fff',
              fontFamily: 'Space Grotesk, sans-serif',
            }}>
              {severity}
            </span>
          </div>
          <div>
            <p style={{
              fontFamily: 'Space Grotesk, sans-serif', fontSize: 20,
              fontWeight: 700, color: '#14213D', margin: '0 0 4px',
            }}>
              {SEV_NAME[severity]}
            </p>
            <p style={{ fontSize: 13, color: '#534433', margin: 0, lineHeight: 1.45 }}>
              {severity_label}
            </p>
          </div>
        </div>

        {/* Confidence bar */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: '#534433', margin: 0 }}>
              Model confidence
            </p>
            <p style={{ fontSize: 11, fontWeight: 700, color: '#221a11', margin: 0 }}>
              {pct}%
            </p>
          </div>
          <div style={{
            height: 7, borderRadius: 4,
            background: '#f0e0d1', overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', width: `${pct}%`,
              background: severity_color, borderRadius: 4,
              transition: 'width .6s ease',
            }} />
          </div>
        </div>

        {/* Signals used chips */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {Object.entries(signals_used || {}).map(([k, v]) => (
            <span key={k} style={{
              fontSize: 11, padding: '3px 10px', borderRadius: 20,
              fontWeight: 600,
              background: v ? '#EAF3DE' : '#f0e0d1',
              color:      v ? '#27500A' : '#867461',
            }}>
              {v ? '✓' : '—'} {k.charAt(0).toUpperCase() + k.slice(1)}
            </span>
          ))}
        </div>
      </div>

      {/* ── SHAP explanation card ──────────────────────────── */}
      {shap_factors?.length > 0 && (
        <div style={{
          background: '#fff', borderRadius: 12, padding: '16px 18px',
          border: '0.5px solid rgba(0,0,0,0.1)',
        }}>
          <p style={{
            fontFamily: 'Space Grotesk, sans-serif', fontSize: 14,
            fontWeight: 600, color: '#14213D', marginBottom: 12,
          }}>
            Why this severity?
          </p>
          {shap_factors.map((f, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start',
              gap: 10, marginBottom: i < shap_factors.length - 1 ? 10 : 0,
            }}>
              <div style={{
                width: 22, height: 22, borderRadius: '50%',
                background: '#14213D', flexShrink: 0,
                display: 'flex', alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11, fontWeight: 700, color: '#fff',
              }}>
                {i + 1}
              </div>
              <p style={{ fontSize: 13, color: '#534433', margin: 0, lineHeight: 1.5 }}>
                {f.label || f.feature}
              </p>
            </div>
          ))}
          <p style={{
            fontSize: 11, color: '#867461', marginTop: 12,
            fontStyle: 'italic', lineHeight: 1.5,
          }}>
            Powered by SHAP — these factors drove the AI decision.
            Always apply clinical judgment alongside this result.
          </p>
        </div>
      )}

      {/* ── Voice transcript ───────────────────────────────── */}
      {transcript && (
        <div style={{
          background: '#fff', borderRadius: 12, padding: '14px 18px',
          border: '0.5px solid rgba(0,0,0,0.1)',
        }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: '#534433', marginBottom: 6 }}>
            Voice transcript
          </p>
          <p style={{
            fontSize: 13, color: '#221a11',
            fontStyle: 'italic', lineHeight: 1.65, margin: 0,
          }}>
            "{transcript}"
          </p>
        </div>
      )}

      {/* ── Medical safety note ────────────────────────────── */}
      <div style={{
        background: '#FFF3CD', borderRadius: 10,
        padding: '10px 14px',
        border: '0.5px solid #fca311',
        display: 'flex', gap: 8, alignItems: 'flex-start',
      }}>
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 16, color: '#633806', flexShrink: 0, marginTop: 1 }}
        >
          warning
        </span>
        <p style={{ fontSize: 11, color: '#633806', margin: 0, lineHeight: 1.5 }}>
          <strong>For paramedics:</strong> Override this assessment with clinical judgment.
          AI triage is a decision-support tool only — not a medical diagnosis.
        </p>
      </div>

      {/* ── Action buttons ─────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 10 }}>
        <button
          id="triage-send-hospital-btn"
          onClick={() => {
            const sessionId = localStorage.getItem('activeTrackingSession');
            if (sessionId && navigator.onLine) {
              fetch(`${API_BASE}/api/family/session/${sessionId}/status`, {
                method:  'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ severity }),
              }).catch(() => {});
            }
            navigate(`/hospital?severity=${severity}`);
          }}
          style={{
            flex: 2, padding: '14px', borderRadius: 10,
            border: 'none', background: '#14213D', color: '#fff',
            fontSize: 13, fontWeight: 700, cursor: 'pointer',
            fontFamily: 'Space Grotesk, sans-serif',
            boxShadow: '0 4px 0 rgba(0,0,0,0.2)',
          }}
        >
          Send to hospital →
        </button>
        <button
          id="triage-reassess-btn"
          onClick={onRetry}
          style={{
            flex: 1, padding: '14px', borderRadius: 10,
            border: '1.5px solid #d9c3ad', background: 'transparent',
            color: '#221a11', fontSize: 12, fontWeight: 600,
            cursor: 'pointer', fontFamily: 'Inter, sans-serif',
          }}
        >
          Reassess
        </button>
      </div>

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
