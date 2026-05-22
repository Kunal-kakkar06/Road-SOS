import { Link } from 'react-router-dom';

export default function LiveMap() {
  return (
    <div className="placeholder-page fade-in">
      <div className="placeholder-page-icon">
        <span className="material-symbols-outlined" style={{fontSize:40,color:'#006687'}}>map</span>
      </div>
      <h1 className="placeholder-page-title">Live Blackspot Map</h1>
      <p className="placeholder-page-desc">
        Real-time accident blackspot data overlaid on your route. 
        Receive alerts when approaching high-risk zones.
      </p>
      <Link to="/" className="link-primary" style={{fontSize:14}}>← Back to Dashboard</Link>
    </div>
  );
}
