import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../services/authService';

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await register(name, email, password, confirmPassword);
      // Initialize fresh profile shell for new user onboarding
      const initialProfile = { full_name: name, blood_type: '', emergency_contacts: [] };
      localStorage.setItem('medicalProfile', JSON.stringify(initialProfile));
      setSuccess('Registration successful! Redirecting to login...');
      setTimeout(() => {
        navigate('/login');
      }, 1500);
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
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
        {/* Header */}
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
            Create an Emergency Account
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

        {success && (
          <div style={{
            backgroundColor: '#d2e7d6',
            color: '#144120',
            padding: '12px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 600,
            marginBottom: '16px',
            border: '1px solid rgba(39, 174, 96, 0.2)'
          }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '13px', fontWeight: 700, color: '#221a11' }}>Full Name</label>
            <input
              type="text"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
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
            <label style={{ fontSize: '13px', fontWeight: 700, color: '#221a11' }}>Password</label>
            <input
              type="password"
              placeholder="At least 6 characters"
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

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '13px', fontWeight: 700, color: '#221a11' }}>Confirm Password</label>
            <input
              type="password"
              placeholder="Confirm Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
            {loading ? 'Registering...' : 'Register Account →'}
          </button>
        </form>

        <div style={{
          textAlign: 'center',
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '1px solid rgba(20, 33, 61, 0.1)'
        }}>
          <p style={{ fontSize: '13px', color: '#534433', margin: 0 }}>
            Already have an account?{' '}
            <Link to="/login" style={{ fontWeight: 700, color: '#14213D' }}>
              Log In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
