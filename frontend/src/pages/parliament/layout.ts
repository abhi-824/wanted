import type { MPSummary } from '../../api/types'
import { partyColor, roleForName, ROLES } from '../../lib/parties'

// --- CHAMBER GEOMETRY ---

export const TOTAL_SEATS = 543
export const MAJORITY = 272

const BLOCKS = 6
const ROWS = 11
const ARC_SPAN = 162
const BLOCK_GAP = 3.5
const BSPAN = (ARC_SPAN - BLOCK_GAP * (BLOCKS - 1)) / BLOCKS
const ARC_START = 180 + (180 - ARC_SPAN) / 2

export type CoalitionSide = 'INDIA' | 'Others' | 'NDA'

export interface ChamberSeat {
  x: number
  y: number
  r: number
  block: number
  row: number
  mp: MPSummary
  color: string
  coalition: string | null
  isMinister: boolean
}

export interface SpeakerSeat {
  x: number
  y: number
  r: number
  mp: MPSummary | null
  color: string
  block: number
  row: number
  isMinister: boolean
}

export interface ChamberLayout {
  seats: ChamberSeat[]
  speaker: SpeakerSeat
  width: number
  height: number
  cx: number
  cy: number
  seatRadius: number
  minR: number
  maxR: number
  rowSpacing: number
}

const ROLE_RANK: Record<string, number> = Object.fromEntries(
  Object.keys(ROLES).map((name, i) => [name, i]),
)

function coalitionSide(coalition: string | null): CoalitionSide {
  if (coalition === 'NDA') return 'NDA'
  if (coalition === 'INDIA') return 'INDIA'
  return 'Others'
}

function ministerRank(name: string): number {
  return ROLE_RANK[name] ?? 999
}

function sortMembers(members: MPSummary[]): MPSummary[] {
  return [...members].sort((a, b) => {
    const d = ministerRank(a.name) - ministerRank(b.name)
    return d !== 0 ? d : a.name.localeCompare(b.name)
  })
}

function makeRowCounts(total: number): number[] {
  const base = Math.floor(total / ROWS)
  const rem = total % ROWS
  return Array.from({ length: ROWS }, (_, i) => (i < rem ? base + 1 : base))
}

/** Split `total` into `parts` buckets (largest remainder). */
function distribute(total: number, parts: number): number[] {
  if (parts <= 0) return []
  const base = Math.floor(total / parts)
  const rem = total % parts
  return Array.from({ length: parts }, (_, i) => (i < rem ? base + 1 : base))
}

function blockGroups(counts: Record<CoalitionSide, number>): CoalitionSide[] {
  const total = counts.INDIA + counts.Others + counts.NDA
  if (total === 0) return Array.from({ length: BLOCKS }, () => 'Others' as CoalitionSide)

  const sides: CoalitionSide[] = ['INDIA', 'Others', 'NDA']
  const raw = sides.map((s) => ({
    side: s,
    count: counts[s],
    blocks: counts[s] > 0 ? Math.max(1, Math.round((counts[s] / total) * BLOCKS)) : 0,
  }))

  let assigned = raw.reduce((n, r) => n + r.blocks, 0)
  while (assigned > BLOCKS) {
    const idx = raw
      .map((r, i) => ({ i, blocks: r.blocks, count: r.count }))
      .sort((a, b) => b.blocks - a.blocks || b.count - a.count)[0]?.i
    if (idx == null || raw[idx].blocks <= 1) break
    raw[idx].blocks -= 1
    assigned -= 1
  }
  while (assigned < BLOCKS) {
    const idx = raw
      .map((r, i) => ({ i, count: r.count, blocks: r.blocks }))
      .sort((a, b) => b.count - a.count || a.blocks - b.blocks)[0]?.i
    if (idx == null) break
    raw[idx].blocks += 1
    assigned += 1
  }

  const groups: CoalitionSide[] = []
  for (const { side, blocks } of raw) {
    for (let i = 0; i < blocks; i++) groups.push(side)
  }
  while (groups.length < BLOCKS) groups.push('NDA')
  return groups.slice(0, BLOCKS)
}

function isSpeaker(mp: MPSummary): boolean {
  return mp.name === 'Om Birla' || roleForName(mp.name)?.role === 'Speaker'
}

interface RawSeat {
  x: number
  y: number
  r: number
  block: number
  row: number
  side: CoalitionSide
}

export function buildChamber(members: MPSummary[], w: number, h: number): ChamberLayout {
  const cx = w / 2
  const cy = h
  const minR = Math.min(w, h * 1.8) * 0.155
  const maxR = Math.min(w / 2, h) * 0.91
  const rowSpacing = (maxR - minR) / (ROWS - 1)
  const seatR = Math.max(3.5, Math.min(8, rowSpacing * 0.28))

  const speakerMp = members.find(isSpeaker) ?? null
  const floorMembers = speakerMp ? members.filter((m) => m.myneta_id !== speakerMp.myneta_id) : members

  const bySide: Record<CoalitionSide, MPSummary[]> = {
    INDIA: [],
    Others: [],
    NDA: [],
  }
  for (const m of floorMembers) {
    bySide[coalitionSide(m.coalition)].push(m)
  }
  for (const key of Object.keys(bySide) as CoalitionSide[]) {
    bySide[key] = sortMembers(bySide[key])
  }

  const counts: Record<CoalitionSide, number> = {
    INDIA: bySide.INDIA.length,
    Others: bySide.Others.length,
    NDA: bySide.NDA.length,
  }
  const groups = blockGroups(counts)

  const blockTotals: number[] = []
  for (let b = 0; b < BLOCKS; b++) {
    const side = groups[b]
    const blocksOnSide = groups.filter((g) => g === side).length
    const idxOnSide = groups.slice(0, b + 1).filter((g) => g === side).length - 1
    const share = distribute(counts[side], blocksOnSide)
    blockTotals[b] = share[idxOnSide] ?? 0
  }

  const rawSeats: RawSeat[] = []
  for (let b = 0; b < BLOCKS; b++) {
    const bS = ((ARC_START + b * (BSPAN + BLOCK_GAP)) * Math.PI) / 180
    const bE = bS + (BSPAN * Math.PI) / 180
    const rowCounts = makeRowCounts(blockTotals[b])
    for (let r = 0; r < ROWS; r++) {
      const arcR = minR + r * rowSpacing
      const n = rowCounts[r]
      for (let s = 0; s < n; s++) {
        const t = n === 1 ? (bS + bE) / 2 : bS + (s / (n - 1)) * (bE - bS)
        rawSeats.push({
          x: cx + arcR * Math.cos(t),
          y: cy + arcR * Math.sin(t),
          r: seatR,
          block: b,
          row: r,
          side: groups[b],
        })
      }
    }
  }

  rawSeats.sort((a, b) => a.block - b.block || a.row - b.row || a.x - b.x)

  const queues: Record<CoalitionSide, MPSummary[]> = {
    INDIA: [...bySide.INDIA],
    Others: [...bySide.Others],
    NDA: [...bySide.NDA],
  }

  const seats: ChamberSeat[] = []
  for (const spot of rawSeats) {
    const mp = queues[spot.side].shift()
    if (!mp) continue
    seats.push({
      x: spot.x,
      y: spot.y,
      r: spot.r,
      block: spot.block,
      row: spot.row,
      mp,
      color: partyColor(mp.party),
      coalition: mp.coalition,
      isMinister: roleForName(mp.name) != null && mp.name !== 'Om Birla',
    })
  }

  const speaker: SpeakerSeat = {
    x: cx,
    y: cy - minR * 0.52,
    r: Math.max(7, seatR * 1.7),
    mp: speakerMp,
    color: '#d4a400',
    block: -1,
    row: -1,
    isMinister: false,
  }

  return {
    seats,
    speaker,
    width: w,
    height: h,
    cx,
    cy,
    seatRadius: seatR,
    minR,
    maxR,
    rowSpacing,
  }
}

export function lighten(hex: string, amt = 75): string {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgb(${Math.min(255, r + amt)},${Math.min(255, g + amt)},${Math.min(255, b + amt)})`
}
