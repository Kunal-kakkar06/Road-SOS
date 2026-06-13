import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import AppLayout from './components/AppLayout';

// Lazy-load all pages for route-level code splitting
const Home                = lazy(() => import('./pages/Home'));
const MedicalProfilePage  = lazy(() => import('./pages/MedicalProfilePage'));
const DigiLockerCallback  = lazy(() => import('./pages/DigiLockerCallback'));
const MockDigiLocker      = lazy(() => import('./pages/MockDigiLocker'));
const LiveMap             = lazy(() => import('./pages/LiveMap'));
const History             = lazy(() => import('./pages/History'));
const Hospital            = lazy(() => import('./pages/Hospital'));
const FirstAid            = lazy(() => import('./pages/FirstAid'));
const Ambulance           = lazy(() => import('./pages/Ambulance'));
const IncidentReportPage  = lazy(() => import('./pages/IncidentReportPage'));
const FamilyTrackingPage  = lazy(() => import('./pages/FamilyTrackingPage'));
const PreventionMapPage   = lazy(() => import('./pages/PreventionMapPage'));
const AITriagePage        = lazy(() => import('./pages/AITriagePage'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          height: '100vh', background: '#0a0a0f', color: '#e63946',
          fontSize: '1.2rem', fontFamily: 'sans-serif'
        }}>
          Loading...
        </div>
      }>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/"                    element={<Home />} />
            <Route path="/medical-profile"     element={<MedicalProfilePage />} />
            <Route path="/digilocker/callback" element={<DigiLockerCallback />} />
            <Route path="/map"                 element={<PreventionMapPage />} />
            <Route path="/history"             element={<History />} />
            <Route path="/hospital"            element={<Hospital />} />
            <Route path="/first-aid"           element={<FirstAid />} />
            <Route path="/ambulance"           element={<Ambulance />} />
            <Route path="/incident/:incidentId" element={<IncidentReportPage />} />
            <Route path="/triage"              element={<AITriagePage />} />
          </Route>
          <Route path="/mock-digilocker" element={<MockDigiLocker />} />
          <Route path="/track/:sessionId" element={<FamilyTrackingPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
