import localforage from 'localforage';

const audioCache = localforage.createInstance({
  name: 'roadsos-audio'
});

const treeCache = localforage.createInstance({
  name: 'roadsos-tree'
});

// Premium Offline Decision Tree mapping for absolute offline safety
const LOCAL_TREE = {
  bleeding: {
    text: "Is the bleeding severe and spurting?",
    options: ["Yes, severe/spurting", "No, slow/controlled"],
    nodes: {
      "Yes, severe/spurting": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Apply firm, direct pressure on the wound using a clean cloth or sterile dressing.",
            "If pressure does not stop the bleeding and it is on a limb, apply a tourniquet 2-3 inches above the wound.",
            "Tighten the tourniquet until the bleeding stops. Note the exact time it was applied.",
            "Keep the patient calm, lay them flat, and cover them to prevent shock while help arrives."
          ],
          audio_file_ids: ["press_wound", "tourniquet", "tighten", "prevent_shock"],
          auto_trigger_sos: true
        }
      },
      "No, slow/controlled": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Clean the wound gently under running water if possible.",
            "Apply a sterile dressing or clean bandage over the cut.",
            "Elevate the injured limb above the level of the heart to reduce swelling.",
            "Monitor the patient for any signs of dizziness or worsening symptoms."
          ],
          audio_file_ids: ["clean_water", "sterile_bandage", "elevate_limb", "monitor"],
          auto_trigger_sos: false
        }
      }
    }
  },
  fracture: {
    text: "Is there an open wound with visible bone protruding?",
    options: ["Yes, open bone visible", "No, closed fracture"],
    nodes: {
      "Yes, open bone visible": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Do not try to push the bone back in. Cover the wound with a sterile dressing.",
            "Stabilize the joint above and below the fracture using a temporary splint or folded cardboard.",
            "Apply a clean bandage firmly around the splint, but not so tight that it cuts off circulation.",
            "Lay the patient down, keep them warm, and monitor for shock. Await emergency responders."
          ],
          audio_file_ids: ["cover_bone", "temp_splint", "firm_bandage", "monitor_shock"],
          auto_trigger_sos: true
        }
      },
      "No, closed fracture": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Stabilize the injured limb in the position it was found. Do not try to realign it.",
            "Apply a cold compress or ice pack wrapped in a cloth to reduce swelling.",
            "Construct a simple splint to prevent the bone from shifting during movement.",
            "Keep the limb elevated and support it comfortably while awaiting transport."
          ],
          audio_file_ids: ["stabilize_limb", "cold_compress", "prevent_shift", "elevate_support"],
          auto_trigger_sos: false
        }
      }
    }
  },
  choking: {
    text: "Is the victim coughing, or completely unable to speak or breathe?",
    options: ["Coughing weakly", "Completely silent / clutching throat"],
    nodes: {
      "Completely silent / clutching throat": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Stand behind the victim, wrap your arms around their waist, and lean them slightly forward.",
            "Make a fist with one hand and place it slightly above the navel.",
            "Grasp your fist with the other hand and press into the abdomen with quick, upward thrusts.",
            "Repeat abdominal thrusts (Heimlich maneuver) until the blockage is dislodged."
          ],
          audio_file_ids: ["stand_behind", "make_fist", "upward_thrusts", "repeat_heimlich"],
          auto_trigger_sos: true
        }
      },
      "Coughing weakly": {
        is_complete: true,
        final_instruction: {
          steps: [
            "Encourage the victim to cough forcefully to clear the blockage naturally.",
            "Stand slightly to the side and support their chest with one hand.",
            "Deliver up to five sharp back blows between their shoulder blades using the heel of your hand.",
            "If the object is not dislodged and they stop coughing, prepare to perform abdominal thrusts."
          ],
          audio_file_ids: ["encourage_cough", "support_chest", "back_blows", "prepare_thrusts"],
          auto_trigger_sos: false
        }
      }
    }
  }
};

export const downloadOfflinePack = async () => {
  try {
    const res = await fetch('/api/voice-guidance/generate', {
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
      const res = await fetch(`http://localhost:8000/static/audio/${instructionId}.mp3`);
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
    const res = await fetch('http://localhost:8000/api/voice-guidance/decision-tree', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_node: currentNode, user_answer: userAnswer })
    });
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
    const res = await fetch('http://localhost:8000/api/voice-guidance/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ injury_type: injuryType, severity })
    });
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
    const res = await fetch('http://localhost:8000/api/voice-guidance/nearby-responders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng })
    });
    return await res.json();
  } catch (e) {
    console.warn("Failed to fetch responders online, reporting offline status", e);
    return { responders: [] };
  }
};
