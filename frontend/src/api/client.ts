import type {
  IpcSectionBatchResponse,
  MPDetail,
  MPSummary,
  StatsResponse,
} from './types'

export const API_BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body: unknown = await res.json()
      if (
        body &&
        typeof body === 'object' &&
        'detail' in body &&
        typeof (body as { detail: unknown }).detail === 'string'
      ) {
        message = (body as { detail: string }).detail
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status)
  }
  return res.json() as Promise<T>
}

export const api = {
  stats: (signal?: AbortSignal) => getJson<StatsResponse>('/stats', signal),

  constituencies: (signal?: AbortSignal) =>
    getJson<string[]>('/mps/constituencies', signal),

  mps: (limit?: number, signal?: AbortSignal) => {
    const qs = limit != null ? `?limit=${encodeURIComponent(String(limit))}` : ''
    return getJson<MPSummary[]>(`/mps${qs}`, signal)
  },

  mp: (id: number, signal?: AbortSignal) => getJson<MPDetail>(`/mps/${id}`, signal),

  ipcSections: (codes: string[], signal?: AbortSignal) => {
    const sections = codes.join(',')
    return getJson<IpcSectionBatchResponse>(
      `/ipc?sections=${encodeURIComponent(sections)}`,
      signal,
    )
  },
}
