import logging
import pandas as pd
import requests
import io
import os
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from typing import List, Optional

logger = logging.getLogger(__name__)

class SpreadsheetProcessor:
    """Handles processing of spreadsheet files (CSV, Excel) from URLs"""
    
    def __init__(self):
        pass
        
    def process_spreadsheet_urls(self, urls: List[str]) -> str:
        """Download and extract content from spreadsheet URLs"""
        all_text = []
        
        for url in urls:
            try:
                text = self._process_single_url(url)
                if text:
                    all_text.append(f"--- Document Source: {url} ---\n{text}")
            except Exception as e:
                logger.error(f"Failed to process spreadsheet URL {url}: {e}")
                
        return "\n\n".join(all_text)
    
    def _process_single_url(self, url: str) -> Optional[str]:
        """Download and extract content from a single spreadsheet URL"""
        try:
            # Determine file type from URL or content-type
            file_ext = self._get_extension(url)
            
            # Download file
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            file_content = io.BytesIO(response.content)
            
            # Retrieve content based on extension
            df = None
            if file_ext in ['.csv', '.txt']:
                # Try reading as CSV
                try:
                    df = pd.read_csv(file_content)
                except Exception:
                    # Fallback for weird delimiters or encoding? for now just fail is fine
                    logger.warning(f"Failed to read CSV from {url}")
            elif file_ext in ['.xlsx', '.xls', '.xlsm']:
                try:
                    df = pd.read_excel(file_content)
                except Exception:
                    logger.warning(f"Failed to read Excel from {url}")
            else:
                # Try inferring? 
                # Let's try excel first then csv as fallback if extension is unknown/missing
                try:
                    df = pd.read_excel(file_content)
                except Exception:
                    file_content.seek(0)
                    try:
                        df = pd.read_csv(file_content)
                    except Exception:
                        logger.warning(f"Could not infer spreadsheet type for {url}")
                        return None

            if df is not None and not df.empty:
                # Convert to markdown table or text representation
                # Using to_markdown() requires tabulate, which we might need to add to deps?
                # Alternatively, to_csv or to_string is safer without extra deps.
                # to_string() gives a tabular representation.
                # to_csv(index=False) is good for preserving data structure for LLM.
                return df.to_csv(index=False)
            
            return None

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None

    def _get_extension(self, url: str) -> str:
        """Get file extension from URL"""
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1].lower()
        return ext
