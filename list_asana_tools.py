#!/usr/bin/env python3
"""
Simple script to list all available Asana MCP tools.
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

async def list_tools():
    """List all available Asana MCP tools."""
    
    try:
        # Import after environment is loaded
        from agent import create_asana_mcp_server
        
        logger.info("🔧 Listing Asana MCP Tools...")
        
        # Set the token directly
        os.environ["ASANA_ACCESS_TOKEN"] = "2/1203422181648476/1210469533636732:cb4cc6cfe7871e7d0363b5e2061765d3"
        
        # Create Asana MCP server
        asana_server = await create_asana_mcp_server()
        
        async with asana_server:
            logger.info("✅ Connected to Asana MCP Server")
            
            # List all tools
            tools = await asana_server.list_tools()
            logger.info(f"📋 Found {len(tools)} tools:")
            
            for i, tool in enumerate(tools, 1):
                print(f"\n{i}. {tool.name}")
                print(f"   Description: {tool.description}")
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    print(f"   Parameters: {list(tool.inputSchema.get('properties', {}).keys())}")
            
            # Look for project-related tools
            project_tools = [t for t in tools if 'project' in t.name.lower()]
            print(f"\n🏗️ Project-related tools ({len(project_tools)}):")
            for tool in project_tools:
                print(f"   - {tool.name}")
            
            # Look for task-related tools
            task_tools = [t for t in tools if 'task' in t.name.lower()]
            print(f"\n📋 Task-related tools ({len(task_tools)}):")
            for tool in task_tools:
                print(f"   - {tool.name}")
            
    except Exception as e:
        logger.error(f"❌ Failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(list_tools())
