#!/usr/bin/env python3
"""
Article Crawler - Main Entry Point

This script orchestrates the extraction of content from article URLs.
It processes URLs by category from JSON files and extracts content using specialized scrapers.
"""

import os
import sys
import json
import argparse
import concurrent.futures
import logging
import time
import gc
import random
from colorama import Fore, Style, init
from datetime import datetime

# Add parent directory to path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules from the article_crawler package
from src.extractors.config import CHECKPOINT_FILE, MAX_WAIT_TIME, MAX_RETRIES
from src.extractors.logger import log_scrape_status, log_debug, ensure_log_directories
from src.extractors.utils import load_checkpoint
from src.extractors.file_processor import process_file

# Import psutil for memory tracking
try:
    import psutil
    MEMORY_TRACKING = True
except ImportError:
    MEMORY_TRACKING = False

# Initialize colorama for colored terminal output
init(autoreset=True)

def log_memory_usage():
    """Log current memory usage of the process."""
    if not MEMORY_TRACKING:
        return
        
    process = psutil.Process(os.getpid())
    memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
    log_scrape_status(f"{Fore.CYAN}Memory usage: {memory:.2f} MB{Style.RESET_ALL}")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Extract article content from URLs.")
    parser.add_argument("--reset-checkpoint", action="store_true",
                        help="Reset the checkpoint file")
    parser.add_argument("--input-dir", type=str, default="output/urls",
                        help="Directory containing URL JSON files (default: Scrape_urls)")
    parser.add_argument("--output-dir", type=str, default="output/articles",
                        help="Directory to save extracted articles (default: Article)")
    parser.add_argument("--max-workers", type=int, default=6,
                        help="Maximum number of concurrent workers (default: 6)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output")
    return parser.parse_args()

def main():
    """Main function to run the article crawler."""
    args = parse_args()
    
    # Reset checkpoint if requested
    if args.reset_checkpoint:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            log_scrape_status(f"{Fore.YELLOW}Checkpoint file reset.{Style.RESET_ALL}")
    
    # Create log directories at startup
    ensure_log_directories()
    
    log_scrape_status(f"{Fore.GREEN}========================{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}STARTING ARTICLE CRAWLER{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}========================{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Starting with MAX_WAIT_TIME={MAX_WAIT_TIME}s, MAX_RETRIES={MAX_RETRIES}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Input directory: {args.input_dir}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Output directory: {args.output_dir}{Style.RESET_ALL}")
    
    input_folder = args.input_dir
    if not os.path.exists(input_folder):
        log_scrape_status(f"{Fore.RED}[ERROR] Input folder '{input_folder}' not found!{Style.RESET_ALL}")
        return 1
        
    files = [os.path.join(input_folder, file) for file in os.listdir(input_folder) if file.endswith(".json")]
    log_scrape_status(f"Found {len(files)} URL files to process")
    
    # Set the output directory in a module-level variable that scrapers can access
    import storage
    storage.set_output_directory(args.output_dir)
    
    # Track results across all files
    total_processed = 0
    total_failed = 0
    total_urls = 0
    total_files_processed = 0

    # Process files concurrently with ThreadPoolExecutor
    max_workers = min(args.max_workers, len(files))  # Don't create more workers than files
    log_scrape_status(f"{Fore.CYAN}Starting concurrent processing of {max_workers} files at a time{Style.RESET_ALL}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all files for processing
        future_to_file = {executor.submit(process_file, file): file for file in files}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            category = os.path.splitext(os.path.basename(file))[0]
            try:
                result = future.result()
                if "error" in result:
                    log_scrape_status(f"{Fore.RED}❌ [ERROR] Failed to process file {file}: {result['error']}{Style.RESET_ALL}")
                else:
                    total_processed += result["processed"]
                    total_failed += result["failed"]
                    total_urls += result["total"]
                    total_files_processed += 1
                    
                    # Log completion of this file
                    log_scrape_status(f"{Fore.GREEN}✅ Finished processing file: {file}, {result['processed']}/{result['total']} articles processed, {result['failed']} failed{Style.RESET_ALL}")
            except Exception as exc:
                log_scrape_status(f"{Fore.RED}❌ [ERROR] File {file} generated an exception: {exc}{Style.RESET_ALL}")
            finally:
                # Force garbage collection after each file completes
                gc.collect()
                log_debug(f"Garbage collection performed after file: {file}")
                log_memory_usage()  # Track memory after garbage collection

    # Final message after scraping
    log_scrape_status(f"\n{Fore.GREEN}✅ Scraping completed! Successfully saved {total_processed} articles from {total_files_processed}/{len(files)} files.{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}Total URLs: {total_urls}, Successful: {total_processed}, Failed: {total_failed}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}========================{Style.RESET_ALL}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
