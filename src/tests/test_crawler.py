import os
import sys
import time
import json
import importlib.util
from typing import Dict, Set, List
import traceback
import concurrent.futures
import argparse
import logging
import atexit

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger, setup_logger

# Create log directories
os.makedirs(os.path.join(project_root, "logs", "crawlers"), exist_ok=True)
os.makedirs(os.path.join(project_root, "logs", "categories"), exist_ok=True)

# Initialize logger
logger = get_crawler_logger('test_crawler')

# Set up an exit handler to flush all logs
def exit_handler():
    for handler in logger.handlers:
        handler.flush()
    for handler in logging.root.handlers:
        handler.flush()
    logging.shutdown()

atexit.register(exit_handler)

# Try to rename the crawler file if it exists in old format
try:
    btv_old_path = os.path.join(project_root, "src", "crawlers", "Urls_Crawler", "BTV_crawler.py")
    btv_new_path = os.path.join(project_root, "src", "crawlers", "Urls_Crawler", "btv_crawler.py")
    if os.path.exists(btv_old_path) and not os.path.exists(btv_new_path):
        os.rename(btv_old_path, btv_new_path)
        logger.info("Renamed BTV_crawler.py to btv_crawler.py")
except Exception as e:
    logger.debug(f"File renaming not needed or failed: {e}")

def load_categories():
    """Load categories from the JSON file."""
    try:
        config_path = os.path.join(project_root, "config", "categories.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        return {}

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
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
                
        logger.error(f"Crawler module not found for: {crawler_name}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to import {crawler_name} module: {e}")
        return None

def test_crawler(crawler_name: str, category: str, max_urls: int = 5):
    """
    Test a specific crawler for a category.
    
    Args:
        crawler_name: Name of the crawler to test
        category: Category to crawl
        max_urls: Maximum number of URLs to collect (-1 for unlimited)
    
    Returns:
        bool: Success or failure
    """
    # Set up a category-specific log file
    log_dir = os.path.join(project_root, "logs", "categories") 
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{crawler_name}_{category}.log")
    
    cat_logger = setup_logger(
        f"{crawler_name}_{category}", 
        log_file,
        console=True
    )
    
    cat_logger.info(f"Testing {crawler_name} crawler for {category}")
    
    # Initialize URL manager for testing with absolute path
    output_dir = os.path.abspath("output/urls")  # Changed to use main output dir
    url_manager = URLManager(output_dir, crawler_name)
    cat_logger.info(f"URLs will be saved to: {os.path.join(output_dir, f'{category}.json')}")
    
    # Get source URLs for this crawler/category
    sources = url_manager.get_sources_for_category(category, crawler_name)
    if not sources:
        cat_logger.error(f"No source URLs found for {crawler_name} - {category}")
        return False
    
    # Import the crawler module
    crawler_module = import_crawler_module(crawler_name)
    if not crawler_module:
        cat_logger.error(f"Failed to import {crawler_name} crawler module")
        return False
    
    start_time = time.time()
    urls_collected = 0
    success = False
    
    try:
        for source_url in sources:
            cat_logger.info(f"Testing {crawler_name} crawler for {category} at {source_url}")
            
            if hasattr(crawler_module, 'crawl_category'):
                try:
                    # Call crawl_category with appropriate parameters based on crawler type
                    urls = None
                    if crawler_name == "rfanews":
                        urls = crawler_module.crawl_category(source_url, category, max_clicks=-1)
                    elif crawler_name == "postkhmer":
                        urls = crawler_module.crawl_category(source_url, category, max_click=-1)
                    elif crawler_name == "kohsantepheapdaily":
                        urls = crawler_module.crawl_category(source_url, category, max_scroll=-1)
                    elif crawler_name == "dapnews":
                        urls = crawler_module.crawl_category(source_url, category, max_pages=-1)
                    elif crawler_name == "sabaynews":
                        urls = crawler_module.crawl_category(source_url, category, max_pages=-1)
                    else:
                        urls = crawler_module.crawl_category(source_url, category, max_pages=-1)
                    
                    # Safety checks on returned URLs
                    if not urls:
                        cat_logger.warning(f"{crawler_name} crawler returned no URLs")
                        continue
                        
                    if not isinstance(urls, (list, set)):
                        cat_logger.error(f"{crawler_name} returned invalid URL type: {type(urls)}")
                        continue
                    
                    # Convert to set for deduplication
                    new_urls = set(urls)
                    
                    # Load existing URLs if file exists - using simple list format JSON
                    output_file = os.path.join(output_dir, f"{category}.json")
                    existing_urls = []
                    
                    if os.path.exists(output_file):
                        try:
                            with open(output_file, 'r', encoding='utf-8') as f:
                                existing_urls = json.load(f)
                        except Exception as e:
                            cat_logger.error(f"Error loading existing URLs: {e}")
                    
                    # Combine existing and new URLs using sets for deduplication
                    combined_urls = list(set(existing_urls) | new_urls)
                    
                    # Save updated URL list
                    try:
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(combined_urls, f, ensure_ascii=False, indent=2)
                        
                        # Track number of new URLs added
                        added_urls = len(combined_urls) - len(existing_urls)
                        urls_collected += added_urls
                        cat_logger.info(f"Found {len(new_urls)} URLs, added {added_urls} new unique URLs")
                        cat_logger.info(f"Saved {len(combined_urls)} URLs to {output_file}")
                        success = True
                    except Exception as e:
                        cat_logger.error(f"Error saving URLs to file: {e}")
                    
                except Exception as e:
                    cat_logger.error(f"Error during crawl_category: {str(e)}")
                    continue
            else:
                cat_logger.error("Crawler module missing crawl_category function")
                return False
            
            # Only check max_urls if it's not set to unlimited (-1)
            if max_urls != -1 and urls_collected >= max_urls:
                break
                
    except Exception as e:
        cat_logger.error(f"Error testing crawler: {str(e)}")
        return False
        
    duration = time.time() - start_time
    cat_logger.info(f"\nTest completed in {duration:.2f} seconds")
    cat_logger.info(f"URLs collected: {urls_collected}")
    
    return success

def load_test_config() -> Dict:
    """Load test configuration from sources.json."""
    config_path = os.path.join(project_root, "src", "config", "sources.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading test config: {e}")
        return {}

def get_available_crawlers():
    """Get list of available crawler modules."""
    crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")
    crawlers = []
    for file in os.listdir(crawler_dir):
        if file.endswith("_crawler.py"):
            crawler_name = file.replace("_crawler.py", "").lower()
            crawlers.append(crawler_name)
    return sorted(crawlers)

def get_available_categories(url_manager: URLManager) -> List[str]:
    """Get list of available categories."""
    return sorted(url_manager.category_sources.keys())

def process_category(category: str, crawlers: List[str], url_manager: URLManager):
    """Process a single category with all relevant crawlers."""
    # Get a category-specific logger
    cat_logger = get_crawler_logger(f"category_{category}")
    
    # Load categories to find relevant crawlers
    categories_config = load_categories()
    if not categories_config:
        cat_logger.error("Failed to load categories configuration")
        return False

    # Find crawlers that have sources for this category
    if category in categories_config:
        category_crawlers = categories_config[category].keys()
        # Filter by available crawlers
        relevant_crawlers = [c for c in category_crawlers if c in crawlers]
        
        if not relevant_crawlers:
            cat_logger.error(f"No crawlers found for category: {category}")
            return False
        
        cat_logger.info(f"Running {len(relevant_crawlers)} crawlers for category '{category}': {', '.join(relevant_crawlers)}")
        
        success = True
        for crawler in relevant_crawlers:
            cat_logger.info(f"\n{'=' * 50}")
            cat_logger.info(f"RUNNING {crawler.upper()} CRAWLER FOR {category.upper()}")
            cat_logger.info(f"{'=' * 50}")
            
            try:
                crawler_success = test_crawler(crawler, category, max_urls=-1)  # -1 means unlimited
                if not crawler_success:
                    cat_logger.warning(f"Crawler {crawler} failed for category {category}")
                    success = False
                else:
                    cat_logger.info(f"Crawler {crawler} completed successfully for category {category}")
            except Exception as e:
                cat_logger.error(f"Exception in {crawler} crawler for {category}: {str(e)}")
                cat_logger.error(traceback.format_exc())
                success = False
                # Continue with next crawler despite errors
        
        cat_logger.info(f"\n{'=' * 50}")
        cat_logger.info(f"CATEGORY {category.upper()} COMPLETED")
        cat_logger.info(f"Status: {'SUCCESS' if success else 'PARTIAL FAILURE'}")
        cat_logger.info(f"{'=' * 50}")
        
        # Also log to the main logger
        logger.info(f"Category {category} processing {'succeeded' if success else 'had failures'}")
        
        return success
    else:
        cat_logger.error(f"Category not found in configuration: {category}")
        return False

def main():
    """Main test function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test crawlers for categories")
    parser.add_argument("mode", nargs="?", default="test", help="Mode: 'test' or 'prod'")
    parser.add_argument("category", nargs="?", help="Category to crawl (if not specified, run all)")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--log", help="Log file path (for daemon mode)")
    parser.add_argument("--workers", type=int, default=6, help="Number of concurrent workers")
    parser.add_argument("--timeout", type=int, default=3600, help="Timeout per category in seconds")
    
    args = parser.parse_args()
    is_prod_mode = args.mode.lower() == "prod" 
    
    # Configure process to run in background if needed
    if args.daemon:
        # Redirect output to log file when running as daemon
        log_file = "crawler_test.log" if not args.log else args.log
        
        # Make sure the log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Set up file logging for main logger
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        logger.info(f"Running in daemon mode, output redirected to {log_file}")
        
        # Don't redirect stdout/stderr as this interferes with logging
        # Instead, we'll ensure our loggers write to both console and file
    
    url_manager = URLManager("output/urls", "test")
    
    # Get available categories and crawlers
    categories = get_available_categories(url_manager)
    crawlers = get_available_crawlers()
    
    logger.info(f"Available categories: {', '.join(categories)}")
    logger.info(f"Available crawlers: {', '.join(crawlers)}")
    
    if is_prod_mode:
        # Check if a specific category was provided as an argument
        specified_category = args.category
        if specified_category and specified_category.lower() != "--daemon" and specified_category.lower() != "--log":
            specified_category = specified_category.lower()
            if specified_category not in categories:
                logger.error(f"Invalid category: {specified_category}")
                sys.exit(1)
            
            logger.info(f"Running production crawl for specified category: {specified_category}")
            success = process_category(specified_category, crawlers, url_manager)
            sys.exit(0 if success else 1)
        else:
            # Run all categories concurrently
            logger.info(f"Running production crawl for ALL categories with {args.workers} workers")
            
            overall_start_time = time.time()
            results = {}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
                # Submit all categories for processing
                future_to_category = {
                    executor.submit(process_category, category, crawlers, url_manager): category 
                    for category in categories
                }
                
                # Process results as they complete
                overall_success = True
                for future in concurrent.futures.as_completed(future_to_category):
                    category = future_to_category[future]
                    try:
                        success = future.result()
                        results[category] = success
                        if not success:
                            overall_success = False
                            logger.warning(f"Category {category} processing had failures")
                        else:
                            logger.info(f"Category {category} processing completed successfully")
                    except concurrent.futures.TimeoutError:
                        overall_success = False
                        logger.error(f"Timeout processing category {category}")
                        results[category] = False
                    except Exception as e:
                        overall_success = False
                        logger.error(f"Error processing category {category}: {str(e)}")
                        logger.error(traceback.format_exc())
                        results[category] = False
            
            overall_duration = time.time() - overall_start_time
            
            # Final summary
            logger.info(f"\n{'#' * 60}")
            logger.info(f"ALL CATEGORIES COMPLETED in {overall_duration:.2f} seconds")
            
            # Print results for each category
            for cat, success in results.items():
                logger.info(f"- {cat}: {'SUCCESS' if success else 'FAILURE'}")
                
            logger.info(f"Overall status: {'SUCCESS' if overall_success else 'PARTIAL FAILURE'}")
            logger.info(f"{'#' * 60}")
            sys.exit(0 if overall_success else 1)
    else:
        # In test mode, show options and get input
        print("\nAvailable categories:")
        print(", ".join(categories))
        print()
        
        # Get category from user
        category = input("Enter category to test: ").strip().lower()
        while category not in categories:
            print(f"Invalid category. Please choose from: {', '.join(categories)}")
            category = input("Enter category to test: ").strip().lower()
        
        print("\nAvailable crawlers:")
        print(", ".join(crawlers))
        print()
        
        # Get and validate crawler name case-insensitively
        crawler_name = input("Enter crawler name to test: ").strip().lower()
        while crawler_name not in crawlers:
            print(f"Invalid crawler. Please choose from: {', '.join(crawlers)}")
            crawler_name = input("Enter crawler name to test: ").strip().lower()
        
        logger.info(f"Starting test crawl for {crawler_name} - {category}")
        success = test_crawler(crawler_name, category)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
