import { Link } from 'react-router-dom';

export default function Ambulance() {
  return (
    <div className="placeholder-page fade-in">
      <div className="placeholder-page-icon">
        <span className="material-symbols-outlined" style={{fontSize:40,color:'#006687'}}>ambulance</span>
      </div>
      <h1 className="placeholder-page-title">Ambulance Tracker</h1>
      <p className="placeholder-page-desc">
        Track dispatched ambulance units in real-time. 
        View ETA, unit details, and direct communication channels.
      </p>
      <Link to="/" className="link-primary" style={{fontSize:14}}>← Back to Dashboard</Link>
    </div>
  );
}
