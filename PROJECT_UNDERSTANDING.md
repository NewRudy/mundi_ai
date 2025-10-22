# Mundi.ai (Anway) Project Understanding

## Project Overview

**Name**: Mundi.ai / Anway  
**Description**: Open-source AI-native web GIS platform  
**License**: AGPLv3 (with GPLv3 for QGIS integration components)  
**Tech Stack**: FastAPI (Python) + React/TypeScript + Neo4j + PostgreSQL/PostGIS + MinIO + Redis

Anway is a self-hostable, AI-powered Geographic Information System supporting:
- Vector, raster, and point cloud data
- Spatial databases (PostGIS) connectivity
- LLM-driven geoprocessing and symbology editing
- Real-time collaboration via WebSockets
- Knowledge graph-based spatial-temporal reasoning

---

## Architecture Overview

### Multi-Service Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Docker Compose Stack                     │
├──────────────────────────────────────────────────────────────┤
│ 1. app (FastAPI)         - Main application server            │
│ 2. neo4j                 - Knowledge graph database            │
│ 3. postgresdb            - Main database with PostGIS          │
│ 4. redis                 - Caching & session management        │
│ 5. minio (S3)            - Object storage for files            │
│ 6. qgis-processing       - Separate geoprocessing service      │
└──────────────────────────────────────────────────────────────┘
```

### Core Services

1. **Main Application** (`app` container)
   - FastAPI backend serving REST API + SPA
   - Uvicorn ASGI server (port 8000)
   - Built-in frontend serving (Vite-built React SPA)
   - Python 3.11+, asyncio-based

2. **Neo4j Knowledge Graph** (`neo4j` container)
   - Version: 5.26.8 Community Edition
   - Ports: 7474 (Browser), 7687 (Bolt protocol)
   - Purpose: Spatial-temporal knowledge graph
   - APOC plugins enabled

3. **PostgreSQL + PostGIS** (`postgresdb` container)
   - Version: PostgreSQL 15
   - Primary database with PostGIS extension
   - Stores: Projects, Maps, Layers, Conversations, Messages

4. **Redis** (`redis` container)
   - Alpine version
   - Session management and caching

5. **MinIO** (`minio` container)
   - S3-compatible object storage
   - Stores uploaded GIS files (GeoTIFF, Shapefiles, etc.)

6. **QGIS Processing** (`qgis-processing` container)
   - Separate microservice for QGIS algorithms
   - FastAPI server on port 8817
   - Handles complex geoprocessing tasks

---

## Directory Structure

```
mundi.ai/
├── src/                          # Backend Python code
│   ├── database/                 # SQLAlchemy models & migrations
│   │   ├── models.py             # Core database models
│   │   ├── connection.py         # Database connection management
│   │   └── migrate.py            # Alembic migration runner
│   ├── dependencies/             # Dependency injection services
│   │   ├── neo4j_connection.py   # Neo4j connection pool
│   │   ├── db_pool.py            # PostgreSQL connection pool
│   │   ├── postgis.py            # PostGIS query provider
│   │   ├── chat_completions.py   # LLM chat interface
│   │   └── ...
│   ├── routes/                   # FastAPI route handlers
│   │   ├── postgres_routes.py    # Map/project/upload endpoints
│   │   ├── layer_router.py       # Layer CRUD operations
│   │   ├── message_routes.py     # AI agent orchestration
│   │   ├── conversation_routes.py# Chat/conversation management
│   │   ├── graph_routes.py       # Neo4j knowledge graph API
│   │   ├── kg_minimal_routes.py  # Simplified KG sync API
│   │   ├── websocket.py          # Real-time communication
│   │   └── ...
│   ├── services/                 # Business logic services
│   │   ├── graph_service.py      # Neo4j CRUD operations
│   │   └── kg_minimal.py         # Config-driven KG sync
│   ├── models/                   # Pydantic models
│   │   └── graph_models.py       # Neo4j node/relationship models
│   ├── geoprocessing/            # Geoprocessing logic
│   │   └── dispatch.py           # QGIS algorithm dispatch
│   ├── tools/                    # LLM tool implementations
│   │   ├── pyd.py                # Pydantic tool definitions
│   │   ├── openstreetmap.py      # OSM integration
│   │   ├── amap.py               # Amap integration (China)
│   │   ├── zoom.py               # Zoom to extent tool
│   │   └── ...
│   ├── symbology/                # MapLibre style generation
│   │   ├── llm.py                # LLM-based styling
│   │   └── verify.py             # Style validation
│   ├── scripts/                  # Utility scripts
│   │   └── init_graph_data.py    # Initialize Neo4j data
│   └── wsgi.py                   # FastAPI app entry point
├── frontendts/                   # Frontend TypeScript/React
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── MapLibreMap.tsx   # Core map component
│   │   │   ├── LayerList.tsx     # Layer management UI
│   │   │   ├── ProjectView.tsx   # Main workspace interface
│   │   │   └── ...
│   │   ├── contexts/             # React contexts
│   │   ├── hooks/                # Custom React hooks
│   │   ├── lib/
│   │   │   └── types.tsx         # TypeScript type definitions
│   │   ├── pages/                # Page components
│   │   ├── App.tsx               # Root component
│   │   └── main.tsx              # Entry point
│   └── package.json
├── alembic/                      # Database migrations
├── knowledge_config/             # Knowledge graph configs
│   ├── table-ontology-mapping.yml        # Table→Ontology mappings
│   ├── spatial-analysis-mapping-v2.yml   # Spatial analysis configs
│   └── config/                   # Domain-specific mappings
├── qgis-processing/              # QGIS processing service
├── docs/                         # Documentation
│   └── neo4j-integration.md      # Neo4j integration guide
├── docker-compose.yml            # Development stack
├── Dockerfile                    # Multi-stage build
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Python project config
├── README.md                     # Project README
└── WARP.md                       # Warp AI guidance
```

---

## Backend Architecture

### Core Models (PostgreSQL)

**MundiProject** (`user_mundiai_projects`)
- Container for maps with access control
- Fields: `id`, `owner_uuid`, `editor_uuids`, `viewer_uuids`, `title`, `maps[]`, `created_on`
- Relationships: `postgres_connections`

**MundiMap** (`user_mundiai_maps`)
- Individual map versions
- Fields: `id`, `project_id`, `parent_map_id`, `layers[]`, `title`, `description`, `basemap`
- Version control through `parent_map_id` (forms a DAG)
- Relationships: `chat_completion_messages`, `layer_styles`, `parent_map`, `child_maps`

**MapLayer** (`map_layers`)
- Spatial data references
- Types: `vector`, `raster`, `postgis`, `point_cloud`
- Fields: `layer_id`, `name`, `s3_key`, `type`, `postgis_query`, `bounds`, `geometry_type`
- Metadata stored in JSONB field

**ProjectPostgresConnection** (`project_postgres_connections`)
- External database connections
- Fields: `id`, `project_id`, `connection_uri`, `connection_name`
- Relationships: `summaries`, `layers`

**MundiChatCompletionMessage** (`chat_completion_messages`)
- Chat messages for AI interactions
- Fields: `id`, `map_id`, `sender_id`, `message_json`, `conversation_id`

**Conversation** (`conversations`)
- Chat conversation management
- Fields: `id`, `project_id`, `owner_uuid`, `title`, `created_at`

### Knowledge Graph (Neo4j)

**Architecture**
- Spatiotemporal knowledge graph for enhanced GIS reasoning
- Two integration approaches:
  1. **Full Graph Service** (`graph_routes.py`, `graph_service.py`)
  2. **Minimal Config-Driven** (`kg_minimal_routes.py`, `kg_minimal.py`)

**Node Types** (from `graph_models.py`)
- `Location`: Geographic places with coordinates/boundaries
- `AdministrativeUnit`: Countries, states, cities
- `Feature`: Individual GIS features/objects
- `Dataset`: Metadata about GIS datasets
- `Attribute`: Feature attributes/fields
- `TimePeriod`: Temporal ranges
- `Concept`: GIS terminology and concepts
- `UserQuery`: Query understanding and context

**Relationship Types**
- `CONTAINS`: Spatial containment
- `ADJACENT_TO`: Spatial adjacency
- `PART_OF`: Hierarchical relationships
- `HAS_ATTRIBUTE`: Feature-attribute links
- `OCCURS_DURING`: Temporal relationships
- `RELATED_TO`: Conceptual associations
- `QUERIES`, `MENTIONS`: Query relationships

**Config-Driven KG Sync** (Minimal Approach)
- YAML-based configuration (`knowledge_config/`)
- Node ID conventions:
  - Ontology: `ontology:{ontology_id}`
  - Table: `table:{table_name}`
  - Instance: `instance:{table_name}:{pg_id}`
- Operations:
  - `apply_config_yaml`: Build ontology & table topology
  - `upsert_instances`: Create/update Instance nodes
  - `ingest_spatial_relationships`: Store spatial analysis results
  - `ingest_llm_triples`: Generic LLM-produced triples

**Configuration Files**
- `table-ontology-mapping.yml`: PostgreSQL table → Ontology mappings
- `spatial-analysis-mapping-v2.yml`: Batch spatial analysis configs
- Domain-specific mappings in `config/` directory

### API Routes

**Core Routes**
- `/api/maps/*` - Map/project management, rendering, uploads
- `/api/layers/*` - Layer CRUD operations
- `/api/messages/*` - AI agent message handling
- `/api/conversations/*` - Conversation management
- `/api/graph/*` - Knowledge graph operations (full API)
- `/api/kg/*` - Minimal KG sync API
- `/ws/maps/{map_id}` - WebSocket for real-time updates

**Authentication**
- Handled via `@mundi/ee` package (enterprise edition)
- Session verification: `verify_session_required`
- User context: `UserContext` (uuid, email)

### Data Flow Patterns

**1. File Upload → Layer Creation**
```
User uploads file → S3 storage (MinIO)
→ Layer record creation (MapLayer)
→ Format conversion (COG for rasters, PMTiles for vectors)
→ Bounds/metadata extraction
→ Layer added to map
```

**2. Rendering Pipeline**
```
Raster: COG → XYZ tiles via rio-tiler
Vector: GeoJSON/Shapefile → PMTiles generation via tippecanoe
PostGIS: Direct MVT tile generation
Point Cloud: LAZ format with LAStools
```

**3. AI Workflow**
```
User message → Tool selection (LLM)
→ Tool execution (PostGIS/DuckDB/QGIS)
→ Result processing
→ New layer creation + styling
→ Map version fork (if needed)
→ WebSocket notification
```

**4. Knowledge Graph Sync**
```
PostgreSQL data → Config-driven mapping
→ Ontology nodes created (if not exist)
→ Instance nodes upserted
→ Spatial relationships ingested
→ Neo4j graph updated
```

### Security & Constraints

**PostGIS Queries**
- Validated with `EXPLAIN (FORMAT JSON)` to prevent writes
- Limited to < 1000 results
- Read-only access enforced

**LLM Tool Calls**
- Restricted Pydantic parameter templates
- Tool registry: `PydanticToolRegistry`
- Tool definitions in `src/tools/pyd.py`

**MapLibre Styles**
- Validated through `src/symbology/verify.py`
- JSON schema compliance checked

---

## Frontend Architecture

### Tech Stack
- **React 18** with TypeScript
- **MapLibre GL JS** for web mapping
- **Deck.gl** for advanced visualizations
- **Radix UI** for component primitives
- **TanStack Query** for data fetching
- **React Router** for routing
- **Vite** for build tooling

### Key Components

**MapLibreMap.tsx**
- Core mapping component
- Integrates MapLibre GL + Deck.gl
- Handles layer rendering, interactions
- Protocol handlers: `pmtiles://`, `cog://`

**ProjectView.tsx**
- Main workspace interface
- Map canvas, layer list, chat panel
- Real-time collaboration via WebSocket
- Message streaming with LLM responses

**LayerList.tsx**
- Layer management UI
- Drag-and-drop reordering
- Visibility toggles, styling controls

**App.tsx**
- Root component with routing
- Authentication provider (`@mundi/ee`)
- Query client setup

### State Management
- **React Context**: `ProjectsContext`
- **TanStack Query**: Server state caching
- **WebSocket**: Real-time ephemeral updates
- **Local State**: Component-level state with hooks

### API Integration
- Type definitions in `frontendts/src/lib/types.tsx`
- HTTP requests via `fetch` / `httpx`
- WebSocket for real-time updates
- Message streaming for LLM responses

---

## Development Workflow

### Local Development

**Start Full Stack** (Docker Compose):
```bash
docker compose up
```

**Backend Only** (requires services running):
```bash
uv sync --dev
uv run uvicorn src.wsgi:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend Only**:
```bash
cd frontendts
npm ci --legacy-peer-deps
npm run dev
```

**Run Tests**:
```bash
# Backend tests
uv run pytest -xvs
uv run pytest src/routes/test_*.py

# Specific markers
uv run pytest -m postgres  # PostgreSQL tests
uv run pytest -m s3        # S3/MinIO tests

# In Docker
docker compose run app pytest -xvs -n auto
```

**Linting & Type Checking**:
```bash
# Python
ruff check .
ruff format .
uv run basedpyright

# Frontend
cd frontendts
npm run lint
```

**Database Migrations**:
```bash
uv run alembic upgrade head
```

**Initialize Neo4j Data**:
```bash
python src/scripts/init_graph_data.py
```

### Environment Variables

**Core Variables** (from `docker-compose.yml`):
```bash
# Authentication
MUNDI_AUTH_MODE=edit  # "edit" or "view_only"

# S3/MinIO
S3_ACCESS_KEY_ID=s3user
S3_SECRET_ACCESS_KEY=backup123
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=test-bucket

# PostgreSQL
POSTGRES_HOST=postgresdb
POSTGRES_PORT=5432
POSTGRES_DB=mundidb
POSTGRES_USER=mundiuser
POSTGRES_PASSWORD=gdalpassword

# Neo4j
NEO4J_HOST=neo4j
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=onlywtx.

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# LLM (examples in docker-compose.yml)
OPENAI_API_KEY=$OPENAI_API_KEY
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=ZhipuAI/GLM-4.6

# Services
QGIS_PROCESSING_URL=http://qgis-processing:8817
WEBSITE_DOMAIN=http://localhost:8000
```

### Code Organization

**Python Code Style**
- Async/await for all I/O operations
- Explicit type annotations for public APIs
- Pydantic models for request/response validation
- OpenTelemetry tracing for observability
- HTTPException with structured error details

**Frontend Code Style**
- Functional components with hooks
- TypeScript for all new code
- React.memo/useMemo for performance optimization
- MapLibre integration through centralized wrapper
- API types in `lib/types.tsx`

**File Placement Conventions**
- New routes: `src/routes/`
- Shared utilities: `src/dependencies/`
- Database models: `src/database/models.py`
- Frontend components: `frontendts/src/components/`
- Tests: Colocated with source files (`test_*.py`)

---

## Testing Strategy

**Backend**
- pytest with asyncio support
- Markers for service dependencies (`-m postgres`, `-m s3`)
- Colocated tests (`test_*.py` alongside source)
- Integration tests with full Docker stack

**Frontend**
- Biome for linting and formatting
- TypeScript type checking

**CI/CD**
- GitHub Actions workflows
- Depot for container builds

---

## Key Dependencies

### Geospatial Stack
- **GDAL 3.11.3+**: Raster/vector processing
- **PostGIS**: Spatial database operations
- **QGIS 3.x**: Advanced geoprocessing (separate container)
- **Tippecanoe**: Vector tile generation
- **rio-tiler**: Cloud-Optimized GeoTIFF serving
- **LAStools**: Point cloud processing

### Frontend Stack
- **React 18**: UI framework
- **MapLibre GL JS**: Web mapping
- **Deck.gl**: Advanced visualizations
- **Radix UI**: Component primitives
- **TanStack Query**: Data fetching

### Backend Stack
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM (async)
- **Alembic**: Database migrations
- **OpenAI client**: LLM integration
- **Neo4j Python driver**: Graph database
- **Boto3/aioboto3**: S3 operations

---

## Recent Development (Git History)

**Latest Commits**:
1. `7ac66ad` - Delete amap_api_key
2. `5415abd` - Add Python version of knowledge_driver module
3. `153ae1e` - Add amap module
4. `3cb53c1` - Add summarize module
5. `8cf2266` - Add disaster reporting modules

**Key Recent Changes**:
- Knowledge graph integration (Neo4j)
- Config-driven KG sync (`kg_minimal.py`)
- Amap integration for China
- Disaster reporting and situation summarization tools
- PostgreSQL SSL mode handling
- LLM provider flexibility (OpenAI, Gemini, SiliconFlow, ModelScope)

---

## Domain Knowledge

**GIS Concepts**
- **Vector Data**: Points, lines, polygons (GeoJSON, Shapefiles)
- **Raster Data**: Grid-based imagery (GeoTIFF, COG)
- **Point Cloud**: LiDAR data (LAZ format)
- **CRS/SRID**: Coordinate reference systems (EPSG codes)
- **Bounds/BBox**: Geographic extent [minX, minY, maxX, maxY]
- **MVT**: Mapbox Vector Tiles (efficient vector serving)
- **PMTiles**: Serverless vector tile format
- **COG**: Cloud-Optimized GeoTIFF (efficient raster serving)

**Knowledge Graph Concepts**
- **Ontology**: Hierarchical concept structure
- **Instance**: Concrete entity (e.g., specific power station)
- **Spatial Relationships**: CONTAINS, ADJACENT_TO, INTERSECTS
- **Temporal Relationships**: OCCURS_DURING, BEFORE, AFTER

---

## Chinese Domain Context

Based on the configuration files in `knowledge_config/`:

**Emergency Management Domain**
- Focus on disaster response and infrastructure monitoring
- Power stations (`power_station`)
- Hydro stations (`hydro_station`)
- Airports, railway stations, roads, highways
- Buildings and public facilities
- Geological hazards

**Ontology Structure**
- Infrastructure (基础设施) - `001_003_003`
- Public Service Facilities (公共服务设施)
- Emergency Management (应急管理)
- Geological Disasters (地质灾害)
- Resource Environment (资源环境)

**Spatial Analysis Configurations**
- Dam break flood analysis (溃坝淹没分析)
- Building-facility nearest neighbor analysis
- Buffer intersection analysis
- Batch processing with adaptive sizing

---

## Notable Features

**AI Integration**
- LLM-driven geoprocessing tool selection
- Natural language to spatial query
- Automatic layer styling generation
- Conversation-based workflows

**Collaboration**
- Real-time presence tracking via WebSocket
- Ephemeral actions for live updates
- Map version control (DAG of map states)
- Multi-user access control

**Knowledge Graph**
- Spatial-temporal reasoning
- Entity relationship tracking
- Query context understanding
- Config-driven data synchronization

**Flexibility**
- Self-hostable with Docker
- Local LLM support
- Multiple LLM provider options
- Extensible geoprocessing pipeline

---

## Next Steps for Exploration

1. **Test Suite**: Explore test files to understand validation strategies
2. **Geoprocessing Tools**: Dive into `src/geoprocessing/` for algorithm implementations
3. **Message Loop**: Trace message handling flow in `message_routes.py`
4. **WebSocket Protocol**: Understand real-time communication in `websocket.py`
5. **Symbology Generation**: Study `src/symbology/llm.py` for styling logic
6. **DuckDB Integration**: Explore `src/duckdb.py` for analytical queries
7. **Knowledge Graph Sync**: Implement or enhance KG sync logic in `kg_minimal.py`

---

## Contact & Resources

- **Discord**: https://discord.gg/V63VbgH8dT
- **GitHub**: https://github.com/BuntingLabs/mundi.ai
- **License**: AGPLv3
- **Maintainer**: Bunting Labs, Inc.

---

*This document was auto-generated by exploring the codebase. Last updated: 2025-10-22*
