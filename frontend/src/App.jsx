import { Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home.jsx'
import Diagnostic from './pages/Diagnostic.jsx'
import Results from './pages/Results.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/diagnostic" element={<Diagnostic />} />
      <Route path="/results" element={<Results />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
