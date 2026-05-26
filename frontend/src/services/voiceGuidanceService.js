import localforage from 'localforage';

const audioCache = localforage.createInstance({
  name: 'roadsos-audio'
});

const treeCache = localforage.createInstance({
  name: 'roadsos-tree'
});

// Mock the initial download of the tree and all audio files for offline use
export const downloadOfflinePack = async () => {
  try {
    const res = await fetch('/api/voice-guidance/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ injury_type: 'mock', severity: 'mock' })
    });
    // This is just to ensure the backend is reachable in a real app
    // We would actually fetch the full tree JSON here and store it
  } catch (e) {
    console.error("Failed to download pack", e);
  }
};

// Play audio from cache or network
export const playInstructionAudio = async (instructionId) => {
  try {
    let blob = await audioCache.getItem(instructionId);
    if (!blob) {
      const res = await fetch(`http://localhost:8000/static/audio/${instructionId}.mp3`);
      if (res.ok) {
        blob = await res.blob();
        await audioCache.setItem(instructionId, blob);
      } else {
        throw new Error('Audio not found');
      }
    }
    
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
  } catch (error) {
    console.error("Could not play audio", error);
    return Promise.resolve(); // Continue even if audio fails
  }
};

export const getDecisionTreeProgress = async (currentNode, userAnswer) => {
  try {
    const res = await fetch('http://localhost:8000/api/voice-guidance/decision-tree', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_node: currentNode, user_answer: userAnswer })
    });
    return await res.json();
  } catch (e) {
    console.error("Failed to progress decision tree", e);
    // Offline fallback logic would go here
    return null;
  }
};

export const generateGuidance = async (injuryType, severity) => {
  try {
    const res = await fetch('http://localhost:8000/api/voice-guidance/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ injury_type: injuryType, severity })
    });
    return await res.json();
  } catch (e) {
    console.error("Failed to generate guidance", e);
    return null;
  }
};

export const getNearbyResponders = async (lat, lng) => {
  try {
    const res = await fetch('http://localhost:8000/api/voice-guidance/nearby-responders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng })
    });
    return await res.json();
  } catch (e) {
    console.error("Failed to fetch responders", e);
    return { responders: [] };
  }
};
