#!/usr/bin/env python3
"""
Test script for Neo4j integration
Run this to verify that Neo4j is properly integrated
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.services.graph_service import graph_service
from src.models.graph_models import NodeType, CreateNodeRequest


async def test_neo4j_connection():
    """Test basic Neo4j connection"""
    print("🔍 Testing Neo4j connection...")
    
    try:
        stats = await graph_service.get_graph_stats()
        print(f"✅ Neo4j connection successful!")
        print(f"   Total nodes: {stats['total_nodes']}")
        print(f"   Total relationships: {stats['total_relationships']}")
        return True
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False


async def test_create_node():
    """Test creating a node"""
    print("\n🔍 Testing node creation...")
    
    try:
        # Create a test location node
        request = CreateNodeRequest(
            node_type=NodeType.LOCATION,
            properties={
                "name": "Test Location",
                "country_code": "TEST",
                "admin_level": 0
            }
        )
        
        node_id = await graph_service.create_node(request)
        print(f"✅ Node created successfully with ID: {node_id}")
        
        # Retrieve the node to verify
        node = await graph_service.get_node(node_id)
        if node:
            print(f"✅ Node retrieved successfully: {node['name']}")
            
            # Clean up: delete the test node
            deleted = await graph_service.delete_node(node_id)
            if deleted:
                print("✅ Test node cleaned up successfully")
            
            return True
        else:
            print("❌ Failed to retrieve created node")
            return False
            
    except Exception as e:
        print(f"❌ Node creation test failed: {e}")
        return False


async def test_find_nodes():
    """Test finding nodes"""
    print("\n🔍 Testing node search...")
    
    try:
        # Search for location nodes
        locations = await graph_service.find_nodes_by_properties(
            properties={}, 
            labels=[NodeType.LOCATION.value]
        )
        
        print(f"✅ Found {len(locations)} location nodes")
        if locations:
            print(f"   Sample: {locations[0].get('name', 'Unnamed')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Node search test failed: {e}")
        return False


async def run_tests():
    """Run all tests"""
    print("🚀 Starting Neo4j integration tests...\n")
    
    tests = [
        test_neo4j_connection,
        test_create_node,
        test_find_nodes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Neo4j integration is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)