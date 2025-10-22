# Copyright (C) 2025 Bunting Labs, Inc.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from src.services.graph_service import graph_service
from src.models.graph_models import (
    CreateNodeRequest, CreateRelationshipRequest, GraphQuery, GraphQueryResult,
    NodeType, RelationshipType
)

router = APIRouter()


# Response models
class NodeResponse(BaseModel):
    """Node response model"""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class RelationshipResponse(BaseModel):
    """Relationship response model"""
    id: str
    type: str
    other_node_id: str
    direction: str
    properties: Dict[str, Any]


class GraphStatsResponse(BaseModel):
    """Graph statistics response model"""
    nodes: Dict[str, int]
    relationships: Dict[str, int]
    total_nodes: int
    total_relationships: int


@router.post("/nodes", response_model=Dict[str, str])
async def create_node(node_request: CreateNodeRequest):
    """Create a new node in the graph database"""
    try:
        node_id = await graph_service.create_node(node_request)
        return {"id": node_id, "message": "Node created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}", response_model=Optional[NodeResponse])
async def get_node(node_id: str = Path(..., description="The node ID")):
    """Get a node by its ID"""
    try:
        node = await graph_service.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return NodeResponse(**node)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nodes/{node_id}")
async def update_node(
    node_id: str = Path(..., description="The node ID"),
    properties: Dict[str, Any] = None
):
    """Update a node's properties"""
    if not properties:
        raise HTTPException(status_code=400, detail="Properties are required")
    
    try:
        success = await graph_service.update_node(node_id, properties)
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"message": "Node updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str = Path(..., description="The node ID")):
    """Delete a node and all its relationships"""
    try:
        success = await graph_service.delete_node(node_id)
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"message": "Node deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes", response_model=List[NodeResponse])
async def find_nodes(
    labels: Optional[List[str]] = Query(None, description="Filter by node labels"),
    **properties
):
    """Find nodes by properties and optional labels"""
    try:
        # Extract properties from query parameters
        search_properties = {k: v for k, v in properties.items() if v is not None}
        
        nodes = await graph_service.find_nodes_by_properties(search_properties, labels)
        return [NodeResponse(**node) for node in nodes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships", response_model=Dict[str, str])
async def create_relationship(relationship_request: CreateRelationshipRequest):
    """Create a new relationship between two nodes"""
    try:
        rel_id = await graph_service.create_relationship(relationship_request)
        return {"id": rel_id, "message": "Relationship created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}/relationships", response_model=List[RelationshipResponse])
async def get_node_relationships(
    node_id: str = Path(..., description="The node ID"),
    direction: str = Query("both", description="Relationship direction: incoming, outgoing, or both")
):
    """Get all relationships for a node"""
    if direction not in ["incoming", "outgoing", "both"]:
        raise HTTPException(status_code=400, detail="Direction must be 'incoming', 'outgoing', or 'both'")
    
    try:
        relationships = await graph_service.get_node_relationships(node_id, direction)
        return [RelationshipResponse(**rel) for rel in relationships]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/{relationship_id}")
async def delete_relationship(relationship_id: str = Path(..., description="The relationship ID")):
    """Delete a relationship"""
    try:
        success = await graph_service.delete_relationship(relationship_id)
        if not success:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return {"message": "Relationship deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spatial/neighbors/{location_name}", response_model=List[NodeResponse])
async def get_spatial_neighbors(
    location_name: str = Path(..., description="The location name"),
    max_distance_km: float = Query(100, description="Maximum distance in kilometers")
):
    """Find spatial neighbors of a location within a distance"""
    try:
        neighbors = await graph_service.find_spatial_neighbors(location_name, max_distance_km)
        return [NodeResponse(**neighbor) for neighbor in neighbors]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=GraphQueryResult)
async def execute_cypher_query(query: GraphQuery):
    """Execute a custom Cypher query on the graph database"""
    try:
        result = await graph_service.execute_cypher_query(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_statistics():
    """Get graph database statistics"""
    try:
        stats = await graph_service.get_graph_stats()
        return GraphStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Convenience endpoints for specific node types
@router.post("/locations", response_model=Dict[str, str])
async def create_location(
    name: str,
    geometry_type: Optional[str] = None,
    coordinates: Optional[List[float]] = None,
    bbox: Optional[List[float]] = None,
    admin_level: Optional[int] = None,
    country_code: Optional[str] = None
):
    """Create a new location node"""
    properties = {
        "name": name,
        "geometry_type": geometry_type,
        "coordinates": coordinates,
        "bbox": bbox,
        "admin_level": admin_level,
        "country_code": country_code
    }
    # Remove None values
    properties = {k: v for k, v in properties.items() if v is not None}
    
    request = CreateNodeRequest(node_type=NodeType.LOCATION, properties=properties)
    return await create_node(request)


@router.post("/datasets", response_model=Dict[str, str])
async def create_dataset(
    name: str,
    description: Optional[str] = None,
    source: Optional[str] = None,
    data_type: Optional[str] = None,
    crs: Optional[str] = None,
    bbox: Optional[List[float]] = None
):
    """Create a new dataset node"""
    properties = {
        "name": name,
        "description": description,
        "source": source,
        "data_type": data_type,
        "crs": crs,
        "bbox": bbox
    }
    # Remove None values
    properties = {k: v for k, v in properties.items() if v is not None}
    
    request = CreateNodeRequest(node_type=NodeType.DATASET, properties=properties)
    return await create_node(request)


@router.get("/health")
async def health_check():
    """Health check endpoint for the graph database"""
    try:
        stats = await graph_service.get_graph_stats()
        return {
            "status": "healthy",
            "total_nodes": stats["total_nodes"],
            "total_relationships": stats["total_relationships"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Subgraph API for visualization
class SubgraphNode(BaseModel):
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class SubgraphRelationship(BaseModel):
    id: str
    type: str
    start: str
    end: str
    properties: Dict[str, Any]


class SubgraphPage(BaseModel):
    limit: int
    offset: int
    has_more: bool


class SubgraphResponse(BaseModel):
    nodes: List[SubgraphNode]
    relationships: List[SubgraphRelationship]
    page: SubgraphPage


_ALLOWED_NODE_PROPS = {
    "id",
    "name",
    "english_name",
    "node_kind",
    "table_name",
    "schema",
    "entity_type",
    "pg_id",
    "bbox",
    "centroid",
}


@router.get("/subgraph", response_model=SubgraphResponse)
async def get_subgraph(
    root_id: str = Query(..., description="Root node id to expand from"),
    depth: int = Query(2, ge=1, le=3),
    labels: Optional[List[str]] = Query(None, description="Restrict to these labels"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Return a bounded subgraph for visualization.
    Returns nodes reachable within `depth` and relationships among returned nodes.
    """
    from src.dependencies.neo4j_connection import get_neo4j_session

    lbls = labels or []

    # Phase 1: fetch nodes
    node_query = (
        "MATCH (r {id: $root}) "
        "WITH r "
        "MATCH p=(r)-[*1..$depth]-(n) "
        "WHERE $labels = [] OR any(l IN labels(n) WHERE l IN $labels) "
        "WITH collect(distinct n) + r AS ns "
        "UNWIND ns AS n "
        "RETURN n, labels(n) as labels SKIP $offset LIMIT $limit"
    )

    nodes: List[Dict[str, Any]] = []
    async with get_neo4j_session() as session:
        try:
            result = await session.run(
                node_query,
                root=root_id,
                depth=depth,
                labels=lbls,
                offset=offset,
                limit=limit,
            )
            async for record in result:
                n = dict(record["n"])  # raw props from Neo4j
                # Whitelist props
                props = {k: v for k, v in n.items() if k in _ALLOWED_NODE_PROPS}
                nid = n.get("id")
                if not nid:
                    continue
                nodes.append({
                    "id": nid,
                    "labels": record["labels"],
                    "properties": props,
                })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"subgraph node query failed: {e}")

    node_ids = [n["id"] for n in nodes]
    if not node_ids:
        return SubgraphResponse(nodes=[], relationships=[], page=SubgraphPage(limit=limit, offset=offset, has_more=False))

    # Phase 2: fetch relationships among the node set
    rel_limit = min(limit * 4, 4000)
    rel_query = (
        "WITH $ids AS ids "
        "MATCH (a)-[r]-(b) WHERE a.id IN ids AND b.id IN ids "
        "RETURN r, startNode(r).id AS start, endNode(r).id AS end, type(r) AS t "
        "LIMIT $rel_limit"
    )

    relationships: List[Dict[str, Any]] = []
    async with get_neo4j_session() as session:
        try:
            result = await session.run(rel_query, ids=node_ids, rel_limit=rel_limit)
            async for record in result:
                r = dict(record["r"])  # properties
                props = {k: v for k, v in r.items() if isinstance(k, str)}
                rid = r.get("id")
                if not rid:
                    # Generate a synthetic id from start-end-type if missing
                    rid = f"{record['start']}->{record['t']}->{record['end']}"
                relationships.append({
                    "id": rid,
                    "type": record["t"],
                    "start": record["start"],
                    "end": record["end"],
                    "properties": props,
                })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"subgraph relationship query failed: {e}")

    has_more = len(nodes) == limit
    # Build response models
    node_models = [SubgraphNode(**n) for n in nodes]
    rel_models = [SubgraphRelationship(**r) for r in relationships]
    return SubgraphResponse(nodes=node_models, relationships=rel_models, page=SubgraphPage(limit=limit, offset=offset, has_more=has_more))
