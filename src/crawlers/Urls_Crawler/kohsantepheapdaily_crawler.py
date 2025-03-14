import warnings
# Suppress SSL warnings
warnings.filterwarnings('ignore', message='.*urllib3 v2 only supports OpenSSL 1.1.1.*')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import os
import json
import time
import sys

# Add parent directory to sys.path to import chrome_setup module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver

# Import URLManager
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Replace old logging setup with new logger
logger = get_crawler_logger('kohsantepheap')

def setup_selenium():
    """Set up Selenium WebDriver."""
    try:
        driver = setup_chrome_driver(
            headless=True,
            disable_images=True,
            random_user_agent=True
        )
        # Set page load timeout
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Error setting up WebDriver: {e}")
        raise

def fetch_links(driver, url, category, max_scrolls=2000, scroll_pause_time=4):
    """Fetch links iteratively and collect unique links."""
    links = set()
    logger.info(f"Opening URL: {url}")
    
    try:
        driver.get(url)
        
        # Increase initial page load wait time
        logger.info("Waiting for page to load...")
        time.sleep(10)  # Add initial wait time
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info("Page loaded successfully")

        # Extra time to ensure JavaScript content is loaded
        time.sleep(5)
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_retry_count = 0  # To retry scrolls if no content is loaded
        links_count_prev = 0  # Track link count to detect when no new links are found
        current_page = 1
        
        # First try directly looking for the load more button and click it repeatedly
        load_more_button_found = False
        try:
            # Check if category_load_more_location exists
            load_more_location = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "category_load_more_location"))
            )
            
            if load_more_location:
                load_more_button_found = True
                logger.info("Found load more button container")
                
                # Try direct AJAX pagination by manipulating data-paged attribute
                for page in range(2, 20):  # Try up to 20 pages
                    try:
                        logger.info(f"Attempting to load page {page} via AJAX")
                        # Update the data-paged attribute to the next page
                        driver.execute_script(f"document.getElementById('category_load_more_location').setAttribute('data-paged', {page});")
                        # Trigger click or custom event to load more content
                        driver.execute_script("""
                            var clickEvent = new MouseEvent('click', {
                                'view': window,
                                'bubbles': true,
                                'cancelable': true
                            });
                            document.getElementById('category_load_more_location').dispatchEvent(clickEvent);
                        """)
                        time.sleep(5)  # Wait for AJAX content to load
                        
                        # Check if new content was loaded by comparing article count
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        articles_count = len(soup.select("article.white-box, div.content, article[class*='col-']"))
                        logger.info(f"Found {articles_count} articles after attempting page {page}")
                        
                        # Extract links from the page
                        extract_links_from_page(soup, url, links)
                        
                        if articles_count < page * 10:  # Assuming each page should have at least 10 articles
                            logger.info(f"No more pages to load after page {page}")
                            break
                    except Exception as e:
                        logger.error(f"Error loading page {page}: {e}")
                        break
        except Exception as e:
            logger.info(f"No load more button container found: {e}")
        
        # If AJAX pagination didn't work, use the scrolling approach
        if not load_more_button_found or len(links) < 100:  # If we didn't find many links, try scrolling
            logger.info("Starting scroll-based crawling")
            for scroll_count in range(max_scrolls):
                # Scroll to the bottom of the page
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)  # Wait for content to load
                
                # Try clicking any load more buttons if they exist and are visible
                try:
                    load_more_elements = driver.find_elements(By.CSS_SELECTOR, 
                        "#category_load_more_location, .more-link, button.load-more, .loader-bouncing")
                    for load_more in load_more_elements:
                        if load_more.is_displayed():
                            logger.info("Clicking load more button")
                            driver.execute_script("arguments[0].click();", load_more)
                            time.sleep(5)  # Wait for content to load after clicking
                except Exception as e:
                    logger.debug(f"No load more button to click: {str(e)}")
                
                # Randomly scroll up and down to trigger lazy loading
                if scroll_count % 3 == 0:
                    driver.execute_script(f"window.scrollTo(0, {last_height * 0.8});")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)

                # Parse the page content
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Find article containers with broader selectors
                article_containers = soup.select("article, div.content, .white-box, .big-image, .grid-one-four")
                
                logger.info(f"Found {len(article_containers)} article containers on scroll {scroll_count + 1}")
                
                new_links_found = len(links)
                
                # Extract links from the page
                extract_links_from_page(soup, url, links)
                
                new_links_found = len(links) - new_links_found
                logger.info(f"Found {new_links_found} new links on scroll {scroll_count + 1}. Total: {len(links)}")

                # Check if no more content is being loaded or no new links found
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height and len(links) == links_count_prev:
                    scroll_retry_count += 1
                    logger.info(f"No new content detected. Retrying... ({scroll_retry_count}/5)")
                    
                    # Try more aggressive scrolling when stuck
                    if scroll_retry_count > 2:
                        logger.info("Using more aggressive scrolling to trigger content load")
                        # Scroll to various positions to trigger lazy loading
                        for scroll_position in [0.7, 0.5, 0.3, 0.1, 0.9]:
                            driver.execute_script(f"window.scrollTo(0, {last_height * scroll_position});")
                            time.sleep(1)
                        
                        # Return to bottom
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                    
                    if scroll_retry_count >= 5:
                        logger.info(f"No more content to load after {scroll_count + 1} scrolls.")
                        break
                else:
                    if new_height != last_height:
                        logger.info(f"Page height increased from {last_height} to {new_height}")
                        scroll_retry_count = 0  # Reset retry count if page height changes
                    elif len(links) != links_count_prev:
                        logger.info(f"New links found without height change")
                        scroll_retry_count = 0  # Reset retry count if new links found
                    else:
                        logger.debug("No changes detected but not incrementing retry count")

                last_height = new_height
                links_count_prev = len(links)
        
        # Final extraction after all methods have been tried
        soup = BeautifulSoup(driver.page_source, "html.parser")
        extract_links_from_page(soup, url, links)
        
    except Exception as e:
        logger.error(f"Error while fetching links from {url}: {e}")
    
    logger.info(f"Completed crawling {url}. Found {len(links)} unique article links.")
    return links

# Rest of the helper functions remain unchanged
def extract_links_from_page(soup, base_url, links_set):
    """Extract article links from the page and add them to links_set."""
    # Method 1: Find links with article pattern in URL
    for a_tag in soup.select("a[href*='/article/']"):
        if a_tag.has_attr("href"):
            full_url = urljoin(base_url, a_tag["href"])
            links_set.add(full_url)
    
    # Method 2: Find links that end with .html (common article pattern)
    for a_tag in soup.select("a[href$='.html']"):
        if a_tag.has_attr("href"):
            full_url = urljoin(base_url, a_tag["href"])
            links_set.add(full_url)
    
    # Method 3: Find links within article containers
    for container in soup.select("article.white-box, div.content, article[class*='col-'], .grid-one-four, .big-image"):
        # Look for direct article links
        for a_tag in container.select("a.back-link, a[href*='/article/'], a[href$='.html']"):
            if a_tag.has_attr("href"):
                full_url = urljoin(base_url, a_tag["href"])
                links_set.add(full_url)
        
        # Look for title links (common pattern)
        for title in container.select("h3.title"):
            for a_tag in title.select("a"):
                if a_tag.has_attr("href"):
                    full_url = urljoin(base_url, a_tag["href"])
                    links_set.add(full_url)
    
    # Method 4: Find links within figures (common for image links to articles)
    for figure in soup.select("figure"):
        for a_tag in figure.select("a"):
            if a_tag.has_attr("href"):
                full_url = urljoin(base_url, a_tag["href"])
                if '/article/' in full_url or full_url.endswith('.html'):
                    links_set.add(full_url)

def crawl_url(url: str, shared_links: set, lock: threading.Lock, category: str) -> None:
    driver = setup_selenium()
    try:
        logger.info(f"Crawling URL: {url}")
        links = fetch_links(driver, url, category)
        
        # Add links to shared set with thread safety
        with lock:
            shared_links.update(links)
        logger.info(f"Added {len(links)} new links to shared set from URL: {url}")
    except Exception as e:
        logger.error(f"Error crawling URL {url}: {e}")
    finally:
        driver.quit()

# Categories to crawl
CATEGORIES = {
    "sport": "https://kohsantepheapdaily.com.kh/category/sport",
    "technology": "https://kohsantepheapdaily.com.kh/category/technology",
    "politics": "https://kohsantepheapdaily.com.kh/category/politic"
}

def crawl_kohsantepheap(output_dir="output/urls", urls_per_category=500):
    """Main function to crawl all categories using URLManager."""
    # Use standard output directory and URL manager
    url_manager = URLManager(output_dir, "kohsantepheapdaily", urls_per_category)
    
    for category, base_url in CATEGORIES.items():
        try:
            driver = setup_selenium()
            links = fetch_links(driver, base_url, category)
            driver.quit()
            
            added = url_manager.add_urls(category, links)
            logger.info(f"Added {added} links for category {category}")
        except Exception as e:
            logger.error(f"Error crawling category {category}: {e}")
    
    # Save final results at the end
    results = url_manager.save_final_results()
    logger.info(f"Total URLs saved: {sum(results.values())}")
    return results

def main():
    # Initialize URL manager
    url_manager = URLManager("output/urls", "kohsantepheap")
    
    try:
        for category in url_manager.category_sources:
            sources = url_manager.get_sources_for_category(category, "kohsantepheap")
            if sources:
                try:
                    driver = setup_selenium()
                    for url in sources:
                        links = fetch_links(driver, url, category)
                        driver.quit()
                        
                        added = url_manager.add_urls(category, links)
                        logger.info(f"Added {added} new links for category {category}")
                except Exception as e:
                    logger.error(f"Error crawling category {category}: {e}")
    finally:
        # Save final results
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script interrupted by user. Exiting...")

