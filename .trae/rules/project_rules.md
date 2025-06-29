
# Project Context
- User is working on a Livia chatbot project integrating OpenAI Agents SDK with Slack, repository at https://github.com/lucastzuka/liviaNew3.git
- The project uses OpenAI Agents SDK for local MCPs with keyword-based routing, but user wants to explore using only OpenAI Agents SDK for both local and remote MCPs (including Zapier).
- User wants to implement Slack API integration using Bolt for Python with Socket Mode, responding only when mentioned in first message of threads.
- User wants to restrict Slack chatbot communication to only channel C059NNLU3E1 during development phase for security.
- User decided to abandon slash commands (like /pensar) because Slack API doesn't support slash commands in threads, switching to shortcuts named with +.

# User Preferences
- Prefers organizing code by separating tools and MCPs into dedicated files/folders.    
- Prefers minimal logging for cleaner debugging
- Prefers image generation with gpt-image-1 over DALL-E with progress updates
- Prefers prioritizing OpenAI Agents SDK over other approaches, always using streaming for text messages
- Prefers concise/direct responses with dynamic brevity, minimal emojis in instructions, XML-tagged for organizing prompts.
- Prefers fixed error messages: 'Erro: xxx. Se persistir entre em contato com: <@U046LTU4TT5>'
- Envie uma mensagem nova depois da ultima msg na mesma thread falando 'Você chegou no limite de memória, comece uma nova conversa' quando chegar no limite de contexto daquele chat.
- User prefers removing all emojis from system prompts and agent instructions as they can interfere with agent performance.
- User prefers chatbot to display real user names instead of Slack IDs, suggests using Slack API to fetch user info (name/email) and map to IDs so the AI model sees human names rather than technical IDs.
- User prefers refactoring duplicate logic to reduce redundancy, if necessary suggesting it could be removed for simplification.
- User prefers using structured outputs in parts of the system communicating of agents to make responses more precise and reliable.
- User prefers +think keyword to trigger Block Kit input modal for isolated o3 model processing without conversation past context, then return to normal model with full context including o3 response.
- User wants o3 thinking mode to use specific system instructions.
- User prefers that error messages from the thinking interface (+think) should appear in terminal output for debugging access, not just in Slack.
- User prefers chunked o3 thinking responses without 'Continuação X:' headers for cleaner output that can be easily copied.

# Technical Implementations
- Successfully implemented real-time streaming responses with intelligent rate limiting and progressive message updates
- Audio transcription implemented using OpenAI Agents API, supporting multiple formats up to 25MB
- Implemented complete Slack formatting system: markdown-to-slack conversion, intelligent hyperlinks
- File Search Tool implemented using OpenAI FileSearchTool with vector_store_ids parameters
- Image generation implemented using OpenAI Agents SDK ImageGenerationTool.
- OpenAI Structured Outputs feature ensures responses adhere to JSON Schema with text_format parameter
- OpenAI Agents SDK supports native multi-turn execution with Runner.run_sync/run_streamed
- OpenAI Agents SDK supports MCP tool caching with cache_tools_list=True parameter
- OpenAI Agents SDK 0.0.17 moved MCP server classes to agents.mcp.server module
- OpenAI Agents SDK CodeInterpreterTool has a name property that returns 'code_interpreter' and requires tool_config with CodeInterpreter configuration
- OpenAI Agents SDK uses MCPServerStdio/MCPServerSse/MCPServerStreamableHttp classes for MCP servers, agents use mcp_servers parameter with these server classes. HostedMCPTool may be obsolete.
- MCPServerSseParams is a TypedDict that acts as a regular Python dict at runtime with keys: url (str), headers (dict, optional), timeout (float, optional), sse_read_timeout (float, optional) for creating MCPServerSse instances.
- OpenAI Agents SDK tool outputs always pass through the main agent before reaching the user - tools don't send responses directly, the Runner re-contextualizes tool outputs through the main agent model, and agent instructions like 'BE CONCISE' affect how the model processes tool responses.

# MCP Integrations
- User created multiple Zapier MCP servers: Everhour, Asana, Gmail, GoogleCalendar, Slack, GoogleDocs, GoogleSheets
- Gmail MCP supports search operators like 'from:sender' or 'subject:keyword' for filtering
- Everhour MCP should include all available commands in instructions and handle 'Hoje' (today) references by converting to current date/time in Brazil timezone for accurate timesheet operations.

# Tool Tagging and Issues
- Livia chatbot tags should be formatted with backticks around them like `⛭ WebSearch`
- Remove file_search tag from Livia chatbot since RAG always uses it
- Use specific tool tags for WebSearch, ImageGeneration, Voice, and individual MCP tools