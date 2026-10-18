import { useEffect, useState } from 'react'

import { api } from '../api/client'
import type { StatsResponse } from '../api/types'
import GridBackground from '../components/GridBackground'
import { normConstName } from '../lib/format'
import FinderPanel from './map/FinderPanel'
import MapPanel from './map/MapPanel'
import StatusBar from './map/StatusBar'
import TopBar from './map/TopBar'
import './map/map.css'

const PAGE_TITLE = 'Neta Check — Know Your MP'

function loadErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err)
  if (msg.includes('SVG') || msg.toLowerCase().includes('constituencies.svg')) {
    return 'MAP LOAD ERROR — SVG file missing'
  }
  return 'API ERROR — failed to load map data'
}

export default function MapPage() {
  const [selectedName, setSelectedName] = useState('')
  const [svgHtml, setSvgHtml] = useState<string | null>(null)
  const [names, setNames] = useState<string[]>([])
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [constituencyToMpId, setConstituencyToMpId] = useState<Map<string, number>>(
    () => new Map(),
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const prevTitle = document.title
    const prevOverflow = document.body.style.overflow
    document.title = PAGE_TITLE
    document.body.style.overflow = 'hidden'
    return () => {
      document.title = prevTitle
      document.body.style.overflow = prevOverflow
    }
  }, [])

  useEffect(() => {
    const ac = new AbortController()
    const { signal } = ac

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [svgRes, statsData, namesData, members] = await Promise.all([
          fetch('/india_constituencies.svg', { signal }),
          api.stats(signal),
          api.constituencies(signal),
          api.mps(543, signal),
        ])

        if (!svgRes.ok) throw new Error('SVG not found')
        const svgText = await svgRes.text()

        const idMap = new Map<string, number>()
        for (const m of members) {
          const key = normConstName(m.constituency)
          if (key && !idMap.has(key)) idMap.set(key, m.myneta_id)
        }

        setSvgHtml(svgText)
        setStats(statsData)
        setNames(Array.isArray(namesData) ? [...namesData].sort() : [])
        setConstituencyToMpId(idMap)
        setLoading(false)
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        if (err instanceof Error && err.name === 'AbortError') return
        setError(loadErrorMessage(err))
        setLoading(false)
      }
    }

    void load()
    return () => ac.abort()
  }, [])

  return (
    <div className="map-page">
      <GridBackground />
      <div className="corner tl" aria-hidden="true" />
      <div className="corner tr" aria-hidden="true" />
      <div className="corner bl" aria-hidden="true" />
      <div className="corner br" aria-hidden="true" />

      <div className="page">
        <TopBar stats={stats} />
        <div className="main">
          <MapPanel
            svgHtml={svgHtml}
            loading={loading}
            error={error}
            selectedName={selectedName}
            onSelectName={setSelectedName}
          />
          <FinderPanel
            names={names}
            selectedName={selectedName}
            onSelectName={setSelectedName}
            stats={stats}
            constituencyToMpId={constituencyToMpId}
          />
        </div>
        <StatusBar />
      </div>
    </div>
  )
}
