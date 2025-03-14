import os
import sys
import time# idaijasd
import json
import importlib.util
from typing import Dict, Set, List

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
        # Standardize crawler name format
        crawler_name = crawler_name.lower()
        module_name = f"{crawler_name}_crawler"
        
        module_path = os.path.join(
            project_root,
            "src", 
            "crawlers",
            "Urls_Crawler",
            f"{module_name}.py"
        )
        
        if not os.path.exists(module_path):
            logger.error(f"Crawler module not found at: {module_path}")
            return None
            
        # Import the module using spec
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module
    except Exception as e:
        logger.error(f"Failed to import {crawler_name} module: {e}")
        return None

def test_crawler(crawler_name: str, category: str, max_urls: int = 5):
    """Test a specific crawler for a category."""
    logger.info(f"Testing {crawler_name} crawler for {category}")
    
    # Initialize URL manager for testing
    url_manager = URLManager("output/test_urls", crawler_name)
    
    # Get source URLs for this crawler/category
    sources = url_manager.get_sources_for_category(category, crawler_name)
    if not sources:
        logger.error(f"No source URLs found for {crawler_name} - {category}")
        return False
        
    # Import the crawler module
    crawler_module = import_crawler_module(crawler_name)
    if not crawler_module:
        logger.error(f"Failed to import {crawler_name} crawler module")
        return False
    
    start_time = time.time()
    urls_collected = 0
    
    try:
        for source_url in sources:
            logger.info(f"Testing {crawler_name} crawler for {category} at {source_url}")
            # Use crawl_category function if it exists
            if hasattr(crawler_module, 'crawl_category'):
                # Pass max_pages=10 for testing
                urls = crawler_module.crawl_category(source_url, category, max_pages=10)
            else:
                logger.error("Crawler module missing crawl_category function")
                return False
            
            if urls:
                urls_collected += len(urls)
                logger.info(f"Found {len(urls)} URLs")
            
            if urls_collected >= max_urls:
                break
                
    except Exception as e:
        logger.error(f"Error testing crawler: {e}")
        return False
        
    duration = time.time() - start_time
    logger.info(f"\nTest completed in {duration:.2f} seconds")
    logger.info(f"URLs collected: {urls_collected}")
    
    return urls_collected > 0

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
            crawler_name = file.replace("_crawler.py", "")
            crawlers.append(crawler_name)
    return sorted(crawlers)

def get_available_categories(url_manager: URLManager) -> List[str]:
    """Get list of available categories."""
    return sorted(url_manager.category_sources.keys())

def main():
    """Main test function."""
    url_manager = URLManager("output/test_urls", "test")
    
    # Show available options
    crawlers = get_available_crawlers()
    categories = get_available_categories(url_manager)
    
    print("\nAvailable crawlers:")
    print(", ".join(crawlers))
    print("\nAvailable categories:")
    print(", ".join(categories))
    print()
    
    # Get crawler name from user
    crawler_name = input("Enter crawler name to test: ").strip().lower()
    while crawler_name not in crawlers:
        print(f"Invalid crawler. Please choose from: {', '.join(crawlers)}")
        crawler_name = input("Enter crawler name to test: ").strip().lower()
    
    # Get category from user
    category = input("Enter category to test: ").strip().lower()
    while category not in categories:
        print(f"Invalid category. Please choose from: {', '.join(categories)}")
        category = input("Enter category to test: ").strip().lower()
    
    logger.info(f"Starting test crawl for {crawler_name} - {category}")
    success = test_crawler(crawler_name, category)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
