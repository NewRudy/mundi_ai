"""
Test script for Knowledge Graph API endpoints
Run with: python test_kg_api.py
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.kg_init import init_neo4j_constraints_and_indexes, get_neo4j_schema_info
from src.services.kg_config_service import list_kg_configs, read_kg_config
from src.services.graph_service import graph_service
from src.services.kg_minimal import apply_ontology_json, apply_config_yaml


async def test_schema_init():
    """Test Neo4j schema initialization"""
    print("\n=== Testing Schema Initialization ===")
    try:
        result = await init_neo4j_constraints_and_indexes()
        print(f"✓ Constraints created: {len(result['constraints_created'])}")
        print(f"✓ Indexes created: {len(result['indexes_created'])}")
        if result['errors']:
            print(f"⚠ Errors: {result['errors']}")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def test_schema_info():
    """Test getting schema info"""
    print("\n=== Testing Schema Info ===")
    try:
        info = await get_neo4j_schema_info()
        print(f"✓ Labels: {info['labels']}")
        print(f"✓ Relationship types: {info['relationship_types']}")
        print(f"✓ Constraints: {len(info['constraints'])}")
        print(f"✓ Indexes: {len(info['indexes'])}")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def test_list_configs():
    """Test listing configuration files"""
    print("\n=== Testing Config Listing ===")
    try:
        result = await list_kg_configs()
        print(f"✓ Found {result['total']} config files")
        if result['items']:
            print(f"  Sample files:")
            for item in result['items'][:3]:
                print(f"  - {item['rel_path']} ({item['type']}, {item['size_bytes']} bytes)")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def test_read_config():
    """Test reading a config file"""
    print("\n=== Testing Config Reading ===")
    try:
        # Try to read the ontology JSON
        result = await read_kg_config("电站时空知识图谱.json")
        print(f"✓ Read file: {result['name']}")
        print(f"  Type: {result['type']}")
        if result['content']:
            content = result['content']
            if isinstance(content, dict):
                print(f"  Root keys: {list(content.keys())}")
    except FileNotFoundError:
        print("⚠ Ontology JSON file not found")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def test_graph_stats():
    """Test getting graph statistics"""
    print("\n=== Testing Graph Stats ===")
    try:
        stats = await graph_service.get_graph_stats()
        print(f"✓ Total nodes: {stats['total_nodes']}")
        print(f"✓ Total relationships: {stats['total_relationships']}")
        if stats['nodes']:
            print(f"  Node counts by label:")
            for label, count in sorted(stats['nodes'].items()):
                print(f"    {label}: {count}")
        if stats['relationships']:
            print(f"  Relationship counts by type:")
            for rel_type, count in sorted(stats['relationships'].items()):
                print(f"    {rel_type}: {count}")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def test_search_nodes():
    """Test node search"""
    print("\n=== Testing Node Search ===")
    try:
        result = await graph_service.search_nodes(
            labels=["Ontology"],
            limit=5
        )
        print(f"✓ Found {len(result['nodes'])} nodes")
        print(f"  Total: {result['page']['total']}, Has more: {result['page']['has_more']}")
        if result['nodes']:
            print(f"  Sample nodes:")
            for node in result['nodes'][:3]:
                print(f"    - {node.get('name', 'N/A')} ({node.get('id')})")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def test_extract_subgraph():
    """Test subgraph extraction"""
    print("\n=== Testing Subgraph Extraction ===")
    try:
        # First find a node to use as root
        search_result = await graph_service.search_nodes(labels=["Ontology"], limit=1)
        if not search_result['nodes']:
            print("⚠ No Ontology nodes found to test subgraph extraction")
            return
        
        root_node = search_result['nodes'][0]
        root_id = root_node['id']
        print(f"  Using root node: {root_node.get('name')} ({root_id})")
        
        result = await graph_service.extract_subgraph(
            root_id=root_id,
            depth=2,
            limit=10
        )
        print(f"✓ Extracted subgraph:")
        print(f"  Nodes: {result['meta']['node_count']}")
        print(f"  Relationships: {result['meta']['relationship_count']}")
        print(f"  Depth: {result['meta']['depth']}")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Knowledge Graph API Tests")
    print("=" * 60)
    
    await test_schema_init()
    await test_schema_info()
    await test_list_configs()
    await test_read_config()
    await test_graph_stats()
    await test_search_nodes()
    await test_extract_subgraph()
    
    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
