#!/usr/bin/env python3
"""
Image Vision Processing for Livia Slack Chatbot
-----------------------------------------------
Handles image processing, URL extraction, and Slack image authentication.
"""

import os
import logging
import re
import base64
import aiohttp
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image processing and vision capabilities."""
    
    @staticmethod
    def extract_image_urls(event: Dict[str, Any]) -> List[str]:
        """Extract image URLs from Slack event."""
        image_urls = []

        # Check for file uploads
        files = event.get("files", [])
        for file in files:
            if file.get("mimetype", "").startswith("image/"):
                # For Slack uploaded images, we need to use the URL with auth headers
                if "url_private" in file:
                    slack_image_url = f"{file['url_private']}?token={os.environ.get('SLACK_BOT_TOKEN', '')}"
                    image_urls.append(slack_image_url)
                    logger.info(f"Found uploaded image: {file.get('name', 'unknown')} - {file['url_private']}")

        # Check for image URLs in text (enhanced URL detection)
        text = event.get("text", "")

        url_patterns = [
            r'https?://[^\s<>]+\.(?:jpg|jpeg|png|gif|webp|bmp|tiff)(?:\?[^\s<>]*)?',
            r'https?://[^\s<>]*(?:imgur|flickr|instagram|twitter|facebook)[^\s<>]*',
            r'https?://[^\s<>]*\.(?:com|org|net)/[^\s<>]*\.(?:jpg|jpeg|png|gif|webp)',
        ]

        for pattern in url_patterns:
            found_urls = re.findall(pattern, text, re.IGNORECASE)
            for url in found_urls:
                url = re.sub(r'[.,;!?]+$', '', url)
                if url not in image_urls:
                    image_urls.append(url)
                    logger.info(f"Found image URL in text: {url}")

        if image_urls:
            logger.info(f"Total images found: {len(image_urls)}")

        return image_urls

    @staticmethod
    async def process_slack_image(image_url: str) -> Optional[str]:
        """Process Slack private image URL to make it accessible."""
        try:
            if "files.slack.com" in image_url:
                headers = {
                    "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN', '')}"
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url, headers=headers) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            base64_image = base64.b64encode(image_data).decode('utf-8')
                            return f"data:{content_type};base64,{base64_image}"
                        else:
                            logger.error(f"Failed to download Slack image: {response.status}")
                            return None
            else:
                return image_url

        except Exception as e:
            logger.error(f"Error processing image URL {image_url}: {e}")
            return None

    @staticmethod
    async def process_image_urls(image_urls: List[str]) -> List[str]:
        """Process a list of image URLs and return processed URLs."""
        processed_urls = []
        
        for img_url in image_urls:
            processed_url = await ImageProcessor.process_slack_image(img_url)
            if processed_url:
                processed_urls.append(processed_url)
        
        logger.info(f"Successfully processed {len(processed_urls)} out of {len(image_urls)} images")
        return processed_urls
