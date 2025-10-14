# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Mundi.ai is an open-source AI-native web GIS platform supporting vector, raster, and point cloud data. It connects to spatial databases like PostGIS and uses LLMs to call geoprocessing algorithms and edit symbology.

## Common Development Commands

### Local Development (Docker Compose)
```bash
# Start the full development environment
docker compose up

# Build and start with clean rebuild
docker compose up --build

# Run tests in containers
docker compose run app pytest -xvs -n auto

# Run a single test file
docker compose run app pytest src/routes/test_attribute_table.py -v

# Run specific test by name
docker compose run app pytest -k "test_function_name" -v
```

### Frontend Development
```bash
# Navigate to frontend directory
cd frontendts

# Install dependencies
npm ci --legacy-peer-deps

# Start development server
npm run dev

# Build for production
npm run build

# Lint frontend code
npm run lint

# TypeScript watch mode
npm run watch
```

### Backend Development
```bash
# Install Python dependencies with uv
uv sync --dev

# Run backend directly (requires services)
uv run uvicorn src.wsgi:app --host 0.0.0.0 --port 8000 --reload

# Run tests with pytest
uv run pytest -xvs
uv run pytest src/routes/test_*.py

# Run specific test markers
uv run pytest -m postgres  # PostgreSQL tests
uv run pytest -m s3        # S3/MinIO tests

# Type checking
uv run basedpyright

# Database migrations
uv run alembic upgrade head
```

### Documentation
```bash
# Navigate to docs directory
cd docs

# Start documentation development server
npm run dev

# Build documentation
npm run build
```

### Linting and Quality
```bash
# Python linting (from root)
ruff check .
ruff format .

# Frontend linting (from frontendts/)
biome ci --error-on-warnings src/

# Type checking
uv run basedpyright
```

## Architecture Overview

### Multi-Service Architecture
- **Main Application**: FastAPI backend serving both API and SPA frontend
- **Frontend**: React/TypeScript SPA built with Vite, using MapLibre for mapping
- **QGIS Processing**: Separate service for geoprocessing operations
- **PostgreSQL**: Primary database with PostGIS extension
- **Redis**: Caching and session management
- **MinIO**: S3-compatible object storage for file uploads

### Key Components

#### Backend (`src/`)
- **`wsgi.py`**: FastAPI application entry point with router mounting
- **`database/models.py`**: SQLAlchemy models (Projects, Maps, Layers, etc.)
- **`routes/`**: API endpoints organized by functionality
  - `postgres_routes.py`: Map/project management, rendering, uploads
  - `layer_router.py`: Layer CRUD operations
  - `message_routes.py`: AI agent orchestration
  - `conversation_routes.py`: Chat/conversation management
  - `websocket.py`: Real-time communication
- **`dependencies/`**: Shared services and dependency injection
- **`geoprocessing/`**: QGIS integration and spatial processing

#### Frontend (`frontendts/src/`)
- **`main.tsx`**: React application entry point
- **`App.tsx`**: Root component with routing
- **`components/`**: Reusable UI components
  - `MapLibreMap.tsx`: Core mapping component
  - `LayerList.tsx`: Layer management UI
  - `ProjectView.tsx`: Project workspace interface
- **`lib/types.tsx`**: TypeScript type definitions for API integration

#### Data Flow Patterns
1. **Data Ingestion**: File upload → S3 storage → Layer record creation
2. **Rendering Pipeline**:
   - Raster: COG/XYZ tiles via rio-tiler
   - Vector: MVT/PMTiles generation
3. **AI Workflow**: User message → Tool selection → PostGIS/DuckDB/QGIS execution → New layer + styling

### Database Schema Highlights
- **`MundiProject`**: Container for maps with access control
- **`MundiMap`**: Individual maps with layer collections and versioning
- **`MapLayer`**: Spatial data references (vector/raster/PostGIS/point cloud)
- **`ProjectPostgresConnection`**: External database connections
- **`MapLayerStyle`**: MapLibre GL styling for layers

### Development Patterns

#### Asynchronous Operations
- All database connections use asyncpg through `get_async_db_connection()`
- S3 operations use aioboto3 via `get_async_s3_client()`
- QGIS processing calls external service with timeout handling

#### Security Constraints
- PostGIS queries validated with `EXPLAIN (FORMAT JSON)` to prevent writes
- All external queries limited to < 1000 results
- LLM tool calls use restricted Pydantic parameter templates
- MapLibre styles validated through `src/symbology/verify.py`

#### Geographic Data Handling
- Supports multiple projections via pyproj
- Raster data processed as Cloud Optimized GeoTIFF (COG)
- Vector data served as Mapbox Vector Tiles (MVT)
- Point clouds handled via LAZ format with LAStools

## Development Environment Setup

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ with uv (for backend development)

### Environment Variables
The docker-compose.yml provides defaults, but key variables include:
- `POSTGRES_*`: Database connection settings
- `S3_*`: Object storage configuration
- `OPENAI_API_KEY`: LLM integration
- `QGIS_PROCESSING_URL`: Geoprocessing service endpoint
- `MUNDI_AUTH_MODE`: Set to "edit" or "view_only"

### Testing Strategy
- Backend: pytest with asyncio support, markers for service dependencies
- Frontend: Biome for linting and formatting
- Integration: Docker Compose for full stack testing
- CI/CD: GitHub Actions with Depot for container builds

## Code Organization

### Python Code Style
- Use async/await for all I/O operations
- Explicit type annotations for public APIs
- Pydantic models for request/response validation
- OpenTelemetry tracing for observability
- HTTPException with structured error details

### Frontend Code Style  
- Functional components with hooks
- TypeScript for all new code
- React.memo/useMemo for performance optimization
- MapLibre integration through centralized wrapper
- Separation of API types in `lib/types.tsx`

### File Placement Conventions
- New routes: `src/routes/`
- Shared utilities: `src/dependencies/`
- Database models: `src/database/models.py`
- Frontend components: `frontendts/src/components/`
- Tests: Colocated with source files using `test_*.py` naming

## Key External Dependencies

### Geospatial Stack
- GDAL 3.11.3+ for raster/vector processing
- PostGIS for spatial database operations
- QGIS 3.x for advanced geoprocessing (separate container)
- Tippecanoe for vector tile generation

### Frontend Stack
- React 18 with TypeScript
- MapLibre GL JS for web mapping
- Deck.gl for advanced visualizations
- Radix UI for component primitives
- TanStack Query for data fetching

### Backend Stack
- FastAPI with SQLAlchemy async
- Alembic for database migrations
- OpenAI client for LLM integration
- Boto3/aioboto3 for S3 operations