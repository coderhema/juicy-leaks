import { useEffect, useMemo, useRef, useState } from 'react'
import { VStack } from '@astryxdesign/core/VStack'
import { HStack } from '@astryxdesign/core/HStack'
import { Heading } from '@astryxdesign/core/Heading'
import { Text } from '@astryxdesign/core/Text'
import { Button } from '@astryxdesign/core/Button'
import { SegmentedControl, SegmentedControlItem } from '@astryxdesign/core/SegmentedControl'
import { Selector } from '@astryxdesign/core/Selector'
import { Switch } from '@astryxdesign/core/Switch'
import { NumberInput } from '@astryxdesign/core/NumberInput'
import { FileInput } from '@astryxdesign/core/FileInput'
import { Banner } from '@astryxdesign/core/Banner'
import { Divider } from '@astryxdesign/core/Divider'
import { Grid } from '@astryxdesign/core/Grid'
import { EmptyState } from '@astryxdesign/core/EmptyState'
import { getConfig, getExamples, getJob, startScan } from './api'
import { FlowMap } from './FlowMap'
import { Results } from './Results'
import { KIND_LABEL, STAGES, countsFromReport, type Config, type Example, type Kind, type Report, type StageState } from './types'

const allDone = () => Object.fromEntries(STAGES.map(s => [s.key, 'done' as StageState]))

export default function App() {
  const [examples, setExamples] = useState<Example[]>([])
  const [config, setConfig] = useState<Config | null>(null)
  const [kind, setKind] = useState<Kind>('chatbot')
  const [exampleId, setExampleId] = useState('bank_bot')
  const [advanced, setAdvanced] = useState(false)
  const [live, setLive] = useState(false)
  const [provider, setProvider] = useState('nvidia')
  const [mutations, setMutations] = useState(1)
  const [limit, setLimit] = useState<number | null>(null)
  const [compare, setCompare] = useState(true)
  const [agent, setAgent] = useState(true)
  const [file, setFile] = useState<File | null>(null)

  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState<Record<string, StageState>>({})
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [status, setStatus] = useState('')
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState<string | null>(null)
  const poll = useRef<number | undefined>(undefined)

  useEffect(() => {
    getExamples().then(setExamples).catch(e => setError(`Can't reach the GuardRail Lens server: ${e.message}`))
    getConfig().then(c => { setConfig(c); setProvider(c.default_provider) }).catch(() => {})
    return () => window.clearInterval(poll.current)
  }, [])

  const options = useMemo(() => examples.filter(e => e.type === kind)
    .map(e => ({ value: e.id, label: e.name, description: e.description })), [examples, kind])

  const pickKind = (k: string) => {
    setKind(k as Kind)
    const first = examples.find(e => e.type === k)
    if (first) setExampleId(first.id)
  }

  const showReport = (r: Report) => {
    setReport(r); setStages(allDone()); setCounts(countsFromReport(r)); setKind((r.kind as Kind) ?? kind)
  }

  const run = async (override?: { example: string; kind: Kind }) => {
    const ex = override?.example ?? exampleId
    if (override) { setKind(override.kind); setExampleId(override.example) }
    setError(null); setReport(null); setCounts({}); setStages({ target: 'active' }); setRunning(true); setStatus('Starting…')
    try {
      const { id } = await startScan({
        example: ex, mock: override ? true : !live, provider, mutations, limit: limit || null, compare, agent,
      })
      poll.current = window.setInterval(async () => {
        try {
          const job = await getJob(id)
          setStages(job.stages); setCounts(job.counts); setStatus(job.log.at(-1) ?? '')
          if (job.status === 'running') return
          window.clearInterval(poll.current); setRunning(false)
          if (job.status === 'error') { setError(job.error); setStages({}) } else if (job.report) showReport(job.report)
        } catch (e) { window.clearInterval(poll.current); setRunning(false); setError(String(e)) }
      }, 600)
    } catch (e) { setRunning(false); setStages({}); setError((e as Error).message) }
  }

  const loadFile = async (f: File | File[] | null) => {
    const one = Array.isArray(f) ? f[0] : f
    setFile(one ?? null)
    if (!one) return
    try { showReport(JSON.parse(await one.text())); setError(null) } catch { setError('That file is not a GuardRail Lens report.') }
  }

  const selected = examples.find(e => e.id === exampleId)

  return (
    <VStack maxWidth={980} width="100%" paddingInline={6} paddingBlock={8} gap={8} style={{ marginInline: 'auto' }}>
      <VStack gap={2}>
        <img src="/logo.png" alt="GuardRail Lens" style={{ height: 64, width: "auto", alignSelf: "flex-start" }} />
        <Text type="large" color="secondary">Red-team your chatbots, MCP servers and endpoints before attackers do.</Text>
      </VStack>

      {error && <Banner status="error" title="Something went wrong" description={error} isDismissable onDismiss={() => setError(null)} />}

      <VStack gap={4}>
        <VStack gap={1}>
          <Heading level={2}>1 · Choose what to test</Heading>
          <Text type="supporting">Pick a kind of target and one of the built-in examples (all fake data).</Text>
        </VStack>
        <SegmentedControl label="Target type" value={kind} onChange={pickKind} size="lg">
          {(['chatbot', 'http', 'mcp'] as Kind[]).map(k => <SegmentedControlItem key={k} value={k} label={KIND_LABEL[k]} />)}
        </SegmentedControl>
        <Grid columns={{ minWidth: 280 }} gap={4} align="end">
          <Selector label="Example" options={options} value={exampleId} onChange={v => v && setExampleId(v)} size="lg" />
          <HStack gap={3} vAlign="center">
            <Button label={running ? 'Scanning…' : 'Run scan'} variant="primary" size="lg" isLoading={running} onClick={() => run()} isDisabled={!selected}
              tooltip="Sends about 30 attacks to the target, grades every reply, then writes and tests a fix." />
            <Switch label="Advanced" value={advanced} onChange={setAdvanced} labelTooltip="Live model, provider, number of attacks, open a saved report." />
          </HStack>
        </Grid>
        {kind === 'http' && <Text type="supporting">The demo endpoint starts by itself. Endpoints are scored but not patched, since we can't edit their prompt.</Text>}

        {advanced && (
          <VStack gap={4} padding={4} style={{ background: 'var(--color-background-muted)', borderRadius: 'var(--radius-container)' }}>
            <Text type="supporting">Optional settings. The defaults are fine for a demo.</Text>
            <Grid columns={{ minWidth: 220 }} gap={4}>
              <Switch label="Use a real model (live)" value={live} onChange={setLive}
                description={config ? `Needs ${config.key_env} on the server. Off = mock mode, no key needed.` : undefined} />
              <Selector label="Model provider" value={provider} onChange={v => v && setProvider(v)}
                options={(config?.providers ?? ['nvidia', 'groq', 'custom']).map(p => ({ value: p, label: p === 'nvidia' ? 'NVIDIA NIM (Meta models)' : p === 'groq' ? 'Groq (Llama)' : 'Custom (OpenAI-compatible)' }))} />
              {kind !== 'mcp' && <NumberInput label="Rewrites per attack" value={mutations} onChange={setMutations}
                description="Extra AI-written variants of each attack." />}
              {kind !== 'mcp' && <NumberInput label="Max attacks" value={limit} onChange={setLimit} placeholder="All 30" />}
              {kind === 'mcp' && <Switch label="Also scan the hardened server" value={compare} onChange={setCompare} />}
              {kind === 'mcp' && <Switch label="Let an AI agent use the tools" value={agent} onChange={setAgent} />}
              <FileInput label="Open a saved report" value={file} onChange={loadFile} accept=".json" />
            </Grid>
          </VStack>
        )}
      </VStack>

      <Divider />

      <VStack gap={4}>
        <VStack gap={1}>
          <Heading level={2}>2 · Watch the scan</Heading>
          <Text type="supporting">Each step lights up as it runs; the numbers show what happened.</Text>
        </VStack>
        <FlowMap kind={kind} states={stages} counts={counts} />
        {running && status && <Text type="supporting">{status}</Text>}
      </VStack>

      {!report && !running && (
        <EmptyState title="No scan yet" headingLevel={3}
          description="Not sure where to start? Run the demo: we attack a fake bank chatbot and show you what leaked and how to fix it. Takes a few seconds, no API key."
          actions={<Button label="Try the demo" variant="primary" onClick={() => run({ example: 'bank_bot', kind: 'chatbot' })} />} />
      )}

      {report && <><Divider /><Results report={report} /></>}
    </VStack>
  )
}
