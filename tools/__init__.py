#!/usr/bin/env python3
"""
Tools module for Livia Slack Chatbot
------------------------------------
Exports all available tools for the chatbot.
"""

from .web_search import WebSearchTool
from .image_generation import ImageGenerationTool, image_generator

# Create a simple ImageProcessor class for compatibility
class ImageProcessor:
    """Simple image processor for Slack integration."""

    @staticmethod
    def extract_image_urls(event):
        """Extract image URLs from Slack event."""
        image_urls = []

        if "files" in event:
            for file in event["files"]:
                mimetype = file.get("mimetype", "")
                if mimetype.startswith("image/"):
                    image_urls.append(file.get("url_private", ""))

        return image_urls

    @staticmethod
    async def process_image_urls(image_urls):
        """Process image URLs for OpenAI vision."""
        return image_urls  # Return as-is for now

    @staticmethod
    async def process_slack_image(image_url):
        """Process Slack private image URL."""
        return image_url  # Return as-is for now

__all__ = ["WebSearchTool", "ImageProcessor", "ImageGenerationTool", "image_generator"]
