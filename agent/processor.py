#!/usr/bin/env python3
"""
Livia Agent Message Processor
-----------------------------
Processamento principal de mensagens do agente Livia.
Inclui roteamento para MCPs e execução unificada.
"""

import logging
import re
from typing import Optional, List
from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

from .config import ZAPIER_MCPS
from .mcp_processor import (
    detect_zapier_mcp_needed,
    process_message_with_enhanced_multiturn_mcp,
    process_message_with_structured_output
)
from .mcp_streaming import process_message_with_zapier_mcp_streaming

logger = logging.getLogger(__name__)


async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> dict:
    """
    Runs the agent with the given message and optional image URLs with streaming support.
    Now uses unified Agents SDK with native multi-turn execution for all MCPs.

    Args:
        agent: The OpenAI Agent instance
        message: User message to process
        image_urls: Optional list of image URLs for vision processing
        stream_callback: Optional callback for streaming updates

    Returns:
        Dict: {"text": ..., "tools": [...], "token_usage": {...}}
    """
    logger.info(f"Processing message: {message[:100]}{'...' if len(message) > 100 else ''}")
    
    if image_urls:
        logger.info(f"Processing {len(image_urls)} image(s)")

    # Check if a Zapier MCP is needed based on keywords
    mcp_key = detect_zapier_mcp_needed(message)
    
    if mcp_key:
        logger.info(f"Detected MCP needed: {mcp_key}")
        
        # Use enhanced multi-turn execution for better workflow handling
        try:
            return await process_message_with_enhanced_multiturn_mcp(
                mcp_key, message, image_urls, stream_callback
            )
        except Exception as e:
            logger.error(f"Enhanced multi-turn MCP failed: {e}")
            # Fallback to regular MCP processing
            try:
                return await process_message_with_zapier_mcp_streaming(
                    mcp_key, message, image_urls, stream_callback
                )
            except Exception as e2:
                logger.error(f"Regular MCP processing also failed: {e2}")
                # Continue with native Agents SDK processing
                logger.info("Falling back to native Agents SDK processing")

    # Use native Agents SDK with streaming
    try:
        logger.info("Using native Agents SDK with streaming")
        
        # Prepare input for the agent
        if image_urls:
            # For vision processing, include images in the input
            input_content = [{"type": "text", "text": message}]
            for image_url in image_urls:
                input_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url, "detail": "low"}
                })
            agent_input = input_content
        else:
            agent_input = message

        # Create dummy callback if none provided (always use streaming internally)
        if not stream_callback:
            async def dummy_callback(delta_text: str, full_text: str, tool_calls_detected=None):
                pass
            stream_callback = dummy_callback

        # Always use streaming execution with OpenAI Agents SDK API
        full_response = ""
        tool_calls = []

        # Use run_streamed() which returns RunResultStreaming
        result = Runner.run_streamed(agent, agent_input)

        async for event in result.stream_events():
            if event.type == "raw_response_event":
                # Handle raw streaming events (token by token)
                if isinstance(event.data, ResponseTextDeltaEvent) and event.data.delta:
                    delta_text = event.data.delta
                    full_response += delta_text
                    await stream_callback(delta_text, full_response, tool_calls)
                elif hasattr(event.data, 'delta') and event.data.delta:
                    # Fallback for other delta events
                    delta_text = event.data.delta
                    full_response += delta_text
                    await stream_callback(delta_text, full_response, tool_calls)
            elif event.type == "run_item_stream_event":
                # Handle higher-level events (tool calls, messages, etc)
                if event.item.type == "tool_call_item":
                    tool_info = {
                        "tool_name": getattr(event.item, 'name', 'unknown'),
                        "arguments": getattr(event.item, 'arguments', {}),
                        "type": "tool_call_started"
                    }
                    tool_calls.append(tool_info)
                    await stream_callback("", full_response, tool_calls)
                elif event.item.type == "tool_call_output_item":
                    # Update the last tool call with completion info
                    if tool_calls:
                        tool_calls[-1].update({
                            "output": getattr(event.item, 'output', None),
                            "type": "tool_call_completed"
                        })

        # After streaming is complete, access final data directly from RunResultStreaming
        # The final_output and other properties are available directly on the result object

        return {
            "text": full_response or str(result.final_output) if result.final_output else "No response generated.",
            "tools": tool_calls,
            "token_usage": {"input": 0, "output": 0, "total": 0}  # Token usage not directly available in streaming mode
        }
            
    except Exception as e:
        logger.error(f"Native Agents SDK processing failed: {e}", exc_info=True)
        
        # Final fallback - return error message
        return {
            "text": f"Erro no processamento da mensagem: {str(e)}",
            "tools": [],
            "token_usage": {"input": 0, "output": 0, "total": 0}
        }


def extract_tool_calls_from_response(response_text: str) -> List[dict]:
    """
    Extract tool call information from response text for logging purposes.
    
    Args:
        response_text: The response text to analyze
        
    Returns:
        List of tool call dictionaries
    """
    tool_calls = []
    
    # Look for common tool indicators in the response
    if "web search" in response_text.lower() or "search" in response_text.lower():
        tool_calls.append({"tool_name": "web_search", "type": "inferred"})
    
    if "file search" in response_text.lower() or "document" in response_text.lower():
        tool_calls.append({"tool_name": "file_search", "type": "inferred"})
    
    if "image" in response_text.lower() and ("generat" in response_text.lower() or "creat" in response_text.lower()):
        tool_calls.append({"tool_name": "image_generation", "type": "inferred"})
    
    # Look for MCP indicators
    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        for keyword in mcp_config.get('keywords', []):
            if keyword in response_text.lower():
                tool_calls.append({"tool_name": f"mcp_{mcp_key}", "type": "inferred"})
                break
    
    return tool_calls
