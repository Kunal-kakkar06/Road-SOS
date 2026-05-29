import localforage from 'localforage';

const audioCache = localforage.createInstance({
  name: 'roadsos-audio'
});

const treeCache = localforage.createInstance({
  name: 'roadsos-tree'
});

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Premium Offline Decision Tree mapping for absolute offline safety
const LOCAL_TREE = {
  bleeding: {
    text: "How severe is the bleeding?",
    options: ["Minor (small cut)", "Moderate (steady flow)", "Severe (spurting)"],
    nodes: {
      "Minor (small cut)": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Wash your hands with soap and water if possible.",
            "Clean the wound with clean water.",
            "Apply gentle pressure with a clean cloth or bandage.",
            "Apply a sterile bandage or dressing."
          ],
          audio_file_ids: ["bleeding_minor_1", "bleeding_minor_2", "bleeding_minor_3", "bleeding_minor_4"],
          auto_trigger_sos: false
        }
      },
      "Moderate (steady flow)": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Apply direct pressure to the wound with a clean cloth.",
            "Maintain pressure continuously for at least 5 minutes.",
            "If blood soaks through, do not remove the cloth. Add another layer on top.",
            "Elevate the injured area above the heart if possible."
          ],
          audio_file_ids: ["bleeding_mod_1", "bleeding_mod_2", "bleeding_mod_3", "bleeding_mod_4"],
          auto_trigger_sos: false
        }
      },
      "Severe (spurting)": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Call emergency services immediately.",
            "Apply firm, continuous direct pressure to the wound using a clean cloth.",
            "Do not remove any impaled objects. Apply pressure around the object.",
            "If bleeding does not stop and is on a limb, consider using a tourniquet 2 inches above the wound."
          ],
          audio_file_ids: ["bleeding_sev_1", "bleeding_sev_2", "bleeding_sev_3", "bleeding_sev_4"],
          auto_trigger_sos: true
        }
      }
    }
  },
  choking: {
    text: "Is the person able to cough, speak, or breathe?",
    options: ["Yes (Partial airway block)", "No (Complete airway block)"],
    nodes: {
      "Yes (Partial airway block)": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Encourage the person to keep coughing forcefully.",
            "Do not give them anything to drink.",
            "Do not strike them on the back, as it might lodge the object deeper.",
            "Stay with them and monitor their breathing."
          ],
          audio_file_ids: ["choking_part_1", "choking_part_2", "choking_part_3", "choking_part_4"],
          auto_trigger_sos: false
        }
      },
      "No (Complete airway block)": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Call emergency services immediately.",
            "Stand behind the person and lean them slightly forward.",
            "Give 5 firm back blows between their shoulder blades using the heel of your hand.",
            "Give 5 quick upward abdominal thrusts (Heimlich maneuver) just above their navel.",
            "Alternate between 5 back blows and 5 abdominal thrusts until the object is dislodged."
          ],
          audio_file_ids: ["choking_comp_1", "choking_comp_2", "choking_comp_3", "choking_comp_4", "choking_comp_5"],
          auto_trigger_sos: true
        }
      }
    }
  },
  burns: {
    text: "What caused the burn?",
    options: ["Heat/Fire/Scalding", "Chemical", "Electrical"],
    nodes: {
      "Heat/Fire/Scalding": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Cool the burn immediately with cool running water for at least 10 minutes.",
            "Remove any tight items, such as rings or clothing, from the burned area.",
            "Do not break blisters or apply ointments, butter, or ice.",
            "Cover the burn loosely with a sterile, non-fluffy dressing or cling film."
          ],
          audio_file_ids: ["burns_heat_1", "burns_heat_2", "burns_heat_3", "burns_heat_4"],
          auto_trigger_sos: false
        }
      },
      "Chemical": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Call emergency services immediately.",
            "Brush off any dry chemicals using gloves or a cloth.",
            "Rinse the area with a steady stream of cool water for at least 20 minutes.",
            "Remove contaminated clothing while continuing to flush with water."
          ],
          audio_file_ids: ["burns_chem_1", "burns_chem_2", "burns_chem_3", "burns_chem_4"],
          auto_trigger_sos: true
        }
      },
      "Electrical": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Call emergency services immediately.",
            "Do not touch the person if they are still in contact with the electrical source.",
            "Turn off the source of electricity if it is safe to do so.",
            "Once safe, check for breathing and a heartbeat. Be prepared to start CPR."
          ],
          audio_file_ids: ["burns_elec_1", "burns_elec_2", "burns_elec_3", "burns_elec_4"],
          auto_trigger_sos: true
        }
      }
    }
  },
  cpr: {
    text: "Is the person responsive and breathing normally?",
    options: ["Yes, breathing normally", "No, not breathing or gasping"],
    nodes: {
      "Yes, breathing normally": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Place the person in the recovery position.",
            "Roll them onto their side, support their head, and bend their top knee to stabilize them.",
            "Keep their airway open by tilting their head back slightly.",
            "Monitor their breathing continuously until help arrives."
          ],
          audio_file_ids: ["cpr_recov_1", "cpr_recov_2", "cpr_recov_3", "cpr_recov_4"],
          auto_trigger_sos: false
        }
      },
      "No, not breathing or gasping": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Call emergency services immediately.",
            "Place the heel of your hand on the center of the person's chest, and place your other hand on top.",
            "Push hard and fast. Compress the chest at least 2 inches deep at a rate of 100 to 120 compressions per minute.",
            "Allow the chest to rise completely between compressions.",
            "Do not stop until the person starts breathing, an AED arrives, or emergency personnel take over."
          ],
          audio_file_ids: ["cpr_start_1", "cpr_start_2", "cpr_start_3", "cpr_start_4", "cpr_start_5"],
          auto_trigger_sos: true
        }
      }
    }
  }
};

export const downloadOfflinePack = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/voice-guidance/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ injury_type: 'mock', severity: 'mock' })
    });
  } catch (e) {
    console.warn("Failed to download pack (safely operating offline mode)", e);
  }
};

// Play audio from server cache, falling back beautifully to browser's SpeechSynthesis TTS if offline
export const playInstructionAudio = async (instructionId, fallbackText, langCode = 'en-US') => {
  try {
    let blob = await audioCache.getItem(instructionId);
    
    // If not in cache and online, attempt fetching from server
    if (!blob && navigator.onLine) {
      const res = await fetch(`${API_BASE}/api/voice-guidance/audio/${instructionId}`);
      if (res.ok) {
        blob = await res.blob();
        await audioCache.setItem(instructionId, blob);
      }
    }
    
    if (blob && langCode === 'en-US') {
      return new Promise((resolve, reject) => {
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => {
          URL.revokeObjectURL(url);
          resolve();
        };
        audio.onerror = (e) => reject(e);
        audio.play().catch(reject);
      });
    } else {
      // Offline or non-English fallback: Use native browser Speech Synthesis (TTS) in chosen language
      return new Promise((resolve) => {
        if ('speechSynthesis' in window && fallbackText) {
          window.speechSynthesis.cancel(); // Cancel active speeches
          const utterance = new SpeechSynthesisUtterance(fallbackText);
          utterance.lang = langCode;
          utterance.onend = () => resolve();
          utterance.onerror = () => resolve();
          window.speechSynthesis.speak(utterance);
        } else {
          resolve();
        }
      });
    }
  } catch (error) {
    console.warn("Audio file failed or offline, falling back to TTS:", error);
    // Silent fallback to browser TTS directly on error
    return new Promise((resolve) => {
      if ('speechSynthesis' in window && fallbackText) {
        const utterance = new SpeechSynthesisUtterance(fallbackText);
        utterance.lang = langCode;
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
      } else {
        resolve();
      }
    });
  }
};


export const getDecisionTreeProgress = async (currentNode, userAnswer) => {
  try {
    if (!navigator.onLine) {
      throw new Error("Offline mode active");
    }
    const res = await fetch(`${API_BASE}/api/voice-guidance/decision-tree`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_node: currentNode, user_answer: userAnswer })
    });
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.warn("Failed to progress online decision tree, using local offline fallback", e);
    // Offline fallback: Query local decision tree
    const root = LOCAL_TREE[currentNode];
    if (root && root.nodes && root.nodes[userAnswer]) {
      return root.nodes[userAnswer];
    }
    return null;
  }
};

export const generateGuidance = async (injuryType, severity) => {
  try {
    if (!navigator.onLine) {
      throw new Error("Offline mode active");
    }
    const res = await fetch(`${API_BASE}/api/voice-guidance/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ injury_type: injuryType, severity })
    });
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.warn("Failed to query online guidance, using local offline fallback", e);
    // Offline fallback: return local tree start nodes
    const root = LOCAL_TREE[injuryType];
    if (root) {
      return {
        decision_tree_start: {
          text: root.text,
          options: root.options
        }
      };
    }
    return null;
  }
};

export const getNearbyResponders = async (lat, lng) => {
  try {
    if (!navigator.onLine) {
      throw new Error("Offline mode active");
    }
    const res = await fetch(`${API_BASE}/api/voice-guidance/nearby-responders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng })
    });
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.warn("Failed to fetch responders online, reporting offline status", e);
    return { responders: [] };
  }
};
