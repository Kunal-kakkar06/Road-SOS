import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { handleDigiLockerCallback } from '../services/digilockerService';

export default function DigiLockerCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('Processing DigiLocker Auth...');

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setStatus('No code provided from DigiLocker.');
      return;
    }

    handleDigiLockerCallback(code)
      .then((data) => {
        if (data.success) {
          // Merge imported ABHA medical records into local storage cache
          try {
            const cached = JSON.parse(localStorage.getItem('medicalProfile') || '{}');
            const prefilled = data.prefilled || {};
            const merged = {
              ...cached,
              full_name: cached.full_name || "Arjun Kumar", // Default setup name if empty
              digilocker_linked: true,
              abha_id: data.abha_id,
              blood_type: cached.blood_type || prefilled.blood_type,
              allergies: Array.from(new Set([...(cached.allergies || []), ...(prefilled.allergies || [])])),
              conditions: Array.from(new Set([...(cached.conditions || []), ...(prefilled.conditions || [])])),
              medications: Array.from(new Set([...(cached.medications || []), ...(prefilled.medications || [])]))
            };
            // Save immediately so it is created and active
            localStorage.setItem('medicalProfile', JSON.stringify(merged));
          } catch (_) {}

          setStatus('DigiLocker Imported! Loading your new Medical ID...');
          setTimeout(() => navigate('/medical-profile'), 1200);
        } else {
          setStatus('Failed to import DigiLocker data.');
        }
      })
      .catch((err) => {
        setStatus('Error processing DigiLocker callback.');
      });
  }, [searchParams, navigate]);

  return (
    <div style={{ padding: 40, textAlign: 'center', color: '#534433' }}>
      {status}
    </div>
  );
}
