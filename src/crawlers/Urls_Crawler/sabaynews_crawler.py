#!/usr/bin/env python3
"""
SabayNews Web Crawler

This script crawls the SabayNews website to extract article URLs from different categories
and saves them in both TXT and JSON formats.
"""

import os
import time
import json
import logging
import sys
import platform
from urllib.parse import urljoin
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional
import argparse
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Import chrome_setup module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver, setup_chrome_options

# Import the url_saver module
from src.utils.url_saver import save_urls_to_file, save_urls_to_multiple_formats

# Import URLManager
from src.crawlers.url_manager import URLManager

# Import get_crawler_logger
from src.utils.log_utils import get_crawler_logger

# ==== CONFIGURATION ====
@dataclass
class CrawlerConfig:
    """Configuration settings for the crawler."""
    chrome_driver_path: Optional[str] = None
    wait_time: int = 2
    max_workers: int = 3
    categories: List[str] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = ["entertainment", "technology", "sport"]

# ==== SETUP LOGGING ====
def setup_logging() -> logging.Logger:
    """Configure logging for the crawler."""
    logger = logging.getLogger("sabaynews_crawler")
    logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger with color coding
logger = get_crawler_logger('sabaynews')

# ==== SELENIUM SETUP ====
def setup_selenium(config: CrawlerConfig) -> webdriver.Chrome:
    """
    Setup and configure Selenium WebDriver with optimized settings.
    
    Args:
        config: The crawler configuration.
        
    Returns:
        Configured Chrome WebDriver instance.
    """
    # Use the chrome_setup module to set up the WebDriver
    try:
        logger.info("Setting up Chrome WebDriver")
        # Create chrome options with our preferred settings
        chrome_options = setup_chrome_options(
            headless=True,
            disable_images=True,
            random_user_agent=True,
            additional_arguments=None
        )
        
        # Initialize the driver using our common setup function
        driver = setup_chrome_driver(
            chromedriver_path=config.chrome_driver_path,
            options=chrome_options,
            use_webdriver_manager=True
        )
        logger.debug("WebDriver setup complete")
        return driver
    except Exception as e:
        logger.error(f"Failed to set up Chrome driver: {e}")
        raise

# ==== URL SCRAPING FUNCTIONS ====
def scrape_urls(driver: webdriver.Chrome) -> Set[str]:
    """
    Scrape article URLs from the current page.
    
    Args:
        driver: Selenium WebDriver instance.
        
    Returns:
        Set of article URLs.
    """
    urls = set()
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(driver.current_url, href)
        
        # Only keep URLs containing 'article' but not containing 'tag'
        if "article" in full_url and "/tag/" not in full_url:
            urls.add(full_url)
    
    return urls

def crawl_category(url: str, category: str, max_pages: int = -1) -> Set[str]:
    """
    Crawl a category page using AJAX pagination.
    
    Args:
        url: Base URL for the category
        category: Category name
        max_pages: Maximum number of pages to crawl (-1 for unlimited pagination)
    
    Returns:
        Set of article URLs
    """
    driver = setup_selenium(CrawlerConfig())
    urls = set()
    page = 0
    consecutive_empty = 0
    
    try:
        # Get initial page content
        logger.info(f"Crawling initial page at {url}")
        driver.get(url)
        time.sleep(2)
        urls.update(scrape_urls(driver))
        
        # Then use AJAX URLs for pagination
        while (max_pages == -1 or page <= max_pages) and consecutive_empty < 3:
            # Construct AJAX URL for pagination
            ajax_url = f"https://news.sabay.com.kh/ajax/topics/{category}/{page + 1}"
            logger.info(f"Crawling page {page + 1} at {ajax_url}")
            
            try:
                driver.get(ajax_url)
                time.sleep(2)
                
                page_urls = scrape_urls(driver)
                
                if not page_urls:
                    consecutive_empty += 1
                    logger.info(f"Empty page (attempt {consecutive_empty}/3)")
                else:
                    consecutive_empty = 0
                    urls.update(page_urls)
                    logger.info(f"Found {len(page_urls)} URLs on page {page + 1} (Total: {len(urls)})")
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error on page {page + 1}: {e}")
                consecutive_empty += 1
                
    finally:
        driver.quit()
        
    return urls

# ==== MAIN FUNCTIONS ====
def scrape_all_categories(config: CrawlerConfig) -> None:
    """Scrape all categories using URL manager."""
    url_manager = URLManager("output/urls", "sabay")
    
    try:
        for category in url_manager.category_sources:
            sources = url_manager.get_sources_for_category(category, "sabay")
            if sources:
                for base_url in sources:
                    logger.info(f"Crawling category {category} from {base_url}")
                    urls = crawl_category(base_url, category)
                    if urls:
                        added = url_manager.add_urls(category, urls)
                        logger.info(f"Added {added} URLs for category {category}")
    finally:
        # Save final results
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="SabayNews web crawler")
    parser.add_argument("--driver", dest="chrome_driver_path", 
                      help="Path to ChromeDriver executable")
    parser.add_argument("--wait", dest="wait_time", type=int, default=2,
                      help="Wait time between page loads (default: 2)")
    parser.add_argument("--workers", dest="max_workers", type=int, default=3,
                      help="Maximum number of worker threads (default: 3)")
    parser.add_argument("--categories", nargs="+", default=None,
                      help="Categories to scrape, e.g., 'entertainment technology sport'")
    return parser.parse_args()

def main() -> None:
    """Main entry point for the crawler."""
    logger.info("Starting SabayNews crawler")
    args = parse_arguments()
    
    config = CrawlerConfig(
        chrome_driver_path=args.chrome_driver_path,
        wait_time=args.wait_time,
        max_workers=args.max_workers,
        categories=args.categories
    )
    
    logger.info(f"Operating System: {platform.system()} {platform.release()}")
    logger.info(f"Python Version: {platform.python_version()}")
    logger.info(f"Categories to scrape: {config.categories}")
    
    scrape_all_categories(config)
    logger.info("Crawler finished execution")

if __name__ == "__main__":
    main()
