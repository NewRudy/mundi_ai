import { useQuery, useMutation } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
// Using local tabs and native selects to keep dependencies minimal
import { Search, GitBranch, Activity, Database } from 'lucide-react';
import GraphVisualization from '@/components/GraphVisualization';

interface GraphStats {
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

interface GraphNode {
  id: string;
  labels: string[];
  name?: string;
  english_name?: string;
  created_at?: string;
  [key: string]: any;
}

interface SearchResponse {
  nodes: GraphNode[];
  page: {
    limit: number;
    offset: number;
    total: number;
    has_more: boolean;
  };
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
  page: {
    limit: number;
    offset: number;
    has_more: boolean;
  };
  meta: {
    root_id: string;
    depth: number;
    node_count: number;
    relationship_count: number;
  };
}

type TabKey = 'search' | 'details' | 'stats';

export default function KgOverview() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLabels, setSelectedLabels] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [graphDepth, setGraphDepth] = useState<number>(2);
  const [subgraphData, setSubgraphData] = useState<SubgraphResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('search');
  const [relTypeFilter, setRelTypeFilter] = useState<string>('');
  const [nodePropFilter, setNodePropFilter] = useState<string>('');

  // Fetch graph statistics
  const statsQuery = useQuery<GraphStats>({
    queryKey: ['kg-stats'],
    queryFn: async () => {
      const r = await fetch('/api/kg/graph/stats');
      if (!r.ok) throw new Error('Failed to fetch stats');
      return r.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Search nodes
  const searchQuery = useQuery<SearchResponse>({
    queryKey: ['kg-search', searchTerm, selectedLabels],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchTerm) params.append('name', searchTerm);
      if (selectedLabels) params.append('labels', selectedLabels);
      params.append('limit', '50');
      
      const r = await fetch(`/api/kg/graph/search?${params}`);
      if (!r.ok) throw new Error('Failed to search nodes');
      return r.json();
    },
    enabled: searchTerm.length > 0 || selectedLabels.length > 0,
  });

  // Fetch subgraph
  const fetchSubgraph = useMutation({
    mutationFn: async (nodeId: string) => {
      const params = new URLSearchParams({
        root_id: nodeId,
        depth: graphDepth.toString(),
        limit: '500',
      });
      
      const r = await fetch(`/api/kg/graph/subgraph?${params}`);
      if (!r.ok) throw new Error('Failed to fetch subgraph');
      return r.json() as Promise<SubgraphResponse>;
    },
    onSuccess: (data) => {
      setSubgraphData(data);
    },
  });

  const handleNodeSelect = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    fetchSubgraph.mutate(node.id);
  }, [fetchSubgraph]);

  const handleSearch = useCallback(() => {
    searchQuery.refetch();
  }, [searchQuery]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <GitBranch className="h-6 w-6" />
          Knowledge Graph Overview
        </h1>
        <Button 
          variant="outline"
          onClick={() => statsQuery.refetch()}
        >
          Refresh Stats
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Nodes</p>
              <p className="text-2xl font-semibold">
                {statsQuery.data?.total_nodes?.toLocaleString() || '0'}
              </p>
            </div>
            <Database className="h-8 w-8 text-muted-foreground" />
          </div>
        </Card>
        
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Relationships</p>
              <p className="text-2xl font-semibold">
                {statsQuery.data?.total_relationships?.toLocaleString() || '0'}
              </p>
            </div>
            <Activity className="h-8 w-8 text-muted-foreground" />
          </div>
        </Card>

        <Card className="p-4">
          <div>
            <p className="text-sm text-muted-foreground mb-2">Node Types</p>
            <div className="flex flex-wrap gap-1">
              {statsQuery.data && Object.entries(statsQuery.data.nodes)
                .slice(0, 3)
                .map(([label, count]) => (
                  <Badge key={label} variant="secondary" className="text-xs">
                    {label}: {count}
                  </Badge>
                ))}
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div>
            <p className="text-sm text-muted-foreground mb-2">Relationship Types</p>
            <div className="flex flex-wrap gap-1">
              {statsQuery.data && Object.entries(statsQuery.data.relationships)
                .slice(0, 3)
                .map(([type, count]) => (
                  <Badge key={type} variant="outline" className="text-xs">
                    {type}: {count}
                  </Badge>
                ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <Button variant={activeTab === 'search' ? 'default' : 'outline'} size="sm" onClick={() => setActiveTab('search')}>Search & Explore</Button>
        <Button variant={activeTab === 'details' ? 'default' : 'outline'} size="sm" onClick={() => setActiveTab('details')}>Node Details</Button>
        <Button variant={activeTab === 'stats' ? 'default' : 'outline'} size="sm" onClick={() => setActiveTab('stats')}>Detailed Stats</Button>
      </div>

      {activeTab === 'search' && (
        <div className="space-y-4">
          {/* Search Section */}
          <Card className="p-4">
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Search by name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="flex-1"
                />
                <select
                  className="w-48 border rounded px-2 py-1 bg-background text-foreground"
                  value={selectedLabels}
                  onChange={(e) => setSelectedLabels(e.target.value)}
                >
                  <option value="">All Labels</option>
                  <option value="Ontology">Ontology</option>
                  <option value="Table">Table</option>
                  <option value="Instance">Instance</option>
                  <option value="Location">Location</option>
                  <option value="Concept">Concept</option>
                </select>
                <Button onClick={handleSearch}>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>

              {/* Search Results */}
              {searchQuery.data && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Found {searchQuery.data.page.total} results
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-96 overflow-y-auto">
                    {searchQuery.data.nodes.map((node) => (
                      <Card
                        key={node.id}
                        className="p-3 cursor-pointer hover:bg-accent transition-colors"
                        onClick={() => handleNodeSelect(node)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-sm">
                              {node.name || node.english_name || node.id}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              ID: {node.id}
                            </p>
                          </div>
                          <div className="flex gap-1">
                            {node.labels.map(label => (
                              <Badge key={label} variant="outline" className="text-xs">
                                {label}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Graph Visualization */}
          {subgraphData && (
            <Card className="p-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">
                    Subgraph Visualization
                  </h3>
                  <div className="flex items-center gap-2">
                    <label className="text-sm">Depth:</label>
                    <select
                      className="w-20 border rounded px-2 py-1 bg-background text-foreground"
                      value={graphDepth.toString()}
                      onChange={(e) => setGraphDepth(Number(e.target.value))}
                    >
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3">3</option>
                    </select>
                    <label className="text-sm">Rel Type:</label>
                    <select
                      className="w-40 border rounded px-2 py-1 bg-background text-foreground"
                      value={relTypeFilter}
                      onChange={(e) => setRelTypeFilter(e.target.value)}
                    >
                      <option value="">All</option>
                      {Array.from(new Set((subgraphData?.relationships || []).map(r => r.type))).map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <label className="text-sm">Node filter:</label>
                    <input
                      className="w-56 border rounded px-2 py-1 bg-background text-foreground"
                      placeholder="prop text contains..."
                      value={nodePropFilter}
                      onChange={(e) => setNodePropFilter(e.target.value)}
                    />
                    {selectedNode && (
                      <>
                        <Button 
                          size="sm" 
                          onClick={() => fetchSubgraph.mutate(selectedNode.id)}
                        >
                          Refresh
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => {
                          if (!subgraphData) return;
                          const filteredNodes = (subgraphData.nodes || []).filter(n => {
                            if (!nodePropFilter) return true;
                            try {
                              return JSON.stringify(n).toLowerCase().includes(nodePropFilter.toLowerCase());
                            } catch { return true; }
                          });
                          const nodeIds = new Set(filteredNodes.map(n => n.id));
                          const filteredRels = (subgraphData.relationships || []).filter(r => (
                            (!relTypeFilter || r.type === relTypeFilter) && nodeIds.has(r.start_node_id) && nodeIds.has(r.end_node_id)
                          ));
                          const payload = { nodes: filteredNodes, relationships: filteredRels };
                          const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = 'subgraph.json';
                          a.click();
                          URL.revokeObjectURL(url);
                        }}>Export JSON</Button>
                      </>
                    )}
                  </div>
                </div>

                <div className="text-sm text-muted-foreground">
                  Showing {subgraphData.meta.node_count} nodes and {subgraphData.meta.relationship_count} relationships
                </div>

                {(() => {
                  const filteredNodes = (subgraphData.nodes || []).filter(n => {
                    if (!nodePropFilter) return true;
                    try {
                      return JSON.stringify(n).toLowerCase().includes(nodePropFilter.toLowerCase());
                    } catch { return true; }
                  });
                  const nodeIds = new Set(filteredNodes.map(n => n.id));
                  const filteredRels = (subgraphData.relationships || []).filter(r => (
                    (!relTypeFilter || r.type === relTypeFilter) && nodeIds.has(r.start_node_id) && nodeIds.has(r.end_node_id)
                  ));
                  return (
                    <GraphVisualization 
                      nodes={filteredNodes}
                      relationships={filteredRels}
                      height="600px"
                      onNodeClick={(n) => setSelectedNode(n)}
                    />
                  );
                })()}
              </div>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'details' && (
        selectedNode ? (
          <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4">Node Details</h3>
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <span className="text-sm text-muted-foreground">ID:</span>
                <span className="text-sm font-mono">{selectedNode.id}</span>
                
                <span className="text-sm text-muted-foreground">Labels:</span>
                <div className="flex gap-1">
                  {selectedNode.labels.map(label => (
                    <Badge key={label} variant="outline" className="text-xs">
                      {label}
                    </Badge>
                  ))}
                </div>
                
                {selectedNode.name && (
                  <>
                    <span className="text-sm text-muted-foreground">Name:</span>
                    <span className="text-sm">{selectedNode.name}</span>
                  </>
                )}
                
                {selectedNode.english_name && (
                  <>
                    <span className="text-sm text-muted-foreground">English Name:</span>
                    <span className="text-sm">{selectedNode.english_name}</span>
                  </>
                )}
                
                {selectedNode.created_at && (
                  <>
                    <span className="text-sm text-muted-foreground">Created:</span>
                    <span className="text-sm">
                      {new Date(selectedNode.created_at).toLocaleString()}
                    </span>
                  </>
                )}
              </div>
              
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-2">All Properties</h4>
                <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-96">
                  {JSON.stringify(selectedNode, null, 2)}
                </pre>
              </div>
            </div>
          </Card>
        ) : (
          <Card className="p-8 text-center text-muted-foreground">
            Select a node from search results to view details
          </Card>
        )
      )}

      {activeTab === 'stats' && (
        <Card className="p-4">
            <h3 className="text-lg font-semibold mb-4">Detailed Statistics</h3>
            
            {statsQuery.data && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-sm font-medium mb-3">Node Labels</h4>
                  <div className="space-y-2">
                    {Object.entries(statsQuery.data.nodes).map(([label, count]) => (
                      <div key={label} className="flex items-center justify-between">
                        <span className="text-sm">{label}</span>
                        <Badge variant="secondary">{count.toLocaleString()}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <h4 className="text-sm font-medium mb-3">Relationship Types</h4>
                  <div className="space-y-2">
                    {Object.entries(statsQuery.data.relationships).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between">
                        <span className="text-sm">{type}</span>
                        <Badge variant="outline">{count.toLocaleString()}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
        </Card>
      )}
    </div>
  );
}
