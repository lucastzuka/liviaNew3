#!/usr/bin/env python3
"""
Debug Asana search to understand why wrong tasks are returned
-----------------------------------------------------------
"""

import asyncio
import logging
from agent import create_asana_mcp_server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_asana():
    """Debug Asana project and task search."""
    
    try:
        logger.info("🔍 Debugging Asana search...")
        
        # Create Asana MCP server
        asana_server = await create_asana_mcp_server()
        logger.info("✅ Asana MCP server created")
        
        # Test workspace listing
        logger.info("\n📋 Testing workspace listing...")
        
        # Test project search
        logger.info("\n🔍 Searching for 'Pauta Inovação' projects...")
        
        # Test task search in the project
        logger.info("\n📝 Searching for tasks in project...")
        
        logger.info("🏁 Debug completed!")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_asana())
