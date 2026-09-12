import { useEffect, useRef } from 'react';

/**
 * Live Tracking Map — Interactive Leaflet / Google Maps embed with dual-pin tracking.
 * Displays both Patient location (Destination) and Ambulance location (Origin).
 */
export default function LiveTrackingMap({
  patientLat, patientLng, driverLat, driverLng, routeUrl,
}) {
  const mapRef = useRef(null);
  const mapInst = useRef(null);
  const hasDriver = Boolean(driverLat && driverLng);

  useEffect(() => {
    if (!window.L || !mapRef.current || !patientLat || !patientLng) return;

    // Clean up existing map instance on re-render
    if (mapInst.current) {
      mapInst.current.remove();
      mapInst.current = null;
    }

    const pLat = parseFloat(patientLat);
    const pLng = parseFloat(patientLng);
    const dLat = hasDriver ? parseFloat(driverLat) : pLat + 0.015;
    const dLng = hasDriver ? parseFloat(driverLng) : pLng + 0.015;

    const map = window.L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: false
    });

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19
    }).addTo(map);

    // 1. Patient Location Marker (Red Pin)
    const patientIcon = window.L.divIcon({
      className: 'custom-patient-marker',
      html: `<div style="background:#ba1a1a;width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 8px rgba(186,26,26,0.8);animation:pulse-sos 2s infinite"></div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
    window.L.marker([pLat, pLng], { icon: patientIcon })
      .bindPopup('<b style="font-family:Space Grotesk;color:#ba1a1a">📍 Your Emergency Location</b>')
      .addTo(map);

    // 2. Ambulance Location Marker (Blue Vehicle Badge)
    const ambulanceIcon = window.L.divIcon({
      className: 'custom-ambulance-marker',
      html: `<div style="background:#006687;color:#fff;width:32px;height:32px;border-radius:50%;border:3px solid #fff;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 0 10px rgba(0,102,135,0.8)">🚑</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });
    window.L.marker([dLat, dLng], { icon: ambulanceIcon })
      .bindPopup('<b style="font-family:Space Grotesk;color:#006687">🚑 Dispatched Ambulance (En Route)</b>')
      .addTo(map);

    // 3. Draw Connecting Route Line between Ambulance and Patient
    const routeLine = window.L.polyline([[dLat, dLng], [pLat, pLng]], {
      color: '#fca311',
      weight: 4,
      dashArray: '8, 8',
      opacity: 0.95
    }).addTo(map);

    // Auto-fit map bounds to encompass both locations comfortably
    const bounds = window.L.latLngBounds([[pLat, pLng], [dLat, dLng]]);
    map.fitBounds(bounds, { padding: [40, 40] });

    mapInst.current = map;

    return () => {
      if (mapInst.current) {
        mapInst.current.remove();
        mapInst.current = null;
      }
    };
  }, [patientLat, patientLng, driverLat, driverLng, hasDriver]);

  return (
    <div style={{
      background: '#14213D', borderRadius: 16, overflow: 'hidden',
      border: '1px solid rgba(255,255,255,0.08)',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#fca311' }}>
            location_on
          </span>
          <p style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: 14, fontWeight: 700, color: '#fff', margin: 0,
          }}>
            Live Ambulance Tracking
          </p>
        </div>
        <span style={{
          background: 'rgba(42,157,143,0.15)', border: '1px solid rgba(42,157,143,0.3)',
          color: '#2A9D8F', padding: '4px 12px', borderRadius: 20,
          fontSize: 11, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: '#2A9D8F', display: 'inline-block',
            animation: 'pulse 2s infinite',
          }} />
          Live GPS Active
        </span>
      </div>

      {/* Interactive Leaflet Dual-Pin Map with Fallback Iframe */}
      {window.L ? (
        <div ref={mapRef} style={{ width: '100%', height: 280, display: 'block' }} />
      ) : (
        <iframe
          title="Live ambulance tracking"
          width="100%"
          height="280"
          style={{ border: 'none', display: 'block' }}
          loading="lazy"
          src={
            hasDriver
              ? `https://maps.google.com/maps?saddr=${driverLat},${driverLng}&daddr=${patientLat},${patientLng}&output=embed`
              : `https://maps.google.com/maps?q=${patientLat},${patientLng}&z=14&output=embed`
          }
        />
      )}

      {/* Legend */}
      <div style={{
        padding: '12px 18px',
        display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center',
      }}>
        <span style={{
          fontSize: 12, color: '#a0aab2',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: '#ba1a1a', display: 'inline-block',
          }} />
          Your location
        </span>
        <span style={{
          fontSize: 12, color: '#a0aab2',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: '#006687', display: 'inline-block',
          }} />
          Dispatched Ambulance
        </span>
        {routeUrl && (
          <a
            href={routeUrl}
            target="_blank"
            rel="noreferrer"
            style={{
              fontSize: 12, color: '#fca311', fontWeight: 700,
              textDecoration: 'none', marginLeft: 'auto',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            Open in Maps
            <span className="material-symbols-outlined" style={{ fontSize: 14 }}>open_in_new</span>
          </a>
        )}
      </div>
    </div>
  );
}
