import { useEffect, useRef, useState } from 'react'

import { normConstName } from '../../lib/format'
import MapTooltip, { type TooltipData } from './MapTooltip'

type MapPanelProps = {
  svgHtml: string | null
  loading: boolean
  error: string | null
  selectedName: string
  onSelectName: (name: string) => void
}

function readTooltipData(el: Element): TooltipData {
  const d = (el as HTMLElement).dataset
  return {
    name: d.name || '—',
    state: d.state || '',
    party: d.party || '—',
    mp: d.mp || '—',
    coalition: d.coalition || '—',
    color: d.color || '#607080',
  }
}

export default function MapPanel({
  svgHtml,
  loading,
  error,
  selectedName,
  onSelectName,
}: MapPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const selectedRef = useRef(selectedName)
  selectedRef.current = selectedName

  const [hoveredName, setHoveredName] = useState<string | null>(null)
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
    if (!wrap || !svgHtml) return

    const paths = wrap.querySelectorAll<SVGElement>('.constituency')

    function onEnter(e: Event) {
      const el = e.currentTarget as SVGElement
      const name = el.dataset.name || ''
      setHoveredName(name)
      const { left, top } = posTooltip((e as MouseEvent).clientX, (e as MouseEvent).clientY)
      setTooltip({ visible: true, left, top, data: readTooltipData(el) })
    }

    function onMove(e: Event) {
      const me = e as MouseEvent
      const { left, top } = posTooltip(me.clientX, me.clientY)
      setTooltip((t) => (t.visible ? { ...t, left, top } : t))
    }

    function onLeave(e: Event) {
      const el = e.currentTarget as SVGElement
      if (el.dataset.name !== selectedRef.current) {
        /* highlight synced in class effect */
      }
      setHoveredName((h) => (h === el.dataset.name ? null : h))
      setTooltip((t) => ({ ...t, visible: false }))
    }

    function onClick(e: Event) {
      const el = e.currentTarget as SVGElement
      onSelectName(el.dataset.name || '')
      setTooltip((t) => ({ ...t, visible: false }))
    }

    paths.forEach((el) => {
      el.addEventListener('mouseenter', onEnter)
      el.addEventListener('mousemove', onMove)
      el.addEventListener('mouseleave', onLeave)
      el.addEventListener('click', onClick)
    })

    return () => {
      paths.forEach((el) => {
        el.removeEventListener('mouseenter', onEnter)
        el.removeEventListener('mousemove', onMove)
        el.removeEventListener('mouseleave', onLeave)
        el.removeEventListener('click', onClick)
      })
    }
  }, [svgHtml, onSelectName])

  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap) return
    const selectedNorm = normConstName(selectedName)
    const hoveredNorm = normConstName(hoveredName)
    wrap.querySelectorAll<SVGElement>('.constituency').forEach((el) => {
      const n = normConstName(el.dataset.name)
      const active = n === selectedNorm || (hoveredNorm && n === hoveredNorm)
      el.classList.toggle('active', Boolean(active))
    })
  }, [svgHtml, selectedName, hoveredName])

  useEffect(() => {
    if (!selectedName || !wrapRef.current) return
    const el = wrapRef.current.querySelector<SVGElement>(
      `.constituency[data-name="${CSS.escape(selectedName)}"]`,
    )
    if (!el) {
      const paths = wrapRef.current.querySelectorAll<SVGElement>('.constituency')
      for (const p of paths) {
        if (p.dataset.name === selectedName) {
          p.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
          break
        }
      }
      return
    }
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedName, svgHtml])

  useEffect(() => {
    if (!svgHtml || !wrapRef.current) return
    const svg = wrapRef.current.querySelector('svg')
    if (svg) {
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet')
      svg.style.width = '100%'
      svg.style.height = '100%'
    }
  }, [svgHtml])

  return (
    <div className="map-panel" ref={panelRef}>
      <div className="map-label">// INDIA — 543 LOK SABHA CONSTITUENCIES</div>
      <div id="map-wrap" ref={wrapRef} dangerouslySetInnerHTML={svgHtml ? { __html: svgHtml } : undefined} />
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
