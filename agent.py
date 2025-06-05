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
from agents import Agent, Runner, gen_trace_id, trace, WebSearchTool, ItemHelpers, FileSearchTool
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
        "keywords": ["google drive", "drive"],
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
        "keywords": ["calendar", "calendario", "eventos", "evento", "reuniao", "reunioes", "compromisso", "compromissos", "agenda"],
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

    # File Search Tool configuration
    file_search_tool = FileSearchTool(
        vector_store_ids=["vs_683e3a1ac4808191ae5e6fe24392e609"],
        max_num_results=5,
        include_search_results=True
    )

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
        "  - Para Google Docs: use 'docs', 'google docs', 'documento'\n"
        "  - Para Google Drive: use 'drive', 'arquivo', 'pasta'\n"
        "  - Para Everhour: use 'everhour', 'tempo', 'time', 'horas'\n"
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
            """You are Livia, an intelligent chatbot assistant for Slack and works at a Brazilian advertising agency called ℓiⱴε. You are a agent in a slack chat room. You might receive messages from multiple people.
Format bold text *like this*, italic text _like this_ and strikethrough text ~like this~.
Slack user IDs match the regex `<@U.*?>`.
Your Slack user ID is <@{U057233T98A}>.
Each message has the author's Slack user ID prepended, like the regex `^<@U.*?>: ` followed by the message text."
            "IMPORTANT: You should ONLY respond in threads where the bot was mentioned in the FIRST message of the thread. "
            "You have access to multiple powerful tools:\n\n"
            "🔍 **Web Search Tool**: Search the internet for current information, news, facts, and answers\n"
            "📄 **File Search Tool**: Search through uploaded documents and files in your knowledge base for relevant information\n"
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
            "- Use file search when users ask about documents, files, or information from your knowledge base\n"
            "- When users upload images or send image URLs, analyze them and provide detailed descriptions\n"
            "- For images, describe what you see including objects, people, text, colors, and context\n"
            "- For Google Drive searches: try multiple search strategies if first attempt fails\n"
            "- When searching for folders/files, try partial names, different cases, and related terms\n"
            "- If a search returns no results, suggest alternative search terms or approaches\n"
            "- IMPORTANT: If user searches for 'TargetGroup', it's likely the file 'TargetGroupIndex_BR2024'\n"
            "- Consider that file names may have suffixes like _BR2024, _2024, etc.\n"
            "- Always offer to try broader or more specific search terms when initial search fails\n"
            "- When user says 'pasta' but means 'arquivo', correct and search for files instead\n"
            "- For document-related queries, try file search first before other tools\n"
            "- 🔄 **Smart Routing**: Requests are automatically routed to appropriate Zapier MCPs\n"
            "- 🎯 **Keyword Detection**: System detects intent and uses the right integration\n"
            "- 🚨 SECURITY: NEVER use slack_post_message - responses are handled automatically\n"
            "- 🚨 SECURITY: NEVER send messages to channels other than where you were mentioned\n"
            "- Be helpful, concise, and professional in your responses\n"
            "- Ask for clarification if needed\n"
            "- Always cite sources when providing information from web searches\n"
            "- You can help with general questions, provide information, and assist with Slack-related tasks"""
        ),
        model="gpt-4.1",
        tools=[web_search_tool, file_search_tool],
        mcp_servers=mcp_servers,
    )
    servers_info = " and ".join(server_descriptions)
    logger.info(f"Agent '{agent.name}' created with WebSearchTool and access to {servers_info}.")
    return agent


async def process_message_with_zapier_mcp_streaming(mcp_key: str, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> str:
    """
    Generic function to process message using OpenAI Responses API with any Zapier Remote MCP with streaming support.

    Args:
        mcp_key: Key from ZAPIER_MCPS configuration (e.g., 'asana', 'google_drive')
        message: User message to process
        image_urls: Optional list of image URLs for vision processing
        stream_callback: Optional callback function for streaming updates

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

    logger.info(f"Processing message with {mcp_config['name']} (STREAMING)")
    logger.info(f"MCP URL: {mcp_config['url']}")
    logger.info(f"MCP Server Label: {mcp_config['server_label']}")
    logger.info(f"Input message: {message}")

    try:
        # Special handling for Everhour time tracking operations
        if mcp_config["server_label"] == "zapier-everhour":
            stream = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use everhour_add_time tool with exact parameters.\n"
                    "Extract ev:xxxxxxxxxx IDs from message. Time format: 1h, 2h, 30m. Use today's date YYYY-MM-DD.\n"
                    "SUCCESS: 'Tempo adicionado! [time] na task [task_id]'\n"
                    "ERROR: 'Erro: [details]'"
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "allowed_tools": ["everhour_find_project", "everhour_add_time"],
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ],
                stream=True
            )

        elif mcp_config["server_label"] == "zapier-gcalendar":
            # Special handling for Google Calendar with consistent date parameters
            stream = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use Google Calendar tools to search and manage events.\n\n"
                    "🗓️ **CRITICAL: Today is June 5, 2025**: Use 2025-06-05 as reference for 'today'\n"
                    "📅 **Search Strategy**:\n"
                    "- Try these tools in order: gcalendar_find_events, gcalendar_search_events, google_calendar_find_events\n"
                    "- Use start_date and end_date parameters in YYYY-MM-DD format\n"
                    "- Default range: today to next 7 days (2025-06-05 to 2025-06-12)\n"
                    "- Timezone: America/Sao_Paulo\n"
                    "- If no events found, try broader date range (2025-06-01 to 2025-06-30)\n\n"
                    "📋 **Response Format** (Portuguese):\n"
                    "📅 **Eventos no Google Calendar:**\n"
                    "1. **[Nome do Evento]**\n"
                    "   - 📅 Data: [data]\n"
                    "   - ⏰ Horário: [hora início] às [hora fim]\n"
                    "   - 🔗 Link: [link se disponível]\n\n"
                    "⚠️ **IMPORTANT**: Always search with explicit date ranges in JUNE 2025!"
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ],
                stream=True
            )

        elif mcp_config["server_label"] == "zapier-gmail":
            # Special handling for Gmail with optimized search and content limiting
            stream = client.responses.create(
                model="gpt-4o-mini",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use Gmail tools to search and read emails.\n\n"
                    "🔍 **STEP-BY-STEP APPROACH**:\n"
                    "1. **First**: Use gmail_search_emails tool with search string 'in:inbox'\n"
                    "2. **Then**: Use gmail_get_email tool to read the first email from results\n"
                    "3. **Finally**: Summarize the email content\n\n"
                    "📧 **SEARCH EXAMPLES**:\n"
                    "- For latest emails: 'in:inbox'\n"
                    "- For unread emails: 'is:unread'\n"
                    "- For recent emails: 'newer_than:1d'\n"
                    "- Combined: 'in:inbox newer_than:1d'\n\n"
                    "📋 **RESPONSE FORMAT** (Portuguese):\n"
                    "📧 **Último Email Recebido:**\n"
                    "👤 **De:** [sender name and email]\n"
                    "📝 **Assunto:** [subject line]\n"
                    "📅 **Data:** [date received]\n"
                    "📄 **Resumo:** [Brief 2-3 sentence summary of main content]\n\n"
                    "⚠️ **IMPORTANT**:\n"
                    "- Always use gmail_search_emails first to find emails\n"
                    "- Then use gmail_get_email to read the specific email\n"
                    "- Summarize content - don't return full email text\n"
                    "- If search fails, try simpler search terms\n\n"
                    "🎯 **GOAL**: Find and summarize the user's latest email efficiently."
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ],
                stream=True
            )

        elif mcp_config["server_label"] == "zapier-slack":
            # Special handling for Slack with message search and channel operations
            stream = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use slack_find_message with 'in:channel-name' format.\n"
                    "Sort by timestamp desc. Try 'inovacao' or 'inovação' variations.\n"
                    "Return: user, timestamp, message content, permalink, summary in Portuguese."
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ],
                stream=True
            )
        else:
            # Regular MCP processing for other services (Asana, Google Drive, etc.)
            stream = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    f"You are Livia, AI assistant from ℓiⱴε agency with {mcp_config['name']} access. Sequential search: workspace→project→task.\n"
                    "Always include ALL IDs/numbers from responses. Limit 4 results. Portuguese responses.\n"
                    "Example: 'Found project Inovação (ev:123) with task Name (ev:456)'"
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
                ],
                stream=True
            )

        # Process streaming response
        full_response = ""
        for event in stream:
            if hasattr(event, 'type'):
                if event.type == "response.output_text.delta":
                    delta_text = getattr(event, 'delta', '')
                    if delta_text:
                        full_response += delta_text
                        # Call stream callback if provided
                        if stream_callback:
                            await stream_callback(delta_text, full_response)
                elif event.type == "response.completed":
                    logger.info("MCP streaming response completed")
                elif event.type == "error":
                    logger.error(f"MCP streaming error: {event}")

        logger.info(f"MCP Streaming Response completed: {full_response}")
        return full_response or "No response generated."

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error calling {mcp_config['name']} with streaming: {e}")

        # Special handling for Gmail context window exceeded
        if mcp_config["server_label"] == "zapier-gmail" and "context_length_exceeded" in error_message:
            logger.warning("Gmail MCP context window exceeded, trying with simplified request")
            try:
                # Retry with more restrictive search and summarization (non-streaming fallback)
                simplified_response = client.responses.create(
                    model="gpt-4o-mini",
                    input="Busque apenas o último email recebido na caixa de entrada e faça um resumo muito breve",
                    instructions=(
                        "You are Livia, AI assistant from ℓiⱴε agency. Search for the latest email in inbox using 'in:inbox' operator.\n"
                        "CRITICAL: Return only a 2-sentence summary in Portuguese.\n"
                        "Format: 'Último email de [sender] com assunto \"[subject]\". [Brief summary].'\n"
                        "NEVER return full email content - only essential information."
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
                return simplified_response.output_text or "Não foi possível acessar os emails no momento."
            except Exception as retry_error:
                logger.error(f"Gmail MCP retry also failed: {retry_error}")
                return "❌ Não foi possível acessar os emails do Gmail no momento. O email pode ser muito grande para processar. Tente ser mais específico na busca."

        raise


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
    logger.info(f"Token length: {len(mcp_config['token'])} chars")
    logger.info(f"Token starts with: {mcp_config['token'][:10]}...")
    logger.info(f"Authorization header will be: 'Bearer {mcp_config['token'][:10]}...'")

    try:
        # Special handling for Everhour time tracking operations
        if mcp_config["server_label"] == "zapier-everhour":
            response = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use everhour_add_time tool with exact parameters.\n"
                    "Extract ev:xxxxxxxxxx IDs from message. Time format: 1h, 2h, 30m. Use today's date YYYY-MM-DD.\n"
                    "SUCCESS: 'Tempo adicionado! [time] na task [task_id]'\n"
                    "ERROR: 'Erro: [details]'"
                ),

                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "allowed_tools": ["everhour_find_project", "everhour_add_time"],
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ]
            )

        elif mcp_config["server_label"] == "zapier-gcalendar":
            # Special handling for Google Calendar with consistent date parameters
            response = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use Google Calendar tools to search and manage events.\n\n"
                    "🗓️ **CRITICAL: Today is June 5, 2025**: Use 2025-06-05 as reference for 'today'\n"
                    "📅 **Search Strategy**:\n"
                    "- Try these tools in order: gcalendar_find_events, gcalendar_search_events, google_calendar_find_events\n"
                    "- Use start_date and end_date parameters in YYYY-MM-DD format\n"
                    "- Default range: today to next 7 days (2025-06-05 to 2025-06-12)\n"
                    "- Timezone: America/Sao_Paulo\n"
                    "- If no events found, try broader date range (2025-06-01 to 2025-06-30)\n\n"
                    "📋 **Response Format** (Portuguese):\n"
                    "📅 **Eventos no Google Calendar:**\n"
                    "1. **[Nome do Evento]**\n"
                    "   - 📅 Data: [data]\n"
                    "   - ⏰ Horário: [hora início] às [hora fim]\n"
                    "   - 🔗 Link: [link se disponível]\n\n"
                    "⚠️ **IMPORTANT**: Always search with explicit date ranges in JUNE 2025!"
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ]
            )

        elif mcp_config["server_label"] == "zapier-gmail":
            # Special handling for Gmail with optimized search and content limiting
            response = client.responses.create(
                model="gpt-4o-mini",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use Gmail tools to search and read emails.\n\n"
                    "🔍 **STEP-BY-STEP APPROACH**:\n"
                    "1. **First**: Use gmail_search_emails tool with search string 'in:inbox'\n"
                    "2. **Then**: Use gmail_get_email tool to read the first email from results\n"
                    "3. **Finally**: Summarize the email content\n\n"
                    "📧 **SEARCH EXAMPLES**:\n"
                    "- For latest emails: 'in:inbox'\n"
                    "- For unread emails: 'is:unread'\n"
                    "- For recent emails: 'newer_than:1d'\n"
                    "- Combined: 'in:inbox newer_than:1d'\n\n"
                    "📋 **RESPONSE FORMAT** (Portuguese):\n"
                    "📧 **Último Email Recebido:**\n"
                    "👤 **De:** [sender name and email]\n"
                    "📝 **Assunto:** [subject line]\n"
                    "📅 **Data:** [date received]\n"
                    "📄 **Resumo:** [Brief 2-3 sentence summary of main content]\n\n"
                    "⚠️ **IMPORTANT**:\n"
                    "- Always use gmail_search_emails first to find emails\n"
                    "- Then use gmail_get_email to read the specific email\n"
                    "- Summarize content - don't return full email text\n"
                    "- If search fails, try simpler search terms\n\n"
                    "🎯 **GOAL**: Find and summarize the user's latest email efficiently."
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ]
            )

        elif mcp_config["server_label"] == "zapier-slack":
            # Special handling for Slack with message search and channel operations
            response = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use slack_find_message with 'in:channel-name' format.\n"
                    "Sort by timestamp desc. Try 'inovacao' or 'inovação' variations.\n"
                    "Return: user, timestamp, message content, permalink, summary in Portuguese."
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['token'].strip()}"
                        }
                    }
                ]
            )
        else:
            # Regular MCP processing for other services (Asana, Google Drive, etc.)
            response = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    f"You are Livia, AI assistant from ℓiⱴε agency with {mcp_config['name']} access. Sequential search: workspace→project→task.\n"
                    "Always include ALL IDs/numbers from responses. Limit 4 results. Portuguese responses.\n"
                    "Example: 'Found project Inovação (ev:123) with task Name (ev:456)'"
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
        error_message = str(e)
        logger.error(f"Error calling {mcp_config['name']}: {e}")

        # Special handling for Gmail context window exceeded
        if mcp_config["server_label"] == "zapier-gmail" and "context_length_exceeded" in error_message:
            logger.warning("Gmail MCP context window exceeded, trying with simplified request")
            try:
                # Retry with more restrictive search and summarization
                simplified_response = client.responses.create(
                    model="gpt-4o-mini",
                    input="Busque apenas o último email recebido na caixa de entrada e faça um resumo muito breve",
                    instructions=(
                        "You are Livia, AI assistant from ℓiⱴε agency. Search for the latest email in inbox using 'in:inbox' operator.\n"
                        "CRITICAL: Return only a 2-sentence summary in Portuguese.\n"
                        "Format: 'Último email de [sender] com assunto \"[subject]\". [Brief summary].'\n"
                        "NEVER return full email content - only essential information."
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
                return simplified_response.output_text or "Não foi possível acessar os emails no momento."
            except Exception as retry_error:
                logger.error(f"Gmail MCP retry also failed: {retry_error}")
                return "❌ Não foi possível acessar os emails do Gmail no momento. O email pode ser muito grande para processar. Tente ser mais específico na busca."

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
    priority_order = ["everhour", "asana", "google_docs", "google_drive", "gmail", "google_calendar", "slack_external"]

    for mcp_key in priority_order:
        if mcp_key in ZAPIER_MCPS:
            mcp_config = ZAPIER_MCPS[mcp_key]
            detected_keywords = [kw for kw in mcp_config['keywords'] if kw in message_lower]
            if detected_keywords:
                logger.info(f"🎯 Detected {mcp_config['name']} keywords in message: {detected_keywords}")
                logger.info(f"🔀 Routing to MCP: {mcp_key}")
                return mcp_key
            else:
                logger.debug(f"❌ No {mcp_config['name']} keywords found in message")

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

async def process_message_streaming(agent: Agent, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> str:
    """Runs the agent with the given message and optional image URLs with streaming support, returns the final output."""

    # 🔍 Check if message needs a specific Zapier MCP
    mcp_needed = detect_zapier_mcp_needed(message)

    if mcp_needed:
        mcp_name = ZAPIER_MCPS[mcp_needed]["name"]
        logger.info(f"Message requires {mcp_name}, routing to Zapier Remote MCP with streaming")
        try:
            return await process_message_with_zapier_mcp_streaming(mcp_needed, message, image_urls, stream_callback)
        except Exception as e:
            logger.warning(f"{mcp_name} failed, falling back to regular agent: {e}")
            # Continue to regular agent processing below

    # Generate a trace ID for monitoring the agent's execution flow
    trace_id = gen_trace_id()
    logger.info(f"Starting agent run for message: '{message}' with STREAMING. Trace: https://platform.openai.com/traces/{trace_id}")

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

            # Execute the agent with streaming
            result = Runner.run_streamed(starting_agent=agent, input=input_data)

            # Process streaming events
            full_response = ""
            final_message_output = ""

            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    # Handle raw response events for streaming text
                    if hasattr(event.data, 'type') and event.data.type == "response.output_text.delta":
                        delta_text = getattr(event.data, 'delta', '')
                        if delta_text:
                            full_response += delta_text
                            # Call stream callback if provided
                            if stream_callback:
                                await stream_callback(delta_text, full_response)
                    elif hasattr(event.data, 'type') and event.data.type == "response.completed":
                        logger.info("Agent streaming response completed")
                elif event.type == "run_item_stream_event":
                    # Handle higher-level events like tool calls and message outputs
                    if event.item.type == "tool_call_item":
                        logger.info("-- Tool was called during streaming")
                    elif event.item.type == "tool_call_output_item":
                        logger.info(f"-- Tool output during streaming: {event.item.output}")
                    elif event.item.type == "message_output_item":
                        # Get the final message output
                        message_text = ItemHelpers.text_message_output(event.item)
                        if message_text:
                            final_message_output = message_text
                            # Update full response with complete message if different
                            if message_text != full_response:
                                full_response = message_text
                                if stream_callback:
                                    await stream_callback("", full_response)  # Send complete message
                        logger.info(f"-- Message output during streaming: {message_text}")

            # Use the final message output if available, otherwise use accumulated response
            final_output = final_message_output or full_response or "No response generated."

            logger.info(f"Agent streaming run completed. Final output: '{final_output}'")

    except Exception as e:
        logger.error(f"Error during agent streaming run (trace_id: {trace_id}): {e}", exc_info=True)
        final_output = f"An error occurred while processing your request: {str(e)}"

    # Ensure the output is a string
    return str(final_output)


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