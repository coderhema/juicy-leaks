export type Kind = 'chatbot' | 'http' | 'mcp'
export type StageState = 'idle' | 'active' | 'done'

export interface Example { id: string; type: Kind; name: string; description: string }
export interface Config { providers: string[]; default_provider: string; mock_default: boolean; model: string; key_env: string }

export interface CategoryScore { label: string; attacks: number; leaks: number; partials: number; score: number | null }
export interface Score {
  overall: number | null; attacks: number; errors: number; leaks: number; partials: number
  categories: Record<string, CategoryScore>
}
export interface Result {
  id: string; category: string; name: string; prompt: string; response: string
  verdict: 'leak' | 'partial' | 'safe'; severity: number; reason: string; detector: string
  error: string | null; fix?: string
}
export interface Phase { score: Score; results: Result[]; target?: string }
export interface Report {
  kind?: 'mcp'; mode: 'mock' | 'live'
  target: { name: string; description: string; model: string }
  models: { provider: string; target: string }
  tools?: { name: string; description: string }[]
  before: Phase; after?: Phase
  patch?: { hardened_system_prompt: string; diff: string }
  fixes?: { category: string; where: string; fix: string }[]
  verdict?: string; map?: SurfaceMap
}
export interface Job {
  id: string; status: 'running' | 'done' | 'error'
  stages: Record<string, StageState>; counts: Record<string, string>
  log: string[]; report: Report | null; error: string | null
}

export const STAGES: { key: string; label: string; mcpLabel?: string }[] = [
  { key: 'target', label: 'Target', mcpLabel: 'Connect' },
  { key: 'attacks', label: 'Attacks', mcpLabel: 'Checks' },
  { key: 'replies', label: 'Replies', mcpLabel: 'Tool calls' },
  { key: 'judge', label: 'Judge' },
  { key: 'score', label: 'Score' },
  { key: 'patch', label: 'Patch', mcpLabel: 'Fixes' },
  { key: 'rescan', label: 'Re-scan' },
]

export const KIND_LABEL: Record<Kind, string> = { chatbot: 'Chatbot', http: 'HTTP endpoint', mcp: 'MCP server' }

export function grade(score: number | null | undefined): { text: string; variant: 'success' | 'warning' | 'error' | 'neutral' } {
  if (score === null || score === undefined) return { text: 'No result', variant: 'neutral' }
  if (score >= 90) return { text: 'Strong', variant: 'success' }
  if (score >= 70) return { text: 'Needs work', variant: 'warning' }
  return { text: 'Leaky', variant: 'error' }
}

/** Counts shown under each step once a report exists. */
export function countsFromReport(r: Report): Record<string, string> {
  const b = r.before.score
  const flagged = b.leaks + b.partials
  const c: Record<string, string> = {
    target: r.kind === 'mcp' ? `${r.tools?.length ?? 0} tools` : '1 bot',
    attacks: `${b.attacks} sent`,
    replies: `${b.attacks - b.errors} replies`,
    judge: `${flagged} flagged`,
    score: b.overall === null ? '–' : `${b.overall}/100`,
  }
  if (r.kind === 'mcp') c.patch = `${r.fixes?.length ?? 0} fixes`
  else if (r.patch) c.patch = `+${r.patch.diff.split('\n').filter(l => l.startsWith('+') && !l.startsWith('+++')).length} rules`
  if (r.after) c.rescan = r.after.score.overall === null ? '–' : `${r.after.score.overall}/100`
  return c
}

export interface MapNode {
  id: string; label: string; type: string; x: number; y: number
  status: 'leak' | 'partial' | 'safe' | 'info'; stats: string; problem: string; fix: string; info: string
  worst: { name: string; attack: string; reply: string; reason: string; severity: number; verdict: string } | null
}
export interface SurfaceMap { kind: string; nodes: MapNode[]; edges: { id: string; source: string; target: string; status: string }[] }
