# Postgres Documentation Enrichment (Incremental) — Design

## 0. Principles
- Do NOT change current documentation generator (`DefaultDatabaseDocumenter`).
- Enrichment runs are optional, incremental, and write back as new versions (append-only) to existing storage (`project_postgres_summary`) or a sibling table.
- All steps idempotent and auditable; sources (KG, domain docs, spatial configs) are disclosed in metadata.

---

## 1. Target Outcome
- For a Postgres connection, produce a richer markdown summary that blends:
  1) Current schema overview (existing)
  2) Knowledge Graph context (ontology/table/instance coverage, relations)
  3) Domain documents citations (uploaded PDFs/markdown/snippets)
  4) (Optional) Spatial patterns per `spatial-analysis-mapping-v2.yml`
- Keep the output concise, sectioned, and with inline source citations.

---

## 2. Pipeline (staged, pluggable)
Stages executed in order; any stage can be disabled.

1) SchemaSummarizer (existing)
- Input: tables/columns gathered from Postgres
- Output: base markdown (already implemented)

2) KGEnricher (new)
- Input: Neo4j graph; ontology/table mapping from YAML; instance counts (by table)
- Queries (via existing services):
  - Counts by label: `/api/graph/stats`
  - For each mapped table: `MATCH (t:Table {id:$id})<-[:INSTANCE_OF]-(i:Instance) RETURN count(i)`
  - Optional: sample ontology path: `MATCH (t:Table {id:$id})<-[:HAS_TABLE]-(o:Ontology) RETURN o.id,o.name`
- Output sections:
  - “Ontology & Table Mapping” (list mapped tables, their ontology nodes)
  - “Instance Coverage” (counts per table; top-5 examples by name/pg_id)

3) DomainDocEnricher (new, lightweight MVP)
- Input: Uploaded domain docs (plain text/markdown) stored in S3/MinIO; a list of top relevant snippets (no vector DB initially)
- Retrieval MVP:
  - Simple keyword filter from table/ontology names; top-N longest/most relevant paragraphs
  - Include exact quoted snippets as citations
- Prompted synthesis: produce human-readable paragraphs that reference citations
- Output: “Domain Knowledge & Best Practices” section with numbered citations

4) SpatialPatterns (optional)
- Input: Config `spatial-analysis-mapping-v2.yml` and any existing spatial relations in KG
- Output: “Spatial Patterns” section that states configured analyses and presence/absence of matching relations

Metadata
- For every run store: `sources_used`, `kg_snapshot_time`, `doc_ids`, `prompt_version`, `pipeline_flags`

---

## 3. Data Storage (planned)
Keep existing table; add metadata and versioning policy.

Option A (minimal)
- Reuse `project_postgres_summary` with multiple rows per connection (already allowed via `generated_at`); use latest in UI
- Add metadata JSON to `summary_md` tail (YAML front-matter) or add a dedicated column if migration allowed later

Option B (later)
- New table `project_postgres_summary_versions` with foreign key to summary

Knowledge Docs (future when enabling uploads)
- `project_knowledge_documents(id, project_id, filename, mime, size, storage_key, uploaded_at)`
- (Later) `project_knowledge_doc_chunks(doc_id, chunk_idx, text, embedding?)`

---

## 4. API (planned, not implemented in MVP)
1) Upload/list domain docs (per project)
- POST `/api/projects/{projectId}/knowledge/docs` (multipart) → stores to S3/MinIO; returns `{doc_id}`
- GET `/api/projects/{projectId}/knowledge/docs` → lists docs
- DELETE `/api/projects/{projectId}/knowledge/docs/{docId}`

2) Trigger enrichment for a connection
- POST `/api/postgres/{connectionId}/enrich-docs`
  - Body:
    ```
    {
      "useKG": true,
      "useDomainDocs": true,
      "useSpatial": false,
      "maxTokens": 2400,
      "sections": ["mapping","coverage","domain","spatial"],
      "docIds": ["..."],
      "language": "zh-CN"
    }
    ```
  - Behavior: run stages, write a new summary version row; returns `{summary_id, generated_at}`
- GET `/api/postgres/{connectionId}/doc-versions` → list previous versions
- GET `/api/postgres/{connectionId}/jobs/{jobId}` → async status (if backgrounded)

Security & Limits
- Max doc size; mime whitelist; per-request token budget; require map ownership

---

## 5. Prompting & Citations (guidelines)
- Use deterministic, short prompts; temperature low
- Enforce structure: headings + bullet points; no hallucinated tables/columns
- Every domain claim must include a citation `[DocName §paraX]`; reject generation if no snippet available
- Language switch via `language` param (default zh-CN)

---

## 6. Frontend Changes (MVP for later rollout)
- Page: `/postgis/:connectionId`
  - Add “富化文档” panel with toggles (useKG/useDomainDocs/useSpatial)
  - Show preview diff (optional later); “生成”按钮 → 触发后台任务
  - Version dropdown to switch between base and enriched versions
  - Per-paragraph “继续丰富” → 发送上下文（相关KG子图 + top-K文档片段）做增量生成（后续）

---

## 7. Rollout Plan
- Phase A (spec only): keep current generator; implement nothing; finalize contract
- Phase B (MVP): implement KGEnricher + DomainDocEnricher without uploads (use existing docs in repo or pasted text); append-only versions
- Phase C: enable doc uploads + simple keyword retrieval; later add vector retrieval

---

## 8. Acceptance Criteria (when implemented)
- Running enrichment produces a new version without affecting the base version
- Output sections include mapping & coverage (if KG present), domain text with citations, and optional spatial notes
- UI allows selecting version and viewing metadata (timestamp, sources)

---

## 9. Open Points to Confirm
- Versioning location: reuse `project_postgres_summary` (minimal) vs new versions table
- Citation format & doc storage path (MinIO bucket naming)
- Retrieval: keyword filter first or introduce embeddings early?
- Language defaults and style (中文为主，是否混排英文名)
