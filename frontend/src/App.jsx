import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Home from './pages/Home';
import MedicalProfilePage from './pages/MedicalProfilePage';
import DigiLockerCallback from './pages/DigiLockerCallback';
import LiveMap from './pages/LiveMap';
import History from './pages/History';
import Hospital from './pages/Hospital';
import FirstAid from './pages/FirstAid';
import Ambulance from './pages/Ambulance';

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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
