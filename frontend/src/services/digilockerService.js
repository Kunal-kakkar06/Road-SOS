export const startDigiLockerImport = async () => {
  const token = localStorage.getItem('authToken');
  const res   = await fetch('/api/digilocker/auth-url', {
    headers: { Authorization: `Bearer ${token}` }
  });
  const { auth_url } = await res.json();
  // Open DigiLocker OAuth in same tab
  window.location.href = auth_url;
};

// Called on /digilocker/callback page after redirect
export const handleDigiLockerCallback = async (code) => {
  const token = localStorage.getItem('authToken');
  const res   = await fetch('/api/digilocker/callback', {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ code }),
  });
  return res.json(); // { success, prefilled, message }
};
