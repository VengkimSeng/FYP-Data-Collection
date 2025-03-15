import os
import time
import random
import warnings
import sys
import json  # Add missing json import
from urllib.parse import urlparse, urljoin
from typing import Set, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from bs4 import BeautifulSoup

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

def filter_article_urls(urls: List[str], base_domain: str, category: str) -> List[str]:
    """Filter URLs to keep only article pages from the base domain."""
    filtered = []
    
    # Map common category names to RFA URL paths
    category_map = {
        'politic': 'politics',
        'economic': 'economy',
        'technology': 'tech',
        'sport': 'sport',
        'health': 'health',
        'environment': 'environment'
    }
    
    # Get the correct category path
    category_path = category_map.get(category, category)
    
    # Ensure urls is a list
    urls = list(urls) if isinstance(urls, set) else urls
    
    for url in urls:
        if url and isinstance(url, str):
            parsed = urlparse(url)
            # Keep only URLs from the same domain
            if parsed.netloc and base_domain in parsed.netloc:
                # Look for patterns that suggest it's an article page
                path = parsed.path.lower()
                # Check both with and without trailing slash
                if (f"/khmer/news/{category_path}/" in path or f"/khmer/news/{category_path}" in path) and path.endswith(".html"):
                    filtered.append(url)
    
    logger.info(f"Filtered {len(filtered)} URLs out of {len(urls)} raw URLs for {category}")
    if len(filtered) == 0:
        logger.debug(f"Sample raw URLs: {urls[:5] if len(urls) > 5 else urls}")
        logger.debug(f"Looking for pattern: /khmer/news/{category_path}")
    
    return filtered

def click_load_more(driver):
    """Click the 'មើលច្រើនជាងនេះ' (Load More) button."""
    try:
        # Try multiple button locator strategies
        button_selectors = [
            # Strategy 1: By button text with aria-label
            "//button[@aria-label='សូមមើលរឿងច្រើនទៀតអំពីប្រធានបទនេះ']",
            # Strategy 2: By button class and text
            "//button[contains(@class, 'c-button--primary') and .//span[contains(text(), 'មើលច្រើនជាងនេះ')]]",
            # Strategy 3: By Khmer text only
            "//button[.//span[contains(text(), 'មើលច្រើនជាងនេះ')]]",
            # Strategy 4: By class names
            "//button[contains(@class, 'c-button') and contains(@class, 'my-button')]"
        ]
        
        button = None
        for selector in button_selectors:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if button and button.is_displayed():
                    break
            except:
                continue
                
        if not button:
            logger.debug("Load more button not found with any selector")
            return False
            
        # Scroll button into view with offset
        driver.execute_script("""
            arguments[0].scrollIntoView();
            window.scrollBy(0, -100);
        """, button)
        time.sleep(2)
        
        # Try multiple click methods
        try:
            # Try regular click
            button.click()
        except:
            try:
                # Try JavaScript click
                driver.execute_script("arguments[0].click();", button)
            except:
                # Final attempt: dispatch click event
                driver.execute_script("""
                    var event = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    arguments[0].dispatchEvent(event);
                """, button)
                
        time.sleep(3)  # Wait for content to load
        return True
        
    except Exception as e:
        logger.debug(f"Load more button interaction failed: {e}")
        return False

def extract_article_urls(driver, base_domain: str, category: str) -> Set[str]:
    """Extract article URLs using BeautifulSoup's direct parsing."""
    urls = set()
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Log page structure for debugging
    logger.debug("Page structure:")
    logger.debug(f"Title: {soup.title.string if soup.title else 'No title'}")
    
    # Define RFA's specific article patterns
    article_patterns = [
        # Archive page patterns
        {"element": "div", "class": "archive_story"},
        {"element": "div", "class": "archive-story"},
        {"element": "div", "class": "sectionteaser"},
        {"element": "div", "class": "searchresult"},
        # Story grid patterns
        {"element": "div", "class": "story_grid"},
        {"element": "div", "class": "story_teaser"},
    ]
    
    # Try each pattern
    for pattern in article_patterns:
        elements = soup.find_all(pattern["element"], class_=pattern["class"])
        logger.debug(f"Found {len(elements)} elements matching {pattern}")
        
        for element in elements:
            # Look for links within the element
            links = element.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(driver.current_url, href)
                    if base_domain in full_url and ".html" in full_url:
                        urls.add(full_url)
                        
    # Fallback: try direct article links
    direct_links = soup.find_all('a', href=lambda x: x and '.html' in x)
    for link in direct_links:
        href = link.get('href')
        if href:
            full_url = urljoin(driver.current_url, href)
            if base_domain in full_url:
                urls.add(full_url)
    
    # Log results
    logger.debug(f"Raw URLs found: {len(urls)}")
    if len(urls) == 0:
        logger.debug("Page source preview:")
        logger.debug(soup.prettify()[:500])  # First 500 chars for debugging
    
    return urls

def crawl_category(url: str, category: str, max_clicks: int = -1) -> Set[str]:
    """Crawl a category using both direct article extraction and load more button."""
    filtered_urls = set()  # Only keep filtered URLs
    driver = setup_driver()
    clicks = 0
    consecutive_empty = 0
    base_domain = urlparse(url).netloc
    
    try:
        logger.info(f"Processing {category} at {url}")
        driver.get(url)
        time.sleep(5)
        
        while (max_clicks == -1 or clicks < max_clicks) and consecutive_empty < 3:
            # Extract and filter articles in one step
            new_urls = extract_article_urls(driver, base_domain, category)
            filtered = filter_article_urls(list(new_urls), base_domain, category)
            
            old_count = len(filtered_urls)
            filtered_urls.update(filtered)
            
            if len(filtered_urls) > old_count:
                consecutive_empty = 0
                logger.info(f"Found {len(filtered_urls) - old_count} new URLs (Total: {len(filtered_urls)})")
            else:
                consecutive_empty += 1
            
            if click_load_more(driver):
                clicks += 1
                time.sleep(5)
            else:
                consecutive_empty += 1
                
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
    finally:
        driver.quit()
        
    return filtered_urls

def main():
    """Main entry point."""
    url_manager = URLManager("output/urls", "rfanews")
    
    try:
        for category in url_manager.category_sources:
            try:
                sources = url_manager.get_sources_for_category(category, "rfanews")
                if not sources:
                    # Try alternative source name
                    sources = url_manager.get_sources_for_category(category, "rfa")
                
                if sources:
                    for url in sources:
                        logger.info(f"Crawling {category} from {url}")
                        urls = crawl_category(url, category)
                        if urls:
                            # Use url_manager to save URLs
                            added = url_manager.add_urls(category, urls)
                            logger.info(f"Added {added} URLs for {category}")
            except Exception as e:
                logger.error(f"Error processing category {category}: {str(e)}")
                continue
    finally:
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()
