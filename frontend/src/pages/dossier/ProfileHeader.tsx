import { useState } from 'react'

import type { TagClass } from '../../lib/parties'
import { initials } from '../../lib/format'
import StatsBlock, { type StatRow } from './StatsBlock'

export interface ProfileTag {
  label: string
  cls: TagClass
}

interface ProfileHeaderProps {
  name: string
  constituency: string
  state: string
  party: string
  partyColor: string
  photoUrl: string | null
  wantedLevel: number
  tags: ProfileTag[]
  stats: StatRow[]
}

export default function ProfileHeader({
  name,
  constituency,
  state,
  party,
  partyColor,
  photoUrl,
  wantedLevel,
  tags,
  stats,
}: ProfileHeaderProps) {
  const [photoFailed, setPhotoFailed] = useState(false)
  const showPhoto = photoUrl && !photoFailed

  return (
    <>
      <div className="top-bar animate-in">
        <span className="top-bar-label">// parliament dossier v1.0</span>
        <div className="wanted-row" aria-label={`Wanted level ${wantedLevel} of 5`}>
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className={`star ${i < wantedLevel ? 'on' : 'off'}`} />
          ))}
        </div>
      </div>

      <div className="hero animate-in stagger-2">
        <div className="portrait-wrap">
          <div className="portrait">
            {showPhoto ? (
              <img src={photoUrl} alt={name} onError={() => setPhotoFailed(true)} />
            ) : null}
            <div className="portrait-fallback" style={showPhoto ? { display: 'none' } : undefined}>
              {initials(name)}
            </div>
            <div className="portrait-party" style={{ color: partyColor }}>
              {party}
            </div>
          </div>
          <div className="portrait-corner tl" />
          <div className="portrait-corner tr" />
          <div className="portrait-corner bl" />
          <div className="portrait-corner br" />
        </div>
        <div>
          <div className="mp-name">{name}</div>
          <div className="mp-sub">
            {constituency} // {state} · Lok Sabha
          </div>
          <div className="tag-row">
            {tags.map((t) => (
              <span className={`tag ${t.cls}`} key={t.label}>
                {t.label}
              </span>
            ))}
          </div>
          <StatsBlock stats={stats} />
        </div>
      </div>
    </>
  )
}
