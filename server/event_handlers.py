#!/usr/bin/env python3
"""
Event Handlers
--------------
Handlers de eventos do Slack para o bot Livia.
Inclui processamento de mensagens, áudio, imagens e shortcuts.
"""

import logging
import re
from typing import List, Optional, Dict, Any

from .config import (
    is_channel_allowed, get_bot_user_id, get_processed_messages,
    SHOW_DEBUG_LOGS, get_global_agent
)
from .utils import log_message_received, log_error
from .message_processor import MessageProcessor
from tools.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class EventHandlers:
    """Gerencia todos os handlers de eventos do Slack."""
    
    def __init__(self, app, message_processor: MessageProcessor):
        self.app = app
        self.message_processor = message_processor
        self.bot_user_id = get_bot_user_id()
        self.processed_messages = get_processed_messages()
        self.document_processor = DocumentProcessor()
    
    def setup_event_handlers(self):
        """Configura todos os handlers de eventos."""
        self.app.event("message")(self.handle_message_events)
        self.app.action("static_select-action")(self.handle_think_selection)
    
    async def handle_message_events(self, event, say, client):
        """
        Processa eventos de mensagem do Slack.
        Responde apenas quando mencionado na primeira mensagem de threads.
        """
        try:
            # Extract event details
            channel_id = event.get("channel")
            user_id = event.get("user")
            text = event.get("text", "")
            ts = event.get("ts")
            thread_ts = event.get("thread_ts")
            
            # Skip if no agent available
            agent = get_global_agent()
            if not agent:
                logger.warning("Agent not available, skipping message")
                return

            # Security check
            if not await is_channel_allowed(channel_id, user_id, client):
                return

            # Skip bot's own messages
            if user_id == self.bot_user_id:
                if SHOW_DEBUG_LOGS:
                    logger.debug("Skipping bot's own message")
                return

            # Skip if message already processed
            message_key = f"{channel_id}_{ts}_{user_id}"
            if message_key in self.processed_messages:
                if SHOW_DEBUG_LOGS:
                    logger.debug(f"Message already processed: {message_key}")
                return
            self.processed_messages.add(message_key)

            # Check if bot is mentioned in the message
            bot_mentioned = f"<@{self.bot_user_id}>" in text

            # Determine if we should respond
            should_respond = False
            thread_ts_for_reply = None

            if thread_ts:
                # This is a threaded message
                # Check if bot was mentioned in the FIRST message of the thread
                try:
                    thread_info = await client.conversations_replies(
                        channel=channel_id,
                        ts=thread_ts,
                        limit=1,
                        inclusive=True
                    )
                    
                    if thread_info["ok"] and thread_info["messages"]:
                        first_message = thread_info["messages"][0]
                        first_message_text = first_message.get("text", "")
                        
                        # Bot should respond if mentioned in first message of thread
                        if f"<@{self.bot_user_id}>" in first_message_text:
                            should_respond = True
                            thread_ts_for_reply = thread_ts
                            if SHOW_DEBUG_LOGS:
                                logger.debug(f"Bot mentioned in first message of thread {thread_ts}")
                        else:
                            if SHOW_DEBUG_LOGS:
                                logger.debug(f"Bot not mentioned in first message of thread {thread_ts}")
                except Exception as e:
                    logger.error(f"Error checking thread first message: {e}")
                    return
            else:
                # This is a direct message or new thread
                if bot_mentioned:
                    should_respond = True
                    thread_ts_for_reply = ts  # Start new thread
                    if SHOW_DEBUG_LOGS:
                        logger.debug(f"Bot mentioned in direct message, starting new thread")

            if not should_respond:
                if SHOW_DEBUG_LOGS:
                    logger.debug("Bot not mentioned appropriately, not responding")
                return

            # Clean terminal logging
            log_message_received(user_id, channel_id, text)

            # Remove bot mention from text for processing
            clean_text = re.sub(f"<@{self.bot_user_id}>", "", text).strip()

            # Check for +think command
            if clean_text.strip().startswith("+think"):
                await self._handle_think_command(clean_text, channel_id, user_id, thread_ts_for_reply, say, client)
                return

            # Extract image URLs from message
            image_urls = self._extract_image_urls(event)
            
            # Extract audio files from message
            audio_files = await self._extract_audio_files(event, client)
            
            # Extract document files from message
            document_files = await self.document_processor.extract_document_files(event, client)

            # Process the message
            await self.message_processor.process_message(
                text=clean_text,
                say=say,
                client=client,
                channel_id=channel_id,
                thread_ts_for_reply=thread_ts_for_reply,
                image_urls=image_urls,
                audio_files=audio_files,
                document_files=document_files,
                use_thread_history=True,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Error in handle_message_events: {e}", exc_info=True)
            log_error(f"Erro no processamento de mensagem: {str(e)}")

    async def handle_think_selection(self, ack, body, client, say):
        """
        Handle the selection from the think improvement button.
        """
        try:
            await ack()
            
            # Get selection value
            selected_value = body["actions"][0]["selected_option"]["value"]
            channel_id = body["channel"]["id"]
            user_id = body["user"]["id"]
            message_ts = body["message"]["ts"]
            
            # Security check
            if not await is_channel_allowed(channel_id, user_id, client):
                return

            # Get the original think message from the stored context
            original_message = getattr(self, '_pending_think_message', None)
            thread_history = getattr(self, '_pending_think_history', [])
            
            if not original_message:
                await client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text="❌ Sessão expirada. Tente novamente com +think."
                )
                return

            # Determine if we should improve the prompt
            improve_prompt = selected_value == "value-0"  # SIM - melhorar prompt
            
            # Update message to show processing is starting
            if improve_prompt:
                await client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text="✨ Reformulando prompt..."
                )
            else:
                await client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text="🧠 Analisando profundamente..."
                )

            # Process with the new sequential flow
            await self.message_processor.process_think_message(
                original_message,
                channel_id=channel_id,
                user_id=user_id,
                thread_ts=message_ts,
                say=say,
                client=client,
                improve_prompt=improve_prompt,
                thread_history=thread_history if improve_prompt else None
            )
            
            # Clean up stored context
            self._pending_think_message = None
            self._pending_think_history = []

        except Exception as e:
            logger.error(f"Error in handle_think_selection: {e}", exc_info=True)
            await client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text="❌ Erro ao processar seleção. Tente novamente."
            )



    async def _handle_think_command(self, text: str, channel_id: str, user_id: str, thread_ts: str, say, client):
        """
        Handle +think command by showing improvement selection button.
        """
        try:
            # Extract the think message (remove +think prefix)
            think_message = text[6:].strip()  # Remove "+think" and whitespace
            
            if not think_message:
                await say("Por favor, forneça uma mensagem após o comando +think.", thread_ts=thread_ts)
                return

            # Get thread history for context
            thread_history = await self._get_thread_history(channel_id, thread_ts, client)
            
            # Store the message and history for later use
            self._pending_think_message = think_message
            self._pending_think_history = thread_history
            
            # Send the selection button
            await say(
                text="Quer que eu melhore seu prompt antes de enviar?",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Quer que eu melhore seu prompt antes de enviar?"
                        },
                        "accessory": {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "...",
                                "emoji": True
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "SIM ⚡",
                                        "emoji": True
                                    },
                                    "value": "value-0"
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Não 🚫",
                                        "emoji": True
                                    },
                                    "value": "value-1"
                                }
                            ],
                            "action_id": "static_select-action"
                        }
                    }
                ],
                thread_ts=thread_ts
            )
            
        except Exception as e:
            logger.error(f"Error in _handle_think_command: {e}", exc_info=True)
            await say("Erro ao processar comando +think.", thread_ts=thread_ts)

    async def _get_thread_history(self, channel_id: str, thread_ts: str, client) -> List[Dict]:
        """
        Get the conversation history from the thread.
        """
        try:
            response = await client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=20
            )
            return response.get("messages", [])
        except Exception as e:
            logger.error(f"Error getting thread history: {e}")
            return []

    def _extract_image_urls(self, event: Dict[str, Any]) -> List[str]:
        """Extract image URLs from Slack message event."""
        image_urls = []
        
        # Check for files in the message
        files = event.get("files", [])
        for file_info in files:
            if file_info.get("mimetype", "").startswith("image/"):
                # Use the URL that doesn't require authentication if available
                url = file_info.get("url_private") or file_info.get("permalink")
                if url:
                    image_urls.append(url)
        
        # Check for image URLs in text (enhanced URL detection)
        text = event.get("text", "")
        
        # Pattern for image URLs (more comprehensive)
        url_patterns = [
            r'https?://[^\s<>]+\.(?:jpg|jpeg|png|gif|webp|bmp|tiff)(?:\?[^\s<>]*)?',  # Direct image URLs
            r'https?://[^\s<>]*(?:imgur|flickr|instagram|twitter|facebook|ichef\.bbci)[^\s<>]*',   # Image hosting sites including BBC
            r'https?://[^\s<>]*\.(?:com|org|net|co\.uk)/[^\s<>]*\.(?:jpg|jpeg|png|gif|webp)', # Images on websites
            r'https?://ichef\.bbci\.co\.uk/[^\s<>]*',  # BBC image URLs specifically
        ]
        
        for pattern in url_patterns:
            found_urls = re.findall(pattern, text, re.IGNORECASE)
            for url in found_urls:
                # Clean up URL (remove trailing punctuation)
                url = re.sub(r'[.,;!?]+$', '', url)
                if url not in image_urls:
                    image_urls.append(url)
                    logger.info(f"Found image URL in text: {url}")
        
        return image_urls

    async def _extract_audio_files(self, event: Dict[str, Any], client) -> List[Dict[str, Any]]:
        """Extract audio files from Slack message event."""
        audio_files = []
        
        files = event.get("files", [])
        for file_info in files:
            mimetype = file_info.get("mimetype", "")
            if mimetype.startswith("audio/") or file_info.get("name", "").lower().endswith(('.mp3', '.wav', '.m4a', '.ogg', '.flac')):
                try:
                    # Download the audio file
                    file_url = file_info.get("url_private")
                    if file_url:
                        # Get the file content
                        response = await client.api_call(
                            "files.info",
                            file=file_info.get("id")
                        )
                        
                        if response["ok"]:
                            audio_files.append({
                                "name": file_info.get("name", "audio_file"),
                                "url": file_url,
                                "mimetype": mimetype,
                                "size": file_info.get("size", 0)
                            })
                except Exception as e:
                    logger.error(f"Error processing audio file: {e}")
        
        return audio_files

    async def _transcribe_audio_file(self, audio_file: Dict[str, Any]) -> Optional[str]:
        """Transcribe audio file using OpenAI Whisper."""
        try:
            # This would need to be implemented with actual audio transcription
            # For now, return a placeholder
            logger.info(f"Audio transcription not yet implemented for {audio_file['name']}")
            return f"[Áudio: {audio_file['name']} - Transcrição não implementada]"
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
