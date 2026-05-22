import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function MedicalIDCard() {
  const [profile, setProfile] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // 1. Try localStorage first (instant, offline-safe)
    const cached = localStorage.getItem('medicalProfile');
    if (cached) { setProfile(JSON.parse(cached)); }

    // 2. Fetch fresh from FastAPI in background
    const token = localStorage.getItem('authToken');
    if (!token) return;
    fetch('/api/medical-profile', {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) {
          setProfile(data);
          localStorage.setItem('medicalProfile', JSON.stringify(data));
        }
      })
      .catch(() => {});
  }, []);

  // ── Empty state ─────────────────────────────────────────────
  if (!profile) return (
    <div style={cardStyle} onClick={() => navigate('/medical-profile')}>
      <div style={{
        display:'flex',flexDirection:'column',
        alignItems:'center',justifyContent:'center',
        gap:10,padding:'20px 0',cursor:'pointer',
      }}>
        <span className="material-symbols-outlined"
          style={{fontSize:36,color:'#d9c3ad'}}>
          person_add
        </span>
        <p style={{fontSize:14,fontWeight:600,color:'#534433',textAlign:'center'}}>
          Set up your Medical ID
        </p>
        <p style={{fontSize:12,color:'#867461',textAlign:'center'}}>
          Share critical info with paramedics
        </p>
        <button style={setupBtn}>Set up now →</button>
      </div>
    </div>
  );

  // ── Populated card ──────────────────────────────────────────
  return (
    <div style={cardStyle}>
      {/* Header row */}
      <div style={{
        display:'flex',alignItems:'center',
        justifyContent:'space-between',marginBottom:12,
      }}>
        <p style={{
          fontFamily:'Space Grotesk,sans-serif',
          fontSize:15,fontWeight:600,color:'#14213D',margin:0,
        }}>
          Medical ID
        </p>
        {/* Blood type badge */}
        {profile.blood_type && (
          <span style={{
            background:'#ffb95f',color:'#2a1700',
            padding:'4px 12px',borderRadius:20,
            fontSize:14,fontWeight:700,
            fontFamily:'Space Grotesk,sans-serif',
          }}>
            {profile.blood_type}
          </span>
        )}
      </div>

      {/* Name */}
      <p style={{
        fontFamily:'Space Grotesk,sans-serif',
        fontSize:16,fontWeight:600,color:'#221a11',marginBottom:10,
      }}>
        {profile.full_name}
      </p>

      {/* Allergies (max 2 shown) */}
      {profile.allergies?.length > 0 && (
        <div style={{marginBottom:8}}>
          {profile.allergies.slice(0,2).map((a,i) => (
            <p key={i} style={{
              fontSize:13,color:'#221a11',
              display:'flex',alignItems:'center',gap:6,marginBottom:3,
            }}>
              <span style={{
                width:8,height:8,borderRadius:'50%',
                background:'#ba1a1a',flexShrink:0,display:'inline-block',
              }}/>
              {a} allergy
            </p>
          ))}
          {profile.allergies.length > 2 && (
            <p style={{fontSize:12,color:'#534433'}}>
              +{profile.allergies.length-2} more
            </p>
          )}
        </div>
      )}

      {/* Top medication */}
      {profile.medications?.length > 0 && (
        <p style={{
          fontSize:13,color:'#221a11',
          display:'flex',alignItems:'center',gap:6,marginBottom:4,
        }}>
          <span className="material-symbols-outlined"
            style={{fontSize:16,color:'#534433'}}>
            medication
          </span>
          {profile.medications[0]}
          {profile.medications.length > 1 && (
            <span style={{fontSize:12,color:'#534433'}}>
              +{profile.medications.length-1}
            </span>
          )}
        </p>
      )}

      {/* Top condition */}
      {profile.conditions?.length > 0 && (
        <p style={{
          fontSize:13,color:'#221a11',
          display:'flex',alignItems:'center',gap:6,marginBottom:12,
        }}>
          <span className="material-symbols-outlined"
            style={{fontSize:16,color:'#534433'}}>
            favorite
          </span>
          {profile.conditions[0]}
        </p>
      )}

      {/* Edit link */}
      <button onClick={() => navigate('/medical-profile')}
        style={{
          background:'none',border:'none',cursor:'pointer',
          fontSize:13,fontWeight:600,color:'#14213D',
          display:'flex',alignItems:'center',gap:4,
          fontFamily:'Inter,sans-serif',padding:0,
          textDecoration:'underline',
        }}>
        Edit profile →
      </button>
    </div>
  );
}

const cardStyle = {
  background:'#fff',
  border:'0.5px solid rgba(0,0,0,0.1)',
  borderRadius:12,padding:'16px 18px',
  boxShadow:'0 1px 0 rgba(20,33,61,0.06)',
};
const setupBtn = {
  padding:'8px 20px',borderRadius:8,border:'none',
  background:'#14213D',color:'#fff',
  fontSize:13,fontWeight:600,cursor:'pointer',
  fontFamily:'Space Grotesk,sans-serif',
};
