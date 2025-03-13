"""
General utility functions for the article crawler.
"""

import os
import json
import threading
import functools
import time
import traceback
from functools import wraps
from colorama import Fore, Style
from urllib.parse import urlparse

from config import CHECKPOINT_FILE, MAX_RETRIES, RETRY_DELAY
from logger import log_scrape_status, log_debug

# Thread-safe lock for checkpoint operations
checkpoint_lock = threading.Lock()

def load_checkpoint():
    """Load checkpoint data that tracks URLs that have been scraped."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print(f"{Fore.YELLOW}Warning: Checkpoint file corrupted, resetting...{Style.RESET_ALL}")
            return {}
    return {}

def is_scraped(category, url):
    """Check if a URL has already been scraped for a category."""
    checkpoint_data = load_checkpoint()
    return category in checkpoint_data and url in checkpoint_data[category]

def update_checkpoint(category, url):
    """Update checkpoint after successfully scraping a URL."""
    with checkpoint_lock:
        log_debug(f"Updating checkpoint for {category}: {url}")
        checkpoint_data = load_checkpoint()
        if category not in checkpoint_data:
            checkpoint_data[category] = []
        checkpoint_data[category].append(url)
        
        try:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as file:
                json.dump(checkpoint_data, file, ensure_ascii=False, indent=4)
            log_debug(f"Checkpoint updated successfully: {CHECKPOINT_FILE}")
        except Exception as e:
            log_scrape_status(f"{Fore.RED}[ERROR] Failed to update checkpoint: {str(e)}{Style.RESET_ALL}")

def retry_on_exception(max_retries=None, delay=None):
    """Decorator to retry functions on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Always use global MAX_RETRIES and RETRY_DELAY regardless of parameters
            retries = 0
            while retries < MAX_RETRIES:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= MAX_RETRIES:
                        log_scrape_status(f"{Fore.RED}[ERROR] Max retries reached ({MAX_RETRIES}) for {func.__name__}: {e}{Style.RESET_ALL}")
                        raise
                    log_scrape_status(f"{Fore.YELLOW}[RETRY] Attempt {retries}/{MAX_RETRIES} for {func.__name__}: {e}{Style.RESET_ALL}")
                    
                    # Try to forcefully restart WebDriver if it's a WebDriver issue
                    if "driver" in kwargs:
                        try:
                            kwargs["driver"].quit()
                        except:
                            pass
                    
                    time.sleep(RETRY_DELAY)
            return None
        return wrapper
    return decorator

def get_base_url(url):
    """Extract base URL from a full URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_domain(url):
    """Extract domain from URL."""
    return urlparse(url).netloc
