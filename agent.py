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
# For detailed agent logs, uncomment:
# logging.getLogger("openai.agents").setLevel(logging.DEBUG)


async def create_asana_mcp_server() -> MCPServerStdio:
    """Creates and returns an Asana MCP Server instance using @roychri/mcp-server-asana with token authentication."""

    logger.info("Creating Asana MCP Server connection with token authentication...")

    # Use the @roychri/mcp-server-asana package which accepts direct token authentication
    # This avoids OAuth issues and "unusual activity" blocks
    asana_command = "npx"
    asana_args = ["-y", "@roychri/mcp-server-asana"]

    # Your Asana access token
    asana_token = "2/1203422181648476/1210469533636732:cb4cc6cfe7871e7d0363b5e2061765d3"

    logger.info(f"Starting Asana MCP Server with command: {asana_command} {' '.join(asana_args)}")

    # Initialize the Asana MCP Server connection via Standard I/O
    asana_server = MCPServerStdio(
        name="Asana MCP Server",
        params={
            "command": asana_command,
            "args": asana_args,
            "env": {
                # Pass the token directly as environment variable
                **os.environ,
                "ASANA_ACCESS_TOKEN": asana_token
            },
        },
    )
    logger.info("Asana MCP Server instance created with token authentication.")
    return asana_server

async def create_slack_mcp_server() -> MCPServerStdio:
    """Creates and returns a Slack MCP Server instance using MCPServerStdio."""

    # Verify required environment variables for the MCP server
    if "SLACK_BOT_TOKEN" not in os.environ:
        raise ValueError("SLACK_BOT_TOKEN environment variable is not set for MCP Server")
    if "SLACK_TEAM_ID" not in os.environ:
        raise ValueError("SLACK_TEAM_ID environment variable is not set for MCP Server")

    # Command to run the Slack MCP server via npx
    # Ensures the latest version is used without global installation
    slack_command = "npx -y @modelcontextprotocol/server-slack"
    logger.info(f"Attempting to start Slack MCP Server with command: {slack_command}")

    # Initialize the MCP Server connection via Standard I/O
    slack_server = MCPServerStdio(
        name="Slack MCP Server",
        params={
            "command": slack_command.split(" ")[0], # "npx"
            "args": slack_command.split(" ")[1:],  # ["-y", "@modelcontextprotocol/server-slack"]
            "env": {
                # Pass necessary tokens/IDs to the MCP server process environment
                "SLACK_BOT_TOKEN": os.environ["SLACK_BOT_TOKEN"],
                "SLACK_TEAM_ID": os.environ["SLACK_TEAM_ID"],
                # Optional: Limit accessible channels for the MCP server
                # "SLACK_CHANNEL_IDS": "Cxxxx,Cyyyy",
            },
        },
    )
    logger.info("MCPServerStdio instance for Slack created.")
    return slack_server


async def create_agent(slack_server: MCPServerStdio, asana_server: MCPServerStdio = None) -> Agent:
    """Creates and returns Livia, an OpenAI Agent configured to use the Slack MCP server and tools."""

    logger.info("Creating Livia - the Slack Chatbot Agent...")

    # Create WebSearchTool for internet searches
    web_search_tool = WebSearchTool(
        search_context_size="medium"  # Options: "low", "medium", "high"
    )

    # Prepare MCP servers list
    mcp_servers = [slack_server]
    server_descriptions = [f"'{slack_server.name}'"]

    # Add Asana server if available
    if asana_server:
        mcp_servers.append(asana_server)
        server_descriptions.append(f"'{asana_server.name}'")

    # Build instructions with available tools
    asana_tools_description = ""
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

    agent = Agent(
        name="Livia",
        # Instructions guiding the agent on how to behave and use tools
        instructions=(
            "You are Livia, an intelligent chatbot assistant for Slack. "
            "IMPORTANT: You should ONLY respond in threads where the bot was mentioned in the FIRST message of the thread. "
            "You have access to multiple powerful tools:\n\n"
            "🔍 **Web Search Tool**: Search the internet for current information, news, facts, and answers\n"
            "👁️ **Image Vision**: Analyze and describe images uploaded to Slack or provided via URLs\n"
            f"{asana_tools_description}"
            "📱 **Slack Tools** (via MCP Server):\n"
            "  - List channels and users\n"
            "  - Post messages and reply to threads\n"
            "  - Add reactions to messages\n"
            "  - Get channel history and user information\n\n"
            "**Guidelines:**\n"
            "- Use web search when you need current information, recent news, or facts you don't know\n"
            "- When users upload images or send image URLs, analyze them and provide detailed descriptions\n"
            "- For images, describe what you see including objects, people, text, colors, and context\n"
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
        # Specify the model to use - gpt-4.1-mini for cost efficiency with vision support
        model="gpt-4.1-mini",
        # List of tools the agent can use
        tools=[web_search_tool],
        # List of MCP servers the agent can use
        mcp_servers=mcp_servers,
    )
    servers_info = " and ".join(server_descriptions)
    logger.info(f"Agent '{agent.name}' created with WebSearchTool and access to {servers_info}.")
    return agent


async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None) -> str:
    """Runs the agent with the given message and optional image URLs, returns the final output."""

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