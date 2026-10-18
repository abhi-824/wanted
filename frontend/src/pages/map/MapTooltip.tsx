export type TooltipData = {
  name: string
  state: string
  party: string
  mp: string
  coalition: string
  color: string
}

type MapTooltipProps = {
  visible: boolean
  left: number
  top: number
  data: TooltipData | null
}

export default function MapTooltip({ visible, left, top, data }: MapTooltipProps) {
  if (!visible || !data) return null

  return (
    <div
      className="map-tooltip"
      style={{ left, top, display: 'block' }}
      role="tooltip"
      aria-hidden="true"
    >
      <div className="mt-bar" style={{ background: data.color }} />
      <div className="mt-label">CONSTITUENCY</div>
      <div className="mt-name">{data.name || '—'}</div>
      <div className="mt-state">{data.state}</div>
      <div className="mt-stats">
        <div className="mt-stat">
          <div className="l">PARTY</div>
          <div className="v gold" style={{ color: data.color }}>
            {data.party || '—'}
          </div>
        </div>
        <div className="mt-stat">
          <div className="l">MP</div>
          <div className="v">{data.mp || '—'}</div>
        </div>
        <div className="mt-stat">
          <div className="l">COALITION</div>
          <div className="v">{data.coalition || '—'}</div>
        </div>
      </div>
      <div className="mt-hint">[ click to view MP dossier ]</div>
    </div>
  )
}
