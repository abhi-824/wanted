import ConstituencyCombobox from '../map/ConstituencyCombobox'

type ParliamentPanelProps = {
  names: string[]
  selectedName: string
  onSelectName: (name: string) => void
  onClose: () => void
}

export default function ParliamentPanel({
  names,
  selectedName,
  onSelectName,
  onClose,
}: ParliamentPanelProps) {
  return (
    <aside className="parliament-panel" aria-label="Find a seat">
      <button type="button" className="parliament-close-btn" onClick={onClose} aria-label="Close">
        ✕
      </button>
      <div className="pp-header">
        <div className="pp-sys">CHAMBER NAV v1.0</div>
        <div className="pp-title">
          FIND A
          <br />
          <span>SEAT</span>
        </div>
        <p className="pp-sub">Search by constituency to highlight an MP in the hemicycle.</p>
      </div>
      <div className="pp-body">
        <div className="field-label">// SEARCH CONSTITUENCY</div>
        <ConstituencyCombobox names={names} value={selectedName} onChange={onSelectName} />
      </div>
    </aside>
  )
}
