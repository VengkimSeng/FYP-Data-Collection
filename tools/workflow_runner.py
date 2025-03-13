#!/usr/bin/env python3
"""
Complete Workflow Runner

This script runs the complete workflow:
1. Syncs category URLs from categories.json to the Scrape_urls directory
2. Optionally runs the master crawler to collect URLs
3. Runs the article crawler to extract content

Usage:
    python run_complete_workflow.py [options]
"""

import os
import sys
import argparse
import subprocess
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("workflow.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("workflow")

def run_command(command, description):
    """Run a command with logging and error handling."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {' '.join(command)}")
    
    try:
        start_time = time.time()
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Completed: {description} in {elapsed_time:.1f} seconds")
        logger.debug(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in {description}: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to execute {description}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run the complete crawling workflow")
    parser.add_argument("--skip-sync", action="store_true", 
                        help="Skip syncing categories.json to Scrape_urls")
    parser.add_argument("--skip-master", action="store_true", 
                        help="Skip running the master crawler (use existing URLs)")
    parser.add_argument("--urls-per-category", type=int, default=2500,
                        help="Target URLs per category for master crawler (default: 2500)")
    parser.add_argument("--max-workers", type=int, default=3,
                        help="Maximum workers for master crawler (default: 3)")
    parser.add_argument("--reset-checkpoint", action="store_true",
                        help="Reset article extraction checkpoint (process all URLs)")
    
    args = parser.parse_args()
    
    # Create a timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = "Crawl_Results"
    output_dir = os.path.join(base_output_dir, f"crawl_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    article_output_dir = os.path.join(output_dir, "Articles")
    os.makedirs(article_output_dir, exist_ok=True)
    
    logger.info(f"Starting complete workflow at {timestamp}")
    logger.info(f"Output directory: {output_dir}")
    
    # Step 1: Sync categories.json to Scrape_urls directory
    if not args.skip_sync:
        if not run_command(["python", "sync_category_urls.py"], 
                         "Syncing categories to Scrape_urls directory"):
            logger.error("Failed to sync categories. Exiting.")
            return 1
    else:
        logger.info("Skipping category sync as requested")
    
    # Step 2: Run master crawler if not skipped
    if not args.skip_master:
        if not run_command([
            "python", "master_crawler_controller.py",
            "--urls-per-category", str(args.urls_per_category),
            "--max-workers", str(args.max_workers),
            "--output-dir", "output/urls"  # Direct master crawler to write to Scrape_urls
        ], "Running master crawler to collect URLs"):
            logger.error("Master crawler failed. Continuing with existing URLs.")
    else:
        logger.info("Skipping master crawler as requested")
    
    # Step 3: Run article crawler
    reset_flag = ["--reset-checkpoint"] if args.reset_checkpoint else []
    if not run_command([
        "python", "A_Overall_Article_Crawler.py",
        "--input-dir", "output/urls",
        "--output-dir", article_output_dir
    ] + reset_flag, "Extracting article content"):
        logger.error("Article extraction failed")
        return 1
    
    logger.info(f"Complete workflow finished. Results saved in {output_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
