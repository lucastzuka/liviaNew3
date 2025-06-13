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
    create_agent,
    process_message,
)
from tools import ImageProcessor, image_generator
from slack_formatter import format_message_for_slack

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global Variables
# TODO: SLACK_INTEGRATION_POINT - Variáveis globais para integração com Slack
agent = None  # Agente OpenAI principal

# --- Per-Conversation Lock Manager ---
import threading
conversation_locks: Dict[str, asyncio.Lock] = {}
conversation_locks_lock = threading.Lock()

def get_conversation_lock(key: str) -> asyncio.Lock:
    """Returns an asyncio.Lock for a conversation key (thread or channel)."""
    # Use a threading.Lock to synchronize access to the conversation_locks dict
    with conversation_locks_lock:
        lock = conversation_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            conversation_locks[key] = lock
        # Optionally clean up if too many locks are created (memory bound)
        if len(conversation_locks) > 500:
            conversation_locks.clear()
        return lock

processed_messages = set()  # Cache de mensagens processadas
bot_user_id = "U057233T98A"  # ID do bot no Slack - IMPORTANTE para detectar menções

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

    # --- Streaming Message Processing & Response Method ---
    async def _process_and_respond_streaming(
        self, text: str, say: slack_bolt.Say, channel_id: str, thread_ts_for_reply: Optional[str] = None,
        image_urls: Optional[List[str]] = None, audio_files: Optional[List[dict]] = None,
        use_thread_history: bool = True, user_id: str = None
    ):
        """
        Sends message to agent and posts streaming response to Slack, with per-conversation concurrency lock.
        """
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

        # Process audio files if any
        if audio_files:
            logger.info(f"Processing {len(audio_files)} audio file(s)...")
            transcriptions = []

            for audio_file in audio_files:
                logger.info(f"Transcribing audio file: {audio_file['name']}")
                transcription = await self._transcribe_audio_file(audio_file)

                if transcription:
                    transcriptions.append(f"🎵 **Áudio '{audio_file['name']}'**: {transcription}")
                    logger.info(f"Audio transcribed: {audio_file['name']} -> {len(transcription)} chars")
                else:
                    transcriptions.append(f"❌ **Erro ao transcrever áudio '{audio_file['name']}'**")
                    logger.warning(f"Failed to transcribe audio: {audio_file['name']}")

            # Combine transcriptions with text
            if transcriptions:
                if text:
                    context_input = f"{text}\n\n" + "\n\n".join(transcriptions)
                else:
                    context_input = "\n\n".join(transcriptions)

        # Use thread history as context if available
        if use_thread_history and thread_ts_for_reply:
            logger.info(f"Fetching history for thread {thread_ts_for_reply}...")
            full_history = await self._fetch_thread_history(channel_id, thread_ts_for_reply)
            if full_history:
                context_input = full_history + f"\n\nLatest message: {context_input}"
            else:
                logger.warning("Failed to fetch thread history.")

        # --- Per-conversation locking ---
        conv_key = thread_ts_for_reply if thread_ts_for_reply else channel_id
        logger.info(f"[CONV_LOCK] Processing conversation {conv_key}")
        async with get_conversation_lock(conv_key):
            try:
                logger.info(
                    f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] Processing message via Livia agent with STREAMING..."
                )

                # Check if this is an image generation request
                image_generation_keywords = [
                    "gere uma imagem", "gerar imagem", "criar imagem", "desenhe", "desenhar",
                    "faça uma imagem", "fazer imagem", "generate image", "create image", "draw"
                ]

                is_image_generation = any(keyword in text.lower() for keyword in image_generation_keywords)

                if is_image_generation:
                    logger.info("Detected image generation request")
                    await self._handle_image_generation(text, say, original_channel_id, thread_ts_for_reply)
                    return

                # Process image URLs if any
                processed_image_urls = []
                if image_urls:
                    logger.info(f"Processing {len(image_urls)} images...")
                    processed_image_urls = await ImageProcessor.process_image_urls(image_urls)

                # Post initial message to get message timestamp for updates
                initial_response = await say(text="🤔 Pensando...", channel=original_channel_id, thread_ts=thread_ts_for_reply)
                message_ts = initial_response.get("ts")

                # Streaming callback to update Slack message
                current_text = ""
                last_update_length = 0
                import time
                last_update_time = time.time()

                async def stream_callback(delta_text: str, full_text: str):
                    nonlocal current_text, last_update_length, last_update_time
                    current_text = full_text
                    current_time = time.time()

                    # Update message every 10 characters or every 0.5 seconds, or when complete
                    should_update = (
                        len(current_text) - last_update_length >= 10 or  # Every 10 chars
                        current_time - last_update_time >= 0.5 or        # Every 0.5 seconds
                        not delta_text                                    # When complete
                    )

                    if should_update and current_text:
                        try:
                            # Update the message with current streaming text
                            formatted_text = format_message_for_slack(current_text)
                            await self.app.client.chat_update(
                                channel=original_channel_id,
                                ts=message_ts,
                                text=formatted_text
                            )
                            last_update_length = len(current_text)
                            last_update_time = current_time
                        except Exception as update_error:
                            logger.warning(f"Failed to update streaming message: {update_error}")

                # Delegate processing to the agent with streaming support
                response = await process_message(agent, context_input, processed_image_urls, stream_callback)

                # Final update with complete response
                try:
                    formatted_response = format_message_for_slack(str(response))
                    await self.app.client.chat_update(
                        channel=original_channel_id,
                        ts=message_ts,
                        text=formatted_response
                    )
                except Exception as final_update_error:
                    logger.warning(f"Failed to update final message: {final_update_error}")
                    # Fallback: post new message
                    await say(text=str(response), channel=original_channel_id, thread_ts=thread_ts_for_reply)

                logger.info(
                    f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] USER REQUEST: {context_input}"
                )
                formatted_response = format_message_for_slack(str(response))
                logger.info(
                    f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] BOT RESPONSE (STREAMING): {formatted_response}"
                )

            except Exception as e:
                logger.error(f"Error during Livia agent streaming processing: {e}", exc_info=True)
                # Try to update the initial message with error
                try:
                    if 'message_ts' in locals():
                        await self.app.client.chat_update(
                            channel=original_channel_id,
                            ts=message_ts,
                            text=f"Sorry, I encountered an error: {str(e)}"
                        )
                    else:
                        await say(text=f"Sorry, I encountered an error: {str(e)}", channel=original_channel_id, thread_ts=thread_ts_for_reply)
                except:
                    await say(text=f"Sorry, I encountered an error: {str(e)}", channel=original_channel_id, thread_ts=thread_ts_for_reply)

    # --- Message Processing & Response Method ---
    async def _process_and_respond(
        self, text: str, say: slack_bolt.Say, channel_id: str, thread_ts_for_reply: Optional[str] = None,
        image_urls: Optional[List[str]] = None, use_thread_history: bool = True, user_id: str = None
    ):
        """
        Sends message to agent and posts response to Slack, with per-conversation concurrency lock.
        """
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

        # --- Per-conversation locking ---
        conv_key = thread_ts_for_reply if thread_ts_for_reply else channel_id
        logger.info(f"[CONV_LOCK] Processing conversation {conv_key}")
        async with get_conversation_lock(conv_key):
            try:
                logger.info(
                    f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] Processing message via Livia agent..."
                )

                # Process image URLs if any
                processed_image_urls = []
                if image_urls:
                    logger.info(f"Processing {len(image_urls)} images...")
                    processed_image_urls = await ImageProcessor.process_image_urls(image_urls)

                # Delegate processing to the agent with image support (using streaming)
                response = await process_message(agent, context_input, processed_image_urls)

                # Always respond in the original channel
                logger.info(f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] USER REQUEST: {context_input}")
                logger.info(f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] BOT RESPONSE: {response}")
                formatted_response = format_message_for_slack(str(response))
                await say(text=formatted_response, channel=original_channel_id, thread_ts=thread_ts_for_reply)
            except Exception as e:
                logger.error(f"Error during Livia agent processing: {e}", exc_info=True)
                await say(text=f"Sorry, I encountered an error: {str(e)}", channel=original_channel_id, thread_ts=thread_ts_for_reply)

    def _extract_image_urls(self, event: Dict[str, Any]) -> List[str]:
        """Extract image URLs from Slack event."""
        return ImageProcessor.extract_image_urls(event)

    def _extract_audio_files(self, event: dict) -> List[dict]:
        """Extract audio files from Slack event."""
        audio_files = []

        if "files" in event:
            for file in event["files"]:
                mimetype = file.get("mimetype", "")
                filename = file.get("name", "").lower()

                # Check for audio file types supported by OpenAI
                audio_extensions = (".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac")
                audio_mimetypes = ("audio/", "video/mp4", "video/mpeg", "video/webm")

                if (any(mimetype.startswith(mt) for mt in audio_mimetypes) or
                    filename.endswith(audio_extensions)):

                    # Check file size (OpenAI limit is 25MB)
                    file_size = file.get("size", 0)
                    if file_size > 25 * 1024 * 1024:  # 25MB in bytes
                        logger.warning(f"Audio file {filename} is too large ({file_size} bytes). Max size is 25MB.")
                        continue

                    audio_files.append({
                        "id": file.get("id"),
                        "name": filename,
                        "mimetype": mimetype,
                        "url_private": file.get("url_private"),
                        "size": file_size
                    })

        return audio_files

    async def _transcribe_audio_file(self, audio_file: dict) -> Optional[str]:
        """Download and transcribe audio file from Slack."""
        try:
            import tempfile
            import aiohttp
            from openai import OpenAI

            # Download the audio file
            headers = {"Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(audio_file["url_private"], headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download audio file: {response.status}")
                        return None

                    audio_data = await response.read()

            # Create temporary file for transcription
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file['name'].split('.')[-1]}") as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            try:
                # Transcribe using OpenAI
                client = OpenAI()

                with open(temp_file_path, "rb") as audio_file_obj:
                    transcription = client.audio.transcriptions.create(
                        model="gpt-4o-transcribe",
                        file=audio_file_obj,
                        response_format="text",
                        prompt="Transcreva o áudio em português brasileiro. Mantenha pontuação e formatação adequadas."
                    )

                logger.info(f"Audio transcribed successfully: {len(transcription)} characters")
                return transcription

            finally:
                # Clean up temporary file
                import os as temp_os
                if temp_os.path.exists(temp_file_path):
                    temp_os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            return None

    async def _process_slack_image(self, image_url: str) -> Optional[str]:
        """Process Slack private image URL to make it accessible."""
        return await ImageProcessor.process_slack_image(image_url)

    async def _upload_image_to_slack(self, image_path: str, channel_id: str, thread_ts: Optional[str] = None,
                                   title: str = "Generated Image", comment: str = "",
                                   update_message_ts: Optional[str] = None) -> bool:
        """Upload an image file to Slack, optionally updating an existing message."""
        try:
            logger.info(f"Uploading image to Slack: {image_path}")

            if update_message_ts:
                # For progressive updates, upload without comment and update the original message
                response = await self.app.client.files_upload_v2(
                    channel=channel_id,
                    file=image_path,
                    title=title,
                    thread_ts=thread_ts
                )
            else:
                # Regular upload with comment
                response = await self.app.client.files_upload_v2(
                    channel=channel_id,
                    file=image_path,
                    title=title,
                    initial_comment=comment,
                    thread_ts=thread_ts
                )

            if response["ok"]:
                logger.info(f"Image uploaded successfully to Slack: {response['file']['id']}")
                return True
            else:
                logger.error(f"Failed to upload image to Slack: {response.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Error uploading image to Slack: {e}", exc_info=True)
            return False

    async def _upload_image_to_slack_with_response(self, image_path: str, channel_id: str, thread_ts: Optional[str] = None,
                                                 title: str = "Generated Image", comment: str = ""):
        """Upload an image file to Slack and return the full response."""
        try:
            logger.info(f"Uploading image to Slack with response: {image_path}")

            # Upload file to Slack
            response = await self.app.client.files_upload_v2(
                channel=channel_id,
                file=image_path,
                title=title,
                initial_comment=comment,
                thread_ts=thread_ts
            )

            if response["ok"]:
                logger.info(f"Image uploaded successfully to Slack: {response['file']['id']}")
                return response
            else:
                logger.error(f"Failed to upload image to Slack: {response.get('error', 'Unknown error')}")
                return None

        except Exception as e:
            logger.error(f"Error uploading image to Slack: {e}", exc_info=True)
            return None

    async def _handle_image_generation(self, text: str, say: slack_bolt.Say, channel_id: str,
                                     thread_ts: Optional[str] = None):
        """Handle image generation requests with streaming support."""
        try:
            logger.info(f"Processing image generation request: {text}")

            # Extract the prompt from the text
            prompt = self._extract_image_prompt(text)
            if not prompt:
                await say(
                    text="❌ Não consegui entender o que você quer que eu desenhe. Tente algo como: 'Gere uma imagem de um gato fofo'",
                    channel=channel_id,
                    thread_ts=thread_ts
                )
                return

            # Post initial message with progress
            initial_response = await say(
                text="🎨 **Iniciando geração de imagem... 0%**\n\n🤖 Processando seu prompt com gpt-image-1...",
                channel=channel_id,
                thread_ts=thread_ts
            )
            message_ts = initial_response.get("ts")

            # Simple text streaming callback for progress updates
            async def image_stream_callback(status_text: str, progress_percent: int = 0):
                try:
                    # Update status message with current progress
                    await self.app.client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text=f"🎨 {status_text} {progress_percent}%"
                    )
                    logger.info(f"Progress update: {status_text} {progress_percent}%")
                except Exception as e:
                    logger.warning(f"Error in image stream callback: {e}")

            # Generate image with streaming
            result = await image_generator.generate_image(
                prompt=prompt,
                size="auto",
                quality="auto",
                format="png",
                stream_callback=image_stream_callback
            )

            if result["success"]:
                if "image_path" in result:
                    # Upload final image with simple title
                    file_id = f"img_{int(__import__('time').time())}"  # Simple timestamp-based ID
                    final_image_response = await self._upload_image_to_slack_with_response(
                        result["image_path"],
                        channel_id,
                        thread_ts,
                        title=file_id,
                        comment=""  # No comment needed
                    )

                    if final_image_response and final_image_response.get("ok"):
                        # Just remove the status message - image speaks for itself
                        await self.app.client.chat_delete(
                            channel=channel_id,
                            ts=message_ts
                        )
                        logger.info(f"Final image uploaded successfully: {final_image_response['file']['id']}")
                    else:
                        await self.app.client.chat_update(
                            channel=channel_id,
                            ts=message_ts,
                            text="❌ Erro ao fazer upload da imagem"
                        )

                    # Clean up temporary file
                    image_generator.cleanup_temp_file(result["image_path"])
                else:
                    # Case where no image was generated
                    await self.app.client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text="❌ Erro: Nenhuma imagem foi gerada"
                    )

            else:
                await self.app.client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text=f"❌ Erro ao gerar imagem: {result.get('error', 'Erro desconhecido')}"
                )

        except Exception as e:
            logger.error(f"Error in image generation: {e}", exc_info=True)
            await say(
                text=f"❌ Erro ao gerar imagem: {str(e)}",
                channel=channel_id,
                thread_ts=thread_ts
            )

    def _extract_image_prompt(self, text: str) -> Optional[str]:
        """Extract the image prompt from user text."""
        import re

        # Remove common prefixes
        text = text.strip()

        # Patterns to remove
        patterns = [
            r'^gere?\s+uma?\s+imagem\s+(de\s+|do\s+|da\s+)?',
            r'^criar?\s+uma?\s+imagem\s+(de\s+|do\s+|da\s+)?',
            r'^faça?\s+uma?\s+imagem\s+(de\s+|do\s+|da\s+)?',
            r'^fazer?\s+uma?\s+imagem\s+(de\s+|do\s+|da\s+)?',
            r'^desenhe?\s+(uma?\s+)?',
            r'^desenhar?\s+(uma?\s+)?',
            r'^generate\s+an?\s+image\s+(of\s+)?',
            r'^create\s+an?\s+image\s+(of\s+)?',
            r'^draw\s+(an?\s+)?'
        ]

        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

        # If there's still text left, that's our prompt
        if text:
            return text

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
            """
            SLACK_INTEGRATION_POINT - Handler principal para mensagens do Slack

            Lógica atual:
            - Só responde em threads que começaram com menção ao bot
            - Processa áudio automaticamente
            - Aplica filtros de segurança (canais/usuários permitidos)

            TODO: Aqui é onde o agente processa mensagens do Slack
            """
            event = body.get("event", {})


            # Check if message has audio files even if text is empty
            audio_files = self._extract_audio_files(event)
            text = event.get("text", "").strip()

            # Skip bot messages or messages from the bot itself
            if (event.get("bot_id") or event.get("user") == bot_user_id):
                logger.info("Ignoring bot message or message from bot itself")
                return

            # Skip if no text AND no audio files
            if not text and not audio_files:
                logger.info("Ignoring message with no text and no audio files")
                return

            # DEVELOPMENT SECURITY: Early channel validation
            channel_id = event.get("channel")
            user_id = event.get("user")
            if not await is_channel_allowed(channel_id, user_id, self.app.client):
                logger.warning(f"SECURITY: Blocked message event from unauthorized channel {channel_id}")
                return

            text = event.get("text", "").strip()
            thread_ts = event.get("thread_ts")

            logger.info(f"Message: '{text}', Channel: {channel_id}, Thread: {thread_ts}")

            # Check if this is a mention in the message text (fallback detection)
            is_mention_in_text = f"<@{bot_user_id}>" in text

            # Skip mentions in message events - they'll be handled by app_mention
            if is_mention_in_text:
                logger.info("Mention detected in message event, will be handled by app_mention event")
                return

            # Process thread replies, direct messages, OR mentions in text
            if not thread_ts and event.get("channel_type") != "im" and not is_mention_in_text:
                logger.info("Not a thread reply, DM, or mention - ignoring")
                return

            # Now check for duplicates only for messages we will actually process
            message_id = f"{event.get('channel')}_{event.get('ts')}"
            if message_id in processed_messages:
                logger.info(f"Message {message_id} already processed, skipping")
                return
            processed_messages.add(message_id)

            if len(processed_messages) > 100:
                processed_messages.clear()

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
                audio_files = self._extract_audio_files(event)
                await self._process_and_respond_streaming(
                    text=text,
                    say=say,
                    channel_id=channel_id,
                    thread_ts_for_reply=thread_ts,
                    image_urls=image_urls,
                    audio_files=audio_files,
                    user_id=event.get("user")
                )

        @self.app.event("app_mention")
        async def handle_app_mentions(body: Dict[str, Any], say: slack_bolt.Say):
            """
            SLACK_INTEGRATION_POINT - Handler para menções diretas ao bot (@livia)

            Lógica atual:
            - Detecta quando o bot é mencionado
            - Inicia nova thread ou responde em thread existente
            - Remove a menção do texto antes de processar

            TODO: Ponto principal onde o bot é "chamado" pelo usuário
            """
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

            # Create unique ID for this mention to prevent duplicates (same format as message events)
            message_id = f"{event.get('channel')}_{event.get('ts')}"

            # Check if we already processed this specific message
            if message_id in processed_messages:
                logger.info(f"Mention {message_id} already processed, skipping")
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

            # Check for audio files even if no text
            image_urls = self._extract_image_urls(event)
            audio_files = self._extract_audio_files(event)

            # If no text but has audio files, set a default message
            if not text and audio_files:
                text = "🎵 Processando áudio..."
            elif not text:
                text = "Hello! How can I help you?"

            logger.info(f"Processing mention with text: '{text}', audio files: {len(audio_files)}")

            # Mark this mention as processed BEFORE processing to prevent duplicates
            processed_messages.add(message_id)

            # Clean up old processed messages to prevent memory issues
            if len(processed_messages) > 100:
                processed_messages.clear()
                logger.info("Cleared processed messages cache")

            await self._process_and_respond_streaming(
                text=text,
                say=say,
                channel_id=channel_id,
                thread_ts_for_reply=thread_ts,
                image_urls=image_urls,
                audio_files=audio_files,
                use_thread_history=False,  # Don't use history for initial mentions
                user_id=event.get("user")
            )

        @self.app.event("file_shared")
        async def handle_file_shared_events(body: Dict[str, Any]):
            """Handle file shared events - acknowledge to prevent warnings."""
            logger.info("File shared event acknowledged")

        @self.app.event("app_home_opened")
        async def handle_app_home_opened_events(body: Dict[str, Any]):
            """Handle app home opened events - acknowledge to prevent warnings."""
            logger.info("App home opened event acknowledged")

        @self.app.event("file_change")
        async def handle_file_change_events(body: Dict[str, Any]):
            """Handle file change events - acknowledge to prevent warnings."""
            logger.info("File change event acknowledged")

        @self.app.event("reaction_added")
        async def handle_reaction_added_events(body: Dict[str, Any]):
            """Handle reaction added events - acknowledge to prevent warnings."""
            logger.debug("Reaction added event acknowledged")

    # --- Server Start Method ---
    async def start(self):
        """Starts the Socket Mode server asynchronously."""
        logger.info("Starting Slack Socket Mode server (async)...")
        await self.socket_mode_handler.start_async()

# --- Agent Initialization and Cleanup Functions ---
async def initialize_agent():
    """Initializes the Livia agent (without MCP Slack local - using direct API)."""
    global agent

    logger.info("Initializing Livia Agent (using direct Slack API)...")

    try:
        # Create the agent (sem MCP Slack local)
        agent = await create_agent()
        logger.info("Livia agent successfully initialized.")

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        await cleanup_agent()
        raise

async def cleanup_agent():
    """Cleans up the agent resources."""
    global agent

    logger.info("Cleaning up Livia agent resources...")

    # TODO: SLACK_INTEGRATION_POINT - Se precisar de cleanup específico do Slack, adicionar aqui
    # Exemplo: fechar conexões, limpar cache, etc.

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