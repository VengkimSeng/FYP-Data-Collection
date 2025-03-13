"""
URL processing module for handling individual URLs.
"""

import threading
import random
import time
import traceback
from urllib.parse import urlparse
from colorama import Fore, Style

from .logger import log_scrape_status, log_category_progress, log_category_error, log_debug, loading_animation
from .utils import retry_on_exception, get_base_url
from .config import SCRAPER_MAP

# Fix the global variable reference
stop_loading = False

@retry_on_exception()
def process_url(url, category):
    """
    Process a single URL by selecting and using the appropriate scraper.
    
    Args:
        url: The URL to process
        category: The category this URL belongs to
        
    Returns:
        The article data if successful, None otherwise
    """
    global stop_loading
    stop_loading = False  # Reset animation flag

    log_scrape_status(f"🔄 Starting processing for: {url}")
    log_category_progress(category, url, f"Starting processing for category: {category}", is_start=True)
    
    # Start loading animation in a separate thread
    log_debug(f"Starting loading animation for URL: {url}")
    t = threading.Thread(target=loading_animation, daemon=True)
    t.start()

    try:
        base_url = get_base_url(url)
        log_debug(f"Parsed base URL: {base_url}")
        log_scrape_status(f"🔍 Checking scraper function for: {base_url}")
        log_category_progress(category, url, f"Using base URL: {base_url}")
        
        if base_url in SCRAPER_MAP:
            scraper_function = SCRAPER_MAP[base_url]
            log_scrape_status(f"🔧 Using {scraper_function.__name__} for: {url}")
            log_category_progress(category, url, f"Selected scraper: {scraper_function.__name__}")
            
            log_debug(f"Calling scraper function: {scraper_function.__name__}")
            result = scraper_function(url, category)
            log_debug(f"Scraper function returned. Success: {result is not None}")
            
            if result is not None:
                log_category_progress(category, url, "Scraping completed successfully")
            else:
                log_category_progress(category, url, "Scraper returned None result - possible failure")
                log_category_error(category, url, "Scraper returned None result")
            
            log_scrape_status(f"✅ Finished processing: {url}")
            log_scrape_status(f"➡️ Moving to next URL...")
            
            # Add random delay between requests to avoid overwhelming servers
            delay = 2 + (random.random() * 3)  # Random delay between 2-5 seconds
            log_scrape_status(f"⏱️ Waiting {delay:.1f}s before next request")
            log_category_progress(category, url, f"Waiting {delay:.1f}s before next request")
            time.sleep(delay)
            log_category_progress(category, url, "Processing complete", is_end=True)
            return result
        else:
            error_msg = f"No scraper available for {base_url}"
            log_scrape_status(f"{Fore.RED}[ERROR] {error_msg}{Style.RESET_ALL}")
            log_category_progress(category, url, f"ERROR: {error_msg}")
            log_category_error(category, url, error_msg)
            log_category_progress(category, url, "Processing failed - no scraper available", is_end=True)
            return None
    except Exception as e:
        error_msg = f"Processing URL failed: {str(e)}"
        stack_trace = traceback.format_exc()
        log_scrape_status(f"{Fore.RED}[ERROR] {error_msg}{Style.RESET_ALL}")
        log_debug(f"Exception details for {url}: {str(e)}")
        log_scrape_status(f"Stack trace: {stack_trace}")
        
        # Log detailed error information
        log_category_progress(category, url, f"ERROR: {error_msg}")
        log_category_progress(category, url, f"Stack trace: {stack_trace}")
        log_category_error(category, url, f"{error_msg}; Stack trace available in log")
        log_category_progress(category, url, "Processing failed with exception", is_end=True)
        raise  # Re-raise for retry decorator
    finally:
        log_debug(f"Setting stop_loading flag to True for URL: {url}")
        stop_loading = True  # Stop animation
        time.sleep(0.5)  # Give animation thread time to complete
        log_debug(f"Animation thread should be stopped for URL: {url}")
        log_scrape_status(f"🏁 Completed processing attempt for: {url}")
