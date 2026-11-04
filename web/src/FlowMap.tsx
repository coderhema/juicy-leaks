import { Stepper, Step } from '@astryxdesign/core/Stepper'
import { STAGES, type StageState } from './types'

/** Target → Attacks → Replies → Judge → Score → Patch → Re-scan, lit up as the scan runs. */
export function FlowMap({ kind, states, counts }: {
  kind: string; states: Record<string, StageState>; counts: Record<string, string>
}) {
  const firstOpen = STAGES.findIndex(s => states[s.key] !== 'done')
  const active = firstOpen === -1 ? STAGES.length : firstOpen
  return (
    <Stepper activeStep={active} label="Scan progress" density="compact"
      horizontalOptions={{ minimumStepWidth: 84, collapsedVariant: 'withLabel' }}>
      {STAGES.map((s, i) => (
        <Step key={s.key} step={i}
          label={kind === 'mcp' && s.mcpLabel ? s.mcpLabel : s.label}
          description={counts[s.key] ?? (states[s.key] === 'active' ? 'running…' : ' ')}
          status={states[s.key] === 'active' ? 'accent' : states[s.key] === 'done' ? 'success' : undefined} />
      ))}
    </Stepper>
  )
}
