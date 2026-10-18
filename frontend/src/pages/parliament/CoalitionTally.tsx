import { useMemo } from 'react'

import type { MPSummary } from '../../api/types'
import { MAJORITY } from './layout'

type CoalitionTallyProps = {
  members: MPSummary[]
}

function bucket(coalition: string | null): 'NDA' | 'INDIA' | 'Others' {
  if (coalition === 'NDA') return 'NDA'
  if (coalition === 'INDIA') return 'INDIA'
  return 'Others'
}

export default function CoalitionTally({ members }: CoalitionTallyProps) {
  const counts = useMemo(() => {
    const c = { NDA: 0, INDIA: 0, Others: 0 }
    for (const m of members) c[bucket(m.coalition)] += 1
    return c
  }, [members])

  return (
    <div className="coalition-tally" aria-label="Coalition seat counts">
      <div className="coalition-pill">
        <span className="dot nda" aria-hidden="true" />
        <span className="lbl">NDA</span>
        <span className="val nda">{counts.NDA}</span>
      </div>
      <div className="coalition-pill">
        <span className="dot india" aria-hidden="true" />
        <span className="lbl">INDIA</span>
        <span className="val india">{counts.INDIA}</span>
      </div>
      <div className="coalition-pill">
        <span className="dot others" aria-hidden="true" />
        <span className="lbl">Others</span>
        <span className="val others">{counts.Others}</span>
      </div>
      <div className="coalition-pill majority">
        <span className="lbl">Majority</span>
        <span className="val gold">{MAJORITY}</span>
      </div>
    </div>
  )
}
