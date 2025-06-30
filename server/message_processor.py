#!/usr/bin/env python3
"""
Message Processor
-----------------
Processador principal de mensagens com streaming e gerenciamento de contexto.
"""

import logging
import os
import asyncio
from typing import List, Optional, Dict, Any

from .config import (
    get_global_agent, get_agent_semaphore, is_channel_allowed,
    SHOW_DEBUG_LOGS, get_bot_user_id
)
from .context_manager import ContextManager
from .streaming_processor import StreamingProcessor
from tools.document_processor import DocumentProcessor
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
        self.bot_user_id = get_bot_user_id()
        self.document_processor = DocumentProcessor()
        self.current_vector_store_id = None  # Track current vector store for file count
        self.thread_vector_stores = {}  # Track vector stores by thread_ts for accumulation
    
    async def process_message(
        self,
        text: str,
        say,
        client,
        channel_id: str,
        thread_ts_for_reply: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        audio_files: Optional[List[dict]] = None,
        document_files: Optional[List[dict]] = None,
        use_thread_history: bool = True,
        user_id: str = None,
        model_override: Optional[str] = None,
    ):
        """Envia mensagem para o agente e posta resposta em streaming no Slack.
        Implementa:
        - Mensagem estática ":hourglass_flowing_sand: Pensando..." substituída por tags + resposta
        - Tag de cabeçalho no formato `⛭TagName` no topo de todas as respostas
        """
        # Log incoming message details
        logger.info(f"\n{'='*60}")
        logger.info(f"📨 NEW MESSAGE RECEIVED")
        logger.info(f"   Channel: {channel_id}")
        logger.info(f"   User: {user_id or 'unknown'}")
        logger.info(f"   Thread: {thread_ts_for_reply or 'new'}")
        logger.info(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        logger.info(f"   Images: {len(image_urls) if image_urls else 0}")
        logger.info(f"   Audio: {len(audio_files) if audio_files else 0}")
        logger.info(f"   Documents: {len(document_files) if document_files else 0}")
        logger.info(f"   Model override: {model_override or 'none'}")
        logger.info(f"{'='*60}")
        
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

        # Process document files if any - WAIT for completion before proceeding
        document_summary = None
        if document_files:
            logger.info(f"Processing {len(document_files)} document file(s)...")
            document_summary = await self._process_document_files(document_files, client, say, channel_id, thread_ts_for_reply)
            if document_summary:
                if context_input:
                    context_input = f"{context_input}\n\n{document_summary}"
                else:
                    context_input = document_summary
                logger.info(f"✅ Document processing completed. Vector store ID: {self.current_vector_store_id}")
            else:
                logger.warning("❌ Document processing failed or returned no summary")
                # If document processing failed, we should still continue but without file context
                if not context_input.strip():
                    context_input = "O usuário enviou documentos, mas houve erro no processamento."

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
                from agent.processor import process_message
                response = await process_message(current_agent, context_input, processed_image_urls, stream_callback)
                text_resp = response.get("text") if isinstance(response, dict) else str(response)
                tool_calls = response.get("tools") if isinstance(response, dict) else []
                structured_data = response.get("structured_data") if isinstance(response, dict) else None

                # Compute header_prefix_final based on tools actually used (cumulative)
                print(f"🔍 DEBUG: Calling detect_tools_and_model with vector_store_id: {self.current_vector_store_id}")
                print(f"🔍 DEBUG: tool_calls passed: {tool_calls}")
                final_cumulative_tags = await self.streaming_processor.detect_tools_and_model(
                    tool_calls, text_resp, processed_image_urls, audio_files, 
                    text, model_name, self.current_vector_store_id
                )
                print(f"🔍 DEBUG: final_cumulative_tags: {final_cumulative_tags}")
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
                
                # Log final response details
                logger.info(f"\n📤 SENDING FINAL RESPONSE")
                logger.info(f"   Model used: {model_name}")
                logger.info(f"   Response length: {len(text_resp)} chars")
                logger.info(f"   Token usage: {input_tokens}+{output_tokens}={total_tokens}")
                logger.info(f"   Header prefix: {header_prefix_final[:50]}{'...' if len(header_prefix_final) > 50 else ''}")
                logger.info(f"   Response preview: {text_resp[:150]}{'...' if len(text_resp) > 150 else ''}")
                
                try:
                    formatted_response = header_prefix_final + format_message_for_slack(text_with_footer)
                    logger.info(f"   Final formatted length: {len(formatted_response)} chars")
                    
                    await self.app_client.chat_update(
                        channel=original_channel_id,
                        ts=message_ts,
                        text=formatted_response
                    )
                    logger.info(f"✅ Message updated successfully in Slack")
                except Exception as final_update_error:
                    logger.warning(f"Failed to update final message: {final_update_error}")
                    await say(text=formatted_response, channel=original_channel_id, thread_ts=thread_ts_for_reply)
                    logger.info(f"✅ Message sent as new message in Slack")

                # Extract tools used from formatted response
                tools_used = None
                if "`" in formatted_response:
                    import re
                    tools_match = re.findall(r'`([^`]+)`', formatted_response)
                    if tools_match:
                        tools_used = " ".join(tools_match)
                        logger.info(f"🔧 Tools detected in response: {tools_used}")

                log_bot_response(formatted_response, tools_used)
                logger.info(f"{'='*60}\n")

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

    async def _process_document_files(self, document_files: List[dict], client, say, channel_id: str, thread_ts: Optional[str]) -> Optional[str]:
        """Process document files, upload to OpenAI, and update vector store."""
        try:
            if not document_files:
                return None
            
            # Enviar mensagem de status
            status_msg = await say(
                text="📄 Processando documentos...",
                channel=channel_id,
                thread_ts=thread_ts
            )
            
            # Upload dos documentos para OpenAI
            slack_token = os.environ.get("SLACK_BOT_TOKEN")
            uploaded_files = await self.document_processor.upload_to_openai(
                document_files, slack_token
            )
            
            if uploaded_files:
                # Verificar se já existe um vector store para esta thread
                thread_key = f"{channel_id}_{thread_ts or 'main'}"
                existing_vector_store_id = self.thread_vector_stores.get(thread_key)
                
                if existing_vector_store_id:
                    # Adicionar arquivos ao vector store existente
                    vector_store_id = await self.document_processor.add_files_to_existing_vector_store(
                        existing_vector_store_id, uploaded_files
                    )
                    logger.info(f"📁 Arquivos adicionados ao vector store existente: {existing_vector_store_id}")
                else:
                    # Criar novo vector store
                    vector_store_id = await self.document_processor.create_vector_store_with_files(
                        uploaded_files, f"Documentos - {channel_id}"
                    )
                    if vector_store_id:
                        self.thread_vector_stores[thread_key] = vector_store_id
                        logger.info(f"📁 Novo vector store criado para thread: {vector_store_id}")
                
                if vector_store_id:
                    # Criar agente temporário com FileSearchTool para esta conversa
                    await self._create_temporary_agent_with_vector_store(vector_store_id)
                    
                    # Formatar resumo dos arquivos processados
                    summary = self.document_processor.format_upload_summary(uploaded_files)
                    
                    # Atualizar mensagem de status
                    await client.chat_update(
                        channel=channel_id,
                        ts=status_msg["ts"],
                        text=summary
                    )
                    
                    # Retornar contexto para o agente
                    file_names = [f["name"] for f in uploaded_files]
                    return f"📄 O usuário enviou {len(uploaded_files)} documento(s): {', '.join(file_names)}. Os documentos foram processados e estão disponíveis para consulta via file_search."
                else:
                    await client.chat_update(
                        channel=channel_id,
                        ts=status_msg["ts"],
                        text="❌ Erro ao criar base de conhecimento com os documentos."
                    )
            else:
                await client.chat_update(
                    channel=channel_id,
                    ts=status_msg["ts"],
                    text="❌ Não foi possível processar os documentos enviados."
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            if 'status_msg' in locals():
                try:
                    await client.chat_update(
                        channel=channel_id,
                        ts=status_msg["ts"],
                        text="❌ Erro interno ao processar documentos."
                    )
                except:
                    pass
            return None

    async def _create_temporary_agent_with_vector_store(self, vector_store_id: str):
        """Cria um agente temporário com FileSearchTool para a vector store efêmera."""
        try:
            from .config import set_global_agent
            from agent.creator import create_agent_with_vector_store
            
            logger.info(f"Criando agente temporário com vector store efêmera: {vector_store_id}")
            
            # Criar agente temporário com FileSearchTool para esta conversa
            temporary_agent = await create_agent_with_vector_store(vector_store_id)
            if temporary_agent:
                set_global_agent(temporary_agent)
                self.current_vector_store_id = vector_store_id  # Store for file count detection
                logger.info("✅ Agente temporário criado com FileSearchTool ativo")
            else:
                logger.error("❌ Falha ao criar agente temporário")
                
        except Exception as e:
            logger.error(f"Erro ao criar agente temporário: {e}")

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

    async def process_think_message(
        self,
        message: str,
        channel_id: str,
        user_id: str,
        thread_ts: str,
        say,
        client,
        improve_prompt: bool = False,
        thread_history: list = None
    ):
        """Process a think message with sequential PromptImprover -> DeepThinking workflow."""
        try:
            from agents import Agent, Runner
            
            final_prompt = message
            
            # Step 1: Improve prompt if requested
            if improve_prompt and thread_history:
                print(f"[DEBUG] Iniciando reformulação do prompt: {message}")
                
                # Create GPT-4o agent for prompt improvement
                improvement_agent = Agent(
                    name="PromptImprover",
                    model="gpt-4o",
                    instructions="""
Você é um especialista em reformular prompts para análise profunda.

Sua tarefa:
1. Reformule o prompt original deixando-o mais claro, organizado e direto
2. Use o contexto da conversa para entender melhor o que o usuário quer analisar
3. Mantenha o idioma original do prompt
4. Responda APENAS com o prompt reformulado, sem explicações adicionais
5. Torne o prompt mais específico e direcionado para análise profunda
"""
                )
                
                # Format thread history for context
                context = "\n".join([
                    f"Usuário: {msg.get('text', '')}" if msg.get('user') != self.bot_user_id 
                    else f"Livia: {msg.get('text', '')}"
                    for msg in thread_history[-10:]  # Last 10 messages for context
                ])
                
                # Create input for improvement
                improvement_input = f"Contexto da conversa:\n{context}\n\nPrompt original para reformular:\n{message}"
                
                # Run the improvement agent
                improvement_result = await Runner.run(
                    improvement_agent,
                    input=improvement_input,
                    max_turns=1
                )
                
                final_prompt = improvement_result.final_output.strip()
                print(f"[DEBUG] Prompt reformulado: {final_prompt}")
            
            # Step 2: Deep thinking with o3
            print(f"[DEBUG] Iniciando análise profunda com o3: {final_prompt}")
            
            # Update message to show deep analysis is starting
            if client:
                await client.chat_update(
                    channel=channel_id,
                    ts=thread_ts,
                    text=":brain: Analisando cuidadosamente..."
                )
            
            # Create a simple o3 agent for deep thinking
            o3_agent = Agent(
                name="DeepThinking",
                model="o3-mini",
                instructions="""
Você é um assistente especializado em análise profunda. Forneça análises abrangentes, detalhadas e bem estruturadas.

Diretrizes:
- Seja detalhado e completo na análise
- Use estrutura clara com tópicos e subtópicos
- Forneça insights acionáveis
- Responda sempre no mesmo idioma da pergunta
- Seja objetivo mas abrangente
"""
            )
            
            # Process with o3 model directly
            result = await Runner.run(
                o3_agent,
                input=final_prompt,
                max_turns=1
            )
            
            # Get the final output
            final_response = result.final_output
            print(f"[DEBUG] Resposta do o3 (tamanho: {len(final_response)} chars)")
            
            # Check if message is too long for Slack (limit ~3000 chars for safety)
            if len(final_response) > 3000:
                # Split into smaller parts
                parts = self._split_long_message(final_response, max_length=3000)
                
                # Send first part
                first_msg = await say(
                    text=parts[0],
                    thread_ts=thread_ts
                )
                
                # Send remaining parts as new messages (without continuation markers)
                for part in parts[1:]:
                    await say(
                        text=part,
                        thread_ts=thread_ts
                    )
            else:
                # Send the complete result
                await say(
                    text=final_response,
                    thread_ts=thread_ts
                )
            
        except Exception as e:
            logger.error(f"Error in process_think_message: {e}", exc_info=True)
            await say(
                text=f"Erro ao processar análise: {str(e)}",
                thread_ts=thread_ts
            )
    
    def _split_long_message(self, message: str, max_length: int = 3000) -> List[str]:
        """Split a long message into smaller parts for Slack."""
        if len(message) <= max_length:
            return [message]
        
        parts = []
        current_part = ""
        
        # Split by paragraphs first
        paragraphs = message.split('\n\n')
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed limit, save current part
            if len(current_part) + len(paragraph) + 2 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = paragraph
                else:
                    # Paragraph itself is too long, split by sentences
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_part) + len(sentence) + 2 > max_length:
                            if current_part:
                                parts.append(current_part.strip())
                                current_part = sentence
                            else:
                                # Sentence too long, force split
                                while len(sentence) > max_length:
                                    parts.append(sentence[:max_length])
                                    sentence = sentence[max_length:]
                                current_part = sentence
                        else:
                            current_part += sentence + '. '
            else:
                current_part += paragraph + '\n\n'
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
