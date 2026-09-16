import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login } from '../services/authService';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      window.dispatchEvent(new Event('profileUpdated')); // update initials

      // Check if user has completed Medical ID profile
      let isProfileComplete = false;
      try {
        const cached = localStorage.getItem('medicalProfile');
        if (cached) {
          const prof = JSON.parse(cached);
          if (prof && (prof.blood_type || (prof.emergency_contacts && prof.emergency_contacts.length > 0))) {
            isProfileComplete = true;
          }
        }
      } catch (_) {}

      if (!isProfileComplete) {
        navigate('/medical-profile', { replace: true, state: { isOnboarding: true } });
      } else {
        navigate('/', { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: '#E5E5E5',
      padding: '24px 16px',
      fontFamily: 'Inter, sans-serif'
    }}>
      <div className="card-level-2 fade-in" style={{
        width: '100%',
        maxWidth: '440px',
        padding: '32px 24px',
        backgroundColor: '#ffffff'
      }}>
        {/* Wordmark logo */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h1 style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: '32px',
            fontWeight: 700,
            color: '#14213D',
            letterSpacing: '-0.02em',
            margin: 0
          }}>
            RoadSOS
          </h1>
          <p style={{
            fontSize: '14px',
            color: '#534433',
            marginTop: '6px',
            fontWeight: 500
          }}>
            AI-Powered Emergency Assistance
          </p>
        </div>

        {error && (
          <div style={{
            backgroundColor: '#ffdad6',
            color: '#410002',
            padding: '12px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 600,
            marginBottom: '16px',
            border: '1px solid rgba(186, 26, 26, 0.2)'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '13px', fontWeight: 700, color: '#221a11' }}>Email Address</label>
            <input
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                padding: '12px',
                borderRadius: '8px',
                border: '2px solid #14213D',
                fontSize: '14px',
                fontFamily: 'Inter, sans-serif',
                outline: 'none'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '13px', fontWeight: 700, color: '#221a11' }}>Password</label>
              <Link to="/forgot-password" style={{ fontSize: '12px', fontWeight: 600, color: '#006687' }}>
                Forgot Password?
              </Link>
            </div>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                padding: '12px',
                borderRadius: '8px',
                border: '2px solid #14213D',
                fontSize: '14px',
                fontFamily: 'Inter, sans-serif',
                outline: 'none'
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '14px',
              borderRadius: '8px',
              border: 'none',
              background: '#14213D',
              color: '#fff',
              fontSize: '15px',
              fontWeight: 700,
              cursor: loading ? 'default' : 'pointer',
              fontFamily: 'Space Grotesk, sans-serif',
              boxShadow: '0 4px 0 rgba(0,0,0,0.2)',
              marginTop: '8px',
              transition: 'all 0.1s'
            }}
          >
            {loading ? 'Logging in...' : 'Log In →'}
          </button>
        </form>

        <div style={{
          textAlign: 'center',
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '1px solid rgba(20, 33, 61, 0.1)'
        }}>
          <p style={{ fontSize: '13px', color: '#534433', margin: 0 }}>
            Don't have an account?{' '}
            <Link to="/register" style={{ fontWeight: 700, color: '#14213D' }}>
              Register Here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
