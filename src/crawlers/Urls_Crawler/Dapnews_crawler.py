from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import os
import time
import threading
import ssl
import sys
import re
import json
from typing import List

# Add parent directory to path to import chrome_setup  
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver, setup_chrome_options
from src.crawlers.url_manager import URLManager
from src.utils.log_utils import get_crawler_logger

# Replace old logging setup with new logger
logger = get_crawler_logger('dapnews')

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
            logger.debug(f"Found valid article URL: {full_url}")
    
    return links

def crawl_pagination(base_url, start_url, category, url_manager):
    """Crawl through paginated URLs and add to URLManager."""
    driver = setup_selenium()
    page_number = 1
    try:
        while True:
            current_page = f"{start_url}page/{page_number}/" if page_number > 1 else start_url
            logger.info(f"Crawling page {page_number}: {current_page}")
            
            try:
                html = fetch_page_with_scroll(driver, current_page)
                soup = BeautifulSoup(html, "html.parser")

                # Parse links from the current page
                page_links = parse_links(soup, base_url)
                
                if not page_links:  # If no links found, we've reached the end
                    logger.info(f"No more links found on page {page_number}. Stopping.")
                    break

                # Add new links to URLManager and save immediately
                added = url_manager.add_urls(category, page_links)
                if added > 0:
                    url_manager.save_progress()  # Save after each successful page
                    logger.info(f"Added and saved {added} new links from page {page_number}")
                else:
                    logger.info(f"No new links found on page {page_number}")
                    
                # Check if we've reached the target number of URLs
                if url_manager.is_category_complete(category):
                    logger.info(f"Reached target number of URLs for category {category}")
                    break

                page_number += 1
                time.sleep(2)  # Add small delay between pages
                
            except Exception as e:
                logger.error(f"Error on page {page_number}: {e}")
                break

    except Exception as e:
        logger.error(f"Error in pagination crawler: {e}")
    finally:
        driver.quit()

def save_to_file(category: str, links: List[str]) -> None:
    output_path = os.path.join("output", f"{category}.json")
    save_urls_to_file(links, output_path)

def crawl_dapnews(output_dir="output/urls", urls_per_category=500):
    """Main function to crawl Dapnews using URLManager."""
    url_manager = URLManager(output_dir, "dapnews")
    base_url = "https://dap-news.com/"
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for category in url_manager.category_sources:
            # Get only Dapnews sources for this category
            sources = url_manager.get_sources_for_category(category, "dapnews")
            if sources:  # Only process if we have sources for this category
                for source_url in sources:
                    futures.append(executor.submit(
                        crawl_pagination, base_url, source_url, category, url_manager
                    ))

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error processing URL: {e}")

    return url_manager.save_final_results()

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
                logger.error(f"Error in thread execution: {e}")
    
    # Save final results
    results = url_manager.save_final_results()
    logger.info(f"Finished crawling all URLs. Total links saved: {sum(results.values())}.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script interrupted by user. Exiting...")