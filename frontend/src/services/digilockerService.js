const API_BASE = import.meta.env.VITE_API_URL || '';

export const startDigiLockerImport = async () => {
  const token = localStorage.getItem('authToken');
  const redirectUri = `${window.location.origin}/digilocker/callback`;
  const params = new URLSearchParams({ redirect_uri: redirectUri });
  const res   = await fetch(`${API_BASE}/api/digilocker/auth-url?${params}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  const { auth_url } = await res.json();
  // Open DigiLocker OAuth in same tab
  window.location.href = auth_url;
};

// Called on /digilocker/callback page after redirect
export const handleDigiLockerCallback = async (code) => {
  const token = localStorage.getItem('authToken');
  const res   = await fetch(`${API_BASE}/api/digilocker/callback`, {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ code }),
  });
  return res.json(); // { success, prefilled, message }
};
