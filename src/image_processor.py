import requests
import os
from typing import List
import logging
from openai import OpenAI
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Image processor for downloading and generating descriptions for images using OpenAI.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._setup_openai()
        
    def _setup_openai(self):
        """Configure OpenAI"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. Image processing will not work.")
            return
            
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4.1-mini" # User specified model
        
    def download_image_as_base64(self, url: str, timeout: int = 30) -> str:
        """
        Download image from URL and return as base64 string.
        """
        try:
            logger.info(f"Downloading image from: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"Content type '{content_type}' may not be an image")
            
            return base64.b64encode(response.content).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise

    def generate_description(self, base64_image: str) -> str:
        """
        Generate detailed description (alt text) for the image using OpenAI.
        """
        try:
            if not hasattr(self, 'client'):
                self._setup_openai()
                if not hasattr(self, 'client'):
                    return "Error: AI model not configured (missing API Key)."

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Please describe this image in detail. Include main subjects, setting, text (if any visible), and relevant context. The description should be precise and suitable for a knowledge base search index."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ],
                    }
                ],
                max_tokens=500,
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate image description: {e}")
            return f"Error generating description: {e}"

    def process_image_urls(self, urls: List[str]) -> str:
        """
        Download images and generate descriptions.
        """
        descriptions = []
        
        for i, url in enumerate(urls, 1):
            try:
                logger.info(f"Processing Image {i}/{len(urls)}: {url}")
                
                base64_image = self.download_image_as_base64(url)
                description = self.generate_description(base64_image)
                
                if description:
                    descriptions.append(f"=== Image {i}: {url} ===\n[Image Description]:\n{description}")
                else:
                    logger.warning(f"No description generated for image: {url}")
                    
            except Exception as e:
                logger.error(f"Failed to process image {url}: {e}")
                descriptions.append(f"=== Image {i}: {url} ===\nERROR: Failed to process image - {e}")
                
        return "\n\n" + "="*50 + "\n\n".join(descriptions) if descriptions else ""
