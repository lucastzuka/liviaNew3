#!/usr/bin/env python3
"""
Livia Agent Creator
------------------
Funções para criação e configuração do agente Livia.
Inclui versões com e sem MCP servers.
"""

import logging
from typing import List, Optional

from agents import Agent, WebSearchTool, FileSearchTool

try:
    from agents.mcp.server import MCPServerSse, MCPServerSseParams
    MCP_SERVER_AVAILABLE = True
except ImportError:
    MCP_SERVER_AVAILABLE = False
    MCPServerSse = None
    MCPServerSseParams = None

from .config import (
    MCP_AVAILABLE,
    ZAPIER_MCPS,
    get_agent_instructions,
    generate_zapier_tools_description,
    generate_enhanced_zapier_tools_description
)
# from tools.thinking_agent import get_thinking_tool  # Removido para evitar chamadas automáticas

logger = logging.getLogger(__name__)


async def create_agent_with_mcp_servers() -> Agent:
    """Create and configure the main Livia agent with MCP servers from OpenAI Agents SDK."""

    if not MCP_AVAILABLE or not MCP_SERVER_AVAILABLE:
        logger.warning("MCP not available - falling back to hybrid architecture")
        return await create_agent()

    try:
        logger.info("Creating Livia - the Slack Chatbot Agent with MCP servers...")

        # Initialize core tools
        web_search_tool = WebSearchTool(search_context_size="medium")

        # Configure file search with vector store for document retrieval
        # TEMPORARIAMENTE DESABILITADO - usando vector stores efêmeros por arquivo
        # file_search_tool = FileSearchTool(
        #     vector_store_ids=["vs_683e3a1ac4808191ae5e6fe24392e609"],
        #     max_num_results=5,
        #     include_search_results=True
        # )

        # Create MCP servers for all Zapier MCPs
        mcp_servers = []
        for mcp_key, mcp_config in ZAPIER_MCPS.items():
            try:
                # Create MCPServerSse for remote Zapier MCP servers using TypedDict params
                params: MCPServerSseParams = {
                    "url": mcp_config["url"],
                    "headers": {"Authorization": f"Bearer {mcp_config['api_key'].strip()}"},
                    "timeout": 30.0,  # 30 seconds timeout
                    "sse_read_timeout": 300.0  # 5 minutes SSE read timeout
                }

                mcp_server = MCPServerSse(
                    params=params,
                    cache_tools_list=True,  # Cache tools for better performance
                    name=mcp_config["server_label"]
                )

                # Connect to the MCP server
                logger.info(f"Connecting to {mcp_config['name']}...")
                await mcp_server.connect()
                logger.info(f"Connected to {mcp_config['name']}")

                mcp_servers.append(mcp_server)
                logger.info(f"Created MCPServerSse for {mcp_config['name']}")
            except Exception as e:
                # Suppress MCP initialization errors from terminal output
                import logging
                mcp_logger = logging.getLogger('openai.agents')
                mcp_logger.setLevel(logging.CRITICAL)
                # Silently skip failed MCP connections to keep logs clean
                # Continue with other servers
                pass

        # Core tools
        core_tools = [web_search_tool]  # file_search_tool temporariamente removido

        # Generate dynamic Zapier tools description from configuration
        zapier_tools_description = generate_zapier_tools_description()

        logger.info(f"Configured {len(mcp_servers)} MCP servers for Zapier MCPs")

        # If no MCP servers connected successfully, fall back to hybrid architecture
        if len(mcp_servers) == 0:
            logger.warning("No MCP servers connected successfully - falling back to hybrid architecture")
            return await create_agent()

        # Create agent with MCP servers
        agent = Agent(
            name="Livia",
            model="gpt-4.1-mini",  # Default model for text processing
            tools=core_tools,  # Core tools: web search, file search
            mcp_servers=mcp_servers,  # MCP servers will provide additional tools automatically
            instructions=get_agent_instructions(zapier_tools_description)
        )

        logger.info(f"Agent '{agent.name}' created with {len(core_tools)} core tools + {len(mcp_servers)} MCP servers")
        return agent

    except Exception as e:
        logger.error(f"Failed to create agent with MCP servers: {e}")
        logger.info("Falling back to hybrid architecture")
        return await create_agent()


async def create_agent() -> Agent:
    """Create and configure the main Livia agent with all tools and instructions (legacy hybrid version)."""

    logger.info("Creating Livia - the Slack Chatbot Agent...")

    # Initialize core tools
    web_search_tool = WebSearchTool(search_context_size="medium")


    # Configure file search with vector store for document retrieval
    # TEMPORARIAMENTE DESABILITADO - usando vector stores efêmeros por arquivo
    # file_search_tool = FileSearchTool(
    #     vector_store_ids=["vs_683e3a1ac4808191ae5e6fe24392e609"],
    #     max_num_results=5,
    #     include_search_results=True
    # )

    # MCP servers list (local MCPs only - Zapier MCPs via Responses API with enhanced multi-turn)
    mcp_servers = []
    server_descriptions = []

    logger.info("Using hybrid architecture: Agents SDK for local tools + enhanced Responses API for Zapier MCPs")
    logger.info("Enhanced Responses API now includes manual multi-turn execution for complex workflows")

    # Generate dynamic Zapier tools description from configuration
    zapier_tools_description = generate_enhanced_zapier_tools_description()

    logger.info(f"Configured hybrid architecture with enhanced multi-turn for {len(ZAPIER_MCPS)} Zapier MCPs")

    # Slack communication handled directly via API (no MCP tools needed)

    agent = Agent(
        name="Livia",
        instructions=get_agent_instructions(zapier_tools_description),
        model="gpt-4.1-mini",  # Default model for text processing
        tools=[web_search_tool],  # file_search_tool temporariamente removido, CodeInterpreterTool temporarily disabled
        mcp_servers=mcp_servers,
    )
    servers_info = " and ".join(server_descriptions)
    logger.info(f"Agent '{agent.name}' created with WebSearchTool and access to {servers_info}.")
    return agent


async def create_agent_with_vector_store(vector_store_id: str):
    """Cria um agente com uma vector store específica para documentos do usuário."""
    try:
        logger.info(f"Creating agent with custom vector store: {vector_store_id}")

        # Initialize core tools
        web_search_tool = WebSearchTool(search_context_size="medium")

        # Configure file search with the new vector store
        file_search_tool = FileSearchTool(
            vector_store_ids=[vector_store_id],  # Use the new vector store
            max_num_results=5,
            include_search_results=True
        )

        # Core tools
        core_tools = [web_search_tool, file_search_tool]

        # Generate dynamic Zapier tools description from configuration
        zapier_tools_description = generate_enhanced_zapier_tools_description()

        # Create agent with updated tools
        agent = Agent(
            name="Livia",
            model="gpt-4o-mini",
            instructions=get_agent_instructions(zapier_tools_description),
            tools=core_tools,
            mcp_servers=[]
        )

        logger.info(f"Agent updated successfully with vector store: {vector_store_id}")
        return agent

    except Exception as e:
        logger.error(f"Error creating agent with vector store: {e}")
        return None
