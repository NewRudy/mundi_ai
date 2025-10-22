# FastAPI routes for minimal KG sync
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.kg_minimal import (
    apply_config_yaml,
    upsert_instances,
    ingest_spatial_relationships,
    ingest_llm_triples,
)

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
