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
        max_attempts: Maximum number of attempts with no new content before stopping
    """
    last_height = 0
    same_height_count = 0
    
    while same_height_count < max_attempts:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for content to load
        
        # Get new height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Check if height changed
        if new_height == last_height:
            same_height_count += 1
            logger.debug(f"No new content loaded (attempt {same_height_count}/{max_attempts})")
            
            # Try scrolling up and down to trigger lazy loading
            if same_height_count >= 2:
                logger.debug("Trying scroll up/down to trigger content load")
                driver.execute_script(f"window.scrollTo(0, {new_height * 0.5});")  # Scroll to middle
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Back to bottom
                time.sleep(1)
        else:
            same_height_count = 0  # Reset counter when height changes
            logger.debug(f"New content loaded (height: {new_height})")
            
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

def crawl_category(url, category, max_scroll=100000):
    """
    Crawl a single category page.
    
    Args:
        url: URL to crawl
        category: Category name
        max_scroll: Maximum scroll attempts (default: 10)
    """
    urls = set()
    driver = setup_driver()
    
    try:
        logger.info(f"Crawling {category}: {url}")
        driver.get(url)
        time.sleep(5)  # Initial load
        
        # Pass max_scroll parameter
        scroll_page(driver, max_attempts=max_scroll)
        urls.update(extract_urls(driver.page_source, url))
            
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
                    urls = crawl_category(url, category)
                    added = url_manager.add_urls(category, urls)
                    logger.info(f"Added {added} URLs for {category}")
            
    finally:
        # Save results
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()

