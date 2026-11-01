import { useEffect, useRef, useState } from 'react'

import { memberKey, type MemberIndex } from '../../lib/format'
import { COALITIONS, PARTY_COLORS } from '../../lib/parties'
import MapTooltip, { type TooltipData } from './MapTooltip'

type MapPanelProps = {
  svgHtml: string | null
  loading: boolean
  error: string | null
  members: MemberIndex
  selectedName: string
  selectedState?: string
  onSelectName: (name: string, state?: string) => void
}

function readTooltipData(el: Element, members: MemberIndex): TooltipData {
  const d = (el as HTMLElement).dataset
  const name = d.name?.trim() || '—'
  const state = d.state || ''
  const member = members.get(memberKey(d.name, state)) ?? members.get(memberKey(d.name))
  if (!member) {
    return {
      name,
      state,
      party: '—',
      mp: '—',
      coalition: '—',
      color: d.color || '#607080',
    }
  }
  return {
    name,
    state,
    party: member.party,
    mp: member.name,
    coalition: COALITIONS[member.party] || member.coalition || '—',
    color: PARTY_COLORS[member.party] || d.color || '#607080',
  }
}

function constituencySelector(name: string, state?: string): string {
  const namePart = `[data-name="${CSS.escape(name)}" i]`
  const statePart = state ? `[data-state="${CSS.escape(state)}" i]` : ''
  return `.constituency${namePart}${statePart}`
}

export default function MapPanel({
  svgHtml,
  loading,
  error,
  members,
  selectedName,
  selectedState,
  onSelectName,
}: MapPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const membersRef = useRef(members)
  const onSelectRef = useRef(onSelectName)
  const activeElRef = useRef<SVGElement | null>(null)
  const selectedElRef = useRef<SVGElement | null>(null)
  membersRef.current = members
  onSelectRef.current = onSelectName

  const [tooltip, setTooltip] = useState<{
    visible: boolean
    left: number
    top: number
    data: TooltipData | null
  }>({ visible: false, left: 0, top: 0, data: null })

  function posTooltip(clientX: number, clientY: number) {
    const panel = panelRef.current
    if (!panel) return { left: 0, top: 0 }
    const r = panel.getBoundingClientRect()
    let tx = clientX - r.left + 16
    let ty = clientY - r.top - 50
    if (tx + 235 > r.width) tx = clientX - r.left - 245
    if (ty < 5) ty = 5
    if (ty + 160 > r.height) ty = r.height - 165
    return { left: tx, top: ty }
  }

  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap) return
    activeElRef.current = null
    selectedElRef.current = null
    if (!svgHtml) {
      wrap.innerHTML = ''
      return
    }
    wrap.innerHTML = svgHtml
    const svg = wrap.querySelector('svg')
    if (svg) {
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet')
      svg.style.width = '100%'
      svg.style.height = '100%'
    }
  }, [svgHtml])

  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap || !svgHtml) return

    function pathFrom(target: EventTarget | null): SVGElement | null {
      if (!(target instanceof Element)) return null
      return target.closest<SVGElement>('.constituency')
    }

    function onOver(e: MouseEvent) {
      const el = pathFrom(e.target)
      if (!el) return
      const from = e.relatedTarget
      if (from instanceof Node && el.contains(from)) return
      const prev = activeElRef.current
      if (prev && prev !== el && prev !== selectedElRef.current) {
        prev.classList.remove('active')
      }
      activeElRef.current = el
      el.classList.add('active')
      const { left, top } = posTooltip(e.clientX, e.clientY)
      setTooltip({
        visible: true,
        left,
        top,
        data: readTooltipData(el, membersRef.current),
      })
    }

    function onMove(e: MouseEvent) {
      const el = pathFrom(e.target)
      const { left, top } = posTooltip(e.clientX, e.clientY)
      setTooltip((t) => {
        if (!el) return t.visible ? { ...t, visible: false } : t
        return t.visible ? { ...t, left, top } : t
      })
    }

    function onOut(e: MouseEvent) {
      const el = pathFrom(e.target)
      if (!el) return
      const to = e.relatedTarget
      if (to instanceof Node && el.contains(to)) return
      if (activeElRef.current === el) activeElRef.current = null
      if (el !== selectedElRef.current) el.classList.remove('active')
      setTooltip((t) => ({ ...t, visible: false }))
    }

    function onClick(e: MouseEvent) {
      const el = pathFrom(e.target)
      if (!el) return
      onSelectRef.current(el.dataset.name || '', el.dataset.state || undefined)
      setTooltip((t) => ({ ...t, visible: false }))
    }

    function onLeaveWrap() {
      const el = activeElRef.current
      if (el && el !== selectedElRef.current) el.classList.remove('active')
      activeElRef.current = null
      setTooltip((t) => ({ ...t, visible: false }))
    }

    wrap.addEventListener('mouseover', onOver)
    wrap.addEventListener('mousemove', onMove)
    wrap.addEventListener('mouseout', onOut)
    wrap.addEventListener('click', onClick)
    wrap.addEventListener('mouseleave', onLeaveWrap)

    return () => {
      wrap.removeEventListener('mouseover', onOver)
      wrap.removeEventListener('mousemove', onMove)
      wrap.removeEventListener('mouseout', onOut)
      wrap.removeEventListener('click', onClick)
      wrap.removeEventListener('mouseleave', onLeaveWrap)
    }
  }, [svgHtml])

  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap) return
    const next = selectedName
      ? wrap.querySelector<SVGElement>(constituencySelector(selectedName, selectedState))
      : null
    const prev = selectedElRef.current
    if (prev && prev !== next && prev !== activeElRef.current) {
      prev.classList.remove('active')
    }
    selectedElRef.current = next
    if (next) next.classList.add('active')
  }, [svgHtml, selectedName, selectedState])

  useEffect(() => {
    const el = activeElRef.current
    if (!el) return
    setTooltip((t) =>
      t.visible ? { ...t, data: readTooltipData(el, members) } : t,
    )
  }, [members])

  useEffect(() => {
    if (!selectedName || !wrapRef.current) return
    const el = wrapRef.current.querySelector<SVGElement>(
      constituencySelector(selectedName, selectedState),
    )
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedName, selectedState, svgHtml])

  return (
    <div className="map-panel" ref={panelRef}>
      <div className="map-label">// INDIA — 543 LOK SABHA CONSTITUENCIES</div>
      <div id="map-wrap" ref={wrapRef} />
      {loading ? (
        <div id="map-loading">
          <div className="load-text">LOADING CONSTITUENCY MAP...</div>
          <div className="load-bar">
            <div className="load-fill" />
          </div>
        </div>
      ) : null}
      {error && !loading ? (
        <div id="map-loading">
          <div className="load-text">{error}</div>
          <div className="load-bar">
            <div className="load-fill load-fill-error" />
          </div>
        </div>
      ) : null}
      <MapTooltip
        visible={tooltip.visible}
        left={tooltip.left}
        top={tooltip.top}
        data={tooltip.data}
      />
    </div>
  )
}
