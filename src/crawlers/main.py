#!/usr/bin/env python3
"""
Simplified Crawler Manager

This script runs all available crawlers, processes URLs from configured sources,
and saves results to output/urls directory using the unified approach.
"""

import os
import sys
import time
import json
import logging
import argparse
import concurrent.futures
from typing import Dict, List, Set

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Initialize logger
logger = get_crawler_logger('crawler_manager')

def import_crawler_module(crawler_name: str):
    """Import crawler module dynamically."""
    try:
        # Standardize crawler name format
        crawler_name = crawler_name.lower()
        module_name = f"{crawler_name}_crawler"
        crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")

        # Case-insensitive file matching
        for filename in os.listdir(crawler_dir):
            if filename.lower() == f"{module_name}.py":
                module_path = os.path.join(crawler_dir, filename)
                logger.info(f"Found crawler module at: {module_path}")
                
                # Import the module using spec
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
                
        logger.error(f"Crawler module not found for: {crawler_name}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to import {crawler_name} module: {e}")
        return None

def crawl_with_module(crawler_name: str, category: str, source_url: str, url_manager, args):
    """Run a specific crawler for a source URL and category."""
    logger.info(f"Running {crawler_name} crawler for {category} at {source_url}")
    
    # Import the crawler module
    crawler_module = import_crawler_module(crawler_name)
    if not crawler_module:
        logger.error(f"Failed to import {crawler_name} crawler module")
        return 0
    
    try:
        # Call crawl_category with appropriate parameters based on crawler type
        urls = None
        if crawler_name == "rfanews":
            urls = crawler_module.crawl_category(source_url, category, max_clicks=args.max_clicks)
        elif crawler_name == "postkhmer":
            urls = crawler_module.crawl_category(source_url, category, max_click=args.max_clicks)
        elif crawler_name == "kohsantepheapdaily":
            urls = crawler_module.crawl_category(source_url, category, max_scroll=args.max_scrolls)
        elif crawler_name == "dapnews":
            urls = crawler_module.crawl_category(source_url, category, max_pages=args.max_pages)
        elif crawler_name == "sabaynews":
            urls = crawler_module.crawl_category(source_url, category, max_pages=args.max_pages)
        else:
            urls = crawler_module.crawl_category(source_url, category, max_pages=args.max_pages)
        
        # Safety checks on returned URLs
        if not urls:
            logger.warning(f"{crawler_name} crawler returned no URLs")
            return 0
            
        if not isinstance(urls, (list, set)):
            logger.error(f"{crawler_name} returned invalid URL type: {type(urls)}")
            return 0
        
        # Add URLs to URL manager
        url_count = len(urls)
        added = url_manager.add_urls(category, urls)
        logger.info(f"Found {url_count} URLs, added {added} new unique URLs for {category}")
        
        return added
        
    except Exception as e:
        logger.error(f"Error running {crawler_name} crawler for {category}: {str(e)}")
        return 0

def get_available_crawlers():
    """Get list of available crawler modules."""
    crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")
    crawlers = []
    for file in os.listdir(crawler_dir):
        if file.endswith("_crawler.py"):
            crawler_name = file.replace("_crawler.py", "").lower()
            crawlers.append(crawler_name)
    return sorted(crawlers)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run all crawlers to collect URLs")
    parser.add_argument("--output-dir", type=str, default="output/urls",
                        help="Directory to save URLs (default: output/urls)")
    parser.add_argument("--max-workers", type=int, default=6,
                        help="Maximum number of concurrent crawlers (default: 6)")
    parser.add_argument("--max-clicks", type=int, default=-1,
                        help="Maximum clicks for pagination (-1 for unlimited)")
    parser.add_argument("--max-scrolls", type=int, default=-1,
                        help="Maximum scrolls for pagination (-1 for unlimited)")
    parser.add_argument("--max-pages", type=int, default=-1,
                        help="Maximum pages for pagination (-1 for unlimited)")
    parser.add_argument("--crawlers", type=str, nargs="+",
                        help="Specific crawlers to run (default: all)")
    parser.add_argument("--categories", type=str, nargs="+",
                        help="Specific categories to crawl (default: all)")
    return parser.parse_args()

def main():
    """Main function to run all crawlers."""
    args = parse_args()
    
    # Make sure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize URL manager for saving results
    url_manager = URLManager(args.output_dir, "all")
    
    # Get available crawlers
    available_crawlers = get_available_crawlers()
    logger.info(f"Available crawlers: {', '.join(available_crawlers)}")
    
    # Filter crawlers if specified
    crawlers_to_run = args.crawlers if args.crawlers else available_crawlers
    crawlers_to_run = [c for c in crawlers_to_run if c in available_crawlers]
    
    # Get available categories
    available_categories = sorted(url_manager.category_sources.keys())
    logger.info(f"Available categories: {', '.join(available_categories)}")
    
    # Filter categories if specified
    categories_to_process = args.categories if args.categories else available_categories
    categories_to_process = [c for c in categories_to_process if c in available_categories]
    
    # Track overall statistics
    total_urls_added = 0
    
    # Process each crawler and category
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = []
        
        # Submit crawling jobs
        for crawler_name in crawlers_to_run:
            for category in categories_to_process:
                sources = url_manager.get_sources_for_category(category, crawler_name)
                if not sources:
                    # Change log level to debug and provide more context
                    logger.debug(f"No sources found for {crawler_name} - {category} (this is normal if the site doesn't cover this category)")
                    continue
                
                for source_url in sources:
                    futures.append(
                        executor.submit(
                            crawl_with_module,
                            crawler_name,
                            category,
                            source_url,
                            url_manager,
                            args
                        )
                    )
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                urls_added = future.result()
                total_urls_added += urls_added
            except Exception as exc:
                logger.error(f"Crawler generated an exception: {exc}")
    
    # Save final results
    results = url_manager.save_final_results()
    
    # Print summary
    logger.info("="*60)
    logger.info(f"Crawling completed - Added {total_urls_added} new URLs")
    for category, count in results.items():
        logger.info(f"  {category}: {count} URLs")
    logger.info("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())