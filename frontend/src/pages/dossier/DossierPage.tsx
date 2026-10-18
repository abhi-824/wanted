import { useEffect, useState } from 'react'
import { useParams } from 'react-router'

import { api, ApiError } from '../../api/client'
import type { IpcSection, MPDetail } from '../../api/types'
import { extractAllSectionCodes } from '../../lib/cases'
import DossierCard from './DossierCard'
import './dossier.css'

function LoadingState() {
  return (
    <div className="loading-state">
      <div className="loading-text">LOADING DOSSIER...</div>
      <div className="loading-bar">
        <div className="loading-fill" />
      </div>
    </div>
  )
}

function ErrorState({
  title,
  detail,
  hint,
}: {
  title: string
  detail?: string
  hint?: string
}) {
  return (
    <div className="error-state">
      {title}
      {detail ? (
        <>
          <br />
          <span className="error-muted">{detail}</span>
        </>
      ) : null}
      {hint ? (
        <>
          <br />
          <span className="error-muted" style={{ fontSize: 10 }}>
            {hint}
          </span>
        </>
      ) : null}
    </div>
  )
}

export default function DossierPage() {
  const { id: rawId } = useParams<{ id: string }>()
  const mpId = rawId != null ? parseInt(rawId, 10) : NaN

  const [mp, setMp] = useState<MPDetail | null>(null)
  const [ipcLookup, setIpcLookup] = useState<Record<string, IpcSection>>({})
  const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<{ title: string; detail?: string; hint?: string } | null>(
    null,
  )

  useEffect(() => {
    if (rawId == null || Number.isNaN(mpId)) {
      setPhase('error')
      setError({
        title: 'NO MP ID PROVIDED',
        detail: 'Usage: /dossier/<myneta_id>',
      })
      return
    }

    const ac = new AbortController()
    setPhase('loading')
    setMp(null)
    setError(null)

    ;(async () => {
      try {
        const detail = await api.mp(mpId, ac.signal)
        const codes = extractAllSectionCodes(detail.criminal_cases)
        let lookup: Record<string, IpcSection> = {}
        if (codes.length > 0) {
          try {
            const batch = await api.ipcSections(codes, ac.signal)
            lookup = batch.sections
          } catch {
            /* show cases without IPC descriptions */
          }
        }
        if (ac.signal.aborted) return
        setMp(detail)
        setIpcLookup(lookup)
        setPhase('ready')
        document.title = `${detail.name} — Parliament Dossier`
      } catch (err) {
        if (ac.signal.aborted) return
        if (err instanceof ApiError && err.status === 404) {
          setPhase('error')
          setError({
            title: 'MP NOT FOUND',
            detail: `No member with id=${mpId}`,
          })
          return
        }
        const message = err instanceof Error ? err.message : String(err)
        setPhase('error')
        setError({
          title: 'LOAD ERROR',
          detail: message,
          hint: 'Make sure the API is running on localhost:8000',
        })
      }
    })()

    return () => {
      ac.abort()
      document.title = 'Neta Check — Know Your Parliament'
    }
  }, [rawId, mpId])

  return (
    <div className="dossier-page">
      <div className="scan-lines" />
      <div className="card-wrap">
        {phase === 'loading' ? <LoadingState /> : null}
        {phase === 'error' && error ? (
          <ErrorState title={error.title} detail={error.detail} hint={error.hint} />
        ) : null}
        {phase === 'ready' && mp ? <DossierCard mp={mp} ipcLookup={ipcLookup} /> : null}
      </div>
    </div>
  )
}
