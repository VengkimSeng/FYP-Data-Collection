"""
Logging utilities for the article crawler.
"""

import os
import logging
import datetime
import threading
import sys
import time
from colorama import Fore, Style

# Configure logging
logging.basicConfig(
    filename="scraping_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Thread-safe lock for logging operations
log_lock = threading.Lock()

def log_scrape_status(message):
    """Log a message to both console and log file."""
    with log_lock:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} | {message}")
        logging.info(message)

def log_debug(message):
    """Log a debug message with a blue prefix."""
    log_scrape_status(f"{Fore.BLUE}[DEBUG] {message}{Style.RESET_ALL}")

def ensure_log_directories():
    """Create directories for storing log files."""
    os.makedirs("output/logs/categories", exist_ok=True)
    os.makedirs("output/logs/errors", exist_ok=True)

def get_safe_category_name(category):
    """Convert a category name to a safe filename."""
    import re
    return re.sub(r'[\\/*?:"<>|]', "", category)

def log_category_progress(category, url, message, is_start=False, is_end=False):
    """Log progress for a specific category to a dedicated log file."""
    ensure_log_directories()
    safe_category = get_safe_category_name(category)
    log_file = os.path.join("output/logs/categories", f"{safe_category}.log")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    divider = "=" * 50
    
    with open(log_file, "a", encoding="utf-8") as f:
        if is_start:
            f.write(f"\n{divider}\n{timestamp} - START PROCESSING URL: {url} (Category: {category})\n{divider}\n")
        
        f.write(f"{timestamp} - {message} (URL: {url})\n")
        
        if is_end:
            f.write(f"{divider}\n{timestamp} - END PROCESSING URL: {url} (Category: {category})\n{divider}\n\n")
    
    # Also log to main log for debug purposes
    log_debug(message)

def log_category_error(category, url, error_message, html_file=None):
    """Log error information for a specific category in a JSON file."""
    import json
    ensure_log_directories()
    safe_category = get_safe_category_name(category)
    error_file = os.path.join("output/logs/errors", f"{safe_category}_errors.json")
    
    # Initialize or load error data
    error_data = []
    if os.path.exists(error_file):
        try:
            with open(error_file, "r", encoding="utf-8") as f:
                error_data = json.load(f)
        except json.JSONDecodeError:
            log_debug(f"Error reading existing error file for {category}, creating new one")
    
    # Check if this URL already has an error entry
    url_entry = next((item for item in error_data if item["url"] == url), None)
    
    if url_entry:
        # Append new error message if it's not already there
        if error_message not in url_entry["error"]:
            url_entry["error"].append(error_message)
        # Update HTML file reference if provided
        if html_file and html_file != "None":
            url_entry["html_file"] = html_file
    else:
        # Create new entry for this URL
        new_entry = {
            "url": url,
            "error": [error_message],
            "html_file": html_file if html_file else "None"
        }
        error_data.append(new_entry)
    
    # Write updated error data
    with open(error_file, "w", encoding="utf-8") as f:
        json.dump(error_data, f, ensure_ascii=False, indent=4)
    
    log_debug(f"Category error logged to {error_file}")

# Animation utilities for loading indicator
stop_loading = False

def loading_animation():
    """Show a loading animation in the console."""
    while not stop_loading:
        for c in ['|', '/', '-', '\\']:
            if stop_loading:
                return  # Exit immediately when flag is set
            sys.stdout.write(f'\r{Fore.CYAN}Scraping in progress... {c}{Style.RESET_ALL}')
            sys.stdout.flush()
            time.sleep(0.2)
    sys.stdout.write('\r')
    sys.stdout.flush()
