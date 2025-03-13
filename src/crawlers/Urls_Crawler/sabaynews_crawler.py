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
from concurrent.futures import ThreadPoolExecutor
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

# ==== CONFIGURATION ====
@dataclass
class CrawlerConfig:
    """Configuration settings for the crawler."""
    chrome_driver_path: Optional[str] = None
    wait_time: int = 2
    max_workers: int = 3
    output_dir: str = "sabaynews"
    categories: List[str] = None
    
    def __post_init__(self):
        """Set default values if none provided."""
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

# Initialize logger
logger = setup_logging()

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
        
        # Only keep URLs containing 'article'
        if "article" in full_url:
            urls.add(full_url)
            
    return urls

def scrape_category(base_url: str, output_prefix: str, config: CrawlerConfig) -> Set[str]:
    """
    Scrape URLs from a specific category by navigating through pages.
    
    Args:
        base_url: The base URL for the category.
        output_prefix: Prefix for output files.
        config: The crawler configuration.
        
    Returns:
        Set of collected article URLs.
    """
    driver = setup_selenium(config)
    page_number = 1
    all_urls = set()
    
    try:
        while True:
            # Construct the URL for the current page
            current_url = f"{base_url}/{page_number}"
            logger.info(f"Processing {current_url}")
            
            try:
                driver.get(current_url)
                time.sleep(config.wait_time)  # Wait for the page to load
                
                # Scrape URLs from the current view
                current_urls = scrape_urls(driver)
                
                if not current_urls:
                    logger.info(f"No more content found at page {page_number}. Stopping.")
                    break
                
                # Add current URLs to the collection
                previous_count = len(all_urls)
                all_urls.update(current_urls)
                new_count = len(all_urls)
                
                # If we found new URLs, log them
                if new_count > previous_count:
                    logger.info(f"Found {new_count - previous_count} new URLs on page {page_number}")
                
                logger.info(f"Scraped page {page_number} with {len(current_urls)} URLs.")
                page_number += 1
                
            except Exception as e:
                logger.error(f"Error scraping {current_url}: {str(e)}")
                break
                
    finally:
        driver.quit()
    
    return all_urls

# ==== MAIN FUNCTIONS ====
def scrape_all_categories(config: CrawlerConfig, url_manager: URLManager = None) -> None:
    if url_manager is None:
        url_manager = URLManager("output/urls", "sabaynews")
    
    # Prepare tasks for concurrent execution
    tasks = []
    for category in config.categories:
        base_url = f"https://news.sabay.com.kh/ajax/topics/{category}"
        output_prefix = os.path.join(url_manager.output_dir, category)
        tasks.append((base_url, output_prefix, category))
    
    # Execute tasks concurrently
    with ThreadPoolExecutor(max_workers=min(config.max_workers, len(tasks))) as executor:
        futures = {
            executor.submit(scrape_category, base_url, output_prefix, config): category
            for base_url, output_prefix, category in tasks
        }
        
        # Process results as they complete
        for future in futures:
            category = futures[future]
            try:
                result = future.result()
                if url_manager and result:
                    added = url_manager.add_urls(category, result)
                    logger.info(f"Added and saved {added} URLs for category '{category}'")
            except Exception as e:
                logger.error(f"Error scraping category '{category}': {str(e)}")
    
    logger.info("All categories processed")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="SabayNews web crawler")
    parser.add_argument("--driver", dest="chrome_driver_path", 
                      help="Path to ChromeDriver executable")
    parser.add_argument("--wait", dest="wait_time", type=int, default=2,
                      help="Wait time between page loads (default: 2)")
    parser.add_argument("--workers", dest="max_workers", type=int, default=3,
                      help="Maximum number of worker threads (default: 3)")
    parser.add_argument("--output", dest="output_dir", default="sabaynews",
                      help="Output directory for scraped URLs (default: sabaynews)")
    parser.add_argument("--categories", nargs="+", default=None,
                      help="Categories to scrape, e.g., 'entertainment technology sport'")
    return parser.parse_args()

def main() -> None:
    """Main entry point for the crawler."""
    logger.info("Starting SabayNews crawler")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Create configuration from arguments
    config = CrawlerConfig(
        chrome_driver_path=args.chrome_driver_path,
        wait_time=args.wait_time,
        max_workers=args.max_workers,
        output_dir=args.output_dir,
        categories=args.categories
    )
    
    # Log configuration details
    logger.info(f"Operating System: {platform.system()} {platform.release()}")
    logger.info(f"Python Version: {platform.python_version()}")
    logger.info(f"ChromeDriver Path: {config.chrome_driver_path}")
    logger.info(f"Categories to scrape: {config.categories}")
    
    # Initialize URL manager with direct output path
    url_manager = URLManager("output/urls", "sabaynews", auto_save=False)
    
    # Start scraping with URL manager
    scrape_all_categories(config, url_manager)
    
    logger.info("Crawler finished execution")

if __name__ == "__main__":
    main()
