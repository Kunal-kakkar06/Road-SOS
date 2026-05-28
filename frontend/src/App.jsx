import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Home from './pages/Home';
import MedicalProfilePage from './pages/MedicalProfilePage';
import DigiLockerCallback from './pages/DigiLockerCallback';
import MockDigiLocker from './pages/MockDigiLocker';
import LiveMap from './pages/LiveMap';
import History from './pages/History';
import Hospital from './pages/Hospital';
import FirstAid from './pages/FirstAid';
import Ambulance from './pages/Ambulance';
import IncidentReportPage from './pages/IncidentReportPage';
import FamilyTrackingPage from './pages/FamilyTrackingPage';
import PreventionMapPage from './pages/PreventionMapPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/"                  element={<Home />} />
          <Route path="/medical-profile"   element={<MedicalProfilePage />} />
          <Route path="/digilocker/callback" element={<DigiLockerCallback />} />
          <Route path="/map"               element={<LiveMap />} />
          <Route path="/history"           element={<History />} />
          <Route path="/hospital"          element={<Hospital />} />
          <Route path="/first-aid"         element={<FirstAid />} />
          <Route path="/ambulance"         element={<Ambulance />} />
          <Route path="/incident/:incidentId" element={<IncidentReportPage />} />
          <Route path="/prevention"        element={<PreventionMapPage />} />
        </Route>
        <Route path="/mock-digilocker" element={<MockDigiLocker />} />
        <Route path="/track/:sessionId" element={<FamilyTrackingPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
