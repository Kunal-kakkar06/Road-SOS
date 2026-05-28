import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { registerSW } from './services/offlineSOS';
import App from './App.jsx';
import './index.css';

registerSW();

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);
