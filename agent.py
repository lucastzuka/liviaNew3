#!/usr/bin/env python3
"""
Livia - Definição do Agente Chatbot para Slack
----------------------------------------------
Configuração principal do agente Livia usando o OpenAI Agents SDK.
Inclui instruções atemporais, cache de prompts e interpretador de código.
Responde apenas em threads que mencionam o bot na primeira mensagem.
"""

import logging
import time
from pathlib import Path

from security_utils import setup_global_logging_redaction
setup_global_logging_redaction()
from typing import List, Optional
import tiktoken
from dotenv import load_dotenv

# Importa componentes do OpenAI Agents SDK
from agents import (
    Agent,
    Runner,
    gen_trace_id,
    trace,
    WebSearchTool,
    ItemHelpers,
    FileSearchTool,
)
# Importa ferramenta de interpretador de código do OpenAI Agents SDK
from agents import CodeInterpreterTool
from agents.tool import CodeInterpreter

# Importa MCP Server para integração com Zapier MCPs
try:
    from agents.mcp.server import MCPServerSse, MCPServerSseParams
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCPServerSse not available - falling back to hybrid architecture")
    MCP_AVAILABLE = False

# Carrega variáveis de ambiente
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in text for cost calculation and context management."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        # Fallback to default encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


# Import Zapier MCP configurations
from tools.mcp.zapier_mcps import ZAPIER_MCPS

# Zapier MCP configuration is centralized in tools/mcp/zapier_mcps.py
# This includes all remote MCP servers (Asana, Gmail, Google Drive, etc.)

# Note: Local Slack MCP removed - using direct Slack API for better control
# Slack communication handled via slack_bolt in server.py


async def create_agent_with_mcp_servers() -> Agent:
    """Create and configure the main Livia agent with MCP servers from OpenAI Agents SDK."""

    if not MCP_AVAILABLE:
        logger.warning("MCP not available - falling back to hybrid architecture")
        return await create_agent()

    try:
        logger.info("Creating Livia - the Slack Chatbot Agent with MCP servers...")

        # Initialize core tools
        web_search_tool = WebSearchTool(search_context_size="medium")
        # Note: CodeInterpreterTool temporarily disabled due to serialization issues
        # code_interpreter_tool = CodeInterpreterTool(
        #     tool_config=CodeInterpreter(container={"type": "auto"})
        # )

        # Configure file search with vector store for document retrieval
        file_search_tool = FileSearchTool(
            vector_store_ids=["vs_683e3a1ac4808191ae5e6fe24392e609"],
            max_num_results=5,
            include_search_results=True
        )

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
                logger.error(f"Failed to create/connect MCP server for {mcp_config['name']}: {e}")
                # Continue with other servers

        # Core tools only (MCP tools will be added automatically by the agent)
        core_tools = [web_search_tool, file_search_tool]

        # Generate dynamic Zapier tools description from configuration
        zapier_descriptions = []
        for mcp_key, mcp_config in ZAPIER_MCPS.items():
            zapier_descriptions.append(f"  - {mcp_config['description']}")

        zapier_tools_description = (
            "Zapier Integration Tools (via OpenAI Agents SDK MCP Servers):\n"
            + "\n".join(zapier_descriptions) + "\n"
            "Como usar (keywords específicas):\n"
            "  - Para mcpAsana: use 'asana'\n"
            "  - Para mcpEverhour: use 'everhour'\n"
            "  - Para mcpGmail: use 'gmail'\n"
            "  - Para mcpGoogleDocs: use 'docs'\n"
            "  - Para mcpGoogleSheets: use 'sheets'\n"
            "  - Para Google Drive: use 'drive'\n"
            "  - Para mcpGoogleCalendar: use 'calendar'\n"
            "  - Para mcpSlack: use 'slack'\n"
        )

        logger.info(f"Configured {len(mcp_servers)} MCP servers for Zapier MCPs")

        # If no MCP servers connected successfully, fall back to hybrid architecture
        if len(mcp_servers) == 0:
            logger.warning("No MCP servers connected successfully - falling back to hybrid architecture")
            return await create_agent()

        # Create agent with MCP servers
        agent = Agent(
            name="Livia",
            tools=core_tools,  # Core tools: web search, file search
            mcp_servers=mcp_servers,  # MCP servers will provide additional tools automatically
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
- Web Search Tool: search the internet for current information
- File Search Tool: search uploaded documents in the knowledge base
- Image Vision: analyze uploaded images or URLs
- Image Generation Tool: create images with gpt-image-1
- Code Interpreter: run short Python snippets and return the output
- Audio Transcription: convert user audio files to text
- Prompt Caching: reuse stored answers for repeated prompts
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

ELSE IF info changes periodically (e.g., rankings, statistics, trends)
→ ANSWER DIRECTLY but offer to search for latest updates

ELSE IF info changes frequently (e.g., weather, news, stock prices, current events)
→ USE WEB SEARCH immediately for accurate current information

ELSE IF user asks about documents/files
→ USE FILE SEARCH to find relevant documents in knowledge base

ELSE IF user asks for code execution or calculations
→ USE CODE INTERPRETER for Python snippets and computations
</search_strategy>

<response_guidelines>
- NEVER answer with uncertainty - if unsure, USE AVAILABLE TOOLS for verification
- Use web search for current/changing information only
- Use file search when users ask about documents
- Provide detailed image analysis when images are shared - you CAN see and analyze images perfectly
- NEVER say you cannot see images - you have full vision capabilities and should analyze them directly
- Try multiple search strategies if initial attempts fail
- Suggest alternative search terms when no results found

- Correct 'pasta' to 'arquivo' when appropriate
- Cite sources for web searches
- Mention document names for file searches
- Be professional and helpful
- Ask for clarification when needed
- NEVER use slack_post_message - responses handled automatically
- NEVER send messages to other channels
</response_guidelines>
"""
            )
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
    # Note: CodeInterpreterTool temporarily disabled due to serialization issues
    # code_interpreter_tool = CodeInterpreterTool(
    #     tool_config=CodeInterpreter(container={"type": "auto"})
    # )

    # Configure file search with vector store for document retrieval
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

    # MCP servers list (local MCPs only - Zapier MCPs via Responses API with enhanced multi-turn)
    mcp_servers = []
    server_descriptions = []

    logger.info("Using hybrid architecture: Agents SDK for local tools + enhanced Responses API for Zapier MCPs")
    logger.info("Enhanced Responses API now includes manual multi-turn execution for complex workflows")

    # Generate dynamic Zapier tools description from configuration
    zapier_descriptions = []
    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        zapier_descriptions.append(f"  - {mcp_config['description']}")

    zapier_tools_description = (
        "Zapier Integration Tools (Enhanced Multi-Turn via Responses API):\n"
        + "\n".join(zapier_descriptions) + "\n"
        "Enhanced Multi-Turn Execution:\n"
        "  - Improved Responses API with manual multi-turn loops\n"
        "  - Agent will attempt to chain tool calls (e.g., find project → find task → add time)\n"
        "  - Enhanced instructions for complex workflows\n"
        "Como usar (keywords específicas):\n"
        "  - Para mcpAsana: use 'asana'\n"
        "  - Para mcpEverhour: use 'everhour'\n"
        "  - Para mcpGmail: use 'gmail'\n"
        "  - Para mcpGoogleDocs: use 'docs'\n"
        "  - Para mcpGoogleSheets: use 'sheets'\n"
        "  - Para Google Drive: use 'drive'\n"
        "  - Para mcpGoogleCalendar: use 'calendar'\n"
        "  - Para mcpSlack: use 'slack'\n"
        "Dicas:\n"
        "  - IMPORTANTE: TargetGroupIndex_BR2024 é um ARQUIVO, não pasta\n"
        "  - Se não encontrar, tente busca parcial ou termos relacionados\n"
        "  - Instruções aprimoradas para execução em cadeia\n"
    )

    logger.info(f"Configured hybrid architecture with enhanced multi-turn for {len(ZAPIER_MCPS)} Zapier MCPs")

    # Slack communication handled directly via API (no MCP tools needed)

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
- Web Search Tool: search the internet for current information
- File Search Tool: search uploaded documents in the knowledge base
- Image Vision: analyze uploaded images or URLs
- Image Generation Tool: create images with gpt-image-1
- Code Interpreter: run short Python snippets and return the output
- Audio Transcription: convert user audio files to text
- Prompt Caching: reuse stored answers for repeated prompts
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

ELSE IF info changes periodically (e.g., rankings, statistics, trends)
→ ANSWER DIRECTLY but offer to search for latest updates

ELSE IF info changes frequently (e.g., weather, news, stock prices, current events)
→ USE WEB SEARCH immediately for accurate current information

ELSE IF user asks about documents/files
→ USE FILE SEARCH to find relevant documents in knowledge base

ELSE IF user asks for code execution or calculations
→ USE CODE INTERPRETER for Python snippets and computations
</search_strategy>

<response_guidelines>
- NEVER answer with uncertainty - if unsure, USE AVAILABLE TOOLS for verification
- Use web search for current/changing information only
- Use file search when users ask about documents
- Provide detailed image analysis when images are shared - you CAN see and analyze images perfectly
- NEVER say you cannot see images - you have full vision capabilities and should analyze them directly
- Try multiple search strategies if initial attempts fail
- Suggest alternative search terms when no results found

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
        model="gpt-4.1-mini",  # Changed to gpt-4o for better vision support
        tools=[web_search_tool, file_search_tool],  # CodeInterpreterTool temporarily disabled
        mcp_servers=mcp_servers,
    )
    servers_info = " and ".join(server_descriptions)
    logger.info(f"Agent '{agent.name}' created with WebSearchTool and access to {servers_info}.")
    return agent


import re

async def process_message_with_structured_output(mcp_key: str, message: str, image_urls: Optional[List[str]] = None, use_streaming: bool = True) -> dict:
    """
    Process message using OpenAI Responses API with Structured Outputs for reliable JSON schema adherence.

    Args:
        mcp_key: Key for the Zapier MCP to use
        message: User message to process
        image_urls: Optional list of image URLs
        use_streaming: Whether to use streaming (default: True)

    Returns:
        Dict: {"text": ..., "structured_data": {...}, "tools": [...]}
    """
    from openai import OpenAI

    if mcp_key not in ZAPIER_MCPS:
        raise ValueError(f"Unknown MCP key: {mcp_key}. Available: {list(ZAPIER_MCPS.keys())}")

    mcp_config = ZAPIER_MCPS[mcp_key]
    client = OpenAI()

    # Get appropriate schema for this MCP operation
    schema_type = {
        "mcpEverhour": "everhour",
        "mcpAsana": "asana",
        "mcpGmail": "gmail",
        "mcpGoogleDocs": "file_search",
        "mcpGoogleSheets": "file_search",
        "mcpGoogleCalendar": "gmail",  # Similar structure
        "mcpSlack": "gmail"  # Similar structure
    }.get(mcp_key, "unified")

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

    logger.info(f"Processing message with {mcp_config['name']} using Structured Outputs")
    logger.info(f"Schema type: {schema_type}")
    logger.info(f"Streaming: {use_streaming}")

    try:
        # Create the API call (structured outputs temporarily disabled due to API compatibility)
        api_params = {
            "model": "gpt-4o-2024-08-06",  # Required for Structured Outputs
            "input": input_data,
            "instructions": f"You are Livia, AI assistant from ℓiⱴε agency with {mcp_config['name']} access. Provide structured responses following the schema.",
            "tools": [
                {
                    "type": "mcp",
                    "server_label": mcp_config["server_label"],
                    "server_url": mcp_config["url"],
                    "require_approval": "never",
                    "headers": {
                        "Authorization": f"Bearer {mcp_config['api_key'].strip()}"
                    }
                }
            ]
            # Note: text_format parameter removed as it's not supported in Responses API
        }

        if use_streaming:
            api_params["stream"] = True

        response = client.responses.create(**api_params)

        if use_streaming:
            # Handle streaming response
            full_response = ""
            structured_data = None

            for event in response:
                if hasattr(event, 'type'):
                    if event.type == "response.output_text.delta":
                        delta_text = getattr(event, 'delta', '')
                        if delta_text:
                            full_response += delta_text
                    elif event.type == "response.completed":
                        # Structured output streaming completed
                        logger.info("Structured output streaming completed")

            return {
                "text": full_response or "No response generated.",
                "structured_data": structured_data,
                "tools": []
            }
        else:
            # Handle non-streaming response
            if hasattr(response, 'output_parsed'):
                structured_data = response.output_parsed.model_dump()
                response_text = structured_data.get('response_text', response.output_text or "No response generated.")
            else:
                structured_data = None
                response_text = response.output_text or "No response generated."

            return {
                "text": response_text,
                "structured_data": structured_data,
                "tools": []
            }

    except Exception as e:
        logger.error(f"Error with structured output for {mcp_config['name']}: {e}")
        # Fallback to regular processing
        logger.info("Falling back to regular MCP processing")
        return await process_message_with_zapier_mcp_streaming(mcp_key, message, image_urls, None)


async def process_message_with_enhanced_multiturn_mcp(mcp_key: str, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> dict:
    """
    Enhanced multi-turn execution for Zapier MCPs using Responses API.
    Implements manual multi-turn loops for complex workflows like Everhour time tracking.

    Args:
        mcp_key: Key for the Zapier MCP to use
        message: User message to process
        image_urls: Optional list of image URLs
        stream_callback: Optional callback for streaming updates

    Returns:
        Dict: {"text": ..., "tools": [...]}
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

    logger.info(f"Enhanced Multi-Turn Processing with {mcp_config['name']}")
    logger.info(f"Original message: {message}")

    # Enhanced instructions for multi-turn execution with Everhour-specific strategies
    enhanced_instructions = f"""You are Livia, AI assistant from ℓiⱴε agency with {mcp_config['name']} access.

MULTI-TURN EXECUTION STRATEGY:
1. ANALYZE the user request to identify all required steps
2. EXECUTE each step sequentially using available tools
3. CONTINUE until the complete workflow is finished
4. RESPOND only when the entire task is completed

FOR EVERHOUR WORKFLOWS - ENHANCED STRATEGY:

AVAILABLE EVERHOUR COMMANDS:
SEARCH & FIND: everhour_find_internal_project, everhour_find_project, everhour_find_section, everhour_find_member, everhour_find_task
CREATE & MANAGE: everhour_create_client, everhour_create_project, everhour_create_section, everhour_create_task
TIME TRACKING: everhour_start_timer, everhour_stop_timer, everhour_add_time

WORKFLOW STEPS:
- Step 1: Use everhour_find_project to find the project
- Step 2: Try everhour_find_task to find the specific task
- Step 3: IF TASK NOT FOUND: Try everhour_list_tasks for the project to see available tasks
- Step 4: IF STILL NOT FOUND: Try everhour_add_time directly with project ID as taskId (fallback)
- Step 5: Confirm success with details

EVERHOUR TASK SEARCH FALLBACK:
If everhour_find_task returns empty results ({{}}), try these alternatives:
1. Use everhour_list_tasks with the project ID to see all available tasks
2. Look for similar task names in the list
3. DIRECT ID MAPPING: Use these known task IDs directly:
   - "Terminar Livia 2.0" → ev:273393148295192
   - "Teste 1.0" → ev:273447513319222
4. If user mentions "Teste 1.0", use taskId: ev:273447513319222 directly
5. If user mentions "Terminar Livia 2.0", use taskId: ev:273393148295192 directly

DATE HANDLING (Timezone: America/Sao_Paulo):
- 'hoje'/'today' = current date in Brazil timezone
- 'ontem'/'yesterday' = previous day
- 'esta semana'/'this week' = current week range
- Always convert relative dates to YYYY-MM-DD format
- Be precise with dates as this affects timesheet accuracy
- Never hardcode specific dates (e.g., 2024-12-16)
- Let the system determine actual dates at runtime

FOR OTHER WORKFLOWS:
- Break down complex requests into sequential tool calls
- Use results from previous calls to inform next steps
- Don't stop until the complete workflow is finished

CRITICAL RULES:
1. You MUST use everhour tools - never respond without calling tools
2. Do NOT respond to user until ALL required steps are completed
3. Continue calling tools until the entire workflow is finished
4. If you know the task ID directly, use everhour_add_time immediately

REQUIRED ACTIONS FOR TIME TRACKING (Timezone: America/Sao_Paulo):
- ALWAYS call everhour_add_time tool with these parameters:
  - taskId: ev:273447513319222 (for "Teste 1.0")
  - time: "1h" (or user-specified time)
  - date: "today"  # use dynamic date reference in Brazil timezone
  - comment: "Time added via Livia"
- DATE CONVERSION EXAMPLES:
  - "hoje" → current date in YYYY-MM-DD format (Brazil timezone)
  - "ontem" → yesterday's date in YYYY-MM-DD format
  - "segunda-feira" → date of this/next Monday
  - Always convert relative dates to precise YYYY-MM-DD format

RESPONSE FORMAT (Portuguese):
SUCCESS: 'Tempo adicionado com sucesso! [time] na task [task_name] ([task_id])'
ERROR: 'Erro: [specific error details]'

GOAL: Complete the entire multi-step workflow before responding to user.
"""

    try:
        # Create enhanced multi-turn API call with FORCED tool usage
        stream = client.responses.create(
            model="gpt-4.1-mini",
            input=input_data,
            instructions=enhanced_instructions,
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
            tool_choice="required",  # FORCE tool usage - don't allow text-only responses
            stream=True
        )

        # Process streaming response with enhanced logging
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
                    logger.info("Enhanced Multi-Turn MCP streaming response completed")
                elif event.type == "error":
                    error_details = {
                        "type": getattr(event, 'type', 'unknown'),
                        "message": getattr(event, 'message', str(event)),
                        "code": getattr(event, 'code', None),
                        "details": getattr(event, 'details', None)
                    }
                    errors_encountered.append(error_details)
                    logger.error(f"Enhanced Multi-Turn MCP ERROR: {error_details}")
                elif hasattr(event, 'type') and 'tool_call' in event.type:
                    tool_call_info = {
                        "type": event.type,
                        "tool_name": getattr(event, 'name', 'unknown'),
                        "arguments": getattr(event, 'arguments', {}),
                        "output": getattr(event, 'output', None),
                        "error": getattr(event, 'error', None)
                    }
                    tool_calls_made.append(tool_call_info)
                    logger.info(f"Enhanced Multi-Turn TOOL CALL: {tool_call_info}")

        logger.info(f"Enhanced Multi-Turn SUMMARY:")
        logger.info(f"   - Response length: {len(full_response)} chars")
        logger.info(f"   - Tool calls made: {len(tool_calls_made)}")
        logger.info(f"   - Errors encountered: {len(errors_encountered)}")

        if tool_calls_made:
            logger.info(f"MULTI-TURN TOOL SEQUENCE:")
            for i, call in enumerate(tool_calls_made, 1):
                logger.info(f"   {i}. {call['tool_name']}: {call.get('error', 'SUCCESS')}")

        logger.info(f"Enhanced Multi-Turn Final Response: {full_response}")

        # Calculate token usage
        input_tokens = count_tokens(str(message), "gpt-4.1-mini-mini")
        output_tokens = count_tokens(full_response or "", "gpt-4.1-mini-mini")
        token_usage = {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
        }

        return {"text": full_response or "No response generated.", "tools": tool_calls_made, "token_usage": token_usage}

    except Exception as e:
        logger.error(f"Enhanced Multi-Turn MCP processing failed: {e}", exc_info=True)
        # Fallback to regular MCP processing
        logger.info("Falling back to regular MCP processing")
        return await process_message_with_zapier_mcp_streaming(mcp_key, message, image_urls, stream_callback)


async def process_message_with_zapier_mcp_streaming(mcp_key: str, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> dict:
    """
    Generic function to process message using OpenAI Responses API with any Zapier Remote MCP with streaming support.

    Returns:
        Dict: {"text": ..., "tools": [...]}
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
        # ... (unchanged up to stream event loop)

        # Special handling for individual MCPs with detailed logging
        # (code omitted, see above)
        if mcp_config["server_label"] == "zapier-mcpeverhour":
            stream = client.responses.create(
                model="gpt-4.1-mini",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency with Everhour MCP access.\n\n"
                    "EVERHOUR AVAILABLE COMMANDS:\n"
                    "SEARCH & FIND:\n"
                    "- everhour_find_internal_project\n"
                    "- everhour_find_project\n"
                    "- everhour_find_section\n"
                    "- everhour_find_member\n"
                    "- everhour_find_task\n\n"
                    "CREATE & MANAGE:\n"
                    "- everhour_create_client\n"
                    "- everhour_create_project\n"
                    "- everhour_create_section\n"
                    "- everhour_create_task\n\n"
                    "TIME TRACKING:\n"
                    "- everhour_start_timer\n"
                    "- everhour_stop_timer\n"
                    "- everhour_add_time\n\n"
                    "TIME TRACKING WORKFLOW:\n"
                    "- Step 1: Use everhour_find_project to find project\n"
                    "- Step 2: Use everhour_find_task to find specific task\n"
                    "- Step 3: If task not found, try everhour_list_tasks for project\n"
                    "- Step 4: Use everhour_add_time with exact parameters\n"
                    "- Time format: 1h, 2h, 30m (examples: '2h', '1.5h', '30m')\n\n"
                    "DATE & TIME HANDLING (Timezone: America/Sao_Paulo):\n"
                    "- 'hoje' / 'today' = current date in Brazil timezone\n"
                    "- 'ontem' / 'yesterday' = previous day\n"
                    "- 'esta semana' / 'this week' = current week range\n"
                    "- Always convert relative dates to YYYY-MM-DD format\n"
                    "- Current date reference: use system date in Brazil timezone\n"
                    "- For time entries, be precise with dates as this affects timesheet accuracy\n\n"
                    "- Current known tasks in Inovação project (ev:273391483277215):\n"
                    "  * ev:273393148295192 (Terminar Livia 2.0)\n"
                    "  * ev:273447513319222 (Teste 1.0)\n\n"
                    "FALLBACK STRATEGY:\n"
                    "If everhour_find_task returns {{}}, try everhour_list_tasks or use known task IDs\n\n"
                    "RESPONSE FORMAT:\n"
                    "SUCCESS: 'Tempo adicionado com sucesso! [time] na task [task_name] ([task_id])'\n"
                    "ERROR: 'Erro: [details]'\n\n"
                    "GOAL: Add time efficiently and provide clear feedback in Portuguese."
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
        elif mcp_config["server_label"] == "zapier-mcpgmail":
            # Special handling for Gmail with optimized search and content limiting
            stream = client.responses.create(
                model="gpt-4.1-mini",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use Gmail tools to search and read emails.\n\n"
                    "STEP-BY-STEP APPROACH:\n"
                    "1. First: Use gmail_search_emails tool with search string 'in:inbox'\n"
                    "2. Then: Use gmail_get_email tool to read the first email from results\n"
                    "3. Finally: Summarize the email content\n\n"
                    "SEARCH EXAMPLES:\n"
                    "- For latest emails: 'in:inbox'\n"
                    "- For unread emails: 'is:unread'\n"
                    "- For recent emails: 'newer_than:1d'\n"
                    "- Combined: 'in:inbox newer_than:1d'\n\n"
                    "RESPONSE FORMAT (Portuguese):\n"
                    "Último Email Recebido:\n"
                    "De: [sender name and email]\n"
                    "Assunto: [subject line]\n"
                    "Data: [date received]\n"
                    "Resumo: [Brief 2-3 sentence summary of main content]\n\n"
                    "IMPORTANT:\n"
                    "- Always use gmail_search_emails first to find emails\n"
                    "- Then use gmail_get_email to read the specific email\n"
                    "- Summarize content - don't return full email text\n"
                    "- If search fails, try simpler search terms\n\n"
                    "GOAL: Find and summarize the user's latest email efficiently."
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
                model="gpt-4.1-mini",
                input=input_data,
                instructions=(
                    f"You are Livia, AI assistant from ℓiⱴε agency with {mcp_config['name']} access.\n\n"
                    "ASANA PROJECT MANAGEMENT:\n"
                    "- Sequential search: workspace→project→task\n"
                    "- Always include ALL IDs/numbers from responses\n"
                    "- Limit 4 results, Portuguese responses\n"
                    "- Example: 'Found project Inovação (ev:123) with task Name (ev:456)'\n"
                    "- For task creation: use exact project names and descriptions\n"
                    "- ALWAYS log detailed information about API calls and responses\n\n"
                    "GOAL: Manage projects and tasks efficiently with detailed feedback."
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
                model="gpt-4.1-mini",
                input=input_data,
                instructions=(
                    "You are Livia, AI assistant from ℓiⱴε agency. Use Google Calendar tools to search and manage events.\n\n"
                    "Search Strategy:\n"
                    "- Try these tools in order: gcalendar_find_events, gcalendar_search_events, google_calendar_find_events\n"
                    "- Use dynamic date parameters: start_date='today', end_date='next week'\n"
                    "- Default range: today to next 7 days (calculated dynamically)\n"
                    "- Timezone: America/Sao_Paulo\n"
                    "- If no events found, try a broader date range\n\n"
                    "Response Format (Portuguese):\n"
                    "Eventos no Google Calendar:\n"
                    "1. [Nome do Evento]\n"
                    "   - Data: [data]\n"
                    "   - Horário: [hora início] às [hora fim]\n"
                    "   - Link: [link se disponível]\n\n"
                    "IMPORTANT: Always search with explicit date ranges"
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
                model="gpt-4.1-mini",
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
                model="gpt-4.1-mini",
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
                    logger.error(f"MCP DETAILED ERROR: {error_details}")
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
                    logger.info(f"MCP TOOL CALL: {tool_call_info}")

        logger.info(f"MCP STREAMING SUMMARY:")
        logger.info(f"   - Response length: {len(full_response)} chars")
        logger.info(f"   - Tool calls made: {len(tool_calls_made)}")
        logger.info(f"   - Errors encountered: {len(errors_encountered)}")

        if tool_calls_made:
            logger.info(f"TOOL CALLS DETAILS:")
            for i, call in enumerate(tool_calls_made, 1):
                logger.info(f"   {i}. {call['tool_name']}: {call.get('error', 'SUCCESS')}")

        if errors_encountered:
            logger.error(f"ERROR DETAILS:")
            for i, error in enumerate(errors_encountered, 1):
                logger.error(f"   {i}. {error['message']} (Code: {error.get('code', 'N/A')})")

        logger.info(f"MCP Final Response: {full_response}")

        # Calculate token usage
        input_tokens = count_tokens(str(message), "gpt-4.1-mini-mini")
        output_tokens = count_tokens(full_response or "", "gpt-4.1-mini-mini")
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
                    model="gpt-4.1-mini",
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
                return {"text": "Não foi possível acessar os emails do Gmail no momento. O email pode ser muito grande para processar. Tente ser mais específico na busca.", "tools": []}

        raise





def detect_zapier_mcp_needed(message: str) -> Optional[str]:
    """
    Detect which Zapier MCP is needed based on message keywords.
    Detecta qual MCP do Zapier é necessário com base nas palavras-chave da mensagem.

    Args:
        message: Mensagem do usuário para análise

    Returns:
        Chave do MCP se detectada, None caso contrário
    """
    message_lower = message.lower()

    # Ordem de prioridade: Serviços mais específicos primeiro para evitar conflitos
    priority_order = ["mcpEverhour", "mcpAsana", "mcpGmail", "mcpGoogleDocs", "mcpGoogleSheets", "mcpGoogleCalendar", "mcpSlack", "google_drive"]

    for mcp_key in priority_order:
        if mcp_key in ZAPIER_MCPS:
            mcp_config = ZAPIER_MCPS[mcp_key]
            detected_keywords = [kw for kw in mcp_config['keywords'] if kw in message_lower]
            if detected_keywords:
                logger.info(f"Detected {mcp_config['name']} keywords in message: {detected_keywords}")
                logger.info(f"Routing to MCP: {mcp_key}")
                return mcp_key
            else:
                logger.debug(f"No {mcp_config['name']} keywords found in message")

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

    # Check if message needs a specific Zapier MCP (enhanced with multi-turn)
    mcp_needed = detect_zapier_mcp_needed(message)

    if mcp_needed:
        mcp_name = ZAPIER_MCPS[mcp_needed]["name"]
        logger.info(f"Message requires {mcp_name}, routing to Enhanced Zapier MCP with multi-turn")

        try:
            return await process_message_with_enhanced_multiturn_mcp(mcp_needed, message, image_urls, stream_callback)
        except Exception as e:
            logger.warning(f"{mcp_name} failed, falling back to regular agent: {e}")
            # Continue to regular agent processing below

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
        final_output = "Erro: Falha no processamento. Se persistir entre em contato com: <@U046LTU4TT5>"

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