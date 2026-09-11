import { Route, Routes } from 'react-router-dom';
import { ExperimentPage } from './pages/ExperimentPage';
import { LandingPage } from './pages/LandingPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/experiments/:experimentId" element={<ExperimentPage />} />
    </Routes>
  );
}

export default App;
