import { useQuery, useMutation } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useProjects } from '@/contexts/ProjectsContext';

interface ProjectSourceItem {
  connection_id: string;
  table_count: number;
  is_documented: boolean;
  processed_tables_count?: number;
  friendly_name?: string;
  last_error_text?: string | null;
  last_error_timestamp?: string | null;
}

interface UpsertResult {
  count: number;
  instance_ids: string[];
}

export default function KgInstanceImport() {
  const { allProjects, allProjectsLoading } = useProjects();
  const [projectId, setProjectId] = useState<string>('');
  const [selectedConn, setSelectedConn] = useState<string>('');
  const [jsonText, setJsonText] = useState<string>('');
  const [validated, setValidated] = useState<{ ok: boolean; message: string; items?: any[] }>({ ok: false, message: '' });

  useEffect(() => {
    // Auto-select the first project if available
    if (!projectId && allProjects && allProjects.length > 0) {
      setProjectId(allProjects[0].id);
    }
  }, [allProjects, projectId]);

  const sourcesQuery = useQuery<{ items: ProjectSourceItem[] } | ProjectSourceItem[]>({
    queryKey: ['project-sources', projectId],
    queryFn: async () => {
      if (!projectId) return { items: [] } as any;
      const r = await fetch(`/api/projects/${projectId}/sources`);
      if (!r.ok) throw new Error('Failed to fetch project sources');
      return r.json();
    },
    enabled: !!projectId,
  });

  const sources: ProjectSourceItem[] = useMemo(() => {
    const data = sourcesQuery.data as any;
    if (!data) return [];
    // project_routes returns a list directly
    return Array.isArray(data) ? data : (data.items || []);
  }, [sourcesQuery.data]);

  const validate = () => {
    try {
      const parsed = JSON.parse(jsonText);
      if (!Array.isArray(parsed)) throw new Error('JSON must be an array');
      for (const it of parsed) {
        if (!it.table_name) throw new Error('Each item must have table_name');
        if (it.pg_id === undefined || it.pg_id === null) throw new Error('Each item must have pg_id');
      }
      setValidated({ ok: true, message: `Valid items: ${parsed.length}`, items: parsed });
    } catch (e: any) {
      setValidated({ ok: false, message: e.message });
    }
  };

  const upsertMutation = useMutation<UpsertResult>({
    mutationFn: async () => {
      if (!validated.ok || !validated.items) throw new Error('Please validate JSON first');
      const r = await fetch('/api/kg/upsert-instances' + (selectedConn ? `?connection_id=${encodeURIComponent(selectedConn)}` : ''), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(validated.items),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
  });

  const sample = `[
  {
    "table_name": "power_station",
    "pg_id": "123",
    "name": "某电站",
    "properties": { "capacity_mw": 500, "schema": "public" }
  },
  {
    "table_name": "airport",
    "pg_id": "A001",
    "name": "某机场",
    "properties": { "city": "某市" }
  }
]`;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Import Instances to Knowledge Graph</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setJsonText(sample)}>Load Sample</Button>
          <Button variant="outline" onClick={validate}>Validate</Button>
          <Button onClick={() => upsertMutation.mutate()} disabled={!validated.ok || upsertMutation.isPending}>
            {upsertMutation.isPending ? 'Importing…' : 'Upsert Instances'}
          </Button>
        </div>
      </div>

      <Card className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm font-medium mb-1">Project</div>
            <select
              className="w-full border rounded px-2 py-2 bg-background text-foreground"
              value={projectId}
              onChange={(e) => { setProjectId(e.target.value); setSelectedConn(''); }}
            >
              {allProjectsLoading && <option>Loading…</option>}
              {!allProjectsLoading && allProjects.map(p => (
                <option key={p.id} value={p.id}>{p.title || p.id}</option>
              ))}
            </select>
          </div>

          <div>
            <div className="text-sm font-medium mb-1">PostgreSQL Connection (optional)</div>
            <select
              className="w-full border rounded px-2 py-2 bg-background text-foreground"
              value={selectedConn}
              onChange={(e) => setSelectedConn(e.target.value)}
              disabled={!projectId}
            >
              <option value="">Default Neo4j</option>
              {sources.map(s => (
                <option key={s.connection_id} value={s.connection_id}>
                  {(s.friendly_name || s.connection_id) + (s.table_count ? ` · ${s.table_count} tables` : '')}
                </option>
              ))}
            </select>
            {sourcesQuery.isLoading && <div className="text-xs text-muted-foreground mt-1">Loading connections…</div>}
            {sourcesQuery.error && <div className="text-xs text-red-600 mt-1">Failed to load connections</div>}
          </div>

          <div>
            <div className="text-sm font-medium mb-1">Status</div>
            <div className="text-sm">
              {validated.ok ? (
                <Badge variant="secondary">Valid: {validated.items?.length}</Badge>
              ) : (
                <Badge variant="outline">Not validated</Badge>
              )}
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium">Instance Items (JSON Array)</div>
          </div>
          <textarea
            className="w-full h-[50vh] text-xs font-mono border rounded p-2"
            placeholder={sample}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
          />
          <div className="text-xs text-muted-foreground mt-1">Each item: {`{ table_name, pg_id, name?, properties? }`}</div>
        </div>

        {(validated.message || upsertMutation.data) && (
          <div className="space-y-2">
            {validated.message && (
              <Card className="p-2 text-xs">
                <div>{validated.ok ? 'Validation OK' : 'Validation Error'}: {validated.message}</div>
              </Card>
            )}
            {upsertMutation.data && (
              <Card className="p-2 text-xs">
                <pre>{JSON.stringify(upsertMutation.data, null, 2)}</pre>
              </Card>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}