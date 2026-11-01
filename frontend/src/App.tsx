import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useSearchParams } from 'react-router'

import HomePage from './pages/home/HomePage'

const MapPage = lazy(() => import('./pages/map/MapPage'))
const ParliamentPage = lazy(() => import('./pages/parliament/ParliamentPage'))
const DossierPage = lazy(() => import('./pages/dossier/DossierPage'))

function LegacyIdRedirect({ to }: { to: string }) {
  const [params] = useSearchParams()
  const id = params.get('id')
  return <Navigate to={id ? `${to}/${encodeURIComponent(id)}` : to} replace />
}

export default function App() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/parliament" element={<ParliamentPage />} />
        <Route path="/parliament/:id" element={<ParliamentPage />} />
        <Route path="/dossier" element={<DossierPage />} />
        <Route path="/dossier/:id" element={<DossierPage />} />

        <Route path="/index.html" element={<Navigate to="/" replace />} />
        <Route path="/india-map.html" element={<Navigate to="/map" replace />} />
        <Route path="/dossier.html" element={<LegacyIdRedirect to="/dossier" />} />
        <Route path="/parliament.html" element={<LegacyIdRedirect to="/parliament" />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
