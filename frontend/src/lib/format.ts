export function normConstName(name: string | null | undefined): string {
  return (name || '')
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/\([^)]*\)/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ')
}

export function formatAvgAssetsCr(inr: number | null | undefined): string {
  if (inr == null) return '—'
  return `₹${(inr / 1_00_00_000).toFixed(0)}Cr`
}

export function inrToCr(inr: number | null | undefined): string | null {
  if (inr == null) return null
  return (inr / 1_00_00_000).toFixed(1)
}

export function formatAssetsCr(inr: number | null | undefined): string {
  const cr = inrToCr(inr)
  return cr != null ? `₹${cr} Cr` : '—'
}

export function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function seededPct(name: string, base: number, range: number): number {
  const seed = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return Math.min(99, Math.max(15, base + (seed % range)))
}

export function ordinalSuffix(n: number): string {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return s[(v - 20) % 10] || s[v] || s[0]
}
