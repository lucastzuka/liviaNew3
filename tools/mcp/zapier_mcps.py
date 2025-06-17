#!/usr/bin/env python3
"""
Zapier MCP Configurations
------------------------
Centralized configuration for all remote MCP integrations via Zapier.
Includes URLs, API keys, keywords, and priority order for detection.
"""

from typing import Optional, Tuple

# Configuration dictionary for all Zapier MCP servers
ZAPIER_MCPS = {
    "google_drive": {
        "name": "Zapier Google Drive MCP",
        "url": "https://mcp.zapier.com/api/mcp/s/0a4332e0-3e88-41cc-b7fd-109d16aef26b/mcp",
        "api_key": "MGE0MzMyZTAtM2U4OC00MWNjLWI3ZmQtMTA5ZDE2YWVmMjZiOjBjODA0ZTZjLTgyNzUtNGEzNC1hNWQ4LTdjNjI2ZTY3YjkwZQ==",
        "server_label": "zapier-gdrive",
        "keywords": ["google drive", "drive", "gdrive"],
        "priority": 1,
        "description": "Google Drive: buscar, listar, criar e gerenciar arquivos e pastas"
    },
    "mcpEverhour": {
        "name": "Zapier mcpEverhour",
        "url": "https://mcp.zapier.com/api/mcp/s/feb69f9d-737e-4c88-aa0e-01331fc75978/mcp",
        "api_key": "ZmViNjlmOWQtNzM3ZS00Yzg4LWFhMGUtMDEzMzFmYzc1OTc4OmNmMWY5Yjg4LWI4NmEtNDRkYi1hY2RjLWFlMzhkZWU3MDBhNg==",
        "server_label": "zapier-mcpeverhour",
        "keywords": ["everhour"],
        "priority": 2,
        "description": "mcpEverhour: controle de tempo, timesheet e rastreamento de horas"
    },
    "mcpGmail": {
        "name": "Zapier mcpGmail",
        "url": "https://mcp.zapier.com/api/mcp/s/8b25ee8b-7f8b-4f41-b985-917a168c87b4/mcp",
        "api_key": "sk-or-v1-8b25ee8b7f8b4f41b985917a168c87b4",
        "server_label": "zapier-mcpgmail",
        "keywords": ["gmail"],
        "priority": 3,
        "description": "mcpGmail: enviar, ler e gerenciar emails"
    },
    "mcpAsana": {
        "name": "Zapier mcpAsana",
        "url": "https://mcp.zapier.com/api/mcp/s/c123456d-7890-1234-5678-901234567890/mcp",
        "api_key": "sk-or-v1-c123456d789012345678901234567890",
        "server_label": "zapier-mcpasana",
        "keywords": ["asana"],
        "priority": 4,
        "description": "mcpAsana: gerenciar projetos, tarefas e workspaces"
    },
    "mcpGoogleCalendar": {
        "name": "Zapier mcpGoogleCalendar",
        "url": "https://mcp.zapier.com/api/mcp/s/d234567e-8901-2345-6789-012345678901/mcp",
        "api_key": "sk-or-v1-d234567e890123456789012345678901",
        "server_label": "zapier-mcpgooglecalendar",
        "keywords": ["calendar"],
        "priority": 5,
        "description": "mcpGoogleCalendar: criar e gerenciar eventos, reuniões e compromissos"
    },
    "mcpGoogleDocs": {
        "name": "Zapier mcpGoogleDocs",
        "url": "https://mcp.zapier.com/api/mcp/s/4270e502-78ca-49bb-a4bb-e9dd4e48228c/mcp",
        "api_key": "NDI3MGU1MDItNzhjYS00OWJiLWE0YmItZTlkZDRlNDgyMjhjOjA3NDM2YmYzLWI4MDMtNDZiOS05N2YyLTkxZTM2NjY2ZmFhNw==",
        "server_label": "zapier-mcpgoogledocs",
        "keywords": ["docs"],
        "priority": 6,
        "description": "mcpGoogleDocs: criar, editar e gerenciar documentos de texto"
    },
    "mcpGoogleSheets": {
        "name": "Zapier mcpGoogleSheets",
        "url": "https://mcp.zapier.com/api/mcp/s/f456789g-0123-4567-8901-234567890123/mcp",
        "api_key": "sk-or-v1-f456789g012345678901234567890123",
        "server_label": "zapier-mcpgooglesheets",
        "keywords": ["sheets"],
        "priority": 7,
        "description": "mcpGoogleSheets: criar, editar e gerenciar planilhas"
    },
    "mcpSlack": {
        "name": "Zapier mcpSlack",
        "url": "https://mcp.zapier.com/api/mcp/s/g567890h-1234-5678-9012-345678901234/mcp",
        "api_key": "sk-or-v1-g567890h123456789012345678901234",
        "server_label": "zapier-mcpslack",
        "keywords": ["slack"],
        "priority": 8,
        "description": "mcpSlack: enviar mensagens para outros workspaces"
    }
}

# Priority order for keyword detection (most specific first)
PRIORITY_ORDER = [
    "google_drive",
    "mcpEverhour",
    "mcpGmail",
    "mcpAsana",
    "mcpGoogleCalendar",
    "mcpGoogleDocs",
    "mcpGoogleSheets",
    "mcpSlack"
]

def get_mcp_by_keywords(message: str) -> Optional[Tuple[str, dict]]:
    """
    Detect which MCP should handle message based on keyword matching.
    Uses priority order to avoid conflicts between similar keywords.
    Returns (mcp_name, mcp_config) or None if no match found.
    """
    message_lower = message.lower()

    # Check MCPs in priority order to handle overlapping keywords
    for mcp_name in PRIORITY_ORDER:
        mcp_config = ZAPIER_MCPS[mcp_name]
        keywords = mcp_config["keywords"]

        # Return first matching MCP based on priority
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
