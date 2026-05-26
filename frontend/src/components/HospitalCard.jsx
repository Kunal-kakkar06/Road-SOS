import { useState, useEffect } from 'react';
import { subscribeToLiveBeds, openGoogleMapsRoute } from '../services/hospitalService';

export default function HospitalCard({ hospital: h, rank }) {
  const [beds, setBeds] = useState({
    trauma_beds: h.trauma_beds,
    icu_beds: h.icu_beds,
    general_beds: h.general_beds,
    blood_types: h.blood_types,
  });
  const [bedsFlash, setBedsFlash] = useState(false);

  // Subscribe to live bed updates via SSE
  useEffect(() => {
    const unsubscribe = subscribeToLiveBeds(h.id, (data) => {
      setBeds({
        trauma_beds: data.trauma_beds,
        icu_beds: data.icu_beds,
        general_beds: data.general_beds,
        blood_types: data.blood_types,
      });
      // Flash animation on update
      setBedsFlash(true);
      setTimeout(() => setBedsFlash(false), 1200);
    });
    return unsubscribe;
  }, [h.id]);

  const bedColor = (count) =>
    count === 0 ? '#ba1a1a' : count <= 3 ? '#fca311' : '#27AE60';

  const userProfile = (() => {
    try { return JSON.parse(localStorage.getItem('medicalProfile') || '{}'); }
    catch (_) { return {}; }
  })();

  return (
    <div style={{
      background: '#14213D',
      border: rank === 1 ? '2px solid #fca311' : '1px solid rgba(255,255,255,0.08)',
      borderRadius: 16,
      padding: '18px 20px',
      boxShadow: rank === 1 ? '0 4px 24px rgba(252,163,17,0.15)' : '0 2px 8px rgba(0,0,0,0.2)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'transform 0.2s, box-shadow 0.2s',
    }}>
      {/* Rank badge */}
      {rank === 1 && (
        <div style={{
          position: 'absolute', top: 0, right: 0,
          background: '#fca311', color: '#14213D',
          padding: '4px 14px 4px 18px',
          borderRadius: '0 0 0 16px',
          fontSize: 10, fontWeight: 800,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          fontFamily: 'Space Grotesk, sans-serif',
        }}>
          ★ Best Match
        </div>
      )}

      {/* Rank + Name row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
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
              {h.name}
            </p>
            <p style={{ fontSize: 12, color: '#a0aab2', margin: '2px 0 0' }}>
              {h.type === 'govt' ? '🏛 Government' : '🏥 Private'} · {h.distance_km} km
            </p>
          </div>
        </div>
        {/* ETA pill */}
        <div style={{
          background: 'rgba(252,163,17,0.15)',
          border: '1px solid rgba(252,163,17,0.3)',
          color: '#fca311',
          padding: '6px 14px', borderRadius: 24,
          fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap',
          fontFamily: 'Space Grotesk, sans-serif',
          flexShrink: 0, marginLeft: 12,
        }}>
          {h.eta_text || `${h.distance_km} km`}
        </div>
      </div>

      {/* Beds row */}
      <div style={{
        display: 'flex', gap: 8, marginBottom: 12,
        transition: bedsFlash ? 'opacity 0.3s' : 'none',
        opacity: bedsFlash ? 0.7 : 1,
      }}>
        <BedChip label="Trauma" count={beds.trauma_beds} color={bedColor(beds.trauma_beds)} />
        <BedChip label="ICU" count={beds.icu_beds} color={bedColor(beds.icu_beds)} />
        <BedChip label="General" count={beds.general_beds} color={bedColor(beds.general_beds)} />
      </div>

      {/* Blood bank row */}
      {h.blood_bank && (
        <div style={{ marginBottom: 12 }}>
          <p style={{ fontSize: 11, color: '#a0aab2', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Blood Bank
          </p>
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            {(beds.blood_types || []).map(bt => {
              const isUserMatch = h.blood_match && bt === userProfile.bloodType;
              return (
                <span key={bt} style={{
                  background: isUserMatch ? '#E63946' : 'rgba(255,255,255,0.06)',
                  color: isUserMatch ? '#fff' : '#cbd5e1',
                  border: isUserMatch ? '1px solid #E63946' : '1px solid rgba(255,255,255,0.08)',
                  padding: '3px 10px', borderRadius: 20,
                  fontSize: 11, fontWeight: 700,
                }}>
                  {bt}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Capability chips */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {h.has_trauma && <Cap label="Trauma Centre" />}
        {h.has_cath_lab && <Cap label="Cath Lab" />}
        {h.has_neuro && <Cap label="Neuro Unit" />}
        {h.blood_match && <Cap label="✓ Blood Match" bg="rgba(42,157,143,0.15)" border="rgba(42,157,143,0.3)" text="#2A9D8F" />}
      </div>

      {/* CTA buttons */}
      <div style={{ display: 'flex', gap: 10 }}>
        <button
          onClick={() => openGoogleMapsRoute(h.route_url)}
          style={{
            flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
            background: '#fca311', color: '#14213D',
            fontSize: 13, fontWeight: 800, cursor: 'pointer',
            fontFamily: 'Space Grotesk, sans-serif',
            transition: 'transform 0.1s, opacity 0.2s',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>navigation</span>
          Navigate
        </button>
        <a
          href={`tel:${h.phone}`}
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
          Call
        </a>
      </div>
    </div>
  );
}


function BedChip({ label, count, color }) {
  return (
    <div style={{
      flex: 1,
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 10,
      padding: '8px 10px', textAlign: 'center',
    }}>
      <p style={{ fontSize: 10, color: '#a0aab2', margin: 0, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em' }}>{label}</p>
      <p style={{
        fontSize: 20, fontWeight: 800, color, margin: '2px 0',
        fontFamily: 'Space Grotesk, sans-serif',
        transition: 'color 0.3s',
      }}>{count}</p>
      <p style={{ fontSize: 9, color: '#6b7280', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>beds</p>
    </div>
  );
}


function Cap({ label, bg = 'rgba(255,255,255,0.06)', border = 'rgba(255,255,255,0.08)', text = '#cbd5e1' }) {
  return (
    <span style={{
      background: bg, color: text,
      border: `1px solid ${border}`,
      padding: '4px 12px', borderRadius: 20,
      fontSize: 11, fontWeight: 600,
    }}>
      {label}
    </span>
  );
}
