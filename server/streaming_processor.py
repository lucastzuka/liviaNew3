#!/usr/bin/env python3
"""
Streaming Processor
-------------------
Processamento de streaming e sistema de tags para respostas do bot.
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class StreamingProcessor:
    """Processa streaming de respostas e gerencia sistema de tags."""
    
    def __init__(self):
        self.stream_start_time = None
        self.max_stream_duration = 120  # 2 minutes max
        self.max_response_length = 8000  # Max characters to prevent infinite responses
        self.max_updates = 200  # Max number of updates to prevent infinite loops
    
    def derive_cumulative_tags(self, tool_calls: List[Dict], audio_files: Optional[List], 
                              image_urls: Optional[List], user_message: Optional[str] = None, 
                              final_response: Optional[str] = None, model_name: str = "gpt-4.1-mini") -> List[str]:
        """
        Constrói tags cumulativas mostrando todas as tecnologias usadas na resposta.
        Formato: `⛭ modelo` `Vision` `WebSearch` etc.
        Modelos: gpt-4.1-mini (texto), gpt-4o (visão), o3-mini (thinking)
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

        # Determine model based on content type and tools used
        if thinking_used:
            tags.append("o3-mini")
        elif image_urls:
            tags.append("gpt-4o")  # Use gpt-4o for vision processing
        else:
            tags.append(model_name)  # Default gpt-4.1-mini for text

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

    def get_initial_cumulative_tags(self, text: str, audio_files: Optional[List], 
                                   image_urls: Optional[List], model_name: str = "gpt-4.1-mini") -> List[str]:
        """Determine initial cumulative tags based on heuristics."""
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

        # Determine model based on content type
        if thinking_will_be_used:
            initial_tags = ["o3-mini", "Thinking"]
        elif image_urls:
            initial_tags = ["gpt-4o"]  # Use gpt-4o for vision processing
        else:
            initial_tags = [model_name]  # Default gpt-4.1-mini for text

        if any(keyword in (text or "").lower() for keyword in image_generation_keywords):
            initial_tags.append("ImageGen")
        if audio_files:
            initial_tags.append("AudioTranscribe")
        if image_urls and not any(keyword in (text or "").lower() for keyword in image_generation_keywords):
            initial_tags.append("Vision")

        return initial_tags

    def format_tags_display(self, tags: List[str]) -> str:
        """Format tags as: `⛭ modelo` `Vision` etc. (modelo: gpt-4.1-mini/gpt-4o/o3-mini)"""
        return " ".join([f"`⛭ {tag}`" if i == 0 else f"`{tag}`" for i, tag in enumerate(tags)])

    async def create_stream_callback(self, app_client, original_channel_id: str, message_ts: str, 
                                   header_prefix: str, audio_files: Optional[List], 
                                   image_urls: Optional[List], user_message: str, 
                                   model_name: str) -> Callable:
        """Create a stream callback function for updating Slack messages."""
        current_text_only = ""
        sent_header = False
        last_update_length = 0
        detected_tools = []
        current_header_prefix = header_prefix
        last_update_time = time.time()
        update_count = 0
        
        # Initialize circuit breaker
        self.stream_start_time = time.time()

        async def stream_callback(delta_text: str, full_text: str, tool_calls_detected=None):
            nonlocal current_text_only, last_update_length, last_update_time, sent_header, detected_tools, current_header_prefix, update_count

            # Circuit breaker: Check for infinite loop conditions
            current_time = time.time()
            stream_duration = current_time - self.stream_start_time
            update_count += 1

            # Protection against infinite loops
            if stream_duration > self.max_stream_duration:
                logger.error(f"🚨 CIRCUIT BREAKER: Stream timeout after {stream_duration:.1f}s - stopping to prevent infinite loop")
                return

            if len(full_text) > self.max_response_length:
                logger.error(f"🚨 CIRCUIT BREAKER: Response too long ({len(full_text)} chars) - stopping to prevent infinite loop")
                return

            if update_count > self.max_updates:
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
                cumulative_tags = self.derive_cumulative_tags(detected_tools, audio_files, image_urls, user_message=user_message, final_response=full_text, model_name=model_name)
                # Format as: `⛭ {model_name}` `Vision` `WebSearch`
                tag_display = self.format_tags_display(cumulative_tags)
                current_header_prefix = f"{tag_display}\n\n"

            should_update = (
                len(current_text_only) - last_update_length >= 10 or
                current_time - last_update_time >= 0.5 or
                not delta_text
            )

            if not sent_header:
                # Replace thinking message with header before first chunk
                try:
                    await app_client.chat_update(
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
                    from slack_formatter import format_message_for_slack
                    formatted_text = current_header_prefix + format_message_for_slack(current_text_only)
                    await app_client.chat_update(
                        channel=original_channel_id,
                        ts=message_ts,
                        text=formatted_text
                    )
                    last_update_length = len(current_text_only)
                    last_update_time = current_time
                except Exception as update_error:
                    logger.warning(f"Failed to update streaming message: {update_error}")

        return stream_callback
