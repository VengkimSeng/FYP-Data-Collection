import os
import time
import json
import random
import warnings
import logging
import platform
import sys
from urllib3.exceptions import InsecureRequestWarning
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from concurrent.futures import ThreadPoolExecutor
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Add parent directory to path to import chrome_setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver, setup_chrome_options

# Import the url_saver module
from src.utils.url_saver import save_urls_to_file, save_urls_with_progress, load_progress

# Import the URLManager
from src.crawlers.url_manager import URLManager

# Suppress urllib3 warnings related to SSL
warnings.filterwarnings('ignore', category=urllib3.exceptions.NotOpenSSLWarning)
urllib3.disable_warnings(InsecureRequestWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rfanews_crawler.log")
    ]
)
logger = logging.getLogger(__name__)

def setup_driver():
    """Set up Selenium WebDriver with options."""
    try:
        # Use chrome_setup module for consistent browser configuration
        options = setup_chrome_options(
            headless=True,
            disable_images=True,
            random_user_agent=True,
            additional_arguments=[
                "--disable-blink-features=AutomationControlled",
                "--ignore-certificate-errors",
                "--ignore-ssl-errors=yes",
                "--allow-running-insecure-content"
            ]
        )
        
        # Initialize the driver using our common setup function
        driver = setup_chrome_driver(
            options=options,
            use_webdriver_manager=True
        )
        
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize ChromeDriver: {e}")
        raise

def increment_url(base_url, increment):
    """Increment the pagination parameter in the URL."""
    url_parts = list(urlparse(base_url))
    query = parse_qs(url_parts[4])
    start_value = int(query.get('b_start:int', [0])[0])
    query['b_start:int'] = [start_value + increment]
    url_parts[4] = urlencode(query, doseq=True)
    return urlunparse(url_parts)

def load_progress(base_url):
    """Load progress from a saved file."""
    category = urlparse(base_url).path.split('/')[-2]
    return load_progress("Rfanews", category)

def save_progress(base_url, current_url, unique_urls, pages_scraped):
    """Save progress to a file."""
    category = urlparse(base_url).path.split('/')[-2]
    progress_data = {
        "current_url": current_url,
        "unique_urls": unique_urls,
        "pages_scraped": pages_scraped
    }
    
    save_urls_with_progress(unique_urls, category, "Rfanews", progress_data)

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

def scrape_urls(base_url, max_urls=6000, retry_count=3, url_manager=None):
    """Scrape unique URLs from the given base URL."""
    progress = load_progress(base_url)
    current_url = progress.get("current_url", base_url)
    unique_urls = set(progress.get("unique_urls", []))
    pages_scraped = progress.get("pages_scraped", 0)
    base_domain = urlparse(base_url).netloc
    category = urlparse(base_url).path.split('/')[-2]  # Extract category

    logger.info(f"Starting scraping for {base_url}")
    logger.info(f"Current progress: {pages_scraped} pages scraped, {len(unique_urls)} URLs collected")
    
    driver = None
    
    try:
        driver = setup_driver()
        
        while len(unique_urls) < max_urls:
            # Try loading the page with retries
            page_loaded = False
            for attempt in range(retry_count):
                try:
                    logger.info(f"Loading page: {current_url} (Attempt {attempt+1}/{retry_count})")
                    driver.get(current_url)
                    time.sleep(random.uniform(2, 4))
                    page_loaded = True
                    break
                except Exception as e:
                    logger.error(f"Failed to load page {current_url}: {e}")
                    if attempt == retry_count - 1:
                        logger.error("Max retries reached. Moving to next page.")
                    else:
                        time.sleep(random.uniform(5, 10))  # Longer wait between retries
            
            if not page_loaded:
                current_url = increment_url(current_url, 15)
                continue
            
            # Get all links on the page
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                page_urls = [link.get_attribute("href") for link in links]
                filtered_urls = filter_article_urls(page_urls, base_domain, category)
                
                # Add new URLs to our collection
                previous_count = len(unique_urls)
                for url in filtered_urls:
                    if url and url not in unique_urls:
                        unique_urls.add(url)
                new_count = len(unique_urls)
                new_urls = new_count - previous_count
                
                logger.info(f"Found {new_urls} new article URLs (Total: {len(unique_urls)})")
                
                # Add to URL manager if provided
                if url_manager and new_urls > 0:
                    added = url_manager.add_urls(category, filtered_urls)
                    logger.info(f"Added {added} URLs to URL manager for category '{category}'")
                
                # Save progress immediately whenever we find new URLs
                if new_urls > 0:
                    logger.info(f"Saving {new_urls} new URLs")
                    # If using URL manager, it will auto-save, otherwise save manually
                    if not url_manager:
                        filename = f"{category}_urls.json"
                        save_progress(base_url, current_url, list(unique_urls), pages_scraped)
                
                # Also save periodically even if no new URLs
                elif pages_scraped % 5 == 0 and not url_manager:
                    filename = f"{category}_urls.json"
                    save_progress(base_url, current_url, list(unique_urls), pages_scraped)
                
                # Check if we've reached the end (no new URLs found)
                if new_urls == 0 and pages_scraped > 5:
                    logger.info(f"No new URLs found after page {pages_scraped}. Considering pagination complete.")
                    consecutive_empty_pages = progress.get('consecutive_empty_pages', 0) + 1
                    if consecutive_empty_pages >= 3:
                        logger.info("Three consecutive pages with no new URLs. Stopping.")
                        break
                    progress['consecutive_empty_pages'] = consecutive_empty_pages
                else:
                    progress['consecutive_empty_pages'] = 0
                
                # Increment the URL and navigate to the next page
                current_url = increment_url(current_url, 15)
                pages_scraped += 1
                logger.info(f"Moving to page {pages_scraped}")
                
            except Exception as e:
                logger.error(f"Error processing page: {e}")
                # Try to continue with the next page
                current_url = increment_url(current_url, 15)
                pages_scraped += 1
                
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        if driver:
            driver.quit()
            
    logger.info(f"Scraping completed for {base_url}")
    logger.info(f"Total pages scraped: {pages_scraped}")
    logger.info(f"Total unique URLs collected: {len(unique_urls)}")
    
    # Final save of progress if not using URL manager
    if not url_manager:
        filename = f"{category}_urls.json"
        save_progress(base_url, current_url, list(unique_urls), pages_scraped)
    
    return list(unique_urls)[:max_urls]

def main():
    logger.info(f"Starting RFA News Web Crawler on {platform.system()} {platform.release()}")
    logger.info(f"Python version: {platform.python_version()}")
    
    urls_to_scrape = [
        "https://www.rfa.org/khmer/news/health/story_archive",
        "https://www.rfa.org/khmer/news/economy/story_archive",
        "https://www.rfa.org/khmer/news/environment/story_archive",
        "https://www.rfa.org/khmer/news/politics/story_archive",
    ]

    # Use standard output directory
    output_dir = "output/urls" 
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize URL manager with standard output dir
    url_manager = URLManager(output_dir, "rfanews")

    # Optional: use fewer workers to reduce resource usage
    max_workers = min(len(urls_to_scrape), 2)  # Limit to 2 concurrent workers
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_urls, url, 6000, 3, url_manager): url for url in urls_to_scrape}

        for future in futures:
            base_url = futures[future]
            category = urlparse(base_url).path.split('/')[-2]
            try:
                scraped_urls = future.result()
                logger.info(f"Completed scraping for {category}: {len(scraped_urls)} URLs collected")
            except Exception as e:
                logger.error(f"Error scraping {base_url}: {e}")
    
    # Save final results
    results = url_manager.save_final_results()
    logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()
