import { useQuery, useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useProjects } from '@/contexts/ProjectsContext';
import GraphVisualization from '@/components/GraphVisualization';

interface GraphNode {
  id: string;
  labels: string[];
  name?: string;
  english_name?: string;
  [key: string]: any;
}

interface SearchResponse {
  nodes: GraphNode[];
  page: { total: number };
}

interface SubgraphResponse {
  nodes: GraphNode[];
  relationships: Array<{
    id: string;
    type: string;
    start_node_id: string;
    end_node_id: string;
    [key: string]: any;
  }>;
}

interface GraphStats {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

interface Neo4jConnectionItem {
  connection_id: string;
  connection_name?: string;
}

export default function KgSpatialRelations() {
  const { allProjects, allProjectsLoading } = useProjects();
  const [projectId, setProjectId] = useState('');
  const [connectionId, setConnectionId] = useState('');

  const [activeTab, setActiveTab] = useState<'browse' | 'import'>('browse');

  // Browse state
  const [searchTerm, setSearchTerm] = useState('');
  const [labelFilter, setLabelFilter] = useState('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [depth, setDepth] = useState(2);
  const [typeFilter, setTypeFilter] = useState('');

  type Operator = 'contains' | 'equals';
  interface FilterCondition { key: string; op: Operator; value: string }
  const [conditions, setConditions] = useState<FilterCondition[]>([]);
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [hoverHighlight, setHoverHighlight] = useState(true);

  // Import state
  const [jsonText, setJsonText] = useState('');
  const [validImport, setValidImport] = useState<{ ok: boolean; message: string; items?: any[] }>({ ok: false, message: '' });

  useEffect(() => {
    if (!projectId && allProjects && allProjects.length > 0) setProjectId(allProjects[0].id);
  }, [allProjects, projectId]);

  // List project postgres connections (to pick Neo4j connection context)
  const neo4jQuery = useQuery<Neo4jConnectionItem[]>({
    queryKey: ['project-neo4j', projectId],
    queryFn: async () => {
      if (!projectId) return [];
      const r = await fetch(`/api/projects/${projectId}/neo4j-connections`);
      if (!r.ok) throw new Error('Failed to fetch connections');
      return r.json();
    },
    enabled: !!projectId,
  });

  const statsQuery = useQuery<GraphStats>({
    queryKey: ['kg-stats', connectionId],
    queryFn: async () => {
      const url = new URL('/api/kg/graph/stats', window.location.origin);
      if (connectionId) url.searchParams.set('connection_id', connectionId);
      const r = await fetch(url.toString());
      if (!r.ok) throw new Error('Failed to fetch stats');
      return r.json();
    },
  });

  const searchQuery = useQuery<SearchResponse>({
    queryKey: ['kg-search', searchTerm, labelFilter, connectionId],
    queryFn: async () => {
      const url = new URL('/api/kg/graph/search', window.location.origin);
      if (searchTerm) url.searchParams.set('name', searchTerm);
      if (labelFilter) url.searchParams.set('labels', labelFilter);
      url.searchParams.set('limit', '50');
      if (connectionId) url.searchParams.set('connection_id', connectionId);
      const r = await fetch(url.toString());
      if (!r.ok) throw new Error('Failed to search');
      return r.json();
    },
    enabled: activeTab === 'browse' && (!!searchTerm || !!labelFilter),
  });

  const subgraphMutation = useMutation<SubgraphResponse, Error, string>({
    mutationFn: async (nodeId: string) => {
      const url = new URL('/api/kg/graph/subgraph', window.location.origin);
      url.searchParams.set('root_id', nodeId);
      url.searchParams.set('depth', String(depth));
      url.searchParams.set('limit', '500');
      if (connectionId) url.searchParams.set('connection_id', connectionId);
      const r = await fetch(url.toString());
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
  });

  const deleteRel = useMutation<{ message: string }, Error, string>({
    mutationFn: async (relId: string) => {
      const url = new URL(`/api/graph/relationships/${encodeURIComponent(relId)}`, window.location.origin);
      if (connectionId) url.searchParams.set('connection_id', connectionId);
      const r = await fetch(url.toString(), { method: 'DELETE' });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    onSuccess: () => {
      if (selectedNode) subgraphMutation.mutate(selectedNode.id);
    }
  });

  const nodeMap = useMemo(() => {
    const m = new Map<string, GraphNode>();
    subgraphMutation.data?.nodes.forEach(n => m.set(n.id, n));
    return m;
  }, [subgraphMutation.data]);

  const relTypes = useMemo(() => {
    const set = new Set<string>();
    subgraphMutation.data?.relationships.forEach(r => set.add(r.type));
    return Array.from(set).sort();
  }, [subgraphMutation.data]);

  const matchesNode = useCallback((n: GraphNode) => {
    if (!conditions.length) return true;
    return conditions.every(c => {
      const val = (n as any)[c.key] ?? (n as any).properties?.[c.key];
      const s = (val === undefined || val === null) ? '' : String(val);
      if (c.op === 'equals') return s === c.value;
      return s.toLowerCase().includes((c.value || '').toLowerCase());
    });
  }, [conditions]);

  const filteredNodes = useMemo(() => {
    const all = subgraphMutation.data?.nodes || [];
    return all.filter(matchesNode);
  }, [subgraphMutation.data, matchesNode]);

  const filteredRels = useMemo(() => {
    const all = subgraphMutation.data?.relationships || [];
    const allowedIds = new Set(filteredNodes.map(n => n.id));
    return (typeFilter ? all.filter(r => r.type === typeFilter) : all).filter(r => allowedIds.has(r.start_node_id) && allowedIds.has(r.end_node_id));
  }, [subgraphMutation.data, typeFilter, filteredNodes]);

  const onSelectNode = useCallback((n: GraphNode) => {
    setSelectedNode(n);
    subgraphMutation.mutate(n.id);
  }, [subgraphMutation]);

  const validateImport = () => {
    try {
      const parsed = JSON.parse(jsonText);
      if (!Array.isArray(parsed)) throw new Error('JSON must be an array');
      for (const it of parsed) {
        if (!it.source || !it.target) throw new Error('Each item must have source and target');
      }
      setValidImport({ ok: true, message: `Valid items: ${parsed.length}`, items: parsed });
    } catch (e: any) {
      setValidImport({ ok: false, message: e.message });
    }
  };

  const importMutation = useMutation<{ count: number }, Error>({
    mutationFn: async () => {
      if (!validImport.ok || !validImport.items) throw new Error('Validate first');
      const url = new URL('/api/kg/relationships/spatial', window.location.origin);
      if (connectionId) url.searchParams.set('connection_id', connectionId);
      const r = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(validImport.items),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    onSuccess: () => {
      if (selectedNode) subgraphMutation.mutate(selectedNode.id);
    }
  });

  const sample = `[
  {
    "source": { "table_name": "power_station", "pg_id": "123" },
    "target": { "table_name": "airport", "pg_id": "A001" },
    "type": "NEARBY",
    "properties": { "distance_km": 7.5 }
  },
  {
    "source": { "node_id": "instance:public.power_station:123" },
    "target": { "node_id": "instance:public.transmission_line:456" },
    "type": "INTERSECTS"
  }
]`;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Spatial Relations</h1>
        <div className="flex gap-2">
          <Button variant={activeTab === 'browse' ? 'default' : 'outline'} onClick={() => setActiveTab('browse')}>Browse</Button>
          <Button variant={activeTab === 'import' ? 'default' : 'outline'} onClick={() => setActiveTab('import')}>Import</Button>
        </div>
      </div>

      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm font-medium mb-1">Project</div>
            <select className="w-full border rounded px-2 py-2" value={projectId} onChange={e => { setProjectId(e.target.value); setConnectionId(''); }}>
              {allProjectsLoading && <option>Loading…</option>}
              {!allProjectsLoading && allProjects.map(p => (
                <option key={p.id} value={p.id}>{p.title || p.id}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Neo4j Connection (optional)</div>
            <select className="w-full border rounded px-2 py-2" value={connectionId} onChange={e => setConnectionId(e.target.value)} disabled={!projectId}>
              <option value="">Default</option>
              {(neo4jQuery.data || []).map(s => (
                <option key={s.connection_id} value={s.connection_id}>{s.connection_name || s.connection_id}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="text-sm font-medium mb-1">Stats</div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Badge variant="secondary">Nodes: {statsQuery.data?.total_nodes ?? 0}</Badge>
              <Badge variant="outline">Rels: {statsQuery.data?.total_relationships ?? 0}</Badge>
            </div>
          </div>
        </div>
      </Card>

      {activeTab === 'browse' && (
        <Card className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 items-end">
            <div>
              <div className="text-sm mb-1">Search nodes by name</div>
              <input className="w-full border rounded px-2 py-2" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="e.g., 电站" />
            </div>
            <div>
              <div className="text-sm mb-1">Filter by label</div>
              <select className="w-full border rounded px-2 py-2" value={labelFilter} onChange={e => setLabelFilter(e.target.value)}>
                <option value="">All</option>
                <option value="Ontology">Ontology</option>
                <option value="Table">Table</option>
                <option value="Instance">Instance</option>
                <option value="Location">Location</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => searchQuery.refetch()}>Search</Button>
              {selectedNode && <Button variant="outline" onClick={() => subgraphMutation.mutate(selectedNode.id)}>Refresh</Button>}
            </div>
          </div>

          {searchQuery.data && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-auto">
              {searchQuery.data.nodes.map(n => (
                <Card key={n.id} className="p-2 cursor-pointer hover:bg-accent" onClick={() => onSelectNode(n)}>
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">{n.name || n.english_name || n.id}</div>
                    <div className="flex gap-1">
                      {n.labels.map(l => <Badge key={l} variant="outline" className="text-2xs">{l}</Badge>)}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">{n.id}</div>
                </Card>
              ))}
            </div>
          )}

          {selectedNode && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-sm">Root: <span className="font-mono">{selectedNode.id}</span></div>
                <div className="flex gap-2 items-center">
                  <div className="text-sm">Depth</div>
                  <select className="border rounded px-2 py-1" value={depth} onChange={e => setDepth(Number(e.target.value))}>
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                  </select>
                  <div className="text-sm">Type</div>
                  <select className="border rounded px-2 py-1" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
                    <option value="">All</option>
                    {relTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <div className="text-sm">Node filters</div>
                  <div className="flex flex-col gap-1">
                    {conditions.map((c, idx) => (
                      <div key={idx} className="flex gap-1 items-center">
                        <input className="w-28 border rounded px-1 py-0.5" placeholder="key" value={c.key} onChange={e => setConditions(cs => cs.map((cc,i) => i===idx?{...cc,key:e.target.value}:cc))} />
                        <select className="border rounded px-1 py-0.5" value={c.op} onChange={e => setConditions(cs => cs.map((cc,i) => i===idx?{...cc,op:(e.target.value as Operator)}:cc))}>
                          <option value="contains">contains</option>
                          <option value="equals">equals</option>
                        </select>
                        <input className="w-32 border rounded px-1 py-0.5" placeholder="value" value={c.value} onChange={e => setConditions(cs => cs.map((cc,i) => i===idx?{...cc,value:e.target.value}:cc))} />
                        <Button size="sm" variant="outline" onClick={() => setConditions(cs => cs.filter((_,i)=>i!==idx))}>X</Button>
                      </div>
                    ))}
                    <Button size="sm" variant="outline" onClick={() => setConditions(cs => [...cs, {key:'', op:'contains', value:''}])}>Add filter</Button>
                  </div>
                </div>
              </div>

              <div className="flex flex-col md:flex-row gap-4">
                <div className="md:w-1/2 w-full overflow-auto max-h-[50vh] border rounded">
                  <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted">
                      <th className="p-2 text-left">Type</th>
                      <th className="p-2 text-left">Start</th>
                      <th className="p-2 text-left">End</th>
                      <th className="p-2 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRels.map(rel => {
                      const s = nodeMap.get(rel.start_node_id);
                      const e = nodeMap.get(rel.end_node_id);
                      return (
                        <tr key={rel.id} className="border-b hover:bg-accent/40">
                          <td className="p-2"><Badge variant="secondary">{rel.type}</Badge></td>
                          <td className="p-2">
                            <div className="font-mono text-xs">{rel.start_node_id}</div>
                            <div className="text-xs text-muted-foreground">{s?.name || s?.english_name}</div>
                          </td>
                          <td className="p-2">
                            <div className="font-mono text-xs">{rel.end_node_id}</div>
                            <div className="text-xs text-muted-foreground">{e?.name || e?.english_name}</div>
                          </td>
                          <td className="p-2">
                            <Button size="sm" variant="outline" onClick={() => deleteRel.mutate(rel.id)}>Delete</Button>
                          </td>
                        </tr>
                      );
                    })}
                    {!filteredRels.length && (
                      <tr><td className="p-2 text-sm text-muted-foreground" colSpan={4}>No relationships in current subgraph</td></tr>
                    )}
                  </tbody>
                  </table>
                </div>
                <div className="md:w-1/2 w-full">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-sm font-medium">Subgraph Preview</div>
                    <div className="flex items-center gap-2 text-xs">
                      <label className="flex items-center gap-1"><input type="checkbox" checked={hoverHighlight} onChange={e => setHoverHighlight(e.target.checked)} /> Hover highlight</label>
                      <label className="flex items-center gap-1"><input type="checkbox" checked={showEdgeLabels} onChange={e => setShowEdgeLabels(e.target.checked)} /> Edge labels</label>
                      <Button size="sm" variant="outline" onClick={() => {
                        // Export CSV edges
                        const rows = [['id','type','start','end'], ...filteredRels.map(r => [r.id, r.type, r.start_node_id, r.end_node_id])];
                        const csv = rows.map(r => r.map(x => '"' + String(x).replace(/"/g,'""') + '"').join(',')).join('\n');
                        const blob = new Blob([csv], { type: 'text/csv' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url; a.download = 'relations.csv'; a.click(); URL.revokeObjectURL(url);
                      }}>Export CSV</Button>
                    </div>
                  </div>
                  <GraphVisualization
                    nodes={filteredNodes}
                    relationships={filteredRels}
                    height="400px"
                    highlightNeighborsOnHover={hoverHighlight}
                    showEdgeLabels={showEdgeLabels}
                    onNodeClick={(n) => setSelectedNode(n)}
                  />
                </div>
              </div>
            </div>
          )}
        </Card>
      )}

      {activeTab === 'import' && (
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">Import Spatial Relationships (JSON Array)</div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setJsonText(sample)}>Load Sample</Button>
              <Button variant="outline" onClick={validateImport}>Validate</Button>
              <Button onClick={() => importMutation.mutate()} disabled={!validImport.ok || importMutation.isPending}>{importMutation.isPending ? 'Importing…' : 'Import'}</Button>
            </div>
          </div>
          <textarea className="w-full h-[50vh] text-xs font-mono border rounded p-2" value={jsonText} onChange={e => setJsonText(e.target.value)} />
          <div className="text-xs text-muted-foreground">Item: {`{ source: {node_id|table_name+pg_id}, target: {...}, type: 'CONTAINS|ADJACENT_TO|NEARBY|INTERSECTS|RELATED_TO', properties? }`}</div>
          {(validImport.message || importMutation.data) && (
            <Card className="p-2 text-xs">
              {validImport.message && <div>{validImport.ok ? 'Validation OK' : 'Validation Error'}: {validImport.message}</div>}
              {importMutation.data && <pre className="mt-2">{JSON.stringify(importMutation.data, null, 2)}</pre>}
            </Card>
          )}
        </Card>
      )}
    </div>
  );
}