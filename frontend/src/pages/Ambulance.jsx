import { useState, useEffect } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { findNearestAmbulances, dispatchAmbulance, trackAmbulance } from '../services/ambulanceService';
import AmbulanceCard from '../components/AmbulanceCard';
import LiveTrackingMap from '../components/LiveTrackingMap';
import useLocationCoords from '../hooks/useLocationCoords';

export default function Ambulance() {
  const { isOnline } = useOutletContext();
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dispatching, setDispatching] = useState(false);
  const [dispatch, setDispatch] = useState(null);
  const [driverPos, setDriverPos] = useState(null);
  const { coords, gpsError } = useLocationCoords();
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!coords) return;
    setLoading(true);
    setError(gpsError);

    (async () => {
      const res = await findNearestAmbulances({ lat: coords.lat, lng: coords.lng });
      setProviders(res.providers || []);
      if (res.error) setError('Could not reach server');
      setLoading(false);
    })();
  }, [coords, gpsError]);

  // SSE tracking when dispatch is active
  useEffect(() => {
    if (!dispatch) return;
    const stop = trackAmbulance(
      dispatch.dispatch_id,
      (loc) => setDriverPos({ lat: loc.driver_lat, lng: loc.driver_lng }),
      (status) => {
        setDispatch(prev => ({ ...prev, status }));
      }
    );
    return stop;
  }, [dispatch?.dispatch_id]);

  const handleDispatch = async () => {
    if (!coords) return;
    setDispatching(true);
    setError(null);
    try {
      const profile = (() => {
        try { return JSON.parse(localStorage.getItem('medicalProfile') || '{}'); }
        catch (_) { return {}; }
      })();
      const result = await dispatchAmbulance({
        patientLat: coords.lat,
        patientLng: coords.lng,
        patientUserId: profile.userId || 'anonymous',
        severity: 3,
      });
      setDispatch(result);
      if (result.driver_lat && result.driver_lng) {
        setDriverPos({ lat: result.driver_lat, lng: result.driver_lng });
      } else {
        setDriverPos({ lat: coords.lat + 0.015, lng: coords.lng + 0.015 });
      }
    } catch (e) {
      setError(e.message || 'Dispatch failed — call 108 directly');
    }
    setDispatching(false);
  };

  const filtered = filter === 'all'
    ? providers
    : providers.filter(p => {
        const t = (p.type || '').toLowerCase();
        if (filter === 'basic') return t === 'basic' || t === 'bls';
        return t === filter;
      });

  // ══════════════ ACTIVE DISPATCH VIEW ══════════════
  if (dispatch) {
    const amb = dispatch.assigned_ambulance || dispatch;
    return (
      <div className="fade-in" style={{ paddingBottom: 32 }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="material-symbols-outlined icon-fill" style={{ fontSize: 28, color: '#fca311' }}>
              ambulance
            </span>
            <h1 style={{
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 22, fontWeight: 700, color: '#fff', margin: 0,
            }}>
              Ambulance Dispatched
            </h1>
          </div>
        </div>

        {/* Dispatch info card */}
        <div style={{
          background: '#14213D', borderRadius: 16, padding: '20px',
          border: '2px solid #fca311', marginBottom: 14,
        }}>
          {/* Provider info */}
          <p style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 16, fontWeight: 700, color: '#fff', margin: '0 0 4px',
          }}>
            {amb.provider_name}
          </p>
          <p style={{ fontSize: 13, color: '#a0aab2', margin: '0 0 14px' }}>
            {amb.driver_name} · Vehicle: {amb.vehicle_number}
          </p>

          {/* ETA */}
          <div style={{
            background: 'rgba(252,163,17,0.15)', border: '1px solid rgba(252,163,17,0.3)',
            color: '#fca311', padding: '12px 18px', borderRadius: 12,
            display: 'inline-block', marginBottom: 14,
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 22, fontWeight: 800,
          }}>
            ETA: {dispatch.eta_minutes || '—'} min
          </div>

          {/* Status */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '10px 16px', borderRadius: 10, marginBottom: 14,
            background: dispatch.status === 'arrived'
              ? 'rgba(42,157,143,0.15)' : 'rgba(252,163,17,0.1)',
            border: dispatch.status === 'arrived'
              ? '1px solid rgba(42,157,143,0.3)' : '1px solid rgba(252,163,17,0.2)',
          }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
              background: dispatch.status === 'arrived' ? '#2A9D8F' : '#fca311',
            }} />
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: dispatch.status === 'arrived' ? '#2A9D8F' : '#fca311',
            }}>
              {dispatch.status === 'assigned' ? 'Driver notified — en route to you' :
               dispatch.status === 'en_route' ? 'Ambulance is on the way' :
               dispatch.status === 'arrived' ? '✓ Ambulance has arrived!' :
               dispatch.status === 'completed' ? '✓ Trip completed' :
               dispatch.status}
            </span>
          </div>

          {/* SMS confirmation */}
          {dispatch.driver_sms_sent && (
            <p style={{ fontSize: 12, color: '#a0aab2', margin: '0 0 14px' }}>
              ✓ SMS sent to driver ({amb.driver_phone})
            </p>
          )}
          {dispatch.driver_sms_sent === false && (
            <p style={{ fontSize: 12, color: '#fca311', margin: '0 0 14px' }}>
              ⚠ SMS service not configured — call driver directly
            </p>
          )}

          {/* Call driver */}
          <a
            href={`tel:${amb.driver_phone}`}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '12px', borderRadius: 10,
              background: '#fca311', color: '#14213D',
              fontWeight: 800, fontSize: 14, textDecoration: 'none',
              fontFamily: 'Space Grotesk, sans-serif',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>call</span>
            Call Driver
          </a>
        </div>

        {/* Live tracking map */}
        {coords && (
          <LiveTrackingMap
            patientLat={coords.lat}
            patientLng={coords.lng}
            driverLat={driverPos?.lat}
            driverLng={driverPos?.lng}
            routeUrl={dispatch.route_url}
          />
        )}

        {/* Emergency fallback */}
        <div style={{
          marginTop: 16,
          background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.2)',
          borderRadius: 12, padding: '14px 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, color: '#fff', margin: 0 }}>Need more help?</p>
            <p style={{ fontSize: 11, color: '#a0aab2', margin: '2px 0 0' }}>Call 108 for additional ambulances</p>
          </div>
          <a href="tel:108" style={{
            padding: '8px 18px', borderRadius: 8, background: '#E63946', color: '#fff',
            fontSize: 12, fontWeight: 700, textDecoration: 'none',
            fontFamily: 'Space Grotesk, sans-serif', flexShrink: 0,
          }}>
            Call 108
          </a>
        </div>
      </div>
    );
  }

  // ══════════════ PROVIDER LIST VIEW ══════════════
  return (
    <div className="fade-in" style={{ paddingBottom: 32 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="material-symbols-outlined icon-fill" style={{ fontSize: 28, color: '#fca311' }}>
            ambulance
          </span>
          <div>
            <h1 style={{
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 22, fontWeight: 700, color: '#0f172a', margin: 0,
            }}>
              Ambulance
            </h1>
            <p style={{ fontSize: 12, color: '#475569', margin: '2px 0 0' }}>
              Verified providers near you — sorted by distance
            </p>
          </div>
        </div>
        <Link to="/" style={{
          background: 'rgba(0,0,0,0.04)', border: '1px solid rgba(0,0,0,0.08)',
          borderRadius: 10, padding: '8px 14px',
          color: '#334155', fontSize: 12, fontWeight: 600,
          textDecoration: 'none', fontFamily: 'Inter, sans-serif',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_back</span>
          Dashboard
        </Link>
      </div>

      {/* Offline banner */}
      {!isOnline && (
        <div style={{
          background: 'rgba(252,163,17,0.1)', border: '1px solid rgba(252,163,17,0.25)',
          borderRadius: 10, padding: '10px 16px', marginTop: 10, marginBottom: 14,
          display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, color: '#fca311',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>wifi_off</span>
          <span>Offline — call 108 directly for ambulance service</span>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div style={{
          background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.2)',
          borderRadius: 10, padding: '10px 16px', marginTop: 10, marginBottom: 14,
          fontSize: 12, color: '#f87171',
        }}>
          {error}
        </div>
      )}

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 8, margin: '16px 0', flexWrap: 'wrap' }}>
        {[
          { key: 'all', label: 'All', icon: 'list' },
          { key: 'basic', label: 'Basic', icon: 'local_shipping' },
          { key: 'als', label: 'ALS', icon: 'medical_services' },
          { key: 'icu', label: 'ICU', icon: 'emergency' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: '7px 16px', borderRadius: 24, border: 'none',
              cursor: 'pointer', fontSize: 12, fontWeight: 600,
              fontFamily: 'Inter, sans-serif',
              background: filter === f.key ? '#fca311' : 'rgba(0, 0, 0, 0.05)',
              color: filter === f.key ? '#14213D' : '#334155',
              border: filter === f.key ? 'none' : '1px solid rgba(0, 0, 0, 0.08)',
              transition: 'all .2s',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16, color: filter === f.key ? '#14213D' : '#475569' }}>{f.icon}</span>
            {f.label}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div style={{
          background: '#14213D', borderRadius: 16, padding: '48px 24px',
          textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)',
        }}>
          <div style={{
            width: 40, height: 40, margin: '0 auto 16px',
            border: '3px solid rgba(255,255,255,0.08)',
            borderTop: '3px solid #fca311',
            borderRadius: '50%', animation: 'spin 1s linear infinite',
          }} />
          <p style={{ fontSize: 14, fontWeight: 600, color: '#fff', margin: 0 }}>
            Finding ambulances near you…
          </p>
        </div>
      )}

      {/* No results */}
      {!loading && filtered.length === 0 && (
        <div style={{
          background: '#14213D', borderRadius: 16, padding: '48px 24px',
          textAlign: 'center', border: '1px solid rgba(255,255,255,0.06)',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, color: '#a0aab2', display: 'block', marginBottom: 12 }}>
            ambulance
          </span>
          <p style={{ fontSize: 16, fontWeight: 700, color: '#fff', margin: '0 0 6px' }}>
            No ambulances available nearby
          </p>
          <p style={{ fontSize: 13, color: '#a0aab2', margin: '0 0 20px' }}>
            Call 108 for emergency ambulance service
          </p>
          <a href="tel:108" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '12px 28px', borderRadius: 10,
            background: '#E63946', color: '#fff',
            fontWeight: 700, textDecoration: 'none',
            fontFamily: 'Space Grotesk, sans-serif', fontSize: 14,
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>call</span>
            Call 108
          </a>
        </div>
      )}

      {/* Provider cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {filtered.map((p, i) => (
          <AmbulanceCard
            key={p.id}
            provider={p}
            rank={i + 1}
            onDispatch={() => handleDispatch()}
            dispatching={dispatching}
          />
        ))}
      </div>

      {/* Emergency fallback strip */}
      {!loading && providers.length > 0 && (
        <div style={{
          marginTop: 20,
          background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.2)',
          borderRadius: 12, padding: '14px 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 22, color: '#E63946' }}>emergency</span>
            <div>
              <p style={{ fontSize: 13, fontWeight: 700, color: '#fff', margin: 0 }}>Government ambulance</p>
              <p style={{ fontSize: 11, color: '#a0aab2', margin: '2px 0 0' }}>Call 108 for free emergency pickup</p>
            </div>
          </div>
          <a href="tel:108" style={{
            padding: '8px 18px', borderRadius: 8, background: '#E63946', color: '#fff',
            fontSize: 12, fontWeight: 700, textDecoration: 'none',
            fontFamily: 'Space Grotesk, sans-serif', flexShrink: 0,
          }}>
            Call 108
          </a>
        </div>
      )}
    </div>
  );
}
