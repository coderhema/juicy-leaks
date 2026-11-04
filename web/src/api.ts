import type { Config, Example, Job } from './types'

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const getExamples = () => fetch('/api/examples').then(r => j<Example[]>(r))
export const getConfig = () => fetch('/api/config').then(r => j<Config>(r))
export const getJob = (id: string) => fetch(`/api/scan/${id}`).then(r => j<Job>(r))
export const startScan = (body: object) =>
  fetch('/api/scan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(r => j<{ id: string }>(r))
