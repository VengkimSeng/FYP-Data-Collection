import os
import sys
import time
from typing import Set, Optional
from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Initialize logger
logger = get_crawler_logger('btv')

def fetch_page(driver: webdriver.Chrome, url: str) -> Optional[str]:
    """Fetch and scroll a single page."""
    try:
        driver.get(url)
        time.sleep(3)  # Initial load wait
        
        # Simple scroll logic
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(3):  # Limit scrolls
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        return driver.page_source
    except Exception as e:
        logger.error(f"Error fetching page {url}: {e}")
        return None

def extract_urls(html: str, base_url: str) -> Set[str]:
    """Extract article URLs from page HTML."""
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Find article links
    for a_tag in soup.select("article a, .post-title a, a[href*='/article/']"):
        if href := a_tag.get("href"):
            url = urljoin(base_url, href)
            if "/article/" in url:
                # Clean URL format
                try:
                    article_id = url.split("/article/")[1].split("/")[0].split("?")[0]
                    urls.add(f"https://btv.com.kh/article/{article_id}")
                except IndexError:
                    continue
    
    return urls

def crawl_category(source_url: str, category: str, url_manager=None, max_pages: int = 500) -> Set[str]:
    """
    Crawl a category from source URL.
    
    Args:
        source_url: The base URL for the category
        category: Category being crawled
        url_manager: Optional URLManager instance
        max_pages: Maximum number of pages to crawl (default: 500)
    
    Returns:
        Set of collected URLs
    """
    all_urls = set()
    current_page = 1
    empty_pages_count = 0  # Track consecutive empty pages
    
    while current_page <= max_pages:
        try:
            # Use query parameter for pagination instead of path
            page_url = f"{source_url}{'&' if '?' in source_url else '?'}page={current_page}"
            logger.info(f"Crawling page {current_page}: {page_url}")
            
            # Setup driver and fetch page
            driver = setup_chrome_driver()
            try:
                html = fetch_page(driver, page_url)
                if not html:
                    logger.warning(f"Failed to fetch page {current_page}")
                    empty_pages_count += 1
                    if empty_pages_count >= 2:  # Stop after 2 consecutive empty pages
                        logger.info("Multiple empty pages detected, stopping crawl")
                        break
                    continue
                
                # Extract URLs from the page
                page_urls = extract_urls(html, page_url)
                
                if page_urls:
                    all_urls.update(page_urls)
                    if url_manager:
                        url_manager.add_urls(category, page_urls)
                    logger.info(f"Found {len(page_urls)} URLs on page {current_page}")
                    empty_pages_count = 0
                else:
                    empty_pages_count += 1
                    if empty_pages_count >= 2:  # Stop after 2 consecutive empty pages
                        logger.info("No more content found after multiple attempts, stopping crawl")
                        break
                    logger.info(f"No URLs found on page {current_page}")
                
            finally:
                driver.quit()
            
            current_page += 1
            time.sleep(2)  # Add small delay between pages
            
        except Exception as e:
            logger.error(f"Error crawling page {current_page}: {e}")
            empty_pages_count += 1
            if empty_pages_count >= 2:
                logger.info("Multiple errors encountered, stopping crawl")
                break
    
    logger.info(f"Completed crawling after {current_page-1} pages with {len(all_urls)} total URLs")
    return all_urls

def main():
    """Main entry point for the BTV crawler."""
    url_manager = URLManager("output/urls", "btv")
    
    # Process each category
    for category in url_manager.category_sources:
        sources = url_manager.get_sources_for_category(category, "btv")
        if not sources:
            continue
            
        for source_url in sources:
            logger.info(f"Starting crawl of {category} from {source_url}")
            urls = crawl_category(source_url, category, url_manager)
            logger.info(f"Found {len(urls)} URLs for {category}")
    
    # Save everything at the end
    results = url_manager.save_final_results()
    logger.info(f"Crawling complete. Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()
