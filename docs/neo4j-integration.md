# Neo4j Knowledge Graph Integration

This document describes the Neo4j knowledge graph integration in Anway.ai, which provides spatial-temporal reasoning capabilities for GIS queries.

## Overview

The Neo4j integration implements a **spatiotemporal knowledge graph** that enhances Anway's ability to understand and respond to complex GIS queries by maintaining relationships between:

- Geographic locations and administrative units
- Spatial features and datasets
- Temporal relationships
- Conceptual relationships between GIS terms
- User query patterns and context

## Architecture

### Components

1. **Neo4j Database** (`docker-compose.yml`)
   - Neo4j 5.x community edition
   - Web interface available at http://localhost:7474
   - Bolt protocol on port 7687

2. **Connection Management** (`src/dependencies/neo4j_connection.py`)
   - Async connection pooling
   - Configuration via environment variables
   - Graceful error handling

3. **Data Models** (`src/models/graph_models.py`)
   - Node types: Location, Dataset, Feature, Concept, etc.
   - Relationship types: CONTAINS, ADJACENT_TO, PART_OF, etc.
   - Pydantic models for type safety

4. **Service Layer** (`src/services/graph_service.py`)
   - CRUD operations for nodes and relationships
   - Spatial neighbor finding
   - Custom Cypher query execution
   - Property conversion utilities

5. **API Endpoints** (`src/routes/graph_routes.py`)
   - RESTful API for graph operations
   - Health checks and statistics
   - Convenience endpoints for common operations

6. **Data initialization** (`src/scripts/init_graph_data.py`)
   - Loads initial world locations
   - Creates basic GIS concepts
   - Establishes spatial relationships

## Node Types

### Location Nodes
- Geographic places with coordinates and boundaries
- Administrative levels (country, state, city)
- Spatial relationships (contains, adjacent to)

### Dataset Nodes
- Metadata about GIS datasets
- Source information, CRS, data types
- Relationships to features and locations

### Feature Nodes
- Individual GIS features/objects
- Attributes and geometric properties
- Links to parent datasets

### Concept Nodes
- GIS terminology and concepts
- Synonyms and categories
- Semantic relationships

### Time Period Nodes
- Temporal ranges and granularity
- Temporal relationships (before, after, during)

### User Query Nodes
- Query understanding and context
- Spatial and temporal intent
- Learning from user interactions

## Relationship Types

- **CONTAINS**: Spatial containment (country contains state)
- **ADJACENT_TO**: Spatial adjacency with distance/direction
- **PART_OF**: Hierarchical relationships
- **HAS_ATTRIBUTE**: Feature-attribute relationships
- **OCCURS_DURING**: Temporal relationships
- **RELATED_TO**: Conceptual associations
- **QUERIES**: User query relationships
- **MENTIONS**: Reference relationships

## Environment Variables

```bash
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## API Endpoints

### Core Operations
- `POST /api/graph/nodes` - Create a node
- `GET /api/graph/nodes/{id}` - Get node by ID
- `PUT /api/graph/nodes/{id}` - Update node properties
- `DELETE /api/graph/nodes/{id}` - Delete node and relationships
- `GET /api/graph/nodes` - Search nodes by properties

### Relationships
- `POST /api/graph/relationships` - Create relationship
- `GET /api/graph/nodes/{id}/relationships` - Get node relationships
- `DELETE /api/graph/relationships/{id}` - Delete relationship

### Spatial Operations
- `GET /api/graph/spatial/neighbors/{location}` - Find spatial neighbors

### Advanced
- `POST /api/graph/query` - Execute custom Cypher query
- `GET /api/graph/stats` - Graph statistics
- `GET /api/graph/health` - Health check

### Convenience Endpoints
- `POST /api/graph/locations` - Create location node
- `POST /api/graph/datasets` - Create dataset node

## Usage Examples

### Create a Location
```python
from src.models.graph_models import CreateNodeRequest, NodeType

request = CreateNodeRequest(
    node_type=NodeType.LOCATION,
    properties={
        "name": "San Francisco",
        "admin_level": 3,
        "country_code": "US",
        "bbox": [-122.5, 37.7, -122.3, 37.8]
    }
)

location_id = await graph_service.create_node(request)
```

### Find Spatial Neighbors
```python
neighbors = await graph_service.find_spatial_neighbors("San Francisco", max_distance_km=50)
```

### Execute Custom Query
```python
from src.models.graph_models import GraphQuery

query = GraphQuery(
    cypher="MATCH (l:Location {country_code: $country}) RETURN l.name as name",
    parameters={"country": "US"}
)

result = await graph_service.execute_cypher_query(query)
```

## Data Initialization

Run the initialization script to populate basic data:

```bash
cd /path/to/anway
python src/scripts/init_graph_data.py
```

This creates:
- World administrative locations (countries, states, cities)
- Basic GIS concepts and terminology
- Spatial relationships between locations
- Sample datasets

## Testing

Test the integration:

```bash
python test_neo4j_integration.py
```

## Performance Considerations

### Indexes
The system automatically creates indexes on:
- Node IDs (unique constraints)
- Location and dataset names
- Concept names
- Temporal ranges
- Query timestamps

### Query Optimization
- Use parameterized queries to prevent injection
- Limit result sets with pagination
- Use spatial indexes for geographic queries
- Cache frequent relationship patterns

## Future Enhancements

### Phase 2: Enhanced Spatial Reasoning
- Real geometric calculations
- Advanced spatial relationships
- Multi-scale spatial hierarchies

### Phase 3: Temporal Reasoning  
- Time-series data integration
- Temporal pattern recognition
- Historical change detection

### Phase 4: Machine Learning Integration
- Query intent classification
- Spatial relationship prediction
- Automated knowledge extraction

### Phase 5: Real-time Updates
- Live data stream integration
- Event-driven graph updates
- Collaborative knowledge building

## Troubleshooting

### Connection Issues
1. Verify Neo4j container is running: `docker ps`
2. Check connection settings in environment variables
3. Verify network connectivity: `docker network ls`

### Performance Issues
1. Monitor query performance with `EXPLAIN` and `PROFILE`
2. Check index usage: `SHOW INDEXES`
3. Monitor memory usage and heap size

### Data Issues
1. Validate constraints: `SHOW CONSTRAINTS`
2. Check data integrity with validation queries
3. Use graph algorithms for consistency checks

## Resources

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Graph Data Science Library](https://neo4j.com/docs/graph-data-science/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)