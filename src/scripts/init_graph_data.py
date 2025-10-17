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

"""
Initialize Neo4j knowledge graph with basic spatial-temporal data
"""

import asyncio
from typing import List, Dict, Any

from src.services.graph_service import graph_service
from src.models.graph_models import (
    NodeType, RelationshipType,
    CreateNodeRequest, CreateRelationshipRequest
)


async def create_constraints_and_indexes():
    """Create Neo4j constraints and indexes for better performance"""
    from src.dependencies.neo4j_connection import get_neo4j_session
    
    constraints_and_indexes = [
        # Unique constraints
        "CREATE CONSTRAINT unique_node_id IF NOT EXISTS FOR (n:Location) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT unique_dataset_id IF NOT EXISTS FOR (n:Dataset) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT unique_feature_id IF NOT EXISTS FOR (n:Feature) REQUIRE n.id IS UNIQUE",
        
        # Indexes for better search performance
        "CREATE INDEX location_name_index IF NOT EXISTS FOR (n:Location) ON (n.name)",
        "CREATE INDEX dataset_name_index IF NOT EXISTS FOR (n:Dataset) ON (n.name)",
        "CREATE INDEX concept_name_index IF NOT EXISTS FOR (n:Concept) ON (n.name)",
        "CREATE INDEX time_period_dates IF NOT EXISTS FOR (n:TimePeriod) ON (n.start_date, n.end_date)",
        "CREATE INDEX user_query_created_at IF NOT EXISTS FOR (n:UserQuery) ON (n.created_at)",
    ]
    
    async with get_neo4j_session() as session:
        for constraint_or_index in constraints_and_indexes:
            try:
                await session.run(constraint_or_index)
                print(f"✅ Created: {constraint_or_index.split(' ')[1]} {constraint_or_index.split(' ')[2]}")
            except Exception as e:
                print(f"⚠️ {constraint_or_index}: {e}")


async def init_world_locations():
    """Initialize basic world administrative locations"""
    locations_data = [
        # Countries
        {"name": "United States", "admin_level": 0, "country_code": "US", "bbox": [-179.14734, 18.91619, -66.94666, 71.36598]},
        {"name": "Canada", "admin_level": 0, "country_code": "CA", "bbox": [-141.00187, 41.67598, -52.61998, 83.23324]},
        {"name": "China", "admin_level": 0, "country_code": "CN", "bbox": [73.55785, 18.15931, 134.77281, 53.56086]},
        {"name": "Brazil", "admin_level": 0, "country_code": "BR", "bbox": [-73.98283, -33.75118, -28.84799, 5.27438]},
        {"name": "Australia", "admin_level": 0, "country_code": "AU", "bbox": [113.33843, -43.63431, 153.56929, -10.66813]},
        
        # Major US states
        {"name": "California", "admin_level": 1, "country_code": "US", "bbox": [-124.48200, 32.52884, -114.13123, 42.00952]},
        {"name": "Texas", "admin_level": 1, "country_code": "US", "bbox": [-106.64565, 25.83738, -93.50814, 36.50070]},
        {"name": "New York", "admin_level": 1, "country_code": "US", "bbox": [-79.76259, 40.47739, -71.77749, 45.01585]},
        {"name": "Florida", "admin_level": 1, "country_code": "US", "bbox": [-87.63488, 24.39631, -79.97431, 31.00097]},
        
        # Major cities
        {"name": "New York City", "admin_level": 3, "country_code": "US", "bbox": [-74.25909, 40.49612, -73.70018, 40.91553]},
        {"name": "Los Angeles", "admin_level": 3, "country_code": "US", "bbox": [-118.66819, 33.70367, -118.15539, 34.33734]},
        {"name": "Chicago", "admin_level": 3, "country_code": "US", "bbox": [-87.94011, 41.64454, -87.52414, 42.02304]},
        {"name": "Toronto", "admin_level": 3, "country_code": "CA", "bbox": [-79.63940, 43.58371, -79.11626, 43.85565]},
        {"name": "London", "admin_level": 3, "country_code": "GB", "bbox": [-0.51037, 51.28676, 0.33401, 51.69187]},
        {"name": "Beijing", "admin_level": 3, "country_code": "CN", "bbox": [115.42361, 39.44226, 117.51413, 41.06075]},
        {"name": "Sydney", "admin_level": 3, "country_code": "AU", "bbox": [150.52066, -34.11821, 151.34319, -33.57802]},
    ]
    
    created_locations = {}
    for location_data in locations_data:
        request = CreateNodeRequest(
            node_type=NodeType.LOCATION,
            properties=location_data
        )
        location_id = await graph_service.create_node(request)
        created_locations[location_data["name"]] = location_id
        print(f"✅ Created location: {location_data['name']} (ID: {location_id})")
    
    return created_locations


async def create_location_relationships(locations: Dict[str, str]):
    """Create hierarchical relationships between locations"""
    relationships = [
        # States/provinces to countries
        ("California", "United States", RelationshipType.PART_OF),
        ("Texas", "United States", RelationshipType.PART_OF),
        ("New York", "United States", RelationshipType.PART_OF),
        ("Florida", "United States", RelationshipType.PART_OF),
        
        # Cities to countries/states
        ("New York City", "New York", RelationshipType.PART_OF),
        ("Los Angeles", "California", RelationshipType.PART_OF),
        ("Chicago", "United States", RelationshipType.PART_OF),
        ("Toronto", "Canada", RelationshipType.PART_OF),
        ("London", "United Kingdom", RelationshipType.PART_OF),
        ("Beijing", "China", RelationshipType.PART_OF),
        ("Sydney", "Australia", RelationshipType.PART_OF),
        
        # Adjacent relationships (simplified)
        ("United States", "Canada", RelationshipType.ADJACENT_TO),
        ("California", "Nevada", RelationshipType.ADJACENT_TO),
        ("New York", "New Jersey", RelationshipType.ADJACENT_TO),
    ]
    
    for start_name, end_name, rel_type in relationships:
        if start_name in locations and end_name in locations:
            request = CreateRelationshipRequest(
                start_node_id=locations[start_name],
                end_node_id=locations[end_name],
                relationship_type=rel_type
            )
            try:
                rel_id = await graph_service.create_relationship(request)
                print(f"✅ Created relationship: {start_name} -{rel_type.value}-> {end_name}")
            except Exception as e:
                print(f"⚠️ Failed to create relationship {start_name} -> {end_name}: {e}")


async def init_basic_concepts():
    """Initialize basic GIS and spatial concepts"""
    concepts_data = [
        {"name": "Geographic Information System", "category": "technology", 
         "synonyms": ["GIS", "geospatial system", "mapping system"]},
        {"name": "Population", "category": "demographic", 
         "synonyms": ["inhabitants", "residents", "people count"]},
        {"name": "Land Use", "category": "planning", 
         "synonyms": ["land cover", "zoning", "spatial planning"]},
        {"name": "Transportation", "category": "infrastructure", 
         "synonyms": ["transit", "mobility", "transport network"]},
        {"name": "Climate", "category": "environment", 
         "synonyms": ["weather patterns", "atmospheric conditions"]},
        {"name": "Urban Planning", "category": "planning", 
         "synonyms": ["city planning", "urban development", "spatial planning"]},
        {"name": "Natural Resources", "category": "environment", 
         "synonyms": ["resources", "environmental assets", "natural assets"]},
        {"name": "Demographics", "category": "social", 
         "synonyms": ["population statistics", "census data", "social data"]},
    ]
    
    created_concepts = {}
    for concept_data in concepts_data:
        request = CreateNodeRequest(
            node_type=NodeType.CONCEPT,
            properties=concept_data
        )
        concept_id = await graph_service.create_node(request)
        created_concepts[concept_data["name"]] = concept_id
        print(f"✅ Created concept: {concept_data['name']} (ID: {concept_id})")
    
    return created_concepts


async def init_sample_datasets():
    """Initialize sample datasets"""
    datasets_data = [
        {
            "name": "US Census Data 2020",
            "description": "Population and demographic data from US Census 2020",
            "source": "U.S. Census Bureau",
            "data_type": "vector",
            "crs": "EPSG:4326"
        },
        {
            "name": "World Administrative Boundaries",
            "description": "Country and administrative unit boundaries worldwide",
            "source": "Natural Earth",
            "data_type": "vector",
            "crs": "EPSG:4326"
        },
        {
            "name": "Global Land Cover",
            "description": "Satellite-based land cover classification",
            "source": "ESA",
            "data_type": "raster",
            "crs": "EPSG:4326"
        },
        {
            "name": "OpenStreetMap",
            "description": "Collaborative mapping data",
            "source": "OpenStreetMap Foundation",
            "data_type": "vector",
            "crs": "EPSG:4326"
        }
    ]
    
    created_datasets = {}
    for dataset_data in datasets_data:
        request = CreateNodeRequest(
            node_type=NodeType.DATASET,
            properties=dataset_data
        )
        dataset_id = await graph_service.create_node(request)
        created_datasets[dataset_data["name"]] = dataset_id
        print(f"✅ Created dataset: {dataset_data['name']} (ID: {dataset_id})")
    
    return created_datasets


async def create_concept_relationships(concepts: Dict[str, str]):
    """Create relationships between concepts"""
    concept_relationships = [
        ("Population", "Demographics", RelationshipType.RELATED_TO),
        ("Land Use", "Urban Planning", RelationshipType.RELATED_TO),
        ("Transportation", "Urban Planning", RelationshipType.RELATED_TO),
        ("Climate", "Natural Resources", RelationshipType.RELATED_TO),
        ("Demographics", "Urban Planning", RelationshipType.RELATED_TO),
    ]
    
    for start_name, end_name, rel_type in concept_relationships:
        if start_name in concepts and end_name in concepts:
            request = CreateRelationshipRequest(
                start_node_id=concepts[start_name],
                end_node_id=concepts[end_name],
                relationship_type=rel_type
            )
            try:
                await graph_service.create_relationship(request)
                print(f"✅ Created concept relationship: {start_name} -{rel_type.value}-> {end_name}")
            except Exception as e:
                print(f"⚠️ Failed to create concept relationship: {e}")


async def main():
    """Main initialization function"""
    print("🚀 Starting Neo4j knowledge graph initialization...")
    
    try:
        # Step 1: Create constraints and indexes
        print("\n📊 Creating constraints and indexes...")
        await create_constraints_and_indexes()
        
        # Step 2: Initialize locations
        print("\n🌍 Creating world locations...")
        locations = await init_world_locations()
        
        # Step 3: Create location relationships
        print("\n🔗 Creating location relationships...")
        await create_location_relationships(locations)
        
        # Step 4: Initialize concepts
        print("\n💡 Creating basic concepts...")
        concepts = await init_basic_concepts()
        
        # Step 5: Create concept relationships
        print("\n🔗 Creating concept relationships...")
        await create_concept_relationships(concepts)
        
        # Step 6: Initialize datasets
        print("\n📊 Creating sample datasets...")
        datasets = await init_sample_datasets()
        
        # Get final statistics
        print("\n📈 Getting final statistics...")
        stats = await graph_service.get_graph_stats()
        print(f"✅ Initialization complete!")
        print(f"   Total nodes: {stats['total_nodes']}")
        print(f"   Total relationships: {stats['total_relationships']}")
        print(f"   Node types: {dict(stats['nodes'])}")
        print(f"   Relationship types: {dict(stats['relationships'])}")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())