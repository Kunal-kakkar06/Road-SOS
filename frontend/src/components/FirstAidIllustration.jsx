import React from 'react';

/**
 * FirstAidIllustration — Dynamic vector diagram generator for First Aid procedural steps.
 * Analyzes step text keywords and renders tailored visual illustrations.
 */
export default function FirstAidIllustration({ stepText = '', category = '' }) {
  const text = stepText.toLowerCase();

  // 1. Tourniquet Application
  if (text.includes('tourniquet') || (text.includes('limb') && text.includes('bleed'))) {
    return (
      <div style={containerStyle('#BA1A1A', '#5C0909')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Background grid */}
          <pattern id="grid1" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
          </pattern>
          <rect width="400" height="150" fill="url(#grid1)" />

          {/* Arm outline */}
          <path d="M 40 75 Q 120 70, 200 75 T 360 75" stroke="#E2E8F0" strokeWidth="32" strokeLinecap="round" opacity="0.3" />
          <path d="M 40 75 Q 120 70, 200 75 T 360 75" stroke="#FCA5A5" strokeWidth="26" strokeLinecap="round" opacity="0.8" />

          {/* Wound site */}
          <circle cx="300" cy="75" r="10" fill="#EF4444" />
          <circle cx="300" cy="75" r="18" fill="none" stroke="#EF4444" strokeWidth="2" strokeDasharray="4,4" />
          <text x="300" y="110" fill="#FCA5A5" fontSize="11" fontWeight="700" textAnchor="middle">WOUND SITE</text>

          {/* Tourniquet Band (2-3 inches above wound) */}
          <rect x="140" y="45" width="24" height="60" rx="4" fill="#FCA311" stroke="#FFF" strokeWidth="2" />
          {/* Tightening rod */}
          <line x1="152" y1="25" x2="152" y2="125" stroke="#FFF" strokeWidth="5" strokeLinecap="round" />
          <circle cx="152" cy="75" r="6" fill="#1E293B" stroke="#FFF" strokeWidth="2" />

          {/* Distance arrow */}
          <line x1="164" y1="75" x2="280" y2="75" stroke="#FDE047" strokeWidth="2" strokeDasharray="4,4" />
          <text x="222" y="65" fill="#FDE047" fontSize="11" fontWeight="800" textAnchor="middle">2-3 INCHES ABOVE</text>

          {/* Title Badge */}
          <rect x="12" y="12" width="160" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">🩸 TOURNIQUET GUIDE</text>
        </svg>
      </div>
    );
  }

  // 2. Direct Pressure / Wound Control
  if (text.includes('pressure') || text.includes('wound') || text.includes('cloth') || text.includes('soak') || text.includes('bleeding')) {
    return (
      <div style={containerStyle('#991B1B', '#450A0A')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Body Surface */}
          <rect x="50" y="90" width="300" height="40" rx="8" fill="#FECDD3" opacity="0.9" />
          {/* Wound Area */}
          <ellipse cx="200" cy="90" rx="35" ry="10" fill="#DC2626" />

          {/* Clean Cloth / Dressing Pad */}
          <rect x="150" y="70" width="100" height="20" rx="4" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="2" />
          <rect x="160" y="65" width="80" height="10" rx="2" fill="#F1F5F9" />

          {/* Hand Applying Downward Force */}
          <path d="M 200 15 L 200 55" stroke="#FDE047" strokeWidth="6" strokeLinecap="round" />
          <path d="M 188 45 L 200 58 L 212 45" stroke="#FDE047" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />

          {/* Force Vectors */}
          <path d="M 165 25 L 165 50 M 235 25 L 235 50" stroke="#FDE047" strokeWidth="3" strokeDasharray="3,3" />

          {/* Label */}
          <rect x="12" y="12" width="190" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">🩹 DIRECT PRESSURE METHOD</text>

          <text x="200" y="138" fill="#FDE047" fontSize="12" fontWeight="800" textAnchor="middle">FIRM CONTINUOUS PRESSURE (5+ MINS)</text>
        </svg>
      </div>
    );
  }

  // 3. CPR Chest Compressions
  if (text.includes('compress') || text.includes('chest') || text.includes('push') || text.includes('100 to 120') || text.includes('heel of your hand')) {
    return (
      <div style={containerStyle('#006687', '#00334E')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Patient Chest Silhouette */}
          <path d="M 80 110 Q 200 80, 320 110" stroke="#93C5FD" strokeWidth="20" strokeLinecap="round" opacity="0.4" />
          <circle cx="200" cy="95" r="16" fill="#EF4444" opacity="0.8" />
          <text x="200" y="99" fill="#FFF" fontSize="10" fontWeight="900" textAnchor="middle">STERNUM</text>

          {/* Interlocked Hands Graphic */}
          <rect x="165" y="45" width="70" height="30" rx="8" fill="#FFFFFF" stroke="#38BDF8" strokeWidth="3" />
          <path d="M 175 55 H 225 M 180 63 H 220" stroke="#0284C7" strokeWidth="3" strokeLinecap="round" />

          {/* Push Down Arrow */}
          <path d="M 200 8 L 200 36" stroke="#FDE047" strokeWidth="5" strokeLinecap="round" />
          <path d="M 190 28 L 200 38 L 210 28" stroke="#FDE047" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Compression Depth & Rate Badge */}
          <rect x="12" y="12" width="140" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">🫀 CPR CHEST COMPRESSIONS</text>

          <rect x="250" y="12" width="138" height="24" rx="12" fill="rgba(252,163,17,0.2)" border="1px solid #FCA311" />
          <text x="319" y="28" fill="#FDE047" fontSize="10" fontWeight="800" textAnchor="middle">100-120 COMPRESSIONS/MIN</text>

          <text x="200" y="138" fill="#BAE6FD" fontSize="11" fontWeight="800" textAnchor="middle">PUSH 2 INCHES DEEP · ALLOW FULL CHEST RECOIL</text>
        </svg>
      </div>
    );
  }

  // 4. Heimlich Maneuver / Abdominal Thrusts
  if (text.includes('thrust') || text.includes('heimlich') || text.includes('abdominal') || text.includes('navel')) {
    return (
      <div style={containerStyle('#D97706', '#78350F')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Patient Body Profile */}
          <path d="M 170 20 Q 210 70, 180 130" stroke="#FDE68A" strokeWidth="18" strokeLinecap="round" opacity="0.6" />

          {/* Rescuer Fist Placement Above Navel */}
          <circle cx="195" cy="75" r="14" fill="#F59E0B" stroke="#FFF" strokeWidth="3" />
          <text x="195" y="79" fill="#FFF" fontSize="10" fontWeight="900" textAnchor="middle">FIST</text>

          {/* Upward & Inward Force Curved Arrow */}
          <path d="M 230 95 C 230 65, 195 55, 190 35" fill="none" stroke="#FDE047" strokeWidth="5" strokeDasharray="4,4" />
          <path d="M 183 42 L 190 33 L 198 42" fill="none" stroke="#FDE047" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />

          <rect x="12" y="12" width="180" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">😮‍💨 HEIMLICH ABDOMINAL THRUSTS</text>

          <text x="200" y="138" fill="#FEF08A" fontSize="11" fontWeight="800" textAnchor="middle">QUICK UPWARD & INWARD THRUSTS ABOVE NAVEL</text>
        </svg>
      </div>
    );
  }

  // 5. Back Blows (Choking)
  if (text.includes('back blow') || text.includes('shoulder blade') || text.includes('blows')) {
    return (
      <div style={containerStyle('#B45309', '#451A03')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Patient Leaning Forward */}
          <path d="M 120 110 L 220 50" stroke="#FDE68A" strokeWidth="22" strokeLinecap="round" opacity="0.6" />

          {/* Target Impact Area between shoulder blades */}
          <ellipse cx="180" cy="70" rx="18" ry="12" fill="#EF4444" opacity="0.8" />
          <text x="180" y="74" fill="#FFF" fontSize="9" fontWeight="900" textAnchor="middle">TARGET</text>

          {/* Hand Heel Firm Strike Arrow */}
          <path d="M 240 30 L 195 60" stroke="#FDE047" strokeWidth="5" strokeLinecap="round" />
          <path d="M 200 48 L 192 62 L 208 62" fill="none" stroke="#FDE047" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />

          <rect x="12" y="12" width="160" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">🖐️ 5 FIRM BACK BLOWS</text>

          <text x="200" y="138" fill="#FEF08A" fontSize="11" fontWeight="800" textAnchor="middle">STRIKE HARD BETWEEN SHOULDER BLADES</text>
        </svg>
      </div>
    );
  }

  // 6. Recovery Position / Airway Tilt
  if (text.includes('recovery') || text.includes('side') || text.includes('tilt') || text.includes('airway')) {
    return (
      <div style={containerStyle('#047857', '#064E3B')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Side-lying patient posture */}
          <path d="M 60 85 Q 200 70, 340 85" stroke="#A7F3D0" strokeWidth="18" strokeLinecap="round" opacity="0.5" />
          {/* Bent knee */}
          <path d="M 240 85 L 270 115 L 300 85" stroke="#A7F3D0" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />

          {/* Head Tilt Support */}
          <circle cx="85" cy="80" r="16" fill="#34D399" />
          <path d="M 75 80 Q 85 65, 95 80" stroke="#FFF" strokeWidth="3" fill="none" />

          <rect x="12" y="12" width="180" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">🛌 RECOVERY POSITION</text>

          <text x="200" y="138" fill="#A7F3D0" fontSize="11" fontWeight="800" textAnchor="middle">ROLL ONTO SIDE · BEND TOP KNEE · TILT HEAD BACK</text>
        </svg>
      </div>
    );
  }

  // 7. Cool Water for Burns
  if (text.includes('burn') || text.includes('cool') || text.includes('fire') || text.includes('water')) {
    return (
      <div style={containerStyle('#0284C7', '#0C4A6E')}>
        <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Burned Skin Area */}
          <rect x="120" y="85" width="160" height="30" rx="8" fill="#F87171" opacity="0.8" />

          {/* Running Cool Water Stream */}
          <path d="M 200 10 L 200 80" stroke="#38BDF8" strokeWidth="12" strokeLinecap="round" opacity="0.8" />
          <path d="M 185 25 L 185 80 M 215 25 L 215 80" stroke="#7DD3FC" strokeWidth="4" strokeDasharray="6,4" />

          {/* Cool Temperature indicator */}
          <rect x="12" y="12" width="170" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
          <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">💧 COOL RUNNING WATER</text>

          <text x="200" y="138" fill="#BAE6FD" fontSize="11" fontWeight="800" textAnchor="middle">COOL BURN UNDER RUNNING WATER FOR 10-20 MINS</text>
        </svg>
      </div>
    );
  }

  // Default Clinical Action Diagram
  return (
    <div style={containerStyle('#1E293B', '#0F172A')}>
      <svg width="100%" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
        <pattern id="grid_def" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
        </pattern>
        <rect width="400" height="150" fill="url(#grid_def)" />

        {/* Pulse ECG Line */}
        <path d="M 30 75 L 120 75 L 135 45 L 150 105 L 165 60 L 180 85 L 195 75 L 370 75" stroke="#FCA311" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

        {/* Cross Badge */}
        <circle cx="200" cy="75" r="22" fill="#FCA311" />
        <path d="M 200 63 V 87 M 188 75 H 212" stroke="#1E293B" strokeWidth="5" strokeLinecap="round" />

        <rect x="12" y="12" width="190" height="24" rx="12" fill="rgba(0,0,0,0.4)" />
        <text x="22" y="28" fill="#FFF" fontSize="11" fontWeight="800">🏥 CLINICAL ACTION GUIDE</text>

        <text x="200" y="138" fill="#94A3B8" fontSize="11" fontWeight="800" textAnchor="middle">FOLLOW PROCEDURAL INSTRUCTIONS STEP BY STEP</text>
      </svg>
    </div>
  );
}

function containerStyle(color1, color2) {
  return {
    width: '100%',
    height: '150px',
    borderRadius: '14px',
    overflow: 'hidden',
    background: `linear-gradient(135deg, ${color1} 0%, ${color2} 100%)`,
    boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
    border: '1px solid rgba(255,255,255,0.1)',
    display: 'flex',
    alignItems: 'center',
    justify: 'center'
  };
}
