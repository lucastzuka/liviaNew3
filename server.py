#!/usr/bin/env python3
"""
Slack Socket Mode Server for Livia Chatbot
------------------------------------------
Handles Slack events and manages bot responses with anti-loop protection.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List

import slack_bolt
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
import ssl
import certifi
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent import (
    create_slack_mcp_server,
    create_agent,
    process_message,
    MCPServerStdio,
)
from tools import ImageProcessor

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global Variables
slack_mcp_server: MCPServerStdio | None = None
agent = None
agent_lock = asyncio.Lock()
processed_messages = set()
bot_user_id = "U057233T98A"

# DEVELOPMENT SECURITY: Whitelist of allowed channels and users
ALLOWED_CHANNELS = {"C059NNLU3E1"}  # Only this specific channel
ALLOWED_USERS = {"U046LTU4TT5"}     # Only this specific user for DMs
ALLOWED_DM_CHANNELS = set()         # Will be populated with DM channel IDs for allowed users

# --- Security Functions ---
async def is_channel_allowed(channel_id: str, user_id: str, app_client) -> bool:
    """
    DEVELOPMENT SECURITY: Check if the channel is allowed for bot responses.
    Only allows specific whitelisted channels and DMs with specific users.
    """
    global ALLOWED_DM_CHANNELS

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
            logger.error(f"SECURITY: Error checking channel info for {channel_id}: {e}")

    # Check if it's a cached DM channel
    if channel_id in ALLOWED_DM_CHANNELS:
        return True

    logger.warning(f"SECURITY: Channel {channel_id} with user {user_id} - BLOCKED")
    return False

# --- Server Class ---
class SlackSocketModeServer:
    """Handles Slack connection and event processing."""
    def __init__(self):
        """Initializes the server, checks env vars, sets up Bolt App."""
        # Check required environment variables
        required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"]
        missing_vars = [var for var in required_vars if var not in os.environ]

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            logger.info(f"Using CA bundle from certifi: {certifi.where()}")
        except Exception as e:
            logger.error(f"Failed to create SSL context using certifi: {e}", exc_info=True)
            ssl_context = ssl.create_default_context()
            logger.warning("Falling back to default SSL context.")

        async_web_client = AsyncWebClient(
            token=os.environ["SLACK_BOT_TOKEN"],
            ssl=ssl_context
        )

        self.app = AsyncApp(
            client=async_web_client
        )

        self.socket_mode_handler = AsyncSocketModeHandler(
            self.app,
            os.environ["SLACK_APP_TOKEN"]
        )

        # Log security configuration
        logger.info("🔒 DEVELOPMENT SECURITY ENABLED:")
        logger.info(f"   Allowed channels: {ALLOWED_CHANNELS}")
        logger.info(f"   Allowed users for DMs: {ALLOWED_USERS}")
        logger.info("   All other channels/users will be BLOCKED")

        # Set up event handlers
        self._setup_event_handlers()



    # --- Thread History Fetching Method ---
    async def _fetch_thread_history(self, channel_id: str, thread_ts: str) -> Optional[str]:
        """Fetches and formats thread history."""
        try:
            logger.debug(f"Fetching history for thread {channel_id}/{thread_ts}...")

            # Get thread replies
            response = await self.app.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=50  # Limit to last 50 messages
            )

            if not response["ok"]:
                logger.warning(f"Failed to fetch thread history: {response.get('error', 'Unknown error')}")
                return None

            messages = response.get("messages", [])
            if not messages:
                return None

            # Format the thread history
            formatted_history = "Thread History:\n"
            for msg in messages:
                user_id = msg.get("user", "Unknown")
                text = msg.get("text", "")

                # Get user info for better formatting
                try:
                    user_info = await self.app.client.users_info(user=user_id)
                    username = user_info["user"]["display_name"] or user_info["user"]["real_name"] or user_id
                except:
                    username = user_id

                formatted_history += f"[{username}]: {text}\n"

            return formatted_history

        except Exception as e:
            logger.error(f"Error fetching thread history: {e}", exc_info=True)
            return None

    # --- Message Processing & Response Method ---
    async def _process_and_respond(
        self, text: str, say: slack_bolt.Say, channel_id: str, thread_ts_for_reply: Optional[str] = None,
        image_urls: Optional[List[str]] = None, use_thread_history: bool = True, user_id: str = None
    ):
        """Sends message to agent and posts response to Slack."""
        global agent
        if not agent: # Check if agent is ready
            logger.error("Livia agent not ready.")
            await say(text="Livia is starting up, please wait.", channel=channel_id, thread_ts=thread_ts_for_reply)
            return

        # Store the original channel for validation
        original_channel_id = channel_id

        # Check if channel is allowed
        if not await is_channel_allowed(channel_id, user_id or "unknown", self.app.client):
            return  # Silently ignore unauthorized channels

        if text and any(phrase in text.lower() for phrase in [
            "encontrei o arquivo", "você pode acessá-lo", "estou à disposição",
            "não consegui encontrar", "vou procurar", "aqui está"
        ]):
            logger.info("Detected bot's own response pattern, skipping processing")
            return

        context_input = text

        # Use thread history as context if available
        if use_thread_history and thread_ts_for_reply:
            logger.info(f"Fetching history for thread {thread_ts_for_reply}...")
            full_history = await self._fetch_thread_history(channel_id, thread_ts_for_reply)
            if full_history:
                context_input = full_history + f"\n\nLatest message: {text}"
            else:
                logger.warning("Failed to fetch thread history.")

        async with agent_lock: # Ensure only one request processed at a time
            try:
                logger.info(f"Processing message via Livia agent...")

                # Process image URLs if any
                processed_image_urls = []
                if image_urls:
                    logger.info(f"Processing {len(image_urls)} images...")
                    processed_image_urls = await ImageProcessor.process_image_urls(image_urls)

                # Delegate processing to the agent with image support
                response = await process_message(agent, context_input, processed_image_urls)

                # Always respond in the original channel
                logger.info(f"USER REQUEST: {context_input}")
                logger.info(f"BOT RESPONSE: {response}")
                await say(text=str(response), channel=original_channel_id, thread_ts=thread_ts_for_reply)
            except Exception as e:
                logger.error(f"Error during Livia agent processing: {e}", exc_info=True)
                await say(text=f"Sorry, I encountered an error: {str(e)}", channel=original_channel_id, thread_ts=thread_ts_for_reply)

    def _extract_image_urls(self, event: Dict[str, Any]) -> List[str]:
        """Extract image URLs from Slack event."""
        return ImageProcessor.extract_image_urls(event)

    async def _process_slack_image(self, image_url: str) -> Optional[str]:
        """Process Slack private image URL to make it accessible."""
        return await ImageProcessor.process_slack_image(image_url)

    async def _is_thread_started_with_mention(self, channel_id: str, thread_ts: str) -> bool:
        """Check if a thread was started with a mention to Livia."""
        try:
            # Get the first message of the thread
            response = await self.app.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1,
                oldest=thread_ts
            )

            if not response["ok"] or not response.get("messages"):
                return False

            first_message = response["messages"][0]
            text = first_message.get("text", "")

            # Check if the first message mentions the bot
            try:
                auth_response = await self.app.client.auth_test()
                current_bot_id = auth_response["user_id"]
                return f"<@{current_bot_id}>" in text
            except Exception as e:
                logger.error(f"Error getting bot user ID for thread check: {e}")
                # Fallback: check for any mention pattern
                import re
                return bool(re.search(r'<@[A-Z0-9]+>', text))

        except Exception as e:
            logger.error(f"Error checking thread start: {e}", exc_info=True)
            return False


    # --- Event Handler Setup ---
    def _setup_event_handlers(self):
        """Sets up handlers for 'message' and 'app_mention' events."""

        @self.app.event("message")
        async def handle_message_events(body: Dict[str, Any], say: slack_bolt.Say):
            """Handle message events - only respond in threads that started with a mention."""
            event = body.get("event", {})


            if (event.get("bot_id") or
                not event.get("text") or
                event.get("user") == bot_user_id):
                logger.info("Ignoring bot message, empty text, or message from bot itself")
                return

            # DEVELOPMENT SECURITY: Early channel validation
            channel_id = event.get("channel")
            user_id = event.get("user")
            if not await is_channel_allowed(channel_id, user_id, self.app.client):
                logger.warning(f"SECURITY: Blocked message event from unauthorized channel {channel_id}")
                return

            message_id = f"{event.get('channel')}_{event.get('ts')}"
            if message_id in processed_messages:
                logger.info(f"Message {message_id} already processed, skipping")
                return
            processed_messages.add(message_id)

            if len(processed_messages) > 100:
                processed_messages.clear()

            text = event.get("text", "").strip()
            thread_ts = event.get("thread_ts")

            logger.info(f"Message: '{text}', Channel: {channel_id}, Thread: {thread_ts}")

            # Check if this is a mention in the message text (fallback detection)
            is_mention_in_text = f"<@{bot_user_id}>" in text

            # Process thread replies, direct messages, OR mentions in text
            if not thread_ts and event.get("channel_type") != "im" and not is_mention_in_text:
                logger.info("Not a thread reply, DM, or mention - ignoring")
                return

            if is_mention_in_text and thread_ts:
                logger.info("Mention in thread detected, will be handled by app_mention event")
                return

            # Skip mentions in message events - they'll be handled by app_mention
            if is_mention_in_text:
                logger.info("Mention detected in message event, will be handled by app_mention event")
                return

            # For DMs, always process. For threads, check if started with mention
            should_process = False
            if event.get("channel_type") == "im":
                logger.info("Direct message, processing...")
                should_process = True
            elif thread_ts and await self._is_thread_started_with_mention(channel_id, thread_ts):
                logger.info("Thread started with mention, processing...")
                should_process = True
            else:
                logger.info("Thread did not start with mention, ignoring")

            if should_process:
                image_urls = self._extract_image_urls(event)
                await self._process_and_respond(
                    text=text,
                    say=say,
                    channel_id=channel_id,
                    thread_ts_for_reply=thread_ts,
                    image_urls=image_urls,
                    user_id=event.get("user")
                )

        @self.app.event("app_mention")
        async def handle_app_mentions(body: Dict[str, Any], say: slack_bolt.Say):
            """Handle app mentions - start new threads or respond in existing ones."""
            event = body.get("event", {})


            if event.get("user") == "U057233T98A":  # Bot user ID
                logger.info("Ignoring app mention from bot itself")
                return

            # DEVELOPMENT SECURITY: Early channel validation
            channel_id = event.get("channel")
            user_id = event.get("user")
            if not await is_channel_allowed(channel_id, user_id, self.app.client):
                logger.warning(f"SECURITY: Blocked app mention from unauthorized channel {channel_id}")
                return

            # Create unique ID for this mention to prevent duplicates
            mention_id = f"mention_{event.get('channel')}_{event.get('ts')}"

            # Check if we already processed this specific mention
            if mention_id in processed_messages:
                logger.info(f"Mention {mention_id} already processed, skipping")
                return

            text = event.get("text", "").strip()
            thread_ts = event.get("thread_ts") or event.get("ts")  # Use message ts if no thread

            logger.info(f"App mention - Text: '{text}', Channel: {channel_id}, Thread: {thread_ts}")

            # Remove the mention from the text
            try:
                auth_response = await self.app.client.auth_test()
                current_bot_id = auth_response["user_id"]
                text = text.replace(f"<@{current_bot_id}>", "").strip()
                logger.info(f"Cleaned text after removing mention: '{text}'")
            except Exception as e:
                logger.error(f"Error getting bot user ID: {e}")
                # Fallback: try to remove any mention pattern
                import re
                text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
                logger.info(f"Fallback cleaned text: '{text}'")

            if not text:
                text = "Hello! How can I help you?"

            logger.info(f"Processing mention with text: '{text}'")
            image_urls = self._extract_image_urls(event)

            # Mark this mention as processed BEFORE processing to prevent duplicates
            processed_messages.add(mention_id)

            # Clean up old processed messages to prevent memory issues
            if len(processed_messages) > 100:
                processed_messages.clear()
                logger.info("Cleared processed messages cache")

            await self._process_and_respond(
                text=text,
                say=say,
                channel_id=channel_id,
                thread_ts_for_reply=thread_ts,
                image_urls=image_urls,
                use_thread_history=False,  # Don't use history for initial mentions
                user_id=event.get("user")
            )

    # --- Server Start Method ---
    async def start(self):
        """Starts the Socket Mode server asynchronously."""
        logger.info("Starting Slack Socket Mode server (async)...")
        await self.socket_mode_handler.start_async()

# --- Agent Initialization and Cleanup Functions ---
async def initialize_agent():
    """Initializes the global agent and MCP server instances."""
    global slack_mcp_server, agent

    logger.info("Initializing Livia Slack MCP Server and Agent...")

    try:
        # Create and start the Slack MCP server
        slack_mcp_server = await create_slack_mcp_server()
        await slack_mcp_server.__aenter__()  # Start the MCP server context

        # Create the agent with the MCP server (Zapier Asana is integrated via Remote MCP)
        agent = await create_agent(slack_mcp_server)

        logger.info("Livia agent successfully initialized.")

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        await cleanup_agent()
        raise

async def cleanup_agent():
    """Cleans up the MCP server resources."""
    global slack_mcp_server, agent

    logger.info("Cleaning up Livia agent resources...")

    if slack_mcp_server:
        try:
            await slack_mcp_server.__aexit__(None, None, None)
            logger.info("Slack MCP server cleaned up.")
        except Exception as e:
            logger.error(f"Error cleaning up Slack MCP server: {e}", exc_info=True)
        finally:
            slack_mcp_server = None

    agent = None
    logger.info("Agent cleanup completed.")

# --- Main Execution Logic ---
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
        # Initialize the agent
        await initialize_agent()

        # Create and start the Slack server
        server = SlackSocketModeServer()
        await server.start()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
    finally:
        # Clean up resources
        await cleanup_agent()
        logger.info("Livia Slack Chatbot shutdown complete.")

def main():
    """Main synchronous entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()