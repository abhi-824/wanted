import { useId, useState, type MutableRefObject } from 'react'

import type { IpcSection } from '../../api/types'
import { splitSectionCodes } from '../../lib/cases'

interface IpcPillsProps {
  rawSectionsString: string | null | undefined
  lookup: Record<string, IpcSection>
  sectionCounts: Record<string, number>
  shownCountBadges: MutableRefObject<Set<string>>
}

export default function IpcPills({
  rawSectionsString,
  lookup,
  sectionCounts,
  shownCountBadges,
}: IpcPillsProps) {
  const baseId = useId()
  const codes = splitSectionCodes(rawSectionsString)
  if (codes.length === 0) return null

  return (
    <div className="ipc-pill-row">
      {codes.map((code, idx) => (
        <IpcPill
          key={`${code}-${idx}`}
          code={code}
          lookup={lookup}
          sectionCounts={sectionCounts}
          shownCountBadges={shownCountBadges}
          idPrefix={baseId}
        />
      ))}
    </div>
  )
}

function IpcPill({
  code,
  lookup,
  sectionCounts,
  shownCountBadges,
  idPrefix,
}: {
  code: string
  lookup: Record<string, IpcSection>
  sectionCounts: Record<string, number>
  shownCountBadges: MutableRefObject<Set<string>>
  idPrefix: string
}) {
  const descId = `${idPrefix}-${code.replace(/[^a-zA-Z0-9]/g, '')}`
  const key = code.toUpperCase()
  const entry = lookup[key]
  const count = sectionCounts[key] ?? 1
  const [expanded, setExpanded] = useState(false)

  let countBadge: React.ReactNode = null
  if (count > 1 && !shownCountBadges.current.has(key)) {
    countBadge = (
      <span
        className="ipc-pill-count"
        title={`§${code} appears in ${count} cases total across this dossier`}
      >
        ×{count}
      </span>
    )
    shownCountBadges.current.add(key)
  }

  return (
    <div className="ipc-pill-wrap">
      <button
        type="button"
        className="ipc-pill"
        aria-expanded={expanded}
        title={entry ? entry.section_title : 'Description unavailable'}
        onClick={() => setExpanded((v) => !v)}
      >
        §{code}
        {countBadge}
      </button>
      <div
        className={`ipc-desc ${entry ? '' : 'not-found'}`}
        id={descId}
        hidden={!expanded}
      >
        {entry ? (
          <>
            {entry.chapter_title ? (
              <span className="ipc-chapter">{entry.chapter_title}</span>
            ) : null}
            <strong>{entry.section_title}</strong>
            <span>{entry.section_desc}</span>
          </>
        ) : (
          <>No description on file for section {code} yet.</>
        )}
      </div>
    </div>
  )
}
