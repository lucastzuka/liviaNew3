#!/usr/bin/env python3
"""
Image Generation Tool for Livia Chatbot
---------------------------------------
Generates images using OpenAI's gpt-image-1 model through the Responses API.
Supports streaming with partial images and automatic Slack upload.
"""

import os
import base64
import tempfile
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageGenerationTool:
    """
    Tool for generating images using OpenAI's gpt-image-1 model.
    Integrates with Slack for automatic image upload and sharing.
    """
    
    def __init__(self):
        """Initialize the image generation tool."""
        self.model = "gpt-4.1-mini"  # Model that supports image generation tool
        self.supported_formats = ["png", "jpeg", "webp"]
        self.supported_sizes = ["1024x1024", "1536x1024", "1024x1536", "auto"]
        self.supported_qualities = ["low", "medium", "high", "auto"]
        
        logger.info("ImageGenerationTool initialized with gpt-image-1 support")
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "auto",
        quality: str = "auto",
        format: str = "png",
        compression: Optional[int] = None,
        transparent_background: bool = False,
        stream_callback=None
    ) -> Dict[str, Any]:
        """
        Generate an image from a text prompt using OpenAI's gpt-image-1.
        
        Args:
            prompt: Text description of the image to generate
            size: Image dimensions (1024x1024, 1536x1024, 1024x1536, auto)
            quality: Rendering quality (low, medium, high, auto)
            format: Output format (png, jpeg, webp)
            compression: Compression level for jpeg/webp (0-100)
            transparent_background: Whether to use transparent background
            stream_callback: Optional callback for streaming partial images
            
        Returns:
            Dict containing image data, metadata, and file path
        """
        from openai import OpenAI
        
        try:
            client = OpenAI()
            
            # Prepare image generation tool configuration
            tool_config = {
                "type": "image_generation",
                "size": size,
                "quality": quality,
                "background": "transparent" if transparent_background else "opaque"
            }

            # Note: format and compression are not supported in the tool config
            # They are handled by the model automatically
            
            # Remove partial images - we'll only use text streaming
            # if stream_callback:
            #     tool_config["partial_images"] = 2
            
            logger.info(f"Generating image with prompt: '{prompt[:100]}...'")
            logger.info(f"Settings: size={size}, quality={quality}, format={format}")
            
            # Generate image using Responses API
            if stream_callback:
                # Start with progress updates
                import asyncio

                await stream_callback("Iniciando geração da imagem...", 10)

                # Start the actual generation in background
                try:
                    await stream_callback("Processando com gpt-image-1...", 30)

                    # Generate the actual image (non-streaming)
                    response = client.responses.create(
                        model=self.model,
                        input=prompt,
                        tools=[tool_config]
                    )

                    await stream_callback("Finalizando imagem...", 80)

                    # Extract image data from response
                    image_data = [
                        output.result
                        for output in response.output
                        if output.type == "image_generation_call"
                    ]

                    if not image_data:
                        raise ValueError("No image data found in response")

                    image_base64 = image_data[0]

                    # Get revised prompt if available
                    revised_prompt = None
                    for output in response.output:
                        if output.type == "image_generation_call" and hasattr(output, 'revised_prompt'):
                            revised_prompt = output.revised_prompt
                            break

                    if not revised_prompt:
                        revised_prompt = prompt

                    # Capture usage information
                    usage_info = getattr(response, 'usage', None)
                    if usage_info:
                        self._log_usage_info(usage_info, prompt)

                    # Final callback with 100%
                    await stream_callback("Imagem gerada com sucesso!", 100)

                except Exception as e:
                    logger.error(f"Error during image generation: {e}")
                    await stream_callback("Erro na geração da imagem", 0)
                    raise
                
            else:
                # Non-streaming generation
                response = client.responses.create(
                    model=self.model,
                    input=prompt,
                    tools=[tool_config]
                )
                
                # Extract image data from response
                image_data = [
                    output.result
                    for output in response.output
                    if output.type == "image_generation_call"
                ]
                
                if not image_data:
                    raise ValueError("No image data found in response")
                
                image_base64 = image_data[0]
                
                # Get revised prompt if available
                revised_prompt = None
                for output in response.output:
                    if output.type == "image_generation_call" and hasattr(output, 'revised_prompt'):
                        revised_prompt = output.revised_prompt
                        break

                if not revised_prompt:
                    revised_prompt = prompt

                # Capture usage information
                usage_info = getattr(response, 'usage', None)
                if usage_info:
                    self._log_usage_info(usage_info, prompt)
            
            # Save final image
            image_path = await self._save_temp_image(image_base64, "generated", format)
            
            # Get image metadata
            image_size = os.path.getsize(image_path)
            
            result = {
                "success": True,
                "image_path": image_path,
                "image_base64": image_base64,
                "original_prompt": prompt,
                "revised_prompt": revised_prompt,
                "format": format,
                "size": size,
                "quality": quality,
                "file_size": image_size,
                "model": "gpt-image-1"
            }
            
            logger.info(f"Image generated successfully: {image_path} ({image_size} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Error generating image: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "original_prompt": prompt
            }
    
    async def _save_temp_image(self, image_base64: str, prefix: str, format: str) -> str:
        """Save base64 image data to a temporary file."""
        try:
            # Decode base64 image data
            image_bytes = base64.b64decode(image_base64)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f".{format}", 
                prefix=f"livia_{prefix}_"
            ) as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name
            
            logger.debug(f"Image saved to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error saving temporary image: {e}")
            raise
    
    def _log_usage_info(self, usage_info, prompt: str) -> None:
        """Log detailed usage information and cost calculation."""
        try:
            # Extract usage data
            input_tokens = getattr(usage_info, 'input_tokens', 0)
            output_tokens = getattr(usage_info, 'output_tokens', 0)
            total_tokens = getattr(usage_info, 'total_tokens', input_tokens + output_tokens)

            # Image token pricing (as of 2024 - check OpenAI pricing for current rates)
            # These are approximate rates - check OpenAI pricing page for exact values
            input_token_cost = 0.00001  # $0.01 per 1K tokens (example)
            output_image_token_cost = 0.00004  # $0.04 per 1K tokens (example)

            # Calculate costs
            input_cost = (input_tokens / 1000) * input_token_cost
            output_cost = (output_tokens / 1000) * output_image_token_cost
            total_cost = input_cost + output_cost

            # Log detailed information with high visibility
            print("\n" + "=" * 70)
            print("🎨 IMAGE GENERATION USAGE & COST REPORT")
            print("=" * 70)
            print(f"📝 Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
            print(f"🔤 Input Tokens: {input_tokens:,}")
            print(f"🖼️  Output Image Tokens: {output_tokens:,}")
            print(f"📊 Total Tokens: {total_tokens:,}")
            print(f"💰 Input Cost: ${input_cost:.6f}")
            print(f"💰 Output Cost: ${output_cost:.6f}")
            print(f"💰 TOTAL COST: ${total_cost:.6f}")
            print("=" * 70 + "\n")

            # Also log to logger for file logging
            logger.info("=" * 60)
            logger.info("🎨 IMAGE GENERATION USAGE & COST REPORT")
            logger.info("=" * 60)
            logger.info(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            logger.info(f"🔤 Input Tokens: {input_tokens:,}")
            logger.info(f"🖼️  Output Image Tokens: {output_tokens:,}")
            logger.info(f"📊 Total Tokens: {total_tokens:,}")
            logger.info(f"💰 Input Cost: ${input_cost:.6f}")
            logger.info(f"💰 Output Cost: ${output_cost:.6f}")
            logger.info(f"💰 TOTAL COST: ${total_cost:.6f}")
            logger.info("=" * 60)

        except Exception as e:
            logger.warning(f"Failed to log usage info: {e}")
            print(f"⚠️  Failed to log usage info: {e}")

    def cleanup_temp_file(self, file_path: str) -> None:
        """Clean up temporary image file."""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")
    
    def get_generation_info(self) -> Dict[str, Any]:
        """Get information about image generation capabilities."""
        return {
            "model": "gpt-image-1",
            "supported_formats": self.supported_formats,
            "supported_sizes": self.supported_sizes,
            "supported_qualities": self.supported_qualities,
            "features": [
                "Text-to-image generation",
                "High-quality output",
                "Streaming with partial images",
                "Automatic prompt revision",
                "Multiple formats and sizes",
                "Transparent backgrounds",
                "Custom compression"
            ]
        }


# Global instance for easy access
image_generator = ImageGenerationTool()
