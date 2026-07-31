import { useState, useEffect } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { getNearestHospitals } from '../services/hospitalService';
import HospitalCard from '../components/HospitalCard';

export default function Hospital() {
  const { isOnline } = useOutletContext();
  const [hospitals, setHospitals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [coords, setCoords] = useState(null);
  const [filter, setFilter] = useState('all');
  const [fromCache, setFromCache] = useState(false);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCoords({ lat, lng });

        const profile = (() => {
          try { return JSON.parse(localStorage.getItem('medicalProfile') || '{}'); }
          catch (_) { return {}; }
        })();

        const result = await getNearestHospitals({
          lat,
          lng,
          bloodType: profile.bloodType,
          severity: 'P2',
        });

        setHospitals(result.hospitals || []);
        setFromCache(!!result.fromCache);
        if (result.error) setError('Could not reach server — showing cached results');
        setLoading(false);
      },
      (err) => {
        // GPS denied or unavailable — show an error so user knows results may not reflect their location
        setError('Location access denied. Enable GPS permission for accurate hospital results.');
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []);

  const filtered = filter === 'all'
    ? hospitals
    : hospitals.filter(h => h.type === filter);

  return (
    <div className="fade-in" style={{ paddingBottom: 32 }}>

      {/* ── Header ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="material-symbols-outlined icon-fill" style={{ fontSize: 32, color: '#fca311' }}>
            local_hospital
          </span>
          <div>
            <h1 style={{
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 24, fontWeight: 700, color: '#14213D', margin: 0,
            }}>
              Find Hospital
            </h1>
            <p style={{ fontSize: 13, color: '#4a5568', fontWeight: 600, margin: '2px 0 0' }}>
              Ranked by ETA · bed availability · blood match
            </p>
          </div>
        </div>
        <Link to="/" style={{
          background: '#14213D',
          borderRadius: 10, padding: '10px 16px',
          color: '#fff', fontSize: 13, fontWeight: 700,
          textDecoration: 'none',
          fontFamily: 'Inter, sans-serif',
          display: 'flex', alignItems: 'center', gap: 6,
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_back</span>
          Dashboard
        </Link>
      </div>

      {/* ── Cache / Offline banner ── */}
      {fromCache && (
        <div style={{
          background: 'rgba(252,163,17,0.1)',
          border: '1px solid rgba(252,163,17,0.25)',
          borderRadius: 10, padding: '10px 16px',
          marginBottom: 14,
          display: 'flex', alignItems: 'center', gap: 10,
          fontSize: 12, color: '#fca311',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>wifi_off</span>
          <span>Showing cached results — bed counts may be outdated</span>
        </div>
      )}

      {/* ── Filter chips ── */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { key: 'all', label: 'All hospitals', icon: 'list' },
          { key: 'govt', label: 'Government', icon: 'account_balance' },
          { key: 'private', label: 'Private', icon: 'domain' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: '9px 18px', borderRadius: 24, border: 'none',
              cursor: 'pointer', fontSize: 13, fontWeight: 700,
              fontFamily: 'Inter, sans-serif',
              background: filter === f.key ? '#14213D' : '#e2e8f0',
              color: filter === f.key ? '#fff' : '#14213D',
              border: filter === f.key ? 'none' : '1px solid #cbd5e1',
              transition: 'all .25s',
              display: 'flex', alignItems: 'center', gap: 6,
              boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>{f.icon}</span>
            {f.label}
          </button>
        ))}
      </div>

      {/* ── Loading state ── */}
      {loading && (
        <div style={{
          background: '#14213D', borderRadius: 16, padding: '48px 24px',
          textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)',
        }}>
          <div style={{
            width: 40, height: 40, margin: '0 auto 16px',
            border: '3px solid rgba(255,255,255,0.08)',
            borderTop: '3px solid #fca311',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          <p style={{ fontSize: 14, fontWeight: 600, color: '#fff', margin: 0 }}>
            Finding nearest hospitals…
          </p>
          <p style={{ fontSize: 12, color: '#a0aab2', margin: '6px 0 0' }}>
            Calculating distance and live traffic ETA
          </p>
        </div>
      )}

      {/* ── No results ── */}
      {!loading && filtered.length === 0 && (
        <div style={{
          background: '#14213D', borderRadius: 16, padding: '48px 24px',
          textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, color: '#a0aab2', marginBottom: 12, display: 'block' }}>
            location_off
          </span>
          <p style={{ fontSize: 16, fontWeight: 700, color: '#fff', margin: '0 0 6px' }}>
            No hospitals found nearby
          </p>
          <p style={{ fontSize: 13, color: '#a0aab2', margin: '0 0 20px' }}>
            Call 108 for emergency ambulance service
          </p>
          <a href="tel:108" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '12px 28px', borderRadius: 10,
            background: '#E63946', color: '#fff',
            fontWeight: 700, textDecoration: 'none',
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 14,
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>call</span>
            Call 108
          </a>
        </div>
      )}

      {/* ── Hospital cards ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {filtered.map((h, i) => (
          <HospitalCard key={h.id} hospital={h} rank={i + 1} />
        ))}
      </div>

      {/* ── Emergency fallback strip ── */}
      {!loading && hospitals.length > 0 && (
        <div style={{
          marginTop: 20,
          background: 'rgba(230,57,70,0.08)',
          border: '1px solid rgba(230,57,70,0.2)',
          borderRadius: 12, padding: '14px 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 22, color: '#E63946' }}>emergency</span>
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: '#fff', margin: 0 }}>Can't reach a hospital?</p>
              <p style={{ fontSize: 11, color: '#a0aab2', margin: '2px 0 0' }}>Call 108 for free ambulance pickup</p>
            </div>
          </div>
          <a href="tel:108" style={{
            padding: '8px 18px', borderRadius: 8,
            background: '#E63946', color: '#fff',
            fontSize: 12, fontWeight: 700,
            textDecoration: 'none',
            fontFamily: 'Space Grotesk, sans-serif',
            flexShrink: 0,
          }}>
            Call 108
          </a>
        </div>
      )}
    </div>
  );
}
