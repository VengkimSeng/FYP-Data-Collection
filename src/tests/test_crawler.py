import os
import sys
import time
import json
import importlib.util
from typing import Dict, Set

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Initialize logger
logger = get_crawler_logger('test_crawler')

# Try to rename the crawler file if it exists in old format
try:
    btv_old_path = os.path.join(project_root, "src", "crawlers", "Urls_Crawler", "BTV_crawler.py")
    btv_new_path = os.path.join(project_root, "src", "crawlers", "Urls_Crawler", "btv_crawler.py")
    if os.path.exists(btv_old_path) and not os.path.exists(btv_new_path):
        os.rename(btv_old_path, btv_new_path)
        logger.info("Renamed BTV_crawler.py to btv_crawler.py")
except Exception as e:
    logger.debug(f"File renaming not needed or failed: {e}")

def import_crawler_module(crawler_name: str):
    """Import crawler module dynamically."""
    try:
        # Construct the full path to the crawler module
        module_path = os.path.join(
            project_root,
            "src",
            "crawlers",
            "Urls_Crawler",
            f"{crawler_name}_crawler.py"
        )
        
        if not os.path.exists(module_path):
            logger.error(f"Crawler module not found at: {module_path}")
            return None
            
        # Import the module using importlib
        spec = importlib.util.spec_from_file_location(
            f"{crawler_name}_crawler",
            module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module
        
    except Exception as e:
        logger.error(f"Error importing crawler module: {e}")
        return None

def test_single_category(crawler_name: str, category: str, source_url: str) -> Set[str]:
    """Test crawling a single category from one source URL."""
    logger.info(f"Testing {crawler_name} crawler for {category} at {source_url}")
    
    # Initialize URL manager for testing
    test_output_dir = "output/test_urls"
    url_manager = URLManager(test_output_dir, crawler_name)
    
    try:
        # Import the crawler module
        crawler_module = import_crawler_module(crawler_name)
        if not crawler_module:
            logger.error(f"Failed to import {crawler_name} crawler module")
            return set()
        
        # Call the crawler's main function
        if hasattr(crawler_module, 'crawl_category'):
            logger.info("Calling crawl_category function...")
            try:
                # For BTV crawler, limit to 10 pages
                if crawler_name.lower() == 'btv':
                    urls = crawler_module.crawl_category(source_url, category, url_manager, max_pages=10)
                else:
                    urls = crawler_module.crawl_category(source_url, category, url_manager)
            except TypeError as e:
                # If max_pages is not supported, fall back to standard call
                logger.warning(f"max_pages not supported by {crawler_name} crawler, using default implementation")
                urls = crawler_module.crawl_category(source_url, category, url_manager)
<<<<<<< HEAD
                
=======
            except TypeError as e:
                # If max_pages is not supported, fall back to standard call
                logger.warning(f"max_pages not supported by {crawler_name} crawler, using default implementation")
                urls = crawler_module.crawl_category(source_url, category, url_manager)
>>>>>>> d8c146afee34cddaffe22415ad32a2f9f564623d
            logger.info(f"Found {len(urls)} URLs")
            return urls
        else:
            logger.error(f"Crawler module does not have crawl_category function")
            return set()
            
    except Exception as e:
        logger.error(f"Error testing crawler: {e}", exc_info=True)
        return set()

def load_test_config() -> Dict:
    """Load test configuration from sources.json."""
    config_path = os.path.join(project_root, "src", "config", "sources.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading test config: {e}")
        return {}

def main():
    """Main test function."""
    # Load test configuration
    config = load_test_config()
    if not config:
        logger.error("Failed to load test configuration")
        return
        
    # Ask user which crawler and category to test
    print("\nAvailable categories and sources:")
    for category, sources in config.items():
        print(f"\n{category}:")
        if isinstance(sources, dict):
            for site, url in sources.items():
                print(f"  - {site}: {url}")
        elif isinstance(sources, list):
            for url in sources:
                print(f"  - {url}")

    # Get user input
    crawler_name = input("\nEnter crawler name to test (e.g., btv, sabay, postkhmer): ").lower()
    category = input("Enter category to test: ").lower()
    
    # Find source URL for the selected crawler and category
    source_url = None
    if category in config:
        sources = config[category]
        if isinstance(sources, dict):
            source_url = sources.get(crawler_name)
        elif isinstance(sources, list):
            # For lists of URLs, try to find one matching the crawler
            for url in sources:
                if crawler_name in url:
                    source_url = url
                    break
    
    if not source_url:
        logger.error(f"No source URL found for {crawler_name} in category {category}")
        return
        
    # Run the test
    logger.info(f"Starting test crawl for {crawler_name} - {category}")
    start_time = time.time()
    
    urls = test_single_category(crawler_name, category, source_url)
    
    duration = time.time() - start_time
    logger.info(f"\nTest completed in {duration:.2f} seconds")
    logger.info(f"URLs collected: {len(urls)}")
    
    # Save test results
    if urls:
        output_dir = "output/test_results"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"test_{crawler_name}_{category}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(list(urls), f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
