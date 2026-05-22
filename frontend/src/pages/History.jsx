import { Link } from 'react-router-dom';

export default function History() {
  return (
    <div className="placeholder-page fade-in">
      <div className="placeholder-page-icon">
        <span className="material-symbols-outlined" style={{fontSize:40,color:'#006687'}}>history</span>
      </div>
      <h1 className="placeholder-page-title">Incident History</h1>
      <p className="placeholder-page-desc">
        View your past SOS events, crash reports, and triage assessments. 
        All records are synced from your device.
      </p>
      <Link to="/" className="link-primary" style={{fontSize:14}}>← Back to Dashboard</Link>
    </div>
  );
}
