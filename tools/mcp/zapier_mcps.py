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
    "mcpEverhour": {
        "name": "Zapier mcpEverhour",
        "url": "https://mcp.zapier.com/api/mcp/s/feb69f9d-737e-4c88-aa0e-01331fc75978/mcp",
        "api_key": "ZmViNjlmOWQtNzM3ZS00Yzg4LWFhMGUtMDEzMzFmYzc1OTc4OmNmMWY5Yjg4LWI4NmEtNDRkYi1hY2RjLWFlMzhkZWU3MDBhNg==",
        "server_label": "zapier-mcpeverhour",
        "keywords": ["everhour"],
        "priority": 2,
        "description": "⏰ **mcpEverhour**: controle de tempo, timesheet e rastreamento de horas"
    },
    "mcpGmail": {
        "name": "Zapier mcpGmail",
        "url": "https://mcp.zapier.com/api/mcp/s/8b25ee8b-7f8b-4f41-b985-917a168c87b4/mcp",
        "api_key": "OGIyNWVlOGItN2Y4Yi00ZjQxLWI5ODUtOTE3YTE2OGM4N2I0OmE5NDgzMzY2LTVlYTMtNDliNS04NjQ2LWQ5YmJiMGI2NWJmZg==",
        "server_label": "zapier-mcpgmail",
        "keywords": ["gmail"],
        "priority": 3,
        "description": "📧 **mcpGmail**: enviar, ler e gerenciar emails"
    },
    "mcpAsana": {
        "name": "Zapier mcpAsana",
        "url": "https://mcp.zapier.com/api/mcp/s/cdd634f5-9842-41eb-8847-d5916e001ade/mcp",
        "api_key": "Y2RkNjM0ZjUtOTg0Mi00MWViLTg4NDctZDU5MTZlMDAxYWRlOmMxNmMxNjk0LTViYzMtNDViMC04MjI5LWFlYmUzYTVlZmEzMw==",
        "server_label": "zapier-mcpasana",
        "keywords": ["asana"],
        "priority": 4,
        "description": "📋 **mcpAsana**: gerenciar projetos, tarefas e workspaces"
    },
    "mcpGoogleCalendar": {
        "name": "Zapier mcpGoogleCalendar",
        "url": "https://mcp.zapier.com/api/mcp/s/fe3bee78-5a79-4bee-9ab5-1ab70068db39/mcp",
        "api_key": "ZmUzYmVlNzgtNWE3OS00YmVlLTlhYjUtMWFiNzAwNjhkYjM5Ojk3YWE4NWFiLWE2ZDAtNGMyNS05NTdkLTFjMTllMDE1OTgzZg==",
        "server_label": "zapier-mcpgooglecalendar",
        "keywords": ["calendar"],
        "priority": 5,
        "description": "📅 **mcpGoogleCalendar**: criar e gerenciar eventos, reuniões e compromissos"
    },
    "mcpGoogleDocs": {
        "name": "Zapier mcpGoogleDocs",
        "url": "https://mcp.zapier.com/api/mcp/s/4270e502-78ca-49bb-a4bb-e9dd4e48228c/mcp",
        "api_key": "NDI3MGU1MDItNzhjYS00OWJiLWE0YmItZTlkZDRlNDgyMjhjOjA3NDM2YmYzLWI4MDMtNDZiOS05N2YyLTkxZTM2NjY2ZmFhNw==",
        "server_label": "zapier-mcpgoogledocs",
        "keywords": ["docs"],
        "priority": 6,
        "description": "📝 **mcpGoogleDocs**: criar, editar e gerenciar documentos de texto"
    },
    "mcpGoogleSheets": {
        "name": "Zapier mcpGoogleSheets",
        "url": "https://mcp.zapier.com/api/mcp/s/401a7b31-986b-43cc-87d3-3e249be5c095/mcp",
        "api_key": "NDAxYTdiMzEtOTg2Yi00M2NjLTg3ZDMtM2UyNDliZTVjMDk1OjgwMzRmNTg4LWFkYWMtNGVkYy05NGE0LWQ2YjI5ZmNhYzI0Yw==",
        "server_label": "zapier-mcpgooglesheets",
        "keywords": ["sheets"],
        "priority": 7,
        "description": "📊 **mcpGoogleSheets**: criar, editar e gerenciar planilhas"
    },
    "mcpSlack": {
        "name": "Zapier mcpSlack",
        "url": "https://mcp.zapier.com/api/mcp/s/4df0a3db-32f5-458c-94e0-1553028ad4be/mcp",
        "api_key": "NGRmMGEzZGItMzJmNS00NThjLTk0ZTAtMTU1MzAyOGFkNGJlOjk5ZmNmMjc0LWI1MjEtNDI3OC1iZTI1LWE4ZDAxZDliNDNiZg==",
        "server_label": "zapier-mcpslack",
        "keywords": ["slack"],
        "priority": 8,
        "description": "💬 **mcpSlack**: se comunicar com o slack"
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
