import { Link } from 'react-router-dom';

export default function FirstAid() {
  return (
    <div className="placeholder-page fade-in">
      <div className="placeholder-page-icon">
        <span className="material-symbols-outlined" style={{fontSize:40,color:'#006687'}}>health_and_safety</span>
      </div>
      <h1 className="placeholder-page-title">First Aid Guide</h1>
      <p className="placeholder-page-desc">
        Step-by-step first aid instructions for common emergencies. 
        Available offline — cached on your device for instant access.
      </p>
      <Link to="/" className="link-primary" style={{fontSize:14}}>← Back to Dashboard</Link>
    </div>
  );
}
