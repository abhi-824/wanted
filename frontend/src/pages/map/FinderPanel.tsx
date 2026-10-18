import { useState } from 'react'
import { useNavigate } from 'react-router'

import StatChip from '../../components/StatChip'
import type { StatsResponse } from '../../api/types'
import { formatAvgAssetsCr } from '../../lib/format'
import { normConstName } from '../../lib/format'
import ConstituencyCombobox from './ConstituencyCombobox'

type FinderPanelProps = {
  names: string[]
  selectedName: string
  onSelectName: (name: string) => void
  stats: StatsResponse | null
  constituencyToMpId: Map<string, number>
}

export default function FinderPanel({
  names,
  selectedName,
  onSelectName,
  stats,
  constituencyToMpId,
}: FinderPanelProps) {
  const navigate = useNavigate()
  const [ctaMessage, setCtaMessage] = useStateCta()

  function goToMP() {
    if (!selectedName) {
      setCtaMessage('⚠ SELECT A CONSTITUENCY FIRST')
      return
    }
    const mpId = constituencyToMpId.get(normConstName(selectedName))
    if (mpId == null) {
      setCtaMessage('⚠ MP ID NOT FOUND FOR THIS SEAT')
      return
    }
    navigate(`/dossier/${encodeURIComponent(String(mpId))}`)
  }

  return (
    <div className="right-panel">
      <div className="r-header">
        <div className="r-sys">CONSTITUENCY FINDER v1.0</div>
        <div className="r-title">
          FIND YOUR
          <br />
          <span>MP</span>
        </div>
        <div className="r-sub">Search or select your constituency to see your MP&apos;s full dossier.</div>
      </div>
      <div className="r-body">
        <div className="field-label">// SEARCH CONSTITUENCY</div>
        <ConstituencyCombobox names={names} value={selectedName} onChange={onSelectName} />

        <div className="stats-strip">
          <StatChip
            tone="blue"
            value={stats ? String(stats.total_mps) : '—'}
            label="TOTAL MPS"
          />
          <StatChip
            tone="red"
            value={stats ? String(stats.with_cases) : '—'}
            label="WITH CASES"
          />
          <StatChip tone="gold" value={formatAvgAssetsCr(stats?.avg_assets_inr)} label="AVG ASSETS" />
        </div>

        <button
          type="button"
          className={ctaMessage ? 'cta-btn cta-btn-error' : 'cta-btn'}
          onClick={goToMP}
        >
          {ctaMessage ?? (
            <>
              VIEW MP DOSSIER <span className="btn-arrow">→</span>
            </>
          )}
        </button>
        <div className="disclaimer">
          Data from ECI self-declared affidavits (2024 General Election)
          <br />
          via ADR / myneta.info. Public domain. Cases are pending unless
          <br />
          marked convicted. Last updated: June 2024.
        </div>
      </div>
    </div>
  )
}

function useStateCta() {
  const [ctaMessage, setCtaMessage] = useState<string | null>(null)

  function flash(msg: string) {
    setCtaMessage(msg)
    window.setTimeout(() => setCtaMessage(null), 1800)
  }

  return [ctaMessage, flash] as const
}
