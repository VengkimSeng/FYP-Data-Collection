from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import os
import logging
import time
import threading
import ssl
import sys
import re  # Import for regex pattern matching
import json  # Import for JSON saving

# Add parent directory to path to import chrome_setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver, setup_chrome_options
from src.crawlers.url_manager import URLManager

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Fix SSL issues
ssl._create_default_https_context = ssl._create_unverified_context

visited_links = set()
saved_links = set()
lock = threading.Lock()

def setup_selenium():
    """Initialize Chrome WebDriver using the chrome_setup module"""
    # Create options with our desired settings first
    options = setup_chrome_options(
        headless=True,
        disable_images=True,
        random_user_agent=True,
        additional_arguments=[
            "--ignore-certificate-errors",
            "--allow-insecure-localhost",
            "--disable-web-security",
            "--disable-webgl",
            "--enable-unsafe-swiftshader"
        ],
        additional_preferences={
            "profile.default_content_settings.popups": 0,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False
        }
    )
    
    # Then pass those options to setup_chrome_driver
    return setup_chrome_driver(
        chromedriver_path="/opt/homebrew/bin/Chromedriver",
        options=options
    )

def fetch_page_with_scroll(driver, url, scroll_pause_time=2):
    driver.get(url)
    time.sleep(5)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    return driver.page_source

def parse_links(soup, base_url):
    links = set()
    # Define pattern for article URLs - must be category/year/month/day/number/
    article_pattern = re.compile(r'^https://dap-news\.com/([^/]+)/(\d{4})/(\d{2})/(\d{2})/(\d+)/$')
    
    for a_tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, a_tag["href"])
        
        # Check if URL matches the specific article pattern and hasn't been visited yet
        if article_pattern.match(full_url) and full_url not in visited_links:
            links.add(full_url)
    
    return links

def crawl_pagination(base_url, start_url, category, url_manager):
    """Crawl through paginated URLs and add to URLManager."""
    driver = setup_selenium()
    links = set()
    try:
        current_page = start_url
        while current_page:
            logging.info(f"Crawling page: {current_page}")
            html = fetch_page_with_scroll(driver, current_page)
            soup = BeautifulSoup(html, "html.parser")

            # Parse links from the current page
            page_links = parse_links(soup, base_url)
            
            # Add new links to our collection
            previous_count = len(links)
            links.update(page_links)
            new_count = len(links)
            
            # If we found new links, add them to URLManager
            if new_count > previous_count:
                added = url_manager.add_urls(category, page_links)
                logging.info(f"Added {added} new links from {current_page}")

            # Look for the next page in pagination
            next_page = None
            for a_tag in soup.find_all("a", href=True):
                if "next" in a_tag.text.lower() or ">" in a_tag.text:  # Look for "Next" button
                    next_page = urljoin(base_url, a_tag["href"])
                    break

            # Move to next page if available
            if next_page and next_page != current_page:
                current_page = next_page
            else:
                break  # No next page found
    except Exception as e:
        logging.error(f"Error crawling pagination: {e}")
    finally:
        driver.quit()

def crawl_dapnews(output_dir="output/urls", urls_per_category=500):
    """Main function to crawl Dapnews using URLManager."""
    base_url = "https://dap-news.com/"
    urls_to_crawl = {
        "economic": "https://dap-news.com/category/economic/",
        "sport": "https://dap-news.com/category/sport/",
        "politic": "https://dap-news.com/category/politic/",
        "technology": "https://dap-news.com/category/technology/",
        "health": "https://dap-news.com/category/health/"
    }
    
    # Use standard output directory and URL manager
    url_manager = URLManager(output_dir, "dapnews", urls_per_category)
    max_workers = 3
    
    with ThreadPoolExecutor(max_workers) as executor:
        futures = []
        for category, url in urls_to_crawl.items():
            futures.append(executor.submit(crawl_pagination, base_url, url, category, url_manager))

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error processing URL: {e}")
    
    # Save final results
    results = url_manager.save_final_results()
    logging.info(f"Total URLs saved: {sum(results.values())}")
    return results

def main():
    base_url = "https://dap-news.com/"
    urls_to_crawl = [
        "https://dap-news.com/category/economic/",
        "https://dap-news.com/category/sport/",
        "https://dap-news.com/category/politic/",
        "https://dap-news.com/category/technology/",
        "https://dap-news.com/category/health/"
    ]
    
    # Use standard output directory
    output_dir = "output/urls"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize URL manager with standard output directory
    url_manager = URLManager(output_dir, "dapnews")
    
    # Map URLs to categories
    category_map = {
        "https://dap-news.com/category/economic/": "economic",
        "https://dap-news.com/category/sport/": "sport",
        "https://dap-news.com/category/politic/": "politic",
        "https://dap-news.com/category/technology/": "technology",
        "https://dap-news.com/category/health/": "health"
    }
    
    # Process each URL with threading for better performance
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for url in urls_to_crawl:
            category = category_map.get(url, "uncategorized")
            futures.append(executor.submit(crawl_pagination, base_url, url, category, url_manager))
        
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error in thread execution: {e}")
    
    # Save final results
    results = url_manager.save_final_results()
    logging.info(f"Finished crawling all URLs. Total links saved: {sum(results.values())}.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")