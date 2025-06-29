#!/usr/bin/env python3
"""
Slack Server
------------
Classe principal do servidor Slack Socket Mode refatorada.
"""

import os
import logging
import ssl
import certifi
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from .config import set_global_agent
from .utils import log_startup
from .event_handlers import EventHandlers
from .message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class SlackSocketModeServer:
    """Trata conexão do Slack e processamento de eventos."""
    
    def __init__(self):
        """Inicializa o servidor, verifica variáveis de ambiente e configura o Bolt App."""
        # Verifica variáveis de ambiente necessárias
        required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"]
        missing_vars = [var for var in required_vars if var not in os.environ]

        if missing_vars:
            raise ValueError(f"Variáveis de ambiente necessárias ausentes: {missing_vars}")

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            logger.info(f"Usando CA bundle do certifi: {certifi.where()}")
        except Exception as e:
            logger.error(f"Erro ao criar contexto SSL usando certifi: {e}", exc_info=True)
            ssl_context = ssl.create_default_context()
            logger.warning("Falling back to default SSL context.")

        async_web_client = AsyncWebClient(
            token=os.environ["SLACK_BOT_TOKEN"],
            ssl=ssl_context
        )

        self.app = AsyncApp(
            client=async_web_client,
            logger=logging.getLogger("slack_bolt_disabled")  # Use a disabled logger
        )

        # Explicitly disable all Slack Bolt logging after app creation
        self.app.logger.setLevel(logging.CRITICAL)
        self.app.logger.disabled = True

        self.socket_mode_handler = AsyncSocketModeHandler(
            self.app,
            os.environ["SLACK_APP_TOKEN"]
        )

        # Log security configuration
        # Use visual logging for startup
        log_startup()

        # Set up event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Configura os handlers de eventos usando a classe EventHandlers."""
        # Create message processor
        message_processor = MessageProcessor(self.app.client)
        
        # Create and setup event handlers
        event_handlers = EventHandlers(self.app, message_processor)
        event_handlers.setup_event_handlers()
        
        # Store references for potential future use
        self.message_processor = message_processor
        self.event_handlers = event_handlers

    async def start_async(self):
        """Starts the Socket Mode server asynchronously."""
        logger.info("Starting Slack Socket Mode server (async)...")
        await self.socket_mode_handler.start_async()


# --- Funções de Inicialização e Limpeza do Agente ---
async def initialize_agent():
    """Initializes the Livia agent (without MCP Slack local - using direct API)."""
    logger.info("Initializing Livia Agent (using direct Slack API)...")

    try:
        from agent.creator import create_agent_with_mcp_servers
        agent = await create_agent_with_mcp_servers()
        set_global_agent(agent)
        logger.info("Livia agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        await cleanup_agent()
        raise


async def cleanup_agent():
    """Cleans up the agent resources."""
    logger.info("Cleaning up Livia agent resources...")


    # For now, just reset the global agent
    set_global_agent(None)
    logger.info("Agent cleanup completed.")


# --- Lógica Principal de Execução ---
async def async_main():
    """Main asynchronous entry point."""
    logger.info("Starting Livia Slack Chatbot...")

    # Check required environment variables
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_TEAM_ID", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if var not in os.environ]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return

    try:
        # Initialize the agent first
        await initialize_agent()
        
        # Create and start the server
        server = SlackSocketModeServer()
        await server.start_async()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
    finally:
        # Clean up resources
        await cleanup_agent()
        logger.info("Livia Slack Chatbot shutdown complete.")


def main():
    """Main synchronous entry point."""
    import asyncio
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    main()
