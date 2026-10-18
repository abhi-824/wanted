export interface StatRow {
  icon: string
  label: string
  val: string
  cls?: string
  style?: React.CSSProperties
}

interface StatsBlockProps {
  stats: StatRow[]
}

export default function StatsBlock({ stats }: StatsBlockProps) {
  return (
    <div className="stats-block">
      {stats.map((s) => (
        <div className="stat-row" key={s.label}>
          <span className="stat-icon">{s.icon}</span>
          <span className="stat-label">{s.label}</span>
          <span className={`stat-val ${s.cls ?? ''}`} style={s.style}>
            {s.val}
          </span>
        </div>
      ))}
    </div>
  )
}
