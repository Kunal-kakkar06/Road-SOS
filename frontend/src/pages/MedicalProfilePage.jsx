import { useState, useEffect } from 'react';
import { startDigiLockerImport } from '../services/digilockerService';

const BLOOD_TYPES = ['A+','A-','B+','B-','AB+','AB-','O+','O-'];
const GENDERS     = ['Male','Female','Non-binary','Prefer not to say'];

export default function MedicalProfilePage() {
  const [profile, setProfile] = useState({
    full_name:'', date_of_birth:'', gender:'', phone:'',
    blood_type:'', allergies:[], medications:[], conditions:[],
    disabilities:[], emergency_contacts:[],
    insurance_provider:'', insurance_policy_no:'',
  });
  const [loading,  setLoading]  = useState(true);
  const [saving,   setSaving]   = useState(false);
  const [saved,    setSaved]    = useState(false);
  const [newAllergy,   setNewAllergy]   = useState('');
  const [newMed,       setNewMed]       = useState('');
  const [newCondition, setNewCondition] = useState('');

  // Load existing profile on mount
  useEffect(() => {
    const fetch_profile = async () => {
      const token = localStorage.getItem('authToken');
      if (!token) { setLoading(false); return; }
      try {
        const res = await fetch('/api/medical-profile', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setProfile(data);
          // Mirror to localStorage for offline SOS access
          localStorage.setItem('medicalProfile', JSON.stringify(data));
        }
      } catch(_) {}
      setLoading(false);
    };
    fetch_profile();
  }, []);

  const save = async () => {
    setSaving(true);
    const token = localStorage.getItem('authToken');
    try {
      const res = await fetch('/api/medical-profile', {
        method:  'PUT',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
        localStorage.setItem('medicalProfile', JSON.stringify(data));
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch(_) {}
    setSaving(false);
  };

  const addToList = (field, value, clearFn) => {
    if (!value.trim()) return;
    setProfile(p => ({ ...p, [field]: [...(p[field]||[]), value.trim()] }));
    clearFn('');
  };

  const removeFromList = (field, idx) => {
    setProfile(p => ({ ...p, [field]: p[field].filter((_,i) => i !== idx) }));
  };

  const addContact = () => {
    setProfile(p => ({
      ...p,
      emergency_contacts: [
        ...(p.emergency_contacts||[]),
        { name:'', phone:'', relation:'' }
      ]
    }));
  };

  const updateContact = (idx, key, val) => {
    const updated = [...(profile.emergency_contacts||[])];
    updated[idx]  = { ...updated[idx], [key]: val };
    setProfile(p => ({ ...p, emergency_contacts: updated }));
  };

  if (loading) return (
    <div style={{padding:40,textAlign:'center',color:'#534433'}}>
      Loading your medical profile…
    </div>
  );

  return (
    <div style={{
      maxWidth:800, margin:'0 auto',
      padding:'24px 16px 80px',
      background:'#E5E5E5', minHeight:'100vh',
    }}>

      {/* ── Page header ── */}
      <div style={{marginBottom:24}}>
        <h1 style={{
          fontFamily:'Space Grotesk,sans-serif',
          fontSize:24,fontWeight:700,color:'#14213D',marginBottom:4,
        }}>
          Medical Profile
        </h1>
        <p style={{fontSize:14,color:'#534433'}}>
          This information is shared with paramedics during emergencies.
          Keep it accurate and up to date.
        </p>
      </div>

      {/* ── DigiLocker import banner ── */}
      <div style={{
        background:'#fff',border:'0.5px solid rgba(0,0,0,0.1)',
        borderRadius:12,padding:'14px 18px',
        display:'flex',alignItems:'center',justifyContent:'space-between',
        marginBottom:16,flexWrap:'wrap',gap:10,
      }}>
        <div>
          <p style={{fontSize:13,fontWeight:600,color:'#14213D',marginBottom:2}}>
            Import from DigiLocker / ABHA
          </p>
          <p style={{fontSize:12,color:'#534433'}}>
            Auto-fill blood type, allergies and conditions from your health record
          </p>
        </div>
        <button onClick={startDigiLockerImport} style={{
          padding:'9px 18px',borderRadius:8,border:'none',
          background:'#006687',color:'#fff',
          fontSize:13,fontWeight:600,cursor:'pointer',
          fontFamily:'Space Grotesk,sans-serif',whiteSpace:'nowrap',
        }}>
          Connect DigiLocker
        </button>
      </div>

      {/* ── Section: Personal ── */}
      <Section title="Personal information" icon="person">
        <div style={grid2}>
          <Field label="Full name *"
            value={profile.full_name}
            onChange={v => setProfile(p=>({...p,full_name:v}))}
            placeholder="Arjun Kumar"/>
          <Field label="Phone"
            value={profile.phone}
            onChange={v => setProfile(p=>({...p,phone:v}))}
            placeholder="+91 98765 43210"/>
          <Field label="Date of birth"
            value={profile.date_of_birth}
            onChange={v => setProfile(p=>({...p,date_of_birth:v}))}
            placeholder="DD/MM/YYYY"/>
          <div>
            <label style={labelStyle}>Gender</label>
            <select value={profile.gender||''}
              onChange={e => setProfile(p=>({...p,gender:e.target.value}))}
              style={inputStyle}>
              <option value="">Select…</option>
              {GENDERS.map(g => <option key={g}>{g}</option>)}
            </select>
          </div>
        </div>
      </Section>

      {/* ── Section: Critical medical ── */}
      <Section title="Critical medical information" icon="favorite">
        {/* Blood type */}
        <div style={{marginBottom:16}}>
          <label style={labelStyle}>Blood type</label>
          <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:6}}>
            {BLOOD_TYPES.map(bt => (
              <button key={bt}
                onClick={() => setProfile(p=>({...p,blood_type:bt}))}
                style={{
                  padding:'8px 16px',borderRadius:20,border:'none',cursor:'pointer',
                  fontWeight:600,fontSize:13,fontFamily:'Inter,sans-serif',
                  background: profile.blood_type===bt ? '#ba1a1a' : '#f0e0d1',
                  color:      profile.blood_type===bt ? '#fff'    : '#221a11',
                  transition: 'all .15s',
                }}>
                {bt}
              </button>
            ))}
          </div>
        </div>

        {/* Allergies */}
        <TagInput
          label="Allergies"
          items={profile.allergies||[]}
          value={newAllergy}
          onChange={setNewAllergy}
          onAdd={() => addToList('allergies', newAllergy, setNewAllergy)}
          onRemove={i => removeFromList('allergies', i)}
          placeholder="e.g. Penicillin"
          tagColor="#FCEBEB"
          tagText="#A32D2D"
        />

        {/* Medications */}
        <TagInput
          label="Current medications"
          items={profile.medications||[]}
          value={newMed}
          onChange={setNewMed}
          onAdd={() => addToList('medications', newMed, setNewMed)}
          onRemove={i => removeFromList('medications', i)}
          placeholder="e.g. Metformin 500mg"
          tagColor="#E6F1FB"
          tagText="#0C447C"
        />

        {/* Conditions */}
        <TagInput
          label="Medical conditions"
          items={profile.conditions||[]}
          value={newCondition}
          onChange={setNewCondition}
          onAdd={() => addToList('conditions', newCondition, setNewCondition)}
          onRemove={i => removeFromList('conditions', i)}
          placeholder="e.g. Hypertension"
          tagColor="#EAF3DE"
          tagText="#27500A"
        />
      </Section>

      {/* ── Section: Emergency contacts ── */}
      <Section title="Emergency contacts" icon="contacts">
        {(profile.emergency_contacts||[]).map((c,i) => (
          <div key={i} style={{
            background:'#f5e5d7',borderRadius:10,
            padding:'12px 14px',marginBottom:10,
          }}>
            <div style={grid3c}>
              <Field label="Name" value={c.name}
                onChange={v => updateContact(i,'name',v)}
                placeholder="Sarah K"/>
              <Field label="Phone" value={c.phone}
                onChange={v => updateContact(i,'phone',v)}
                placeholder="+91 98765 43210"/>
              <Field label="Relation" value={c.relation}
                onChange={v => updateContact(i,'relation',v)}
                placeholder="Wife"/>
            </div>
            <button onClick={() => removeFromList('emergency_contacts',i)}
              style={{fontSize:12,color:'#ba1a1a',background:'none',
                border:'none',cursor:'pointer',marginTop:4}}>
              Remove
            </button>
          </div>
        ))}
        <button onClick={addContact} style={{
          padding:'9px 18px',borderRadius:8,
          border:'2px dashed #d9c3ad',
          background:'transparent',color:'#534433',
          fontSize:13,fontWeight:600,cursor:'pointer',
          fontFamily:'Inter,sans-serif',width:'100%',marginTop:4,
        }}>
          + Add emergency contact
        </button>
      </Section>

      {/* ── Section: Insurance ── */}
      <Section title="Insurance details" icon="shield">
        <div style={grid2}>
          <Field label="Insurance provider"
            value={profile.insurance_provider||''}
            onChange={v => setProfile(p=>({...p,insurance_provider:v}))}
            placeholder="e.g. Star Health"/>
          <Field label="Policy number"
            value={profile.insurance_policy_no||''}
            onChange={v => setProfile(p=>({...p,insurance_policy_no:v}))}
            placeholder="e.g. P/211111/01/2024/000001"/>
        </div>
      </Section>

      {/* ── Save button (sticky bottom) ── */}
      <div style={{
        position:'fixed',bottom:0,left:0,right:0,
        background:'#fff8f4',borderTop:'1px solid #d9c3ad',
        padding:'12px 24px',display:'flex',
        alignItems:'center',justifyContent:'space-between',
        zIndex:100,
      }}>
        {saved && (
          <p style={{fontSize:13,fontWeight:600,color:'#27AE60'}}>
            ✓ Profile saved successfully
          </p>
        )}
        {!saved && <span/>}
        <button onClick={save} disabled={saving||!profile.full_name}
          style={{
            padding:'13px 32px',borderRadius:10,border:'none',
            background: saving ? '#d9c3ad' : '#14213D',
            color:'#fff',fontSize:15,fontWeight:700,
            cursor: saving ? 'default' : 'pointer',
            fontFamily:'Space Grotesk,sans-serif',
          }}>
          {saving ? 'Saving…' : 'Save medical profile'}
        </button>
      </div>
    </div>
  );
}

// ── Reusable sub-components ──────────────────────────────────

function Section({ title, icon, children }) {
  return (
    <div style={{
      background:'#fff',border:'0.5px solid rgba(0,0,0,0.1)',
      borderRadius:12,padding:'18px 18px 14px',marginBottom:12,
    }}>
      <div style={{
        display:'flex',alignItems:'center',gap:8,
        marginBottom:14,paddingBottom:10,
        borderBottom:'1px solid #f0e0d1',
      }}>
        <span className="material-symbols-outlined"
          style={{fontSize:20,color:'#14213D',
                  fontVariationSettings:"'FILL' 1"}}>
          {icon}
        </span>
        <p style={{
          fontFamily:'Space Grotesk,sans-serif',
          fontSize:15,fontWeight:600,color:'#14213D',margin:0,
        }}>
          {title}
        </p>
      </div>
      {children}
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type='text' }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={value||''} placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        style={inputStyle}/>
    </div>
  );
}

function TagInput({ label, items, value, onChange, onAdd, onRemove,
                    placeholder, tagColor, tagText }) {
  return (
    <div style={{marginBottom:14}}>
      <label style={labelStyle}>{label}</label>
      <div style={{display:'flex',gap:6,marginTop:6,marginBottom:8,flexWrap:'wrap'}}>
        {items.map((item,i) => (
          <span key={i} style={{
            background:tagColor,color:tagText,
            padding:'4px 10px',borderRadius:20,
            fontSize:12,fontWeight:500,display:'flex',
            alignItems:'center',gap:6,
          }}>
            {item}
            <button onClick={()=>onRemove(i)}
              style={{background:'none',border:'none',
                cursor:'pointer',color:tagText,fontSize:14,
                lineHeight:1,padding:0}}>×</button>
          </span>
        ))}
      </div>
      <div style={{display:'flex',gap:8}}>
        <input value={value} onChange={e=>onChange(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&onAdd()}
          placeholder={placeholder} style={{...inputStyle,flex:1}}/>
        <button onClick={onAdd} style={{
          padding:'9px 16px',borderRadius:8,border:'none',
          background:'#14213D',color:'#fff',
          fontSize:13,fontWeight:600,cursor:'pointer',whiteSpace:'nowrap',
        }}>Add</button>
      </div>
    </div>
  );
}

const labelStyle = {
  display:'block',fontSize:12,fontWeight:600,
  color:'#534433',marginBottom:4,
};
const inputStyle = {
  width:'100%',padding:'10px 12px',borderRadius:8,
  border:'1px solid #d9c3ad',fontSize:14,
  fontFamily:'Inter,sans-serif',color:'#221a11',
  background:'#fff',outline:'none',
};
const grid2  = {display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginBottom:14};
const grid3c = {display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:10};
