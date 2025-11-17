# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mundi.ai** (also known as **Anway**) is an open-source, AI-native web GIS platform that revolutionizes spatial data analysis through large language model integration. The platform enables users to perform complex geoprocessing operations, visualize spatial data, and build knowledge graphs using natural language interactions.

**Key Capabilities:**
- Multi-format spatial data support (vector, raster, point cloud)
- PostGIS database integration with AI-powered querying
- LLM-driven geoprocessing and symbology editing
- Real-time collaboration via WebSockets
- Knowledge graph-based spatial-temporal reasoning
- Self-hostable with local LLM support

**License:** AGPLv3 (with GPLv3 for QGIS integration components)

## System Architecture

### Multi-Service Docker Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├──────────────────────────────────────────────────────────────┤
│ 1. app (FastAPI)         │ Main application server          │
│ 2. neo4j                 │ Knowledge graph database         │
│ 3. postgresdb            │ Main database + PostGIS          │
│ 4. redis                 │ Caching & session management     │
│ 5. minio (S3)            │ Object storage for files         │
│ 6. qgis-processing       │ Separate geoprocessing service   │
└──────────────────────────────────────────────────────────────┘
```

### Core Technology Stack

**Backend:**
- **Framework:** FastAPI (Python 3.11+) with asyncio
- **Database:** PostgreSQL 15 + PostGIS extension
- **Knowledge Graph:** Neo4j 5.26.8 Community Edition
- **Cache:** Redis for session management
- **Storage:** MinIO (S3-compatible object storage)
- **Geoprocessing:** Separate QGIS processing service

**Frontend:**
- **Framework:** React 18 + TypeScript + Vite
- **Mapping:** MapLibre GL JS with custom protocols
- **State Management:** React Context + TanStack Query
- **UI Components:** Radix UI + Tailwind CSS
- **Build Tool:** Vite with TypeScript

## Backend Architecture (FastAPI)

### Entry Point & Application Structure

**Main Entry:** `src/wsgi.py`
- FastAPI application with lifespan management
- Automatic database migrations on startup
- Neo4j knowledge graph initialization
- Static file serving for built frontend
- SPA fallback routing

### Core Route Modules

**Primary API Routes:**
- **`postgres_routes.py`** - Map/project management, data uploads, PostGIS operations
- **`layer_router.py`** - Layer CRUD operations, styling, visualization
- **`message_routes.py`** - AI chat interface, tool orchestration, geoprocessing
- **`conversation_routes.py`** - Session management, conversation history
- **`graph_routes.py`** - Knowledge graph operations, ontology management
- **`kg_minimal_routes.py`** - Minimal knowledge graph API endpoints

**Specialized Routes:**
- **`websocket.py`** - Real-time communication, collaborative editing
- **`attribute_table.py`** - Data table operations, attribute queries

### Data Models & Architecture

**Database Models:** `src/database/models.py`
- SQLAlchemy declarative models with PostgreSQL-specific features
- Project-based multi-tenancy with UUID-based ownership
- Versioned maps with diff tracking
- Connection management for external databases

**Knowledge Graph Models:** `src/models/graph_models.py`
- Pydantic models for Neo4j node/relationship types
- Spatial-temporal node types (Location, AdministrativeUnit, Feature, etc.)
- Relationship types for spatial and temporal connections

### Key Services

**Graph Service:** `src/services/graph_service.py`
- Neo4j database operations with async session management
- Node/relationship CRUD operations
- Property conversion for Neo4j compatibility
- Connection-specific graph instances

**Database Operations:**
- Asynchronous PostgreSQL connections via asyncpg
- PostGIS query validation and safety checks
- Connection pooling for external databases
- Read-only query enforcement with EXPLAIN validation

### Security & Validation

- **SQL Safety:** All PostGIS queries validated with EXPLAIN, read-only enforcement
- **LLM Tool Constraints:** Pydantic models for tool parameters, no free-text SQL execution
- **Style Validation:** MapLibre style verification via `src/symbology/verify.py`
- **File Upload Security:** Size limits, format validation, virus scanning

## Frontend Architecture (React/TypeScript)

### Application Structure

**Entry Points:**
- **`main.tsx`** - Application initialization with authentication
- **`App.tsx`** - Main router and global providers

**Core Components:**
- **`MapLibreMap.tsx`** - Primary mapping component with protocol handlers
- **`LayerList.tsx`** - Layer management and styling interface
- **`ProjectView.tsx`** - Main project workspace
- **`GraphVisualization.tsx`** - Knowledge graph visualization with canvas rendering

### State Management

**Global State:**
- **`ProjectsContext.tsx`** - Project and map state management
- **TanStack Query** - Server state caching and synchronization
- **React Router** - Client-side routing with authentication guards

**Map Protocols:**
- Custom protocols for PMTiles, COG (Cloud Optimized GeoTIFF)
- Integration with MapLibre GL JS for advanced visualization

### UI Architecture

**Component Library:** Radix UI primitives with custom styling
**Styling:** Tailwind CSS with design system consistency
**Icons:** Lucide React icon library
**Forms:** React Hook Form with Zod validation

## Knowledge Graph System

### Neo4j Integration

**Node Types:**
- **Location** - Geographic coordinates and bounding boxes
- **AdministrativeUnit** - Hierarchical administrative boundaries
- **Feature** - GIS layers and spatial features
- **Dataset** - Data source references
- **Concept** - Abstract semantic concepts
- **TimePeriod** - Temporal annotations

**Relationship Types:**
- **CONTAINS** - Spatial containment
- **ADJACENT_TO** - Spatial adjacency
- **PART_OF** - Hierarchical relationships
- **HAS_ATTRIBUTE** - Attribute connections
- **OCCURS_DURING** - Temporal relationships

### Knowledge Graph API

**Configuration Management:**
- Ontology JSON/YAML configuration application
- Schema initialization and management
- Instance ingestion from PostgreSQL

**Query & Visualization:**
- Graph statistics and node search
- Subgraph extraction and visualization
- Spatial relationship analysis

## Critical Development Guidelines

### Security Requirements
1. **NEVER execute user-provided SQL directly** - Always validate through `sql_validator.py`
2. **All database queries must be parameterized** - No string concatenation
3. **Enforce read-only mode** for user queries when possible
4. **Validate file uploads** - Check format, size, and scan for threats
5. **Use Pydantic models** for all LLM tool parameters

### Backend Development Patterns
1. **Always use async/await** - FastAPI is fully async
2. **Connection pooling** for external databases
3. **Proper error handling** with structured responses
4. **Type annotations** required for all Python code
5. **Database migrations** via Alembic for schema changes

### Frontend Development Patterns
1. **TypeScript strict mode** - All components must be properly typed
2. **Custom MapLibre protocols** for PMTiles, COG, and vector tiles
3. **TanStack Query** for server state management
4. **React Context** for local UI state only
5. **Accessibility compliance** with ARIA standards

### Common Pitfalls to Avoid
1. **Don't bypass SQL validation** - Even for "simple" queries
2. **Don't use synchronous database calls** - Use asyncpg
3. **Don't store large files in PostgreSQL** - Use MinIO for file storage
4. **Don't skip migration testing** - Test on both empty and existing databases
5. **Don't ignore WebSocket state** - Handle connection failures gracefully

## Development Guidelines

### Backend Development

**Code Standards:**
- Python 3.11+ with comprehensive type annotations
- Asynchronous operations using asyncio and asyncpg
- Pydantic models for request/response validation
- Comprehensive error handling with structured responses

**Database Operations:**
- Always use connection pooling for external databases
- Validate queries with EXPLAIN before execution
- Enforce read-only operations on user queries
- Implement proper LIMIT constraints

**Security Practices:**
- Never execute free-text SQL from user input
- Validate all file uploads for type and size
- Use parameterized queries for all database operations
- Implement proper authentication and authorization

### Frontend Development

**Component Standards:**
- Function components with TypeScript interfaces
- Consistent error boundary implementation
- Performance optimization with React.memo and useMemo
- Accessibility compliance with ARIA standards

**State Management:**
- Use TanStack Query for server state
- Implement proper loading and error states
- Cache optimization with stale-while-revalidate
- Optimistic updates for better UX

### Testing Strategy

**Backend Testing:**
- pytest with async support
- Database transaction rollback for test isolation
- Mock external services (S3, Neo4j, QGIS)
- Integration tests for API endpoints

**Frontend Testing:**
- Component testing with React Testing Library
- E2E testing for critical user flows
- Performance testing for large datasets
- Accessibility testing compliance

## High-Level Architecture Patterns

### Security-First Design
1. **SQL Injection Prevention:** All user queries validated through `src/sql_validator.py` using EXPLAIN analysis
2. **Read-Only Enforcement:** User database queries can be restricted to read-only operations
3. **LLM Tool Sandboxing:** All AI tools use Pydantic validation with no free-text SQL execution
4. **File Upload Security:** Comprehensive validation, scanning, and size limits

### Multi-Service Architecture
```
Frontend (React/TypeScript) → FastAPI Backend → PostgreSQL/PostGIS
                                     ↓
                              Neo4j Knowledge Graph
                                     ↓
                            Redis Cache & MinIO Storage
                                     ↓
                            QGIS Processing Service
```

### AI Integration Architecture
1. **Tool Registry:** Dynamic registration of geoprocessing tools with Pydantic models
2. **Context Management:** Conversation history with spatial context preservation
3. **Knowledge Graph Reasoning:** Neo4j-based spatial-temporal relationship analysis
4. **LLM Orchestration:** Multi-step reasoning with tool selection and execution

### Data Flow Patterns
1. **File Upload:** Client → MinIO → Format Conversion → PostgreSQL → Layer Creation
2. **AI Workflow:** User Message → Tool Selection → Execution → Layer Creation → Styling
3. **Knowledge Graph Sync:** PostgreSQL → Config Mapping → Neo4j Graph Updates
4. **Real-time Collaboration:** WebSocket → State Synchronization → UI Updates

### Key Architectural Decisions
1. **Async Everything:** FastAPI with async/await throughout the backend
2. **Protocol-Based Mapping:** Custom MapLibre protocols for PMTiles, COG, vector tiles
3. **Project-Based Multi-tenancy:** UUID-based ownership with connection-specific isolation
4. **Version Control:** DAG-based map versioning with diff tracking
5. **External Database Support:** Connection pooling with read-only enforcement

## Essential Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync --dev                    # Backend dependencies
cd frontendts && npm ci --legacy-peer-deps  # Frontend dependencies

# Start all services
docker compose up -d             # Detached mode for development
```

### Daily Development
```bash
# Backend development server
uv run uvicorn src.wsgi:app --host 0.0.0.0 --port 8000 --reload

# Frontend development server
cd frontendts && npm run dev     # Vite dev server on port 5173

# Database operations
uv run alembic upgrade head      # Apply migrations
uv run alembic revision --autogenerate -m "description"  # Create migration
```

### Testing Commands
```bash
# Backend tests
uv run pytest -xvs -n auto       # All tests with parallel execution
uv run pytest -m postgres        # PostgreSQL tests only
uv run pytest -m s3             # S3/MinIO tests only

# Run specific test
uv run pytest src/routes/test_layers.py::test_create_layer -xvs

# Frontend tests
cd frontendts && npm test
```

### Code Quality (Run Before Committing)
```bash
# Python linting and formatting
ruff check . && ruff format .
uv run basedpyright              # Type checking

# Frontend linting
cd frontendts && npm run lint    # Biome linting
```

### Build Commands
```bash
# Frontend production build
cd frontendts && npm run build

# Docker build
docker buildx bake --file docker-compose.yml --load
```

## Recent Development Focus

### Patent Development
The team is actively developing core patents in `/a_patent/invention_patent/` focusing on:
- Dynamic knowledge graph construction methods
- AI-powered spatial analysis decision-making
- Large language model autonomous spatial intelligence

### Knowledge Graph Enhancement
Current development priorities include:
- **Instance Import:** PostgreSQL to knowledge graph data ingestion
- **Spatial Relations:** Automated spatial relationship detection
- **Schema Management:** Improved ontology and constraint management
- **Visualization Performance:** Large graph rendering optimization

## AI Assistant Configuration

### Cursor Rules
The project includes comprehensive cursor rules in `.cursor/rules/`:
- **project-structure.mdc** - Project navigation and structure guidelines
- **backend-style.mdc** - Python/FastAPI coding standards
- **frontend-style.mdc** - React/TypeScript best practices
- **knowledge-graph.mdc** - Neo4j and graph database guidelines
- **security-and-eval.mdc** - Security and validation requirements

### Claude Configuration
Claude settings are configured in `.claude/settings.local.json` with appropriate permissions for file operations and bash commands.

## Documentation Structure

**Technical Documentation:**
- `PROJECT_UNDERSTANDING.md` - Comprehensive project overview (Chinese)
- `IFLOW.md` - Project flow and architecture (Chinese)
- `WARP.md` - Development commands and setup instructions
- `docs/` - Full documentation site with API guides

**Knowledge Graph Documentation:**
- `docs/KG_API_USAGE.md` - Knowledge graph API usage guide
- `docs/FRONTEND_KG_DEVELOPMENT_PLAN.md` - Frontend KG development roadmap
- `docs/KG_BUILDER_VISUALIZER_DESIGN.md` - KG builder and visualizer design

This architecture enables Mundi.ai to deliver a powerful, scalable, and maintainable AI-native GIS platform that bridges the gap between complex spatial analysis and intuitive natural language interaction.
