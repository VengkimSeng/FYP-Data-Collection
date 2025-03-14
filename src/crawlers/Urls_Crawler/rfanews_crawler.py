import os
import time
import random
import warnings
import sys
from urllib.parse import urlparse
from typing import Set
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

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

def click_load_more(driver):
    """Click the 'មើលច្រើនជាងនេះ' (Load More) button."""
    try:
        # Wait for button with Khmer text
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'មើលច្រើនជាងនេះ')]"))
        )
        
        # Scroll button into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        time.sleep(1)
        
        # Try regular click first
        try:
            button.click()
        except ElementClickInterceptedException:
            # Fallback to JavaScript click
            driver.execute_script("arguments[0].click();", button)
            
        time.sleep(2)  # Wait for content to load
        return True
    except Exception as e:
        logger.debug(f"Load more button not found or not clickable: {e}")
        return False

def crawl_category(url: str, category: str, max_clicks: int = -1) -> Set[str]:
    """
    Crawl a category using infinite scroll and load more button.
    
    Args:
        url: Starting URL 
        category: Category being crawled
        max_clicks: Maximum load more clicks (-1 for unlimited)
    """
    urls = set()
    driver = setup_driver()
    clicks = 0
    consecutive_empty = 0
    base_domain = urlparse(url).netloc
    
    try:
        logger.info(f"Processing {category} at {url}")
        driver.get(url)
        time.sleep(3)
        
        while (max_clicks == -1 or clicks < max_clicks) and consecutive_empty < 3:
            # Get current page links
            links = driver.find_elements(By.TAG_NAME, "a")
            page_urls = [link.get_attribute("href") for link in links]
            new_urls = filter_article_urls(page_urls, base_domain, category)
            
            # Check if we found new URLs
            old_count = len(urls)
            urls.update(new_urls)
            
            if len(urls) > old_count:
                consecutive_empty = 0
                logger.info(f"Found {len(urls) - old_count} new URLs (Total: {len(urls)})")
            else:
                consecutive_empty += 1
                logger.info(f"No new URLs (attempt {consecutive_empty}/3)")
            
            # Try to load more content
            if click_load_more(driver):
                clicks += 1
                logger.info(f"Clicked load more button (click {clicks})")
            else:
                consecutive_empty += 1
                
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
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
