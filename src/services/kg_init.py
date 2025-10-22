# Knowledge Graph Neo4j initialization
# Sets up constraints and indexes per KG_BUILDER_VISUALIZER_DESIGN.md

from typing import Dict, Any, List
from src.dependencies.neo4j_connection import get_neo4j_session

async def init_neo4j_constraints_and_indexes() -> Dict[str, Any]:
    """Initialize Neo4j constraints and indexes for the knowledge graph.
    
    Creates:
    - Unique constraints on id for Ontology, Table, Instance, Dataset, Location, Concept, TimePeriod
    - Indexes on name/table_name/pg_id for improved query performance
    
    Returns summary of created constraints and indexes.
    """
    async with get_neo4j_session() as session:
        results = {
            "constraints_created": [],
            "indexes_created": [],
            "errors": []
        }
        
        # Unique constraints on id for each node type
        constraint_queries = [
            "CREATE CONSTRAINT unique_ontology_id IF NOT EXISTS FOR (n:Ontology) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT unique_table_id IF NOT EXISTS FOR (n:Table) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT unique_instance_id IF NOT EXISTS FOR (n:Instance) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT unique_dataset_id IF NOT EXISTS FOR (n:Dataset) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT unique_location_id IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT unique_concept_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT unique_timeperiod_id IF NOT EXISTS FOR (n:TimePeriod) REQUIRE n.id IS UNIQUE",
        ]
        
        for query in constraint_queries:
            try:
                await session.run(query)
                results["constraints_created"].append(query.split()[2])
            except Exception as e:
                results["errors"].append(f"Constraint error: {str(e)}")
        
        # Helpful indexes for common search patterns
        index_queries = [
            "CREATE INDEX ontology_name_idx IF NOT EXISTS FOR (n:Ontology) ON (n.name)",
            "CREATE INDEX table_name_idx IF NOT EXISTS FOR (n:Table) ON (n.table_name)",
            "CREATE INDEX instance_pg_id_idx IF NOT EXISTS FOR (n:Instance) ON (n.pg_id)",
            "CREATE INDEX instance_name_idx IF NOT EXISTS FOR (n:Instance) ON (n.name)",
            "CREATE INDEX location_name_idx IF NOT EXISTS FOR (n:Location) ON (n.name)",
            "CREATE INDEX concept_name_idx IF NOT EXISTS FOR (n:Concept) ON (n.name)",
        ]
        
        for query in index_queries:
            try:
                await session.run(query)
                results["indexes_created"].append(query.split()[2])
            except Exception as e:
                results["errors"].append(f"Index error: {str(e)}")
        
        return results


async def get_neo4j_schema_info() -> Dict[str, Any]:
    """Get current Neo4j schema information (constraints, indexes, labels, relationship types)"""
    async with get_neo4j_session() as session:
        schema_info = {
            "constraints": [],
            "indexes": [],
            "labels": [],
            "relationship_types": []
        }
        
        # Get constraints
        try:
            result = await session.run("SHOW CONSTRAINTS")
            async for record in result:
                schema_info["constraints"].append(dict(record))
        except Exception:
            pass
        
        # Get indexes
        try:
            result = await session.run("SHOW INDEXES")
            async for record in result:
                schema_info["indexes"].append(dict(record))
        except Exception:
            pass
        
        # Get node labels
        try:
            result = await session.run("CALL db.labels()")
            async for record in result:
                schema_info["labels"].append(record[0])
        except Exception:
            pass
        
        # Get relationship types
        try:
            result = await session.run("CALL db.relationshipTypes()")
            async for record in result:
                schema_info["relationship_types"].append(record[0])
        except Exception:
            pass
        
        return schema_info
