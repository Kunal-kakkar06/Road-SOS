import React, { useState, useEffect } from 'react';

// Hardcoded userId for prototype without real auth
const USER_ID = "local_user_01";
const API_BASE = "/api";

export default function MedicalProfilePage({ onClose, onProfileUpdated }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState({
    full_name: '',
    date_of_birth: '',
    blood_type: '',
    allergies: '',
    medications: '',
    emergency_contact_name: '',
    emergency_contact_phone: ''
  });
  const [isNew, setIsNew] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/profile/${USER_ID}`);
      if (res.ok) {
        const data = await res.json();
        setProfile({
          full_name: data.full_name || '',
          date_of_birth: data.date_of_birth || '',
          blood_type: data.blood_type || '',
          allergies: data.allergies || '',
          medications: data.medications || '',
          emergency_contact_name: data.emergency_contact_name || '',
          emergency_contact_phone: data.emergency_contact_phone || ''
        });
        setIsNew(false);
      }
    } catch (e) {
      console.log('No existing profile or error fetching');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setProfile(prev => ({...prev, [e.target.name]: e.target.value}));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const method = isNew ? 'POST' : 'PUT';
      const url = isNew ? `${API_BASE}/profile/` : `${API_BASE}/profile/${USER_ID}`;
      
      const payload = { ...profile, user_id: USER_ID };
      // if DOB is empty, set to null
      if (!payload.date_of_birth) delete payload.date_of_birth;

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        onProfileUpdated(data);
        onClose();
      } else {
        alert("Error saving profile");
      }
    } catch (e) {
      alert("Network error while saving profile");
    } finally {
      setSaving(false);
    }
  };

  const handleDigiLocker = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/profile/${USER_ID}/digilocker`, { method: 'POST' });
      if (res.ok) {
        await fetchProfile();
        alert("DigiLocker data imported successfully!");
      }
    } catch (e) {
      alert("Error importing from DigiLocker. Save your profile first if it's new.");
    } finally {
      setLoading(false);
    }
  };

  const overlayStyle = {
    position: 'fixed', inset: 0, zIndex: 9999,
    background: '#fff', display: 'flex', flexDirection: 'column',
    overflowY: 'auto'
  };

  const headerStyle = {
    padding: '20px', display: 'flex', alignItems: 'center',
    borderBottom: '1px solid #e5e4e7', background: '#fcfcfc',
    position: 'sticky', top: 0, zIndex: 10
  };

  const inputStyle = {
    width: '100%', padding: '12px', borderRadius: 8,
    border: '1px solid #e5e4e7', boxSizing: 'border-box',
    fontSize: 15, fontFamily: 'Inter, sans-serif',
    marginBottom: 16
  };
  const labelStyle = {
    display: 'block', fontSize: 13, fontWeight: 600,
    color: '#534433', marginBottom: 6
  };

  if (loading) return <div style={overlayStyle}><div style={{padding: 20}}>Loading...</div></div>;

  return (
    <div style={overlayStyle}>
      <div style={headerStyle}>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', fontSize: 24, cursor: 'pointer', marginRight: 16
        }}>✕</button>
        <h2 style={{margin: 0, fontSize: 20, color: '#14213D'}}>Medical ID</h2>
      </div>

      <div style={{padding: '20px', maxWidth: 600, margin: '0 auto', width: '100%', boxSizing: 'border-box'}}>
        
        {!isNew && (
          <button 
            type="button" 
            onClick={handleDigiLocker}
            style={{
              width: '100%', padding: 14, borderRadius: 8,
              background: '#e6f3ff', color: '#0066cc', border: '1px dashed #0066cc',
              fontWeight: 700, fontSize: 15, marginBottom: 24, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
            }}>
            <span className="material-symbols-outlined">cloud_download</span>
            Sync with DigiLocker
          </button>
        )}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>Full Name *</label>
          <input required style={inputStyle} name="full_name" value={profile.full_name} onChange={handleChange} />

          <div style={{display: 'flex', gap: 16}}>
            <div style={{flex: 1}}>
              <label style={labelStyle}>Date of Birth</label>
              <input type="date" style={inputStyle} name="date_of_birth" value={profile.date_of_birth} onChange={handleChange} />
            </div>
            <div style={{flex: 1}}>
              <label style={labelStyle}>Blood Type</label>
              <select style={inputStyle} name="blood_type" value={profile.blood_type} onChange={handleChange}>
                <option value="">Select...</option>
                <option value="A+">A+</option>
                <option value="A-">A-</option>
                <option value="B+">B+</option>
                <option value="B-">B-</option>
                <option value="AB+">AB+</option>
                <option value="AB-">AB-</option>
                <option value="O+">O+</option>
                <option value="O-">O-</option>
              </select>
            </div>
          </div>

          <label style={labelStyle}>Allergies</label>
          <textarea style={{...inputStyle, height: 80}} name="allergies" value={profile.allergies} onChange={handleChange} placeholder="Any known allergies..." />

          <label style={labelStyle}>Current Medications</label>
          <textarea style={{...inputStyle, height: 80}} name="medications" value={profile.medications} onChange={handleChange} placeholder="List any medications..." />

          <h3 style={{fontSize: 16, marginTop: 12, marginBottom: 16, color: '#14213D'}}>Emergency Contact</h3>
          
          <label style={labelStyle}>Contact Name</label>
          <input style={inputStyle} name="emergency_contact_name" value={profile.emergency_contact_name} onChange={handleChange} />

          <label style={labelStyle}>Contact Phone</label>
          <input type="tel" style={inputStyle} name="emergency_contact_phone" value={profile.emergency_contact_phone} onChange={handleChange} />

          <button 
            type="submit" 
            disabled={saving}
            style={{
              width: '100%', padding: 16, borderRadius: 8,
              background: '#ba1a1a', color: '#fff', border: 'none',
              fontWeight: 700, fontSize: 16, marginTop: 12, cursor: saving ? 'not-allowed' : 'pointer'
            }}>
            {saving ? 'Saving...' : 'Save Medical Profile'}
          </button>
        </form>
      </div>
    </div>
  );
}
