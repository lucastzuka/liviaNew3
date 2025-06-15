#!/usr/bin/env python3
"""
Zapier MCP configurations for Livia Slack Chatbot
------------------------------------------------
Centralized configuration for all Zapier MCP integrations.
"""

from typing import Optional, Tuple

# Zapier MCP configurations
ZAPIER_MCPS = {
    "google_drive": {
        "name": "Zapier Google Drive MCP",
        "url": "https://mcp.zapier.com/api/mcp/s/0a4332e0-3e88-41cc-b7fd-109d16aef26b/mcp",
        "api_key": "MGE0MzMyZTAtM2U4OC00MWNjLWI3ZmQtMTA5ZDE2YWVmMjZiOjBjODA0ZTZjLTgyNzUtNGEzNC1hNWQ4LTdjNjI2ZTY3YjkwZQ==",
        "server_label": "zapier-gdrive",
        "keywords": ["google drive", "drive", "gdrive"],
        "priority": 1,
        "description": "📁 **Google Drive**: buscar, listar, criar e gerenciar arquivos e pastas"
    },
    "mcpGmail": {
        "name": "Zapier mcpGmail",
        "url": "https://mcp.zapier.com/api/mcp/s/8b25ee8b-7f8b-4f41-b985-917a168c87b4/mcp",
        "api_key": "sk-or-v1-8b25ee8b7f8b4f41b985917a168c87b4",
        "server_label": "zapier-mcpgmail",
        "keywords": ["gmail", "email", "e-mail"],
        "priority": 2,
        "description": "📧 **mcpGmail**: enviar, ler e gerenciar emails"
    },
    "mcpAsana": {
        "name": "Zapier mcpAsana",
        "url": "https://mcp.zapier.com/api/mcp/s/c123456d-7890-1234-5678-901234567890/mcp",
        "api_key": "sk-or-v1-c123456d789012345678901234567890",
        "server_label": "zapier-mcpasana",
        "keywords": ["asana", "task", "projeto"],
        "priority": 3,
        "description": "📋 **mcpAsana**: gerenciar projetos, tarefas e workspaces"
    },
    "mcpGoogleCalendar": {
        "name": "Zapier mcpGoogleCalendar",
        "url": "https://mcp.zapier.com/api/mcp/s/d234567e-8901-2345-6789-012345678901/mcp",
        "api_key": "sk-or-v1-d234567e890123456789012345678901",
        "server_label": "zapier-mcpgooglecalendar",
        "keywords": ["calendar", "calendario", "agenda", "evento"],
        "priority": 4,
        "description": "📅 **mcpGoogleCalendar**: criar e gerenciar eventos, reuniões e compromissos"
    },
    "mcpGoogleDocs": {
        "name": "Zapier mcpGoogleDocs",
        "url": "https://mcp.zapier.com/api/mcp/s/e345678f-9012-3456-7890-123456789012/mcp",
        "api_key": "sk-or-v1-e345678f901234567890123456789012",
        "server_label": "zapier-mcpgoogledocs",
        "keywords": ["docs", "google docs", "documento"],
        "priority": 5,
        "description": "📝 **mcpGoogleDocs**: criar, editar e gerenciar documentos de texto"
    },
    "mcpGoogleSheets": {
        "name": "Zapier mcpGoogleSheets",
        "url": "https://mcp.zapier.com/api/mcp/s/f456789g-0123-4567-8901-234567890123/mcp",
        "api_key": "sk-or-v1-f456789g012345678901234567890123",
        "server_label": "zapier-mcpgooglesheets",
        "keywords": ["sheets", "google sheets", "planilha"],
        "priority": 6,
        "description": "📊 **mcpGoogleSheets**: criar, editar e gerenciar planilhas"
    },
    "mcpSlack": {
        "name": "Zapier mcpSlack",
        "url": "https://mcp.zapier.com/api/mcp/s/g567890h-1234-5678-9012-345678901234/mcp",
        "api_key": "sk-or-v1-g567890h123456789012345678901234",
        "server_label": "zapier-mcpslack",
        "keywords": ["slack", "mensagem"],
        "priority": 7,
        "description": "💬 **mcpSlack**: enviar mensagens para outros workspaces"
    }
}

# Priority order for keyword detection (most specific first)
PRIORITY_ORDER = [
    "google_drive",
    "mcpGmail", 
    "mcpAsana",
    "mcpGoogleCalendar",
    "mcpGoogleDocs",
    "mcpGoogleSheets",
    "mcpSlack"
]

def get_mcp_by_keywords(message: str) -> Optional[Tuple[str, dict]]:
    """
    Detect which MCP should handle the message based on keywords.
    Returns (mcp_name, mcp_config) or None if no match.
    """
    message_lower = message.lower()
    
    # Check in priority order (most specific first)
    for mcp_name in PRIORITY_ORDER:
        mcp_config = ZAPIER_MCPS[mcp_name]
        keywords = mcp_config["keywords"]
        
        # Check if any keyword matches
        for keyword in keywords:
            if keyword in message_lower:
                return mcp_name, mcp_config
    
    return None

def get_all_mcps() -> dict:
    """Get all MCP configurations."""
    return ZAPIER_MCPS

def get_mcp_config(mcp_name: str) -> Optional[dict]:
    """Get specific MCP configuration."""
    return ZAPIER_MCPS.get(mcp_name)
