#!/usr/bin/env python3
"""
Livia - Slack Chatbot Agent Definition
--------------------------------------
Defines Livia, an intelligent chatbot agent for Slack using OpenAI Agents SDK and API Responses.
Responds only in threads that mention the bot in the first message.
Includes tools: file_search, web_search, image vision, and MCP tools.
"""

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


# ===== ZAPIER MCP CONFIGURATION =====
# Centralized configuration for all Zapier MCP integrations
ZAPIER_MCPS = {
    "asana": {
        "name": "Zapier Asana MCP",
        "server_label": "zapier-asana",
        "url": "https://mcp.zapier.com/api/mcp/s/867dc3af-2aa3-45f0-b872-61f08060faa2/mcp",
        "token": "ODY3ZGMzYWYtMmFhMy00NWYwLWI4NzItNjFmMDgwNjBmYWEyOjZhOGQ3YzRmLWRhZTQtNGRmMS1iY2JlLWJkNjJhM2MwM2YxYw==",
        "keywords": ["asana"],
        "description": "📋 **Asana**: gerenciar projetos, tarefas e workspaces"
    },
    "google_drive": {
        "name": "Zapier Google Drive MCP",
        "server_label": "zapier-gdrive",
        "url": "https://mcp.zapier.com/api/mcp/s/196901ca-f828-4a37-ba99-383e7a618534/mcp",
        "token": "MTk2OTAxY2EtZjgyOC00YTM3LWJhOTktMzgzZTdhNjE4NTM0OjJkOWQ0MTFiLTk0YjktNDMyMi1hNTEwLTI4NjRiMmY1NWE0MQ==",
        "keywords": ["google", "drive"],
        "description": "📁 **Google Drive**: buscar, listar, criar e gerenciar arquivos e pastas"
    },
    "everhour": {
        "name": "Zapier Everhour MCP",
        "server_label": "zapier-everhour",
        "url": "https://mcp.zapier.com/api/mcp/s/66bdad6b-b992-46ae-8682-908de2721485/mcp",
        "token": "NjZiZGFkNmItYjk5Mi00NmFlLTg2ODItOTA4ZGUyNzIxNDg1OmY5NjA0MzQzLTRjNjEtNGQ3Yy05MGIzLTk1MDE3MWZlM2FiNw==",
        "keywords": ["everhour", "tempo", "time", "horas", "timesheet"],
        "description": "⏰ **Everhour**: controle de tempo, timesheet e rastreamento de horas"
    },
    "google_docs": {
        "name": "Zapier Google Docs MCP",
        "server_label": "zapier-gdocs",
        "url": "https://mcp.zapier.com/api/mcp/s/efb9e233-c3e3-4dff-9ac0-b77be2ee0d98/mcp",
        "token": "ZWZiOWUyMzMtYzNlMy00ZGZmLTlhYzAtYjc3YmUyZWUwZDk4OjM2OWZjOTAzLTc4MGUtNDA2ZC04MTMzLTBlYmIxNGQ5YjQ5NA==",
        "keywords": ["docs"],
        "description": "📝 **Google Docs**: criar, editar e gerenciar documentos de texto"
    },
    "slack_external": {
        "name": "Zapier Slack MCP",
        "server_label": "zapier-slack",
        "url": "https://mcp.zapier.com/api/mcp/s/a4c531ae-e564-4f2e-acda-4d76f9f345b9/mcp",
        "token": "YTRjNTMxYWUtZTU2NC00ZjJlLWFjZGEtNGQ3NmY5ZjM0NWI5OjE5YjAzNjY0LTg4ZjYtNDMyYy1hZDhmLWQ3ZmQ5YzAyMmYyNw==",
        "keywords": ["slack"],
        "description": "💬 **Slack**: enviar mensagens para outros workspaces"
    },
    "google_calendar": {
        "name": "Zapier Google Calendar MCP",
        "server_label": "zapier-gcalendar",
        "url": "https://mcp.zapier.com/api/mcp/s/e364090d-c050-4ace-97af-1314ab430dfe/mcp",
        "token": "ZTM2NDA5MGQtYzA1MC00YWNlLTk3YWYtMTMxNGFiNDMwZGZlOjhlZDliNGNlLTlhYzAtNDU0NC1hOWViLTA3ZDgyMjMyNDEzZg==",
        "keywords": ["calendar"],
        "description": "📅 **Google Calendar**: criar e gerenciar eventos, reuniões e compromissos"
    },
    "gmail": {
        "name": "Zapier Gmail MCP",
        "server_label": "zapier-gmail",
        "url": "https://mcp.zapier.com/api/mcp/s/3b20917b-c9f1-4d12-9f2a-1c60c84ae6d1/mcp",
        "token": "M2IyMDkxN2ItYzlmMS00ZDEyLTlmMmEtMWM2MGM4NGFlNmQxOmYzMmU4MjIxLWQ5NjUtNDJhMy05YjIzLTJkZTJhMDY2NWZkZA==",
        "keywords": ["gmail"],
        "description": "📧 **Gmail**: enviar, ler e gerenciar emails"
    }
    # 🚀 FUTURE MCPs: Add new Zapier integrations here following the same pattern
    #
    # EXAMPLE - Notion Integration:
    # "notion": {
    #     "name": "Zapier Notion MCP",
    #     "server_label": "zapier-notion",
    #     "url": "https://mcp.zapier.com/api/mcp/s/YOUR-NOTION-SERVER-ID/mcp",
    #     "token": "YOUR-NOTION-TOKEN",
    #     "keywords": ["notion"],
    #     "description": "� **Notion**: criar páginas e gerenciar bases de dados"
    # }
}



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


async def create_agent(slack_server: MCPServerStdio) -> Agent:
    """Creates and returns Livia, an OpenAI Agent configured to use the Slack MCP server and tools."""

    logger.info("Creating Livia - the Slack Chatbot Agent...")

    web_search_tool = WebSearchTool(search_context_size="medium")

    mcp_servers = [slack_server]
    server_descriptions = [f"'{slack_server.name}'"]

    # Generate dynamic Zapier tools description from configuration
    zapier_descriptions = []
    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        zapier_descriptions.append(f"  - ✅ {mcp_config['description']}")

    zapier_tools_description = (
        "⚡ **Zapier Integration Tools** (Remote MCP):\n"
        + "\n".join(zapier_descriptions) + "\n"
        "**Como usar (keywords simplificadas):**\n"
        "  - Para Asana: use 'asana'\n"
        "  - Para Google Drive: use 'google' ou 'drive'\n"
        "  - Para Everhour: use 'everhour', 'tempo', 'time', 'horas'\n"
        "  - Para Google Docs: use 'docs'\n"
        "  - Para Gmail: use 'gmail'\n"
        "  - Para Google Calendar: use 'calendar'\n"
        "  - Para Slack Externo: use 'slack'\n"
        "**Dicas:**\n"
        "  - IMPORTANTE: TargetGroupIndex_BR2024 é um ARQUIVO, não pasta\n"
        "  - Se não encontrar, tente busca parcial ou termos relacionados\n"
        "  - Roteamento automático baseado em palavras-chave\n"
    )

    agent = Agent(
        name="Livia",
        instructions=(
            "You are Livia, an intelligent chatbot assistant for Slack. "
            "IMPORTANT: You should ONLY respond in threads where the bot was mentioned in the FIRST message of the thread. "
            "You have access to multiple powerful tools:\n\n"
            "🔍 **Web Search Tool**: Search the internet for current information, news, facts, and answers\n"
            "👁️ **Image Vision**: Analyze and describe images uploaded to Slack or provided via URLs\n"
            f"{zapier_tools_description}"
            "📱 **Slack Tools** (via MCP Server):\n"
            "  - List channels and users\n"
            "  - Get channel history and user information\n"
            "  - Add reactions to messages\n"
            "  - ⚠️ **CRITICAL**: NEVER use slack_post_message tool - responses are handled automatically\n\n"
            "**CRITICAL MCP USAGE INSTRUCTIONS:**\n"
            "1. **Sequential Search Strategy**: When MCPs require multiple fields (workspace → project → task), perform searches step-by-step:\n"
            "   - First: Search for workspace/organization\n"
            "   - Second: Use workspace result to search for project\n"
            "   - Third: Use project result to search for specific task\n"
            "   - Example: Find workspace 'INOVAÇÃO' → Find project 'Inovação' → Find task 'Terminar Livia 2.0'\n"
            "2. **ALWAYS CITE IDs/NUMBERS**: Include ALL IDs, codes, and numbers from MCP responses in your answers:\n"
            "   - Example: 'Found project Inovação (ev:273391483277215) with task Terminar Livia 2.0 (ev:273391484704922)'\n"
            "   - This enables future operations using these exact IDs\n"
            "3. **Use Exact IDs When Available**: If conversation history contains IDs, use them directly instead of searching by name\n"
            "4. **Multiple Tool Calls**: Don't hesitate to make multiple MCP calls to complete a task properly\n\n"
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
            "- 🔄 **Smart Routing**: Requests are automatically routed to appropriate Zapier MCPs\n"
            "- 🎯 **Keyword Detection**: System detects intent and uses the right integration\n"
            "- 🚨 SECURITY: NEVER use slack_post_message - responses are handled automatically\n"
            "- 🚨 SECURITY: NEVER send messages to channels other than where you were mentioned\n"
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


async def process_message_with_zapier_mcp(mcp_key: str, message: str, image_urls: Optional[List[str]] = None) -> str:
    """
    Generic function to process message using OpenAI Responses API with any Zapier Remote MCP.

    Args:
        mcp_key: Key from ZAPIER_MCPS configuration (e.g., 'asana', 'google_drive')
        message: User message to process
        image_urls: Optional list of image URLs for vision processing

    Returns:
        Response text from the MCP
    """
    from openai import OpenAI

    if mcp_key not in ZAPIER_MCPS:
        raise ValueError(f"Unknown MCP key: {mcp_key}. Available: {list(ZAPIER_MCPS.keys())}")

    mcp_config = ZAPIER_MCPS[mcp_key]
    client = OpenAI()

    # Prepare input data with optional images
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

    logger.info(f"Processing message with {mcp_config['name']}")
    logger.info(f"MCP URL: {mcp_config['url']}")
    logger.info(f"MCP Server Label: {mcp_config['server_label']}")
    logger.info(f"Input message: {message}")

    try:
        # Special handling for Everhour time tracking operations
        if mcp_config["server_label"] == "zapier-everhour":
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=input_data,
                instructions=(
                    "You are an Everhour time tracking specialist. Use the everhour_add_time tool and return a user-friendly message.\n\n"
                    "🎯 **CRITICAL INSTRUCTIONS**:\n"
                    "1. **Use everhour_add_time tool** with exact parameters from user message\n"
                    "2. **Extract IDs directly**: Look for 'ev:xxxxxxxxxx' format in user message\n"
                    "3. **Time format**: '1h', '2h', '30m' (never '1:00')\n"
                    "4. **Date**: Use today's date in 'YYYY-MM-DD' format\n"
                    "5. **Return user-friendly message** based on the tool results\n\n"
                    "📋 **Response Format**:\n"
                    "If SUCCESS: '✅ Tempo adicionado com sucesso! ⏰ [time] na task [task_id] em [date]'\n"
                    "If ERROR: '❌ Erro ao adicionar tempo: [error details]'\n\n"
                    "✅ **EXAMPLE**:\n"
                    "User: 'adicionar 2h na task ev:273393148295192 no projeto ev:273391483277215'\n"
                    "1. Call: everhour_add_time(task_id='ev:273393148295192', project_id='ev:273391483277215', time='2h', date='2025-01-05', comment='Time tracking')\n"
                    "2. Return: '✅ Tempo adicionado com sucesso! ⏰ 2h na task ev:273393148295192 em 2025-01-05'\n\n"
                    "🎯 **GOAL**: Use MCP tool and return clear, friendly message in Portuguese!"
                ),

                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "allowed_tools": ["everhour_find_project", "everhour_add_time"],
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token']}"
                        }
                    }
                ]
            )
        else:
            # Regular MCP processing for other services (Asana, Google Drive, etc.)
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=input_data,
                instructions=(
                    f"You are an intelligent assistant with access to {mcp_config['name']} via MCP tools. "
                    "Follow these guidelines for optimal performance:\n\n"
                    "🔍 **SEARCH STRATEGY**:\n"
                    "1. **Sequential Search**: For hierarchical data (workspace → project → task):\n"
                    "   - Step 1: Search for workspace/organization by name\n"
                    "   - Step 2: Use workspace result to search for project\n"
                    "   - Step 3: Use project result to search for specific task\n"
                    "   - Example: Find workspace 'INOVAÇÃO' → Find project 'Inovação' → Find task 'Terminar Livia 2.0'\n\n"
                    "2. **Limit Results**: Return only 4 results at a time, ask user if they want more\n"
                    "3. **Be Specific**: Try exact names first, then partial matches if needed\n\n"
                    "📋 **RESPONSE REQUIREMENTS**:\n"
                    "- **ALWAYS CITE IDs/NUMBERS**: Include ALL IDs, codes, and numbers from MCP responses\n"
                    "- Example: 'Found project Inovação (ev:273391483277215) with task Terminar Livia 2.0 (ev:273391484704922)'\n"
                    "- This enables future operations using these exact IDs\n"
                    "- Return clear, user-friendly messages in Portuguese\n\n"
                    "⚡ **EFFICIENCY TIPS**:\n"
                    "- Use exact IDs when available from conversation history\n"
                    "- Make multiple MCP calls as needed to complete tasks\n"
                    "- If essential info is missing (size, color, etc.), ask follow-up questions first\n\n"
                    "🎯 **GOAL**: Provide accurate, actionable results with all necessary IDs and details."
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token']}"
                        }
                    }
                ]
            )

        logger.info(f"MCP Response received: {response.output_text}")

        # Log the raw response for debugging
        logger.info(f"Raw MCP Response: {response.output_text}")

        return response.output_text or "No response generated."

    except Exception as e:
        logger.error(f"Error calling {mcp_config['name']}: {e}")
        raise


def detect_zapier_mcp_needed(message: str) -> Optional[str]:
    """
    Detect which Zapier MCP is needed based on message keywords.
    Uses priority-based detection to handle overlapping keywords.

    Args:
        message: User message to analyze

    Returns:
        MCP key if detected, None otherwise
    """
    message_lower = message.lower()

    # Priority order: More specific services first to avoid conflicts
    priority_order = ["everhour", "asana", "google_drive", "google_docs", "gmail", "google_calendar", "slack_external"]

    for mcp_key in priority_order:
        if mcp_key in ZAPIER_MCPS:
            mcp_config = ZAPIER_MCPS[mcp_key]
            if any(keyword in message_lower for keyword in mcp_config["keywords"]):
                logger.info(f"Detected {mcp_config['name']} keywords in message: {[kw for kw in mcp_config['keywords'] if kw in message_lower]}")
                return mcp_key

    return None


def get_available_zapier_mcps() -> dict:
    """
    Get information about all available Zapier MCPs.

    Returns:
        Dictionary with MCP information for debugging/monitoring
    """
    return {
        mcp_key: {
            "name": config["name"],
            "description": config["description"],
            "keywords": config["keywords"]
        }
        for mcp_key, config in ZAPIER_MCPS.items()
    }

async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None) -> str:
    """Runs the agent with the given message and optional image URLs, returns the final output."""

    # 🔍 Check if message needs a specific Zapier MCP
    mcp_needed = detect_zapier_mcp_needed(message)

    if mcp_needed:
        mcp_name = ZAPIER_MCPS[mcp_needed]["name"]
        logger.info(f"Message requires {mcp_name}, routing to Zapier Remote MCP")
        try:
            return await process_message_with_zapier_mcp(mcp_needed, message, image_urls)
        except Exception as e:
            logger.warning(f"{mcp_name} failed, falling back to regular agent: {e}")
            # Continue to regular agent processing below

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