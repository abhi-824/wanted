import type { MPSummary } from '../../api/types'
import { roleForName } from '../../lib/parties'
import type { HoverTarget } from './ChamberCanvas'

type SeatTooltipProps = {
  target: HoverTarget
  clientX: number
  clientY: number
  wrapRect: DOMRect | null
}

function casesBadge(mp: MPSummary) {
  if (mp.total_cases > 0) {
    return (
      <span className="tt-cases warn">
        ⚖ {mp.total_cases} case{mp.total_cases > 1 ? 's' : ''}
      </span>
    )
  }
  return <span className="tt-cases clean">✓ clean</span>
}

export default function SeatTooltip({ target, clientX, clientY, wrapRect }: SeatTooltipProps) {
  if (!target?.mp || !wrapRect) return null

  const mp = target.mp
  const color = 'color' in target ? target.color : '#d4a400'
  const role = roleForName(mp.name)

  let left = clientX - wrapRect.left + 16
  let top = clientY - wrapRect.top - 55
  if (left + 270 > wrapRect.width) left = clientX - wrapRect.left - 275
  if (top < 0) top = 4

  return (
    <div className="parliament-tooltip" style={{ left, top }} role="tooltip">
      <div className="tt-bar" style={{ background: color }} />
      <div className="tt-name">
        {mp.name}
        {casesBadge(mp)}
      </div>
      {role ? (
        <div className="tt-role-tag" style={{ color, borderColor: color, background: `${color}15` }}>
          {role.role}
        </div>
      ) : null}
      <div className="tt-const">
        {mp.constituency || '—'} · {mp.state || ''}
      </div>
      <div className="tt-row">
        <div className="tt-cell">
          <div className="l">Party</div>
          <div className="v" style={{ color }}>
            {mp.party}
          </div>
        </div>
        <div className="tt-cell">
          <div className="l">Coalition</div>
          <div className="v">{mp.coalition || '—'}</div>
        </div>
      </div>
      <div className="tt-hint">[ click to select ]</div>
    </div>
  )
}
