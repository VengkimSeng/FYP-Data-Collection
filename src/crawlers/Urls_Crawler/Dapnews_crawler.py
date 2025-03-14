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

def extract_urls(html: str, base_url: str) -> set:
    """Extract article URLs from page."""
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    article_pattern = re.compile(r'^https://dap-news\.com/([^/]+)/(\d{4})/(\d{2})/(\d{2})/(\d+)/$')
    
    for a_tag in soup.find_all("a", href=True):
        url = urljoin(base_url, a_tag["href"])
        if article_pattern.match(url):
            urls.add(url)
    return urls

def crawl_category(source_url: str, category: str, url_manager=None, max_pages: int = 500) -> set:
    """
    Crawl a category and return all article URLs.
    
    Args:
        source_url: The base URL for the category
        category: Category being crawled
        url_manager: Optional URLManager instance
        max_pages: Maximum number of pages to crawl
    
    Returns:
        Set of collected URLs
    """
    urls = set()
    driver = setup_chrome_driver()
    
    try:
        page = 1
        while page <= max_pages:
            url = f"{source_url}page/{page}/" if page > 1 else source_url
            logger.info(f"Crawling {category} page {page}")
            
            driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            # Extract URLs from current page
            soup = BeautifulSoup(driver.page_source, "html.parser")
            new_urls = extract_urls(driver.page_source, source_url)
            
            if not new_urls:
                break
                
            urls.update(new_urls)
            if url_manager:
                url_manager.add_urls(category, new_urls)
            logger.info(f"Found {len(new_urls)} URLs on page {page}")
            
            page += 1
            if len(urls) >= 500:
                break
                
    finally:
        driver.quit()
    
    return urls

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