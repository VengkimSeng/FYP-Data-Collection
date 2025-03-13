"""
Storage utility functions for saving article data.
"""

import os
import json
import time
import traceback
import threading
from colorama import Fore, Style

from src.extractors.logger import log_scrape_status, log_debug
from src.extractors.utils import update_checkpoint

# Default output directory that can be overridden
OUTPUT_DIR = "output/articles"

# Thread-safe lock for file operations
file_locks = {}

def set_output_directory(directory):
    """Set the global output directory."""
    global OUTPUT_DIR
    OUTPUT_DIR = directory
    # Ensure the directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_debug(f"Output directory set to: {OUTPUT_DIR}")

def get_file_lock(filename):
    """Get or create a lock for a specific file."""
    if filename not in file_locks:
        file_locks[filename] = threading.Lock()
    return file_locks[filename]

def save_article_data(category, article_data, url=None):
    """Save article data to a JSON file."""
    # Use the global output directory
    output_file = os.path.join(OUTPUT_DIR, f"{category}.json")
    
    log_scrape_status(f"🔄 Starting save process: {article_data['title'][:30]}... to {output_file}")

    # Get the lock for this specific file
    file_lock = get_file_lock(output_file)
    
    with file_lock:
        try:
            # Load existing data
            existing_data = []
            if os.path.exists(output_file):
                try:
                    log_debug(f"Reading existing file: {output_file}")
                    with open(output_file, "r", encoding="utf-8") as file:
                        file_content = file.read()
                        if file_content.strip():  # Check if file is not empty
                            existing_data = json.loads(file_content)
                            log_debug(f"Loaded {len(existing_data)} articles from existing file")
                        else:
                            log_debug("File is empty, starting fresh")
                except json.JSONDecodeError:
                    log_scrape_status(f"{Fore.YELLOW}⚠️ Warning: JSON file corrupted. Creating backup and resetting.{Style.RESET_ALL}")
                    # Create backup of corrupted file
                    if os.path.exists(output_file):
                        backup_file = f"{output_file}.bak.{int(time.time())}"
                        try:
                            import shutil
                            shutil.copy2(output_file, backup_file)
                            log_scrape_status(f"Created backup of corrupted file at {backup_file}")
                        except Exception as backup_err:
                            log_scrape_status(f"Failed to backup corrupted file: {backup_err}")
                    existing_data = []
                except Exception as read_err:
                    log_scrape_status(f"{Fore.RED}❌ [ERROR] Failed to read existing file: {read_err}{Style.RESET_ALL}")
                    existing_data = []

            # Append new article
            existing_data.append(article_data)

            # Write data to file using a temporary file for safety
            temp_file = f"{output_file}.temp"
            try:
                log_debug(f"Writing to temporary file: {temp_file}")
                with open(temp_file, "w", encoding="utf-8") as file:
                    json.dump(existing_data, file, ensure_ascii=False, indent=4)
                log_debug(f"Temporary file written successfully")
                
                # Replace original file with updated file
                if os.path.exists(output_file):
                    os.replace(temp_file, output_file)
                else:
                    os.rename(temp_file, output_file)
                
                log_debug(f"File saved successfully to {output_file}")
                log_scrape_status(f"{Fore.GREEN}✅ Successfully saved article: {article_data['title'][:50]}... Moving to next URL.{Style.RESET_ALL}")
                
                # Update checkpoint
                if url:
                    log_debug(f"Updating checkpoint for URL: {url}")
                    update_checkpoint(category, url)
            except Exception as write_err:
                log_scrape_status(f"{Fore.RED}❌ [ERROR] Failed to write file {output_file}: {write_err}{Style.RESET_ALL}")
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        log_debug(f"Removed temporary file after error: {temp_file}")
                    except:
                        pass

        except Exception as e:
            log_scrape_status(f"{Fore.RED}❌ [ERROR] General error in save_article_data: {e}{Style.RESET_ALL}")
            log_scrape_status(f"Stack trace: {traceback.format_exc()}")
