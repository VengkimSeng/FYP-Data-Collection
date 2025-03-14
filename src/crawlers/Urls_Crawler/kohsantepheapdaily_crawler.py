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
    
    while (max_attempts == -1 or same_height_count < max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
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
        
        # Pass max_scroll parameter
        scroll_page(driver, max_attempts=max_scroll)
        page_urls = extract_urls(driver.page_source, url)
        urls.update(page_urls)
        
        # Save URLs if url_manager is provided
        if url_manager and page_urls:
            url_manager.add_urls(category, page_urls)
            logger.info(f"Added {len(page_urls)} URLs using url_manager")
            
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
    finally:
        driver.quit()
        
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

