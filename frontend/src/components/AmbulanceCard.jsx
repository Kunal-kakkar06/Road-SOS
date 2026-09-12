const TYPE_LABEL = {
  basic: 'Basic Life Support',
  bls: 'Basic Life Support',
  als: 'Advanced Life Support',
  icu: 'Mobile ICU',
  air: 'Air Ambulance',
};

const TYPE_STYLE = {
  basic: { bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.08)', text: '#cbd5e1' },
  bls: { bg: 'rgba(255,255,255,0.06)', border: 'rgba(255,255,255,0.08)', text: '#cbd5e1' },
  als: { bg: 'rgba(0,102,135,0.15)', border: 'rgba(0,102,135,0.3)', text: '#5cc8e8' },
  icu: { bg: 'rgba(230,57,70,0.12)', border: 'rgba(230,57,70,0.25)', text: '#f87171' },
  air: { bg: 'rgba(42,157,143,0.15)', border: 'rgba(42,157,143,0.3)', text: '#2A9D8F' },
};

export default function AmbulanceCard({ provider: p, rank, onDispatch, dispatching }) {
  const ts = TYPE_STYLE[p.type] || TYPE_STYLE.als;

  return (
    <div style={{
      background: '#14213D',
      border: rank === 1 ? '2px solid #fca311' : '1px solid rgba(255,255,255,0.08)',
      borderRadius: 16, padding: '18px 20px',
      boxShadow: rank === 1 ? '0 4px 24px rgba(252,163,17,0.15)' : '0 2px 8px rgba(0,0,0,0.2)',
      position: 'relative', overflow: 'hidden',
    }}>
      {rank === 1 && (
        <div style={{
          position: 'absolute', top: 0, right: 0,
          background: '#fca311', color: '#14213D',
          padding: '4px 14px 4px 18px', borderRadius: '0 0 0 16px',
          fontSize: 10, fontWeight: 800, textTransform: 'uppercase',
          letterSpacing: '0.06em', fontFamily: 'Space Grotesk, sans-serif',
        }}>
          ★ Nearest
        </div>
      )}

      {/* Name row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: rank === 1 ? '#fca311' : 'rgba(255,255,255,0.08)',
            color: rank === 1 ? '#14213D' : '#cbd5e1',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, fontWeight: 800, flexShrink: 0,
            fontFamily: 'Space Grotesk, sans-serif',
          }}>
            {rank}
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 15, fontWeight: 700, color: '#fff', margin: 0,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {p.name}
            </p>
            <p style={{ fontSize: 12, color: '#a0aab2', margin: '2px 0 0' }}>
              {p.operator_name} · {p.vehicle_number}
            </p>
          </div>
        </div>
        {/* ETA pill */}
        <div style={{
          background: 'rgba(252,163,17,0.15)', border: '1px solid rgba(252,163,17,0.3)',
          color: '#fca311', padding: '6px 14px', borderRadius: 24,
          fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap',
          fontFamily: 'Space Grotesk, sans-serif', flexShrink: 0, marginLeft: 12,
        }}>
          {p.eta_text || `${p.distance_km} km`}
        </div>
      </div>

      {/* Badges */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        <span style={{
          background: ts.bg, border: `1px solid ${ts.border}`, color: ts.text,
          padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 600,
        }}>
          {TYPE_LABEL[p.type] || p.type}
        </span>
        {p.is_verified && (
          <span style={{
            background: 'rgba(42,157,143,0.15)', border: '1px solid rgba(42,157,143,0.3)',
            color: '#2A9D8F', padding: '4px 12px', borderRadius: 20,
            fontSize: 11, fontWeight: 600,
          }}>
            ✓ Verified
          </span>
        )}
        <span style={{
          background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)',
          color: '#a0aab2', padding: '4px 12px', borderRadius: 20,
          fontSize: 11, fontWeight: 600,
        }}>
          {p.distance_km} km away
        </span>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 10 }}>
        <button
          onClick={onDispatch}
          disabled={dispatching}
          style={{
            flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
            background: dispatching ? '#6b7280' : '#fca311',
            color: dispatching ? '#fff' : '#14213D',
            fontSize: 13, fontWeight: 800, cursor: dispatching ? 'default' : 'pointer',
            fontFamily: 'Space Grotesk, sans-serif',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            transition: 'opacity 0.2s',
            opacity: dispatching ? 0.7 : 1,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
            {dispatching ? 'hourglass_empty' : 'ambulance'}
          </span>
          {dispatching ? 'Dispatching…' : 'Dispatch'}
        </button>
        <a
          href={`tel:${p.phone}`}
          style={{
            flex: 1, padding: '12px 0', borderRadius: 10,
            border: '1px solid rgba(255,255,255,0.12)', background: 'transparent',
            color: '#fff', fontSize: 13, fontWeight: 700,
            cursor: 'pointer', textAlign: 'center', textDecoration: 'none',
            fontFamily: 'Space Grotesk, sans-serif',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>call</span>
          Call Driver
        </a>
      </div>
    </div>
  );
}
