const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const createIncident = async (payload) => {
  try {
    const res = await fetch(`${API_BASE}/api/incident/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to create incident');
    return await res.json();
  } catch (e) {
    console.error('[Incident Service] Error creating incident:', e);
    return { error: true, message: e.message };
  }
};

export const addTimelineEvent = async (incidentId, eventPayload) => {
  try {
    const res = await fetch(`${API_BASE}/api/incident/${incidentId}/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(eventPayload),
    });
    if (!res.ok) throw new Error('Failed to add timeline event');
    return await res.json();
  } catch (e) {
    console.error('[Incident Service] Error adding timeline event:', e);
    return { error: true, message: e.message };
  }
};

export const uploadIncidentPhotos = async (incidentId, files) => {
  try {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const res = await fetch(`${API_BASE}/api/incident/${incidentId}/photos`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload photos');
    return await res.json();
  } catch (e) {
    console.error('[Incident Service] Error uploading photos:', e);
    return { error: true, message: e.message };
  }
};

export const generateIncidentPDF = async (incidentId) => {
  try {
    const res = await fetch(`${API_BASE}/api/incident/${incidentId}/generate-pdf`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to generate PDF');
    return await res.json();
  } catch (e) {
    console.error('[Incident Service] Error generating PDF:', e);
    return { error: true, message: e.message };
  }
};

export const getIncidentDetails = async (incidentId) => {
  try {
    const res = await fetch(`${API_BASE}/api/incident/${incidentId}`, {
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error('Failed to fetch incident details');
    const data = await res.json();
    
    // Save to local storage for offline use
    localStorage.setItem(`incident_${incidentId}`, JSON.stringify(data));
    localStorage.setItem(`incident_${incidentId}_ts`, Date.now().toString());
    
    return data;
  } catch (e) {
    console.error('[Incident Service] Error fetching incident details, using cache:', e);
    const cached = localStorage.getItem(`incident_${incidentId}`);
    if (cached) {
      const data = JSON.parse(cached);
      data.fromCache = true;
      return data;
    }
    return { error: true, message: e.message };
  }
};

export const getUserIncidents = async (userId) => {
  try {
    const res = await fetch(`${API_BASE}/api/incident/user/${userId}`);
    if (!res.ok) throw new Error('Failed to fetch user incidents');
    return await res.json();
  } catch (e) {
    console.error('[Incident Service] Error fetching user incidents:', e);
    return [];
  }
};

export const getFIRGuide = async (incidentId) => {
  try {
    const res = await fetch(`${API_BASE}/api/incident/${incidentId}/fir-guide`);
    if (!res.ok) throw new Error('Failed to fetch FIR guide');
    return await res.json();
  } catch (e) {
    console.error('[Incident Service] Error fetching FIR guide:', e);
    return { error: true, message: e.message };
  }
};

export const getDownloadPDFUrl = (incidentId) => {
  return `${API_BASE}/api/incident/${incidentId}/download-pdf`;
};
