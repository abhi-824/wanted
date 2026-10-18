import { useRef } from 'react'

import type { CriminalCase, IpcSection } from '../../api/types'
import { countSectionOccurrences, groupCasesBySection } from '../../lib/cases'
import IpcPills from './IpcPills'

interface CriminalCasesProps {
  cases: CriminalCase[]
  ipcLookup: Record<string, IpcSection>
}

export default function CriminalCases({ cases, ipcLookup }: CriminalCasesProps) {
  const shownCountBadges = useRef(new Set<string>())
  shownCountBadges.current = new Set()

  if (cases.length === 0) {
    return (
      <div className="cases-section animate-in stagger-4">
        <div className="section-title">// criminal record</div>
        <div className="clean-record">
          <span style={{ color: '#5ec97a' }}>✓</span> No pending cases declared in 2024 ECI
          affidavit.
        </div>
      </div>
    )
  }

  const sectionCounts = countSectionOccurrences(cases)
  const groups = groupCasesBySection(cases)

  return (
    <div className="cases-section animate-in stagger-4">
      <div className="section-title">// pending cases</div>
      {groups.map((group, gi) => {
        const first = group[0]
        const isGrouped = group.length > 1
        const numbers = group.map((c, i) => c.serial_no || String(i + 1))
        const numLabel = isGrouped ? numbers.map((n) => `#${n}`).join(', ') : `#${numbers[0]}`
        const courts = [...new Set(group.map((c) => c.court).filter(Boolean))] as string[]
        const dates = group.map((c) => c.charge_date).filter(Boolean) as string[]
        const anySerious = group.some((c) => c.is_serious)

        return (
          <div className="case-item" key={gi}>
            <span className="case-num">{isGrouped ? `×${group.length}` : numLabel}</span>
            <div className="case-text">
              {isGrouped ? (
                <div className="case-serials">cases {numbers.map((n) => `#${n}`).join(', ')}</div>
              ) : null}
              {first.ipc_sections ? (
                <>
                  <strong>IPC:</strong> {first.ipc_sections}
                </>
              ) : null}
              {first.other_acts ? <> &nbsp;|&nbsp; {first.other_acts}</> : null}
              {courts.length ? (
                <>
                  <br />
                  <span className="case-meta">{courts.join(' · ')}</span>
                </>
              ) : null}
              {dates.length === 1 ? (
                <span className="case-meta"> · {dates[0]}</span>
              ) : null}
              {dates.length > 1 ? (
                <span className="case-meta">
                  {' '}
                  · {dates[0]} – {dates[dates.length - 1]}
                </span>
              ) : null}
              {anySerious ? (
                <>
                  <br />
                  <span className="case-serious">⚠ SERIOUS</span>
                </>
              ) : null}
              <IpcPills
                rawSectionsString={first.ipc_sections}
                lookup={ipcLookup}
                sectionCounts={sectionCounts}
                shownCountBadges={shownCountBadges}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
