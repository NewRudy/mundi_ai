import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Neo4jConn {
  connection_id: string;
  connection_name?: string;
  last_error_text?: string;
  last_error_timestamp?: string;
}

export default function KgConnections() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [uri, setUri] = useState('');

  const { data, isLoading, error } = useQuery<Neo4jConn[]>({
    queryKey: ['neo4j-conns', projectId],
    queryFn: async () => {
      const r = await fetch(`/api/projects/${projectId}/neo4j-connections`);
      if (!r.ok) throw new Error('Failed to list');
      return r.json();
    },
    enabled: !!projectId,
  });

  const add = useMutation<{ connection_id: string }, Error>({
    mutationFn: () => fetch(`/api/projects/${projectId}/neo4j-connections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ connection_name: name, connection_uri: uri }),
    }).then(r => r.json()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['neo4j-conns', projectId] }),
  });

  const del = useMutation<{ message: string }, Error, string>({
    mutationFn: (id) => fetch(`/api/projects/${projectId}/neo4j-connections/${id}`, {
      method: 'DELETE',
    }).then(r => r.json()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['neo4j-conns', projectId] }),
  });

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-2xl font-semibold">Neo4j Connections for Project {projectId}</h1>

      <Card className="p-4 space-y-3">
        <div className="text-lg font-medium">Add New</div>
        <div className="flex gap-2">
          <input className="w-full border rounded p-2" placeholder="Connection Name" value={name} onChange={e => setName(e.target.value)} />
          <input className="w-full border rounded p-2" placeholder="bolt://user:pass@host:port" value={uri} onChange={e => setUri(e.target.value)} />
          <Button onClick={() => add.mutate()} disabled={add.isPending || !name || !uri}>Add</Button>
        </div>
        {add.error && <div className="text-sm text-red-600">{add.error.message}</div>}
      </Card>

      <Card className="p-4 space-y-3">
        <div className="text-lg font-medium">Existing Connections</div>
        {isLoading && <div>Loading...</div>}
        {error && <div className="text-sm text-red-600">{error.message}</div>}
        <div className="space-y-2">
          {(data || []).map(c => (
            <Card key={c.connection_id} className="p-3 flex justify-between items-center">
              <div>
                <div className="font-medium">{c.connection_name || c.connection_id}</div>
                <div className="text-xs text-muted-foreground font-mono">{c.connection_id}</div>
                {c.last_error_text && (
                  <Badge variant="destructive" className="mt-1">{c.last_error_text}</Badge>
                )}
              </div>
              <Button size="sm" variant="outline" onClick={() => del.mutate(c.connection_id)}>Delete</Button>
            </Card>
          ))}
        </div>
      </Card>
    </div>
  );
}
