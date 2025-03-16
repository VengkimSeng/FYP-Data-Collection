import warnings
warnings.filterwarnings('ignore', message='.*urllib3 v2 only supports OpenSSL 1.1.1.*')

from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

logger = get_crawler_logger('kohsantepheap')

# Remove CATEGORIES dictionary since we'll use url_manager

def setup_driver():
    """Initialize WebDriver with basic settings"""
    return setup_chrome_driver(
        headless=True,
        disable_images=True,
        random_user_agent=True
    )

def scroll_page(driver, max_attempts=5):
    """
    Scroll page until no new content is loaded.
    
    Args:
        driver: WebDriver instance
        max_attempts: Maximum attempts without new content before stopping.
                     Use -1 for unlimited scrolling until no new content
    """
    last_height = 0
    same_height_count = 0
    total_scrolls = 0
    
    # Convert -1 to a large number for unlimited scrolling
    effective_max = 10000 if max_attempts == -1 else max_attempts
    
    # Reduce wait time to avoid timeouts
    scroll_wait = 1  # Reduced from 2 seconds to 1 second
    
    while (same_height_count < 3 and (max_attempts == -1 or total_scrolls < effective_max)):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_wait)  # Reduced wait time
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            same_height_count += 1
            if same_height_count >= 3:  # Always stop after 3 consecutive no-changes
                logger.info(f"No new content after {total_scrolls} scrolls")
                break
                
            # Try scroll up/down to trigger lazy loading
            logger.debug("Trying scroll up/down to trigger content load")
            driver.execute_script(f"window.scrollTo(0, {new_height * 0.5});")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        else:
            same_height_count = 0
            total_scrolls += 1
            logger.debug(f"New content loaded at scroll {total_scrolls} (height: {new_height})")
            
        last_height = new_height

def extract_urls(html, base_url):
    """Extract article URLs from page"""
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Find all potential article links
    for a_tag in soup.find_all("a", href=True):
        url = urljoin(base_url, a_tag["href"])
        if '/article/' in url or url.endswith('.html'):
            urls.add(url)
            
    return urls

def crawl_category(url: str, category: str, url_manager=None, max_scroll: int = -1) -> set:
    """
    Crawl a single category page.
    
    Args:
        url: URL to crawl
        category: Category name
        url_manager: Optional URLManager instance for saving URLs
        max_scroll: Maximum scroll attempts (-1 for unlimited scrolling)
    
    Returns:
        Set of collected URLs
    """
    urls = set()
    driver = setup_driver()
    
    try:
        logger.info(f"Crawling {category}: {url}")
        driver.get(url)
        time.sleep(5)  # Initial load
        
        # Pass max_scroll parameter directly (already handles -1)
        scroll_page(driver, max_attempts=max_scroll)
        initial_page_urls = extract_urls(driver.page_source, url)
        urls.update(initial_page_urls)
        
        # Save URLs if url_manager is provided
        if url_manager and initial_page_urls:
            added_count = url_manager.add_urls(category, initial_page_urls)
            logger.info(f"Added {added_count} URLs using url_manager from initial page")
            
        # If pagination is available, follow it
        page = 2
        consecutive_no_new_urls = 0
        max_consecutive_no_new = 2
        
        while consecutive_no_new_urls < max_consecutive_no_new:
            try:
                # Construct page URL - format depends on the site
                # Try both formats common for pagination
                page_url = f"{url}/page/{page}"
                logger.info(f"Trying pagination: {page_url}")
                
                driver.get(page_url)
                time.sleep(3)
                
                # Check if page loaded successfully
                if "404" in driver.title or "not found" in driver.title.lower():
                    logger.info(f"Pagination ended at page {page-1}")
                    break
                    
                scroll_page(driver, max_attempts=max_scroll)
                page_urls = extract_urls(driver.page_source, page_url)
                
                # Check for new unique URLs
                old_count = len(urls)
                urls.update(page_urls)
                new_unique_count = len(urls) - old_count
                
                if new_unique_count > 0:
                    consecutive_no_new_urls = 0
                    logger.info(f"Found {new_unique_count} new unique URLs on page {page}")
                    
                    if url_manager:
                        added_count = url_manager.add_urls(category, page_urls)
                        logger.info(f"Added {added_count} URLs using url_manager from page {page}")
                else:
                    consecutive_no_new_urls += 1
                    logger.info(f"No new unique URLs on page {page} (attempt {consecutive_no_new_urls}/{max_consecutive_no_new})")
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error processing pagination: {e}")
                break
                
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
    finally:
        driver.quit()
        
    logger.info(f"Completed crawling {category} with {len(urls)} total unique URLs")
    return urls

def main():
    """Main crawler entry point"""
    url_manager = URLManager("output/urls", "kohsantepheap")
    
    try:
        # Use categories from url_manager
        for category in url_manager.category_sources:
            sources = url_manager.get_sources_for_category(category, "kohsantepheap")
            if sources:
                for url in sources:
                    urls = crawl_category(url, category, url_manager=url_manager)
                    added = url_manager.add_urls(category, urls)
                    logger.info(f"Added {added} URLs for {category}")
            
    finally:
        # Save results
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()

