"""
File processing module for handling URL files.
"""

import json
import threading
import os
from colorama import Fore, Style
import traceback

from .logger import log_scrape_status, log_category_progress, log_category_error, log_debug
from .url_processor import process_url

def process_file(file):
    """
    Process a single URL file.
    
    Args:
        file: Path to the JSON file containing URLs
        
    Returns:
        Dict with results of processing
    """
    category = os.path.splitext(os.path.basename(file))[0]
    
    # Create a thread identifier for logging
    thread_id = threading.current_thread().name
    
    log_scrape_status(f"[Thread {thread_id}] Starting to process category: {category}")
    
    try:
        with open(file, "r", encoding="utf-8") as f:
            urls = json.load(f)
        
        log_scrape_status(f"[Thread {thread_id}] Total URLs to process: {len(urls)} for category {category}")
    
        processed = 0
        failed = 0
        for i, url in enumerate(urls):
            try:
                log_scrape_status(f"[Thread {thread_id}] ⏳ Processing URL {i+1}/{len(urls)}: {url}")
                log_category_progress(category, url, f"Starting processing as URL {i+1}/{len(urls)} in category {category}", is_start=True)
                
                result = process_url(url, category)
                
                if result is not None:
                    processed += 1
                    log_scrape_status(f"[Thread {thread_id}] ✅ Successfully scraped URL {i+1}: {url}")
                    log_category_progress(category, url, "Successfully scraped and saved article")
                else:
                    failed += 1
                    log_scrape_status(f"[Thread {thread_id}] ⚠️ URL returned None result: {url}")
                    log_category_progress(category, url, "WARNING: URL returned None result")
                    log_category_error(category, url, "URL returned None result")
                
                log_category_progress(category, url, "Processing complete", is_end=True)
            except Exception as e:
                failed += 1
                error_msg = f"Failed to process URL: {str(e)}"
                log_scrape_status(f"[Thread {thread_id}] {Fore.RED}❌ [ERROR] {error_msg}{Style.RESET_ALL}")
                log_category_progress(category, url, f"ERROR: {error_msg}", is_end=True)
                log_category_error(category, url, error_msg)
                # Continue with the next URL instead of stopping
                continue
                
            log_scrape_status(f"[Thread {thread_id}] 📊 Progress: {processed} successful, {failed} failed, {i+1}/{len(urls)} total")
            log_scrape_status(f"[Thread {thread_id}] ➡️ Moving to next URL in category {category}...")
        
        log_scrape_status(f"[Thread {thread_id}] {Fore.GREEN}[COMPLETE] Category {category}: {processed}/{len(urls)} articles processed, {failed} failed{Style.RESET_ALL}")
        return {"category": category, "processed": processed, "failed": failed, "total": len(urls)}
    except Exception as e:
        log_scrape_status(f"[Thread {thread_id}] {Fore.RED}❌ [ERROR] Failed to process category {category}: {str(e)}{Style.RESET_ALL}")
        log_scrape_status(f"[Thread {thread_id}] Stack trace: {traceback.format_exc()}")
        return {"category": category, "processed": 0, "failed": 0, "total": 0, "error": str(e)}
