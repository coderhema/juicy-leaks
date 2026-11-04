import { useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, type Node, type Edge, type NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { VStack } from '@astryxdesign/core/VStack'
import { HStack } from '@astryxdesign/core/HStack'
import { Text } from '@astryxdesign/core/Text'
import { Heading } from '@astryxdesign/core/Heading'
import { Badge } from '@astryxdesign/core/Badge'
import { Switch } from '@astryxdesign/core/Switch'
import { Card } from '@astryxdesign/core/Card'
import { CodeBlock } from '@astryxdesign/core/CodeBlock'
import type { MapNode, SurfaceMap } from './types'

const COLOR: Record<string, string> = {
  leak: 'var(--color-error, #dc2626)', partial: 'var(--color-warning, #d97706)',
  safe: 'var(--color-success, #16a34a)', info: 'var(--color-text-secondary, #64748b)',
}
const WORD: Record<string, { text: string; variant: 'error' | 'warning' | 'success' | 'neutral' }> = {
  leak: { text: 'Leaked', variant: 'error' }, partial: { text: 'Partly leaked', variant: 'warning' },
  safe: { text: 'Safe', variant: 'success' }, info: { text: 'Part of the target', variant: 'neutral' },
}
const CSS = `
.gl-node{padding:8px 12px;border-radius:var(--radius-container,10px);background:var(--color-background-surface,#fff);
 border:2px solid var(--c);min-width:150px;max-width:210px;font:inherit;cursor:pointer;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.gl-node .t{font-size:13px;font-weight:600;color:var(--color-text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gl-node .s{font-size:11px;color:var(--color-text-secondary)}
.gl-node .k{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:var(--c)}
.gl-node.leak{animation:glpulse 1.6s ease-in-out infinite}
.gl-node.sel{outline:3px solid var(--color-accent);outline-offset:2px}
@keyframes glpulse{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,.45)}50%{box-shadow:0 0 0 8px rgba(220,38,38,0)}}
.react-flow__edge.leak path{stroke-width:2.5}
`
const KIND: Record<string, string> = {
  attack: 'attack', target: 'your bot', prompt: 'instructions', secret: 'secret', pii: 'personal data', policy: 'rules',
  server: 'MCP server', tool: 'tool', input: 'inputs', output: 'output', data: 'data', agent: 'AI agent',
  endpoint: 'endpoint', route: 'route',
}

type Data = MapNode & { selected?: boolean } & Record<string, unknown>
function GlNode({ data }: NodeProps<Node<Data>>) {
  return (
    <div className={`gl-node ${data.status} ${data.selected ? 'sel' : ''}`} style={{ ['--c' as string]: COLOR[data.status] }}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="k">{KIND[data.type] ?? data.type}</div>
      <div className="t" title={data.label}>{data.label}</div>
      {data.stats && <div className="s">{data.stats}</div>}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}
const nodeTypes = { gl: GlNode }

/** Clickable graph of the target's surface; red paths show how attacks got through. */
export function AttackMap({ map }: { map: SurfaceMap }) {
  const firstBad = map.nodes.find(n => n.status === 'leak') ?? map.nodes[0]
  const [sel, setSel] = useState<string | undefined>(firstBad?.id)
  const [onlyProblems, setOnlyProblems] = useState(false)

  const { nodes, edges } = useMemo(() => {
    const keep = (n: MapNode) => !onlyProblems || n.status === 'leak' || n.status === 'partial' || n.status === 'info'
    const vis = new Set(map.nodes.filter(keep).map(n => n.id))
    const nodes: Node<Data>[] = map.nodes.filter(n => vis.has(n.id)).map(n => ({
      id: n.id, type: 'gl', position: { x: n.x, y: n.y }, data: { ...n, selected: n.id === sel },
    }))
    const edges: Edge[] = map.edges.filter(e => vis.has(e.source) && vis.has(e.target))
      .filter(e => !onlyProblems || e.status === 'leak' || e.status === 'partial')
      .map(e => ({
        id: e.id, source: e.source, target: e.target, className: e.status,
        animated: e.status === 'leak' || e.status === 'partial',
        style: { stroke: COLOR[e.status], strokeWidth: e.status === 'leak' ? 2.5 : 1.5, opacity: e.status === 'info' ? 0.5 : 1 },
      }))
    return { nodes, edges }
  }, [map, sel, onlyProblems])

  const node = map.nodes.find(n => n.id === sel)
  const w = node ? WORD[node.status] : null

  return (
    <VStack gap={3}>
      <style>{CSS}</style>
      <HStack gap={4} vAlign="center" wrap="wrap">
        <Text type="supporting">Click any box to see what went wrong and how to fix it. Red = leaked, amber = partly, green = safe.</Text>
        <Switch label="Show only problems" value={onlyProblems} onChange={setOnlyProblems} size="sm" />
      </HStack>
      <HStack gap={4} vAlign="stretch" wrap="wrap">
        <Card padding={0} width="62%" minHeight={520} data-testid="attack-map">
          <div style={{ width: '100%', height: 520 }}>
            <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.15 }}
              onNodeClick={(_, n) => setSel(n.id)} nodesDraggable={false} nodesConnectable={false}
              proOptions={{ hideAttribution: true }} minZoom={0.3}>
              <Background gap={24} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
        </Card>
        <Card padding={4} width="34%" data-testid="map-panel">
          {node && w ? (
            <VStack gap={3}>
              <VStack gap={1}>
                <Text type="label" color="secondary">{KIND[node.type] ?? node.type}</Text>
                <Heading level={3}>{node.label}</Heading>
                <HStack gap={2}><Badge variant={w.variant} label={w.text} />{node.stats && <Text type="supporting">{node.stats}</Text>}</HStack>
              </VStack>
              {node.problem && <VStack gap={1}><Text type="label">{node.status === 'leak' || node.status === 'partial' ? "What's wrong" : 'What this is'}</Text><Text>{node.problem}</Text></VStack>}
              {node.worst && <VStack gap={1}>
                <Text type="label">Worst attempt: {node.worst.name}</Text>
                <CodeBlock code={node.worst.attack || '(none)'} isWrapped width="100%" size="sm" hasCopyButton={false} maxHeight={130} />
                {node.worst.reply && <CodeBlock code={node.worst.reply} isWrapped width="100%" size="sm" hasCopyButton={false} maxHeight={150} />}
                <Text type="supporting">Judge: {node.worst.reason}</Text>
              </VStack>}
              {node.fix && <VStack gap={1}><Text type="label">Suggested fix</Text><Text>{node.fix}</Text></VStack>}
            </VStack>
          ) : <Text type="supporting">Click a box on the map.</Text>}
        </Card>
      </HStack>
    </VStack>
  )
}
