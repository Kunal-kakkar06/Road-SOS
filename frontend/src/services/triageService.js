const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function submitTriage(data) {
  const response = await fetch(`${API_BASE}/api/triage`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('Failed to submit triage diagnostic');
  }
  return await response.json();
}

export async function uploadTriageImage(file) {
  const formData = new FormData();
  if (file) {
    formData.append('file', file);
  }
  const response = await fetch(`${API_BASE}/api/triage/image`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error('Failed to upload triage image');
  }
  return await response.json();
}

export async function uploadTriageVoice(file) {
  const formData = new FormData();
  if (file) {
    formData.append('file', file);
  }
  const response = await fetch(`${API_BASE}/api/triage/voice`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error('Failed to upload triage voice');
  }
  return await response.json();
}
