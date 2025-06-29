#!/usr/bin/env python3
"""
Server Configuration
--------------------
Configurações de segurança e variáveis globais do servidor Slack.
"""

import os
import logging
import asyncio
import math
from typing import Set

# Variáveis Globais
agent = None  # Agente OpenAI principal

# Semáforo de concorrência para múltiplos usuários
try:
    max_concurrency = int(os.environ.get("LIVIA_MAX_CONCURRENCY", "5"))
    if max_concurrency < 1:
        raise ValueError
except Exception:
    logging.warning("Invalid LIVIA_MAX_CONCURRENCY, falling back to 5")
    max_concurrency = 5

agent_semaphore = asyncio.Semaphore(max_concurrency)
processed_messages = set()  # Cache de mensagens processadas
bot_user_id = "U057233T98A"  # ID do bot no Slack - IMPORTANTE para detectar menções

# Sistema de cache de prompts para reduzir custos de API em consultas repetidas
prompt_cache = {}
PROMPT_CACHE_LIMIT = 100  # Maximum cached responses before cleanup

# Unified Agents SDK configuration - all MCPs now use native multi-turn execution
logging.info("Using unified Agents SDK with native multi-turn execution for all MCPs")

# 🔒 STRICT DEVELOPMENT SECURITY: ONLY CHANNEL C059NNLU3E1 ALLOWED
ALLOWED_CHANNELS = {"C059NNLU3E1"}  # ONLY this specific channel - NO DMs, NO other channels
DEVELOPMENT_MODE = True             # Set to False for production
ALLOWED_USERS = set()               # NO DMs allowed in development mode
ALLOWED_DM_CHANNELS = set()         # NO DMs allowed in development mode

# 🔇 LOG LIMPO: Exibe apenas interações reais do bot, oculta blocos de segurança
SHOW_SECURITY_BLOCKS = False       # Set to True to see all security blocks in terminal
SHOW_DEBUG_LOGS = False             # Set to True to see debug logs
SHOW_AGENT_LOGS = False             # Set to True to see detailed agent logs


async def is_channel_allowed(channel_id: str, user_id: str, app_client) -> bool:
    """
    STRICT DEVELOPMENT SECURITY: ONLY allows channel C059NNLU3E1
    BLOCKS ALL other channels, DMs, groups, and private channels.
    """
    if DEVELOPMENT_MODE:
        # STRICT: Only allow the specific development channel
        if channel_id in ALLOWED_CHANNELS:
            # Only log allowed channels in debug mode
            if SHOW_DEBUG_LOGS:
                logging.debug(f"SECURITY: Channel {channel_id} ALLOWED (development channel)")
            return True
        else:
            # Only show security blocks if explicitly enabled
            if SHOW_SECURITY_BLOCKS:
                logging.warning(f"SECURITY: Channel {channel_id} with user {user_id} - BLOCKED (development mode)")
            return False
    else:
        # Production mode (when DEVELOPMENT_MODE = False)
        # Check if it's the allowed public channel
        if channel_id in ALLOWED_CHANNELS:
            return True

        # Check if it's a DM with an allowed user
        if user_id in ALLOWED_USERS:
            try:
                # Get channel info to check if it's a DM
                channel_info = await app_client.conversations_info(channel=channel_id)
                if channel_info["ok"] and channel_info["channel"]["is_im"]:
                    ALLOWED_DM_CHANNELS.add(channel_id)  # Cache DM channel ID
                    return True
            except Exception as e:
                logging.error(f"SECURITY: Error checking channel info for {channel_id}: {e}")

        # Check if it's a cached DM channel
        if channel_id in ALLOWED_DM_CHANNELS:
            return True

        # Only show security blocks if explicitly enabled
        if SHOW_SECURITY_BLOCKS:
            logging.warning(f"SECURITY: Channel {channel_id} with user {user_id} - BLOCKED")
        return False


def get_global_agent():
    """Get the global agent instance."""
    return agent


def set_global_agent(new_agent):
    """Set the global agent instance."""
    global agent
    agent = new_agent


def get_agent_semaphore():
    """Get the agent semaphore for concurrency control."""
    return agent_semaphore


def get_processed_messages():
    """Get the processed messages cache."""
    return processed_messages


def get_bot_user_id():
    """Get the bot user ID."""
    return bot_user_id


def get_prompt_cache():
    """Get the prompt cache dictionary."""
    return prompt_cache


def get_security_config():
    """Get security configuration."""
    return {
        "allowed_channels": ALLOWED_CHANNELS,
        "development_mode": DEVELOPMENT_MODE,
        "allowed_users": ALLOWED_USERS,
        "allowed_dm_channels": ALLOWED_DM_CHANNELS,
        "show_security_blocks": SHOW_SECURITY_BLOCKS,
        "show_debug_logs": SHOW_DEBUG_LOGS,
        "show_agent_logs": SHOW_AGENT_LOGS
    }
