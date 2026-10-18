import { useMemo } from 'react'
import { Link } from 'react-router'

import type { IpcSection, MPDetail } from '../../api/types'
import { formatAssetsCr } from '../../lib/format'
import {
  coalitionForParty,
  partyColor,
  roleForName,
  wantedLevel,
  type TagClass,
} from '../../lib/parties'
import CriminalCases from './CriminalCases'
import EducationBlock from './EducationBlock'
import NetworkGrid from './NetworkGrid'
import PerformanceBars from './PerformanceBars'
import ProfileHeader, { type ProfileTag } from './ProfileHeader'
import type { StatRow } from './StatsBlock'

interface DossierCardProps {
  mp: MPDetail
  ipcLookup: Record<string, IpcSection>
}

export default function DossierCard({ mp, ipcLookup }: DossierCardProps) {
  const color = partyColor(mp.party)
  const coalition = coalitionForParty(mp.party, mp.coalition)
  const role = roleForName(mp.name)
  const totalCases = mp.total_cases ?? 0
  const seriousCases = mp.serious_cases ?? 0
  const wl = wantedLevel(totalCases, seriousCases, role?.wl ?? 1)

  const tags = useMemo((): ProfileTag[] => {
    const list: ProfileTag[] = []
    if (role) list.push({ label: role.role, cls: role.tag })
    if (totalCases > 10) list.push({ label: `${totalCases} cases`, cls: 'tag-red' })
    else if (totalCases > 0)
      list.push({
        label: `${totalCases} case${totalCases > 1 ? 's' : ''}`,
        cls: 'tag-red',
      })
    else list.push({ label: 'Clean record', cls: 'tag-green' })
    if (coalition) {
      let cls: TagClass = 'tag-gold'
      if (coalition === 'NDA') cls = 'tag-orange'
      else if (coalition === 'INDIA') cls = 'tag-blue'
      list.push({ label: coalition, cls })
    }
    list.push({ label: mp.state, cls: 'tag-gold' })
    return list
  }, [role, totalCases, coalition, mp.state])

  const stats: StatRow[] = [
    {
      icon: '⚖️',
      label: 'CRIMINAL CASES',
      val: String(totalCases),
      cls: totalCases > 0 ? 'red' : '',
    },
    {
      icon: '🔴',
      label: 'SERIOUS CASES',
      val: String(seriousCases),
      cls: seriousCases > 0 ? 'red' : '',
    },
    {
      icon: '💰',
      label: 'DECLARED ASSETS',
      val: formatAssetsCr(mp.assets_inr),
      cls: 'gold',
    },
    {
      icon: '🗳️',
      label: 'PARTY',
      val: mp.party,
      style: { color },
    },
    {
      icon: '🏛️',
      label: 'COALITION',
      val: coalition || 'Other',
      cls: coalition === 'NDA' ? 'gold' : 'green',
    },
    { icon: '📍', label: 'STATE', val: mp.state, cls: '' },
  ]

  const pr = mp.parliament_record

  const network = [
    { name: mp.party, rel: 'political party' },
    { name: coalition || '—', rel: 'coalition' },
    { name: mp.state, rel: 'home state' },
    { name: mp.constituency, rel: 'constituency' },
  ]

  return (
    <>
      <ProfileHeader
        name={mp.name}
        constituency={mp.constituency}
        state={mp.state}
        party={mp.party}
        partyColor={color}
        photoUrl={mp.photo_url}
        wantedLevel={wl}
        tags={tags}
        stats={stats}
      />

      <EducationBlock
        educationLevel={pr?.education_level ?? null}
        educationDetails={pr?.education_details ?? null}
        fallbackEducation={mp.education}
      />

      <PerformanceBars
        parliamentRecord={pr}
        severityPercentile={mp.severity_percentile}
        mountKey={mp.myneta_id}
      />

      <CriminalCases cases={mp.criminal_cases} ipcLookup={ipcLookup} />

      <NetworkGrid people={network} />

      <div className="bottom-bar animate-in stagger-5">
        <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          <Link className="src-link" to={`/parliament/${mp.myneta_id}`}>
            view in lok sabha ↗
          </Link>
          <a
            className="src-link"
            href="https://myneta.info/LokSabha2024"
            target="_blank"
            rel="noreferrer"
          >
            source: myneta.info + sansad.in + ADR affidavit ↗
          </a>
        </div>
        <span className="adr-badge">data: ADR verified</span>
      </div>
    </>
  )
}
