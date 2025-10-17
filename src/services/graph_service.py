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

import uuid
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from neo4j import AsyncSession
from neo4j.exceptions import Neo4jError

from src.dependencies.neo4j_connection import get_neo4j_session
from src.models.graph_models import (
    GraphNode, GraphRelationship, GraphQuery, GraphQueryResult,
    NodeType, RelationshipType,
    LocationNode, AdministrativeUnitNode, FeatureNode, DatasetNode,
    AttributeNode, TimePeriodNode, ConceptNode, UserQueryNode,
    CreateNodeRequest, CreateRelationshipRequest
)


class GraphService:
    """Neo4j graph database service for spatial-temporal knowledge graph operations"""
    
    @staticmethod
    def _convert_properties_for_neo4j(properties: Dict[str, Any]) -> Dict[str, Any]:
        """Convert properties for Neo4j storage (handle datetime, etc.)"""
        converted = {}
        for key, value in properties.items():
            if isinstance(value, datetime):
                converted[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                # Neo4j doesn't handle nested structures well, convert to JSON string
                import json
                converted[key] = json.dumps(value)
            else:
                converted[key] = value
        return converted
    
    @staticmethod
    def _convert_properties_from_neo4j(properties: Dict[str, Any]) -> Dict[str, Any]:
        """Convert properties from Neo4j storage (parse datetime, JSON, etc.)"""
        converted = {}
        for key, value in properties.items():
            if isinstance(value, str):
                # Try to parse as datetime
                try:
                    converted[key] = datetime.fromisoformat(value)
                    continue
                except ValueError:
                    pass
                
                # Try to parse as JSON
                try:
                    import json
                    parsed = json.loads(value)
                    if isinstance(parsed, (list, dict)):
                        converted[key] = parsed
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
            
            converted[key] = value
        return converted
    
    async def create_node(self, node_data: Union[GraphNode, CreateNodeRequest]) -> str:
        """Create a new node in the graph"""
        async with get_neo4j_session() as session:
            if isinstance(node_data, CreateNodeRequest):
                labels = [node_data.node_type.value]
                properties = node_data.properties
            else:
                labels = node_data.labels
                properties = dict(node_data.properties)
                # Add node-specific properties
                if hasattr(node_data, 'dict'):
                    node_dict = node_data.dict(exclude={'id', 'labels', 'properties'})
                    properties.update({k: v for k, v in node_dict.items() if v is not None})
            
            # Generate unique ID if not provided
            node_id = str(uuid.uuid4())
            properties['id'] = node_id
            properties['created_at'] = datetime.now().isoformat()
            
            # Convert properties for Neo4j
            neo4j_properties = self._convert_properties_for_neo4j(properties)
            
            # Create Cypher query
            labels_str = ':'.join(labels)
            cypher = f"CREATE (n:{labels_str} $properties) RETURN n.id as id"
            
            try:
                result = await session.run(cypher, properties=neo4j_properties)
                record = await result.single()
                return record['id']
            except Neo4jError as e:
                raise Exception(f"Failed to create node: {e}")
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by ID"""
        async with get_neo4j_session() as session:
            cypher = "MATCH (n {id: $node_id}) RETURN n, labels(n) as labels"
            
            try:
                result = await session.run(cypher, node_id=node_id)
                record = await result.single()
                if not record:
                    return None
                
                node = dict(record['n'])
                node['labels'] = record['labels']
                
                # Convert properties back from Neo4j
                node = self._convert_properties_from_neo4j(node)
                return node
            except Neo4jError as e:
                raise Exception(f"Failed to get node: {e}")
    
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update a node's properties"""
        async with get_neo4j_session() as session:
            properties['updated_at'] = datetime.now().isoformat()
            neo4j_properties = self._convert_properties_for_neo4j(properties)
            
            cypher = "MATCH (n {id: $node_id}) SET n += $properties RETURN n.id as id"
            
            try:
                result = await session.run(cypher, node_id=node_id, properties=neo4j_properties)
                record = await result.single()
                return record is not None
            except Neo4jError as e:
                raise Exception(f"Failed to update node: {e}")
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its relationships"""
        async with get_neo4j_session() as session:
            cypher = "MATCH (n {id: $node_id}) DETACH DELETE n RETURN count(n) as deleted_count"
            
            try:
                result = await session.run(cypher, node_id=node_id)
                record = await result.single()
                return record['deleted_count'] > 0
            except Neo4jError as e:
                raise Exception(f"Failed to delete node: {e}")
    
    async def create_relationship(self, relationship_data: Union[GraphRelationship, CreateRelationshipRequest]) -> str:
        """Create a relationship between two nodes"""
        async with get_neo4j_session() as session:
            if isinstance(relationship_data, CreateRelationshipRequest):
                start_node_id = relationship_data.start_node_id
                end_node_id = relationship_data.end_node_id
                rel_type = relationship_data.relationship_type.value
                properties = relationship_data.properties or {}
            else:
                start_node_id = relationship_data.start_node
                end_node_id = relationship_data.end_node
                rel_type = relationship_data.type.value
                properties = relationship_data.properties
            
            # Generate relationship ID and add metadata
            rel_id = str(uuid.uuid4())
            properties['id'] = rel_id
            properties['created_at'] = datetime.now().isoformat()
            
            neo4j_properties = self._convert_properties_for_neo4j(properties)
            
            cypher = f"""
            MATCH (a {{id: $start_id}}), (b {{id: $end_id}})
            CREATE (a)-[r:{rel_type} $properties]->(b)
            RETURN r.id as id
            """
            
            try:
                result = await session.run(
                    cypher, 
                    start_id=start_node_id, 
                    end_id=end_node_id, 
                    properties=neo4j_properties
                )
                record = await result.single()
                if not record:
                    raise Exception("Failed to create relationship - nodes may not exist")
                return record['id']
            except Neo4jError as e:
                raise Exception(f"Failed to create relationship: {e}")
    
    async def get_node_relationships(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """Get all relationships for a node"""
        async with get_neo4j_session() as session:
            if direction.lower() == "outgoing":
                cypher = """
                MATCH (n {id: $node_id})-[r]->(m)
                RETURN r, type(r) as rel_type, m.id as other_node_id, 'outgoing' as direction
                """
            elif direction.lower() == "incoming":
                cypher = """
                MATCH (n {id: $node_id})<-[r]-(m)
                RETURN r, type(r) as rel_type, m.id as other_node_id, 'incoming' as direction
                """
            else:  # both
                cypher = """
                MATCH (n {id: $node_id})-[r]-(m)
                RETURN r, type(r) as rel_type, m.id as other_node_id,
                       CASE WHEN startNode(r).id = $node_id THEN 'outgoing' ELSE 'incoming' END as direction
                """
            
            try:
                result = await session.run(cypher, node_id=node_id)
                relationships = []
                async for record in result:
                    rel_data = dict(record['r'])
                    rel_data = self._convert_properties_from_neo4j(rel_data)
                    rel_data['type'] = record['rel_type']
                    rel_data['other_node_id'] = record['other_node_id']
                    rel_data['direction'] = record['direction']
                    relationships.append(rel_data)
                return relationships
            except Neo4jError as e:
                raise Exception(f"Failed to get relationships: {e}")
    
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship by ID"""
        async with get_neo4j_session() as session:
            cypher = "MATCH ()-[r {id: $rel_id}]-() DELETE r RETURN count(r) as deleted_count"
            
            try:
                result = await session.run(cypher, rel_id=relationship_id)
                record = await result.single()
                return record['deleted_count'] > 0
            except Neo4jError as e:
                raise Exception(f"Failed to delete relationship: {e}")
    
    async def find_nodes_by_properties(self, properties: Dict[str, Any], labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Find nodes by properties and optional labels"""
        async with get_neo4j_session() as session:
            # Build labels part of query
            labels_str = ""
            if labels:
                labels_str = ":" + ":".join(labels)
            
            # Build properties part of query
            property_conditions = []
            params = {}
            for key, value in properties.items():
                param_key = f"prop_{key}"
                property_conditions.append(f"n.{key} = ${param_key}")
                params[param_key] = value
            
            where_clause = " AND ".join(property_conditions) if property_conditions else ""
            if where_clause:
                where_clause = f"WHERE {where_clause}"
            
            cypher = f"MATCH (n{labels_str}) {where_clause} RETURN n, labels(n) as labels"
            
            try:
                result = await session.run(cypher, **params)
                nodes = []
                async for record in result:
                    node = dict(record['n'])
                    node['labels'] = record['labels']
                    node = self._convert_properties_from_neo4j(node)
                    nodes.append(node)
                return nodes
            except Neo4jError as e:
                raise Exception(f"Failed to find nodes: {e}")
    
    async def find_spatial_neighbors(self, location_name: str, max_distance_km: float = 100) -> List[Dict[str, Any]]:
        """Find spatial neighbors within a distance (simplified version)"""
        async with get_neo4j_session() as session:
            cypher = """
            MATCH (center:Location {name: $location_name})
            MATCH (neighbor:Location)
            WHERE neighbor.name <> center.name
            OPTIONAL MATCH (center)-[r:ADJACENT_TO|CONTAINS]-(neighbor)
            RETURN neighbor, r, 
                   CASE WHEN r IS NOT NULL THEN coalesce(r.distance_km, 0) ELSE null END as distance
            ORDER BY distance ASC
            LIMIT 50
            """
            
            try:
                result = await session.run(cypher, location_name=location_name)
                neighbors = []
                async for record in result:
                    neighbor = dict(record['neighbor'])
                    neighbor = self._convert_properties_from_neo4j(neighbor)
                    neighbor['distance_km'] = record['distance']
                    neighbors.append(neighbor)
                return neighbors
            except Neo4jError as e:
                raise Exception(f"Failed to find spatial neighbors: {e}")
    
    async def execute_cypher_query(self, query: GraphQuery) -> GraphQueryResult:
        """Execute a custom Cypher query"""
        async with get_neo4j_session() as session:
            try:
                result = await session.run(query.cypher, **query.parameters)
                records = []
                async for record in result:
                    record_dict = dict(record)
                    # Convert any node/relationship objects to dicts
                    for key, value in record_dict.items():
                        if hasattr(value, '__dict__'):
                            record_dict[key] = dict(value)
                    records.append(record_dict)
                
                summary_info = {
                    "query": query.cypher,
                    "parameters": query.parameters,
                    "record_count": len(records)
                }
                
                return GraphQueryResult(records=records, summary=summary_info)
            except Neo4jError as e:
                raise Exception(f"Failed to execute query: {e}")
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph database statistics"""
        async with get_neo4j_session() as session:
            try:
                # Get node counts by label
                cypher_nodes = """
                MATCH (n)
                RETURN labels(n) as labels, count(n) as count
                """
                result = await session.run(cypher_nodes)
                node_stats = {}
                async for record in result:
                    labels = record['labels']
                    count = record['count']
                    for label in labels:
                        node_stats[label] = node_stats.get(label, 0) + count
                
                # Get relationship counts by type
                cypher_rels = """
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                """
                result = await session.run(cypher_rels)
                rel_stats = {}
                async for record in result:
                    rel_stats[record['rel_type']] = record['count']
                
                return {
                    "nodes": node_stats,
                    "relationships": rel_stats,
                    "total_nodes": sum(node_stats.values()),
                    "total_relationships": sum(rel_stats.values())
                }
            except Neo4jError as e:
                raise Exception(f"Failed to get graph stats: {e}")


# Global service instance
graph_service = GraphService()