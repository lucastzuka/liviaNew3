#!/usr/bin/env python3
"""
Test script for Asana MCP functionality.
This script tests the basic Asana MCP operations to ensure they work correctly.
"""

import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_asana_mcp():
    """Test basic Asana MCP functionality."""
    
    try:
        # Import after environment is loaded
        from agent import create_asana_mcp_server
        
        logger.info("🧪 Testing Asana MCP Server...")
        
        # Create Asana MCP server
        asana_server = await create_asana_mcp_server()
        
        async with asana_server:
            logger.info("✅ Asana MCP Server created and connected")
            
            # Test 1: List all available tools
            logger.info("🔍 Test 1: Listing all available tools...")
            tools = await asana_server.list_tools()
            logger.info(f"📋 Available tools ({len(tools)}):")
            for i, tool in enumerate(tools, 1):
                logger.info(f"  {i}. {tool.name} - {tool.description[:100]}...")

            # Test 2: List workspaces
            logger.info("🔍 Test 2: Listing workspaces...")
            workspace_tool = next((t for t in tools if t.name == "asana_list_workspaces"), None)
            
            if workspace_tool:
                result = await asana_server.call_tool("asana_list_workspaces", {})
                logger.info(f"✅ Workspaces found: {len(result.content) if hasattr(result, 'content') else 'Unknown'}")
                print(f"Workspaces result: {result}")
            else:
                logger.error("❌ asana_list_workspaces tool not found")
            
            # Test 2: Search projects
            logger.info("🔍 Test 2: Searching projects...")
            project_tool = next((t for t in tools if t.name == "asana_search_projects"), None)
            
            if project_tool:
                # Use the known workspace ID
                result = await asana_server.call_tool("asana_search_projects", {
                    "workspace": "1200537647127763",
                    "name_pattern": ".*"  # Match all projects
                })
                logger.info(f"✅ Projects search completed")
                print(f"Projects result: {result}")
            else:
                logger.error("❌ asana_search_projects tool not found")
            
            # Test 3: Search specific project (ELECTROLUX)
            logger.info("🔍 Test 3: Searching ELECTROLUX project...")
            if project_tool:
                result = await asana_server.call_tool("asana_search_projects", {
                    "workspace": "1200537647127763",
                    "name_pattern": ".*ELECTROLUX.*BR.*"  # Match ELECTROLUX (BR)
                })
                logger.info(f"✅ ELECTROLUX project search completed")
                print(f"ELECTROLUX project result: {result}")

                # Extract project GID if found
                if hasattr(result, 'content') and result.content:
                    # Try to find project GID from result
                    logger.info("Found ELECTROLUX project, will test task search...")

            # Test 4: Search tasks with proper filters
            logger.info("🔍 Test 4: Searching tasks with filters...")
            task_tool = next((t for t in tools if t.name == "asana_search_tasks"), None)

            if task_tool:
                # Search with text filter to avoid "must specify at least one search filter" error
                result = await asana_server.call_tool("asana_search_tasks", {
                    "workspace": "1200537647127763",
                    "text": "task",  # Add text filter
                    "completed": False,  # Add completed filter
                    "opt_fields": "gid,name,assignee,completed,due_on"
                })
                logger.info(f"✅ Tasks search completed")
                print(f"Tasks result: {result}")
            else:
                logger.error("❌ asana_search_tasks tool not found")
            
            logger.info("🎉 All tests completed!")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

async def main():
    """Main test function."""
    logger.info("🚀 Starting Asana MCP Tests...")

    # Set the token directly for testing (same as in agent.py)
    os.environ["ASANA_ACCESS_TOKEN"] = "2/1203422181648476/1210469533636732:cb4cc6cfe7871e7d0363b5e2061765d3"

    await test_asana_mcp()
    logger.info("✅ Test session completed")

if __name__ == "__main__":
    asyncio.run(main())
