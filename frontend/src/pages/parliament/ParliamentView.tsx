import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { api } from '../../api/client'
import type { MPSummary, StatsResponse } from '../../api/types'
import GridBackground from '../../components/GridBackground'
import { normConstName } from '../../lib/format'
import { PARTY_COLORS } from '../../lib/parties'
import StatusBar from '../map/StatusBar'
import TopBar from '../map/TopBar'
import '../map/map.css'
import ChamberCanvas, { type HoverTarget } from './ChamberCanvas'
import CoalitionTally from './CoalitionTally'
import { buildChamber, type ChamberSeat } from './layout'
import ParliamentPanel from './ParliamentPanel'
import SeatCard from './SeatCard'
import SeatTooltip from './SeatTooltip'
import './parliament.css'

const PAGE_TITLE = 'Neta Check — 18th Lok Sabha'

const LEGEND_PARTIES: [string, string][] = [
  ['BJP', 'BJP'],
  ['INC', 'INC'],
  ['SP', 'SP'],
  ['TMC', 'TMC'],
  ['DMK', 'DMK'],
  ['TDP', 'TDP'],
  ['JDU', 'JDU'],
  ['SSUBT', 'SS(UBT)'],
  ['NCPSP', 'NCP-SP'],
  ['SHS', 'Shiv Sena'],
  ['LJP', 'LJP'],
  ['JMM', 'JMM'],
  ['AAP', 'AAP'],
  ['IND', 'Ind'],
]

function parseSelectedId(raw: string | undefined): number | null {
  if (!raw) return null
  const id = parseInt(raw, 10)
  return Number.isFinite(id) ? id : null
}

export default function ParliamentView() {
  const { id: idParam } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const canvasWrapRef = useRef<HTMLDivElement>(null)

  const selectedId = parseSelectedId(idParam)

  const [members, setMembers] = useState<MPSummary[]>([])
  const [names, setNames] = useState<string[]>([])
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchName, setSearchName] = useState('')
  const [hoverTarget, setHoverTarget] = useState<HoverTarget>(null)
  const [pointer, setPointer] = useState({ x: 0, y: 0 })

  const idToMp = useMemo(() => {
    const m = new Map<number, MPSummary>()
    for (const mp of members) m.set(mp.myneta_id, mp)
    return m
  }, [members])

  const nameToId = useMemo(() => {
    const m = new Map<string, number>()
    for (const mp of members) {
      const key = normConstName(mp.constituency)
      if (key && !m.has(key)) m.set(key, mp.myneta_id)
    }
    return m
  }, [members])

  const selectedMp = selectedId != null ? idToMp.get(selectedId) ?? null : null

  const [layoutTick, setLayoutTick] = useState(0)

  const selectedSeat = useMemo((): ChamberSeat | null => {
    if (selectedId == null || members.length === 0) return null
    const el = canvasWrapRef.current
    const w = el?.clientWidth ?? 800
    const h = el?.clientHeight ?? 600
    const layout = buildChamber(members, w, h)
    return layout.seats.find((s) => s.mp.myneta_id === selectedId) ?? null
    // layoutTick forces recompute after canvas resize
  }, [selectedId, members, layoutTick])

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
        const [statsData, namesData, mpsData] = await Promise.all([
          api.stats(signal),
          api.constituencies(signal),
          api.mps(600, signal),
        ])
        setStats(statsData)
        setNames(Array.isArray(namesData) ? [...namesData].sort() : [])
        setMembers(mpsData)
        setLoading(false)
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        if (err instanceof Error && err.name === 'AbortError') return
        setError(err instanceof Error ? err.message : 'Failed to load parliament data')
        setLoading(false)
      }
    }

    void load()
    return () => ac.abort()
  }, [])

  useEffect(() => {
    if (!searchName) return
    const mpId = nameToId.get(normConstName(searchName))
    if (mpId != null) navigate(`/parliament/${mpId}`, { replace: true })
  }, [searchName, nameToId, navigate])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && selectedId != null) navigate('/parliament')
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [selectedId, navigate])

  const selectMp = useCallback(
    (mpId: number) => {
      navigate(`/parliament/${mpId}`)
      setHoverTarget(null)
    },
    [navigate],
  )

  const wrapRect = canvasWrapRef.current?.getBoundingClientRect() ?? null

  return (
    <div className="map-page parliament-page">
      <GridBackground />
      <div className="corner tl" aria-hidden="true" />
      <div className="corner tr" aria-hidden="true" />
      <div className="corner bl" aria-hidden="true" />
      <div className="corner br" aria-hidden="true" />

      <div className="page">
        <TopBar stats={stats} />
        <div className="parliament-coalition-row">
          <CoalitionTally members={members} />
        </div>

        <div className="parliament-main">
          <div
            className="parliament-canvas-wrap"
            ref={canvasWrapRef}
            onMouseMove={(e) => setPointer({ x: e.clientX, y: e.clientY })}
          >
            {loading ? (
              <div className="parliament-loading">
                <div className="parliament-loading-text">LOADING PARLIAMENT DATA...</div>
              </div>
            ) : error ? (
              <div className="parliament-loading">
                <div className="parliament-loading-text">API ERROR — {error}</div>
              </div>
            ) : (
              <>
                <ChamberCanvas
                  members={members}
                  hoveredId={hoverTarget?.mp?.myneta_id ?? null}
                  selectedId={selectedId}
                  wrapRef={canvasWrapRef}
                  onHover={setHoverTarget}
                  onSelect={selectMp}
                  onLayout={() => setLayoutTick((n) => n + 1)}
                />
                {hoverTarget?.mp && !selectedMp ? (
                  <SeatTooltip
                    target={hoverTarget}
                    clientX={pointer.x}
                    clientY={pointer.y}
                    wrapRect={wrapRect}
                  />
                ) : null}
              </>
            )}
          </div>

          <ParliamentPanel names={names} selectedName={searchName} onSelectName={setSearchName} />

          {selectedMp ? (
            <SeatCard mp={selectedMp} seat={selectedSeat} onClose={() => navigate('/parliament')} />
          ) : null}
        </div>

        <div className="parliament-bottom">
          <div className="parliament-legend">
            {LEGEND_PARTIES.map(([key, label]) =>
              PARTY_COLORS[key] ? (
                <div className="li" key={key}>
                  <div className="ld" style={{ background: PARTY_COLORS[key] }} />
                  {label}
                </div>
              ) : null,
            )}
            <div className="li">
              <div className="ld" style={{ background: '#d4a400' }} />
              Speaker
            </div>
            <div className="li">
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  border: '1.5px solid rgba(255,220,80,0.7)',
                  background: '#e8630a',
                  flexShrink: 0,
                }}
                aria-hidden="true"
              />
              Minister
            </div>
          </div>
          <div className="parliament-tips">
            <span className="tip">
              <span className="tk">Hover</span> see MP name & party
            </span>
            <span className="tip">
              <span className="tk">Click</span> select seat
            </span>
            <span className="tip">
              <span className="tk">Gold ring</span> Cabinet minister
            </span>
            <span className="tip">
              <span className="tk">Esc</span> close panel
            </span>
          </div>
        </div>

        <StatusBar />
      </div>
    </div>
  )
}
