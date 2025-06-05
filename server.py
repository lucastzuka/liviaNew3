# server.py (Key parts related to initialization and structure)

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List

import slack_bolt
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp
# Import AsyncWebClient for SSL config
from slack_sdk.web.async_client import AsyncWebClient
# from slack_sdk.errors import SlackApiError  # Not used currently
import ssl
import certifi # For SSL certificate handling
from agent import (
    create_slack_mcp_server,
    create_agent,
    process_message,
    MCPServerStdio,
)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Global Variables ---
slack_mcp_server: MCPServerStdio | None = None
agent = None
agent_lock = asyncio.Lock()

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

        # Create SSL context using certifi
        # Helps prevent certificate verification errors, especially on macOS
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            logger.info(f"Using CA bundle from certifi: {certifi.where()}")
        except Exception as e:
            logger.error(f"Failed to create SSL context using certifi: {e}", exc_info=True)
            ssl_context = ssl.create_default_context()
            logger.warning("Falling back to default SSL context.")

        # Create an AsyncWebClient instance with Bot Token and custom SSL context
        async_web_client = AsyncWebClient(
            token=os.environ["SLACK_BOT_TOKEN"],
            ssl=ssl_context # Pass the SSL context here
        )

        # Initialize AsyncApp by passing the custom client instance
        # Ensures custom SSL settings are used for API calls
        self.app = AsyncApp(
            client=async_web_client # Pass the client instead of the token directly
        )

        # Initialize Async Socket Mode Handler using the App-Level Token
        self.socket_mode_handler = AsyncSocketModeHandler(
            self.app, # Pass the app instance (containing the custom client)
            os.environ["SLACK_APP_TOKEN"]
        )
        # Set up event handlers
        self._setup_event_handlers()

        # Add a simple test handler to see if we're receiving any events
        @self.app.event("message")
        async def test_message_handler(body, say):
            logger.info(f"TEST: Received any message event: {body}")

        @self.app.event("app_mention")
        async def test_mention_handler(body, say):
            logger.info(f"TEST: Received mention event: {body}")
            await say("I received your mention!")

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
                timestamp = msg.get("ts", "")

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
        image_urls: Optional[List[str]] = None, use_thread_history: bool = True
    ):
        """Sends message to agent and posts response to Slack."""
        global agent
        if not agent: # Check if agent is ready
            logger.error("Livia agent not ready.")
            await say(text="Livia is starting up, please wait.", channel=channel_id, thread_ts=thread_ts_for_reply)
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
                    for img_url in image_urls:
                        processed_url = await self._process_slack_image(img_url)
                        if processed_url:
                            processed_image_urls.append(processed_url)
                    logger.info(f"Successfully processed {len(processed_image_urls)} images")

                # Delegate processing to the agent with image support
                response = await process_message(agent, context_input, processed_image_urls)
                # Post the agent's response back to Slack
                await say(text=str(response), channel=channel_id, thread_ts=thread_ts_for_reply)
                logger.info("Livia responded successfully.")
            except Exception as e:
                logger.error(f"Error during Livia agent processing: {e}", exc_info=True)
                await say(text=f"Sorry, I encountered an error: {str(e)}", channel=channel_id, thread_ts=thread_ts_for_reply)

    def _extract_image_urls(self, event: Dict[str, Any]) -> List[str]:
        """Extract image URLs from Slack event."""
        image_urls = []

        # Check for file uploads
        files = event.get("files", [])
        for file in files:
            if file.get("mimetype", "").startswith("image/"):
                # For Slack uploaded images, we need to use the URL with auth headers
                if "url_private" in file:
                    # Add auth header info to the URL for Slack images
                    slack_image_url = f"{file['url_private']}?token={os.environ.get('SLACK_BOT_TOKEN', '')}"
                    image_urls.append(slack_image_url)
                    logger.info(f"Found uploaded image: {file.get('name', 'unknown')} - {file['url_private']}")

        # Check for image URLs in text (enhanced URL detection)
        text = event.get("text", "")
        import re

        # Pattern for image URLs (more comprehensive)
        url_patterns = [
            r'https?://[^\s<>]+\.(?:jpg|jpeg|png|gif|webp|bmp|tiff)(?:\?[^\s<>]*)?',  # Direct image URLs
            r'https?://[^\s<>]*(?:imgur|flickr|instagram|twitter|facebook)[^\s<>]*',   # Image hosting sites
            r'https?://[^\s<>]*\.(?:com|org|net)/[^\s<>]*\.(?:jpg|jpeg|png|gif|webp)', # Images on websites
        ]

        for pattern in url_patterns:
            found_urls = re.findall(pattern, text, re.IGNORECASE)
            for url in found_urls:
                # Clean up URL (remove trailing punctuation)
                url = re.sub(r'[.,;!?]+$', '', url)
                if url not in image_urls:
                    image_urls.append(url)
                    logger.info(f"Found image URL in text: {url}")

        if image_urls:
            logger.info(f"Total images found: {len(image_urls)}")

        return image_urls

    async def _process_slack_image(self, image_url: str) -> Optional[str]:
        """Process Slack private image URL to make it accessible."""
        try:
            if "files.slack.com" in image_url:
                # For Slack images, we need to download and convert to base64
                import aiohttp
                import base64

                headers = {
                    "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url, headers=headers) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            # Convert to base64 data URL
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            base64_image = base64.b64encode(image_data).decode('utf-8')
                            return f"data:{content_type};base64,{base64_image}"
                        else:
                            logger.error(f"Failed to download Slack image: {response.status}")
                            return None
            else:
                # For external URLs, return as-is
                return image_url

        except Exception as e:
            logger.error(f"Error processing image URL {image_url}: {e}")
            return None

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
                bot_user_id = auth_response["user_id"]
                return f"<@{bot_user_id}>" in text
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
            logger.info(f"Received message event: {event}")

            # Ignore bot messages, empty text, or messages without subtype
            if event.get("bot_id") or not event.get("text"):
                logger.info("Ignoring bot message or empty text")
                return

            channel_id = event.get("channel")
            text = event.get("text", "").strip()
            thread_ts = event.get("thread_ts")

            logger.info(f"Message: '{text}', Channel: {channel_id}, Thread: {thread_ts}")

            # Process thread replies OR direct messages
            if not thread_ts and event.get("channel_type") != "im":
                logger.info("Not a thread reply or DM, ignoring")
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
                    image_urls=image_urls
                )

        @self.app.event("app_mention")
        async def handle_app_mentions(body: Dict[str, Any], say: slack_bolt.Say):
            """Handle app mentions - start new threads or respond in existing ones."""
            event = body.get("event", {})
            logger.info(f"Received app mention event: {event}")

            channel_id = event.get("channel")
            text = event.get("text", "").strip()
            thread_ts = event.get("thread_ts") or event.get("ts")  # Use message ts if no thread

            logger.info(f"App mention - Text: '{text}', Channel: {channel_id}, Thread: {thread_ts}")

            # Remove the mention from the text
            try:
                auth_response = await self.app.client.auth_test()
                bot_user_id = auth_response["user_id"]
                text = text.replace(f"<@{bot_user_id}>", "").strip()
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
            await self._process_and_respond(
                text=text,
                say=say,
                channel_id=channel_id,
                thread_ts_for_reply=thread_ts,
                image_urls=image_urls,
                use_thread_history=False  # Don't use history for initial mentions
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

        # Create the agent with the MCP server
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
            logger.error(f"Error cleaning up MCP server: {e}", exc_info=True)
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