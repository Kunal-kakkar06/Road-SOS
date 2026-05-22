import { Link } from 'react-router-dom';

export default function Hospital() {
  return (
    <div className="placeholder-page fade-in">
      <div className="placeholder-page-icon">
        <span className="material-symbols-outlined" style={{fontSize:40,color:'#006687'}}>local_hospital</span>
      </div>
      <h1 className="placeholder-page-title">Find Hospital</h1>
      <p className="placeholder-page-desc">
        Locate the nearest hospitals and trauma centres based on your 
        current GPS position and severity of the emergency.
      </p>
      <Link to="/" className="link-primary" style={{fontSize:14}}>← Back to Dashboard</Link>
    </div>
  );
}
