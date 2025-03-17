"""
Utility functions for the article extractor.
"""

import os
import json
import time
from typing import Dict, List, Any
from functools import wraps
from src.extractors.config import CHECKPOINT_FILE
from src.extractors.logger import log_debug

def load_checkpoint() -> Dict[str, Any]:
    """
    Load checkpoint data from file.
    
    Returns:
        Checkpoint data as dictionary
    """
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_debug(f"Error loading checkpoint: {e}")
    return {}

def update_checkpoint(data: Dict[str, Any]) -> bool:
    """
    Update checkpoint data in file.
    
    Args:
        data: Checkpoint data to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        
        # Merge with existing checkpoint data
        checkpoint = load_checkpoint()
        checkpoint.update(data)
        
        # Write to temporary file first
        temp_file = f"{CHECKPOINT_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2)
            
        # Atomic replace
        os.replace(temp_file, CHECKPOINT_FILE)
        return True
    except Exception as e:
        log_debug(f"Error updating checkpoint: {e}")
        return False

def get_url_hostname(url: str) -> str:
    """
    Extract hostname from URL.
    
    Args:
        url: URL to parse
        
    Returns:
        Hostname part of the URL
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""

def format_timestamp(timestamp: float) -> str:
    """
    Format a Unix timestamp as string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted timestamp string
    """
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def is_scraped(url: str, category: str = None) -> bool:
    """
    Check if a URL has already been scraped.
    
    Args:
        url: URL to check
        category: Optional category to check specifically
        
    Returns:
        True if the URL has been scraped, False otherwise
    """
    checkpoint = load_checkpoint()
    processed_urls = checkpoint.get('processed_urls', [])
    
    # If category is specified, check category-specific processing
    if category and 'category_urls' in checkpoint:
        category_urls = checkpoint['category_urls'].get(category, [])
        return url in category_urls
        
    # Otherwise check global processed URLs
    return url in processed_urls

def retry_on_exception(max_retries=3, delay=2):
    """
    Decorator to retry a function on exception.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Time to wait between retries in seconds
        
    Returns:
        Decorated function that will retry on exception
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        log_debug(f"Max retries reached ({max_retries}) for {func.__name__}: {e}")
                        raise
                    
                    log_debug(f"Retry {retries}/{max_retries} for {func.__name__}: {e}")
                    time.sleep(delay)
            
            return None  # Should never reach here
        return wrapper
    return decorator
