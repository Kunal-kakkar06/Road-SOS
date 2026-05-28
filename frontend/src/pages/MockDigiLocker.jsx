import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export default function MockDigiLocker() {
  const [searchParams] = useSearchParams();
  const redirectUri = searchParams.get('redirect_uri') || 'http://localhost:5175/digilocker/callback';

  const [step, setStep] = useState(1); // 1 = login, 2 = pin/otp, 3 = consent
  const [loginVal, setLoginVal] = useState('');
  const [pinVal, setPinVal] = useState('');
  const [error, setError] = useState('');

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    if (!loginVal.trim()) {
      setError('Please enter your Aadhaar, Username or Mobile number');
      return;
    }
    setError('');
    setStep(2);
  };

  const handlePinSubmit = (e) => {
    e.preventDefault();
    if (pinVal.length < 6) {
      setError('Please enter a valid 6-digit Security PIN');
      return;
    }
    setError('');
    setStep(3);
  };

  const handleAllow = () => {
    // Redirect with authorization code
    window.location.href = `${redirectUri}?code=mock_digilocker_success_auth`;
  };

  const handleDeny = () => {
    // Navigate back to medical profile
    window.location.href = '/medical-profile';
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: '#F0F4F8',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'Inter, sans-serif',
      color: '#2D3748'
    }}>
      {/* Official Government Header Bar */}
      <div style={{
        background: '#FFFFFF',
        borderBottom: '4px solid #F56565', // Indian Saffron accent
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        padding: '12px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            background: 'linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #128807 100%)',
            width: 32,
            height: 32,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            fontSize: 14,
            border: '2px solid #000088',
            color: '#000088'
          }}>
            🇮🇳
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#1A365D', letterSpacing: '0.5px' }}>
              DigiLocker
            </div>
            <div style={{ fontSize: 10, color: '#718096', fontWeight: 600 }}>
              Ministry of Electronics & IT, Govt. of India
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#4A5568', background: '#EDF2F7', padding: '4px 8px', borderRadius: 4 }}>
            SECURE SANDBOX
          </span>
        </div>
      </div>

      {/* Main Form Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px'
      }}>
        <div style={{
          background: '#FFFFFF',
          borderRadius: 16,
          boxShadow: '0 10px 25px rgba(0,0,0,0.05)',
          border: '1px solid #E2E8F0',
          width: '100%',
          maxWidth: 440,
          overflow: 'hidden'
        }}>
          {/* Top Banner */}
          <div style={{
            background: 'linear-gradient(135deg, #1A365D 0%, #2A4365 100%)',
            padding: '24px',
            color: '#FFFFFF',
            textAlign: 'center'
          }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 8px 0', fontFamily: 'Space Grotesk, sans-serif' }}>
              Link RoadSOS with DigiLocker
            </h2>
            <p style={{ fontSize: 13, color: '#E2E8F0', margin: 0, fontWeight: 500 }}>
              Access your digital documents securely anytime, anywhere.
            </p>
          </div>

          <div style={{ padding: '24px' }}>
            {error && (
              <div style={{
                background: '#FFF5F5',
                color: '#C53030',
                border: '1px solid #FEB2B2',
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 13,
                fontWeight: 600,
                marginBottom: 16
              }}>
                ⚠️ {error}
              </div>
            )}

            {step === 1 && (
              <form onSubmit={handleLoginSubmit}>
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#4A5568', marginBottom: 6 }}>
                    Aadhaar / Username / Mobile Number
                  </label>
                  <input
                    type="text"
                    value={loginVal}
                    onChange={(e) => setLoginVal(e.target.value)}
                    placeholder="Enter 12 digit Aadhaar or Mobile"
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: 8,
                      border: '1px solid #CBD5E0',
                      fontSize: 14,
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
                <button
                  type="submit"
                  style={{
                    width: '100%',
                    padding: '12px',
                    borderRadius: 8,
                    border: 'none',
                    background: '#3182CE',
                    color: '#FFFFFF',
                    fontWeight: 700,
                    fontSize: 14,
                    cursor: 'pointer',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={(e) => e.target.style.background = '#2B6CB0'}
                  onMouseOut={(e) => e.target.style.background = '#3182CE'}
                >
                  Next
                </button>
              </form>
            )}

            {step === 2 && (
              <form onSubmit={handlePinSubmit}>
                <div style={{ marginBottom: 20 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: '#4A5568', marginBottom: 6 }}>
                    Enter 6-Digit Security PIN
                  </label>
                  <input
                    type="password"
                    maxLength={6}
                    value={pinVal}
                    onChange={(e) => setPinVal(e.target.value.replace(/\D/g, ''))}
                    placeholder="******"
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: 8,
                      border: '1px solid #CBD5E0',
                      fontSize: 18,
                      textAlign: 'center',
                      letterSpacing: '8px',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                  <span style={{ fontSize: 11, color: '#718096', display: 'block', marginTop: 6, fontWeight: 500 }}>
                    Hint: Enter any 6 digits for testing sandbox (e.g. 123456)
                  </span>
                </div>
                <button
                  type="submit"
                  style={{
                    width: '100%',
                    padding: '12px',
                    borderRadius: 8,
                    border: 'none',
                    background: '#3182CE',
                    color: '#FFFFFF',
                    fontWeight: 700,
                    fontSize: 14,
                    cursor: 'pointer',
                    transition: 'background 0.2s'
                  }}
                  onMouseOver={(e) => e.target.style.background = '#2B6CB0'}
                  onMouseOut={(e) => e.target.style.background = '#3182CE'}
                >
                  Sign In
                </button>
              </form>
            )}

            {step === 3 && (
              <div>
                <div style={{
                  background: '#EDF2F7',
                  borderRadius: 10,
                  padding: '16px',
                  marginBottom: 20
                }}>
                  <p style={{ fontSize: 13, fontWeight: 700, color: '#2D3748', margin: '0 0 10px 0' }}>
                    Consent Request
                  </p>
                  <p style={{ fontSize: 12, color: '#4A5568', margin: '0 0 14px 0', lineHeight: 1.4 }}>
                    <strong>RoadSOS</strong> is requesting permission to access your digital locker to retrieve the following data:
                  </p>
                  <div style={{
                    background: '#FFFFFF',
                    borderRadius: 8,
                    padding: '10px 12px',
                    border: '1px solid #E2E8F0',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10
                  }}>
                    <span className="material-symbols-outlined" style={{ color: '#E53E3E', fontSize: 20 }}>medical_information</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#2D3748' }}>ABHA Health Record</div>
                      <div style={{ fontSize: 10, color: '#718096' }}>Blood Group, Allergies, Medical Conditions</div>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 12 }}>
                  <button
                    onClick={handleDeny}
                    style={{
                      flex: 1,
                      padding: '12px',
                      borderRadius: 8,
                      border: '1px solid #CBD5E0',
                      background: '#FFFFFF',
                      color: '#4A5568',
                      fontWeight: 700,
                      fontSize: 14,
                      cursor: 'pointer'
                    }}
                  >
                    Deny
                  </button>
                  <button
                    onClick={handleAllow}
                    style={{
                      flex: 1,
                      padding: '12px',
                      borderRadius: 8,
                      border: 'none',
                      background: '#48BB78',
                      color: '#FFFFFF',
                      fontWeight: 700,
                      fontSize: 14,
                      cursor: 'pointer',
                      transition: 'background 0.2s'
                    }}
                    onMouseOver={(e) => e.target.style.background = '#38A169'}
                    onMouseOut={(e) => e.target.style.background = '#48BB78'}
                  >
                    Allow
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div style={{
        padding: '16px',
        textAlign: 'center',
        fontSize: 11,
        color: '#718096',
        background: '#FFFFFF',
        borderTop: '1px solid #E2E8F0'
      }}>
        DigiLocker is a secure cloud-based platform for storage, sharing and verification of documents & certificates.
      </div>
    </div>
  );
}
