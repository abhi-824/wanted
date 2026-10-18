import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

import type { MPSummary } from '../../api/types'
import { buildChamber, lighten, type ChamberLayout, type ChamberSeat, type SpeakerSeat } from './layout'

export type HoverTarget = ChamberSeat | SpeakerSeat | null

type ChamberCanvasProps = {
  members: MPSummary[]
  hoveredId: number | null
  selectedId: number | null
  wrapRef?: RefObject<HTMLDivElement | null>
  onHover: (target: HoverTarget) => void
  onSelect: (mpId: number) => void
  onLayout?: () => void
}

function mpIdOf(target: HoverTarget): number | null {
  if (!target?.mp) return null
  return target.mp.myneta_id
}

function hitTest(layout: ChamberLayout, mx: number, my: number, pad: number): HoverTarget {
  for (const s of layout.seats) {
    const dx = mx - s.x
    const dy = my - s.y
    if (dx * dx + dy * dy <= (s.r + pad) * (s.r + pad)) return s
  }
  const sp = layout.speaker
  if (sp.mp) {
    const dx = mx - sp.x
    const dy = my - sp.y
    if (dx * dx + dy * dy <= (sp.r + pad) * (sp.r + pad)) return sp
  }
  return null
}

function drawChamber(
  ctx: CanvasRenderingContext2D,
  layout: ChamberLayout,
  hovered: HoverTarget,
  selectedId: number | null,
) {
  const { width: CW, height: CH, cx, cy, minR, rowSpacing, seatRadius: SEAT_R } = layout
  const BLOCKS = 6
  const ROWS = 11
  const ARC_SPAN = 162
  const BLOCK_GAP = 3.5
  const BSPAN = (ARC_SPAN - BLOCK_GAP * (BLOCKS - 1)) / BLOCKS
  const ARC_START = 180 + (180 - ARC_SPAN) / 2

  ctx.clearRect(0, 0, CW, CH)
  ctx.fillStyle = '#05080f'
  ctx.fillRect(0, 0, CW, CH)

  for (let b = 0; b < BLOCKS; b++) {
    const bS = ((ARC_START + b * (BSPAN + BLOCK_GAP)) * Math.PI) / 180
    const bE = bS + (BSPAN * Math.PI) / 180
    for (let r = 0; r < ROWS; r++) {
      ctx.beginPath()
      ctx.arc(cx, cy, minR + r * rowSpacing, bS, bE)
      ctx.strokeStyle = '#0d1e30'
      ctx.lineWidth = SEAT_R * 2 + 3
      ctx.stroke()
    }
  }

  function drawSeat(
    s: ChamberSeat | SpeakerSeat,
    color: string,
    isMin: boolean,
  ) {
    const isH = s === hovered
    const isSel = s.mp != null && s.mp.myneta_id === selectedId
    if (isMin) {
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r + 3.5, 0, 2 * Math.PI)
      ctx.strokeStyle = isH || isSel ? 'rgba(255,220,80,0.9)' : 'rgba(255,220,80,0.5)'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
    ctx.beginPath()
    ctx.arc(s.x, s.y, s.r + (isH || isSel ? 2.5 : 0), 0, 2 * Math.PI)
    ctx.fillStyle = isH || isSel ? lighten(color) : color
    ctx.fill()
    if (isH || isSel) {
      ctx.strokeStyle = '#ffffff66'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
  }

  for (const s of layout.seats) {
    drawSeat(s, s.color, s.isMinister)
  }

  const sp = layout.speaker
  if (sp.mp) {
    ctx.beginPath()
    ctx.arc(sp.x, sp.y, sp.r + 4, 0, 2 * Math.PI)
    ctx.strokeStyle = 'rgba(212,164,0,0.3)'
    ctx.lineWidth = 2
    ctx.stroke()
    drawSeat(sp, sp.color, false)
  }

  const fs = Math.max(9, Math.min(11, CW * 0.012))
  ctx.font = `${fs}px 'Share Tech Mono', monospace`
  ctx.fillStyle = 'rgba(196,148,0,0.65)'
  ctx.textAlign = 'center'
  ctx.fillText('SPEAKER', cx, sp.y - sp.r - 6)
  ctx.fillStyle = '#1a4060'
  ctx.textAlign = 'left'
  ctx.fillText('NDA →', cx + 14, cy - 8)
  ctx.textAlign = 'right'
  ctx.fillText('← INDIA', cx - 14, cy - 8)
}

export default function ChamberCanvas({
  members,
  hoveredId,
  selectedId,
  wrapRef: externalWrapRef,
  onHover,
  onSelect,
  onLayout,
}: ChamberCanvasProps) {
  const localWrapRef = useRef<HTMLDivElement>(null)
  const wrapRef = externalWrapRef ?? localWrapRef
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const layoutRef = useRef<ChamberLayout | null>(null)
  const hoveredRef = useRef<HoverTarget>(null)
  const [touchTap, setTouchTap] = useState<number | null>(null)

  const paint = useCallback(() => {
    const canvas = canvasRef.current
    const layout = layoutRef.current
    if (!canvas || !layout) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    drawChamber(ctx, layout, hoveredRef.current, selectedId)
  }, [selectedId])

  useEffect(() => {
    hoveredRef.current = null
    if (hoveredId == null) {
      paint()
      return
    }
    const layout = layoutRef.current
    if (!layout) return
    const seat =
      layout.seats.find((s) => s.mp.myneta_id === hoveredId) ??
      (layout.speaker.mp?.myneta_id === hoveredId ? layout.speaker : null)
    hoveredRef.current = seat ?? null
    paint()
  }, [hoveredId, paint])

  useEffect(() => {
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas || members.length === 0) return

    const ro = new ResizeObserver(() => {
      const dpr = window.devicePixelRatio || 1
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      layoutRef.current = buildChamber(members, w, h)
      paint()
      onLayout?.()
    })

    ro.observe(wrap)
    return () => ro.disconnect()
  }, [members, paint, onLayout])

  function pointerToCanvas(e: React.MouseEvent | React.TouchEvent): { mx: number; my: number; clientX: number; clientY: number } | null {
    const canvas = canvasRef.current
    const layout = layoutRef.current
    if (!canvas || !layout) return null
    const rect = canvas.getBoundingClientRect()
    const sx = layout.width / rect.width
    const sy = layout.height / rect.height
    const clientX = 'touches' in e ? e.changedTouches[0]?.clientX : e.clientX
    const clientY = 'touches' in e ? e.changedTouches[0]?.clientY : e.clientY
    if (clientX == null || clientY == null) return null
    return {
      mx: (clientX - rect.left) * sx,
      my: (clientY - rect.top) * sy,
      clientX,
      clientY,
    }
  }

  function updateHover(found: HoverTarget) {
    hoveredRef.current = found
    onHover(found)
    paint()
  }

  return (
    <canvas
        ref={canvasRef}
        className="parliament-canvas"
        onMouseMove={(e) => {
          const pt = pointerToCanvas(e)
          const layout = layoutRef.current
          if (!pt || !layout) return
          const found = hitTest(layout, pt.mx, pt.my, 6)
          if (mpIdOf(found) !== mpIdOf(hoveredRef.current)) updateHover(found)
          if (found) canvasRef.current!.style.cursor = 'pointer'
          else canvasRef.current!.style.cursor = 'default'
        }}
        onMouseLeave={() => {
          updateHover(null)
        }}
        onClick={() => {
          const id = mpIdOf(hoveredRef.current)
          if (id != null) onSelect(id)
        }}
        onTouchStart={(e) => e.preventDefault()}
        onTouchEnd={(e) => {
          e.preventDefault()
          const pt = pointerToCanvas(e)
          const layout = layoutRef.current
          if (!pt || !layout) return
          const found = hitTest(layout, pt.mx, pt.my, 14)
          const id = mpIdOf(found)
          if (id != null) {
            if (touchTap === id) {
              onSelect(id)
              setTouchTap(null)
              updateHover(null)
            } else {
              setTouchTap(id)
              updateHover(found)
            }
          } else {
            setTouchTap(null)
            updateHover(null)
          }
        }}
      />
  )
}
