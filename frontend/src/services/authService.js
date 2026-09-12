const API_BASE = import.meta.env.VITE_API_URL || '';

export async function login(email, password) {
  if (!email || !password) {
    throw new Error('Please fill in all fields.');
  }

  // Try real backend API if available
  try {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const contentType = response.headers.get('content-type');
    if (response.ok && contentType && contentType.includes('application/json')) {
      const data = await response.json();
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      localStorage.setItem('authToken', data.access_token); // Legacy compatibility
      localStorage.setItem('user', JSON.stringify(data.user));

      try {
        const cachedProfile = localStorage.getItem('medicalProfile');
        const profile = cachedProfile ? JSON.parse(cachedProfile) : {};
        profile.userId = data.user.id;
        localStorage.setItem('medicalProfile', JSON.stringify(profile));
      } catch (_) {}

      return data;
    }
  } catch (err) {
    console.warn('Backend auth endpoint unreachable, using client login fallback:', err);
  }

  // Check if user registered locally in this browser session
  let userName = email.split('@')[0] ? email.split('@')[0].replace(/[\._]/g, ' ').toUpperCase() : 'Demo User';
  try {
    const usersStr = localStorage.getItem('registeredUsers') || '[]';
    const users = JSON.parse(usersStr);
    const found = users.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (found && found.name) {
      userName = found.name;
    }
  } catch (_) {}

  // Client demo mode fallback for Vercel static deployments
  const mockUser = {
    id: 'usr_demo_' + Date.now(),
    name: userName,
    email: email,
    role: 'citizen'
  };

  const mockToken = 'mock_jwt_token_' + Date.now();
  const mockData = {
    access_token: mockToken,
    refresh_token: mockToken,
    user: mockUser
  };

  localStorage.setItem('accessToken', mockData.access_token);
  localStorage.setItem('refreshToken', mockData.refresh_token);
  localStorage.setItem('authToken', mockData.access_token);
  localStorage.setItem('user', JSON.stringify(mockData.user));

  try {
    const cachedProfile = localStorage.getItem('medicalProfile');
    const profile = cachedProfile ? JSON.parse(cachedProfile) : {};
    profile.userId = mockUser.id;
    localStorage.setItem('medicalProfile', JSON.stringify(profile));
  } catch (_) {}

  return mockData;
}

export async function register(name, email, password, confirmPassword) {
  if (!name || !email || !password) {
    throw new Error('Please fill in all required fields.');
  }
  if (password !== confirmPassword) {
    throw new Error('Passwords do not match.');
  }

  // Try real backend API if available
  try {
    const response = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, confirm_password: confirmPassword })
    });

    const contentType = response.headers.get('content-type');
    if (response.ok && contentType && contentType.includes('application/json')) {
      return await response.json();
    }
  } catch (err) {
    console.warn('Backend auth endpoint unreachable, using client registration fallback:', err);
  }

  // Client demo mode fallback for Vercel static deployments
  const mockUser = {
    id: 'usr_' + Date.now(),
    name: name,
    email: email,
    role: 'citizen'
  };

  const mockToken = 'mock_jwt_token_' + Date.now();
  const mockData = {
    access_token: mockToken,
    refresh_token: mockToken,
    user: mockUser
  };

  localStorage.setItem('accessToken', mockData.access_token);
  localStorage.setItem('refreshToken', mockData.refresh_token);
  localStorage.setItem('authToken', mockData.access_token);
  localStorage.setItem('user', JSON.stringify(mockData.user));

  // Store in registeredUsers array in localStorage
  try {
    const usersStr = localStorage.getItem('registeredUsers') || '[]';
    const users = JSON.parse(usersStr);
    users.push({ email, password, name, user: mockUser });
    localStorage.setItem('registeredUsers', JSON.stringify(users));
  } catch (_) {}

  return mockData;
}

export async function logout() {
  const refreshToken = localStorage.getItem('refreshToken');
  if (refreshToken) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    } catch (err) {
      console.warn('Backend logout call failed', err);
    }
  }

  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('authToken'); // Legacy compatibility
  localStorage.removeItem('user');
  localStorage.removeItem('medicalProfile');
  localStorage.removeItem('emergencyContacts');
}

export function getCurrentUser() {
  try {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  } catch (_) {
    return null;
  }
}
