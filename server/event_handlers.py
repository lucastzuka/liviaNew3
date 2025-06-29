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

logger = logging.getLogger(__name__)


class EventHandlers:
    """Gerencia todos os handlers de eventos do Slack."""
    
    def __init__(self, app, message_processor: MessageProcessor):
        self.app = app
        self.message_processor = message_processor
        self.bot_user_id = get_bot_user_id()
        self.processed_messages = get_processed_messages()
    
    def setup_event_handlers(self):
        """Configura todos os handlers de eventos."""
        self.app.event("message")(self.handle_message_events)
        self.app.shortcut("livia_think")(self.handle_thinking_shortcut)
    
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

            # Extract image URLs from message
            image_urls = self._extract_image_urls(event)
            
            # Extract audio files from message
            audio_files = await self._extract_audio_files(event, client)

            # Process the message
            await self.message_processor.process_and_respond_streaming(
                text=clean_text,
                say=say,
                channel_id=channel_id,
                thread_ts_for_reply=thread_ts_for_reply,
                image_urls=image_urls,
                audio_files=audio_files,
                use_thread_history=True,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Error in handle_message_events: {e}", exc_info=True)
            log_error(f"Erro no processamento de mensagem: {str(e)}")

    async def handle_thinking_shortcut(self, ack, shortcut, client, say):
        """
        Handle the thinking shortcut (+think) that opens a modal for o3 processing.
        """
        try:
            await ack()
            
            # Security check
            channel_id = shortcut.get("channel", {}).get("id")
            user_id = shortcut.get("user", {}).get("id")
            
            if not await is_channel_allowed(channel_id, user_id, client):
                return

            # Open modal for thinking input
            await client.views_open(
                trigger_id=shortcut["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "thinking_modal",
                    "title": {"type": "plain_text", "text": "🧠 Modo Pensamento"},
                    "submit": {"type": "plain_text", "text": "Analisar"},
                    "close": {"type": "plain_text", "text": "Cancelar"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "thinking_input",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "thinking_text",
                                "multiline": True,
                                "placeholder": {
                                    "type": "plain_text",
                                    "text": "Descreva o problema ou situação que precisa de análise profunda..."
                                }
                            },
                            "label": {"type": "plain_text", "text": "Análise Profunda"}
                        }
                    ]
                }
            )

        except Exception as e:
            logger.error(f"Error in handle_thinking_shortcut: {e}", exc_info=True)

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
        
        # Check for image URLs in text
        text = event.get("text", "")
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(jpg|jpeg|png|gif|webp|bmp)'
        found_urls = re.findall(url_pattern, text, re.IGNORECASE)
        for url_match in found_urls:
            # url_match is a tuple, we want the full URL
            full_url = text[text.find(url_match[0]) - len(url_match[0]) - 8:text.find(url_match[0]) + len(url_match[1]) + 1]
            if full_url.startswith('http'):
                image_urls.append(full_url)
        
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
