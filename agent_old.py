#!/usr/bin/env python3
"""
Livia - Definição do Agente Chatbot para Slack
----------------------------------------------
Define a Livia, um agente chatbot inteligente para Slack usando OpenAI Agents SDK e API Responses.
Responde apenas em threads que mencionam o bot na primeira mensagem.
Inclui ferramentas: file_search, web_search, visão de imagem e ferramentas MCP.
Aprimorado com Outputs Estruturados para aderência confiável ao schema JSON.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional
import tiktoken
from dotenv import load_dotenv

# Componentes do OpenAI Agents SDK
from agents import Agent, Runner, gen_trace_id, trace, WebSearchTool, ItemHelpers, FileSearchTool, HostedMCPTool

# Carrega variáveis de ambiente do arquivo .env
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Return the number of tokens for a given text and model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


# Import MCP configurations from organized module
from tools.mcp.zapier_mcps import ZAPIER_MCPS
from tools.mcp.cache_manager import cache_manager, setup_mcp_caching, CachedMCPWrapper

# ===== ZAPIER MCP CONFIGURATION =====
# Configuration moved to tools/mcp/zapier_mcps.py for better organization



# MCP Slack local removido - usando API Slack direta para maior controle
# A comunicação com Slack é feita diretamente via slack_bolt no server.py


async def create_agent() -> Agent:
    """Creates and returns Livia, an OpenAI Agent configured to use the Slack MCP server and tools."""

    logger.info("Creating Livia - the Slack Chatbot Agent...")

    web_search_tool = WebSearchTool(search_context_size="medium")

    # File Search Tool configuration
    file_search_tool = FileSearchTool(
        vector_store_ids=["vs_683e3a1ac4808191ae5e6fe24392e609"],
        max_num_results=5,
        include_search_results=True
    )

    # Image Generation Tool configuration
    # TODO: SLACK_INTEGRATION_POINT - Ferramenta de geração de imagem para o Slack
    # Configuração correta do ImageGenerationTool (temporariamente removida - erro tools[2].type)
    # image_generation_tool = ImageGenerationTool(
    #     tool_config={
    #         "size": "auto",
    #         "quality": "auto"
    #     }
    # )

    # 🚀 ZAPIER MCPs VIA AGENTS SDK - HostedMCPTool approach
    # Create HostedMCPTool instances for each Zapier MCP
    zapier_tools = []

    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        # Convert Zapier MCP URL from /mcp to /sse for HostedMCPTool
        server_url = mcp_config["url"]
        if server_url.endswith("/mcp"):
            server_url = server_url.replace("/mcp", "/sse")

        hosted_mcp = HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": mcp_config["server_label"],
                "server_url": server_url,
                "headers": {
                    "Authorization": f"Bearer {mcp_config['api_key'].strip()}"
                },
                "require_approval": "never"
            }
        )
        zapier_tools.append(hosted_mcp)
        logger.info(f"✅ Created HostedMCPTool for {mcp_config['name']}")

    logger.info(f"🚀 Using OpenAI Agents SDK as PRIMARY architecture with {len(zapier_tools)} Zapier MCPs via HostedMCPTool")
    logger.info("✨ All MCPs now use Agents SDK - no more hybrid architecture!")

    # Generate dynamic Zapier tools description from configuration
    zapier_descriptions = []
    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        zapier_descriptions.append(f"  - ✅ {mcp_config['description']}")

    zapier_tools_description = (
        "⚡ **Zapier Integration Tools** (Enhanced Multi-Turn via Responses API):\n"
        + "\n".join(zapier_descriptions) + "\n"
        "**Enhanced Multi-Turn Execution:**\n"
        "  - Improved Responses API with manual multi-turn loops\n"
        "  - Agent will attempt to chain tool calls (e.g., find project → find task → add time)\n"
        "  - Enhanced instructions for complex workflows\n"
        "**Como usar (keywords específicas):**\n"
        "  - Para mcpAsana: use 'asana'\n"
        "  - Para mcpEverhour: use 'everhour'\n"
        "  - Para mcpGmail: use 'gmail'\n"
        "  - Para mcpGoogleDocs: use 'docs'\n"
        "  - Para mcpGoogleSheets: use 'sheets'\n"
        "  - Para Google Drive: use 'drive'\n"
        "  - Para mcpGoogleCalendar: use 'calendar'\n"
        "  - Para mcpSlack: use 'slack'\n"
        "**Dicas:**\n"
        "  - IMPORTANTE: TargetGroupIndex_BR2024 é um ARQUIVO, não pasta\n"
        "  - Se não encontrar, tente busca parcial ou termos relacionados\n"
        "  - Instruções aprimoradas para execução em cadeia\n"
    )

    logger.info(f"✅ Configured hybrid architecture with enhanced multi-turn for {len(ZAPIER_MCPS)} Zapier MCPs")

    # Slack communication handled directly via API (no MCP tools needed)

    # Combine all tools: built-in tools + Zapier HostedMCPTools
    all_tools = [web_search_tool, file_search_tool] + zapier_tools

    agent = Agent(
        name="Livia",
        instructions=(
            """<identity>
You are Livia, an intelligent chatbot assistant working at ℓiⱴε, a Brazilian advertising agency. You operate in Slack channels, groups, and DMs and your Slack ID is <@U057233T98A>.
</identity>

<communication_style>
- BE EXTREMELY CONCISE AND BRIEF - this is your primary directive
- Default to short, direct answers unless explicitly asked for details
- One sentence responses are preferred for simple questions
- Avoid unnecessary explanations, steps, or elaborations
- Always respond in the same language the user communicates with you
- Use Slack formatting: *bold*, _italic_, ~strikethrough~
- Your Slack ID: <@U057233T98A>
- Only mention File Search or file names when explicitly asked about documents
- Feel free to disagree constructively to improve results
</communication_style>

<available_tools>
- Web Search Tool: Search internet for current information
- File Search Tool: Search uploaded documents in knowledge base
- Image Vision: Analyze uploaded images or URLs - you have FULL vision capabilities
- Image Generation Tool: Create images using gpt-image-1 model
""" + f"{zapier_tools_description}" + """
<mcp_usage_rules>
1. Sequential Search Strategy: workspace → project → task
2. Always include ALL IDs/numbers from API responses
3. Use exact IDs when available in conversation history
4. Make multiple MCP calls as needed to complete tasks
5. Limit results to maximum 4 items per search
</mcp_usage_rules>

<search_strategy>
CRITICAL: Use intelligent search strategy to avoid unnecessary tool calls:

IF info is static/historical (e.g., coding principles, scientific facts, brand colors, company info)
→ ANSWER DIRECTLY without tools (info rarely changes)

ELSE IF info changes annually/slowly (e.g., rankings, statistics, yearly trends)
→ ANSWER DIRECTLY but offer to search for latest updates

ELSE IF info changes frequently (e.g., weather, news, stock prices, current events)
→ USE WEB SEARCH immediately for accurate current information

ELSE IF user asks about documents/files
→ USE FILE SEARCH to find relevant documents in knowledge base
</search_strategy>

<response_guidelines>
- NEVER answer with uncertainty - if unsure, USE AVAILABLE TOOLS for verification
- Use web search for current/changing information only
- Use file search when users ask about documents
- Provide detailed image analysis when images are shared - you CAN see and analyze images perfectly
- NEVER say you cannot see images - you have full vision capabilities and should analyze them directly
- Try multiple search strategies if initial attempts fail
- Suggest alternative search terms when no results found
- Handle 'TargetGroup' searches as 'TargetGroupIndex_BR2024'
- Correct 'pasta' to 'arquivo' when appropriate
- Cite sources for web searches
- Mention document names for file searches
- Be professional and helpful
- Ask for clarification when needed
- NEVER use slack_post_message - responses handled automatically
- NEVER send messages to other channels
</response_guidelines>
"""
        ),
        model="gpt-4.1",
        tools=all_tools  # All tools including Zapier MCPs via HostedMCPTool
    )

    tools_info = f"WebSearchTool, FileSearchTool, and {len(zapier_tools)} Zapier MCPs via HostedMCPTool"
    logger.info(f"Agent '{agent.name}' created with {tools_info}.")
    return agent


# ===== AGENTS SDK ONLY - RESPONSES API FUNCTIONS REMOVED =====
# All MCP processing now handled by OpenAI Agents SDK with HostedMCPTool
# No need for manual Responses API calls - the SDK handles everything


# ===== LEGACY FUNCTIONS REMOVED =====
# All MCP processing now handled by OpenAI Agents SDK with HostedMCPTool
# The following functions are no longer needed:
# - process_message_with_enhanced_multiturn_mcp
# - process_message_with_zapier_mcp_streaming
# - detect_mcp_from_message
# - get_mcp_tag_name

# Multi-turn execution is now handled natively by the Agents SDK Runner
# which automatically loops between LLM calls and tool executions




import re
async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> dict:
            # Special handling for Gmail with optimized search and content limiting
            stream = client.responses.create(
                model="gpt-4.1",
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
                            "Authorization": f"Bearer {mcp_config['api_key'].strip()}"
                        }
                    }
                ],
                stream=True
            )
        elif mcp_config["server_label"] == "zapier-mcpasana":
            # Special handling for Asana operations
            stream = client.responses.create(
                model="gpt-4.1",
                input=input_data,
                instructions=(
                    f"You are Livia, AI assistant from ℓiⱴε agency with {mcp_config['name']} access.\n\n"
                    "📋 **ASANA PROJECT MANAGEMENT**:\n"
                    "- Sequential search: workspace→project→task\n"
                    "- Always include ALL IDs/numbers from responses\n"
                    "- Limit 4 results, Portuguese responses\n"
                    "- Example: 'Found project Inovação (ev:123) with task Name (ev:456)'\n"
                    "- For task creation: use exact project names and descriptions\n"
                    "- ALWAYS log detailed information about API calls and responses\n\n"
                    "🎯 **GOAL**: Manage projects and tasks efficiently with detailed feedback."
                ),
                tools=[
                    {
                        "type": "mcp",
                        "server_label": mcp_config["server_label"],
                        "server_url": mcp_config["url"],
                        "require_approval": "never",
                        "headers": {
                            "Authorization": f"Bearer {mcp_config['api_key']}"
                        }
                    }
                ],
                stream=True
            )

        elif mcp_config["server_label"] == "zapier-mcpgooglecalendar":
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
                            "Authorization": f"Bearer {mcp_config['api_key'].strip()}"
                        }
                    }
                ],
                stream=True
            )

        elif mcp_config["server_label"] == "zapier-mcpslack":
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
                            "Authorization": f"Bearer {mcp_config['api_key'].strip()}"
                        }
                    }
                ],
                stream=True
            )

        else:
            # Regular MCP processing for other services (Google Drive, etc.)
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
                            "Authorization": f"Bearer {mcp_config['api_key']}"
                        }
                    }
                ],
                stream=True
            )

        # Process streaming response with detailed logging
        full_response = ""
        tool_calls_made = []
        errors_encountered = []

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
                    error_details = {
                        "type": getattr(event, 'type', 'unknown'),
                        "message": getattr(event, 'message', str(event)),
                        "code": getattr(event, 'code', None),
                        "details": getattr(event, 'details', None)
                    }
                    errors_encountered.append(error_details)
                    logger.error(f"🚨 MCP DETAILED ERROR: {error_details}")
                elif hasattr(event, 'type') and 'tool_call' in event.type:
                    tool_call_info = {
                        "type": event.type,
                        "tool_name": getattr(event, 'name', 'unknown'),
                        "arguments": getattr(event, 'arguments', {}),
                        "output": getattr(event, 'output', None),
                        "error": getattr(event, 'error', None)
                    }
                    # --- FILE NAMES for file_search ---
                    if tool_call_info["tool_name"].lower() == "file_search":
                        output = tool_call_info.get("output", "")
                        # Try to extract file names from output: e.g., "Arquivo encontrado: nome_do_arquivo.pdf"
                        file_names = re.findall(r"Arquivo[s]?:?\s*([^\n,]+)", str(output), re.IGNORECASE)
                        if not file_names:
                            # Try to extract pdf/doc/docx/xlsx/names from output string
                            file_names = re.findall(r"[\w\-\_]+\.(?:pdf|docx?|xlsx?|pptx?)", str(output), re.IGNORECASE)
                        tool_call_info["file_names"] = file_names if file_names else []
                    tool_calls_made.append(tool_call_info)
                    logger.info(f"🔧 MCP TOOL CALL: {tool_call_info}")

        logger.info(f"📊 MCP STREAMING SUMMARY:")
        logger.info(f"   - Response length: {len(full_response)} chars")
        logger.info(f"   - Tool calls made: {len(tool_calls_made)}")
        logger.info(f"   - Errors encountered: {len(errors_encountered)}")

        if tool_calls_made:
            logger.info(f"🔧 TOOL CALLS DETAILS:")
            for i, call in enumerate(tool_calls_made, 1):
                logger.info(f"   {i}. {call['tool_name']}: {call.get('error', 'SUCCESS')}")

        if errors_encountered:
            logger.error(f"🚨 ERROR DETAILS:")
            for i, error in enumerate(errors_encountered, 1):
                logger.error(f"   {i}. {error['message']} (Code: {error.get('code', 'N/A')})")

        logger.info(f"✅ MCP Final Response: {full_response}")

        # Calculate token usage
        input_tokens = count_tokens(str(message), "gpt-4.1-mini")
        output_tokens = count_tokens(full_response or "", "gpt-4.1-mini")
        token_usage = {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
        }

        return {"text": full_response or "No response generated.", "tools": tool_calls_made, "token_usage": token_usage}

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error calling {mcp_config['name']} with streaming: {e}")

        # Special handling for Gmail context window exceeded
        if mcp_config["server_label"] == "zapier-mcpgmail" and "context_length_exceeded" in error_message:
            logger.warning("Gmail MCP context window exceeded, trying with simplified request")
            try:
                # Retry with more restrictive search and summarization (non-streaming fallback)
                simplified_response = client.responses.create(
                    model="gpt-4.1",
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
                                "Authorization": f"Bearer {mcp_config['api_key']}"
                            }
                        }
                    ]
                )
                return {"text": simplified_response.output_text or "Não foi possível acessar os emails no momento.", "tools": []}
            except Exception as retry_error:
                logger.error(f"Gmail MCP retry also failed: {retry_error}")
                return {"text": "❌ Não foi possível acessar os emails do Gmail no momento. O email pode ser muito grande para processar. Tente ser mais específico na busca.", "tools": []}

        raise





def detect_zapier_mcp_needed(message: str) -> Optional[str]:
    """
    Detect which Zapier MCP is needed based on message keywords.    """
    Detecta qual MCP do Zapier é necessário com base nas palavras-chave da mensagem.
    
    Args:
        message: Mensagem do usuário para análise
    
    Returns:
        Chave do MCP se detectada, None caso contrário
    """
    message_lower = message.lower()

    # Ordem de prioridade: Serviços mais específicos primeiro para evitar conflitos
    priority_order = ["mcpEverhour", "mcpAsana", "mcpGmail", "mcpGoogleDocs", "mcpGoogleSheets", "mcpGoogleCalendar", "mcpSlack", "google_drive"]
{{ ... }}

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

import re
async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> dict:
    """
    Runs the agent with the given message and optional image URLs with streaming support.
    Now uses unified Agents SDK with native multi-turn execution for all MCPs.

    Args:
        agent: OpenAI Agent instance
        message: User message to process
        image_urls: Optional list of image URLs
        stream_callback: Optional callback for streaming updates

    Returns:
        Dict with 'text', 'tools', and optionally 'structured_data'
    """

    # � All MCPs now handled by Agents SDK with HostedMCPTool - no routing needed!

    # Generate a trace ID for monitoring the agent's execution flow
    trace_id = gen_trace_id()
    logger.info(f"Starting agent run for message: '{message}' with STREAMING. Trace: https://platform.openai.com/traces/{trace_id}")

    if image_urls:
        logger.info(f"Processing {len(image_urls)} image(s): {image_urls}")

    final_output = "Sorry, I couldn't process that." # Default response
    tool_calls_made = []
    try:
        # Start tracing for the agent workflow
        with trace(workflow_name="Livia Slack Agent Workflow", trace_id=trace_id):
            # Prepare input with images if provided (format for OpenAI Agents SDK)
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
                logger.info(f"Prepared vision input with {len(image_urls)} images")
            else:
                # Text-only input
                input_data = message

            result = Runner.run_streamed(starting_agent=agent, input=input_data)

            full_response = ""
            final_message_output = ""

            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    if hasattr(event.data, 'type') and event.data.type == "response.output_text.delta":
                        delta_text = getattr(event.data, 'delta', '')
                        if delta_text:
                            full_response += delta_text
                            if stream_callback:
                                await stream_callback(delta_text, full_response)
                    elif hasattr(event.data, 'type') and event.data.type == "response.completed":
                        logger.info("Agent streaming response completed")
                elif event.type == "run_item_stream_event":
                    if event.item.type == "tool_call_item":
                        # Debug: Log all available attributes
                        logger.info(f"DEBUG: Tool call item attributes: {dir(event.item)}")

                        # Robust extraction of tool_name and tool_type
                        tool_name = getattr(event.item, 'name', '')
                        tool_type = ''

                        # Try extracting from .tool attribute if present
                        tool_obj = getattr(event.item, 'tool', None)
                        if tool_obj:
                            logger.info(f"DEBUG: Tool object attributes: {dir(tool_obj)}")
                            if not tool_name:
                                tool_name = getattr(tool_obj, 'name', '') or getattr(tool_obj, 'type', '')

                        # Try .tool_name attribute
                        if not tool_name:
                            tool_name = getattr(event.item, 'tool_name', '')

                        # Try .tool_type attribute (if present)
                        if not tool_type and hasattr(event.item, 'tool_type'):
                            tool_type = getattr(event.item, 'tool_type', '')

                        # Try function/call attributes
                        if not tool_name:
                            tool_name = getattr(event.item, 'function', {}).get('name', '') if hasattr(event.item, 'function') else ''

                        # Try call_id or id attributes
                        if not tool_name:
                            call_id = getattr(event.item, 'call_id', '') or getattr(event.item, 'id', '')
                            if 'web_search' in call_id.lower():
                                tool_name = 'web_search'
                            elif 'file_search' in call_id.lower():
                                tool_name = 'file_search'

                        # Try raw_json if still missing
                        if (not tool_name or not tool_type) and hasattr(event.item, 'raw_json'):
                            try:
                                raw_json = getattr(event.item, 'raw_json', {})
                                logger.info(f"DEBUG: Raw JSON: {raw_json}")
                                if isinstance(raw_json, dict):
                                    if not tool_name:
                                        tool_name = raw_json.get("name", raw_json.get("tool_name", ""))
                                    if not tool_type:
                                        tool_type = raw_json.get("type", raw_json.get("tool_type", ""))
                            except Exception as e:
                                logger.warning(f"DEBUG: Error parsing raw_json: {e}")

                        # Enhanced detection: Check response content for web search indicators
                        if not tool_name:
                            # Check if response contains web search indicators
                            response_content = full_response.lower()
                            web_indicators = [
                                "brandcolorcode.com", "wikipedia.org", "google.com", "bing.com",
                                "utm_source=openai", "search result", "according to", "source:",
                                "based on search", "found on", "website", ".com", ".org", ".net"
                            ]

                            if any(indicator in response_content for indicator in web_indicators):
                                tool_name = "web_search"
                                logger.info("DEBUG: WebSearch detected from response content indicators")
                            else:
                                # Fallback: Check message for search keywords
                                web_keywords = ["pesquisa", "pesquise", "search", "google", "busca", "procura", "internet", "net"]
                                if any(keyword in message.lower() for keyword in web_keywords):
                                    tool_name = "web_search"
                                    logger.info("DEBUG: Fallback detection - assuming web_search based on message keywords")
                                else:
                                    logger.info("DEBUG: No tool detected, will use model name as tag")
                        tool_call_info = {
                            "type": getattr(event.item, 'type', ''),
                            "tool_name": tool_name or '',
                            "tool_type": tool_type or '',
                            "arguments": getattr(event.item, 'arguments', {}),
                            "output": getattr(event.item, 'output', None),
                            "error": getattr(event.item, 'error', None)
                        }
                        # Special: for file_search, try to extract file_names
                        if (tool_call_info["tool_name"] or "").lower() == "file_search":
                            output = tool_call_info.get("output", "")
                            file_names = re.findall(r"Arquivo[s]?:?\s*([^\n,]+)", str(output), re.IGNORECASE)
                            if not file_names:
                                file_names = re.findall(r"[\w\-\_]+\.(?:pdf|docx?|xlsx?|pptx?)", str(output), re.IGNORECASE)
                            tool_call_info["file_names"] = file_names if file_names else []
                        tool_calls_made.append(tool_call_info)
                        logger.info(f"-- Tool was called during streaming: {tool_call_info}")
                        # Notify stream callback about tool detection
                        if stream_callback:
                            await stream_callback("", full_response, tool_calls_detected=[tool_call_info])
                    elif event.item.type == "tool_call_output_item":
                        logger.info(f"-- Tool output during streaming: {event.item.output}")
                    elif event.item.type == "message_output_item":
                        message_text = ItemHelpers.text_message_output(event.item)
                        if message_text:
                            final_message_output = message_text
                            if message_text != full_response:
                                full_response = message_text
                                if stream_callback:
                                    await stream_callback("", full_response)
                        logger.info(f"-- Message output during streaming: {message_text}")

            final_output = final_message_output or full_response or "No response generated."

            logger.info(f"Agent streaming run completed. Final output: '{final_output}'")

    except Exception as e:
        logger.error(f"Error during agent streaming run (trace_id: {trace_id}): {e}", exc_info=True)
        final_output = f"An error occurred while processing your request: {str(e)}"

    # Calculate token usage
    input_tokens = count_tokens(str(message), agent.model)
    output_tokens = count_tokens(str(final_output), agent.model)
    token_usage = {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens,
    }

    return {"text": str(final_output), "tools": tool_calls_made, "token_usage": token_usage}


# Standalone execution part (optional for the article, but good for context)
# async def main_standalone(): ...
# if __name__ == "__main__": ...