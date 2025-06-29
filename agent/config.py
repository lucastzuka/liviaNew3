#!/usr/bin/env python3
"""
Livia Agent Configuration
------------------------
Configuração e inicialização do agente Livia.
Inclui setup de logging, variáveis de ambiente e imports necessários.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional
import tiktoken
from dotenv import load_dotenv

from security_utils import setup_global_logging_redaction
setup_global_logging_redaction()

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

# Carrega variáveis de ambiente
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importa MCP Server para integração com Zapier MCPs
try:
    from agents.mcp.server import MCPServerSse, MCPServerSseParams
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCPServerSse not available - falling back to hybrid architecture")
    MCP_AVAILABLE = False

# Import Zapier MCP configurations
from tools.mcp.zapier_mcps import ZAPIER_MCPS

# Import thinking agent tool
from tools.thinking_agent import get_thinking_tool


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in text for cost calculation and context management."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        # Fallback to default encoding if model not found
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def get_agent_instructions(zapier_tools_description: str) -> str:
    """Get the main agent instructions with dynamic Zapier tools description."""
    return f"""<identity>
You are Livia, an intelligent chatbot assistant working at ℓiⱴε, a Brazilian advertising agency. You operate in Slack channels, groups, and DMs.
</identity>

<communication_style>
- BE EXTREMELY CONCISE AND BRIEF - this is your primary directive
- Default to short, direct answers unless explicitly asked for details
- One sentence responses are preferred for simple questions
- Avoid unnecessary explanations, steps, or elaborations
- Always respond in the same language the user communicates with you
- Use Slack formatting: *bold*, _italic_, ~strikethrough~
- NEVER mention yourself or use self-references in responses
- Only mention File Search or file names when explicitly asked about documents
- Feel free to disagree constructively to improve results
</communication_style>

<available_tools>
- Web Search Tool: search the internet for current information
- File Search Tool: search uploaded documents in the knowledge base
- Deep Thinking Analysis: use +think or 'thinking' for complex analysis with o3-mini
- Image Vision: analyze uploaded images or URLs
- Image Generation Tool: create images with gpt-image-1
- Code Interpreter: run short Python snippets and return the output
- Audio Transcription: convert user audio files to text
- Prompt Caching: reuse stored answers for repeated prompts
{zapier_tools_description}
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

ELSE IF user requests deep analysis, thinking, or complex problem-solving
→ USE DEEP THINKING ANALYSIS tool with keywords: +think, thinking, análise profunda
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


def generate_zapier_tools_description() -> str:
    """Generate dynamic Zapier tools description from configuration."""
    zapier_descriptions = []
    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        zapier_descriptions.append(f"  - {mcp_config['description']}")

    return (
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


def generate_enhanced_zapier_tools_description() -> str:
    """Generate enhanced Zapier tools description for hybrid architecture."""
    zapier_descriptions = []
    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        zapier_descriptions.append(f"  - {mcp_config['description']}")

    return (
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
