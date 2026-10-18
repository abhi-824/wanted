type StatChipProps = {
  value: string
  label: string
  tone?: 'red' | 'gold' | 'blue'
}

export default function StatChip({ value, label, tone }: StatChipProps) {
  const nClass = tone ? `n ${tone}` : 'n'
  return (
    <div className="stat-chip">
      <div className={nClass}>{value}</div>
      <div className="l">{label}</div>
    </div>
  )
}
