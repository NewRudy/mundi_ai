# FastAPI routes for minimal KG sync
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.services.kg_minimal import (
    apply_config_yaml,
    upsert_instances,
    ingest_spatial_relationships,
    ingest_llm_triples,
    apply_ontology_json,
)
from src.services.kg_config_service import list_kg_configs, read_kg_config
from src.services.kg_init import init_neo4j_constraints_and_indexes, get_neo4j_schema_info
from src.services.graph_service import graph_service

router = APIRouter()


class ApplyConfigRequest(BaseModel):
    config_yaml: str


@router.post("/apply-config")
async def api_apply_config(req: ApplyConfigRequest):
    try:
        result = await apply_config_yaml(req.config_yaml)
        return {"message": "Config applied", **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class UpsertInstanceItem(BaseModel):
    table_name: str
    pg_id: str
    name: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


@router.post("/upsert-instances")
async def api_upsert_instances(items: List[UpsertInstanceItem]):
    try:
        payload = [item.model_dump() for item in items]
        return await upsert_instances(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class SpatialEndpointItem(BaseModel):
    source: Dict[str, Any]
    target: Dict[str, Any]
    type: Optional[str] = "RELATED_TO"
    properties: Optional[Dict[str, Any]] = None


@router.post("/relationships/spatial")
async def api_spatial_relationships(items: List[SpatialEndpointItem]):
    try:
        payload = [item.model_dump() for item in items]
        return await ingest_spatial_relationships(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class TripleNode(BaseModel):
    labels: Optional[List[str]] = None
    key: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


class LLMTriple(BaseModel):
    start: TripleNode
    end: TripleNode
    type: Optional[str] = "RELATED_TO"
    properties: Optional[Dict[str, Any]] = None


@router.post("/ingest/llm-triples")
async def api_llm_triples(triples: List[LLMTriple]):
    try:
        payload = [t.model_dump() for t in triples]
        return await ingest_llm_triples(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class OntologyJSONPayload(BaseModel):
    ontology_json: Dict[str, Any]


@router.post("/apply-ontology-json")
async def api_apply_ontology_json(req: OntologyJSONPayload):
    try:
        return await apply_ontology_json(req.ontology_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Config file management
@router.get("/configs")
async def api_list_configs(subdir: Optional[str] = None):
    """List configuration files in knowledge_config/ directory"""
    try:
        return await list_kg_configs(subdir=subdir)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/configs/{rel_path:path}")
async def api_read_config(rel_path: str):
    """Read a specific configuration file"""
    try:
        return await read_kg_config(rel_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Schema management
@router.post("/schema/init")
async def api_init_schema():
    """Initialize Neo4j constraints and indexes"""
    try:
        return await init_neo4j_constraints_and_indexes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/info")
async def api_schema_info():
    """Get current Neo4j schema information"""
    try:
        return await get_neo4j_schema_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Graph query and visualization
@router.get("/graph/stats")
async def api_graph_stats():
    """Get graph database statistics""" 
    try:
        return await graph_service.get_graph_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/search")
async def api_search_nodes(
    name: Optional[str] = Query(None, description="Search by node name"),
    labels: Optional[str] = Query(None, description="Comma-separated labels to filter"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Search nodes by name and/or labels"""
    try:
        label_list = [l.strip() for l in labels.split(",")] if labels else None
        return await graph_service.search_nodes(
            name=name,
            labels=label_list,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/subgraph")
async def api_extract_subgraph(
    root_id: str = Query(..., description="Root node ID to start expansion"),
    depth: int = Query(2, ge=1, le=3, description="Maximum traversal depth (1-3)"),
    labels: Optional[str] = Query(None, description="Comma-separated labels to filter"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Extract a subgraph starting from a root node"""
    try:
        label_list = [l.strip() for l in labels.split(",")] if labels else None
        return await graph_service.extract_subgraph(
            root_id=root_id,
            depth=depth,
            labels=label_list,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
