import requests
import tempfile
import os
from typing import List, Optional
import logging
from pathlib import Path

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF processor for downloading and extracting text from PDF files.
    Supports multiple PDF processing libraries with fallback options.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def download_pdf(self, url: str, timeout: int = 30) -> bytes:
        """
        Download PDF from URL and return content as bytes.
        
        Args:
            url: URL to download PDF from
            timeout: Request timeout in seconds
            
        Returns:
            PDF content as bytes
            
        Raises:
            requests.RequestException: If download fails
        """
        try:
            logger.info(f"Downloading PDF from: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Verify content type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                logger.warning(f"Content type '{content_type}' may not be PDF")
            
            return response.content
            
        except requests.RequestException as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
            raise
    
    def extract_text_with_pdfplumber(self, pdf_content: bytes) -> str:
        """Extract text using pdfplumber library."""
        if not pdfplumber:
            raise ImportError("pdfplumber library not available")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()
            
            try:
                text_parts = []
                with pdfplumber.open(tmp_file.name) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                        except Exception as e:
                            logger.warning(f"Failed to extract text from page {page_num}: {e}")
                
                return "\n\n".join(text_parts)
                
            finally:
                os.unlink(tmp_file.name)
    
    def extract_text_with_pypdf2(self, pdf_content: bytes) -> str:
        """Extract text using PyPDF2 library."""
        if not PyPDF2:
            raise ImportError("PyPDF2 library not available")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()
            
            try:
                text_parts = []
                with open(tmp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                        except Exception as e:
                            logger.warning(f"Failed to extract text from page {page_num}: {e}")
                
                return "\n\n".join(text_parts)
                
            finally:
                os.unlink(tmp_file.name)
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content using available libraries.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text content
            
        Raises:
            Exception: If text extraction fails with all available methods
        """
        errors = []
        
        # Try pdfplumber first (generally better text extraction)
        if pdfplumber:
            try:
                text = self.extract_text_with_pdfplumber(pdf_content)
                if text.strip():
                    logger.info("Successfully extracted text using pdfplumber")
                    return text
            except Exception as e:
                errors.append(f"pdfplumber: {e}")
                logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Fallback to PyPDF2
        if PyPDF2:
            try:
                text = self.extract_text_with_pypdf2(pdf_content)
                if text.strip():
                    logger.info("Successfully extracted text using PyPDF2")
                    return text
            except Exception as e:
                errors.append(f"PyPDF2: {e}")
                logger.warning(f"PyPDF2 extraction failed: {e}")
        
        # If no libraries available or all failed
        if not pdfplumber and not PyPDF2:
            raise ImportError("No PDF processing libraries available. Install pdfplumber or PyPDF2.")
        
        raise Exception(f"Failed to extract text from PDF. Errors: {'; '.join(errors)}")
    
    def process_pdf_urls(self, urls: List[str]) -> str:
        """
        Download and extract text from multiple PDF URLs.
        
        Args:
            urls: List of PDF URLs to process
            
        Returns:
            Combined text content from all PDFs
        """
        all_text = []
        
        for i, url in enumerate(urls, 1):
            try:
                logger.info(f"Processing PDF {i}/{len(urls)}: {url}")
                
                # Download PDF
                pdf_content = self.download_pdf(url)
                
                # Extract text
                text = self.extract_text_from_pdf(pdf_content)
                
                if text.strip():
                    all_text.append(f"=== PDF {i}: {url} ===\n{text}")
                else:
                    logger.warning(f"No text extracted from PDF: {url}")
                    
            except Exception as e:
                logger.error(f"Failed to process PDF {url}: {e}")
                all_text.append(f"=== PDF {i}: {url} ===\nERROR: Failed to process PDF - {e}")
        
        return "\n\n" + "="*50 + "\n\n".join(all_text) if all_text else ""