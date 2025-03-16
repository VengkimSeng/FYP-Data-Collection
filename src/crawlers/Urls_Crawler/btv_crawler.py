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

def crawl_category(source_url: str, category: str, url_manager=None, max_pages: int = -1) -> Set[str]:
    """
    Crawl a category from source URL.
    
    Args:
        source_url: The base URL for the category
        category: Category being crawled
        url_manager: Optional URLManager instance
        max_pages: Maximum number of pages to crawl (default: -1 for unlimited)
    
    Returns:
        Set of collected URLs
    """
    all_urls = set()
    current_page = 1
    empty_pages_count = 0  # Track consecutive empty pages
    max_consecutive_empty = 2  # Stop after this many consecutive empty pages
    consecutive_no_new_urls = 0
    max_consecutive_no_new = 2  # Stop after this many pages with no new URLs
    
    # First try the direct URL (important!)
    logger.info(f"Starting crawl of category '{category}' from URL: {source_url}")
    driver = setup_chrome_driver(
        headless=True, 
        disable_images=True,
        random_user_agent=True
    )
    
    try:
        # Process the first page
        logger.info(f"Crawling main page: {source_url}")
        html = fetch_page(driver, source_url)
        
        if html:
            logger.info(f"Successfully fetched main page HTML ({len(html)} bytes)")
            page_urls = extract_urls(html, source_url)
            
            if page_urls:
                all_urls.update(page_urls)
                logger.info(f"Found {len(page_urls)} URLs on main page")
                # Save URLs from main page immediately and log results
                if url_manager:
                    added_count = url_manager.add_urls(category, page_urls)
                    logger.info(f"Added {added_count} new URLs from main page to URL manager")
                    url_manager.save_to_file(category)  # Force save to file immediately
            else:
                logger.warning("No URLs found on main page")
                empty_pages_count += 1
        else:
            logger.error("Failed to fetch main page HTML")
            empty_pages_count += 1
    except Exception as e:
        logger.error(f"Error on main page: {e}")
        empty_pages_count += 1
    finally:
        driver.quit()
    
    # Continue with pagination starting from page 2
    current_page = 2  # Start from page 2
    
    # For unlimited pages, use a large number that's effectively infinite
    max_iter = 10000 if max_pages == -1 else max_pages
    
    while (current_page <= max_iter and 
           empty_pages_count < max_consecutive_empty and 
           consecutive_no_new_urls < max_consecutive_no_new):
        try:
            # Use query parameter for pagination - example: https://btv.com.kh/category/sport?page=2
            page_url = f"{source_url}{'&' if '?' in source_url else '?'}page={current_page}"
            logger.info(f"Crawling page {current_page}: {page_url}")
            
            # Setup driver and fetch page
            driver = setup_chrome_driver()
            try:
                html = fetch_page(driver, page_url)
                if not html:
                    logger.warning(f"Failed to fetch page {current_page}")
                    empty_pages_count += 1
                    if empty_pages_count >= max_consecutive_empty:
                        logger.info("Multiple empty pages detected, stopping crawl")
                        break
                    continue
                
                # Extract URLs from the page
                page_urls = extract_urls(html, page_url)
                
                # Check if we found new unique URLs
                old_count = len(all_urls)
                all_urls.update(page_urls)
                new_unique_count = len(all_urls) - old_count
                
                if new_unique_count > 0:
                    logger.info(f"Found {len(page_urls)} URLs, {new_unique_count} are new unique")
                    empty_pages_count = 0
                    consecutive_no_new_urls = 0
                    # Save URLs immediately and log results
                    if url_manager:
                        added_count = url_manager.add_urls(category, page_urls)
                        logger.info(f"Added {added_count} new URLs from page {current_page} to URL manager")
                        url_manager.save_to_file(category)  # Force save to file immediately
                else:
                    consecutive_no_new_urls += 1
                    logger.info(f"No new unique URLs on page {current_page} (attempt {consecutive_no_new_urls}/{max_consecutive_no_new})")
                    if consecutive_no_new_urls >= max_consecutive_no_new:
                        logger.info("No more new URLs found after multiple attempts, stopping crawl")
                        break
            finally:
                driver.quit()
            
            current_page += 1
            time.sleep(2)  # Add small delay between pages
            
        except Exception as e:
            logger.error(f"Error crawling page {current_page}: {e}")
            empty_pages_count += 1
            if empty_pages_count >= max_consecutive_empty:
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
