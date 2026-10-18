import ViewTabs from '../../components/ViewTabs'
import type { StatsResponse } from '../../api/types'

type TopBarProps = {
  stats: StatsResponse | null
}

export default function TopBar({ stats }: TopBarProps) {
  const topRight = stats
    ? `${stats.total_mps} MPS · ${stats.with_cases} WITH CASES · ECI + ADR DATA`
    : '543 SEATS · 41 PARTIES · ECI + ADR DATA'

  return (
    <div className="topbar">
      <div className="logo">
        NETA<span>CHECK</span>
        <span className="logo-tag">// 18TH LOK SABHA</span>
      </div>
      <ViewTabs />
      <div className="top-right">{topRight}</div>
    </div>
  )
}
