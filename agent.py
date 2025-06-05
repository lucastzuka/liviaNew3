#!/usr/bin/env python3
"""
Livia - Slack Chatbot Agent Definition
--------------------------------------
Defines Livia, an intelligent chatbot agent for Slack using OpenAI Agents SDK and API Responses.
Responds only in threads that mention the bot in the first message.
Includes tools: file_search, web_search, image vision, and MCP tools.
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# OpenAI Agents SDK components
from agents import Agent, Runner, gen_trace_id, trace, WebSearchTool
from agents.mcp import MCPServerStdio

# Load environment variables from .env file
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_asana_mcp_server() -> MCPServerStdio:
    """Creates and returns an Asana MCP Server instance using @roychri/mcp-server-asana with token authentication."""

    logger.info("Creating Asana MCP Server connection with token authentication...")

    asana_command = "npx"
    asana_args = ["-y", "@roychri/mcp-server-asana"]
    asana_token = "2/1203422181648476/1210469533636732:cb4cc6cfe7871e7d0363b5e2061765d3"

    logger.info(f"Starting Asana MCP Server with command: {asana_command} {' '.join(asana_args)}")

    asana_server = MCPServerStdio(
        name="Asana MCP Server",
        params={
            "command": asana_command,
            "args": asana_args,
            "env": {
                **os.environ,
                "ASANA_ACCESS_TOKEN": asana_token
            },
        },
    )
    logger.info("Asana MCP Server instance created with token authentication.")
    return asana_server


async def create_slack_mcp_server() -> MCPServerStdio:
    """Creates and returns a Slack MCP Server instance using MCPServerStdio."""

    if "SLACK_BOT_TOKEN" not in os.environ:
        raise ValueError("SLACK_BOT_TOKEN environment variable is not set for MCP Server")
    if "SLACK_TEAM_ID" not in os.environ:
        raise ValueError("SLACK_TEAM_ID environment variable is not set for MCP Server")

    slack_command = "npx -y @modelcontextprotocol/server-slack"
    logger.info(f"Attempting to start Slack MCP Server with command: {slack_command}")

    slack_server = MCPServerStdio(
        name="Slack MCP Server",
        params={
            "command": slack_command.split(" ")[0],
            "args": slack_command.split(" ")[1:],
            "env": {
                "SLACK_BOT_TOKEN": os.environ["SLACK_BOT_TOKEN"],
                "SLACK_TEAM_ID": os.environ["SLACK_TEAM_ID"],
            },
        },
    )
    logger.info("MCPServerStdio instance for Slack created.")
    return slack_server


async def create_agent(slack_server: MCPServerStdio, asana_server: MCPServerStdio = None) -> Agent:
    """Creates and returns Livia, an OpenAI Agent configured to use the Slack MCP server and tools."""

    logger.info("Creating Livia - the Slack Chatbot Agent...")

    web_search_tool = WebSearchTool(search_context_size="medium")

    mcp_servers = [slack_server]
    server_descriptions = [f"'{slack_server.name}'"]

    if asana_server:
        mcp_servers.append(asana_server)
        server_descriptions.append(f"'{asana_server.name}'")



    asana_tools_description = ""
    zapier_tools_description = ""

    if asana_server:
        asana_tools_description = (
            "📋 **Asana Tools** (via MCP Server):\n"
            "  - List workspaces and projects\n"
            "  - Search tasks with proper filters (always include text, completed status, or project filters)\n"
            "  - Get specific tasks by ID\n"
            "  - Create and manage tasks\n"
            "  - Update task status and assignments\n"
            "  - Get project sections and task counts\n"
            "  - Manage team collaboration\n\n"
            "**Important Asana Search Guidelines:**\n"
            "  - ALWAYS use workspace ID '1200537647127763' (never use workspace name)\n"
            "  - ALWAYS use asana_search_projects first to find relevant projects and get their GIDs\n"
            "  - When searching tasks, ALWAYS include completed=false AND text='' (empty string is valid)\n"
            "  - Use specific project GIDs (not names) when searching tasks\n"
            "  - For project-specific tasks, use 'projects' filter with project GID + completed + text filters\n"
            "  - For user tasks, search within specific projects rather than workspace-wide\n"
            "  - CRITICAL: API requires completed + text filters even when using projects filter\n"
            "  - Known workspace: 'ℓiⱴε - The Culture-Driven Agency' (ID: 1200537647127763)\n"
            "  - User lucas.vieira@live.tt has ID: 1203422181694687\n"
            "  - WORKFLOW: 1) Find project GID → 2) Search tasks using project GID + filters\n"
            "  - IMPORTANT: Project names have prefixes like '1. ELECTROLUX (BR)', use regex patterns like '.*ELECTROLUX.*BR.*'\n"
            "  - CORRECT EXAMPLE: asana_search_tasks(workspace='1200537647127763', projects=['1204965509777978'], completed=false, text='', limit=5)\n"
            "  - ALTERNATIVE: Use asana_get_project(project_id='1204965509777978') to get project details first\n"
            "  - NEVER use projects_any - always use projects=['project_id'] as array\n"
        )

    zapier_tools_description = (
        "⚡ **Zapier Automation Tools** (ATIVO via Remote MCP):\n"
        "  - ✅ Google Drive: buscar, listar, criar e gerenciar arquivos e pastas\n"
        "  - ✅ Gmail: enviar emails e gerenciar mensagens\n"
        "**Comandos Zapier:**\n"
        "  - 'buscar arquivos no drive', 'listar documentos', 'criar pasta'\n"
        "  - 'procurar pasta', 'encontrar arquivo', 'buscar no google drive'\n"
        "  - 'enviar email', 'criar página no notion', 'adicionar card no trello'\n"
        "  - Use palavras-chave como 'drive', 'gmail', 'automation' para ativar\n"
        "**Dicas para busca no Google Drive:**\n"
        "  - Para arquivos: use 'buscar arquivo [nome]' ou 'encontrar arquivo [nome]'\n"
        "  - Para pastas: use 'procurar pasta [nome]' ou 'buscar pasta [nome]'\n"
        "  - IMPORTANTE: TargetGroupIndex_BR2024 é um ARQUIVO, não pasta\n"
        "  - Se não encontrar, tente busca parcial: 'TargetGroup' pode encontrar 'TargetGroupIndex_BR2024'\n"
        "  - Use termos específicos e considere sufixos como _BR2024, _2024, etc.\n"
        "  - Se busca exata falhar, sugira ao usuário tentar termos parciais\n"
        "  - Sempre especifique se está buscando arquivo ou pasta\n"
    )

    agent = Agent(
        name="Livia",
        instructions=(
            "You are Livia, an intelligent chatbot assistant for Slack. "
            "IMPORTANT: You should ONLY respond in threads where the bot was mentioned in the FIRST message of the thread. "
            "You have access to multiple powerful tools:\n\n"
            "🔍 **Web Search Tool**: Search the internet for current information, news, facts, and answers\n"
            "👁️ **Image Vision**: Analyze and describe images uploaded to Slack or provided via URLs\n"
            f"{asana_tools_description}"
            f"{zapier_tools_description}"
            "📱 **Slack Tools** (via MCP Server):\n"
            "  - List channels and users\n"
            "  - Post messages and reply to threads\n"
            "  - Add reactions to messages\n"
            "  - Get channel history and user information\n\n"
            "**Guidelines:**\n"
            "- Use web search when you need current information, recent news, or facts you don't know\n"
            "- When users upload images or send image URLs, analyze them and provide detailed descriptions\n"
            "- For images, describe what you see including objects, people, text, colors, and context\n"
            "- For Google Drive searches: try multiple search strategies if first attempt fails\n"
            "- When searching for folders/files, try partial names, different cases, and related terms\n"
            "- If a search returns no results, suggest alternative search terms or approaches\n"
            "- IMPORTANT: If user searches for 'TargetGroup', it's likely the file 'TargetGroupIndex_BR2024'\n"
            "- Consider that file names may have suffixes like _BR2024, _2024, etc.\n"
            "- Always offer to try broader or more specific search terms when initial search fails\n"
            "- When user says 'pasta' but means 'arquivo', correct and search for files instead\n"
            f"{'- For Asana: ALWAYS use workspace ID 1200537647127763, NEVER use workspace name' if asana_server else ''}\n"
            f"{'- For Asana workflow: 1) Search projects to get GID → 2) Search tasks using project GID + MANDATORY filters' if asana_server else ''}\n"
            f"{'- When searching tasks: ALWAYS include completed=false AND text=\"\" (empty text is valid filter)' if asana_server else ''}\n"
            f"{'- MANDATORY: asana_search_tasks requires completed + text filters, even if text is empty string' if asana_server else ''}\n"
            f"{'- When users ask for \"my tasks\", use assignee filter with user ID 1203422181694687' if asana_server else ''}\n"
            f"{'- NEVER use projects_any or assignee_any - use projects=[\"project_id\"] as array instead' if asana_server else ''}\n"
            f"{'- CRITICAL: projects parameter must be array like [\"1204965509777978\"], not string' if asana_server else ''}\n"
            "- Be helpful, concise, and professional in your responses\n"
            "- Ask for clarification if needed\n"
            "- Always cite sources when providing information from web searches\n"
            "- You can help with general questions, provide information, and assist with Slack-related tasks"
        ),
        model="gpt-4.1-mini",
        tools=[web_search_tool],
        mcp_servers=mcp_servers,
    )
    servers_info = " and ".join(server_descriptions)
    logger.info(f"Agent '{agent.name}' created with WebSearchTool and access to {servers_info}.")
    return agent


async def process_message_with_zapier(message: str, image_urls: Optional[List[str]] = None) -> str:
    """Process message using OpenAI Responses API with Zapier Remote MCP."""
    from openai import OpenAI

    client = OpenAI()

    if image_urls:
        input_content = [{"type": "input_text", "text": message}]
        for image_url in image_urls:
            input_content.append({
                "type": "input_image",
                "image_url": image_url,
                "detail": "low"
            })
        input_data = input_content
    else:
        input_data = message

    ZAPIER_MCP_URL = "https://mcp.zapier.com/api/mcp/s/196901ca-f828-4a37-ba99-383e7a618534/mcp"
    ZAPIER_MCP_TOKEN = "MTk2OTAxY2EtZjgyOC00YTM3LWJhOTktMzgzZTdhNjE4NTM0OjJkOWQ0MTFiLTk0YjktNDMyMi1hNTEwLTI4NjRiMmY1NWE0MQ=="
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=input_data,
        tools=[
            {
                "type": "mcp",
                "server_label": "zapier-gdrive",
                "server_url": ZAPIER_MCP_URL,
                "require_approval": "never",
                "headers": {
                    "Authorization": f"Bearer {ZAPIER_MCP_TOKEN}"
                }
            }
        ]
    )

    return response.output_text or "No response generated."

async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None) -> str:
    """Runs the agent with the given message and optional image URLs, returns the final output."""

    zapier_keywords = ["zapier", "google drive", "gmail", "notion", "trello", "automation", "workflow", "integrate", "drive", "arquivo", "pasta", "documento"]
    needs_zapier = any(keyword in message.lower() for keyword in zapier_keywords)

    if needs_zapier:
        logger.info("Message requires Zapier tools, using Responses API with Remote MCP")
        try:
            return await process_message_with_zapier(message, image_urls)
        except Exception as e:
            logger.warning(f"Zapier MCP failed, falling back to regular agent: {e}")

    # Generate a trace ID for monitoring the agent's execution flow
    trace_id = gen_trace_id()
    logger.info(f"Starting agent run for message: '{message}'. Trace: https://platform.openai.com/traces/{trace_id}")

    if image_urls:
        logger.info(f"Processing {len(image_urls)} image(s): {image_urls}")

    final_output = "Sorry, I couldn't process that." # Default response
    try:
        # Start tracing for the agent workflow
        with trace(workflow_name="Livia Slack Agent Workflow", trace_id=trace_id):
            # Prepare input with images if provided
            if image_urls:
                # Create input with both text and images for vision processing
                input_content = [
                    {"type": "input_text", "text": message}
                ]

                # Add each image to the input
                for image_url in image_urls:
                    input_content.append({
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "low"  # Use low detail for cost efficiency
                    })

                input_data = [{
                    "role": "user",
                    "content": input_content
                }]
            else:
                # Text-only input
                input_data = message

            # Execute the agent with the input message
            # Runner.run handles the interaction loop between the LLM and tools (MCP server)
            result = await Runner.run(starting_agent=agent, input=input_data)
            final_output = result.final_output if result else "No response generated."
            logger.info(f"Agent run completed. Final output: '{final_output}'")

    except Exception as e:
        logger.error(f"Error during agent run (trace_id: {trace_id}): {e}", exc_info=True)
        final_output = f"An error occurred while processing your request: {str(e)}"

    # Ensure the output is a string
    return str(final_output)

# Standalone execution part (optional for the article, but good for context)
# async def main_standalone(): ...
# if __name__ == "__main__": ...