"""
Livia Slack Chatbot Agent - OpenAI Agents SDK Primary Architecture
Uses HostedMCPTool for all Zapier MCPs - no more hybrid architecture!
"""

import os
import logging
import re
import sys
from typing import Optional, List
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Agents SDK components
from agents import Agent, Runner, gen_trace_id, trace, WebSearchTool, ItemHelpers, FileSearchTool, HostedMCPTool
from agents import enable_verbose_stdout_logging, set_tracing_export_api_key

# Local imports
from tools.mcp.zapier_mcps import ZAPIER_MCPS

# Configure advanced logging and debugging
def setup_advanced_logging():
    """Configure comprehensive logging for debugging MCP issues"""

    # Enable verbose OpenAI Agents SDK logging
    enable_verbose_stdout_logging()

    # Configure Python logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('livia_debug.log', mode='a')
        ]
    )

    # Set specific loggers
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # OpenAI SDK logging
    openai_logger = logging.getLogger("openai")
    openai_logger.setLevel(logging.DEBUG)

    # Agents SDK logging
    agents_logger = logging.getLogger("agents")
    agents_logger.setLevel(logging.DEBUG)

    # Configure tracing if API key is available
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            set_tracing_export_api_key(openai_api_key)
            logger.info("✅ OpenAI tracing configured")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure tracing: {e}")

    logger.info("🔧 Advanced logging and debugging configured")
    return logger

# Initialize logging
logger = setup_advanced_logging()


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Return the number of tokens for a given text and model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def debug_mcp_config(mcp_key: str, mcp_config: dict) -> dict:
    """Debug MCP configuration and return status info"""
    debug_info = {
        "mcp_key": mcp_key,
        "name": mcp_config.get("name", "Unknown"),
        "server_label": mcp_config.get("server_label", "Unknown"),
        "url": mcp_config.get("url", "Unknown"),
        "has_api_key": bool(mcp_config.get("api_key", "").strip()),
        "api_key_length": len(mcp_config.get("api_key", "").strip()) if mcp_config.get("api_key") else 0,
        "status": "unknown"
    }

    logger.debug(f"🔍 Debug MCP {mcp_key}: {debug_info}")
    return debug_info


def test_mcp_connectivity(server_url: str, headers: dict) -> dict:
    """Test basic connectivity to MCP server"""
    import requests

    test_result = {
        "url": server_url,
        "reachable": False,
        "status_code": None,
        "error": None,
        "response_time": None
    }

    try:
        import time
        start_time = time.time()

        # Test basic connectivity (not full MCP protocol)
        response = requests.get(server_url, headers=headers, timeout=10)
        test_result["status_code"] = response.status_code
        test_result["response_time"] = time.time() - start_time
        test_result["reachable"] = True

        logger.debug(f"🌐 Connectivity test for {server_url}: {test_result}")

    except Exception as e:
        test_result["error"] = str(e)
        logger.debug(f"❌ Connectivity test failed for {server_url}: {e}")

    return test_result

def create_agent() -> Agent:
    """
    Create and configure the Livia agent with OpenAI Agents SDK as PRIMARY architecture.
    All MCPs now use HostedMCPTool - unified approach!
    """
    
    # 🔧 CORE TOOLS - Web Search and File Search
    web_search_tool = WebSearchTool()
    
    # File Search Tool with vector store
    vector_store_id = os.getenv("VECTOR_STORE_ID", "vs_683e3a1ac4808191ae5e6fe24392e609")
    file_search_tool = FileSearchTool(
        vector_store_ids=[vector_store_id],
        max_num_results=5,
        include_search_results=True
    )
    
    # 🚀 ZAPIER MCPs VIA AGENTS SDK - HostedMCPTool approach with advanced debugging
    logger.info("🔧 Starting MCP configuration with advanced debugging...")

    zapier_tools = []
    zapier_tools_description = "\n- MCP Tools available:\n"
    mcp_debug_results = []

    # Smart fallback: Only enable MCPs that are working (Status 405 = OK, Status 500 = Skip)
    working_mcps = ["google_drive", "mcpEverhour", "mcpGoogleDocs"]  # Status 405 - Working
    skip_mcps = [k for k in ZAPIER_MCPS.keys() if k not in working_mcps]  # Status 500 - Skip
    logger.info(f"🎯 Smart fallback enabled - Using only working MCPs")
    logger.info(f"✅ Working MCPs: {working_mcps}")
    logger.info(f"⚠️ Skipping problematic MCPs: {skip_mcps}")

    for mcp_key, mcp_config in ZAPIER_MCPS.items():
        # Debug each MCP configuration
        debug_info = debug_mcp_config(mcp_key, mcp_config)
        mcp_debug_results.append(debug_info)

        if mcp_key in skip_mcps:
            logger.warning(f"⚠️ Skipping {mcp_config['name']} - in skip list for testing")
            debug_info["status"] = "skipped"
            continue

        try:
            # Test connectivity first
            server_url = mcp_config["url"]
            headers = {"Authorization": f"Bearer {mcp_config['api_key'].strip()}"}

            connectivity_test = test_mcp_connectivity(server_url, headers)
            debug_info["connectivity"] = connectivity_test

            # URLs are now correctly formatted for HostedMCPTool (v0 API)
            logger.debug(f"🔗 Using URL for {mcp_key}: {server_url}")

            logger.info(f"🔧 Creating HostedMCPTool for {mcp_config['name']}...")

            hosted_mcp = HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": mcp_config["server_label"],
                    "server_url": server_url,
                    "headers": headers,
                    "require_approval": "never"
                    # Removed cache_tools_list - not supported in current API
                }
            )

            zapier_tools.append(hosted_mcp)
            zapier_tools_description += f"  * {mcp_config['name']}: {mcp_config['description']}\n"
            debug_info["status"] = "created"
            logger.info(f"✅ Successfully created HostedMCPTool for {mcp_config['name']}")

        except Exception as e:
            debug_info["status"] = "failed"
            debug_info["error"] = str(e)
            logger.error(f"❌ Failed to create HostedMCPTool for {mcp_config['name']}: {e}")

    # Log summary of MCP configuration
    logger.info(f"📊 MCP Configuration Summary:")
    logger.info(f"   - Total MCPs configured: {len(ZAPIER_MCPS)}")
    logger.info(f"   - MCPs successfully created: {len(zapier_tools)}")
    logger.info(f"   - MCPs skipped: {len(skip_mcps)}")
    logger.info(f"   - MCPs failed: {len([r for r in mcp_debug_results if r.get('status') == 'failed'])}")

    logger.info(f"🚀 Using OpenAI Agents SDK as PRIMARY architecture with {len(zapier_tools)} Zapier MCPs via HostedMCPTool")
    logger.info("✨ All MCPs now use Agents SDK - no more hybrid architecture!")

    # Combine all tools: built-in tools + Zapier HostedMCPTools
    all_tools = [web_search_tool, file_search_tool] + zapier_tools
    
    agent = Agent(
        name="Livia",
        instructions=(
            """<identity>
You are Livia, an intelligent chatbot assistant working at ℓiⱴε, a Brazilian advertising agency. You operate in Slack channels, groups, and DMs and your Slack ID is <@U057233T98A>.
</identity>

<communication_style>
- BE EXTREMELY CONCISE AND BRIEF - this is your primary directive
- Default to short, direct answers unless explicitly asked for details
- One sentence responses are preferred for simple questions
- Avoid unnecessary explanations, steps, or elaborations
- Always respond in the same language the user communicates with you
- Use Slack formatting: *bold*, _italic_, ~strikethrough~
- Your Slack ID: <@U057233T98A>
- Only mention File Search or file names when explicitly asked about documents
- Feel free to disagree constructively to improve results
</communication_style>

<available_tools>
- Web Search Tool: Search internet for current information
- File Search Tool: Search uploaded documents in knowledge base
- Image Vision: Analyze uploaded images or URLs - you have FULL vision capabilities
- Image Generation Tool: Create images using gpt-image-1 model
""" + f"{zapier_tools_description}" + """
<mcp_usage_rules>
1. Sequential Search Strategy: workspace → project → task
2. Always include ALL IDs/numbers from API responses
3. Use exact IDs when available in conversation history
4. Make multiple MCP calls as needed to complete tasks
5. Limit results to maximum 4 items per search
</mcp_usage_rules>

<search_strategy>
CRITICAL: Use intelligent search strategy to avoid unnecessary tool calls:

IF info is static/historical (e.g., coding principles, scientific facts, brand colors, company info)
→ ANSWER DIRECTLY without tools (info rarely changes)

ELSE IF info changes annually/slowly (e.g., rankings, statistics, yearly trends)
→ ANSWER DIRECTLY but offer to search for latest updates

ELSE IF info changes frequently (e.g., weather, news, stock prices, current events)
→ USE WEB SEARCH immediately for accurate current information

ELSE IF user asks about documents/files
→ USE FILE SEARCH to find relevant documents in knowledge base
</search_strategy>

<response_guidelines>
- NEVER answer with uncertainty - if unsure, USE AVAILABLE TOOLS for verification
- Use web search for current/changing information only
- Use file search when users ask about documents
- Provide detailed image analysis when images are shared - you CAN see and analyze images perfectly
- NEVER say you cannot see images - you have full vision capabilities and should analyze them directly
- Try multiple search strategies if initial attempts fail
- Suggest alternative search terms when no results found
- Handle 'TargetGroup' searches as 'TargetGroupIndex_BR2024'
- Correct 'pasta' to 'arquivo' when appropriate
- Cite sources for web searches
- Mention document names for file searches
- Be professional and helpful
- Ask for clarification when needed
- NEVER use slack_post_message - responses handled automatically
- NEVER send messages to other channels
</response_guidelines>
"""
        ),
        model="gpt-4.1",
        tools=all_tools  # All tools including Zapier MCPs via HostedMCPTool
    )
    
    tools_info = f"WebSearchTool, FileSearchTool, and {len(zapier_tools)} Zapier MCPs via HostedMCPTool"
    logger.info(f"Agent '{agent.name}' created with {tools_info}.")
    return agent


async def process_message(agent: Agent, message: str, image_urls: Optional[List[str]] = None, stream_callback=None) -> dict:
    """
    Runs the agent with the given message and optional image URLs with streaming support.
    Now uses unified Agents SDK with native multi-turn execution for all MCPs.

    Args:
        agent: OpenAI Agent instance
        message: User message to process
        image_urls: Optional list of image URLs
        stream_callback: Optional callback for streaming updates

    Returns:
        Dict with 'text', 'tools', and optionally 'structured_data'
    """

    # 🚀 All MCPs now handled by Agents SDK with HostedMCPTool - no routing needed!

    # Generate a trace ID for monitoring the agent's execution flow
    trace_id = gen_trace_id()
    logger.info(f"Starting agent run for message: '{message}' with STREAMING. Trace: https://platform.openai.com/traces/{trace_id}")

    if image_urls:
        logger.info(f"Processing {len(image_urls)} image(s): {image_urls}")

    final_output = "Sorry, I couldn't process that." # Default response
    tool_calls_made = []
    try:
        # Start tracing for the agent workflow
        with trace(workflow_name="Livia Slack Agent Workflow", trace_id=trace_id):
            # Prepare input with images if provided (format for OpenAI Agents SDK)
            if image_urls:
                # Create input with both text and images for vision processing
                input_content = [
                    {"type": "input_text", "text": message}
                ]

                # Add each image to the input
                for image_url in image_urls:
                    input_content.append({
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "low"  # Use low detail for cost efficiency
                    })

                input_data = [{
                    "role": "user",
                    "content": input_content
                }]
                logger.info(f"Prepared vision input with {len(image_urls)} images")
            else:
                # Text-only input
                input_data = message

            result = Runner.run_streamed(starting_agent=agent, input=input_data)

            full_response = ""
            final_message_output = ""

            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    if hasattr(event.data, 'type') and event.data.type == "response.output_text.delta":
                        delta_text = getattr(event.data, 'delta', '')
                        if delta_text:
                            full_response += delta_text
                            if stream_callback:
                                await stream_callback(delta_text, full_response)
                    elif hasattr(event.data, 'type') and event.data.type == "response.completed":
                        logger.info("Agent streaming response completed")
                elif event.type == "run_item_stream_event":
                    if event.item.type == "tool_call_item":
                        # Extract tool information for tracking
                        tool_name = getattr(event.item, 'name', '')
                        
                        # Try extracting from .tool attribute if present
                        tool_obj = getattr(event.item, 'tool', None)
                        if tool_obj and not tool_name:
                            tool_name = getattr(tool_obj, 'name', '') or getattr(tool_obj, 'type', '')

                        # Enhanced detection for web search
                        if not tool_name:
                            response_content = full_response.lower()
                            web_indicators = [
                                "brandcolorcode.com", "wikipedia.org", "google.com", "bing.com",
                                "utm_source=openai", "search result", "according to", "source:",
                                "based on search", "found on", "website", ".com", ".org", ".net"
                            ]
                            if any(indicator in response_content for indicator in web_indicators):
                                tool_name = "web_search"

                        tool_call_info = {
                            "type": getattr(event.item, 'type', ''),
                            "tool_name": tool_name or '',
                            "arguments": getattr(event.item, 'arguments', {}),
                            "output": getattr(event.item, 'output', None),
                            "error": getattr(event.item, 'error', None)
                        }
                        
                        tool_calls_made.append(tool_call_info)
                        logger.info(f"-- Tool was called during streaming: {tool_call_info}")
                        
                        # Notify stream callback about tool detection
                        if stream_callback:
                            await stream_callback("", full_response, tool_calls_detected=[tool_call_info])
                    elif event.item.type == "tool_call_output_item":
                        logger.info(f"-- Tool output during streaming: {event.item.output}")
                    elif event.item.type == "message_output_item":
                        message_text = ItemHelpers.text_message_output(event.item)
                        if message_text:
                            final_message_output = message_text
                            if message_text != full_response:
                                full_response = message_text
                                if stream_callback:
                                    await stream_callback("", full_response)
                        logger.info(f"-- Message output during streaming: {message_text}")

            final_output = final_message_output or full_response or "No response generated."

            logger.info(f"Agent streaming run completed. Final output: '{final_output}'")

    except Exception as e:
        logger.error(f"Error during agent streaming run (trace_id: {trace_id}): {e}", exc_info=True)
        final_output = f"An error occurred while processing your request: {str(e)}"

    # Calculate token usage
    input_tokens = count_tokens(str(message), agent.model)
    output_tokens = count_tokens(str(final_output), agent.model)
    token_usage = {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens,
    }

    return {"text": final_output, "tools": tool_calls_made, "token_usage": token_usage}
