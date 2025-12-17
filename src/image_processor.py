import requests
import os
from typing import List
import logging
import google.generativeai as genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Image processor for downloading and generating descriptions for images using Multimodal LLM.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._setup_genai()
        
    def _setup_genai(self):
        """Configure Google Generative AI"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found. Image processing will not work.")
            return
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
    def download_image(self, url: str, timeout: int = 30) -> Image.Image:
        """
        Download image from URL and return as PIL Image.
        """
        try:
            logger.info(f"Downloading image from: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"Content type '{content_type}' may not be an image")
                
            return Image.open(io.BytesIO(response.content))
            
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise

    def generate_description(self, image: Image.Image) -> str:
        """
        Generate detailed description (alt text) for the image using Gemini.
        """
        try:
            if not hasattr(self, 'model'):
                self._setup_genai()
                if not hasattr(self, 'model'):
                    return "Error: AI model not configured (missing API Key)."

            prompt = (
                "Please describe this image in detail. "
                "Include main subjects, setting, text (if any visible), and relevant context. "
                "The description should be precise and suitable for a knowledge base search index."
            )
            
            response = self.model.generate_content([prompt, image])
            return response.text
            
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
                
                image = self.download_image(url)
                description = self.generate_description(image)
                
                if description:
                    descriptions.append(f"=== Image {i}: {url} ===\n[Image Description]:\n{description}")
                else:
                    logger.warning(f"No description generated for image: {url}")
                    
            except Exception as e:
                logger.error(f"Failed to process image {url}: {e}")
                descriptions.append(f"=== Image {i}: {url} ===\nERROR: Failed to process image - {e}")
                
        return "\n\n" + "="*50 + "\n\n".join(descriptions) if descriptions else ""
