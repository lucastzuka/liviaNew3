#!/usr/bin/env python3
"""
Web Search Tool for Livia Slack Chatbot
---------------------------------------
Provides web search capabilities using OpenAI Agents SDK WebSearchTool.
"""

import logging
from agents import WebSearchTool as OpenAIWebSearchTool

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Web search tool wrapper for Livia chatbot."""

    def __init__(self, search_context_size: str = "medium"):
        self.tool = OpenAIWebSearchTool(search_context_size=search_context_size)
        logger.info(f"WebSearchTool initialized with context size: {search_context_size}")

    def get_tool(self):
        return self.tool
