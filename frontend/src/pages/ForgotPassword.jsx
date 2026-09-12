import { Link } from 'react-router-dom';

export default function ForgotPassword() {
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
        backgroundColor: '#ffffff',
        textAlign: 'center'
      }}>
        {/* Icon */}
        <div style={{
          width: '72px',
          height: '72px',
          borderRadius: '50%',
          backgroundColor: '#fff1e5',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
          border: '2px solid #14213D'
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: '36px', color: '#14213D' }}>
            lock_reset
          </span>
        </div>

        {/* Header */}
        <h2 style={{
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: '24px',
          fontWeight: 700,
          color: '#14213D',
          margin: '0 0 12px'
        }}>
          Reset Password
        </h2>

        {/* Message */}
        <p style={{
          fontSize: '14px',
          color: '#534433',
          lineHeight: '1.6',
          marginBottom: '24px',
          fontFamily: 'Inter, sans-serif'
        }}>
          For security reasons during active emergency services, automated password resets are disabled.
          Please contact the <strong>RoadSOS System Administrator</strong> or notify emergency dispatch to verify your identity and reset your password credentials.
        </p>

        {/* Back Link */}
        <Link
          to="/login"
          style={{
            display: 'inline-block',
            width: '100%',
            padding: '12px',
            borderRadius: '8px',
            background: '#14213D',
            color: '#fff',
            fontSize: '14px',
            fontWeight: 700,
            fontFamily: 'Space Grotesk, sans-serif',
            boxShadow: '0 4px 0 rgba(0,0,0,0.2)',
            textDecoration: 'none'
          }}
        >
          ← Return to Login
        </Link>
      </div>
    </div>
  );
}
