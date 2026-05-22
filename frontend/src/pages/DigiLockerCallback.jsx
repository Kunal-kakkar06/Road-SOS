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
          setStatus('Success! Redirecting to your medical profile...');
          setTimeout(() => navigate('/medical-profile'), 2000);
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
