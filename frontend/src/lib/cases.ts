import type { CriminalCase } from '../api/types'

export function splitSectionCodes(raw: string | null | undefined): string[] {
  if (!raw) return []
  return raw
    .split(/[,/]| and /)
    .map((s) => s.trim())
    .filter(Boolean)
}

export function extractAllSectionCodes(cases: CriminalCase[]): string[] {
  const codes = new Set<string>()
  for (const c of cases) {
    for (const code of splitSectionCodes(c.ipc_sections)) {
      codes.add(code)
    }
  }
  return Array.from(codes)
}

export function countSectionOccurrences(cases: CriminalCase[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const c of cases) {
    for (const code of splitSectionCodes(c.ipc_sections)) {
      const key = code.toUpperCase()
      counts[key] = (counts[key] ?? 0) + 1
    }
  }
  return counts
}

export function groupCasesBySection(cases: CriminalCase[]): CriminalCase[][] {
  const groups = new Map<string, CriminalCase[]>()
  cases.forEach((c, i) => {
    const codes = splitSectionCodes(c.ipc_sections).map((s) => s.toUpperCase())
    const signature = codes.length ? [...new Set(codes)].sort().join('|') : `__none-${i}`
    const list = groups.get(signature)
    if (list) list.push(c)
    else groups.set(signature, [c])
  })
  return Array.from(groups.values())
}
