#!/usr/bin/env python3
"""
Ferramenta de Busca Web para o Chatbot Livia no Slack
-----------------------------------------------------
Fornece capacidades de busca web usando o WebSearchTool do OpenAI Agents SDK.
"""

import logging
from agents import WebSearchTool as OpenAIWebSearchTool

logger = logging.getLogger(__name__)


class WebSearchTool:
    """# Wrapper da ferramenta de busca web para o chatbot Livia."""

    def __init__(self, search_context_size: str = "medium"):
        self.tool = OpenAIWebSearchTool(search_context_size=search_context_size)
        logger.info(f"WebSearchTool inicializada com tamanho de contexto: {search_context_size}")
        return self.tool
