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
    Uses gpt-4o for vision processing and gpt-4.1-mini for text-only processing.

    Args:
        agent: The OpenAI Agent instance
        message: User message to process
        image_urls: Optional list of image URLs for vision processing
        stream_callback: Optional callback for streaming updates

    Returns:
        Dict: {"text": ..., "tools": [...], "token_usage": {...}}
    """
    logger.info(f"Processing message: {message[:100]}{'...' if len(message) > 100 else ''}")
    
    # Create vision-capable agent if images are present
    if image_urls:
        logger.info(f"Processing {len(image_urls)} image(s) with gpt-4o")
        # Create a new agent instance with gpt-4o for vision processing
        vision_agent = Agent(
            name=agent.name,
            model="gpt-4o",  # Use gpt-4o for vision processing
            tools=agent.tools,
            mcp_servers=agent.mcp_servers,
            instructions=agent.instructions
        )
        agent = vision_agent
    else:
        logger.info("Processing text-only message with gpt-4.1-mini")

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
        model_used = agent.model
        logger.info(f"🤖 AGENT PROCESSING - Model: {model_used}")
        logger.info(f"📝 Message: {message[:100]}{'...' if len(message) > 100 else ''}")
        
        # Prepare input for the agent
        if image_urls:
            logger.info(f"🖼️ Processing {len(image_urls)} images with {model_used}")
            for i, url in enumerate(image_urls):
                logger.info(f"   Image {i+1}: {url[:80]}{'...' if len(url) > 80 else ''}")
            
            # For vision processing, use the correct OpenAI Agents SDK format
            # Based on web search results, the format should use input_text and input_image
            content_items = [{"type": "input_text", "text": message}]
            for image_url in image_urls:
                content_items.append({
                    "type": "input_image",
                    "image_url": image_url,
                    "detail": "low"
                })
            
            agent_input = [{
                "role": "user",
                "content": content_items
            }]
            logger.info(f"🔍 Vision input prepared: message + {len(image_urls)} images")
        else:
            agent_input = message
            logger.info(f"💬 Text-only input prepared as string")

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

        # Log final response details
        final_text = full_response or str(result.final_output) if result.final_output else "No response generated."
        logger.info(f"✅ RESPONSE COMPLETE - Model: {agent.model}")
        logger.info(f"📤 Response length: {len(final_text)} chars")
        logger.info(f"🔧 Tools used: {len(tool_calls)} ({[t.get('tool_name', 'unknown') for t in tool_calls]})")
        logger.info(f"💬 Response preview: {final_text[:150]}{'...' if len(final_text) > 150 else ''}")
        
        return {
            "text": final_text,
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
