import { useQuery, useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface ConfigItem {
  name: string;
  type: 'yaml' | 'json' | string;
  rel_path: string;
  size_bytes: number;
  mtime: string;
  meta?: { version?: string; description?: string };
}

interface ConfigListResponse { items: ConfigItem[] }

export default function KgNew() {
  const [selected, setSelected] = useState<ConfigItem | null>(null);
  const [content, setContent] = useState<string>('');

  const listQuery = useQuery<ConfigListResponse>({
    queryKey: ['kg-configs'],
    queryFn: async () => {
      const r = await fetch('/api/kg/configs');
      if (!r.ok) throw new Error('Failed to list configs');
      return r.json();
    },
  });

  const readConfig = async (relPath: string) => {
    const r = await fetch(`/api/kg/configs/${encodeURI(relPath)}`);
    if (!r.ok) throw new Error('Failed to read config');
    const data = await r.json();
    setContent(data.content || '');
  };

  const applyYaml = useMutation({
    mutationFn: async () => {
      if (!content) throw new Error('No content');
      const r = await fetch('/api/kg/apply-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config_yaml: content }),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
  });

  const applyJson = useMutation({
    mutationFn: async () => {
      if (!content) throw new Error('No content');
      let parsed: unknown;
      try { parsed = JSON.parse(content); } catch { throw new Error('Invalid JSON'); }
      const r = await fetch('/api/kg/apply-ontology-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ontology_json: parsed }),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
  });

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Build Knowledge Graph from Config</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-3">
          <div className="text-sm font-medium mb-2">Configs</div>
          {listQuery.isLoading && <div>Loading...</div>}
          {listQuery.data && (
            <ul className="space-y-2 max-h-[60vh] overflow-auto">
              {listQuery.data.items.map((it) => (
                <li key={it.rel_path}>
                  <button
                    className={`w-full text-left px-2 py-1 rounded ${selected?.rel_path === it.rel_path ? 'bg-accent' : 'hover:bg-muted'}`}
                    onClick={() => { setSelected(it); setContent(''); void readConfig(it.rel_path); }}
                  >
                    <div className="text-sm">{it.rel_path}</div>
                    <div className="text-xs text-muted-foreground">{it.type}{it.meta?.version ? ` · v${it.meta.version}` : ''}</div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card className="p-3 md:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium">Preview</div>
            <div className="space-x-2">
              {selected?.type === 'json' ? (
                <Button size="sm" disabled={applyJson.isPending || !content} onClick={() => applyJson.mutate()}>Apply Ontology JSON</Button>
              ) : (
                <Button size="sm" disabled={applyYaml.isPending || !content} onClick={() => applyYaml.mutate()}>Apply Config YAML</Button>
              )}
            </div>
          </div>
          <textarea className="w-full h-[60vh] text-xs font-mono border rounded p-2" readOnly value={content} />
          {(applyYaml.data || applyJson.data) && (
            <pre className="mt-2 text-xs bg-muted p-2 rounded">{JSON.stringify(applyYaml.data || applyJson.data, null, 2)}</pre>
          )}
        </Card>
      </div>
    </div>
  );
}
