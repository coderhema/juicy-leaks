import { useState } from 'react'
import { VStack } from '@astryxdesign/core/VStack'
import { HStack } from '@astryxdesign/core/HStack'
import { Heading } from '@astryxdesign/core/Heading'
import { Text } from '@astryxdesign/core/Text'
import { Badge } from '@astryxdesign/core/Badge'
import { TabList, Tab } from '@astryxdesign/core/TabList'
import { Table } from '@astryxdesign/core/Table'
import { CodeBlock } from '@astryxdesign/core/CodeBlock'
import { Collapsible, CollapsibleGroup } from '@astryxdesign/core/Collapsible'
import { Button } from '@astryxdesign/core/Button'
import { Card } from '@astryxdesign/core/Card'
import { Banner } from '@astryxdesign/core/Banner'
import { AttackMap } from './AttackMap'
import { grade, type Report, type Result } from './types'

const VERDICT: Record<string, { text: string; variant: 'error' | 'warning' | 'success' }> = {
  leak: { text: 'Leaked', variant: 'error' }, partial: { text: 'Partly leaked', variant: 'warning' }, safe: { text: 'Held', variant: 'success' },
}

function Explain({ children }: { children: string }) {
  return <Text type="supporting">{children}</Text>
}

/** One big score, then the details in tabs. */
export function Results({ report }: { report: Report }) {
  const [tab, setTab] = useState(report.map ? 'map' : 'categories')
  const isMcp = report.kind === 'mcp'
  const before = report.before.score
  const after = report.after?.score
  const main = after ?? before
  const g = grade(main.overall)
  const flagged = before.leaks + before.partials

  const cats = Object.entries(before.categories).map(([key, c]) => ({
    key, category: c.label, before: c.score ?? '–',
    after: after?.categories[key]?.score ?? '–', found: `${c.leaks + c.partials} of ${c.attacks}`,
  }))
  const worst = [...report.before.results].filter(r => r.verdict !== 'safe').sort((a, b) => b.severity - a.severity)

  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
    Object.assign(document.createElement('a'), { href: url, download: 'juicy_leaks_report.json' }).click()
  }

  return (
    <VStack gap={6}>
      <VStack gap={1}>
        <Heading level={2}>3 · Results</Heading>
        <Explain>Higher is safer. 100 means no attack got through.</Explain>
      </VStack>

      {report.verdict && <Banner status={flagged ? (after && (after.overall ?? 0) >= 90 ? 'warning' : 'error') : 'success'}
        title={report.verdict} collapsible={false} />}

      <Card padding={6}>
        <HStack gap={8} vAlign="center" wrap="wrap">
          <img src={flagged || before.errors ? '/mascot/spider_leak.gif' : '/mascot/clear.png'} data-testid="verdict-mascot"
            alt={flagged || before.errors ? 'Alarmed spider pointing at a leak' : 'Spider giving a thumbs up: nothing leaked'}
            style={{ height: 120, width: 'auto' }} />
          <VStack gap={1} data-testid="big-score">
            <Text type="label" color="secondary">{after ? (isMcp ? 'Hardened server score' : 'Score after the fix') : 'Safety score'}</Text>
            <Heading level={1} type="display-1">{main.overall ?? '–'}<Text type="large" color="secondary"> / 100</Text></Heading>
            <HStack gap={2}><Badge variant={g.variant} label={g.text} />
              <Badge variant={report.mode === 'live' ? 'info' : 'neutral'} label={report.mode === 'live' ? `Live · ${report.models.target}` : 'Mock mode'} /></HStack>
          </VStack>
          <VStack gap={2}>
            <Text type="large">{report.target.name}</Text>
            {after && <Text>Before: <Text weight="semibold">{before.overall ?? '–'}</Text> → after: <Text weight="semibold">{after.overall ?? '–'}</Text></Text>}
            <Text color="secondary">{flagged} of {before.attacks} {isMcp ? 'checks found a problem' : 'attacks got something out'}{before.errors ? ` · ${before.errors} errored` : ''}.</Text>
          </VStack>
        </HStack>
      </Card>

      <TabList value={tab} onChange={setTab} hasDivider>
        {report.map && <Tab value="map" label="Problem map" />}
        <Tab value="categories" label="By category" />
        <Tab value="findings" label="What leaked" endContent={worst.length ? <Badge variant="error" label={String(worst.length)} /> : undefined} />
        <Tab value="fix" label={isMcp ? 'How to fix' : 'The fix'} />
        <Tab value="all" label={isMcp ? 'All checks' : 'All transcripts'} />
      </TabList>

      {tab === 'map' && report.map && <AttackMap map={report.map} />}

      {tab === 'categories' && (
        <VStack gap={3}>
          <Explain>Each row is one kind of attack, scored before and after hardening.</Explain>
          <Table data={cats} idKey="key" columns={[
            { key: 'category', header: 'Category' },
            { key: 'found', header: 'Got through' },
            { key: 'before', header: 'Before', align: 'end' },
            { key: 'after', header: 'After', align: 'end' },
          ]} />
        </VStack>
      )}

      {tab === 'findings' && (
        <VStack gap={3}>
          <Explain>The worst findings first: what was asked and what came back.</Explain>
          {worst.length ? <Transcripts rows={worst.slice(0, 12)} open /> : <HStack gap={3} vAlign="center"><img src="/mascot/clear.png" alt="" style={{ height: 56, width: 'auto' }} /><Text>Nothing leaked. Every attack was refused.</Text></HStack>}
        </VStack>
      )}

      {tab === 'fix' && (isMcp ? (
        <VStack gap={3}>
          <HStack gap={3} vAlign="center"><img src="/mascot/working.png" alt="" style={{ height: 48, width: 'auto' }} />
            <Explain>{`Concrete changes for the server, one per problem found.${after ? ` The hardened server scores ${after.overall ?? '–'}/100.` : ''}`}</Explain></HStack>
          <Table data={(report.fixes ?? []).map((f, i) => ({ ...f, i }))} idKey="i" verticalAlign="top" columns={[
            { key: 'where', header: 'Where' }, { key: 'fix', header: 'Fix' }]} />
        </VStack>
      ) : (
        <VStack gap={3}>
          <HStack gap={3} vAlign="center"><img src={after && (after.overall ?? 0) >= 90 ? '/mascot/clear.png' : '/mascot/working.png'} alt="" style={{ height: 48, width: 'auto' }} />
            <Explain>{`Security rules added to the system prompt. Green lines are new.${after ? ` After the re-scan: ${after.overall ?? '–'}/100.` : ''}`}</Explain></HStack>
          {report.patch ? <CodeBlock code={report.patch.diff} language="markdown" isDiff isWrapped width="100%" title="system_prompt.diff" maxHeight={520} />
            : <Text>No patch was generated for this scan.</Text>}
        </VStack>
      ))}

      {tab === 'all' && (
        <VStack gap={3}>
          <Explain>{`Every ${isMcp ? 'check' : 'attack'} from the first scan, with the judge's verdict.`}</Explain>
          <Transcripts rows={report.before.results} />
          <HStack><Button label="Download report (JSON)" onClick={download} /></HStack>
        </VStack>
      )}
    </VStack>
  )
}

function Transcripts({ rows, open = false }: { rows: Result[]; open?: boolean }) {
  return (
    <CollapsibleGroup type="multiple" hasDividers>
      {rows.map((r, i) => {
        const v = r.error ? { text: 'Error', variant: 'warning' as const } : VERDICT[r.verdict]
        return (
          <Collapsible key={r.id + i} value={r.id + i} defaultIsOpen={open && i < 2} trigger={
            <HStack gap={2} vAlign="center"><Badge variant={v.variant} label={v.text} /><Text weight="medium">{r.name}</Text>
              <Text type="supporting">{r.category.replace(/_/g, ' ')}</Text></HStack>}>
            <VStack gap={2} paddingBlock={2}>
              <Text type="label">{r.detector === 'static' ? 'Checked' : 'Attack'}</Text>
              <CodeBlock code={r.prompt || '(none)'} isWrapped width="100%" size="sm" hasCopyButton={false} maxHeight={220} />
              {(r.response || r.error) && <>
                <Text type="label">Reply</Text>
                <CodeBlock code={r.error || r.response} isWrapped width="100%" size="sm" hasCopyButton={false} maxHeight={260} />
              </>}
              <Text type="supporting">Judge: {r.reason} (severity {r.severity}/10)</Text>
              {r.fix && <Text type="supporting">Fix: {r.fix}</Text>}
            </VStack>
          </Collapsible>
        )
      })}
    </CollapsibleGroup>
  )
}
