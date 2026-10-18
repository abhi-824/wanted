import { MiniParliamentSvg } from './icons'

export default function ChamberPreview() {
  return (
    <div className="mini-parl">
      <MiniParliamentSvg />
      <div className="mini-legend">
        <div className="ml-row">
          <div className="ml-dot" style={{ background: '#e8630a' }} />
          NDA / BJP seats (right of Speaker)
        </div>
        <div className="ml-row">
          <div className="ml-dot" style={{ background: '#1a7fe0' }} />
          INDIA bloc (left of Speaker)
        </div>
        <div className="ml-row">
          <div className="ml-ring" />
          Gold ring = Cabinet minister
        </div>
        <div className="ml-row">
          <div className="ml-dot" style={{ background: '#d4a400' }} />
          Gold dot = Speaker (Om Birla)
        </div>
      </div>
    </div>
  )
}
