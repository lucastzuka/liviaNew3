#!/usr/bin/env python3
"""
Livia - Definição do Agente Chatbot para Slack (Refatorado)
-----------------------------------------------------------
Arquivo principal refatorado que importa componentes dos módulos separados.
Mantém compatibilidade com o código existente.
"""

# Import all functions from the refactored agent module
from agent import (
    # Configuration
    count_tokens,
    MCP_AVAILABLE,
    ZAPIER_MCPS,

    # Agent creation
    create_agent_with_mcp_servers,
    create_agent,

    # Message processing
    process_message,

    # MCP processing
    detect_zapier_mcp_needed,
    get_available_zapier_mcps,
    process_message_with_structured_output,
    process_message_with_enhanced_multiturn_mcp,
    process_message_with_zapier_mcp_streaming
)