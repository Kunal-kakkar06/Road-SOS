import { useState, useEffect } from 'react';
import { 
  playInstructionAudio, 
  getDecisionTreeProgress, 
  generateGuidance, 
  getNearbyResponders,
  downloadOfflinePack
} from '../services/voiceGuidanceService';

export default function VoiceGuidance({ onClose, initialInjury = "bleeding" }) {
  const [activeTab, setActiveTab] = useState('tree'); // tree, instructions, nearby, offline
  const [currentNode, setCurrentNode] = useState(initialInjury);
  const [questions, setQuestions] = useState([]);
  const [currentOptions, setCurrentOptions] = useState([]);
  const [currentQuestionText, setCurrentQuestionText] = useState("");
  
  const [steps, setSteps] = useState([]);
  const [audioIds, setAudioIds] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  
  const [responders, setResponders] = useState([]);
  const [isTriggerSOS, setIsTriggerSOS] = useState(false);

  useEffect(() => {
    // Initial load: Fetch the root node of the decision tree for the injury
    loadInitialTree(initialInjury);
  }, [initialInjury]);

  const loadInitialTree = async (injury) => {
    // We can simulate fetching the first question
    const res = await generateGuidance(injury, "minor"); // The backend fallback logic returns the start of the tree
    if (res && res.decision_tree_start) {
      setCurrentQuestionText(res.decision_tree_start.text);
      setCurrentOptions(res.decision_tree_start.options);
      setActiveTab('tree');
    }
  };

  const handleOptionSelect = async (option) => {
    const res = await getDecisionTreeProgress(currentNode, option);
    if (res && res.is_complete && res.final_instruction) {
      setSteps(res.final_instruction.steps);
      setAudioIds(res.final_instruction.audio_file_ids);
      setIsTriggerSOS(res.final_instruction.auto_trigger_sos);
      setCurrentStepIndex(0);
      setActiveTab('instructions');
      
      // Auto-play first step
      if (res.final_instruction.audio_file_ids.length > 0) {
        playStep(0, res.final_instruction.audio_file_ids);
      }
    } else if (res && !res.is_complete) {
      setCurrentQuestionText(res.next_question);
      setCurrentOptions(res.options);
    }
  };

  const playStep = async (index, audioArray = audioIds) => {
    if (index >= audioArray.length) return;
    setIsPlaying(true);
    await playInstructionAudio(audioArray[index]);
    setIsPlaying(false);
    
    // Auto-advance
    if (index + 1 < audioArray.length) {
      setCurrentStepIndex(index + 1);
      playStep(index + 1, audioArray);
    }
  };

  const handleNext = () => {
    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
      playStep(currentStepIndex + 1);
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
      playStep(currentStepIndex - 1);
    }
  };

  const fetchResponders = async () => {
    // mock coords
    const lat = 12.9716;
    const lng = 77.5946;
    const res = await getNearbyResponders(lat, lng);
    if (res && res.responders) {
      setResponders(res.responders);
    }
  };

  const styles = {
    modal: {
      position: 'fixed', inset: 0, zIndex: 10000,
      background: '#fff', display: 'flex', flexDirection: 'column',
      fontFamily: 'Space Grotesk, sans-serif'
    },
    header: {
      background: '#14213D', color: '#fff', padding: '16px 20px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      fontWeight: 700, fontSize: 18
    },
    tabs: {
      display: 'flex', borderBottom: '1px solid #ddd', background: '#f8f9fa'
    },
    tab: (active) => ({
      flex: 1, padding: '12px 0', textAlign: 'center',
      fontWeight: 700, fontSize: 13, cursor: 'pointer',
      color: active ? '#fca311' : '#534433',
      borderBottom: active ? '3px solid #fca311' : '3px solid transparent'
    }),
    content: {
      flex: 1, overflowY: 'auto', padding: 24,
      display: 'flex', flexDirection: 'column'
    },
    largeBtn: {
      padding: '20px', borderRadius: 12, border: '2px solid #14213D',
      background: '#fff', color: '#14213D', fontSize: 16, fontWeight: 700,
      cursor: 'pointer', marginBottom: 12, textAlign: 'left',
      minHeight: 64, display: 'flex', alignItems: 'center'
    },
    sosBtn: {
      padding: '20px', borderRadius: 12, border: 'none',
      background: '#ba1a1a', color: '#fff', fontSize: 16, fontWeight: 700,
      cursor: 'pointer', marginTop: 24, textAlign: 'center'
    }
  };

  return (
    <div style={styles.modal}>
      <div style={styles.header}>
        <span>🎧 First Aid Voice Guidance</span>
        <span className="material-symbols-outlined" style={{cursor:'pointer'}} onClick={onClose}>close</span>
      </div>
      
      <div style={styles.tabs}>
        <div style={styles.tab(activeTab === 'tree')} onClick={() => setActiveTab('tree')}>Assessment</div>
        <div style={styles.tab(activeTab === 'instructions')} onClick={() => setActiveTab('instructions')}>Steps</div>
        <div style={styles.tab(activeTab === 'nearby')} onClick={() => { setActiveTab('nearby'); fetchResponders(); }}>Nearby Help</div>
        <div style={styles.tab(activeTab === 'offline')} onClick={() => setActiveTab('offline')}>Offline</div>
      </div>
      
      <div style={styles.content}>
        
        {/* TAB 1: Decision Tree */}
        {activeTab === 'tree' && (
          <div style={{animation: 'fadeIn 0.3s'}}>
            <p style={{fontSize: 22, fontWeight: 700, color: '#14213D', marginBottom: 24}}>
              {currentQuestionText || "Loading assessment..."}
            </p>
            {currentOptions.map((opt, i) => (
              <button key={i} style={styles.largeBtn} onClick={() => handleOptionSelect(opt)}>
                {opt}
              </button>
            ))}
          </div>
        )}

        {/* TAB 2: Instructions */}
        {activeTab === 'instructions' && (
          <div style={{animation: 'fadeIn 0.3s', display:'flex', flexDirection:'column', height:'100%'}}>
            {steps.length > 0 ? (
              <>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20}}>
                  <span style={{fontSize:14, fontWeight:700, color:'#534433'}}>
                    Step {currentStepIndex + 1} of {steps.length}
                  </span>
                  {isPlaying ? (
                    <span className="material-symbols-outlined" style={{color:'#27AE60', animation:'pulse 1s infinite'}}>volume_up</span>
                  ) : (
                    <span className="material-symbols-outlined" style={{color:'#867461'}} onClick={() => playStep(currentStepIndex)}>play_circle</span>
                  )}
                </div>
                
                <p style={{fontSize: 28, fontWeight: 700, color: '#14213D', lineHeight: 1.3, flex:1}}>
                  {steps[currentStepIndex]}
                </p>

                {isTriggerSOS && (
                  <button style={styles.sosBtn} onClick={() => alert("SOS Triggered!")}>
                    🚨 SEND EMERGENCY SOS
                  </button>
                )}

                <div style={{display:'flex', gap:12, marginTop:24}}>
                  <button 
                    onClick={handlePrev} 
                    disabled={currentStepIndex === 0}
                    style={{...styles.largeBtn, flex:1, marginBottom:0, textAlign:'center', justifyContent:'center', opacity: currentStepIndex===0?0.5:1}}
                  >
                    Previous
                  </button>
                  <button 
                    onClick={handleNext} 
                    disabled={currentStepIndex === steps.length - 1}
                    style={{...styles.largeBtn, flex:1, marginBottom:0, textAlign:'center', justifyContent:'center', background:'#14213D', color:'#fff', opacity: currentStepIndex===steps.length-1?0.5:1}}
                  >
                    Next
                  </button>
                </div>
              </>
            ) : (
              <p>Please complete the assessment first.</p>
            )}
          </div>
        )}

        {/* TAB 3: Nearby Help */}
        {activeTab === 'nearby' && (
          <div style={{animation: 'fadeIn 0.3s'}}>
            <p style={{fontSize: 20, fontWeight: 700, color: '#14213D', marginBottom: 16}}>
              First-Aiders within 500m
            </p>
            {responders.length > 0 ? responders.map((r, i) => (
              <div key={i} style={{padding:16, border:'1px solid #ddd', borderRadius:12, marginBottom:12}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                  <span style={{fontWeight:700, fontSize:16}}>{r.name}</span>
                  <span style={{color:'#fca311', fontWeight:700, fontSize:14}}>{r.eta_min} min away</span>
                </div>
                <p style={{color:'#534433', fontSize:13, marginTop:4}}>{r.cert_level} · {r.distance_m}m</p>
              </div>
            )) : <p>Searching for nearby help...</p>}
            
            <button style={{...styles.largeBtn, width:'100%', textAlign:'center', justifyContent:'center', background:'#fca311', color:'#663f00', border:'none', marginTop:12}}>
              Ping All Responders
            </button>
          </div>
        )}

        {/* TAB 4: Offline Status */}
        {activeTab === 'offline' && (
          <div style={{animation: 'fadeIn 0.3s'}}>
            <p style={{fontSize: 20, fontWeight: 700, color: '#14213D', marginBottom: 16}}>
              Offline Storage
            </p>
            <div style={{padding:20, background:'#f8f9fa', borderRadius:12, textAlign:'center'}}>
              <span className="material-symbols-outlined" style={{fontSize:48, color:'#27AE60', marginBottom:12}}>cloud_done</span>
              <p style={{fontWeight:700, fontSize:16}}>Voice Guidance is available offline.</p>
              <p style={{color:'#534433', fontSize:13, marginTop:8}}>Audio files and decision trees are securely cached on your device for emergency situations without internet.</p>
            </div>
            <button 
              onClick={downloadOfflinePack}
              style={{...styles.largeBtn, width:'100%', textAlign:'center', justifyContent:'center', marginTop:24}}
            >
              Force Sync Offline Data
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
