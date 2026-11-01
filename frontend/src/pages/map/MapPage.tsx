import { useEffect, useMemo, useState } from 'react'

import { api } from '../../api/client'
import type { StatsResponse } from '../../api/types'
import GridBackground from '../../components/GridBackground'
import { memberKey, normConstName, type MemberIndex } from '../../lib/format'
import FinderPanel from './FinderPanel'
import MapPanel from './MapPanel'
import StatusBar from './StatusBar'
import TopBar from './TopBar'
import './map.css'

const PAGE_TITLE = 'Neta Check — Know Your MP'

type Selection = {
  name: string
  state?: string
}

function loadErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err)
  if (msg.includes('SVG') || msg.toLowerCase().includes('constituencies.svg')) {
    return 'MAP LOAD ERROR — SVG file missing'
  }
  return 'API ERROR — failed to load map data'
}

export default function MapPage() {
  const [selection, setSelection] = useState<Selection>({ name: '' })
  const [svgHtml, setSvgHtml] = useState<string | null>(null)
  const [names, setNames] = useState<string[]>([])
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [members, setMembers] = useState<MemberIndex>(() => new Map())
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

    api
      .stats(signal)
      .then((data) => {
        if (!signal.aborted) setStats(data)
      })
      .catch(() => {
        /* stats are optional — the map still works without them */
      })

    return () => ac.abort()
  }, [])

  useEffect(() => {
    const ac = new AbortController()
    const { signal } = ac

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [svgRes, namesData, membersData] = await Promise.all([
          fetch('/india_constituencies.svg', { signal }),
          api.constituencies(signal),
          api.mps(543, signal),
        ])

        if (!svgRes.ok) throw new Error('SVG not found')
        const svgText = await svgRes.text()

        const index: MemberIndex = new Map()
        const idMap = new Map<string, number>()
        for (const m of membersData) {
          const nameKey = memberKey(m.constituency)
          if (!nameKey) continue
          if (!idMap.has(nameKey)) idMap.set(nameKey, m.myneta_id)
          if (!index.has(nameKey)) index.set(nameKey, m)
          const fullKey = memberKey(m.constituency, m.state)
          if (!index.has(fullKey)) index.set(fullKey, m)
        }

        setSvgHtml(svgText)
        setNames(Array.isArray(namesData) ? [...namesData].sort() : [])
        setMembers(index)
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

  const finderConstituencyToMpId = useMemo(() => {
    if (!selection.state) return constituencyToMpId
    const member = members.get(memberKey(selection.name, selection.state))
    if (!member) return constituencyToMpId
    const next = new Map(constituencyToMpId)
    next.set(normConstName(selection.name), member.myneta_id)
    return next
  }, [constituencyToMpId, members, selection.name, selection.state])

  function handleSelectName(name: string, state?: string) {
    setSelection({ name, state })
  }

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
            members={members}
            selectedName={selection.name}
            selectedState={selection.state}
            onSelectName={handleSelectName}
          />
          <FinderPanel
            names={names}
            selectedName={selection.name}
            onSelectName={handleSelectName}
            stats={stats}
            constituencyToMpId={finderConstituencyToMpId}
          />
        </div>
        <StatusBar />
      </div>
    </div>
  )
}
