# Minimal config-driven knowledge graph sync for Neo4j
#
# Core features:
# - Apply a simple YAML config to create Ontology, Table nodes and relationships
# - Upsert Instance nodes and link them to Table nodes
# - Store spatial analysis results as relationships (QGIS service outputs or other)
# - Optional LLM ingestion: create Concept/Feature/etc. nodes and relationships
#
# Node and relationship conventions:
# - Node `id` is globally unique and prefixed by type:
#   Ontology -> ontology:{ontology_id}
#   Table    -> table:{table_name}
#   Instance -> instance:{table_name}:{pg_id}
# - Relationships use standard types where possible:
#   IS_A (Ontology hierarchy), HAS_TABLE (Ontology->Table), INSTANCE_OF (Instance->Table)
#   Spatial: CONTAINS, ADJACENT_TO; others map to RELATED_TO if not natively supported
#
# YAML config example:
# ---
# version: '0.1'
# ontology_nodes:
#   - id: '001'
#     name: 'Root'
#     english_name: 'Root'
#   - id: '001_003_003'
#     name: '基础设施'
#     english_name: 'Infrastructure'
#     parent_id: '001'
# tables:
#   - table_name: 'power_station'
#     entity_type: 'PowerStation'
#     ontology_id: '001_003_003'
#     description: '电站'
#   - table_name: 'airport'
#     entity_type: 'Airport'
#     ontology_id: '001_003_003'
#
# Usage from routes: see src/routes/kg_minimal_routes.py

from __future__ import annotations

import yaml
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.services.graph_service import graph_service
from src.models.graph_models import GraphNode, GraphQuery, GraphQueryResult


# -----------------------------
# Config models
# -----------------------------

class OntologyNodeConfig(BaseModel):
    id: str
    name: str
    english_name: Optional[str] = None
    parent_id: Optional[str] = None


class TableMappingConfig(BaseModel):
    table_name: str
    entity_type: str
    ontology_id: str
    description: Optional[str] = None


class KGConfig(BaseModel):
    version: Optional[str] = None
    ontology_nodes: List[OntologyNodeConfig] = Field(default_factory=list)
    tables: List[TableMappingConfig] = Field(default_factory=list)


# -----------------------------
# ID helpers
# -----------------------------

def ontology_node_id(ontology_id: str) -> str:
    return f"ontology:{ontology_id}"


def table_node_id(table_name: str) -> str:
    return f"table:{table_name}"


def instance_node_id(table_name: str, pg_id: str) -> str:
    return f"instance:{table_name}:{pg_id}"


# -----------------------------
# Upsert helpers
# -----------------------------

async def _find_node_by_id(node_id: str) -> Optional[Dict[str, Any]]:
    nodes = await graph_service.find_nodes_by_properties({"id": node_id})
    return nodes[0] if nodes else None


async def _ensure_node(labels: List[str], node_id: str, properties: Dict[str, Any]) -> str:
    existing = await _find_node_by_id(node_id)
    if existing:
        # Update existing properties
        await graph_service.update_node(node_id, properties)
        return node_id

    # Create new node
    node = GraphNode(labels=labels, properties={**properties, "id": node_id})
    created_id = await graph_service.create_node(node)
    return created_id


async def _ensure_relationship(a_id: str, b_id: str, rel_type: str, rel_props: Optional[Dict[str, Any]] = None) -> None:
    # Use Cypher MERGE to avoid duplicates; rel_type must be sanitized (A-Z, underscore)
    if not rel_type or not rel_type.replace("_", "").isalnum():
        raise ValueError("Invalid relationship type")

    props = rel_props or {}
    cypher = (
        f"MERGE (a {{id: $a_id}}) "
        f"MERGE (b {{id: $b_id}}) "
        f"MERGE (a)-[r:{rel_type}]->(b) "
        f"SET r += $props RETURN r"
    )
    await graph_service.execute_cypher_query(GraphQuery(cypher=cypher, parameters={"a_id": a_id, "b_id": b_id, "props": props}))


# -----------------------------
# Public API
# -----------------------------

async def apply_config_yaml(config_yaml: str) -> Dict[str, Any]:
    """Apply YAML config to build ontology and table topology."""
    data = yaml.safe_load(config_yaml) or {}
    cfg = KGConfig.model_validate(data)

    created: Dict[str, int] = {"ontology": 0, "tables": 0, "relations": 0}

    # 1) Ontology nodes and IS_A relations
    for node in cfg.ontology_nodes:
        oid = ontology_node_id(node.id)
        props = {"name": node.name}
        if node.english_name:
            props["english_name"] = node.english_name
        props["node_kind"] = "Ontology"
        await _ensure_node(["Ontology"], oid, props)
        created["ontology"] += 1

    # Parent-child relationships
    for node in cfg.ontology_nodes:
        if node.parent_id:
            child = ontology_node_id(node.id)
            parent = ontology_node_id(node.parent_id)
            await _ensure_relationship(child, parent, "IS_A")
            created["relations"] += 1

    # 2) Table nodes and HAS_TABLE (Ontology->Table)
    for mapping in cfg.tables:
        tid = table_node_id(mapping.table_name)
        props = {
            "table_name": mapping.table_name,
            "entity_type": mapping.entity_type,
            "description": mapping.description,
            "node_kind": "Table",
        }
        await _ensure_node(["Table"], tid, props)
        created["tables"] += 1

        # Link to ontology
        oid = ontology_node_id(mapping.ontology_id)
        await _ensure_relationship(oid, tid, "HAS_TABLE")
        created["relations"] += 1

    return created


# -----------------------------
# Ontology JSON adapter
# -----------------------------

def _walk_ontology_json(node: Dict[str, Any], out: List[OntologyNodeConfig], parent_id: Optional[str] = None) -> None:
    nid = str(node.get("id"))
    name = node.get("name")
    english_name = node.get("englishName")
    if not nid or not name:
        return
    out.append(OntologyNodeConfig(id=nid, name=name, english_name=english_name, parent_id=parent_id))
    for child in (node.get("subclass") or []):
        if isinstance(child, dict):
            _walk_ontology_json(child, out, parent_id=nid)


def ontology_json_to_kgconfig(data: Dict[str, Any]) -> KGConfig:
    nodes: List[OntologyNodeConfig] = []
    _walk_ontology_json(data, nodes, parent_id=None)
    return KGConfig(ontology_nodes=nodes, tables=[])


async def apply_ontology_json(ontology_json: Dict[str, Any]) -> Dict[str, Any]:
    cfg = ontology_json_to_kgconfig(ontology_json)
    # Dump to YAML and reuse existing apply
    cfg_yaml = yaml.safe_dump(cfg.model_dump(mode="python"), allow_unicode=True, sort_keys=False)
    created = await apply_config_yaml(cfg_yaml)
    return {"ontology_created": created.get("ontology", 0), "relations_created": created.get("relations", 0)}


async def upsert_instance(table_name: str, pg_id: str, name: Optional[str] = None, properties: Optional[Dict[str, Any]] = None) -> str:
    """Create or update an Instance node and link to its Table node."""
    iid = instance_node_id(table_name, pg_id)
    props = {"pg_id": pg_id, "table_name": table_name, "node_kind": "Instance"}
    if name:
        props["name"] = name
    if properties:
        props.update(properties)

    # Ensure instance
    await _ensure_node(["Instance"], iid, props)

    # Ensure INSTANCE_OF link to table
    tid = table_node_id(table_name)
    await _ensure_relationship(iid, tid, "INSTANCE_OF")
    return iid


async def upsert_instances(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    created = []
    for it in items:
        table_name = it["table_name"]
        pg_id = str(it["pg_id"])  # normalize to string
        name = it.get("name")
        props = it.get("properties") or {}
        iid = await upsert_instance(table_name, pg_id, name, props)
        created.append(iid)
    return {"count": len(created), "instance_ids": created}


# Spatial relationships ingestion (e.g., from QGIS outputs)
async def ingest_spatial_relationships(relations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Ingest spatial relationships.

    Each relation item format:
    {
      "source": {"table_name": "airport", "pg_id": "123"} | {"node_id": "instance:airport:123"},
      "target": {"table_name": "power_station", "pg_id": "42"} | {"node_id": "instance:power_station:42"},
      "type": "CONTAINS" | "ADJACENT_TO" | "NEARBY" | "INTERSECTS" | "RELATED_TO",
      "properties": {"distance_km": 12.3, ...}
    }
    """
    supported = {"CONTAINS", "ADJACENT_TO", "NEARBY", "INTERSECTS", "RELATED_TO"}
    made = 0

    for rel in relations:
        rtype = rel.get("type", "RELATED_TO").upper()
        if rtype not in supported:
            rtype = "RELATED_TO"

        # Resolve source/target instance node IDs
        s = rel.get("source", {})
        t = rel.get("target", {})

        if "node_id" in s:
            sid = s["node_id"]
        else:
            sid = instance_node_id(s["table_name"], str(s["pg_id"]))
            # ensure node exists with minimal props
            await _ensure_node(["Instance"], sid, {"node_kind": "Instance", "table_name": s["table_name"], "pg_id": str(s["pg_id"])})

        if "node_id" in t:
            tid = t["node_id"]
        else:
            tid = instance_node_id(t["table_name"], str(t["pg_id"]))
            await _ensure_node(["Instance"], tid, {"node_kind": "Instance", "table_name": t["table_name"], "pg_id": str(t["pg_id"])})

        props = rel.get("properties") or {}

        # Map NEARBY/INTERSECTS to supported types when possible
        # Keep the original intent in properties
        if rtype == "NEARBY":
            mapped_type = "ADJACENT_TO"
            props.setdefault("semantic_type", "NEARBY")
        elif rtype == "INTERSECTS":
            mapped_type = "RELATED_TO"
            props.setdefault("semantic_type", "INTERSECTS")
        else:
            mapped_type = rtype

        await _ensure_relationship(sid, tid, mapped_type, props)
        made += 1

    return {"count": made}


# LLM ingestion: generic triples
async def ingest_llm_triples(triples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Ingest LLM-produced triples.

    Triple format:
    {
      "start": {"labels": ["Concept"], "key": {"name": "洪水"}, "properties": {...}},
      "end":   {"labels": ["Concept"], "key": {"name": "大坝"},  "properties": {...}},
      "type": "RELATED_TO",
      "properties": {"confidence": 0.92}
    }
    Key fields are used to form a deterministic node id: id = "llm:{primary_label}:{key_json}"
    """
    created = 0

    for tri in triples:
        start = tri.get("start", {})
        end = tri.get("end", {})
        rtype = (tri.get("type") or "RELATED_TO").upper()
        props = tri.get("properties") or {}

        def _node_id_from_key(labels: List[str], key: Dict[str, Any]) -> str:
            import json
            primary = labels[0] if labels else "Concept"
            # Stable json representation
            key_s = json.dumps(key, sort_keys=True, ensure_ascii=False)
            return f"llm:{primary}:{key_s}"

        # Start node
        s_labels = start.get("labels") or ["Concept"]
        s_key = start.get("key") or {}
        s_props = start.get("properties") or {}
        s_id = _node_id_from_key(s_labels, s_key)
        await _ensure_node(s_labels, s_id, {**s_key, **s_props, "node_kind": s_labels[0]})

        # End node
        e_labels = end.get("labels") or ["Concept"]
        e_key = end.get("key") or {}
        e_props = end.get("properties") or {}
        e_id = _node_id_from_key(e_labels, e_key)
        await _ensure_node(e_labels, e_id, {**e_key, **e_props, "node_kind": e_labels[0]})

        # Relationship
        await _ensure_relationship(s_id, e_id, rtype, props)
        created += 1

    return {"count": created}
