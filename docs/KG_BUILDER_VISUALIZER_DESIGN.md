# KG Builder & Visualizer MVP Design

## 0. Scope & Goals
- Build a minimal, production-safe pipeline to create and inspect a spatiotemporal knowledge graph from configuration files in `knowledge_config/`.
- Frontend: two pages — create (from configs) and visualize (search + subgraph expand).
- Backend: small set of read-only helpers and thin adapters, reusing existing `kg_minimal` + `graph_service` routes.
- Do NOT change existing database documentation flow; this doc only covers KG build/visualization.

---

## 1. Configuration Sources & Schemas (as-is)
- Ontology (hierarchy): `knowledge_config/电站时空知识图谱.json`
  - Fields: `id`, `name`, `englishName`, `description?`, `level?`, `subclass?[]`
- Table-to-ontology mappings (per domain): `knowledge_config/config/*.yml`
  - Root fields: `version`, `description`, `mappings[]`
  - Mapping item: `tableName`, `schema`, `entityType`, `ontologyNodeId`, `ontologyEnglishName`, `description`, `enabled`, `priority`, `fieldMappings{ ... }`
- Master aggregator: `knowledge_config/config/master-mapping.yml`
  - `configFiles[]` (relative paths to per-domain mapping yml), `globalConfig{ defaultOntologyNodeId, ... }`
- Spatial analysis mapping: `knowledge_config/spatial-analysis-mapping-v2.yml`
  - `mappings[]` with `analysisType`, `relationType`, thresholds, batch options (for later phases)
- Legacy aggregate: `knowledge_config/table-ontology-mapping.yml` (subset/union of per-domain files)

Implications for modeling:
- `ontologyNodeId` in mapping files aligns to nodes from the ontology JSON (after conversion).
- Common temporal fields: `start_time`, `end_time`; geometry fields vary; we keep geometry in PostGIS and only store derived centroid/bbox in Neo4j when needed.

---

## 2. Graph Modeling Best Practices
- Node ID scheme (global unique, deterministic):
  - Ontology: `ontology:{ontology_id}` (e.g., `ontology:001_003_003`)
  - Table: `table:{schema}.{table}` (e.g., `table:hazard_affected_body.power_station`)
  - Instance: `instance:{schema}.{table}:{pg_id}` (e.g., `instance:hazard_affected_body.power_station:42`)
- Labels:
  - `Ontology`, `Table`, `Instance`, plus existing types (`Concept`, `Dataset`, `Location`, `TimePeriod`, ... if needed)
- Relationships (UPPER_SNAKE_CASE):
  - Ontology hierarchy: `IS_A` (child -> parent)
  - Ontology→Table: `HAS_TABLE` (ontology -> table)
  - Instance→Table: `INSTANCE_OF` (instance -> table)
  - Spatial: `CONTAINS`, `ADJACENT_TO`, `RELATED_TO`, optionally `LOCATED_IN` (admin unit)
  - Temporal: `OCCURS_DURING` (instance -> time period)
  - Analysis-specific: normalized to allowed set; unsupported types mapped to `RELATED_TO` with `semantic_type` property
- Property whitelist (stored on nodes/relationships):
  - Node common: `id`, `name`, `english_name`, `node_kind`, `created_at`, `updated_at`
  - Table node: `table_name`, `schema`, `entity_type`, `description`
  - Instance node: `pg_id`, `table_name`, `schema`, optionally `centroid`, `bbox`, domain attrs (flat)
  - Relationship: `id`, `created_at`, optional `distance_km`, `direction`, `semantic_type`, domain attrs (flat)
- Geometry handling: keep source geometry in PostGIS; store only `bbox`/`centroid` in Neo4j if required by UX.
- Temporal handling: prefer instance properties `start_time`, `end_time` (ISO-8601 strings). TimePeriod node is optional later.
- Idempotency: all writes use MERGE semantics (in `kg_minimal._ensure_node` and `_ensure_relationship`).

---

## 3. Conversion Rules
### 3.1 Ontology JSON → KGConfig (adapter)
- Traverse `subclass` recursively.
- For each node create `OntologyNodeConfig(id,name,english_name?,parent_id?)`.
- Resulting `KGConfig(ontology_nodes=[...], tables=[])` passed to existing `apply_config_yaml` (converted to YAML string internally).

### 3.2 Mapping YAML (table→ontology)
- For each `mappings[]` item:
  - Ensure Table node: `Table` label with id `table:{schema}.{tableName}` and props `{table_name,schema,entity_type,description,node_kind:'Table'}`
  - Ensure `HAS_TABLE`: `ontology:{ontologyNodeId}` -> `table:{schema}.{tableName}`
- Instance ingestion is separate (Section 3.3) — we do not insert instances at mapping stage.

### 3.3 Instance Upsert (later step, inputs prepared per table)
- For records from `{schema}.{table}`: compute `instance_id = instance:{schema}.{table}:{pg_id}` where `pg_id` is the primary key or designated `id`.
- Minimal props: `{pg_id, table_name, schema, node_kind:'Instance', name?}` + whitelisted domain fields from `fieldMappings`.
- Ensure Instance node; ensure `INSTANCE_OF` to Table node. Optionally add spatial/temporal properties if columns present.

---

## 4. Backend API (MVP)
Re-use existing routes + add two minimal helpers.

### 4.1 Config listing/reading (new)
- GET `/api/kg/configs`
  - List files under `knowledge_config/` (whitelist: `.yml`,`.yaml`,`.json`)
  - Response: `{ items: [{ name, type, rel_path, size_bytes, mtime, meta? }] }`
- GET `/api/kg/configs/{name}`
  - Return `{ name, type, content }` for a file that was listed by the previous endpoint.
  - Security: forbid `..`, absolute paths; size limit 2MB.

### 4.2 Apply ontology JSON (adapter, new)
- POST `/api/kg/apply-ontology-json`
  - Body: `{ ontology_json: {...raw json...} }`
  - Action: convert to KGConfig and forward to existing `apply_config_yaml` (ontology-only). Return counters `{ ontology_created, relations_created }`.

### 4.3 Reuse existing routes (already implemented)
- POST `/api/kg/apply-config` (yaml) — creates Ontology nodes + HAS_TABLE based on YAML `KGConfig` tables.
- POST `/api/kg/upsert-instances` — upsert Instance nodes + `INSTANCE_OF` (payload: list of `{table_name, pg_id, name?, properties?}`)
- POST `/api/kg/relationships/spatial` — batch ingest spatial relations (maps `NEARBY→ADJACENT_TO`, `INTERSECTS→RELATED_TO` with `semantic_type`).
- GET `/api/graph/stats`, `/api/graph/nodes`, `/api/graph/nodes/{id}`, ...

### 4.4 Subgraph extraction (new)
- GET `/api/graph/subgraph?root_id=...&depth=2&labels=Ontology,Table,Instance&limit=500&offset=0`
- Returns `{ nodes: [...], relationships: [...], page: { limit, offset, has_more } }` with property whitelist.
- Cypher (no APOC), two-phase:
  1) Nodes
     ```
     MATCH (r {id:$root})
     WITH r
     MATCH p=(r)-[*1..$depth]-(n)
     WHERE $labels = [] OR any(l IN labels(n) WHERE l IN $labels)
     WITH collect(distinct n) + r AS ns
     UNWIND ns AS n
     RETURN n SKIP $offset LIMIT $limit
     ```
  2) Relationships among returned nodes (bounded by `rel_limit = limit*4`):
     ```
     WITH $node_ids AS ids
     MATCH (a)-[r]-(b)
     WHERE a.id IN ids AND b.id IN ids
     RETURN r LIMIT $rel_limit
     ```
- Defaults: `depth≤3`, `limit≤1000` hard cap; require at least one of `root_id` or a `labels+name` search flow.

---

## 5. Neo4j Indexes & Constraints (recommended)
- Unique per label (id):
  - `CREATE CONSTRAINT unique_ontology_id IF NOT EXISTS FOR (n:Ontology) REQUIRE n.id IS UNIQUE`
  - `CREATE CONSTRAINT unique_table_id IF NOT EXISTS FOR (n:Table) REQUIRE n.id IS UNIQUE`
  - `CREATE CONSTRAINT unique_instance_id IF NOT EXISTS FOR (n:Instance) REQUIRE n.id IS UNIQUE`
  - (Optional) `Dataset`, `Location`, `Concept`, `TimePeriod` similarly
- Helpful indexes:
  - `(n:Ontology).name`, `(n:Table).table_name`, `(n:Instance).pg_id`
  - Relationship type counts are derived; no index per-type in community edition.

---

## 6. Security & Limits
- Config read whitelist: only under `knowledge_config/`; deny `..`/absolute; size ≤ 2MB; UTF-8 only.
- Subgraph limits: default `limit=200`, max `1000`; `depth≤3`; property whitelist;
- Relationship type sanitation: only `[IS_A, HAS_TABLE, INSTANCE_OF, CONTAINS, ADJACENT_TO, RELATED_TO, LOCATED_IN, OCCURS_DURING]`; otherwise mapped to `RELATED_TO` with `semantic_type`.
- All write paths are idempotent via MERGE (already in `kg_minimal`).

---

## 7. Frontend (MVP)
### 7.1 Routes
- `/kg/new` (RequireAuth): choose config → view → apply
- `/kg/overview` (RequireAuth): stats + search + subgraph visualize

### 7.2 Components
- ConfigList (GET `/api/kg/configs`) — list + filter
- ConfigViewer (GET `/api/kg/configs/{name}`) — readonly preview
- ApplyActions — buttons:
  - If JSON → POST `/api/kg/apply-ontology-json`
  - If YAML KGConfig → POST `/api/kg/apply-config`
  - (Instances ingestion UI deferred; backend route exists for later)
- GraphView (Cytoscape.js):
  - Load stats; search via existing `/api/graph/nodes?labels=&name=`; pick a node as root
  - Fetch `/api/graph/subgraph` for depth-expand; color by label; click to inspect node properties
- State/Data: `@tanstack/react-query`; TS types mirror backend responses

---

## 8. Milestones & Acceptance
- M1 (2–4d): endpoints 4.1 & 4.4; pages `/kg/new`, `/kg/overview` with stats+subgraph; ontology apply JSON adapter
- M2 (later): instances ingestion UI, spatial-analysis-driven relations, dry-run preview, WS progress

Acceptance (M1):
- Can list & view configs; apply ontology JSON and KGConfig YAML without errors; graph stats increase as expected
- Can search nodes and expand a subgraph with bounded size; UI remains responsive under default caps

---

## 9. Open Points to Confirm
- Subgraph defaults: `depth=2`, `limit=200` (cap 1000) — acceptable?
- Property whitelist — add/remove fields?
- Placement in UI sidebar — add a “Knowledge Graph” entry?
- Instances ingestion: postpone UI, rely on backend batch (later job) — OK?
