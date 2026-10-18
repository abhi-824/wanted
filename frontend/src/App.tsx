import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useSearchParams } from 'react-router'

import HomePage from './pages/home/HomePage'

const MapPage = lazy(() => import('./pages/MapPage'))
const ParliamentPage = lazy(() => import('./pages/ParliamentPage'))
const ParliamentDetailPage = lazy(() => import('./pages/ParliamentDetailPage'))
const DossierPage = lazy(() => import('./pages/DossierPage'))
const DossierDetailPage = lazy(() => import('./pages/DossierDetailPage'))

function LegacyDossierRedirect() {
  const [params] = useSearchParams()
  const id = params.get('id')
  return <Navigate to={id ? `/dossier/${encodeURIComponent(id)}` : '/dossier'} replace />
}

function LegacyParliamentRedirect() {
  const [params] = useSearchParams()
  const id = params.get('id')
  return (
    <Navigate to={id ? `/parliament/${encodeURIComponent(id)}` : '/parliament'} replace />
  )
}

function PageFallback() {
  return <main aria-busy="true">Loading…</main>
}

export default function App() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/parliament" element={<ParliamentPage />} />
        <Route path="/parliament/:id" element={<ParliamentDetailPage />} />
        <Route path="/dossier" element={<DossierPage />} />
        <Route path="/dossier/:id" element={<DossierDetailPage />} />

        <Route path="/index.html" element={<Navigate to="/" replace />} />
        <Route path="/india-map.html" element={<Navigate to="/map" replace />} />
        <Route path="/dossier.html" element={<LegacyDossierRedirect />} />
        <Route path="/parliament.html" element={<LegacyParliamentRedirect />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
