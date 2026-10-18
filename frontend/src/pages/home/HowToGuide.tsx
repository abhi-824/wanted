const GUIDE_CARDS = [
  {
    className: 'guide-card gc-dot',
    icon: '🟠',
    title: 'Each dot = one MP',
    body: (
      <>
        The chamber shows <b>543 seats</b> arranged in 6 blocks of 11 rows — exactly as the real Lok
        Sabha. Each coloured dot is one elected MP, coloured by their party.
      </>
    ),
  },
  {
    className: 'guide-card gc-ring',
    icon: '⭕',
    title: 'Gold ring = Cabinet minister',
    body: (
      <>
        Ministers have a <b>gold outer ring</b> around their seat dot. PM Modi, Amit Shah, Rajnath
        Singh and other cabinet members are on the <b>right side</b>, front rows.
      </>
    ),
  },
  {
    className: 'guide-card gc-hover',
    icon: '👆',
    title: 'Hover to identify',
    body: (
      <>
        Move your cursor over any dot to see the <b>MP&apos;s name, party, constituency</b> and case
        count instantly. MPs with criminal cases show a red badge.
      </>
    ),
  },
  {
    className: 'guide-card gc-click',
    icon: '🗂',
    title: 'Click to open dossier',
    body: (
      <>
        Click any seat to open the <b>GTA-style dossier card</b> — real IPC sections, asset
        declarations, wanted-level stars, and party info from ADR affidavit data.
      </>
    ),
  },
  {
    className: 'guide-card gc-side',
    icon: '⬅ ➡',
    title: 'Left vs right side',
    body: (
      <>
        <b>Right side</b> of the Speaker = ruling NDA coalition. <b>Left side</b> = INDIA opposition.
        Front rows = senior leaders. This mirrors the actual chamber.
      </>
    ),
  },
  {
    className: 'guide-card gc-esc',
    icon: '✕',
    title: 'Close & navigate',
    body: (
      <>
        Press <b>Esc</b> or click ✕ to close the dossier panel. The chamber rescales automatically.
        Works on any screen size — try resizing the window.
      </>
    ),
  },
] as const

export default function HowToGuide() {
  return (
    <>
      <div className="guide-header">// HOW TO USE THE CHAMBER</div>

      <div className="guide-grid">
        {GUIDE_CARDS.map((card) => (
          <div key={card.title} className={card.className}>
            <span className="gc-icon">{card.icon}</span>
            <div className="gc-title">{card.title}</div>
            <div className="gc-body">{card.body}</div>
          </div>
        ))}
      </div>
    </>
  )
}
