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

def crawl_pagination(base_url, start_url, category):
    """Crawl through paginated URLs and return all discovered links."""
    driver = setup_selenium()
    links = set()  # Add this to collect links
    try:
        current_page = start_url
        while current_page:
            logging.info(f"Crawling page: {current_page}")
            html = fetch_page_with_scroll(driver, current_page)
            soup = BeautifulSoup(html, "html.parser")

            # Parse links from the current page and collect them
            previous_count = len(links)
            page_links = parse_links(soup, base_url)
            links.update(page_links)
            new_count = len(links)
            
            # If we found new links, signal to save them
            if new_count > previous_count:
                logging.info(f"Found {new_count - previous_count} new links on page {current_page}")
                # The master controller will handle saving
                # We'll add this URL to the visited_links set to avoid re-processing

            # Look for the next page in pagination
            next_page = None
            for a_tag in soup.find_all("a", href=True):
                if "next" in a_tag.text.lower() or ">" in a_tag.text:  # Look for "Next" button
                    next_page = urljoin(base_url, a_tag["href"])
                    break

            # Check if the next page has already been visited
            if next_page and next_page not in visited_links:
                visited_links.add(current_page)
                current_page = next_page
            else:
                break  # No next page found
    except Exception as e:
        logging.error(f"Error crawling pagination: {e}")
    finally:
        driver.quit()
    
    # Return the collected links
    return links

def crawl_page(base_url, start_url, category):
    """Crawl the start URL and handle pagination."""
    logging.info(f"Starting crawl for: {start_url}")
    try:
        crawl_pagination(base_url, start_url, category)
    except Exception as e:
        logging.error(f"Error crawling {start_url}: {e}")

def main():
    base_url = "https://dap-news.com/"
    urls_to_crawl = [
        "https://dap-news.com/category/economic/",
        "https://dap-news.com/category/sport/",
        "https://dap-news.com/category/politic/",
        "https://dap-news.com/category/technology/",
        "https://dap-news.com/category/health/"
    ]
    max_threads = 5

    with ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {executor.submit(crawl_page, base_url, url, url): url for url in urls_to_crawl}

        for future in future_to_url:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error processing URL: {future_to_url[future]} - {e}")

    logging.info(f"Finished crawling. Results saved in the 'Dapnews' folder.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")