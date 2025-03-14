import os
import time
import random
import warnings
import sys
from urllib.parse import urlparse
from typing import Set
from selenium.webdriver.common.by import By

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver, setup_chrome_options
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Suppress warnings
warnings.simplefilter('ignore')

logger = get_crawler_logger('rfa')

def setup_driver():
    """Setup WebDriver with standard configuration."""
    options = setup_chrome_options(
        headless=True,
        disable_images=True,
        random_user_agent=True,
        additional_arguments=["--ignore-certificate-errors"]
    )
    return setup_chrome_driver(options=options)

def filter_article_urls(urls, base_domain, category):
    """Filter URLs to keep only article pages from the base domain."""
    filtered = []
    for url in urls:
        if url and isinstance(url, str):
            parsed = urlparse(url)
            # Keep only URLs from the same domain
            if parsed.netloc and base_domain in parsed.netloc:
                # Look for patterns that suggest it's an article page
                path = parsed.path.lower()
                # Make sure it's from the specific category
                if f"/news/{category}/" in path and path.endswith(".html"):
                    filtered.append(url)
    logger.info(f"Filtered {len(filtered)} URLs out of {len(urls)} raw URLs for {category}")
    return filtered

def crawl_category(url: str, category: str, max_pages: int = -1) -> Set[str]:
    """
    Crawl a category and return article URLs.
    
    Args:
        url: Starting URL 
        category: Category being crawled
        max_pages: Maximum pages to crawl (-1 for unlimited)
    """
    urls = set()
    driver = setup_driver()
    page = 1
    consecutive_empty = 0
    base_domain = urlparse(url).netloc
    
    try:
        current_url = url
        while (max_pages == -1 or page <= max_pages) and consecutive_empty < 3:
            logger.info(f"Processing page {page}: {current_url}")
            
            try:
                driver.get(current_url)
                time.sleep(random.uniform(2, 4))
                
                # Get all links and filter them
                links = driver.find_elements(By.TAG_NAME, "a")
                page_urls = [link.get_attribute("href") for link in links]
                new_urls = filter_article_urls(page_urls, base_domain, category)
                
                if new_urls:
                    consecutive_empty = 0
                    urls.update(new_urls)
                    logger.info(f"Found {len(new_urls)} new URLs (Total: {len(urls)})")
                else:
                    consecutive_empty += 1
                    logger.info(f"No new URLs found (attempt {consecutive_empty}/3)")
                
                # Move to next page
                page += 1
                current_url = url + f"?b_start:int={(page-1)*15}"
                
            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                consecutive_empty += 1
                
    finally:
        driver.quit()
        
    return urls

def main():
    """Main entry point."""
    url_manager = URLManager("output/urls", "rfanews")
    
    try:
        for category in url_manager.category_sources:
            sources = url_manager.get_sources_for_category(category, "rfa")
            if sources:
                for url in sources:
                    logger.info(f"Crawling {category} from {url}")
                    urls = crawl_category(url, category)
                    if urls:
                        added = url_manager.add_urls(category, urls)
                        logger.info(f"Added {added} URLs for {category}")
    finally:
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()
