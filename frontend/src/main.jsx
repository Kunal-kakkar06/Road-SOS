import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { registerSW } from './services/offlineSOS';
import App from './App.jsx';
import './index.css';

const API_BASE = import.meta.env.VITE_API_URL || '';

const ORIGINAL_FETCH = window.fetch;
window.fetch = async function (url, options = {}) {
  const isBackend = typeof url === 'string' && (
    (API_BASE && url.startsWith(API_BASE)) ||
    (!API_BASE && url.startsWith('/api/'))
  );

  // Check if target is backend and not auth endpoint
  if (isBackend && !url.includes('/api/auth/')) {
    options.headers = options.headers || {};
    const token = localStorage.getItem('accessToken');
    if (token) {
      if (options.headers instanceof Headers) {
        options.headers.set('Authorization', `Bearer ${token}`);
      } else if (Array.isArray(options.headers)) {
        const hasAuth = options.headers.some(h => h[0].toLowerCase() === 'authorization');
        if (!hasAuth) options.headers.push(['Authorization', `Bearer ${token}`]);
      } else {
        options.headers['Authorization'] = `Bearer ${token}`;
      }
    }
  }

  let response = await ORIGINAL_FETCH(url, options);

  // If 401 Unauthorized, try refreshing tokens
  if (response.status === 401 && isBackend && !url.includes('/api/auth/')) {
    const refreshToken = localStorage.getItem('refreshToken');
    if (refreshToken) {
      try {
        const refreshRes = await ORIGINAL_FETCH(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          localStorage.setItem('accessToken', data.access_token);
          localStorage.setItem('refreshToken', data.refresh_token);
          localStorage.setItem('authToken', data.access_token); // Legacy compatibility
          localStorage.setItem('user', JSON.stringify(data.user));

          // Retry original request with new token
          options.headers = options.headers || {};
          if (options.headers instanceof Headers) {
            options.headers.set('Authorization', `Bearer ${data.access_token}`);
          } else {
            options.headers['Authorization'] = `Bearer ${data.access_token}`;
          }
          return await ORIGINAL_FETCH(url, options);
        } else {
          // Refresh token invalid -> Logout
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('user');
          localStorage.removeItem('medicalProfile');
          localStorage.removeItem('emergencyContacts');
          window.location.href = '/login';
        }
      } catch (err) {
        console.error('Auto-refresh token exchange failed', err);
      }
    }
  }

  return response;
};

registerSW();

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
