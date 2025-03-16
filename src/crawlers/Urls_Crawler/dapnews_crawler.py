import os
import sys
import time
import json
import importlib.util
from typing import Dict, Set, List
import traceback

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Initialize logger
logger = get_crawler_logger('dapnews_crawler')

def fetch_page(driver, url):
    """Fetch the page content using the provided driver."""
    try:
        driver.get(url)
        time.sleep(5)  # Wait for page to load
        return driver.page_source
    except Exception as e:
        logger.error(f"Error fetching page {url}: {e}")
        return None

def extract_urls(html, base_url, category):
    """Extract URLs from the HTML content."""
    # Placeholder implementation, replace with actual URL extraction logic
    return set()

def crawl_category(source_url: str, category: str, url_manager=None, max_pages: int = -1) -> set:
    """
    Crawl a category starting from the source URL.
    
    Args:
        source_url: URL to start crawling from
        category: Category being crawled
        url_manager: Optional URLManager instance
        max_pages: Maximum pages to crawl (-1 for unlimited)
    
    Returns:
        Set of collected URLs
    """
    all_urls = set()
    driver = setup_chrome_driver(
        headless=True,
        disable_images=True,
        random_user_agent=True
    )
    
    try:
        # Process main page first
        logger.info(f"Crawling main page: {source_url}")
        html = fetch_page(driver, source_url)
        
        if html:
            logger.info(f"Main page fetched successfully ({len(html)} bytes)")
            page_urls = extract_urls(html, source_url, category)
            
            if page_urls:
                all_urls.update(page_urls)
                if url_manager:
                    added = url_manager.add_urls(category, page_urls)
                    logger.info(f"Added {added} URLs from main page")
        
        # Then try pagination if needed
        page = 2  # Start from page 2
        consecutive_empty = 0
        max_consecutive_empty = 2
        consecutive_no_new_urls = 0
        max_consecutive_no_new = 2
        
        # For unlimited pages, use a large number that's effectively infinite
        max_iter = 10000 if max_pages == -1 else max_pages
        
        while (page <= max_iter and 
               consecutive_empty < max_consecutive_empty and 
               consecutive_no_new_urls < max_consecutive_no_new):
            # Ensure the source_url has a trailing slash for consistent pagination
            # Example: https://dap-news.com/category/sport/page/2/
            base_url = source_url if source_url.endswith('/') else f"{source_url}/"
            page_url = f"{base_url}page/{page}/"
            logger.info(f"Crawling {category} page {page}: {page_url}")
            
            driver.get(page_url)
            time.sleep(5)  # Wait for page to load
            
            page_urls = extract_urls(driver.page_source, source_url, category)
            
            # Check if we got any new unique URLs
            old_count = len(all_urls)
            all_urls.update(page_urls)
            new_unique_count = len(all_urls) - old_count
            
            if new_unique_count > 0:
                consecutive_empty = 0
                consecutive_no_new_urls = 0
                if url_manager:
                    added = url_manager.add_urls(category, page_urls)
                    logger.info(f"Added {added} new URLs on page {page}, {new_unique_count} are unique")
                logger.info(f"Found {len(page_urls)} URLs on page {page}, {new_unique_count} are unique")
            else:
                consecutive_no_new_urls += 1
                logger.info(f"No new unique URLs on page {page} (attempt {consecutive_no_new_urls}/{max_consecutive_no_new})")
                
                if page_urls:
                    # We found URLs but they were duplicates
                    logger.info(f"Found {len(page_urls)} URLs on page {page}, but all were duplicates")
                else:
                    consecutive_empty += 1
                    logger.info(f"No URLs found on page {page} (attempt {consecutive_empty}/{max_consecutive_empty})")
                
            page += 1
            
            # Circuit breaker for too many URLs
            if len(all_urls) >= 500:
                logger.info("Reached URL limit, stopping crawl")
                break
                
    except Exception as e:
        logger.error(f"Error during crawl: {e}")
    finally:
        driver.quit()
    
    logger.info(f"Completed crawling {category} with {len(all_urls)} total URLs")
    return all_urls