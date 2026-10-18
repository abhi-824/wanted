export interface CriminalCase {
  id: number
  serial_no: string | null
  fir_no: string | null
  case_no: string | null
  court: string | null
  ipc_sections: string | null
  other_acts: string | null
  charges_framed: boolean
  charge_date: string | null
  is_serious: boolean
}

export interface ParliamentRecord {
  prs_id: number
  gender: string | null
  house: string | null
  membership_type: string | null
  term_label: string | null
  term_number: number | null
  term_start: string | null
  term_end: string | null
  in_office: boolean | null
  education_level: string | null
  education_details: string | null
  attendance: number | null
  debates: number | null
  questions: number | null
  private_member_bills: number | null
  national_avg_attendance: number | null
  national_avg_debates: number | null
  national_avg_questions: number | null
  national_avg_pmb: number | null
  state_avg_attendance: number | null
  state_avg_debates: number | null
  state_avg_questions: number | null
  state_avg_pmb: number | null
  note: string | null
  data_period_start: string | null
  data_period_end: string | null
  source: string | null
}

export interface MPSummary {
  myneta_id: number
  name: string
  constituency: string
  state: string
  party: string
  coalition: string | null
  age: number | null
  total_cases: number
  serious_cases: number
  severity_percentile: number | null
  gender: string | null
  attendance: number | null
}

export interface MPDetail {
  myneta_id: number
  name: string
  constituency: string
  state: string
  party: string
  coalition: string | null
  age: number | null
  total_cases: number
  serious_cases: number
  education: string | null
  photo_url: string | null
  assets_inr: number | null
  liabilities_inr: number | null
  self_profession: string | null
  spouse_profession: string | null
  voter_constituency: string | null
  election: string | null
  scraped_at: string | null
  severity_percentile: number | null
  severity_raw_score: number | null
  criminal_cases: CriminalCase[]
  parliament_record: ParliamentRecord | null
}

export interface StateBucket {
  state: string
  case_count: number
}

export interface StatsResponse {
  total_mps: number
  with_cases: number
  with_serious_cases: number
  avg_assets_inr: number | null
  top_states_by_cases: StateBucket[]
}

export interface IpcSection {
  section: string
  chapter: number | null
  chapter_title: string | null
  section_title: string
  section_desc: string
}

export interface IpcSectionBatchResponse {
  sections: Record<string, IpcSection>
  not_found: string[]
}
