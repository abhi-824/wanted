import { Link } from 'react-router'

import type { MPSummary } from '../../api/types'
import { initials } from '../../lib/format'
import { partyColor, roleForName } from '../../lib/parties'
import type { ChamberSeat } from './layout'

type SeatCardProps = {
  mp: MPSummary
  seat: ChamberSeat | null
  onClose: () => void
}

export default function SeatCard({ mp, seat, onClose }: SeatCardProps) {
  const color = partyColor(mp.party)
  const role = roleForName(mp.name)
  const seatLabel =
    seat != null ? `Block ${seat.block + 1} · Row ${seat.row + 1}` : mp.name === 'Om Birla' ? 'Speaker' : '—'

  return (
    <aside className="parliament-card-panel open" aria-label="Selected MP">
      <div className="parliament-card-inner">
        <button type="button" className="parliament-close-btn" onClick={onClose} aria-label="Close">
          ✕
        </button>
        <div className="parliament-card-body">
          <div className="pc-label">// SELECTED SEAT</div>
          <div className="pc-hero">
            <div className="pc-portrait" aria-hidden="true">
              <span className="pc-initials">{initials(mp.name)}</span>
              <span className="pc-party" style={{ color }}>
                {mp.party}
              </span>
            </div>
            <div>
              <h2 className="pc-name">{mp.name}</h2>
              <p className="pc-meta">
                {mp.constituency}
                <br />
                {mp.state} · Lok Sabha
              </p>
              {role ? <span className="pc-role">{role.role}</span> : null}
            </div>
          </div>
          <dl className="pc-stats">
            <div>
              <dt>Seat</dt>
              <dd>{seatLabel}</dd>
            </div>
            <div>
              <dt>Coalition</dt>
              <dd>{mp.coalition || 'Other'}</dd>
            </div>
            <div>
              <dt>Cases</dt>
              <dd className={mp.total_cases > 0 ? 'warn' : ''}>{mp.total_cases}</dd>
            </div>
            <div>
              <dt>Serious</dt>
              <dd className={mp.serious_cases > 0 ? 'warn' : ''}>{mp.serious_cases}</dd>
            </div>
          </dl>
          <Link className="pc-dossier-link" to={`/dossier/${mp.myneta_id}`}>
            Open full dossier →
          </Link>
        </div>
      </div>
    </aside>
  )
}
