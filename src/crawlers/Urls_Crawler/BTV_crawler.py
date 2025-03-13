from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
import os
import logging
import time
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Optional

# Add parent directory to path to import chrome_setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Fix SSL issues
ssl._create_default_https_context = ssl._create_unverified_context

def setup_selenium() -> webdriver.Chrome:
    """Initialize Chrome WebDriver using the chrome_setup module"""
    driver = setup_chrome_driver(
        headless=True,
        disable_images=True
    )
    driver.set_page_load_timeout(30)
    return driver

def fetch_page_content(driver: webdriver.Chrome, url: str) -> Optional[str]:
    """Fetch page content with scrolling and retry logic."""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            driver.get(url)
            time.sleep(5)
            
            # Scroll to load dynamic content
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            max_scrolls = 10
            
            while scroll_count < max_scrolls:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_count += 1
            
            return driver.page_source
            
        except Exception as e:
            logger.error(f"Error fetching page {url} (attempt {retry_count + 1}): {e}")
            retry_count += 1
            time.sleep(5)
    
    return None

def extract_article_urls(html: str, base_url: str) -> Set[str]:
    """Extract article URLs from page content."""
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Find all article links using multiple selectors
    selectors = [
        "article a", 
        ".post-title a",
        "a[href*='/article/']",
        ".entry-title a"
    ]
    
    for selector in selectors:
        for a_tag in soup.select(selector):
            if not a_tag.get("href"):
                continue
                
            url = urljoin(base_url, a_tag["href"])
            if "/article/" in url:
                # Clean URL to standard format
                try:
                    article_id = url.split("/article/")[1].split("/")[0]
                    article_id = article_id.split("?")[0].split("&")[0]
                    clean_url = f"https://btv.com.kh/article/{article_id}"
                    urls.add(clean_url)
                except IndexError:
                    continue
    
    return urls

def crawl_page(url: str, page: int, shared_links: Set[str], lock: threading.Lock, category: Optional[str] = None) -> None:
    """Crawl a single page and add found URLs to shared set."""
    driver = None
    try:
        driver = setup_selenium()
        page_url = f"{url}?page={page}"
        logger.info(f"Crawling page {page}: {page_url}")
        
        html = fetch_page_content(driver, page_url)
        if not html:
            logger.warning(f"Failed to fetch content for page {page}")
            return
            
        article_urls = extract_article_urls(html, url)
        
        with lock:
            original_count = len(shared_links)
            shared_links.update(article_urls)
            new_count = len(shared_links)
            
        if new_count > original_count:
            logger.info(f"Found {new_count - original_count} new URLs on page {page}")
        
    except Exception as e:
        logger.error(f"Error processing page {page}: {e}")
    finally:
        if driver:
            driver.quit()

def crawl_category(base_url: str, category: str, max_pages: int = 100) -> Set[str]:
    """Crawl a category and return all found article URLs."""
    shared_links = set()
    lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for page in range(1, max_pages + 1):
            futures.append(
                executor.submit(crawl_page, base_url, page, shared_links, lock)
            )
        
        # Wait for all futures to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in thread execution: {e}")
            
            # Check if we have enough URLs
            if len(shared_links) >= 500:  # Arbitrary limit
                logger.info(f"Found enough URLs ({len(shared_links)}) for {category}")
                break
    
    return shared_links

def main() -> None:
    """Main entry point for the BTV crawler."""
    categories = {
        "sport": "https://btv.com.kh/category/sport",
        "economic": "https://btv.com.kh/category/economic"
    }
    
    # Use standard output directory
    output_dir = "output/urls"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize URL manager
    url_manager = URLManager(output_dir, "btv")
    
    for category, url in categories.items():
        try:
            logger.info(f"Starting crawl of category: {category}")
            article_urls = crawl_category(url, category)
            
            # Add URLs to URL manager
            if article_urls:
                added = url_manager.add_urls(category, article_urls)
                logger.info(f"Added {added} new URLs for category {category}")
            
        except Exception as e:
            logger.error(f"Error processing category {category}: {e}")
    
    # Save final results
    results = url_manager.save_final_results()
    logger.info(f"Crawling completed. Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Crawler stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
