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
import logging
import time
import sys

# Add parent directory to sys.path to import chrome_setup module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chrome_setup import setup_chrome_driver

# Import the url_saver module
from url_saver import save_urls_to_file

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
        logging.error(f"Error setting up WebDriver: {e}")
        raise

def fetch_and_save_links(driver, url, category, max_scrolls=2000, scroll_pause_time=4):
    """Fetch links iteratively and save unique links."""
    links = set()
    logging.info(f"Opening URL: {url}")
    
    try:
        driver.get(url)
        
        # Increase initial page load wait time
        logging.info("Waiting for page to load...")
        time.sleep(10)  # Add initial wait time
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logging.info("Page loaded successfully")

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
                logging.info("Found load more button container")
                
                # Try direct AJAX pagination by manipulating data-paged attribute
                for page in range(2, 20):  # Try up to 20 pages
                    try:
                        logging.info(f"Attempting to load page {page} via AJAX")
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
                        logging.info(f"Found {articles_count} articles after attempting page {page}")
                        
                        # Extract links from the page
                        extract_links_from_page(soup, url, links)
                        
                        # Save progress
                        save_to_file(category, links)
                        
                        if articles_count < page * 10:  # Assuming each page should have at least 10 articles
                            logging.info(f"No more pages to load after page {page}")
                            break
                    except Exception as e:
                        logging.error(f"Error loading page {page}: {e}")
                        break
        except Exception as e:
            logging.info(f"No load more button container found: {e}")
        
        # If AJAX pagination didn't work, use the scrolling approach
        if not load_more_button_found or len(links) < 100:  # If we didn't find many links, try scrolling
            logging.info("Starting scroll-based crawling")
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
                            logging.info("Clicking load more button")
                            driver.execute_script("arguments[0].click();", load_more)
                            time.sleep(5)  # Wait for content to load after clicking
                except Exception as e:
                    logging.debug(f"No load more button to click: {str(e)}")
                
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
                
                logging.info(f"Found {len(article_containers)} article containers on scroll {scroll_count + 1}")
                
                new_links_found = len(links)
                
                # Extract links from the page
                extract_links_from_page(soup, url, links)
                
                new_links_found = len(links) - new_links_found
                logging.info(f"Found {new_links_found} new links on scroll {scroll_count + 1}. Total: {len(links)}")

                # Save intermediate results 
                if scroll_count % 3 == 0 or new_links_found > 0:
                    save_to_file(category, links)

                # Check if no more content is being loaded or no new links found
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height and len(links) == links_count_prev:
                    scroll_retry_count += 1
                    logging.info(f"No new content detected. Retrying... ({scroll_retry_count}/5)")
                    
                    # Try more aggressive scrolling when stuck
                    if scroll_retry_count > 2:
                        logging.info("Using more aggressive scrolling to trigger content load")
                        # Scroll to various positions to trigger lazy loading
                        for scroll_position in [0.7, 0.5, 0.3, 0.1, 0.9]:
                            driver.execute_script(f"window.scrollTo(0, {last_height * scroll_position});")
                            time.sleep(1)
                        
                        # Return to bottom
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                    
                    if scroll_retry_count >= 5:
                        logging.info(f"No more content to load after {scroll_count + 1} scrolls.")
                        break
                else:
                    if new_height != last_height:
                        logging.info(f"Page height increased from {last_height} to {new_height}")
                        scroll_retry_count = 0  # Reset retry count if page height changes
                    elif len(links) != links_count_prev:
                        logging.info(f"New links found without height change")
                        scroll_retry_count = 0  # Reset retry count if new links found
                    else:
                        logging.debug("No changes detected but not incrementing retry count")

                last_height = new_height
                links_count_prev = len(links)
        
        # Final extraction after all methods have been tried
        soup = BeautifulSoup(driver.page_source, "html.parser")
        extract_links_from_page(soup, url, links)
        
    except Exception as e:
        logging.error(f"Error while fetching links from {url}: {e}")
    
    logging.info(f"Completed crawling {url}. Found {len(links)} unique article links.")
    return links

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

def save_to_file(category, links):
    """Save the scraped links to a category-specific file."""
    folder = "kohsantepheapdaily"
    os.makedirs(folder, exist_ok=True)  # Create the folder if it doesn't exist
    file_path = os.path.join(folder, f"{category}.json")
    
    # Use the common save_urls_to_file function
    save_urls_to_file(links, file_path)

def crawl_url(base_url, shared_links, lock, category):
    """Crawl a single URL and save intermediate results."""
    driver = setup_selenium()
    try:
        logging.info(f"Crawling URL: {base_url}")
        links = fetch_and_save_links(driver, base_url, category)

        with lock:  # Ensure thread-safe access to shared_links
            shared_links.update(links)

        logging.info(f"Found {len(links)} links from URL: {base_url}.")
    except Exception as e:
        logging.error(f"Error crawling URL {base_url}: {e}")
    finally:
        driver.quit()

def main():
    """Main function to crawl the specified URLs."""
    # Hardcoded URLs to scrape
    urls = [
        "https://kohsantepheapdaily.com.kh/category/sport",
        "https://kohsantepheapdaily.com.kh/category/technology",
        "https://kohsantepheapdaily.com.kh/category/politic",
    ]

    logging.info(f"Starting crawl of {len(urls)} categories")
    
    # Create output directory
    output_dir = "kohsantepheapdaily"
    os.makedirs(output_dir, exist_ok=True)
    
    shared_links = set()
    lock = threading.Lock()

    # Reduce to 1 worker to allow more resources for deeper crawling
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [
            executor.submit(crawl_url, url, shared_links, lock, url.strip("/").split("/")[-1])
            for url in urls
        ]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error in thread execution: {e}")

    output_file = os.path.join(output_dir, "all_links.json")
    save_to_file("all_links", shared_links)
    logging.info(f"Finished crawling all URLs. Total links saved to {output_file}.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")

