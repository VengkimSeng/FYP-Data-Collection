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

def crawl_category(base_url: str, category: str, url_manager: URLManager) -> Set[str]:
    """Crawl a category completely."""
    all_urls = set()
    driver = setup_chrome_driver(headless=True, disable_images=True)
    
    try:
        # Crawl pages until we have enough URLs or no new ones found
        page = 1
        consecutive_empty = 0
        max_empty_pages = 3
        
        while consecutive_empty < max_empty_pages and len(all_urls) < 500:
            page_url = f"{base_url}?page={page}"
            logger.info(f"Crawling page {page}: {page_url}")
            
            if html := fetch_page(driver, page_url):
                new_urls = extract_urls(html, base_url)
                previous_count = len(all_urls)
                all_urls.update(new_urls)
                
                # Track if we found new URLs
                if len(all_urls) > previous_count:
                    consecutive_empty = 0
                    logger.info(f"Found {len(new_urls)} new URLs on page {page}")
                else:
                    consecutive_empty += 1
                    logger.info(f"No new URLs on page {page}")
            else:
                consecutive_empty += 1
                
            page += 1
            time.sleep(2)  # Polite delay between pages
            
        # Store all URLs at once
        if all_urls:
            added = url_manager.add_urls(category, all_urls)
            logger.info(f"Stored {added} URLs for category {category}")
            
    except Exception as e:
        logger.error(f"Error crawling category {base_url}: {e}")
    finally:
        driver.quit()
        
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
