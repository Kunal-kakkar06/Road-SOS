const DB_NAME='roadsos-db'; const BS_KEY='blackspot-cache';
const API_BASE = import.meta.env.VITE_API_URL || '';

const openDB=()=>new Promise((res,rej)=>{
  const r=indexedDB.open(DB_NAME,1);
  r.onupgradeneeded=e=>e.target.result.createObjectStore('kv');
  r.onsuccess=e=>res(e.target.result); r.onerror=()=>rej(r.error);
});
const dbGet=async k=>{const db=await openDB();return new Promise(res=>{
  const r=db.transaction('kv','readonly').objectStore('kv').get(k);
  r.onsuccess=()=>res(r.result??null); r.onerror=()=>res(null);
});};
const dbSet=async(k,v)=>{const db=await openDB();return new Promise((res,rej)=>{
  const tx=db.transaction('kv','readwrite');
  tx.objectStore('kv').put(v,k); tx.oncomplete=res; tx.onerror=()=>rej(tx.error);
});};

export const cacheBlackspotsForOffline = async () => {
  try{
    const res=await fetch(`${API_BASE}/api/prevention/blackspots/cache`);
    if(res.ok){ const d=await res.json(); await dbSet(BS_KEY,{...d,cached_at:Date.now()}); }
  }catch(_){}
};

export const getBlackspots = async (lat,lng) => {
  if(navigator.onLine){
    try{
      const p=new URLSearchParams({lat,lng,radius:15000});
      const r=await fetch(`${API_BASE}/api/prevention/blackspots?${p}`,{signal:AbortSignal.timeout(6000)});
      if(r.ok){const d=await r.json();await dbSet(BS_KEY,{...d,cached_at:Date.now()});return d;}
    }catch(_){}
  }
  const c=await dbGet(BS_KEY);
  return c?{...c,offline:true}:{blackspots:[],offline:true};
};

export const getRiskScore = async ({originLat,originLng,destLat,destLng}) => {
  if(navigator.onLine){
    try{
      const p=new URLSearchParams({origin_lat:originLat,origin_lng:originLng,
                                    dest_lat:destLat,dest_lng:destLng});
      const r=await fetch(`${API_BASE}/api/prevention/risk-score?${p}`,
                          {method:'POST',signal:AbortSignal.timeout(8000)});
      if(r.ok) return{...(await r.json()),offline:false};
    }catch(_){}
  }
  // Offline rule-based fallback
  const h=new Date().getHours();
  let score=20;
  if([0,1,2,3,22,23].includes(h)) score+=25;
  else if([8,9,17,18,19].includes(h)) score+=15;
  const label=score>=75?'Critical':score>=50?'High':score>=25?'Moderate':'Low';
  const color=score>=75?'#ba1a1a':score>=50?'#fca311':score>=25?'#006687':'#27AE60';
  return{risk_score:score,risk_label:label,risk_color:color,
         factors:score>=50?['High-risk driving hours']:['Low-risk time of day'],
         offline:true,weather:null,blackspot_count:null};
};

export const getWeather = async (lat,lng) => {
  if(!navigator.onLine){
    const c=await dbGet(`wx:${Math.round(lat*10)}`); return c||null;
  }
  try{
    const r=await fetch(`${API_BASE}/api/prevention/weather?lat=${lat}&lng=${lng}`);
    if(r.ok){const d=await r.json();await dbSet(`wx:${Math.round(lat*10)}`,d);return d;}
  }catch(_){}
  return null;
};

export const searchGeocode = async (query) => {
  try {
    const res = await fetch(`${API_BASE}/api/prevention/geocode?q=${encodeURIComponent(query)}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Geocoding failed", e);
  }
  return [];
};

export const getReverseGeocode = async (lat, lng) => {
  try {
    const res = await fetch(`${API_BASE}/api/prevention/reverse-geocode?lat=${lat}&lng=${lng}`);
    if (res.ok) return await res.json();
  } catch (e) {
    console.error("Reverse geocoding failed", e);
  }
  return null;
};
