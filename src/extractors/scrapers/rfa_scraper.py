"""
RFA (Radio Free Asia) article scraper.

Extracts articles from rfa.org website.
"""

import os
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.extractors.browser import create_driver, close_driver
from src.extractors.logger import log_scrape_status, log_debug, log_error
from src.extractors.utils import is_scraped
from colorama import Fore, Style
from typing import Optional, Dict, Any

def extract_article(url: str, category: str) -> dict:
    """
    Extract article content from RFA URL.
    
    This is an alias for scrape_rfa to provide a consistent interface
    across all scrapers.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dictionary containing article data
    """
    return scrape_rfa(url, category)

def scrape_rfa(url: str, category: str) -> Optional[Dict[str, Any]]:
    """
    Scrape article content from RFA URL.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dictionary containing article data
    """
    driver = None
    
    try:
        # Skip already scraped URLs
        if is_scraped(url, category):
            log_debug(f"URL already scraped, skipping: {url}")
            return None
            
        log_scrape_status(f"{Fore.YELLOW}Scraping RFA article: {url}{Style.RESET_ALL}")
        
        # Initialize the driver
        driver = create_driver(headless=True, no_images=True)
        if not driver:
            raise Exception("Failed to create web driver")
            
        driver.get(url)
        
        # Wait for the article title to load
        title_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.page_title"))
        )
        title = title_element.text.strip()
        
        # Wait for the article content to load
        content_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.articleText, div.wysiwyg"))
        )
        
        # Extract paragraphs
        paragraphs = content_element.find_elements(By.TAG_NAME, "p")
        content_parts = [p.text.strip() for p in paragraphs if p.text.strip()]
        content = "\n".join(content_parts)
        
        # Extract date if available
        try:
            date_element = driver.find_element(By.CSS_SELECTOR, "span.date")
            date_published = date_element.text.strip()
        except NoSuchElementException:
            date_published = datetime.now().strftime("%Y-%m-%d")
            
        # Ensure we're not returning None
        if not title or not content:
            log_error(f"Failed to extract content from {url}")
            return {
                "title": "Error retrieving title",
                "content": "",
                "url": url,
                "category": category,
                "date_extracted": datetime.now().strftime("%Y-%m-%d"),
                "date_published": "",
                "source": "Radio Free Asia (RFA)"
            }
            
        article_data = {
            "title": title,
            "content": content,
            "url": url,
            "category": category,
            "date_extracted": datetime.now().strftime("%Y-%m-%d"),
            "date_published": date_published,
            "source": "Radio Free Asia (RFA)"
        }
        
        log_scrape_status(f"{Fore.GREEN}Successfully extracted RFA article: {title}{Style.RESET_ALL}")
        return article_data
        
    except Exception as e:
        log_error(f"Error scraping RFA article {url}: {str(e)}")
        return {
            "title": "Error retrieving title",
            "content": "",
            "url": url,
            "category": category,
            "date_extracted": datetime.now().strftime("%Y-%m-%d"),
            "date_published": "",
            "source": "Radio Free Asia (RFA)",
            "error": str(e)
        }
    finally:
        close_driver(driver)
