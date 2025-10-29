import { useQuery, useMutation } from '@tanstack/react-query';
import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface SchemaInfo {
  constraints: any[];
  indexes: any[];
  labels: string[];
  relationship_types: string[];
}

export default function KgSchemaManager() {
  const infoQuery = useQuery<SchemaInfo>({
    queryKey: ['kg-schema-info'],
    queryFn: async () => {
      const r = await fetch('/api/kg/schema/info');
      if (!r.ok) throw new Error('Failed to fetch schema info');
      return r.json();
    },
    refetchInterval: 30000,
  });

  const initMutation = useMutation({
    mutationFn: async () => {
      const r = await fetch('/api/kg/schema/init', { method: 'POST' });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    onSuccess: () => {
      void infoQuery.refetch();
    },
  });

  const counts = useMemo(() => ({
    constraints: infoQuery.data?.constraints?.length || 0,
    indexes: infoQuery.data?.indexes?.length || 0,
    labels: infoQuery.data?.labels?.length || 0,
    relTypes: infoQuery.data?.relationship_types?.length || 0,
  }), [infoQuery.data]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Neo4j Schema Manager</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => infoQuery.refetch()} disabled={infoQuery.isFetching}>Refresh</Button>
          <Button onClick={() => initMutation.mutate()} disabled={initMutation.isPending}>
            {initMutation.isPending ? 'Initializing…' : 'Initialize Schema'}
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">Constraints</div>
          <div className="text-2xl font-semibold">{counts.constraints}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">Indexes</div>
          <div className="text-2xl font-semibold">{counts.indexes}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">Labels</div>
          <div className="text-2xl font-semibold">{counts.labels}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-muted-foreground">Relationship Types</div>
          <div className="text-2xl font-semibold">{counts.relTypes}</div>
        </Card>
      </div>

      {/* Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Constraints</h2>
            <Badge variant="secondary">{counts.constraints}</Badge>
          </div>
          <div className="space-y-2 max-h-[50vh] overflow-auto">
            {infoQuery.data?.constraints?.map((c, idx) => (
              <details key={idx} className="rounded border p-2">
                <summary className="cursor-pointer text-sm">
                  {c.name || c.id || `constraint-${idx}`} — {c.type || c.constraintType || ''}
                </summary>
                <pre className="text-xs mt-2 bg-muted p-2 rounded overflow-auto">{JSON.stringify(c, null, 2)}</pre>
              </details>
            ))}
            {!infoQuery.data?.constraints?.length && <div className="text-sm text-muted-foreground">No constraints</div>}
          </div>
        </Card>

        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Indexes</h2>
            <Badge variant="secondary">{counts.indexes}</Badge>
          </div>
          <div className="space-y-2 max-h-[50vh] overflow-auto">
            {infoQuery.data?.indexes?.map((i, idx) => (
              <details key={idx} className="rounded border p-2">
                <summary className="cursor-pointer text-sm">
                  {i.name || i.id || `index-${idx}`} — {i.type || i.indexType || ''}
                </summary>
                <pre className="text-xs mt-2 bg-muted p-2 rounded overflow-auto">{JSON.stringify(i, null, 2)}</pre>
              </details>
            ))}
            {!infoQuery.data?.indexes?.length && <div className="text-sm text-muted-foreground">No indexes</div>}
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h2 className="text-lg font-semibold mb-2">Labels</h2>
        <div className="flex flex-wrap gap-2">
          {infoQuery.data?.labels?.map((l) => (
            <Badge key={l} variant="outline">{l}</Badge>
          ))}
          {!infoQuery.data?.labels?.length && <div className="text-sm text-muted-foreground">No labels</div>}
        </div>
      </Card>

      <Card className="p-4">
        <h2 className="text-lg font-semibold mb-2">Relationship Types</h2>
        <div className="flex flex-wrap gap-2">
          {infoQuery.data?.relationship_types?.map((t) => (
            <Badge key={t} variant="outline">{t}</Badge>
          ))}
          {!infoQuery.data?.relationship_types?.length && <div className="text-sm text-muted-foreground">No relationship types</div>}
        </div>
      </Card>

      {initMutation.data && (
        <Card className="p-4">
          <h2 className="text-lg font-semibold mb-2">Initialization Result</h2>
          <pre className="text-xs bg-muted p-2 rounded overflow-auto">{JSON.stringify(initMutation.data, null, 2)}</pre>
        </Card>
      )}
    </div>
  );
}