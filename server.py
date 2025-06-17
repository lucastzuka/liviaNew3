#!/usr/bin/env python3
"""
Servidor Slack Socket Mode para o Chatbot Livia
-----------------------------------------------
Servidor principal usando Slack Bolt com Socket Mode para comunicação em tempo real.
Inclui respostas em streaming, cache de prompts e restrições de segurança.
Responde apenas quando mencionado na primeira mensagem de threads.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List

from security_utils import setup_global_logging_redaction
setup_global_logging_redaction()

import slack_bolt
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
import ssl
import certifi
import tiktoken
from collections import defaultdict
from dotenv import load_dotenv

# Error handling imports
import openai
from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError
import time

# Error handling imports
import openai
from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError
import time


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Return token count for text using tiktoken."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

# --- Fixed Error Messages (No Token Usage) ---
def get_user_friendly_error_message(error: Exception) -> str:
    """
    Retorna mensagens de erro fixas para evitar gasto de tokens.
    Todas as mensagens seguem o padrão: "Erro: xxx. Se persistir entre em contato com: <@U046LTU4TT5>"
    """
    error_str = str(error).lower()

    # OpenAI API specific errors
    if isinstance(error, APITimeoutError):
        return "Erro: Timeout na API. Se persistir entre em contato com: <@U046LTU4TT5>"

    elif isinstance(error, RateLimitError):
        return "Erro: Limite de requisições atingido. Se persistir entre em contato com: <@U046LTU4TT5>"

    elif isinstance(error, APIConnectionError):
        return "Erro: Falha de conexão com OpenAI. Se persistir entre em contato com: <@U046LTU4TT5>"

    elif isinstance(error, APIError):
        if "context_length_exceeded" in error_str or "token" in error_str:
            return "Erro: Conversa muito longa. Comece uma nova thread."
        elif "model" in error_str and "not found" in error_str:
            return "Erro: Modelo indisponível. Se persistir entre em contato com: <@U046LTU4TT5>"
        else:
            return "Erro: API OpenAI. Se persistir entre em contato com: <@U046LTU4TT5>"

    # Network and connection errors
    elif "timeout" in error_str or "timed out" in error_str:
        return "Erro: Timeout na operação. Se persistir entre em contato com: <@U046LTU4TT5>"

    elif "connection" in error_str or "network" in error_str:
        return "Erro: Problema de rede. Se persistir entre em contato com: <@U046LTU4TT5>"

    elif "ssl" in error_str or "certificate" in error_str:
        return "Erro: Certificado SSL. Se persistir entre em contato com: <@U046LTU4TT5>"

    # Slack API errors
    elif "slack" in error_str:
        if "rate_limited" in error_str:
            return "Erro: Limite do Slack atingido. Se persistir entre em contato com: <@U046LTU4TT5>"
        elif "channel_not_found" in error_str:
            return "Erro: Canal não encontrado. Se persistir entre em contato com: <@U046LTU4TT5>"
        else:
            return "Erro: API do Slack. Se persistir entre em contato com: <@U046LTU4TT5>"

    # Memory and resource errors
    elif "memory" in error_str or "out of" in error_str:
        return "Erro: Recursos insuficientes. Se persistir entre em contato com: <@U046LTU4TT5>"

    # Permission errors
    elif "permission" in error_str or "unauthorized" in error_str or "forbidden" in error_str:
        return "Erro: Sem permissão. Se persistir entre em contato com: <@U046LTU4TT5>"

    # Generic fallback
    else:
        return "Erro: Falha inesperada. Se persistir entre em contato com: <@U046LTU4TT5>"

def should_retry_error(error: Exception) -> bool:
    """
    Determina se um erro deve ser tentado novamente automaticamente.
    """
    error_str = str(error).lower()

    # Retry for temporary issues
    retry_conditions = [
        isinstance(error, (APITimeoutError, APIConnectionError)),
        "timeout" in error_str,
        "connection" in error_str,
        "network" in error_str,
        "rate_limited" in error_str,
        "temporarily unavailable" in error_str,
        "service unavailable" in error_str
    ]

    return any(retry_conditions)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

from agent import (
    create_agent_with_mcp_servers,
    create_agent,
    process_message,
)
from tools import ImageProcessor, image_generator
from slack_formatter import format_message_for_slack

# --- Configuração de Logging ---
# 🔇 TERMINAL LIMPO: Exibir apenas interações essenciais do bot
logging.basicConfig(
    level=logging.CRITICAL, format="%(message)s"  # Only show CRITICAL messages with clean format
)
logger = logging.getLogger(__name__)

# Silencia TODOS os logs do framework completamente - define como CRITICAL para ocultar DEBUG/INFO/WARNING
logging.getLogger("slack_bolt").setLevel(logging.CRITICAL)
logging.getLogger("slack_bolt.AsyncApp").setLevel(logging.CRITICAL)
logging.getLogger("slack_bolt.middleware").setLevel(logging.CRITICAL)
logging.getLogger("slack_bolt.IgnoringSelfEvents").setLevel(logging.CRITICAL)
logging.getLogger("slack_sdk").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("openai").setLevel(logging.CRITICAL)
logging.getLogger("openai.agents").setLevel(logging.CRITICAL)
logging.getLogger("openai._base_client").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("agent").setLevel(logging.CRITICAL)

# Desabilita todos os loggers do slack_bolt no nível root
for name in logging.root.manager.loggerDict:
    if name.startswith('slack_bolt'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
        logging.getLogger(name).disabled = True

# Define nível root de logging como CRITICAL para suprimir DEBUG/INFO/WARNING
logging.getLogger().setLevel(logging.CRITICAL)

# Cria um logger totalmente desabilitado para slack_bolt
slack_bolt_disabled_logger = logging.getLogger("slack_bolt_disabled")
slack_bolt_disabled_logger.setLevel(logging.CRITICAL)
slack_bolt_disabled_logger.disabled = True

# Sistema de cache de prompts para reduzir custos de API em consultas repetidas
prompt_cache = {}
PROMPT_CACHE_LIMIT = 100  # Maximum cached responses before cleanup

# Logger limpo customizado apenas para interações do bot
clean_logger = logging.getLogger("livia_clean")
clean_logger.setLevel(logging.INFO)
clean_handler = logging.StreamHandler()
clean_handler.setFormatter(logging.Formatter("%(message)s"))
clean_logger.addHandler(clean_handler)
clean_logger.propagate = False

# 🎨 Funções de logging visual para terminal limpo
def log_startup():
    clean_logger.info("=" * 60)
    clean_logger.info("🚀 LIVIA SLACK CHATBOT - INICIADO COM SUCESSO")
    clean_logger.info("=" * 60)
    clean_logger.info("🔒 Modo Desenvolvimento: APENAS canal C059NNLU3E1")
    clean_logger.info("🤖 Aguardando mensagens...")
    clean_logger.info("")

def log_message_received(user_id, channel_id, text):
    clean_logger.info("─" * 60)
    clean_logger.info(f"NOVA MENSAGEM")
    clean_logger.info(f"   Usuário: {user_id}")
    clean_logger.info(f"   Canal: {channel_id}")
    clean_logger.info(f"   Texto: {text[:100]}{'...' if len(text) > 100 else ''}")

def log_bot_response(response_text, tools_used=None):
    clean_logger.info(f"🤖 RESPOSTA LIVIA:")
    if tools_used:
        clean_logger.info(f"   🛠️ Ferramentas: {tools_used}")
    clean_logger.info(f"   💭 Resposta: {response_text[:150]}{'...' if len(response_text) > 150 else ''}")
    clean_logger.info("─" * 60)
    clean_logger.info("")

def log_error(error_msg):
    clean_logger.info("❌ ERRO:")
    clean_logger.info(f"   {error_msg}")
    clean_logger.info("")

# Variáveis Globais
# TODO: SLACK_INTEGRATION_POINT - Variáveis globais para integração com Slack
agent = None  # Agente OpenAI principal

# Semáforo de concorrência para múltiplos usuários
import math
try:
    max_concurrency = int(os.environ.get("LIVIA_MAX_CONCURRENCY", "5"))
    if max_concurrency < 1:
        raise ValueError
except Exception:
    logger.warning("Invalid LIVIA_MAX_CONCURRENCY, falling back to 5")
    max_concurrency = 5
agent_semaphore = asyncio.Semaphore(max_concurrency)
processed_messages = set()  # Cache de mensagens processadas
bot_user_id = "U057233T98A"  # ID do bot no Slack - IMPORTANTE para detectar menções

# Token usage tracking per thread/channel
thread_token_usage = defaultdict(int)
MODEL_CONTEXT_LIMITS = {
    "gpt-4o": 128000,
    "gpt-4.1-mini": 128000,
    "gpt-4.1-mini-mini": 128000,
    "gpt-4o-mini": 128000,
    "o3-mini": 128000,
}

# Unified Agents SDK configuration - all MCPs now use native multi-turn execution
logger.info("Using unified Agents SDK with native multi-turn execution for all MCPs")

# 🔒 STRICT DEVELOPMENT SECURITY: ONLY CHANNEL C059NNLU3E1 ALLOWED
ALLOWED_CHANNELS = {"C059NNLU3E1"}  # ONLY this specific channel - NO DMs, NO other channels
DEVELOPMENT_MODE = True             # Set to False for production
ALLOWED_USERS = set()               # NO DMs allowed in development mode
ALLOWED_DM_CHANNELS = set()         # NO DMs allowed in development mode

# 🔇 LOG LIMPO: Exibe apenas interações reais do bot, oculta blocos de segurança
SHOW_SECURITY_BLOCKS = False       # Set to True to see all security blocks in terminal
SHOW_DEBUG_LOGS = False             # Set to True to see debug logs
SHOW_AGENT_LOGS = False             # Set to True to see detailed agent logs

# --- Funções de Segurança ---
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
                logger.debug(f"SECURITY: Channel {channel_id} ALLOWED (development channel)")
            return True
        else:
            # Only show security blocks if explicitly enabled
            if SHOW_SECURITY_BLOCKS:
                logger.warning(f"SECURITY: Channel {channel_id} with user {user_id} - BLOCKED (development mode)")
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
                logger.error(f"SECURITY: Error checking channel info for {channel_id}: {e}")

        # Check if it's a cached DM channel
        if channel_id in ALLOWED_DM_CHANNELS:
            return True

        # Only show security blocks if explicitly enabled
        if SHOW_SECURITY_BLOCKS:
            logger.warning(f"SECURITY: Channel {channel_id} with user {user_id} - BLOCKED")
        return False

# --- Classe do Servidor ---
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



    # --- Context Window Management ---
    def _manage_context_window(self, messages: list, model: str, max_tokens_for_response: int = 4000) -> list:
        """
        Remove mensagens antigas automaticamente quando contexto fica muito cheio.
        Mantém sempre as mensagens mais recentes + margem para resposta.
        """
        if not messages:
            return messages

        context_limit = MODEL_CONTEXT_LIMITS.get(model, 128000)
        max_context_tokens = context_limit - max_tokens_for_response - 1000  # Margem de segurança

        # Calcular tokens das mensagens (do mais recente para o mais antigo)
        messages_with_tokens = []
        total_tokens = 0

        for msg in reversed(messages):  # Começar pelas mais recentes
            msg_text = f"[{msg.get('username', 'User')}]: {msg.get('text', '')}"
            msg_tokens = count_tokens(msg_text, model)

            if total_tokens + msg_tokens <= max_context_tokens:
                messages_with_tokens.insert(0, msg)  # Inserir no início para manter ordem
                total_tokens += msg_tokens
            else:
                # Contexto cheio, parar de adicionar mensagens antigas
                break

        removed_count = len(messages) - len(messages_with_tokens)
        if removed_count > 0:
            logger.info(f"🧹 Context management: Removed {removed_count} old messages to fit context window")
            logger.info(f"📊 Keeping {len(messages_with_tokens)} recent messages ({total_tokens} tokens)")

        return messages_with_tokens

    # --- Thread History Fetching Method ---
    async def _fetch_thread_history(self, channel_id: str, thread_ts: str) -> Optional[str]:
        """Busca e formata o histórico da thread com gerenciamento automático de contexto."""
        try:
            if SHOW_DEBUG_LOGS:
                logger.debug(f"Buscando histórico para thread {channel_id}/{thread_ts}...")

            # Get thread replies (aumentar limite para pegar mais histórico)
            response = await self.app.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=100  # Buscar mais mensagens, depois filtrar por contexto
            )

            if not response["ok"]:
                logger.warning(f"Erro ao buscar histórico da thread: {response.get('error', 'Erro desconhecido')}")
                return None

            messages = response.get("messages", [])
            if not messages:
                return None

            # Preparar mensagens com informações de usuário
            formatted_messages = []
            for msg in messages:
                user_id = msg.get("user", "Desconhecido")
                text = msg.get("text", "")

                # Get user info for better formatting
                try:
                    user_info = await self.app.client.users_info(user=user_id)
                    username = user_info["user"]["display_name"] or user_info["user"]["real_name"] or user_id
                except:
                    username = user_id

                formatted_messages.append({
                    "username": username,
                    "text": text,
                    "ts": msg.get("ts", "")
                })

            # Aplicar gerenciamento de contexto (manter mensagens mais recentes)
            global agent
            model = agent.model if agent else "gpt-4o-mini"
            managed_messages = self._manage_context_window(formatted_messages, model)

            # Format the final thread history
            formatted_history = "Histórico da Thread:\n"
            for msg in managed_messages:
                formatted_history += f"[{msg['username']}]: {msg['text']}\n"

            return formatted_history

        except Exception as e:
            logger.error(f"Erro ao buscar histórico da thread: {e}", exc_info=True)
            return None

    # --- Streaming Message Processing & Response Method ---
    async def _process_and_respond_streaming(
        self,
        text: str,
        say: slack_bolt.Say,
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
        global agent, agent_semaphore
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
        if not await is_channel_allowed(channel_id, user_id or "unknown", self.app.client):
            return

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
            full_history = await self._fetch_thread_history(channel_id, thread_ts_for_reply)
            if full_history:
                context_input = full_history + f"\n\nLatest message: {context_input}"
            else:
                if SHOW_DEBUG_LOGS:
                    logger.warning("Failed to fetch thread history.")

        # --- Static thinking message ---
        async with agent_semaphore:
            thinking_msg = await say(text=":hourglass_flowing_sand: Pensando...", channel=original_channel_id, thread_ts=thread_ts_for_reply)
            message_ts = thinking_msg.get("ts")

            # --- Cumulative Tag System ---
            def derive_cumulative_tags(tool_calls, audio_files, image_urls, user_message=None, final_response=None):
                """
                Constrói tags cumulativas mostrando todas as tecnologias usadas na resposta.
                Formato: `⛭ gpt-4.1-mini` `Vision` `WebSearch` etc.
                """
                tags = []

                # Check if thinking tool was used to determine the correct model
                thinking_used = False
                if tool_calls:
                    for call in tool_calls:
                        name = (call.get("tool_name", "") or call.get("name", "")).lower()
                        if "deep_thinking_analysis" in name or "thinking" in name:
                            thinking_used = True
                            break

                # Use o3-mini if thinking tool was used, otherwise use the main model
                if thinking_used:
                    tags.append("o3-mini")
                else:
                    tags.append(model_name)

                # Add Vision if images are being processed
                if image_urls:
                    tags.append("Vision")

                # Add AudioTranscribe if audio files are present
                if audio_files:
                    tags.append("AudioTranscribe")

                # Add tools based on tool calls
                if tool_calls:
                    for call in tool_calls:
                        # Try both tool_name and tool_type (lowercase)
                        name = (call.get("tool_name", "") or call.get("name", "")).lower()
                        tool_type = call.get("tool_type", "").lower()

                        # Web Search detection
                        if "web_search" in name or "web_search" in tool_type:
                            if "WebSearch" not in tags:
                                tags.append("WebSearch")

                        # Image Generation detection
                        elif name == "image_generation_tool" or tool_type == "image_generation_tool":
                            if "ImageGen" not in tags:
                                tags.append("ImageGen")

                        # Thinking Agent detection
                        elif "deep_thinking_analysis" in name or "thinking" in name:
                            if "Thinking" not in tags:
                                tags.append("Thinking")

                        # MCP detection
                        elif "mcp" in name or "mcp" in tool_type:
                            # Extract MCP service name
                            if "everhour" in name or "everhour" in tool_type:
                                if "McpEverhour" not in tags:
                                    tags.append("McpEverhour")
                            elif "asana" in name or "asana" in tool_type:
                                if "McpAsana" not in tags:
                                    tags.append("McpAsana")
                            elif "gmail" in name or "gmail" in tool_type:
                                if "McpGmail" not in tags:
                                    tags.append("McpGmail")
                            elif "google" in name or "drive" in name or "gdrive" in name:
                                if "McpGoogleDrive" not in tags:
                                    tags.append("McpGoogleDrive")
                            elif "calendar" in name:
                                if "McpGoogleCalendar" not in tags:
                                    tags.append("McpGoogleCalendar")
                            elif "docs" in name:
                                if "McpGoogleDocs" not in tags:
                                    tags.append("McpGoogleDocs")
                            elif "sheets" in name:
                                if "McpGoogleSheets" not in tags:
                                    tags.append("McpGoogleSheets")
                            elif "slack" in name:
                                if "McpSlack" not in tags:
                                    tags.append("McpSlack")

                        # Skip file_search - it's always active (RAG)
                        # We don't show FileSearch tag since it's background functionality

                # Enhanced detection: Check response content for web search indicators (more specific)
                if final_response and "WebSearch" not in tags:
                    response_content = final_response.lower()

                    # More specific web search indicators
                    web_indicators = [
                        "brandcolorcode.com", "wikipedia.org", "bing.com",
                        "utm_source=openai", "search result", "according to", "source:",
                        "based on search", "found on", "website", "search engine"
                    ]

                    # Check for specific web search patterns (exclude common URLs)
                    import re
                    # Look for external URLs but exclude common internal ones
                    external_urls = bool(re.search(r"https?://(?!drive\.google\.com|docs\.google\.com|calendar\.google\.com)", final_response))
                    has_web_indicators = any(indicator in response_content for indicator in web_indicators)

                    # Only add WebSearch if we have clear web search indicators
                    if (external_urls and has_web_indicators) or any(indicator in response_content for indicator in ["brandcolorcode.com", "utm_source=openai"]):
                        tags.append("WebSearch")

                # Enhanced detection: Check if MCP was used based on response content and user message
                if final_response or user_message:
                    response_content = (final_response or "").lower()
                    message_content = (user_message or "").lower()
                    combined_content = response_content + " " + message_content

                    # Google Drive MCP indicators
                    drive_indicators = ["google drive", "my drive", "drive.google.com", "arquivo encontrado", "pasta encontrada", "gdrive", "livia.png", "id:", "drive da live"]
                    if any(indicator in combined_content for indicator in drive_indicators):
                        if "McpGoogleDrive" not in tags:
                            tags.append("McpGoogleDrive")

                    # Everhour MCP indicators (specific keyword only)
                    everhour_indicators = ["everhour", "tempo adicionado", "task ev:", "ev:"]
                    if any(indicator in combined_content for indicator in everhour_indicators):
                        if "McpEverhour" not in tags:
                            tags.append("McpEverhour")

                    # Asana MCP indicators (specific keyword only)
                    asana_indicators = ["asana"]
                    if any(indicator in combined_content for indicator in asana_indicators):
                        if "McpAsana" not in tags:
                            tags.append("McpAsana")

                    # Gmail MCP indicators (specific keyword only)
                    gmail_indicators = ["gmail"]
                    if any(indicator in combined_content for indicator in gmail_indicators):
                        if "McpGmail" not in tags:
                            tags.append("McpGmail")

                    # Google Docs MCP indicators
                    docs_indicators = ["google docs", "documento", "docs", "live_codigodeeticaeconduta"]
                    if any(indicator in combined_content for indicator in docs_indicators):
                        if "McpGoogleDocs" not in tags:
                            tags.append("McpGoogleDocs")

                    # Google Calendar MCP indicators
                    calendar_indicators = ["calendar", "calendario", "agenda", "evento", "reunião"]
                    if any(indicator in combined_content for indicator in calendar_indicators):
                        if "McpGoogleCalendar" not in tags:
                            tags.append("McpGoogleCalendar")

                    # Google Sheets MCP indicators
                    sheets_indicators = ["sheets", "google sheets", "planilha", "spreadsheet"]
                    if any(indicator in combined_content for indicator in sheets_indicators):
                        if "McpGoogleSheets" not in tags:
                            tags.append("McpGoogleSheets")

                return tags

            # --- Determine initial cumulative tags (heuristic) ---
            def get_initial_cumulative_tags():
                image_generation_keywords = [
                    "gere uma imagem", "gerar imagem", "criar imagem", "desenhe", "desenhar",
                    "faça uma imagem", "fazer imagem", "generate image", "create image", "draw"
                ]

                thinking_keywords = [
                    "+think", "thinking", "análise profunda", "análise detalhada",
                    "brainstorm", "brainstorming", "resolução de problema",
                    "estratégia", "decisão", "reflexão", "pensar", "analisar",
                    "problema complexo", "solução criativa", "insights"
                ]

                # Check if thinking will be used based on keywords
                thinking_will_be_used = any(keyword in (text or "").lower() for keyword in thinking_keywords)

                # Use o3-mini if thinking keywords detected, otherwise use main model
                if thinking_will_be_used:
                    initial_tags = ["o3-mini", "Thinking"]
                else:
                    initial_tags = [model_name]

                if any(keyword in (text or "").lower() for keyword in image_generation_keywords):
                    initial_tags.append("ImageGen")
                if audio_files:
                    initial_tags.append("AudioTranscribe")
                if image_urls and not any(keyword in (text or "").lower() for keyword in image_generation_keywords):
                    initial_tags.append("Vision")

                return initial_tags

            initial_tags = get_initial_cumulative_tags()
            # Format as: `⛭ gpt-4.1-mini` `Vision` etc.
            tag_display = " ".join([f"`⛭ {tag}`" if i == 0 else f"`{tag}`" for i, tag in enumerate(initial_tags)])
            header_prefix = f"{tag_display}\n\n"

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

                # Streaming callback to update Slack message
                current_text_only = ""
                sent_header = False
                last_update_length = 0
                detected_tools = []
                current_header_prefix = header_prefix
                import time
                last_update_time = time.time()

                # Circuit breaker variables for infinite loop protection
                stream_start_time = time.time()
                max_stream_duration = 120  # 2 minutes max
                max_response_length = 8000  # Max characters to prevent infinite responses
                update_count = 0
                max_updates = 200  # Max number of updates to prevent infinite loops

                async def stream_callback(delta_text: str, full_text: str, tool_calls_detected=None):
                    nonlocal current_text_only, last_update_length, last_update_time, sent_header, detected_tools, current_header_prefix, update_count

                    # Circuit breaker: Check for infinite loop conditions
                    current_time = time.time()
                    stream_duration = current_time - stream_start_time
                    update_count += 1

                    # Protection against infinite loops
                    if stream_duration > max_stream_duration:
                        logger.error(f"🚨 CIRCUIT BREAKER: Stream timeout after {stream_duration:.1f}s - stopping to prevent infinite loop")
                        return

                    if len(full_text) > max_response_length:
                        logger.error(f"🚨 CIRCUIT BREAKER: Response too long ({len(full_text)} chars) - stopping to prevent infinite loop")
                        return

                    if update_count > max_updates:
                        logger.error(f"🚨 CIRCUIT BREAKER: Too many updates ({update_count}) - stopping to prevent infinite loop")
                        return

                    # Check for repetitive content (potential loop indicator)
                    if full_text and len(full_text) > 100:
                        # Check if the last 50 characters are being repeated
                        text_end = full_text[-50:]
                        text_before_end = full_text[-150:-50] if len(full_text) > 150 else ""
                        if text_end in text_before_end:
                            logger.error(f"🚨 CIRCUIT BREAKER: Repetitive content detected - stopping to prevent infinite loop")
                            return

                    current_text_only = full_text

                    # Update detected tools if provided
                    if tool_calls_detected:
                        detected_tools.extend(tool_calls_detected)
                        # Update header based on cumulative tags
                        cumulative_tags = derive_cumulative_tags(detected_tools, audio_files, processed_image_urls, user_message=text, final_response=full_text)
                        # Format as: `⛭ {model_name}` `Vision` `WebSearch`
                        tag_display = " ".join([f"`⛭ {tag}`" if i == 0 else f"`{tag}`" for i, tag in enumerate(cumulative_tags)])
                        current_header_prefix = f"{tag_display}\n\n"

                    should_update = (
                        len(current_text_only) - last_update_length >= 10 or
                        current_time - last_update_time >= 0.5 or
                        not delta_text
                    )

                    if not sent_header:
                        # Replace thinking message with header before first chunk
                        try:
                            await self.app.client.chat_update(
                                channel=original_channel_id,
                                ts=message_ts,
                                text=current_header_prefix
                            )
                        except Exception as e:
                            logger.warning(f"Failed to set header before streaming: {e}")
                        sent_header = True
                        last_update_length = 0
                        last_update_time = current_time

                    if should_update and current_text_only:
                        try:
                            formatted_text = current_header_prefix + format_message_for_slack(current_text_only)
                            await self.app.client.chat_update(
                                channel=original_channel_id,
                                ts=message_ts,
                                text=formatted_text
                            )
                            last_update_length = len(current_text_only)
                            last_update_time = current_time
                        except Exception as update_error:
                            logger.warning(f"Failed to update streaming message: {update_error}")

                # Agent streaming with unified Agents SDK: { text, tools, structured_data? }
                response = await process_message(current_agent, context_input, processed_image_urls, stream_callback)
                text_resp = response.get("text") if isinstance(response, dict) else str(response)
                tool_calls = response.get("tools") if isinstance(response, dict) else []
                structured_data = response.get("structured_data") if isinstance(response, dict) else None
                # Final update with complete response
                if not sent_header:
                    # If for some reason we never got a chunk, replace thinking message with header
                    try:
                        await self.app.client.chat_update(
                            channel=original_channel_id,
                            ts=message_ts,
                            text=header_prefix
                        )
                    except Exception as e:
                        logger.warning(f"Failed to set header: {e}")

                # Compute header_prefix_final based on tools actually used (cumulative)
                final_cumulative_tags = derive_cumulative_tags(tool_calls, audio_files, processed_image_urls, user_message=text, final_response=text_resp)
                # Format as: `⛭ {model_name}` `Vision` `WebSearch`
                final_tag_display = " ".join([f"`⛭ {tag}`" if i == 0 else f"`{tag}`" for i, tag in enumerate(final_cumulative_tags)])
                header_prefix_final = f"{final_tag_display}\n\n"

                # Check if conversation is approaching token limit
                token_info = response.get("token_usage", {}) if isinstance(response, dict) else {}
                input_tokens = token_info.get("input", count_tokens(context_input))
                output_tokens = token_info.get("output", count_tokens(text_resp))
                total_tokens = input_tokens + output_tokens
                thread_key = thread_ts_for_reply or original_channel_id
                thread_token_usage[thread_key] += total_tokens
                context_limit = MODEL_CONTEXT_LIMITS.get(model_name, 128000)
                percent = (thread_token_usage[thread_key] / context_limit) * 100

                # Add memory limit warning only when reaching limit (100%+)
                memory_warning = ""
                if percent >= 100:
                    memory_warning = "\n\n⚠️ Você chegou no limite de memória, comece uma nova conversa."

                text_with_footer = text_resp + memory_warning
                try:
                    formatted_response = header_prefix_final + format_message_for_slack(text_with_footer)
                    await self.app.client.chat_update(
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
                        return await self._process_and_respond_streaming(
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
                        await self.app.client.chat_update(
                            channel=original_channel_id,
                            ts=message_ts,
                            text=user_error_msg
                        )
                    else:
                        await say(text=user_error_msg, channel=original_channel_id, thread_ts=thread_ts_for_reply)
                except:
                    await say(text="Erro: Falha na comunicação. Se persistir entre em contato com: <@U046LTU4TT5>", channel=original_channel_id, thread_ts=thread_ts_for_reply)
            finally:
                # Clean up processing protection
                if hasattr(self, '_active_processing'):
                    processing_key = f"{original_channel_id}_{thread_ts_for_reply}_{user_id}"
                    self._active_processing.discard(processing_key)

    # --- Message Processing & Response Method ---
    async def _process_and_respond(
        self,
        text: str,
        say: slack_bolt.Say,
        channel_id: str,
        thread_ts_for_reply: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        use_thread_history: bool = True,
        user_id: str = None,
        model_override: Optional[str] = None,
    ):
        """
        Synchronous (non-streaming) response with static ":hourglass_flowing_sand: Pensando..." message replaced by tags + response.
        """
        global agent, agent_semaphore
        current_agent = agent
        if model_override:
            import copy
            current_agent = copy.deepcopy(agent)
            current_agent.model = model_override

        if not current_agent:
            logger.error("Livia agent not ready.")
            await say(text="Livia is starting up, please wait.", channel=channel_id, thread_ts=thread_ts_for_reply)
            return

        original_channel_id = channel_id
        if not await is_channel_allowed(channel_id, user_id or "unknown", self.app.client):
            return

        # Enhanced bot response detection to prevent infinite loops
        bot_response_patterns = [
            "encontrei o arquivo", "você pode acessá-lo", "estou à disposição",
            "não consegui encontrar", "vou procurar", "aqui está",
            "hoje é segunda-feira", "hoje é terça-feira", "hoje é quarta-feira",
            "hoje é quinta-feira", "hoje é sexta-feira", "hoje é sábado", "hoje é domingo",
            "corpus christi", "ponto facultativo", "feriados.inf.br",
            "⛭ gpt-", "websearch", "vision", "imageGen", "mcpgmail", "mcpeverhour"
        ]

        if text and any(phrase in text.lower() for phrase in bot_response_patterns):
            logger.info("Detected bot's own response pattern, skipping processing to prevent loop")
            return

        # Additional protection: Check for repetitive content that might indicate a loop
        if text and len(text) > 50:
            # Check if the message contains repetitive patterns
            words = text.lower().split()
            if len(words) > 10:
                # Check for repeated phrases (potential loop indicator)
                word_counts = {}
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1

                # If any word appears more than 30% of the time, it might be a loop
                max_word_frequency = max(word_counts.values()) if word_counts else 0
                if max_word_frequency > len(words) * 0.3:
                    logger.warning(f"🚨 LOOP PROTECTION: Detected repetitive content, skipping to prevent infinite loop")
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

        # --- Static thinking message ---
        async with agent_semaphore:
            # Additional protection: Check if we're already processing something similar
            processing_key = f"{original_channel_id}_{thread_ts_for_reply}_{user_id}"
            if hasattr(self, '_active_processing') and processing_key in self._active_processing:
                logger.warning(f"🚨 DUPLICATE PROTECTION: Already processing request for {processing_key}, skipping")
                return

            # Mark as processing
            if not hasattr(self, '_active_processing'):
                self._active_processing = set()
            self._active_processing.add(processing_key)

            try:
                thinking_msg = await say(text=":hourglass_flowing_sand:Pensando...", channel=original_channel_id, thread_ts=thread_ts_for_reply)
                message_ts = thinking_msg.get("ts")

                # --- Cumulative Tag System for Non-Streaming ---
                def derive_cumulative_tags_non_streaming(tool_calls, audio_files, image_urls):
                    """Constrói tags cumulativas para respostas não-streaming."""
                    # Check if thinking tool was used to determine the correct model
                    thinking_used = False
                    if tool_calls:
                        for call in tool_calls:
                            name = call.get("tool_name", call.get("name", "")).lower()
                            if "deep_thinking_analysis" in name or "thinking" in name:
                                thinking_used = True
                                break

                    # Use o3-mini if thinking tool was used, otherwise use the main model
                    if thinking_used:
                        tags = ["o3-mini"]
                    else:
                        tags = [model_name]

                    # Add Vision if images are being processed
                    if image_urls:
                        tags.append("Vision")

                    # Add AudioTranscribe if audio files are present
                    if audio_files:
                        tags.append("AudioTranscribe")

                    # Add tools based on tool calls
                    if tool_calls:
                        for call in tool_calls:
                            name = call.get("tool_name", call.get("name", "")).lower()
                            tool_type = call.get("tool_type", "").lower()

                            # Web Search detection
                            if "web_search" in name or "web_search" in tool_type:
                                if "WebSearch" not in tags:
                                    tags.append("WebSearch")

                            # Image Generation detection
                            elif name == "image_generation_tool" or tool_type == "image_generation_tool":
                                if "ImageGen" not in tags:
                                    tags.append("ImageGen")

                            # Thinking Agent detection
                            elif "deep_thinking_analysis" in name or "thinking" in name:
                                if "Thinking" not in tags:
                                    tags.append("Thinking")

                            # MCP detection
                            elif "mcp" in name or "mcp" in tool_type:
                                # Extract MCP service name
                                if "everhour" in name or "everhour" in tool_type:
                                    if "McpEverhour" not in tags:
                                        tags.append("McpEverhour")
                                elif "asana" in name or "asana" in tool_type:
                                    if "McpAsana" not in tags:
                                        tags.append("McpAsana")
                                elif "gmail" in name or "gmail" in tool_type:
                                    if "McpGmail" not in tags:
                                        tags.append("McpGmail")
                                elif "google" in name or "drive" in name or "gdrive" in name:
                                    if "McpGoogleDrive" not in tags:
                                        tags.append("McpGoogleDrive")
                                elif "calendar" in name:
                                    if "McpGoogleCalendar" not in tags:
                                        tags.append("McpGoogleCalendar")
                                elif "docs" in name:
                                    if "McpGoogleDocs" not in tags:
                                        tags.append("McpGoogleDocs")
                                elif "sheets" in name:
                                    if "McpGoogleSheets" not in tags:
                                        tags.append("McpGoogleSheets")
                                elif "slack" in name:
                                    if "McpSlack" not in tags:
                                        tags.append("McpSlack")

                    return tags

                def derive_cumulative_tags_non_streaming_with_response(tool_calls, audio_files, image_urls, final_response=None, user_message=None):
                    """Build cumulative tags for non-streaming responses with response analysis."""
                    tags = derive_cumulative_tags_non_streaming(tool_calls, audio_files, image_urls)

                    # Enhanced detection: Check if MCP was used based on response content and user message
                    if final_response or user_message:
                        response_content = (final_response or "").lower()
                        message_content = (user_message or "").lower()
                        combined_content = response_content + " " + message_content

                        # Google Drive MCP indicators
                        drive_indicators = ["google drive", "my drive", "drive.google.com", "arquivo encontrado", "pasta encontrada", "gdrive", "livia.png", "id:", "drive da live"]
                        if any(indicator in combined_content for indicator in drive_indicators):
                            if "McpGoogleDrive" not in tags:
                                tags.append("McpGoogleDrive")

                        # Everhour MCP indicators (specific keyword only)
                        everhour_indicators = ["everhour", "tempo adicionado", "task ev:", "ev:"]
                        if any(indicator in combined_content for indicator in everhour_indicators):
                            if "McpEverhour" not in tags:
                                tags.append("McpEverhour")

                        # Asana MCP indicators (specific keyword only)
                        asana_indicators = ["asana"]
                        if any(indicator in combined_content for indicator in asana_indicators):
                            if "McpAsana" not in tags:
                                tags.append("McpAsana")

                        # Gmail MCP indicators (specific keyword only)
                        gmail_indicators = ["gmail"]
                        if any(indicator in combined_content for indicator in gmail_indicators):
                            if "McpGmail" not in tags:
                                tags.append("McpGmail")

                        # Google Docs MCP indicators
                        docs_indicators = ["google docs", "documento", "docs", "live_codigodeeticaeconduta"]
                        if any(indicator in combined_content for indicator in docs_indicators):
                            if "McpGoogleDocs" not in tags:
                                tags.append("McpGoogleDocs")

                        # Google Calendar MCP indicators
                        calendar_indicators = ["calendar", "calendario", "agenda", "evento", "reunião"]
                        if any(indicator in combined_content for indicator in calendar_indicators):
                            if "McpGoogleCalendar" not in tags:
                                tags.append("McpGoogleCalendar")

                        # Google Sheets MCP indicators
                        sheets_indicators = ["sheets", "google sheets", "planilha", "spreadsheet"]
                        if any(indicator in combined_content for indicator in sheets_indicators):
                            if "McpGoogleSheets" not in tags:
                                tags.append("McpGoogleSheets")

                    return tags

                def get_initial_tags_non_streaming():
                    image_generation_keywords = [
                        "gere uma imagem", "gerar imagem", "criar imagem", "desenhe", "desenhar",
                        "faça uma imagem", "fazer imagem", "generate image", "create image", "draw"
                    ]

                    thinking_keywords = [
                        "+think", "thinking", "análise profunda", "análise detalhada",
                        "brainstorm", "brainstorming", "resolução de problema",
                        "estratégia", "decisão", "reflexão", "pensar", "analisar",
                        "problema complexo", "solução criativa", "insights"
                    ]

                    # Check if thinking will be used based on keywords
                    thinking_will_be_used = any(keyword in (text or "").lower() for keyword in thinking_keywords)

                    # Use o3-mini if thinking keywords detected, otherwise use main model
                    if thinking_will_be_used:
                        initial_tags = ["o3-mini", "Thinking"]
                    else:
                        initial_tags = [model_name]

                    if any(keyword in (text or "").lower() for keyword in image_generation_keywords):
                        initial_tags.append("ImageGen")
                    if image_urls and not any(keyword in (text or "").lower() for keyword in image_generation_keywords):
                        initial_tags.append("Vision")

                    return initial_tags

                initial_tags = get_initial_tags_non_streaming()
                # Format as: `⛭ {model_name}` `Vision` etc.
                tag_display = " ".join([f"`⛭ {tag}`" if i == 0 else f"`{tag}`" for i, tag in enumerate(initial_tags)])
                header_prefix = f"{tag_display}\n\n"

                # Check prompt cache for repeated queries
                cache_key = f"{text}_{len(image_urls) if image_urls else 0}"
                if cache_key in prompt_cache:
                    logger.info(f"Cache HIT for message: {text[:50]}...")
                    cached_response = prompt_cache[cache_key]
                    await self.app.client.chat_update(
                        channel=original_channel_id,
                        ts=message_ts,
                        text=f"`⛭ Cached` `⛭ {model_name}`\n\n{cached_response}"
                    )
                    return

                logger.info(
                    f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] Processing message via Livia agent..."
                )

                processed_image_urls = []
                if image_urls:
                    logger.info(f"Processing {len(image_urls)} images: {image_urls}")
                    processed_image_urls = await ImageProcessor.process_image_urls(image_urls)
                    logger.info(f"Successfully processed {len(processed_image_urls)} images")
                else:
                    logger.info("No images detected in this message")

                response = await process_message(current_agent, context_input, processed_image_urls, None)

                text_resp = response.get("text") if isinstance(response, dict) else str(response)
                tool_calls = response.get("tools") if isinstance(response, dict) else []
                final_cumulative_tags = derive_cumulative_tags_non_streaming_with_response(tool_calls, [], processed_image_urls, text_resp, text)
                # Format as: `⛭ {model_name}` `Vision` `WebSearch`
                final_tag_display = " ".join([f"`⛭ {tag}`" if i == 0 else f"`{tag}`" for i, tag in enumerate(final_cumulative_tags)])
                header_prefix_final = f"{final_tag_display}\n\n"

                logger.info(f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] USER REQUEST: {context_input}")
                logger.info(f"[{original_channel_id}-{thread_ts_for_reply}-{user_id}] BOT RESPONSE: {text_resp}")

                # Check if conversation is approaching token limit
                token_info = response.get("token_usage", {}) if isinstance(response, dict) else {}
                input_tokens = token_info.get("input", count_tokens(context_input))
                output_tokens = token_info.get("output", count_tokens(text_resp))
                total_tokens = input_tokens + output_tokens
                thread_key = thread_ts_for_reply or original_channel_id
                thread_token_usage[thread_key] += total_tokens
                context_limit = MODEL_CONTEXT_LIMITS.get(model_name, 128000)
                percent = (thread_token_usage[thread_key] / context_limit) * 100

                # Add memory limit warning only when reaching limit (100%+)
                memory_warning = ""
                if percent >= 100:
                    memory_warning = "\n\n⚠️ Você chegou no limite de memória, comece uma nova conversa."

                text_with_footer = text_resp + memory_warning
                formatted_response = header_prefix_final + format_message_for_slack(text_with_footer)
                await self.app.client.chat_update(
                    channel=original_channel_id,
                    ts=message_ts,
                    text=formatted_response
                )

                # Save response to cache for future reuse
                if not image_urls and len(text_resp) < 2000:  # Cache only simple text responses
                    prompt_cache[cache_key] = text_resp
                    if len(prompt_cache) > PROMPT_CACHE_LIMIT:
                        prompt_cache.popitem(last=False)  # Remove oldest entry
                    logger.info(f"Cached response for: {text[:50]}...")
            except Exception as e:
                logger.error(f"Error during Livia agent processing: {e}", exc_info=True)

                # Get user-friendly error message
                user_error_msg = get_user_friendly_error_message(e)

                await self.app.client.chat_update(
                    channel=original_channel_id,
                    ts=message_ts,
                    text=user_error_msg
                )
            finally:
                # Clean up processing protection
                if hasattr(self, '_active_processing'):
                    processing_key = f"{original_channel_id}_{thread_ts_for_reply}_{user_id}"
                    self._active_processing.discard(processing_key)

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
                    text="Erro: Prompt de imagem inválido. Se persistir entre em contato com: <@U046LTU4TT5>",
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
                            text="Erro: Upload de imagem falhou. Se persistir entre em contato com: <@U046LTU4TT5>"
                        )

                    # Clean up temporary file
                    image_generator.cleanup_temp_file(result["image_path"])
                else:
                    # Case where no image was generated
                    await self.app.client.chat_update(
                        channel=channel_id,
                        ts=message_ts,
                        text="Erro: Geração de imagem falhou. Se persistir entre em contato com: <@U046LTU4TT5>"
                    )

            else:
                await self.app.client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    text="Erro: Geração de imagem falhou. Se persistir entre em contato com: <@U046LTU4TT5>"
                )

        except Exception as e:
            logger.error(f"Error in image generation: {e}", exc_info=True)
            await say(
                text="Erro: Geração de imagem falhou. Se persistir entre em contato com: <@U046LTU4TT5>",
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

            Habilitado para concorrência: agora, após todas as validações, cada mensagem é processada em paralelo
            até o limite de LIVIA_MAX_CONCURRENCY usando asyncio.Semaphore.
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
                # Silent block - only log if explicitly enabled
                if SHOW_SECURITY_BLOCKS:
                    logger.warning(f"SECURITY: Blocked message event from unauthorized channel {channel_id}")
                return

            text = event.get("text", "").strip()
            thread_ts = event.get("thread_ts")

            clean_logger.info(f"📩 Mensagem: '{text}' | Canal: {channel_id}")

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
                # Direct message, processing...
                should_process = True
            elif thread_ts and await self._is_thread_started_with_mention(channel_id, thread_ts):
                # Thread started with mention, processing...
                should_process = True
            else:
                # Thread did not start with mention, ignoring
                pass

            if should_process:
                image_urls = self._extract_image_urls(event)
                audio_files = self._extract_audio_files(event)
                logger.info(f"Extracted {len(image_urls)} image URLs and {len(audio_files)} audio files")
                # Spawn processing as a background task to enable high concurrency
                asyncio.create_task(
                    self._process_and_respond_streaming(
                        text=text,
                        say=say,
                        channel_id=channel_id,
                        thread_ts_for_reply=thread_ts,
                        image_urls=image_urls,
                        audio_files=audio_files,
                        user_id=event.get("user")
                    )
                )

        @self.app.event("app_mention")
        async def handle_app_mentions(body: Dict[str, Any], say: slack_bolt.Say):
            """
            SLACK_INTEGRATION_POINT - Handler para menções diretas ao bot (@livia)

            Habilitado para concorrência: após validações, o processamento é feito em background task,
            permitindo dezenas de execuções simultâneas até o limite do semáforo global.
            """
            event = body.get("event", {})

            if event.get("user") == "U057233T98A":  # Bot user ID
                logger.info("Ignoring app mention from bot itself")
                return

            # DEVELOPMENT SECURITY: Early channel validation
            channel_id = event.get("channel")
            user_id = event.get("user")
            if not await is_channel_allowed(channel_id, user_id, self.app.client):
                # Silent block - only log if explicitly enabled
                if SHOW_SECURITY_BLOCKS:
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

            log_message_received(user_id, channel_id, text)

            # Remove the mention from the text and protect against multiple mentions
            try:
                auth_response = await self.app.client.auth_test()
                current_bot_id = auth_response["user_id"]

                # Count mentions to detect potential spam/loops
                mention_pattern = f"<@{current_bot_id}>"
                mention_count = text.count(mention_pattern)

                if mention_count > 3:
                    logger.warning(f"🚨 PROTECTION: Too many mentions ({mention_count}) detected - potential spam/loop, limiting processing")
                    # Still process but with a warning message
                    text = f"⚠️ Detectei muitas menções ({mention_count}). Processando apenas uma vez para evitar loops."
                else:
                    # Remove all mentions normally
                    text = text.replace(mention_pattern, "").strip()
                    logger.info(f"Cleaned text after removing {mention_count} mention(s): '{text}'")

            except Exception as e:
                logger.error(f"Error getting bot user ID: {e}")
                # Fallback: try to remove any mention pattern
                import re
                original_text = text
                text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
                mention_count = len(re.findall(r'<@[A-Z0-9]+>', original_text))
                if mention_count > 3:
                    text = f"⚠️ Detectei muitas menções ({mention_count}). Processando apenas uma vez para evitar loops."
                logger.info(f"Fallback cleaned text: '{text}'")

            # Check for audio files even if no text
            image_urls = self._extract_image_urls(event)
            audio_files = self._extract_audio_files(event)
            logger.info(f"App mention: Extracted {len(image_urls)} image URLs and {len(audio_files)} audio files")

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

            # Spawn processing as a background task to enable high concurrency
            asyncio.create_task(
                self._process_and_respond_streaming(
                    text=text,
                    say=say,
                    channel_id=channel_id,
                    thread_ts_for_reply=thread_ts,
                    image_urls=image_urls,
                    audio_files=audio_files,
                    use_thread_history=False,  # Don't use history for initial mentions
                    user_id=event.get("user")
                )
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





    # --- Método de Inicialização do Servidor ---
    async def start(self):
        """Starts the Socket Mode server asynchronously."""
        logger.info("Starting Slack Socket Mode server (async)...")
        await self.socket_mode_handler.start_async()

# --- Funções de Inicialização e Limpeza do Agente ---
async def initialize_agent():
    """Initializes the Livia agent (without MCP Slack local - using direct API)."""
    global agent

    logger.info("Initializing Livia Agent (using direct Slack API)...")

    try:
        # Create the agent with MCP servers (unified OpenAI Agents SDK approach)
        agent = await create_agent_with_mcp_servers()
        logger.info("Livia agent successfully initialized with MCP servers.")

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