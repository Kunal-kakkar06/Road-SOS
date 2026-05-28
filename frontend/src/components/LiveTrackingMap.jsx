/**
 * Live Tracking Map — Google Maps embed with driver/patient location.
 * Uses a simple iframe embed — no Maps JS SDK needed.
 */
export default function LiveTrackingMap({
  patientLat, patientLng, driverLat, driverLng, routeUrl,
}) {
  const hasDriver = driverLat && driverLng;

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
            Live Tracking
          </p>
        </div>
        {hasDriver && (
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
            Live
          </span>
        )}
      </div>

      {/* Map embed */}
      <iframe
        title="Live ambulance tracking"
        width="100%"
        height="280"
        style={{ border: 'none', display: 'block' }}
        loading="lazy"
        src={
          hasDriver
            ? `https://maps.google.com/maps?q=${driverLat},${driverLng}&z=15&output=embed`
            : `https://maps.google.com/maps?q=${patientLat},${patientLng}&z=14&output=embed`
        }
      />

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
            background: '#E63946', display: 'inline-block',
          }} />
          Your location
        </span>
        {hasDriver && (
          <span style={{
            fontSize: 12, color: '#a0aab2',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: '#5cc8e8', display: 'inline-block',
            }} />
            Ambulance
          </span>
        )}
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
