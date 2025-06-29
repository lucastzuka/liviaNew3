#!/usr/bin/env python3
"""
Message Processor
-----------------
Processador principal de mensagens com streaming e gerenciamento de contexto.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any

from .config import (
    get_global_agent, get_agent_semaphore, is_channel_allowed,
    SHOW_DEBUG_LOGS
)
from .context_manager import ContextManager
from .streaming_processor import StreamingProcessor
from .utils import (
    get_user_friendly_error_message, should_retry_error,
    log_bot_response, count_tokens
)
from slack_formatter import format_message_for_slack
from tools import ImageProcessor, image_generator

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processa mensagens e gerencia streaming de respostas."""
    
    def __init__(self, app_client):
        self.app_client = app_client
        self.context_manager = ContextManager(app_client)
        self.streaming_processor = StreamingProcessor()
    
    async def process_and_respond_streaming(
        self,
        text: str,
        say,
        channel_id: str,
        thread_ts_for_reply: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        audio_files: Optional[List[dict]] = None,
        use_thread_history: bool = True,
        user_id: str = None,
        model_override: Optional[str] = None,
    ):
        """
        Envia mensagem para o agente e posta resposta em streaming no Slack.
        Implementa:
        - Mensagem estática ":hourglass_flowing_sand: Pensando..." substituída por tags + resposta
        - Tag de cabeçalho no formato `⛭TagName` no topo de todas as respostas
        """
        agent = get_global_agent()
        current_agent = agent
        if model_override:
            import copy
            current_agent = copy.deepcopy(agent)
            current_agent.model = model_override

        if not current_agent:
            logger.error("Livia agent not ready.")
            await say(text="Livia is starting up, please wait.", channel=channel_id, thread_ts=thread_ts_for_reply)
            return

        model_name = current_agent.model
        original_channel_id = channel_id
        if not await is_channel_allowed(channel_id, user_id or "unknown", self.app_client):
            return

        # Skip processing if it looks like bot's own response
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
            if transcriptions:
                if text:
                    context_input = f"{text}\n\n" + "\n\n".join(transcriptions)
                else:
                    context_input = "\n\n".join(transcriptions)

        # Use thread history as context if available
        if use_thread_history and thread_ts_for_reply:
            if SHOW_DEBUG_LOGS:
                logger.info(f"Fetching history for thread {thread_ts_for_reply}...")
            full_history = await self.context_manager.fetch_thread_history(
                channel_id, thread_ts_for_reply, model_name
            )
            if full_history:
                context_input = full_history + f"\n\nLatest message: {context_input}"
            else:
                if SHOW_DEBUG_LOGS:
                    logger.warning("Failed to fetch thread history.")

        # --- Static thinking message ---
        agent_semaphore = get_agent_semaphore()
        async with agent_semaphore:
            thinking_msg = await say(
                text=":hourglass_flowing_sand: Pensando...", 
                channel=original_channel_id, 
                thread_ts=thread_ts_for_reply
            )
            message_ts = thinking_msg.get("ts")

            # --- Determine initial cumulative tags (heuristic) ---
            initial_tags = self.streaming_processor.get_initial_cumulative_tags(
                text, audio_files, image_urls, model_name
            )
            
            # Format as: `⛭ gpt-4.1-mini` `Vision` etc.
            header_prefix = self.streaming_processor.format_tags_display(initial_tags) + "\n\n"

            try:
                # Clean terminal: Only show essential bot interactions
                # (Message already logged by log_message_received)

                # If image generation, call handler (it does its own updating)
                if "ImageGen" in initial_tags:
                    await self._handle_image_generation(text, say, original_channel_id, thread_ts_for_reply)
                    return

                # Process image URLs if any
                processed_image_urls = []
                if image_urls:
                    logger.info(f"Processing {len(image_urls)} images: {image_urls}")
                    processed_image_urls = await ImageProcessor.process_image_urls(image_urls)
                    logger.info(f"Successfully processed {len(processed_image_urls)} images")
                else:
                    if SHOW_DEBUG_LOGS:
                        logger.info("No images detected in this message")

                # Create streaming callback
                stream_callback = await self.streaming_processor.create_stream_callback(
                    self.app_client, original_channel_id, message_ts, header_prefix,
                    audio_files, processed_image_urls, text, model_name
                )

                # Agent streaming with unified Agents SDK: { text, tools, structured_data? }
                from agent import process_message
                response = await process_message(current_agent, context_input, processed_image_urls, stream_callback)
                text_resp = response.get("text") if isinstance(response, dict) else str(response)
                tool_calls = response.get("tools") if isinstance(response, dict) else []
                structured_data = response.get("structured_data") if isinstance(response, dict) else None

                # Compute header_prefix_final based on tools actually used (cumulative)
                final_cumulative_tags = self.streaming_processor.derive_cumulative_tags(
                    tool_calls, audio_files, processed_image_urls, 
                    user_message=text, final_response=text_resp, model_name=model_name
                )
                # Format as: `⛭ {model_name}` `Vision` `WebSearch`
                header_prefix_final = self.streaming_processor.format_tags_display(final_cumulative_tags) + "\n\n"

                # Check if conversation is approaching token limit
                token_info = response.get("token_usage", {}) if isinstance(response, dict) else {}
                input_tokens = token_info.get("input", count_tokens(context_input))
                output_tokens = token_info.get("output", count_tokens(text_resp))
                total_tokens = input_tokens + output_tokens
                thread_key = thread_ts_for_reply or original_channel_id
                
                is_at_limit, memory_warning = self.context_manager.check_context_limit(
                    thread_key, total_tokens, model_name
                )

                text_with_footer = text_resp + memory_warning
                try:
                    formatted_response = header_prefix_final + format_message_for_slack(text_with_footer)
                    await self.app_client.chat_update(
                        channel=original_channel_id,
                        ts=message_ts,
                        text=formatted_response
                    )
                except Exception as final_update_error:
                    logger.warning(f"Failed to update final message: {final_update_error}")
                    await say(text=formatted_response, channel=original_channel_id, thread_ts=thread_ts_for_reply)

                # Extract tools used from formatted response
                tools_used = None
                if "`" in formatted_response:
                    import re
                    tools_match = re.findall(r'`([^`]+)`', formatted_response)
                    if tools_match:
                        tools_used = " ".join(tools_match)

                log_bot_response(formatted_response, tools_used)

            except Exception as e:
                logger.error(f"Error during Livia agent streaming processing: {e}", exc_info=True)

                # Get user-friendly error message
                user_error_msg = get_user_friendly_error_message(e)

                # Retry logic for temporary errors
                if should_retry_error(e) and not hasattr(self, '_retry_count'):
                    self._retry_count = 1
                    logger.info(f"🔄 Retrying due to temporary error: {type(e).__name__}")
                    await asyncio.sleep(2)  # Wait 2 seconds before retry

                    try:
                        # Retry the operation once
                        return await self.process_and_respond_streaming(
                            text, say, channel_id, thread_ts_for_reply,
                            image_urls, audio_files, use_thread_history, user_id
                        )
                    except Exception as retry_error:
                        logger.error(f"Retry failed: {retry_error}")
                        user_error_msg = get_user_friendly_error_message(retry_error)
                    finally:
                        delattr(self, '_retry_count')

                try:
                    if 'message_ts' in locals():
                        await self.app_client.chat_update(
                            channel=original_channel_id,
                            ts=message_ts,
                            text=user_error_msg
                        )
                    else:
                        await say(text=user_error_msg, channel=original_channel_id, thread_ts=thread_ts_for_reply)
                except:
                    await say(text="Erro: Falha na comunicação. Se persistir entre em contato com: <@U046LTU4TT5>", channel=original_channel_id, thread_ts=thread_ts_for_reply)

    async def _handle_image_generation(self, text: str, say, channel_id: str, thread_ts: Optional[str]):
        """Handle image generation requests."""
        try:
            # Use the image generator from tools
            result = await image_generator.generate_image_with_progress(
                prompt=text,
                say=say,
                channel=channel_id,
                thread_ts=thread_ts
            )
            logger.info(f"Image generation completed: {result}")
        except Exception as e:
            logger.error(f"Error in image generation: {e}")
            await say(
                text=f"Erro na geração de imagem: {str(e)}", 
                channel=channel_id, 
                thread_ts=thread_ts
            )

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
