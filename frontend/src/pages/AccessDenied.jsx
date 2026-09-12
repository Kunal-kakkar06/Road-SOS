import { useNavigate } from 'react-router-dom';

export default function AccessDenied() {
  const navigate = useNavigate();

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: 'radial-gradient(circle at center, #1b0a0a 0%, #0a0a0f 100%)',
      color: '#fff',
      fontFamily: 'Space Grotesk, sans-serif',
      padding: '20px',
      textAlign: 'center'
    }}>
      <div style={{
        background: 'rgba(230, 57, 70, 0.1)',
        border: '1px solid rgba(230, 57, 70, 0.3)',
        borderRadius: '50%',
        padding: '24px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'pulse 2s infinite'
      }}>
        <span className="material-symbols-outlined" style={{
          fontSize: '64px',
          color: '#e63946'
        }}>gpp_bad</span>
      </div>

      <h1 style={{
        fontSize: '36px',
        fontWeight: 700,
        marginBottom: '12px',
        letterSpacing: '-0.5px',
        background: 'linear-gradient(45deg, #ff4d4d, #e63946)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent'
      }}>
        403 Access Denied
      </h1>

      <p style={{
        fontSize: '16px',
        color: '#a0a0b0',
        maxWidth: '450px',
        marginBottom: '32px',
        lineHeight: 1.6
      }}>
        You do not have the required role permissions to access this page. If you believe this is an error, please contact your administrator.
      </p>

      <div style={{ display: 'flex', gap: '16px' }}>
        <button 
          onClick={() => navigate(-1)} 
          style={{
            background: 'none',
            border: '1px solid rgba(255,255,255,0.2)',
            color: '#fff',
            padding: '12px 24px',
            borderRadius: '10px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s',
            fontFamily: 'Space Grotesk, sans-serif'
          }}
          onMouseOver={(e) => { e.target.style.background = 'rgba(255,255,255,0.05)'; }}
          onMouseOut={(e) => { e.target.style.background = 'none'; }}
        >
          Go Back
        </button>

        <button 
          onClick={() => navigate('/')} 
          style={{
            background: 'linear-gradient(135deg, #e63946 0%, #ba1a1a 100%)',
            border: 'none',
            color: '#fff',
            padding: '12px 24px',
            borderRadius: '10px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(230, 57, 70, 0.3)',
            transition: 'all 0.2s',
            fontFamily: 'Space Grotesk, sans-serif'
          }}
          onMouseOver={(e) => { e.target.style.transform = 'translateY(-1px)'; }}
          onMouseOut={(e) => { e.target.style.transform = 'translateY(0)'; }}
        >
          Return to Dashboard
        </button>
      </div>

      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(230, 57, 70, 0.4); }
          70% { transform: scale(1.05); box-shadow: 0 0 0 15px rgba(230, 57, 70, 0); }
          100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(230, 57, 70, 0); }
        }
      `}</style>
    </div>
  );
}
