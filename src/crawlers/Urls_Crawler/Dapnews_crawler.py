import os
import sys
from selenium import webdriver
import time
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(project_root)

from src.utils.chrome_setup import setup_chrome_driver
from src.utils.log_utils import get_crawler_logger
from src.crawlers.url_manager import URLManager

logger = get_crawler_logger('dapnews')

def fetch_page(driver: webdriver.Chrome, url: str) -> str:
    """Fetch and scroll a single page."""
    driver.get(url)
    # Scroll logic
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    return driver.page_source

def extract_urls(html: str, base_url: str, category: str) -> set:
    """
    Extract article URLs from page that match the specific category pattern.
    
    Args:
        html: Page HTML content
        base_url: Base URL for resolving relative URLs
        category: Category being crawled
    """
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Add debugging 
    logger.debug(f"Extracting URLs from HTML ({len(html)} bytes)")
    
    # More relaxed matching approach
    category_path = category.lower()
    
    # First try specific matches
    for a_tag in soup.find_all("a", href=True):
        url = urljoin(base_url, a_tag["href"])
        
        # Match URLs with category pattern and number pattern
        if f"/{category_path}/" in url.lower() and re.search(r'/\d{4}/\d{2}/\d{2}/\d+/$', url):
            urls.add(url)
    
    # If no URLs found with strict pattern, try more relaxed matching
    if not urls:
        logger.info("No strict matches found, trying relaxed matching")
        for a_tag in soup.find_all("a", href=True):
            url = urljoin(base_url, a_tag["href"])
            
            # More relaxed pattern matching
            if all([
                f"/{category_path}/" in url.lower(),
                not url.endswith('/'),  # Skip category index pages
                not url.endswith('.jpg'),
                not url.endswith('.png'),
                not re.search(r'/page/\d+/?$', url),  # Skip pagination URLs
                "dap-news.com" in url,  # Ensure it's from the right domain
            ]):
                urls.add(url)
    
    logger.info(f"Found {len(urls)} URLs for category '{category}'")
    if not urls:
        # Log the page title for debugging
        page_title = soup.title.text if soup.title else "No title"
        logger.debug(f"Page title: {page_title}")
        
        # Log a few links found on the page for debugging
        all_links = [urljoin(base_url, a['href']) for a in soup.find_all("a", href=True)][:10]
        logger.debug(f"Sample links on page: {all_links}")
            
    return urls

def crawl_category(source_url: str, category: str, url_manager=None, max_pages: int = -1) -> set:
    """
    Crawl a category and return all article URLs.
    
    Args:
        source_url: The base URL for the category
        category: Category being crawled
        url_manager: Optional URLManager instance
        max_pages: Maximum number of pages to crawl (-1 for unlimited)
    
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
        # First try the main category page
        logger.info(f"Crawling main page for {category}: {source_url}")
        driver.get(source_url)
        time.sleep(5)  # Initial load
        
        main_urls = extract_urls(driver.page_source, source_url, category)
        if main_urls:
            all_urls.update(main_urls)
            if url_manager:
                added = url_manager.add_urls(category, main_urls)
                logger.info(f"Added {added} URLs from main page")
        
        # Then try pagination if needed
        page = 2  # Start from page 2
        consecutive_empty = 0
        
        # For unlimited pages, use a large number that's effectively infinite
        max_iter = 10000 if max_pages == -1 else max_pages
        
        while page <= max_iter and consecutive_empty < 2:
            # Ensure the source_url has a trailing slash for consistent pagination
            # Example: https://dap-news.com/category/sport/page/2/
            base_url = source_url if source_url.endswith('/') else f"{source_url}/"
            page_url = f"{base_url}page/{page}/"
            logger.info(f"Crawling {category} page {page}: {page_url}")
            
            driver.get(page_url)
            time.sleep(5)  # Wait for page to load
            
            page_urls = extract_urls(driver.page_source, source_url, category)
            
            if page_urls:
                consecutive_empty = 0
                all_urls.update(page_urls)
                if url_manager:
                    added = url_manager.add_urls(category, page_urls)
                    logger.info(f"Added {added} new URLs on page {page}")
                logger.info(f"Found {len(page_urls)} URLs on page {page}")
            else:
                consecutive_empty += 1
                logger.info(f"No URLs found on page {page} (attempt {consecutive_empty}/2)")
                
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

def main():
    """Main entry point for Dapnews crawler."""
    url_manager = URLManager("output/urls", "dapnews")
    
    try:
        for category in url_manager.category_sources:
            sources = url_manager.get_sources_for_category(category, "dapnews")
            if sources:
                for url in sources:
                    logger.info(f"Crawling category {category} from {url}")
                    urls = crawl_category(url, category, url_manager)
                    logger.info(f"Added {len(urls)} URLs for category {category}")
    finally:
        # Save final results
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()