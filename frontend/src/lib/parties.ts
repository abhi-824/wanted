export const PARTY_COLORS: Record<string, string> = {
  BJP: '#e8630a',
  INC: '#1a7fe0',
  SP: '#e01a1a',
  TMC: '#1a9fe0',
  DMK: '#e01a80',
  TDP: '#e0c01a',
  JDU: '#1ae08a',
  SSUBT: '#e05a1a',
  NCPSP: '#1a5ae0',
  SHS: '#e07a1a',
  LJP: '#5ae01a',
  JMM: '#1ae0c0',
  AAP: '#1a40e0',
  YSRCP: '#1ae040',
  BJD: '#e0801a',
  SAD: '#e0e01a',
  NCP: '#801ae0',
  RJD: '#e0401a',
  CPI: '#e01a1a',
  CPIM: '#c01a1a',
  BSP: '#401ae0',
  IND: '#607080',
}

export const COALITIONS: Record<string, string> = {
  BJP: 'NDA',
  TDP: 'NDA',
  JDU: 'NDA',
  LJP: 'NDA',
  SHS: 'NDA',
  INC: 'INDIA',
  SP: 'INDIA',
  TMC: 'INDIA',
  DMK: 'INDIA',
  SSUBT: 'INDIA',
  NCPSP: 'INDIA',
  JMM: 'INDIA',
  AAP: 'INDIA',
}

export type TagClass = 'tag-orange' | 'tag-blue' | 'tag-green' | 'tag-red' | 'tag-gold'

export interface KnownRole {
  role: string
  tag: TagClass
  wl: number
}

export const ROLES: Record<string, KnownRole> = {
  'Narendra Modi': { role: 'Prime Minister', tag: 'tag-gold', wl: 5 },
  'Om Birla': { role: 'Speaker', tag: 'tag-gold', wl: 3 },
  'Rajnath Singh': { role: 'Defence Minister', tag: 'tag-orange', wl: 3 },
  'Amit Shah': { role: 'Home Minister', tag: 'tag-orange', wl: 4 },
  'Nitin Gadkari': { role: 'Road Transport Min.', tag: 'tag-orange', wl: 3 },
  'Piyush Goyal': { role: 'Commerce Minister', tag: 'tag-orange', wl: 2 },
  'Shivraj Singh Chauhan': { role: 'Agriculture Minister', tag: 'tag-orange', wl: 2 },
  'Jyotiraditya Scindia': { role: 'Civil Aviation Min.', tag: 'tag-orange', wl: 2 },
  'Manohar Lal Khattar': { role: 'Housing Minister', tag: 'tag-orange', wl: 2 },
  'Dharmendra Pradhan': { role: 'Education Minister', tag: 'tag-orange', wl: 2 },
  'Sarbananda Sonowal': { role: 'Ports Minister', tag: 'tag-orange', wl: 2 },
  'Mansukh Mandaviya': { role: 'Labour Minister', tag: 'tag-orange', wl: 2 },
  'G. Kishan Reddy': { role: 'Coal Minister', tag: 'tag-orange', wl: 2 },
  'Kiren Rijiju': { role: 'Parliamentary Affairs', tag: 'tag-orange', wl: 2 },
  'Chirag Paswan': { role: 'Food Processing Min.', tag: 'tag-orange', wl: 2 },
  'Arjun Ram Meghwal': { role: 'Law Minister', tag: 'tag-orange', wl: 2 },
  'Pralhad Joshi': { role: 'New & Renewable Energy', tag: 'tag-orange', wl: 2 },
  'Kinjarapu Ram Mohan Naidu': { role: 'Civil Aviation Min.', tag: 'tag-orange', wl: 2 },
  'Rahul Gandhi': { role: 'Leader of Opposition', tag: 'tag-blue', wl: 3 },
  'K. C. Venugopal': { role: 'INC Org. Secretary', tag: 'tag-blue', wl: 2 },
}

export function partyColor(party: string): string {
  return PARTY_COLORS[party] ?? '#c8a84b'
}

export function coalitionForParty(party: string, fromApi: string | null): string | null {
  return fromApi ?? COALITIONS[party] ?? null
}

export function roleForName(name: string): KnownRole | null {
  return ROLES[name] ?? null
}

export function wantedLevel(
  totalCases: number,
  seriousCases: number,
  roleFallback = 1,
): number {
  if (seriousCases >= 5) return 5
  if (seriousCases >= 3) return 4
  if (seriousCases >= 1) return 3
  if (totalCases >= 5) return 3
  if (totalCases >= 1) return 2
  return roleFallback
}
