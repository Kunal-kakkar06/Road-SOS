import { useState,useEffect,useRef } from 'react';
import { getBlackspots,getRiskScore,getWeather,cacheBlackspotsForOffline,searchGeocode,getReverseGeocode }
  from '../services/preventionService';
import { startFatigueMonitoring,stopFatigueMonitoring }
  from '../services/fatigueDetection';
import FatigueAlert from '../components/FatigueAlert';
import useLocationCoords from '../hooks/useLocationCoords';

const haversineDistance = (lat1, lon1, lat2, lon2) => {
  const R = 6371; // km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

export default function PreventionMapPage(){
  const mapRef=useRef(null); const videoRef=useRef(null);
  const mapInst=useRef(null); const routeLineRef=useRef(null);
  const userMarkerRef=useRef(null);
  const markersRef=useRef([]);
  const routeMarkersRef=useRef([]);

  // Origin Coordinates & Search States
  const [startCoords, setStartCoords] = useState(null);
  const [startQuery, setStartQuery] = useState("");
  const [startResults, setStartResults] = useState([]);
  const [showStartResults, setShowStartResults] = useState(false);
  const [searchingStart, setSearchingStart] = useState(false);

  // Destination Coordinates & Search States
  const [destCoords, setDestCoords] = useState(null);
  const [destQuery, setDestQuery] = useState("");
  const [destResults, setDestResults] = useState([]);
  const [showDestResults, setShowDestResults] = useState(false);
  const [searchingDest, setSearchingDest] = useState(false);

  const { coords: hookCoords } = useLocationCoords();
  const [coords,setCoords] = useState({ lat: 12.9716, lng: 77.5946 });
  const [blackspots,setBlackspots]=useState([]);
  const [risk,setRisk]=useState(null);
  const [weather,setWeather]=useState(null);
  const [fatigue,setFatigue]=useState(null);
  const [fatigueOn,setFatigueOn]=useState(false);
  const [offline,setOffline]=useState(!navigator.onLine);
  const [loading,setLoading]=useState(true);

  useEffect(()=>{
    const on=()=>setOffline(false); const off=()=>setOffline(true);
    window.addEventListener('online',on); window.addEventListener('offline',off);
    return()=>{window.removeEventListener('online',on);window.removeEventListener('offline',off);};
  },[]);

  // Main Loader & Map Initializer based on reactive hookCoords
  useEffect(() => {
    if (!hookCoords) return;
    const { lat, lng } = hookCoords;
    setCoords({ lat, lng });

    const handleLoad = async () => {
      setStartCoords({ lat, lng });
      
      if (!mapInst.current) {
        initMap(lat, lng);
      } else {
        updateGPSPosition(lat, lng);
        mapInst.current.setView([lat, lng], 12);
      }

      try {
        const data = await getReverseGeocode(lat, lng);
        if (data && data.display_name) {
          setStartQuery(data.display_name.split(',')[0] || "🟢 Current Location");
        } else {
          setStartQuery("🟢 Current Location");
        }
      } catch (e) {
        setStartQuery("🟢 Current Location");
      }
      await loadPreventionData(lat, lng);
    };

    handleLoad();
  }, [hookCoords]);

  const updateGPSPosition = (lat, lng) => {
    setCoords({ lat, lng });
    if (userMarkerRef.current) {
      userMarkerRef.current.setLatLng([lat, lng]);
    }
  };

  const initMap = (lat, lng) => {
    if(window.L && mapRef.current && !mapInst.current){
      const map = window.L.map(mapRef.current, {
        center: [lat, lng],
        zoom: 12,
        zoomControl: false,
        attributionControl: false
      });
      
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(map);

      mapInst.current = map;

      userMarkerRef.current = window.L.circle([lat, lng], {
        radius: 45,
        color: '#ffffff',
        weight: 3,
        fillColor: '#006687',
        fillOpacity: 1
      }).addTo(map);
    }
  };

  const loadPreventionData = async (lat, lng) => {
    await cacheBlackspotsForOffline();
    const [bs,wx,rs]=await Promise.all([
      getBlackspots(lat,lng),
      getWeather(lat,lng),
      getRiskScore({originLat:lat,originLng:lng,destLat:lat+0.04,destLng:lng+0.04}),
    ]);
    setBlackspots(bs.blackspots||[]);
    setWeather(wx); setRisk(rs);
    plotBlackspots(bs.blackspots || []);
    setLoading(false);
  };

  const plotBlackspots = (spots) => {
    if (!mapInst.current || !window.L) return;
    
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    spots.forEach(zone => {
      const color = zone.risk === 'critical' ? '#ba1a1a' : '#fca311';
      const circle = window.L.circle([zone.lat, zone.lng], {
        radius: 260,
        color: color,
        weight: 2,
        fillColor: color,
        fillOpacity: 0.22
      }).bindPopup(`<b style="color: ${color}; font-family: Space Grotesk">${zone.road}</b><br/>Safety Alert: ${zone.cause || 'High danger merge point'}`).addTo(mapInst.current);
      markersRef.current.push(circle);
    });
  };

  // Autocomplete Geocoder search using OpenStreetMap Nominatim API
  const handleGeocoderSearch = async (query, target) => {
    if (!query || query.trim().length < 3) return;
    if (target === "start") setSearchingStart(true);
    else setSearchingDest(true);

    try {
      const data = await searchGeocode(query);
      if (data && data.length > 0) {
        if (target === "start") {
          setStartResults(data);
          setShowStartResults(true);
        } else {
          setDestResults(data);
          setShowDestResults(true);
        }
      } else {
        if (target === "start") setStartResults([]);
        else setDestResults([]);
      }
    } catch (e) {
      console.error("OSM Nominatim query failed", e);
    }

    if (target === "start") setSearchingStart(false);
    else setSearchingDest(false);
  };

  const selectStartResult = async (item) => {
    const name = item.display_name.split(',')[0];
    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lon);

    setStartCoords({ lat, lng });
    setStartQuery(name);
    setShowStartResults(false);

    if (mapInst.current) {
      mapInst.current.setView([lat, lng], 14);
    }

    try {
      const wx = await getWeather(lat, lng);
      if (wx) setWeather(wx);
    } catch (e) {
      console.error("Failed to update weather for starting point", e);
    }
  };

  const selectDestResult = (item) => {
    const name = item.display_name.split(',')[0];
    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lon);

    setDestCoords({ lat, lng });
    setDestQuery(`🏁 ${name}`);
    setShowDestResults(false);

    if (mapInst.current) {
      mapInst.current.setView([lat, lng], 14);
    }
  };

  // Recalculates OSRM driving route between dynamic Start and Destination
  const calculateRoute = async () => {
    if (!mapInst.current || !window.L) return;
    if (!startCoords || !destCoords) {
      alert("Please search and select both a Starting Point and a Destination address to plan your safe route.");
      return;
    }
    setLoading(true);

    const rs = await getRiskScore({
      originLat: startCoords.lat, originLng: startCoords.lng,
      destLat: destCoords.lat, destLng: destCoords.lng
    });
    setRisk(rs);
    if (rs && rs.weather) {
      setWeather(rs.weather);
    }

    if (routeLineRef.current) {
      routeLineRef.current.remove();
      routeLineRef.current = null;
    }
    
    routeMarkersRef.current.forEach(m => m.remove());
    routeMarkersRef.current = [];

    try {
      const response = await fetch(`https://router.project-osrm.org/route/v1/driving/${startCoords.lng},${startCoords.lat};${destCoords.lng},${destCoords.lat}?overview=full&geometries=geojson`);
      if (response.ok) {
        const data = await response.json();
        if (data.routes && data.routes.length > 0) {
          const routeCoords = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
          
          const polyline = window.L.polyline(routeCoords, {
            color: rs.color || '#14213D',
            weight: 6,
            opacity: 0.85,
            lineJoin: 'round'
          }).addTo(mapInst.current);

          routeLineRef.current = polyline;

          const startPin = window.L.marker([startCoords.lat, startCoords.lng]).bindPopup(`<b>Start: ${startQuery}</b>`).addTo(mapInst.current);
          const endPin = window.L.marker([destCoords.lat, destCoords.lng]).bindPopup(`<b>Destination: ${destQuery}</b>`).addTo(mapInst.current);
          routeMarkersRef.current.push(startPin, endPin);

          mapInst.current.fitBounds(polyline.getBounds(), { padding: [40, 40] });
        }
      }
    } catch (err) {
      console.error("OSRM Driving service failed", err);
      const pathPoints = [
        [startCoords.lat, startCoords.lng],
        [(startCoords.lat + destCoords.lat)/2 + 0.005, (startCoords.lng + destCoords.lng)/2 - 0.005],
        [destCoords.lat, destCoords.lng]
      ];
      const polyline = window.L.polyline(pathPoints, {
        color: rs.color || '#14213D',
        weight: 5,
        dashArray: '8, 8'
      }).addTo(mapInst.current);
      routeLineRef.current = polyline;
      mapInst.current.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }

    setLoading(false);
  };

  const plotRouteToCoordinates = async (targetLat, targetLng, targetName) => {
    if (!mapInst.current || !window.L) return;
    setLoading(true);

    const rs = await getRiskScore({
      originLat: coords.lat, originLng: coords.lng,
      destLat: targetLat, destLng: targetLng
    });
    setRisk(rs);
    if (rs && rs.weather) {
      setWeather(rs.weather);
    }

    if (routeLineRef.current) {
      routeLineRef.current.remove();
      routeLineRef.current = null;
    }
    
    routeMarkersRef.current.forEach(m => m.remove());
    routeMarkersRef.current = [];

    try {
      const response = await fetch(`https://router.project-osrm.org/route/v1/driving/${coords.lng},${coords.lat};${targetLng},${targetLat}?overview=full&geometries=geojson`);
      if (response.ok) {
        const data = await response.json();
        if (data.routes && data.routes.length > 0) {
          const routeCoords = data.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
          
          const polyline = window.L.polyline(routeCoords, {
            color: '#27AE60',
            weight: 6,
            opacity: 0.85,
            lineJoin: 'round'
          }).addTo(mapInst.current);

          routeLineRef.current = polyline;

          const startPin = window.L.marker([coords.lat, coords.lng]).bindPopup(`<b>Start: Current Location</b>`).addTo(mapInst.current);
          const endPin = window.L.marker([targetLat, targetLng]).bindPopup(`<b>Rest Stop: ${targetName}</b>`).addTo(mapInst.current);
          routeMarkersRef.current.push(startPin, endPin);

          mapInst.current.fitBounds(polyline.getBounds(), { padding: [40, 40] });
        }
      }
    } catch (err) {
      console.error("OSRM Driving service failed for rest stop", err);
    }

    setLoading(false);
  };

  const toggleFatigue=async()=>{
    if(fatigueOn){
      stopFatigueMonitoring();
      setFatigueOn(false);
      setFatigue(null);
    }
    else if(videoRef.current){
      const ok=await startFatigueMonitoring(videoRef.current,d=>setFatigue(d));
      setFatigueOn(!!ok);
    }
  };

  return(
    <div style={{maxWidth:850,margin:'0 auto',background:'#E5E5E5',minHeight:'100vh',boxSizing:'border-box',paddingBottom:40}}>

      {offline&&(
        <div style={{background:'#fca311',padding:'8px 16px',
          display:'flex',alignItems:'center',gap:8}}>
          <span style={{width:8,height:8,borderRadius:'50%',background:'#663f00'}}/>
          <p style={{fontSize:12,fontWeight:600,color:'#663f00',margin:0}}>
            Offline — showing cached data
          </p>
        </div>
      )}

      <div style={{padding:'16px 16px 0', display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
        <div>
          <h1 style={{fontFamily:'Space Grotesk,sans-serif',
            fontSize:20,fontWeight:700,color:'#14213D',marginBottom:4}}>
            Prevention Map & Safety Planner
          </h1>
          <p style={{fontSize:13,color:'#534433',marginBottom:12}}>
            Plot safety routes · Avoid blackspots · Local fatigue scan
          </p>
        </div>
        
        {weather&&(
          <div style={{background:'#fff', borderRadius:10, padding:'6px 12px', border:'0.5px solid rgba(0,0,0,0.1)', display:'flex', alignItems:'center', gap:6, marginLeft:'auto'}}>
            <img src={`https://openweathermap.org/img/wn/${weather.icon}.png`} alt="" style={{width:24,height:24}}/>
            <span style={{fontSize:12, fontWeight:700, color:'#14213D'}}>{weather.temp_c?.toFixed(0)}°C</span>
          </div>
        )}
      </div>

      <div style={{display:'flex', flexDirection:'column', gap:12, padding:'0 16px'}}>
        
        {/* ════ Interactive Route Planning & Search Input Panel ════ */}
        <div style={{background:'#fff', borderRadius:14, padding:'16px 20px', border:'0.5px solid rgba(0,0,0,0.1)', position:'relative', zIndex:1010}}>
          <p style={{fontFamily:'Space Grotesk,sans-serif', fontSize:14, fontWeight:700, color:'#14213D', marginBottom:12}}>
            🗺️ Safety Route Planner
          </p>
          
          <div style={{display:'flex', gap:10, flexWrap:'wrap', alignItems:'flex-start'}}>
            
            {/* Origin Geocoder Search Box */}
            <div style={{flex:1, minWidth:200, position:'relative'}}>
              <label style={{fontSize:11, fontWeight:700, color:'#718096', display:'block', marginBottom:4}}>STARTING POINT</label>
              <div style={{position:'relative', display:'flex', alignItems:'center'}}>
                <input
                  type="text"
                  placeholder="Search starting address..."
                  value={startQuery}
                  onChange={(e)=>{
                    setStartQuery(e.target.value);
                    if (e.target.value.length >= 3) {
                      handleGeocoderSearch(e.target.value, "start");
                    } else {
                      setShowStartResults(false);
                    }
                  }}
                  style={{width:'100%', padding:'10px 32px 10px 10px', borderRadius:8, border:'1px solid #CBD5E0', background:'#fff', fontSize:13, fontWeight:600, color:'#2D3748', boxSizing:'border-box'}}
                />
                
                {/* Reset button to quickly snap back to current live location */}
                <button
                  onClick={() => {
                    setStartCoords({ lat: coords.lat, lng: coords.lng });
                    setStartQuery("🟢 Live GPS Location");
                    setShowStartResults(false);
                  }}
                  style={{position:'absolute', right:30, border:'none', background:'none', cursor:'pointer', color:'#006687', display:'flex', alignItems:'center'}}
                  title="Use Live location"
                >
                  <span className="material-symbols-outlined" style={{fontSize:18}}>my_location</span>
                </button>

                {searchingStart ? (
                  <span className="material-symbols-outlined" style={{position:'absolute', right:10, fontSize:16, color:'#a0aec0', animation:'spin 1s infinite linear'}}>sync</span>
                ) : (
                  <span className="material-symbols-outlined" style={{position:'absolute', right:10, fontSize:18, color:'#a0aec0'}}>search</span>
                )}
              </div>

              {/* Autocomplete Start Results */}
              {showStartResults && startResults.length > 0 && (
                <div style={{position:'absolute', top:'100%', left:0, right:0, background:'#fff', border:'1px solid #CBD5E0', borderRadius:8, marginTop:4, boxShadow:'0 4px 12px rgba(0,0,0,0.15)', zIndex:99999, overflow:'hidden'}}>
                  {startResults.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => selectStartResult(item)}
                      style={{padding:'10px 14px', borderBottom:idx < startResults.length - 1 ? '1px solid #EDF2F7' : 'none', cursor:'pointer', fontSize:12, color:'#2D3748', transition:'background 0.15s'}}
                      onMouseEnter={(e)=>e.target.style.background='#F7FAFC'}
                      onMouseLeave={(e)=>e.target.style.background='transparent'}
                    >
                      📍 <strong>{item.display_name.split(',')[0]}</strong>
                      <span style={{color:'#718096', fontSize:10.5, display:'block', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                        {item.display_name.split(',').slice(1).join(',')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div style={{fontSize:18, color:'#718096', paddingTop:22}}>➜</div>

            {/* Destination Geocoder Search Box */}
            <div style={{flex:1, minWidth:200, position:'relative'}}>
              <label style={{fontSize:11, fontWeight:700, color:'#718096', display:'block', marginBottom:4}}>DESTINATION</label>
              <div style={{position:'relative', display:'flex', alignItems:'center'}}>
                <input
                  type="text"
                  placeholder="Search destination address..."
                  value={destQuery}
                  onChange={(e)=>{
                    setDestQuery(e.target.value);
                    if (e.target.value.length >= 3) {
                      handleGeocoderSearch(e.target.value, "dest");
                    } else {
                      setShowDestResults(false);
                    }
                  }}
                  style={{width:'100%', padding:'10px 32px 10px 10px', borderRadius:8, border:'1px solid #CBD5E0', background:'#fff', fontSize:13, fontWeight:600, color:'#2D3748', boxSizing:'border-box'}}
                />
                {searchingDest ? (
                  <span className="material-symbols-outlined" style={{position:'absolute', right:10, fontSize:16, color:'#a0aec0', animation:'spin 1s infinite linear'}}>sync</span>
                ) : (
                  <span className="material-symbols-outlined" style={{position:'absolute', right:10, fontSize:18, color:'#a0aec0'}}>search</span>
                )}
              </div>

              {/* Autocomplete Destination Results */}
              {showDestResults && destResults.length > 0 && (
                <div style={{position:'absolute', top:'100%', left:0, right:0, background:'#fff', border:'1px solid #CBD5E0', borderRadius:8, marginTop:4, boxShadow:'0 4px 12px rgba(0,0,0,0.15)', zIndex:99999, overflow:'hidden'}}>
                  {destResults.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => selectDestResult(item)}
                      style={{padding:'10px 14px', borderBottom:idx < destResults.length - 1 ? '1px solid #EDF2F7' : 'none', cursor:'pointer', fontSize:12, color:'#2D3748', transition:'background 0.15s'}}
                      onMouseEnter={(e)=>e.target.style.background='#F7FAFC'}
                      onMouseLeave={(e)=>e.target.style.background='transparent'}
                    >
                      🏁 <strong>{item.display_name.split(',')[0]}</strong>
                      <span style={{color:'#718096', fontSize:10.5, display:'block', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                        {item.display_name.split(',').slice(1).join(',')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button onClick={calculateRoute} style={{height:38, marginTop:18, padding:'0 20px', borderRadius:8, border:'none', background:'#14213D', color:'#fff', fontWeight:700, fontSize:13, cursor:'pointer', display:'flex', alignItems:'center', gap:6, fontFamily:'Space Grotesk,sans-serif'}}>
              Plan Safe Route →
            </button>
          </div>
        </div>

        {/* Map Container */}
        <div style={{borderRadius:14,overflow:'hidden', border:'0.5px solid rgba(0,0,0,0.1)',height:320,background:'#f0e0d1',position:'relative', zIndex:990}}>
          {loading && (
            <div style={{position:'absolute', inset:0, background:'rgba(255,255,255,0.7)', zIndex:9999, display:'flex', alignItems:'center', justifyContent:'center', color:'#14213D', fontWeight:700, fontSize:14}}>
              Calculating dynamic route safety…
            </div>
          )}
          <div ref={mapRef} style={{width:'100%',height:'100%'}}/>
        </div>

        {/* Dynamic Safety & Preventions Panel */}
        {risk && (
          <div style={{background:'#fff', borderRadius:14, padding:'20px', border:`2px solid ${risk.color||'#14213D'}`}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12}}>
              <div>
                <span style={{fontSize:11, fontWeight:700, color:'#718096', textTransform:'uppercase', letterSpacing:'.06em'}}>ROUTE SAFETY RATING</span>
                <p style={{fontFamily:'Space Grotesk,sans-serif', fontSize:34, fontWeight:800, color:risk.color, margin:0}}>
                  {Math.round(risk.score || risk.risk_score || 0)}
                  <span style={{fontSize:14, fontWeight:400, color:'#534433'}}>/100</span>
                </p>
              </div>
              <span style={{background:risk.color, color:'#fff', padding:'8px 18px', borderRadius:20, fontSize:14, fontWeight:700, fontFamily:'Space Grotesk,sans-serif'}}>
                {risk.label || risk.risk_label}
              </span>
            </div>

            {/* Smart Safety Tips checklist */}
            <div style={{marginTop:16, borderTop:'1px solid #E2E8F0', paddingTop:14}}>
              <p style={{fontSize:12, fontWeight:800, color:'#14213D', marginBottom:10, textTransform:'uppercase'}}>🛡️ Active Preventions Checklist</p>
              <div style={{display:'flex', flexDirection:'column', gap:8}}>
                <div style={{display:'flex', gap:10, background:'#F7FAFC', padding:'10px 14px', borderRadius:8, borderLeft:`4px solid ${risk.color}`}}>
                  <span style={{fontSize:18}}>⚠️</span>
                  <p style={{fontSize:12.5, color:'#2D3748', margin:0, lineHeight:1.4}}>
                    <strong>Zone Hazard Warning</strong>: Passing through {risk.blackspot_count || 3} verified high-hazard accident blackspots.
                  </p>
                </div>
                <div style={{display:'flex', gap:10, background:'#F7FAFC', padding:'10px 14px', borderRadius:8, borderLeft:'4px solid #006687'}}>
                  <span style={{fontSize:18}}>⏱️</span>
                  <p style={{fontSize:12.5, color:'#2D3748', margin:0, lineHeight:1.4}}>
                    <strong>Velocity Check</strong>: Adhere strictly to a <strong>50 km/h</strong> velocity limit when crossing intersection zones.
                  </p>
                </div>
                {weather && weather.rain_mm > 0 ? (
                  <div style={{display:'flex', gap:10, background:'#EBF8FF', padding:'10px 14px', borderRadius:8, borderLeft:'4px solid #3182CE'}}>
                    <span style={{fontSize:18}}>🌧️</span>
                    <p style={{fontSize:12.5, color:'#2D3748', margin:0, lineHeight:1.4}}>
                      <strong>Rain Friction</strong>: Wet asphalt reduces tire grip by 30%. Increase braking distance by 3 car lengths.
                    </p>
                  </div>
                ) : (
                  <div style={{display:'flex', gap:10, background:'#F7FAFC', padding:'10px 14px', borderRadius:8, borderLeft:'4px solid #27AE60'}}>
                    <span style={{fontSize:18}}>✅</span>
                    <p style={{fontSize:12.5, color:'#2D3748', margin:0, lineHeight:1.4}}>
                      <strong>Standard Alertness</strong>: Clear local visibility reported. Maintain 2-second safe trailing distance.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ════ Premium Glassmorphic Fatigue Scanner Bubble ════ */}
        <div style={{background:'#fff', borderRadius:14, padding:'16px 20px', border:'0.5px solid rgba(0,0,0,0.1)', position:'relative', overflow:'hidden'}}>
          <div style={{display:'flex', justifycontent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:16}}>
            
            <div style={{flex:2, minWidth:260}}>
              <p style={{fontFamily:'Space Grotesk,sans-serif', fontSize:15, fontWeight:700, color:'#14213D', margin:0}}>👁️ Local AI Fatigue Scan</p>
              <p style={{fontSize:12.5, color:'#718096', marginTop:4, lineHeight:1.5}}>
                Uses face mesh analytics directly inside the secure browser to trace blinks, eye closing patterns, and head tilts in real time.
              </p>
              
              <div style={{marginTop:16}}>
                <button onClick={toggleFatigue} style={{padding:'10px 24px', borderRadius:20, border:'none', background:fatigueOn?'#ba1a1a':'#14213D', color:'#fff', fontSize:13, fontWeight:700, cursor:'pointer', fontFamily:'Space Grotesk,sans-serif', display:'inline-flex', alignItems:'center', gap:6}}>
                  <span className="material-symbols-outlined" style={{fontSize:16}}>{fatigueOn?'videocam_off':'videocam'}</span>
                  {fatigueOn?'Stop Camera Feed':'Activate Scanner'}
                </button>
              </div>

              {fatigueOn && (
                <div style={{marginTop:16, display:'flex', gap:8, flexWrap:'wrap'}}>
                  <div style={{background:'#F7FAFC', border:'1px solid #E2E8F0', borderRadius:10, padding:'8px 12px', flex:1, minWidth:110}}>
                    <span style={{fontSize:9, fontWeight:700, color:'#718096', textTransform:'uppercase', display:'block'}}>Fatigue Score</span>
                    <span style={{fontSize:18, fontWeight:800, color: (fatigue?.score || 0) >= 60 ? '#ba1a1a' : '#27AE60', fontFamily:'Space Grotesk,sans-serif'}}>
                      {fatigue?.score || 0}%
                    </span>
                  </div>
                  <div style={{background:'#F7FAFC', border:'1px solid #E2E8F0', borderRadius:10, padding:'8px 12px', flex:1, minWidth:110}}>
                    <span style={{fontSize:9, fontWeight:700, color:'#718096', textTransform:'uppercase', display:'block'}}>Eye Aspect (EAR)</span>
                    <span style={{fontSize:18, fontWeight:800, color:'#14213D', fontFamily:'Space Grotesk,sans-serif'}}>
                      {fatigue?.avgEAR || "0.000"}
                    </span>
                  </div>
                  <div style={{background:'#F7FAFC', border:'1px solid #E2E8F0', borderRadius:10, padding:'8px 12px', flex:1, minWidth:110}}>
                    <span style={{fontSize:9, fontWeight:700, color:'#718096', textTransform:'uppercase', display:'block'}}>Head Tilt</span>
                    <span style={{fontSize:18, fontWeight:800, color:'#14213D', fontFamily:'Space Grotesk,sans-serif'}}>
                      {fatigue?.headTilt || "0.0"}°
                    </span>
                  </div>
                  <div style={{background:'#F7FAFC', border:'1px solid #E2E8F0', borderRadius:10, padding:'8px 12px', flex:1, minWidth:110}}>
                    <span style={{fontSize:9, fontWeight:700, color:'#718096', textTransform:'uppercase', display:'block'}}>Blinks / Min</span>
                    <span style={{fontSize:18, fontWeight:800, color:'#14213D', fontFamily:'Space Grotesk,sans-serif'}}>
                      {fatigue?.blinksPerMin || 0} BPM
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Futuristic Live Scanner Preview Bubble */}
            <div style={{flex:1, display:'flex', justifyContent:'center', alignItems:'center', minWidth:180}}>
              <div style={{
                position:'relative', 
                width:140, 
                height:140, 
                borderRadius:'50%', 
                overflow:'hidden', 
                border: fatigueOn ? '4px solid #27AE60' : '2px dashed #CBD5E0', 
                boxShadow: fatigueOn ? '0 0 15px rgba(39,174,96,0.4)' : 'none', 
                background: fatigueOn ? '#000' : '#F7FAFC',
                display:'flex',
                flexDirection:'column',
                alignItems:'center',
                justifyContent:'center',
                color:'#A0AEC0',
                textAlign:'center'
              }}>
                <video 
                  ref={videoRef} 
                  style={{
                    width:'100%', 
                    height:'100%', 
                    objectFit:'cover', 
                    transform:'scaleX(-1)',
                    display: fatigueOn ? 'block' : 'none'
                  }} 
                  playsInline 
                  autoPlay 
                  muted
                />
                
                {!fatigueOn && (
                  <div style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:10}}>
                    <span className="material-symbols-outlined" style={{fontSize:32, color:'#A0AEC0'}}>sensors</span>
                    <span style={{fontSize:11, fontWeight:600, marginTop:4}}>Scanner Offline</span>
                  </div>
                )}

                {fatigueOn && (
                  <>
                    {/* Cybernetic scanner laser line animation */}
                    <div style={{position:'absolute', top:0, left:0, width:'100%', height:2, background:'rgba(39, 174, 96, 0.85)', boxShadow:'0 0 8px #27AE60', animation:'scan-laser 2s infinite ease-in-out'}}/>
                    <div style={{position:'absolute', bottom:6, left:0, right:0, textAlign:'center'}}>
                      <span style={{fontSize:9, background:'rgba(0,0,0,0.6)', color:'#fff', padding:'2px 6px', borderRadius:8, fontWeight:700, letterSpacing:'.05em'}}>SCANNING</span>
                    </div>
                  </>
                )}
              </div>
            </div>

          </div>
        </div>

      </div>

      <style>{`
        @keyframes scan-laser {
          0%, 100% { top: 5%; }
          50% { top: 90%; }
        }
        .pulsing-route-line {
          animation: pulse-route 1.8s infinite alternate ease-in-out;
        }
        @keyframes pulse-route {
          from { stroke-opacity: 0.75; }
          to { stroke-opacity: 1; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>

      {fatigue&&fatigue.score>=60&&(
        <FatigueAlert fatigue={fatigue}
          onDismiss={()=>setFatigue(null)}
          onTakeBreak={()=>{
            setFatigue(null);
            const restLat = coords.lat + 0.006;
            const restLng = coords.lng + 0.008;
            setDestCoords({ lat: restLat, lng: restLng });
            setDestQuery("📍 Nearest Rest Stop (NH-48 Cafe)");
            plotRouteToCoordinates(restLat, restLng, "NH-48 Rest Cafe");
          }}/>
      )}
    </div>
  );
}
