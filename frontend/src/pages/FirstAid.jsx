import { useState } from 'react';
import { Link } from 'react-router-dom';

/* ── First Aid Guide Database ── */
const FIRST_AID_GUIDES = [
  {
    id: 'cpr',
    title: 'CPR (Adult)',
    icon: 'heart_pulse',
    color: '#ba1a1a', // Emergency Red
    bg: '#FCEBEB',
    condition: 'Unresponsive patient with absent or agonal breathing',
    steps: [
      {
        title: 'Verify Response & Breathing',
        desc: 'Tap shoulders and shout "Are you okay?". Scan chest for rise and fall for max 10 seconds.'
      },
      {
        title: 'Emergency Dispatch (108 / 112)',
        desc: 'If unresponsive and not breathing, immediately call 108 or activate your main RoadSOS dashboard.'
      },
      {
        title: 'Perform 30 Chest Compressions',
        desc: 'Place heel of one hand in center of chest, other hand on top. Push down 2 to 2.4 inches at a rate of 100-120 compressions per minute (to the beat of "Staying Alive").'
      },
      {
        title: 'Give 2 Rescue Breaths',
        desc: 'Tilt head back, lift chin, pinch nose, and blow into mouth until chest visibly rises. (Optional: perform compressions-only CPR if mouth-to-mouth is not feasible).'
      },
      {
        title: 'Repeat & Monitor',
        desc: 'Keep repeating the cycle of 30 compressions and 2 breaths until paramedics arrive, or patient shows signs of life.'
      }
    ]
  },
  {
    id: 'bleeding',
    title: 'Severe Bleeding',
    icon: 'bloodtype',
    color: '#E63946', // Vibrant Blood Red
    bg: '#FFF0F2',
    condition: 'Heavy spurting or continuous bleeding from deep cuts/lacerations',
    steps: [
      {
        title: 'Ensure Safety & Apply Pressure',
        desc: 'Put on gloves if available. Apply firm, direct pressure on the bleeding wound with a sterile gauze or clean cloth.'
      },
      {
        title: 'Maintain Constant Compression',
        desc: 'Do not lift the cloth to check bleeding. Keep holding firm pressure. If blood seeps through, place another layer of cloth directly on top and continue pressing.'
      },
      {
        title: 'Elevate Above Heart',
        desc: 'If possible and if no fracture is suspected, elevate the bleeding limb above the level of the patient\'s heart to slow the blood flow.'
      },
      {
        title: 'Secure with Bandage',
        desc: 'Wrap the gauze tightly with a bandage. Ensure it is firm but not tight enough to stop arterial circulation (check pulse below the wrap).'
      },
      {
        title: 'Tourniquet Fallback',
        desc: 'If bleeding from a limb is catastrophic and uncontrolled by direct pressure, apply a tourniquet 2 inches above the wound (never on joints).'
      }
    ]
  },
  {
    id: 'choking',
    title: 'Choking (Heimlich)',
    icon: 'medical_services',
    color: '#fca311', // Caution Orange
    bg: '#FFF9EE',
    condition: 'Inability to speak, cough, or breathe due to severe airway obstruction',
    steps: [
      {
        title: 'Confirm Airway Obstruction',
        desc: 'Ask "Are you choking?". If they can nod but cannot speak, cough, or breathe, initiate immediate first aid.'
      },
      {
        title: 'Deliver 5 Back Blows',
        desc: 'Lean patient forward. Support chest with one hand, and strike firmly between their shoulder blades with the heel of your other hand 5 times.'
      },
      {
        title: 'Deliver 5 Abdominal Thrusts',
        desc: 'Stand behind patient. Wrap arms around waist. Make a fist, place it slightly above their navel, grab it with other hand, and push quickly in and upward 5 times.'
      },
      {
        title: 'Alternate the Cycle',
        desc: 'Alternate between 5 back blows and 5 abdominal thrusts until the object is expelled, or they lose consciousness.'
      },
      {
        title: 'If Patient Becomes Unconscious',
        desc: 'Gently lay them down on the floor. Immediately call 108 and begin CPR compressions. Check mouth for visible object before breaths.'
      }
    ]
  },
  {
    id: 'fractures',
    title: 'Fractures & Sprains',
    icon: 'boy',
    color: '#006687', // Safe Blue
    bg: '#E6F1FB',
    condition: 'Suspected broken bones, severe joint sprains, or visible deformity',
    steps: [
      {
        title: 'Stop Movement Immediately',
        desc: 'Keep the patient still. Do not try to realign the broken bone or push protruding bone fragments back inside.'
      },
      {
        title: 'Control Any Bleeding',
        desc: 'If there is an open wound with bleeding, apply pressure around the bone edge with clean dressing, not directly on the bone.'
      },
      {
        title: 'Immobilize & Splint',
        desc: 'Support the injured area using rolled magazines, wooden planks, or cardboard wrapped in soft towels. Bind it gently above and below the fracture.'
      },
      {
        title: 'Apply Cold Pack',
        desc: 'Apply a cold compress or ice pack wrapped in a cloth to reduce swelling and pain. Do not place ice directly on raw skin.'
      },
      {
        title: 'Check Distal Circulation',
        desc: 'Check pulse, warmth, and sensation below the splinted area. If fingers/toes turn blue or cold, loosen the ties slightly.'
      }
    ]
  },
  {
    id: 'burns',
    title: 'Burns & Scalds',
    icon: 'mode_heat',
    color: '#d97706', // Hot Amber
    bg: '#FEF3C7',
    condition: 'Thermal burns from fire, steam, boiling liquids, or chemicals',
    steps: [
      {
        title: 'Cool Under Cool Running Water',
        desc: 'Immediately hold the burned skin under cool, slow-running tap water for at least 10 to 20 minutes to stop the burning process.'
      },
      {
        title: 'Remove Jewelry & Tight Clothing',
        desc: 'Gently remove rings, bracelets, or tight garments from the burned area before swelling starts. Do not pull off clothing stuck to the raw burn.'
      },
      {
        title: 'Protect with Loose Wrap',
        desc: 'Cover the burn loosely with a clean plastic wrap, clean zip-lock bag, or a sterile non-stick gauze to shield it from infection.'
      },
      {
        title: 'Do NOT Apply Ice or Remedies',
        desc: 'Never apply ice, butter, grease, toothpaste, or home remedies, as they trap heat in tissues and invite serious infections.'
      },
      {
        title: 'Manage Pain & Hydration',
        desc: 'Keep the patient warm and hydrated. Seek immediate professional emergency help if the burn is larger than the palm of their hand.'
      }
    ]
  }
];

export default function FirstAid() {
  const [activeGuide, setActiveGuide] = useState(FIRST_AID_GUIDES[0]);
  const [stepChecklist, setStepChecklist] = useState({});

  const toggleCheck = (guideId, stepIdx) => {
    const key = `${guideId}-${stepIdx}`;
    setStepChecklist(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const getCompletedCount = (guide) => {
    return guide.steps.reduce((acc, _, idx) => {
      return acc + (stepChecklist[`${guide.id}-${idx}`] ? 1 : 0);
    }, 0);
  };

  return (
    <div className="fade-in" style={{ paddingBottom: 60, maxWidth: 850, margin: '0 auto' }}>
      
      {/* ── Top Header Bento Row ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12, marginBottom: 18
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="material-symbols-outlined icon-fill" style={{ fontSize: 28, color: '#fca311' }}>
              health_and_safety
            </span>
            <h1 style={{
              fontFamily: 'Space Grotesk, sans-serif',
              fontSize: 22, fontWeight: 700, color: '#fff', margin: 0
            }}>
              First Aid Guide
            </h1>
          </div>
          <p style={{ fontSize: 12, color: '#a0aab2', margin: '3px 0 0' }}>
            Interactive, offline-cached step-by-step emergency medical guides
          </p>
        </div>

        {/* Offline Badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'rgba(39, 174, 96, 0.1)', border: '1px solid rgba(39, 174, 96, 0.25)',
          borderRadius: 20, padding: '5px 12px', fontSize: 11, fontWeight: 700, color: '#27AE60'
        }}>
          <span className="material-symbols-outlined icon-fill" style={{ fontSize: 14 }}>verified</span>
          100% Cached Offline
        </div>
      </div>

      {/* ── Quick Emergency Dispatch Call Strip ── */}
      <div style={{
        background: '#ba1a1a', borderRadius: 12, padding: '14px 18px',
        color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 12, marginBottom: 16,
        boxShadow: '0 4px 15px rgba(186,26,26,0.25)'
      }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span className="material-symbols-outlined icon-fill" style={{ fontSize: 24 }}>emergency</span>
          <div>
            <p style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 14, fontWeight: 700, margin: 0 }}>
              Life Threatening Emergency?
            </p>
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.8)', margin: '2px 0 0' }}>
              Do not wait. Dial local ambulance or use SOS button immediately.
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <a href="tel:108" style={{
            background: '#fff', color: '#ba1a1a', padding: '8px 16px', borderRadius: 8,
            fontSize: 12, fontWeight: 800, textDecoration: 'none', fontFamily: 'Space Grotesk, sans-serif',
            display: 'flex', alignItems: 'center', gap: 6
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>call</span>
            Call 108
          </a>
          <Link to="/" style={{
            background: 'rgba(255,255,255,0.18)', color: '#fff', padding: '8px 16px', borderRadius: 8,
            fontSize: 12, fontWeight: 800, textDecoration: 'none', fontFamily: 'Space Grotesk, sans-serif'
          }}>
            Trigger SOS
          </Link>
        </div>
      </div>

      {/* ── Main Bento Grid Layout ── */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr', gap: 16
      }}>
        
        {/* Row 1: Horizontal Category Selector Chips */}
        <div style={{
          display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 6,
          scrollbarWidth: 'none', WebkitOverflowScrolling: 'touch'
        }}>
          {FIRST_AID_GUIDES.map(guide => {
            const isActive = activeGuide.id === guide.id;
            const completed = getCompletedCount(guide);
            const total = guide.steps.length;

            return (
              <button
                key={guide.id}
                onClick={() => setActiveGuide(guide)}
                style={{
                  flexShrink: 0, padding: '12px 18px', borderRadius: 12,
                  background: isActive ? '#fff' : '#14213D',
                  border: isActive ? `2px solid ${guide.color}` : '1px solid rgba(255,255,255,0.08)',
                  color: isActive ? '#14213D' : '#a0aab2',
                  cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
                  fontWeight: 700, fontSize: 13,
                  display: 'flex', alignItems: 'center', gap: 8,
                  transition: 'all 0.15s'
                }}
              >
                <span
                  className="material-symbols-outlined icon-fill"
                  style={{ fontSize: 18, color: isActive ? guide.color : '#6b7280' }}
                >
                  {guide.icon}
                </span>
                <span>{guide.title}</span>
                <span style={{
                  fontSize: 10, background: isActive ? guide.color : 'rgba(255,255,255,0.06)',
                  color: isActive ? '#fff' : '#a0aab2',
                  padding: '2px 6px', borderRadius: 8
                }}>
                  {completed}/{total}
                </span>
              </button>
            );
          })}
        </div>

        {/* Row 2: Selected Guide Detail Card */}
        <div style={{
          background: '#14213D', borderRadius: 16, padding: '20px',
          border: '1px solid rgba(255,255,255,0.08)'
        }}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyItems: 'center',
            gap: 12, marginBottom: 14,
            paddingBottom: 14, borderBottom: '1px dashed rgba(255,255,255,0.08)'
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: activeGuide.bg, display: 'flex', alignItems: 'center',
              justifyContent: 'center', flexShrink: 0
            }}>
              <span
                className="material-symbols-outlined icon-fill"
                style={{ fontSize: 22, color: activeGuide.color }}
              >
                {activeGuide.icon}
              </span>
            </div>
            <div>
              <h2 style={{
                fontFamily: 'Space Grotesk, sans-serif', fontSize: 18,
                fontWeight: 700, color: '#fff', margin: 0
              }}>
                {activeGuide.title} Instructions
              </h2>
              <p style={{ fontSize: 12, color: '#a0aab2', margin: '3px 0 0' }}>
                When: <strong style={{ color: activeGuide.color }}>{activeGuide.condition}</strong>
              </p>
            </div>
          </div>

          {/* Interactive Steps List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {activeGuide.steps.map((step, idx) => {
              const isChecked = !!stepChecklist[`${activeGuide.id}-${idx}`];

              return (
                <div
                  key={idx}
                  onClick={() => toggleCheck(activeGuide.id, idx)}
                  style={{
                    background: isChecked ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.01)',
                    border: isChecked ? `1.5px solid ${activeGuide.color}55` : '1px solid rgba(255,255,255,0.05)',
                    borderRadius: 12, padding: '14px 16px',
                    cursor: 'pointer', transition: 'all 0.15s',
                    display: 'flex', alignItems: 'flex-start', gap: 14
                  }}
                >
                  {/* Step Number Checkbox */}
                  <div style={{
                    width: 26, height: 26, borderRadius: '50%',
                    background: isChecked ? activeGuide.color : 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: 12, fontWeight: 700, flexShrink: 0,
                    transition: 'background 0.15s'
                  }}>
                    {isChecked ? (
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>check</span>
                    ) : (
                      idx + 1
                    )}
                  </div>

                  {/* Step texts */}
                  <div style={{ flex: 1 }}>
                    <p style={{
                      fontFamily: 'Space Grotesk, sans-serif', fontSize: 14,
                      fontWeight: 700, color: '#fff', margin: '0 0 4px',
                      textDecoration: isChecked ? 'line-through' : 'none',
                      opacity: isChecked ? 0.6 : 1
                    }}>
                      {step.title}
                    </p>
                    <p style={{
                      fontSize: 12.5, color: '#a0aab2', margin: 0, lineHeight: 1.5,
                      opacity: isChecked ? 0.6 : 1
                    }}>
                      {step.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Action completion metrics */}
          <div style={{
            marginTop: 18, background: 'rgba(255,255,255,0.02)',
            padding: '12px 16px', borderRadius: 10, display: 'flex',
            alignItems: 'center', justifyItems: 'center', justifyContent: 'space-between',
            border: '1px solid rgba(255,255,255,0.05)'
          }}>
            <div>
              <p style={{ fontSize: 12, fontWeight: 700, color: '#fff', margin: 0 }}>Action Progress</p>
              <p style={{ fontSize: 10.5, color: '#a0aab2', margin: '2px 0 0' }}>
                Mark steps complete as you execute them.
              </p>
            </div>
            <div style={{
              fontSize: 13, fontWeight: 700, color: activeGuide.color,
              fontFamily: 'Space Grotesk, sans-serif',
              background: activeGuide.bg, padding: '4px 10px', borderRadius: 6
            }}>
              {Math.round((getCompletedCount(activeGuide) / activeGuide.steps.length) * 100)}% Done
            </div>
          </div>
        </div>

        {/* Back Link Row */}
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
          <Link to="/" style={{
            color: '#a0aab2', fontSize: 13, fontWeight: 600,
            textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_back</span>
            Back to Dashboard
          </Link>
        </div>

      </div>
    </div>
  );
}
