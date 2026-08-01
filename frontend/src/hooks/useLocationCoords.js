import { useState, useEffect } from 'react';

export default function useLocationCoords() {
  const [coords, setCoords] = useState(() => {
    try {
      const override = localStorage.getItem('userLocationOverride');
      if (override) return JSON.parse(override);
    } catch (_) {}
    return { lat: 12.9716, lng: 77.5946 };
  });

  const [locationType, setLocationType] = useState(() => {
    try {
      return localStorage.getItem('userLocationOverride') ? 'override' : 'gps';
    } catch (_) {
      return 'gps';
    }
  });

  const [gpsError, setGpsError] = useState(null);

  useEffect(() => {
    let watchId = null;

    const updateLocation = () => {
      try {
        const overrideStr = localStorage.getItem('userLocationOverride');
        if (overrideStr) {
          const override = JSON.parse(overrideStr);
          setCoords({ lat: parseFloat(override.lat), lng: parseFloat(override.lng) });
          setLocationType('override');
          setGpsError(null);
          if (watchId !== null && navigator.geolocation) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
          }
          return;
        }
      } catch (_) {}

      setLocationType('gps');
      if (navigator.geolocation) {
        watchId = navigator.geolocation.watchPosition(
          (pos) => {
            setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
            setGpsError(null);
          },
          (err) => {
            console.warn('GPS error, using default Bangalore fallback', err);
            setGpsError('Location access denied or unavailable. Enable GPS permission for accurate results.');
            setCoords({ lat: 12.9716, lng: 77.5946 });
          },
          { enableHighAccuracy: true, timeout: 10000 }
        );
      } else {
        setGpsError('Geolocation is not supported by your browser');
        setCoords({ lat: 12.9716, lng: 77.5946 });
      }
    };

    updateLocation();

    window.addEventListener('locationChanged', updateLocation);
    window.addEventListener('storage', updateLocation);

    return () => {
      window.removeEventListener('locationChanged', updateLocation);
      window.removeEventListener('storage', updateLocation);
      if (watchId !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, []);

  return { coords, locationType, gpsError };
}
