// Copyright Bunting Labs, Inc. 2025

import { ArrowLeft, Database, Loader2, RefreshCw, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useNavigate, useParams } from 'react-router-dom';
import MermaidComponent from '@/components/MermaidComponent';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Scrollspy } from '@/components/ui/scrollspy';

interface PostgresConnection {
  connection_id: string;
  friendly_name?: string;
  connection_name?: string;
}

interface NavigationItem {
  id: string;
  label: string;
  level: number;
}

const PostGISDocumentation = () => {
  const { connectionId } = useParams<{ connectionId: string }>();
  const navigate = useNavigate();
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);

  const [documentation, setDocumentation] = useState<string | null>(null);
  const [connectionName, setConnectionName] = useState<string>('');
  const [projectId, setProjectId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPreviewingEnrich, setIsPreviewingEnrich] = useState(false);
  const [isApplyingEnrich, setIsApplyingEnrich] = useState(false);
  const [navigationItems, setNavigationItems] = useState<NavigationItem[]>([]);

  // Knowledge docs state (simple MVP)
  const [docs, setDocs] = useState<Array<{ doc_id: string; filename: string; size: number; uploaded_at?: string }>>([]);
  const [docError, setDocError] = useState<string | null>(null);
  const [docUploading, setDocUploading] = useState(false);
  const [docFile, setDocFile] = useState<File | null>(null);

  const fetchDocumentation = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // First, we need to find which project this connection belongs to
      const projectsResponse = await fetch('/api/projects/');
      if (!projectsResponse.ok) {
        throw new Error('Failed to fetch projects');
      }
      const projectsData = await projectsResponse.json();

      // Search through all projects to find the one containing this connection
      let foundProjectId = '';
      let foundConnectionName = '';

      for (const project of projectsData.projects) {
        // Fetch project sources (PostGIS connections) for this project
        const sourcesResponse = await fetch(`/api/projects/${project.id}/sources`);
        if (sourcesResponse.ok) {
          const sources = (await sourcesResponse.json()) as PostgresConnection[];
          const connection = sources.find((c) => c.connection_id === connectionId);
          if (connection) {
            foundProjectId = project.id;
            foundConnectionName = connection.friendly_name || connection.connection_name || 'Database';
            break;
          }
        }
      }

      if (!foundProjectId) {
        throw new Error('Connection not found in any project');
      }

      setProjectId(foundProjectId);
      setConnectionName(foundConnectionName);

      // Now fetch the documentation
      const docResponse = await fetch(`/api/projects/${foundProjectId}/postgis-connections/${connectionId}/documentation`);
      if (!docResponse.ok) {
        throw new Error(`Failed to fetch documentation: ${docResponse.statusText}`);
      }
      const docData = await docResponse.json();
      setDocumentation(docData.documentation);
      if (docData.friendly_name) {
        setConnectionName(docData.friendly_name);
      }
    } catch (err) {
      console.error('Error fetching database documentation:', err);
      setError(err instanceof Error ? err.message : 'Failed to load documentation');
      setDocumentation(null);
    } finally {
      setLoading(false);
    }
  }, [connectionId]);

  useEffect(() => {
    if (connectionId) {
      fetchDocumentation();
    }
  }, [connectionId, fetchDocumentation]);

  // Extract headings from markdown content
  useEffect(() => {
    if (documentation) {
      const headingRegex = /^(#{1,6})\s+(.+)$/gm;
      const headings: NavigationItem[] = [];
      let match;

      while ((match = headingRegex.exec(documentation)) !== null) {
        const level = match[1].length;
        const text = match[2].trim();
        const id = text
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-+|-+$/g, '');

        headings.push({
          id,
          label: text,
          level,
        });
      }

      setNavigationItems(headings);
    }
  }, [documentation]);

  const handleRegenerate = async () => {
    if (!connectionId || !projectId) return;

    setIsRegenerating(true);
    setError(null);

    try {
      const response = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/regenerate-documentation`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to regenerate documentation: ${response.statusText}`);
      }

      // Wait a moment and then refetch the documentation
      setTimeout(() => {
        fetchDocumentation();
        setIsRegenerating(false);
      }, 2000);
    } catch (err) {
      console.error('Error regenerating database documentation:', err);
      setError(err instanceof Error ? err.message : 'Failed to regenerate documentation');
      setIsRegenerating(false);
    }
  };

  const handlePreviewEnrich = async () => {
    if (!connectionId || !projectId) return;
    setIsPreviewingEnrich(true);
    setError(null);
    try {
      const params = new URLSearchParams({ useKG: 'true', useDomainDocs: 'true', language: 'zh-CN' });
      const resp = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/enrich/preview?${params}`);
      if (!resp.ok) throw new Error(`Failed to preview enrichment: ${resp.statusText}`);
      const data = await resp.json();
      if (data.preview_md) setDocumentation(data.preview_md);
      if (data.friendly_name) setConnectionName(data.friendly_name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview enrichment');
    } finally {
      setIsPreviewingEnrich(false);
    }
  };

  const fetchDocs = useCallback(async () => {
    if (!projectId) return;
    try {
      const r = await fetch(`/api/projects/${projectId}/knowledge/docs`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setDocs(data.items || []);
    } catch (e) {
      setDocError(e instanceof Error ? e.message : 'Failed to load docs');
    }
  }, [projectId]);

  useEffect(() => { if (projectId) void fetchDocs(); }, [projectId, fetchDocs]);

  const handleUploadDoc = async () => {
    if (!projectId || !docFile) return;
    setDocUploading(true);
    setDocError(null);
    try {
      const fd = new FormData();
      fd.append('file', docFile);
      const r = await fetch(`/api/projects/${projectId}/knowledge/docs`, { method: 'POST', body: fd });
      if (!r.ok) throw new Error(await r.text());
      await fetchDocs();
      setDocFile(null);
    } catch (e) {
      setDocError(e instanceof Error ? e.message : 'Failed to upload');
    } finally {
      setDocUploading(false);
    }
  };

  const handleDeleteDoc = async (doc_id: string) => {
    if (!projectId) return;
    try {
      const r = await fetch(`/api/projects/${projectId}/knowledge/docs/${doc_id}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(await r.text());
      await fetchDocs();
    } catch (e) {
      setDocError(e instanceof Error ? e.message : 'Failed to delete');
    }
  };

  const handleApplyEnrich = async () => {
    if (!connectionId || !projectId) return;
    setIsApplyingEnrich(true);
    setError(null);
    try {
      const resp = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/enrich/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ useKG: true, useDomainDocs: true, language: 'zh-CN' }),
      });
      if (!resp.ok) throw new Error(`Failed to start enrichment: ${resp.statusText}`);
      const data = await resp.json();
      const jobId = data.job_id as string;

      // Poll status up to ~20s
      const start = Date.now();
      const timeoutMs = 20000;
      while (Date.now() - start < timeoutMs) {
        const s = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/enrich/status?job_id=${encodeURIComponent(jobId)}`);
        if (s.ok) {
          const st = await s.json();
          if (st.status === 'done') {
            await fetchDocumentation();
            setIsApplyingEnrich(false);
            return;
          } else if (st.status === 'error') {
            throw new Error(st.error || 'Enrichment failed');
          }
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
      // Timeout
      await fetchDocumentation();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply enrichment');
    } finally {
      setIsApplyingEnrich(false);
    }
  };

  const handleDelete = async () => {
    if (!connectionId || !projectId) return;

    setIsDeleting(true);
    setError(null);

    try {
      const response = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete connection: ${response.statusText}`);
      }

      // Navigate back to the project after successful deletion
      navigate(-1);
    } catch (err) {
      console.error('Error deleting PostGIS connection:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete connection');
      setIsDeleting(false);
    }
  };

  const fallbackContent = `
Documentation is being generated for this database. Please check back in a few moments.

If documentation generation fails, this indicates the database connection details or the database structure couldn't be analyzed automatically.
`;

  return (
    <div className="flex flex-col h-screen bg-background w-full">
      {/* Header */}
      <div className="border-b">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="flex items-center gap-2 hover:cursor-pointer">
              <ArrowLeft className="h-4 w-4" />
              Back to Map
            </Button>
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              <h1 className="text-xl font-semibold">{connectionName || 'Database Documentation'}</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={isRegenerating || loading || isDeleting || isPreviewingEnrich || isApplyingEnrich}
              className="flex items-center gap-2 hover:cursor-pointer"
            >
              {isRegenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {isRegenerating ? 'Regenerating...' : 'Regenerate'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviewEnrich}
              disabled={isPreviewingEnrich || loading || isDeleting || isRegenerating || isApplyingEnrich}
              className="flex items-center gap-2 hover:cursor-pointer"
            >
              {isPreviewingEnrich ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              {isPreviewingEnrich ? 'Previewing…' : 'Preview Enrich'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleApplyEnrich}
              disabled={isApplyingEnrich || loading || isDeleting || isRegenerating}
              className="flex items-center gap-2 hover:cursor-pointer"
            >
              {isApplyingEnrich ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              {isApplyingEnrich ? 'Applying…' : 'Apply Enrich'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting || loading || isRegenerating || isPreviewingEnrich || isApplyingEnrich}
              className="flex items-center gap-2 hover:cursor-pointer text-red-400 hover:text-red-300 border-red-500 hover:border-red-400"
            >
              {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {/* Knowledge Docs (simple) */}
        <div className="border-b p-4 flex items-center gap-3">
          <span className="text-sm font-medium">Knowledge Docs</span>
          <input
            type="file"
            onChange={(e) => setDocFile(e.target.files?.[0] || null)}
            className="text-sm"
          />
          <Button size="sm" onClick={handleUploadDoc} disabled={!docFile || docUploading}>
            {docUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload'}
          </Button>
          {docError && <span className="text-xs text-red-400">{docError}</span>}
          <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            <span>Docs:</span>
            {docs.length === 0 ? (
              <span>0</span>
            ) : (
              <div className="flex items-center gap-2">
                {docs.map(d => (
                  <div key={d.doc_id} className="flex items-center gap-2">
                    <span title={d.filename}>{d.filename.length > 18 ? d.filename.slice(0,18) + '…' : d.filename}</span>
                    <label className="underline cursor-pointer">
                      replace
                      <input type="file" className="hidden" onChange={async (e) => {
                        const f = e.target.files?.[0];
                        if (!f || !projectId) return;
                        try {
                          const fd = new FormData();
                          fd.append('file', f);
                          const r = await fetch(`/api/projects/${projectId}/knowledge/docs/${d.doc_id}`, { method: 'PUT', body: fd });
                          if (!r.ok) throw new Error(await r.text());
                          await fetchDocs();
                        } catch (e) {
                          setDocError(e instanceof Error ? e.message : 'Failed to replace');
                        }
                      }} />
                    </label>
                    <button className="text-red-400 hover:underline" onClick={() => handleDeleteDoc(d.doc_id)}>del</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        {/* Versions and Ops (simple) */}
        <div className="border-b p-4 flex items-center gap-3 text-sm">
          <VersionsAndOps projectId={projectId} connectionId={connectionId || ''} onUpdated={fetchDocumentation} />
        </div>
        <div className="flex h-full">
          {/* Main Content */}
          <div className="flex-1 overflow-y-auto">
            <ScrollArea className="h-full" ref={scrollAreaRef}>
              <div className="p-8">
                {loading && (
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="h-6 w-6 animate-spin mr-2" />
                    <span>Loading database documentation...</span>
                  </div>
                )}

                {error && (
                  <div className="p-4 border border-red-500 rounded-lg mb-4">
                    <p className="text-red-500">Error loading documentation: {error}</p>
                  </div>
                )}

                {!loading && !error && (
                  <div className="prose prose-sm prose-invert max-w-none">
                    <ReactMarkdown
                      components={{
                        code(props) {
                          const { className, children, ...rest } = props;
                          const match = /language-(\w+)/.exec(className || '');
                          const language = match ? match[1] : '';

                          if (language === 'mermaid') {
                            return (
                              <div className="bg-muted/20 mx-auto my-4">
                                <MermaidComponent chart={String(children)} />
                              </div>
                            );
                          }

                          return (
                            <code className={className} {...rest}>
                              {children}
                            </code>
                          );
                        },
                        h1(props) {
                          const { children, ...rest } = props;
                          const text = String(children);
                          const id = text
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '-')
                            .replace(/^-+|-+$/g, '');
                          return (
                            <h1 id={id} {...rest}>
                              {children}
                            </h1>
                          );
                        },
                        h2(props) {
                          const { children, ...rest } = props;
                          const text = String(children);
                          const id = text
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '-')
                            .replace(/^-+|-+$/g, '');
                          return (
                            <h2 id={id} {...rest}>
                              {children}
                            </h2>
                          );
                        },
                        h3(props) {
                          const { children, ...rest } = props;
                          const text = String(children);
                          const id = text
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '-')
                            .replace(/^-+|-+$/g, '');
                          return (
                            <h3 id={id} {...rest}>
                              {children}
                            </h3>
                          );
                        },
                        h4(props) {
                          const { children, ...rest } = props;
                          const text = String(children);
                          const id = text
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '-')
                            .replace(/^-+|-+$/g, '');
                          return (
                            <h4 id={id} {...rest}>
                              {children}
                            </h4>
                          );
                        },
                        h5(props) {
                          const { children, ...rest } = props;
                          const text = String(children);
                          const id = text
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '-')
                            .replace(/^-+|-+$/g, '');
                          return (
                            <h5 id={id} {...rest}>
                              {children}
                            </h5>
                          );
                        },
                        h6(props) {
                          const { children, ...rest } = props;
                          const text = String(children);
                          const id = text
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, '-')
                            .replace(/^-+|-+$/g, '');
                          return (
                            <h6 id={id} {...rest}>
                              {children}
                            </h6>
                          );
                        },
                      }}
                    >
                      {documentation || fallbackContent}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              <div className="border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950 p-4 mb-6 mx-8">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-blue-400 dark:text-blue-300" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-blue-700 dark:text-blue-200">
                      <strong>Have questions?</strong> Open any map that is connected to this PostGIS database, and Anway will be able to
                      answer questions based on this article.
                    </p>
                  </div>
                </div>
              </div>
            </ScrollArea>
          </div>

          {/* Navigation Sidebar - only show if we have navigation items */}
          {navigationItems.length > 0 && !loading && !error && (
            <div className="w-64 border-l bg-muted/20 p-4 overflow-y-auto">
              <h3 className="font-semibold mb-4 text-sm text-muted-foreground uppercase tracking-wide">Table of Contents</h3>
              <Scrollspy offset={50} targetRef={scrollAreaRef} className="flex flex-col gap-1">
                {navigationItems.map((item) => (
                  <Button
                    key={item.id}
                    variant="ghost"
                    size="sm"
                    data-scrollspy-anchor={item.id}
                    className={`
                      justify-start text-left h-auto py-1 px-2 whitespace-normal
                      data-[active=true]:bg-accent data-[active=true]:text-accent-foreground
                      hover:cursor-pointer
                      ${item.level === 1 ? 'font-medium' : ''}
                      ${item.level === 2 ? 'text-sm' : ''}
                      ${item.level === 3 ? 'ml-4 text-sm' : ''}
                      ${item.level >= 4 ? 'ml-8 text-xs' : ''}
                    `}
                  >
                    {item.label}
                  </Button>
                ))}
              </Scrollspy>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function VersionsAndOps({ projectId, connectionId, onUpdated }: { projectId: string; connectionId: string; onUpdated: () => void }) {
  const [versions, setVersions] = useState<Array<{ summary_id: string; friendly_name: string; generated_at?: string }>>([]);
  const [sel, setSel] = useState<string>('');
  const [opHeading, setOpHeading] = useState('');
  const [opReplace, setOpReplace] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!projectId || !connectionId) return;
    try {
      const r = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/versions`);
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setVersions(d.items || []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Failed to load versions');
    }
  }, [projectId, connectionId]);

  useEffect(() => { void load(); }, [load]);

  const rollback = async () => {
    if (!sel) return;
    const r = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/rollback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ summary_id: sel })
    });
    if (!r.ok) { setErr(await r.text()); return; }
    await load(); onUpdated();
  };

  const delByHeading = async () => {
    if (!opHeading) return;
    const r = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/ops/delete_by_heading`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ heading: opHeading })
    });
    if (!r.ok) { setErr(await r.text()); return; }
    await load(); onUpdated();
  };

  const replaceByHeading = async () => {
    if (!opHeading) return;
    const r = await fetch(`/api/projects/${projectId}/postgis-connections/${connectionId}/docs/ops/replace_by_heading`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ heading: opHeading, new_content: opReplace })
    });
    if (!r.ok) { setErr(await r.text()); return; }
    await load(); onUpdated();
  };

  return (
    <div className="w-full flex items-center gap-3">
      <span className="font-medium">Versions</span>
      <select className="border rounded px-2 py-1" value={sel} onChange={(e) => setSel(e.target.value)}>
        <option value="">Latest</option>
        {versions.map(v => (
          <option key={v.summary_id} value={v.summary_id}>{(v.generated_at || '').slice(0,19).replace('T',' ')} · {v.friendly_name}</option>
        ))}
      </select>
      <Button size="sm" variant="outline" onClick={rollback} disabled={!sel}>Rollback to</Button>
      <span className="ml-6 font-medium">Ops</span>
      <input className="border rounded px-2 py-1" placeholder="Heading (exact)" value={opHeading} onChange={(e)=>setOpHeading(e.target.value)} />
      <Button size="sm" onClick={delByHeading} disabled={!opHeading}>Delete section</Button>
      <input className="border rounded px-2 py-1 w-64" placeholder="Replace content" value={opReplace} onChange={(e)=>setOpReplace(e.target.value)} />
      <Button size="sm" onClick={replaceByHeading} disabled={!opHeading}>Replace</Button>
      {err && <span className="text-xs text-red-400">{err}</span>}
    </div>
  );
}

export default PostGISDocumentation;
