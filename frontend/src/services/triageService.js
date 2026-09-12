const API_BASE = import.meta.env.VITE_API_URL || 'https://road-sos-l5ck.onrender.com';

async function fetchWithTimeout(url, options = {}, timeout = 12000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    if (response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('userRole');
      window.location.href = '/login';
      throw new Error('Session expired. Please log in again.');
    }
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please check your connection.');
    }
    throw error;
  }
}

export async function submitTriage(data) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetchWithTimeout(`${API_BASE}/api/triage`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  }, 10000);
  if (!response.ok) {
    throw new Error('Failed to submit triage diagnostic');
  }
  return await response.json();
}

export async function submitAsyncTriage(data) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetchWithTimeout(`${API_BASE}/api/triage/async`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  }, 10000);
  if (!response.ok) {
    throw new Error('Failed to queue async triage diagnostic');
  }
  return await response.json();
}

export async function getTriageJobStatus(jobId) {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetchWithTimeout(`${API_BASE}/api/triage/jobs/${jobId}`, {
    method: 'GET',
    headers,
  }, 5000);
  if (!response.ok) {
    throw new Error('Failed to retrieve triage job status');
  }
  return await response.json();
}

export async function uploadTriageImage(file) {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const formData = new FormData();
  if (file) {
    formData.append('file', file, file.name || 'image.jpg');
  }
  const response = await fetchWithTimeout(`${API_BASE}/api/triage/image`, {
    method: 'POST',
    headers,
    body: formData,
  }, 10000);
  if (!response.ok) {
    throw new Error('Failed to upload triage image');
  }
  return await response.json();
}

export async function uploadTriageVoice(file) {
  if (!file) {
    return { transcript: "I am feeling dizzy, have strong chest pain and cannot breathe properly." };
  }
  
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const formData = new FormData();
  formData.append('file', file, file.name || 'voice.wav');
  const response = await fetchWithTimeout(`${API_BASE}/api/triage/voice`, {
    method: 'POST',
    headers,
    body: formData,
  }, 12000);
  if (!response.ok) {
    throw new Error('Failed to upload triage voice');
  }
  return await response.json();
}

export async function getTriageHistory() {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetchWithTimeout(`${API_BASE}/api/triage/history`, {
    method: 'GET',
    headers,
  }, 10000);
  
  if (!response.ok) {
    throw new Error('Failed to fetch triage history');
  }
  return await response.json();
}

export async function runTriage({
  imageFile,
  audioBlob,
  sensorData,
  textInput,
  manualAnswers,
  incidentId,
  userId
}) {
  let imageLabel = null;
  let voiceTranscript = null;

  // 1. Upload image if exists
  if (imageFile) {
    try {
      const imgRes = await uploadTriageImage(imageFile);
      imageLabel = imgRes.label;
    } catch (e) {
      console.warn("Image upload failed", e);
    }
  }

  // 2. Upload voice if exists
  if (audioBlob) {
    try {
      const voiceRes = await uploadTriageVoice(audioBlob);
      voiceTranscript = voiceRes.transcript;
    } catch (e) {
      console.warn("Voice upload failed", e);
    }
  }

  // 3. Collect medical profile attributes
  let age = 35;
  let gender = "unspecified";
  try {
    const profile = JSON.parse(localStorage.getItem('medicalProfile') || '{}');
    if (profile.date_of_birth) {
      const birthDate = new Date(profile.date_of_birth);
      const today = new Date();
      let calculatedAge = today.getFullYear() - birthDate.getFullYear();
      const m = today.getMonth() - birthDate.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
        calculatedAge--;
      }
      age = calculatedAge;
    } else if (profile.age) {
      age = profile.age;
    }
    if (profile.gender) gender = profile.gender;
  } catch (_) {}

  // 4. Build symptoms text from inputs
  let symptoms = textInput || "";
  if (manualAnswers && manualAnswers.visible_bleeding) {
    symptoms += (symptoms ? ", " : "") + "visible bleeding";
  }

  const payload = {
    age,
    gender,
    symptoms: symptoms || "General assessment",
    consciousness: manualAnswers ? (manualAnswers.conscious ? "Alert" : "Unresponsive") : "Alert",
    breathing: manualAnswers ? (manualAnswers.conscious ? "Normal" : "Absent") : "Normal",
    image_label: imageLabel,
    voice_transcript: voiceTranscript
  };

  // 5. Submit triage
  const backendRes = await submitTriage(payload);

  // 6. Map backend response to what SeverityResult expects
  const sevMap = {
    Critical: 'P1',
    High: 'P2',
    Moderate: 'P3',
    Low: 'P4'
  };
  const colorMap = {
    P1: '#ba1a1a',
    P2: '#fca311',
    P3: '#006687',
    P4: '#27AE60'
  };
  const severityCode = sevMap[backendRes.severity_level] || 'P2';

  // Construct shap factors array
  const shapFactors = Object.entries(backendRes.shap_values || {}).map(([key, val]) => ({
    feature: key,
    label: `${key.charAt(0).toUpperCase() + key.slice(1)} variance contribution (${val > 0 ? '+' : ''}${val})`
  }));

  return {
    severity: severityCode,
    severity_label: backendRes.assessment,
    severity_color: colorMap[severityCode] || '#fca311',
    confidence: (backendRes.severity_score / 100) * 0.95 + 0.05,
    shap_factors: shapFactors,
    signals_used: {
      photo: !!imageFile,
      voice: !!audioBlob,
      text: !!textInput,
      sensors: !!sensorData,
      manual: !!manualAnswers
    },
    transcript: voiceTranscript,
    was_offline: !navigator.onLine,
    event_id: "triage_" + Date.now()
  };
}
