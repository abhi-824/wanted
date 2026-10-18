import { useEffect } from 'react'

import type { ParliamentRecord } from '../../api/types'
import { ordinalSuffix } from '../../lib/format'

interface PerformanceBarsProps {
  parliamentRecord: ParliamentRecord | null
  severityPercentile: number | null
  mountKey: number
}

interface BarModel {
  key: string
  label: string
  display: string
  fillPct: number | null
  avgTickPct: number | null
  fillClass: string
  naTooltip?: string
  valueTitle?: string
}

function pctFromRatio(ratio: number | null | undefined): number | null {
  if (ratio == null) return null
  return Math.min(100, Math.max(0, ratio * 100))
}

function attendanceFillClass(pct: number, nationalAvgPct: number | null): string {
  if (pct < 50) return 'red'
  if (nationalAvgPct != null && pct < nationalAvgPct) return 'gold'
  return 'green'
}

function questionsFillClass(questions: number, nationalAvg: number | null): string {
  if (nationalAvg == null || nationalAvg <= 0) return 'blue'
  if (questions < nationalAvg * 0.5) return 'red'
  if (questions < nationalAvg) return 'gold'
  return 'green'
}

function buildBars(
  pr: ParliamentRecord | null,
  severityPercentile: number | null,
): BarModel[] {
  const note = pr?.note ?? undefined
  const natAttPct = pctFromRatio(pr?.national_avg_attendance)
  const attPct = pctFromRatio(pr?.attendance)

  const attendance: BarModel = {
    key: 'attendance',
    label: 'Attendance',
    display:
      attPct != null ? `${attPct.toFixed(1).replace(/\.0$/, '')}%` : 'N/A',
    fillPct: attPct,
    avgTickPct: natAttPct,
    fillClass:
      attPct != null ? attendanceFillClass(attPct, natAttPct) : 'blue',
    naTooltip: attPct == null ? note : undefined,
  }

  const natQ = pr?.national_avg_questions ?? null
  const questionsCount = pr?.questions ?? null
  let qFill: number | null = null
  if (questionsCount != null && natQ != null && natQ > 0) {
    qFill = Math.min(100, (questionsCount / (2 * natQ)) * 100)
  }

  const questions: BarModel = {
    key: 'questions',
    label: 'Questions asked',
    display: questionsCount != null ? String(questionsCount) : 'N/A',
    fillPct: qFill,
    avgTickPct: natQ != null && natQ > 0 ? 50 : null,
    fillClass:
      questionsCount != null
        ? questionsFillClass(questionsCount, natQ)
        : 'blue',
    naTooltip: questionsCount == null ? note : undefined,
  }

  const bars: BarModel[] = [attendance, questions]

  if (severityPercentile != null) {
    bars.push({
      key: 'severity',
      label: 'Severity percentile',
      display: `${severityPercentile}${ordinalSuffix(severityPercentile)}`,
      fillPct: severityPercentile,
      avgTickPct: 50,
      fillClass: 'red',
      valueTitle:
        'Ranked among MPs with pending criminal cases — not an absolute score.',
    })
  }

  return bars
}

function footnote(pr: ParliamentRecord | null): string {
  if (!pr) {
    return 'Performance data: PRS Legislative Research MPTrack'
  }
  const src = pr.source?.trim() || 'PRS Legislative Research MPTrack'
  const start = pr.data_period_start
  const end = pr.data_period_end
  if (start && end) return `${src} · ${start} – ${end}`
  return src
}

export default function PerformanceBars({
  parliamentRecord,
  severityPercentile,
  mountKey,
}: PerformanceBarsProps) {
  const bars = buildBars(parliamentRecord, severityPercentile)

  useEffect(() => {
    const t = window.setTimeout(() => {
      document
        .querySelectorAll('.dossier-page .bar-fill[data-pct]')
        .forEach((el) => {
          const node = el as HTMLElement
          node.style.width = `${node.dataset.pct}%`
        })
    }, 80)
    return () => window.clearTimeout(t)
  }, [mountKey])

  return (
    <div className="bar-section animate-in stagger-3">
      <div className="section-title">// performance stats</div>
      {bars.map((b) => (
        <div className="bar-row" key={b.key}>
          <div className="bar-label-row">
            <span className="bar-label">{b.label}</span>
            <span
              className={`bar-pct ${b.display === 'N/A' ? 'bar-val-muted' : ''}`}
              title={b.naTooltip ?? b.valueTitle}
            >
              {b.display}
              {b.key === 'severity' ? ' percentile' : ''}
            </span>
          </div>
          <div className="bar-track">
            {b.avgTickPct != null && b.fillPct != null ? (
              <span
                className="bar-avg"
                style={{ left: `${b.avgTickPct}%` }}
                aria-hidden
              />
            ) : null}
            <div className="bar-track-inner">
              {b.fillPct != null ? (
                <div
                  className={`bar-fill ${b.fillClass}`}
                  data-pct={String(b.fillPct)}
                />
              ) : null}
            </div>
          </div>
        </div>
      ))}
      <div className="bar-footnote">{footnote(parliamentRecord)}</div>
    </div>
  )
}
