from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import os
import json
import logging
import time
import ssl
import sys

# Add parent directory to path to import chrome_setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.crawlers.url_manager import URLManager

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Fix SSL issues
ssl._create_default_https_context = ssl._create_unverified_context

def setup_selenium():
    """Initialize Chrome WebDriver using the chrome_setup module"""
    # Use the setup_chrome_driver function from chrome_setup.py
    # Modifying to use only the parameters it accepts
    driver = setup_chrome_driver(
        chromedriver_path="/opt/homebrew/bin/Chromedriver",
        headless=True,
        disable_images=True
    )
    
    # Configure Chrome options directly after driver is created
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    # Set additional options
    driver.set_page_load_timeout(30)
    
    return driver

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
    # Hardcoded URL filter for direct BTV article links
    url_filter = "/article/"
    
    for a_tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, a_tag["href"])
        
        # Only keep direct BTV article links
        if "btv.com.kh/article/" in full_url:
            # Clean the URL to ensure it has the correct format
            try:
                # Extract article ID
                article_id = full_url.split("/article/")[1].split("/")[0]
                # Ensure we only have the numeric ID by stripping any trailing characters
                article_id = article_id.split("?")[0].split("&")[0]
                # Construct clean URL
                clean_url = f"https://btv.com.kh/article/{article_id}"
                links.add(clean_url)
            except IndexError:
                continue
    
    return links

def crawl_page(base_url, page_index, url_manager, category):
    """Crawl a single page and add links to URL manager."""
    driver = setup_selenium()
    try:
        page_url = f"{base_url}?page={page_index}"
        logging.info(f"Crawling page: {page_url}")
        html = fetch_page_with_scroll(driver, page_url)
        soup = BeautifulSoup(html, "html.parser")
        links = parse_links(soup, base_url)

        # Add links to URL manager
        if links:
            added = url_manager.add_urls(category, links)
            logging.info(f"Added {added} new links from page {page_index} to category {category}")
        else:
            logging.info(f"No links found on page {page_index}")

        logging.info(f"Found {len(links)} links on page {page_index}.")
    except Exception as e:
        logging.error(f"Error crawling page {page_index}: {e}")
    finally:
        driver.quit()

def crawl_btv(output_dir="output/urls", urls_per_category=500):
    """Main function to crawl BTV categories using URLManager."""
    urls = [
        "https://btv.com.kh/category/sport",
        "https://btv.com.kh/category/economic"
    ]
    
    # Use standard output directory and URL manager
    url_manager = URLManager(output_dir, "btv", urls_per_category)
    
    for base_url in urls:
        category = base_url.split("/")[-1]
        max_pages = 500  # Limit to 20 pages initially
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(crawl_page, base_url, page, url_manager, category)
                for page in range(1, max_pages + 1)
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in thread execution: {e}")
    
    # Save final results
    results = url_manager.save_final_results()
    logging.info(f"Total URLs saved: {sum(results.values())}")
    return results

def main():
    # Hardcoded URLs to scrape
    urls = [
        "https://btv.com.kh/category/sport",
        "https://btv.com.kh/category/economic"
    ]

    logging.info(f"Starting crawl of {len(urls)} categories")
    
    # Create standard output directory
    output_dir = "output/urls"
    os.makedirs(output_dir, exist_ok=True)
    
    # Use URL manager with standard output directory
    url_manager = URLManager(output_dir, "btv")

    for base_url in urls:
        category = base_url.split("/")[-1]
        max_pages = 500  # Adjust based on site content

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(crawl_page, base_url, page, url_manager, category)
                for page in range(1, max_pages + 1)
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in thread execution: {e}")

        logging.info(f"Finished crawling category '{category}'.")

    # Save final results
    results = url_manager.save_final_results()
    logging.info(f"Finished crawling all URLs. Total links saved: {sum(results.values())}.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")
