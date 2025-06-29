# Livia Chatbot Project

## Core Setup
- OpenAI Agents SDK + Slack Bolt integration
- Responds only when mentioned in thread first message
- User wants to restrict Slack chatbot communication to only channel C059NNLU3E1 during development phase for security.
- Uses shortcuts with + prefix (not slash commands)

## Key Preferences
- Organize tools/MCPs in separate files/folders
- Use gpt-image-1 for image generation e edit image.
- Always use OpenAI Agents SDK and stream text responses.
- Concise responses, minimal emojis, XML-tagged prompts in agents instructions.
- Error format: `Erro: xxx. Se persistir entre em contato com: <@U046LTU4TT5>`
- Context limit message: `Você chegou no limite de memória, comece uma nova conversa` (This message should be sent as a new message in the thread after the message that hit the context limit for that conversation)
- Display real user names (not Slack IDs) using Slack API for Livia agent.
- Use structured outputs for agent communication when optimal to maintain output accuracy
- User prefers +think keyword to trigger Block Kit input modal for isolated o3 model processing without conversation past context, then return to normal model with full context including o3 response.

## Technical Features
- Real-time text streaming with rate limiting
- Audio transcription (OpenAI Agents API)
- Markdown-to-Slack formatting with hyperlinks
- File Search Tool with vector_store_ids
- Image generation via ImageGenerationTool
- Structured outputs with JSON Schema
- MCP tool caching with cache_tools_list=True
- CodeInterpreterTool with proper configuration
- ++

## MCP Servers
- Zapier integrations: Everhour, Asana, Gmail, GoogleCalendar, Slack.
- Gmail supports search operators (from:, subject:)

## Tool Tags
- Format: `⛭ WebSearch`, `⛭ ImageGeneration`, etc.
- Use specific tags for WebSearch, ImageGeneration, Voice, MCP tools