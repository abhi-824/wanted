export default function StatusBar() {
  return (
    <div className="statusbar">
      <div className="sb">
        <div className="sb-dot live" aria-hidden="true" />
        LIVE — 18TH LOK SABHA 2024
      </div>
      <div className="sb">SOURCE: ECI + ADR</div>
      <div className="sb">543 SEATS · 41 PARTIES</div>
      <div className="sb" style={{ marginLeft: 'auto' }}>
        NETACHECK v1.0
      </div>
    </div>
  )
}
