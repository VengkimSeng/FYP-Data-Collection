"""
Generic web scraper for article extraction.

This module provides a fallback method for extracting content from websites
that don't have a dedicated scraper implementation.
"""

import os
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.extractors.browser import create_driver, close_driver
from src.extractors.logger import log_scrape_status, log_debug, log_error, log_category_progress
from src.extractors.utils import is_scraped
from colorama import Fore, Style

def generic_scrape(url: str, category: str, title_selector: str = None, content_selector: str = None, is_id: bool = False, max_retries: int = 3, log_progress: bool = False, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Extract article content using generic extraction techniques.
    
    Args:
        url: URL to extract from
        category: Category of the article
        title_selector: CSS selector for the title element
        content_selector: CSS selector for the content element
        is_id: Whether to use ID instead of CSS selector for content
        max_retries: Maximum number of retries on failure
        log_progress: Whether to log progress messages
        **kwargs: Additional keyword arguments passed to specific scrapers
        
    Returns:
        Dictionary containing article data or None if extraction failed
    """
    driver = None
    retry_count = 0
    success_count = 0
    error_count = 0
    
    while retry_count < int(max_retries):  # Ensure max_retries is int
        try:
            # Check if already scraped
            if is_scraped(url, category):
                log_debug(f"URL already scraped, skipping: {url}")
                return None
                
            # Get the domain
            domain = urlparse(url).netloc
            
            # Create a new driver
            driver = create_driver(headless=True, no_images=True)
            
            # Load the page
            driver.get(url)
            
            if log_progress:
                log_category_progress(category, 0, 1, 0, 0)
                
            # Wait for page to load
            time.sleep(2)
            
            # Extract title using provided selector
            title = extract_title(driver, title_selector) if title_selector else extract_title(driver)
            
            if not title:
                log_error(f"Failed to extract title from {url}")
                close_driver(driver)
                driver = None
                retry_count += 1
                continue
                
            # Extract content using provided selector
            content = extract_content(driver, content_selector, is_id) if content_selector else extract_content(driver)
            
            if not content:
                log_error(f"Failed to extract content from {url}")
                close_driver(driver)
                driver = None
                retry_count += 1
                continue
            
            # Create article data
            from datetime import datetime
            article_data = {
                "url": url,
                "title": title,
                "content": content,
                "category": category,
                "domain": domain,
                "extraction_method": "generic",
                "date_extracted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Log success
            log_scrape_status(f"{Fore.GREEN}Successfully extracted article: {title}{Style.RESET_ALL}")
            
            if log_progress:
                log_category_progress(category, 1, 1, 1, 0)
                
            return article_data
            
        except Exception as e:
            log_error(f"Error extracting content from {url}: {str(e)}")
            retry_count += 1
            
            if retry_count < max_retries:
                log_debug(f"Retrying... ({retry_count}/{max_retries})")
                time.sleep(2 * retry_count)  # Exponential backoff
            
        finally:
            if driver:
                close_driver(driver)
                driver = None
    
    if log_progress:
        log_category_progress(category, 1, 1, 0, 1)
    
    return None

def extract_title(driver: webdriver.Chrome, custom_selector: str = None) -> str:
    """
    Extract article title using provided or default selectors.
    
    Args:
        driver: Selenium WebDriver instance
        custom_selector: Custom CSS selector for the title element
        
    Returns:
        Article title as string
    """
    if custom_selector:
        try:
            element = driver.find_element(By.CSS_SELECTOR, custom_selector)
            title = element.text.strip()
            if title:
                return title
        except:
            pass

    # Fall back to default selectors
    # Common title selectors to try
    title_selectors = [
        ("h1", By.TAG_NAME),
        ("h1.title", By.CSS_SELECTOR),
        ("h1.article-title", By.CSS_SELECTOR),
        ("h1.entry-title", By.CSS_SELECTOR),
        ("h1.post-title", By.CSS_SELECTOR),
        ("article h1", By.CSS_SELECTOR),
        (".article-title", By.CSS_SELECTOR),
        (".entry-title", By.CSS_SELECTOR),
        (".post-title", By.CSS_SELECTOR),
        (".headline", By.CSS_SELECTOR),
        ("meta[property='og:title']", By.CSS_SELECTOR, "content"),  # Meta tag
        ("title", By.TAG_NAME)  # Last resort
    ]
    
    for selector in title_selectors:
        try:
            if len(selector) == 2:
                selector_text, selector_type = selector
                element = driver.find_element(selector_type, selector_text)
                title = element.text.strip()
                if title:
                    return title
            else:
                selector_text, selector_type, attribute = selector
                element = driver.find_element(selector_type, selector_text)
                title = element.get_attribute(attribute).strip()
                if title:
                    return title
        except:
            continue
            
    # Last resort - get page title
    try:
        return driver.title.strip()
    except:
        return "Unknown Title"

def extract_content(driver: webdriver.Chrome, custom_selector: str = None, is_id: bool = False) -> str:
    """
    Extract article content using provided or default selectors.
    
    Args:
        driver: Selenium WebDriver instance
        custom_selector: Custom CSS selector for the content element
        is_id: Whether to use ID instead of CSS selector for content
        
    Returns:
        Article content as string
    """
    if custom_selector:
        try:
            if is_id:
                element = driver.find_element(By.ID, custom_selector)
            else:
                element = driver.find_element(By.CSS_SELECTOR, custom_selector)
            paragraphs = element.find_elements(By.TAG_NAME, "p")
            if paragraphs:
                content = "\n\n".join(p.text.strip() for p in paragraphs if p.text.strip())
                if content:
                    return content
        except:
            pass

    # Fall back to default selectors
    # Common content selectors to try
    content_selectors = [
        ("article", By.TAG_NAME),
        ("div.article-content", By.CSS_SELECTOR),
        ("div.entry-content", By.CSS_SELECTOR),
        ("div.post-content", By.CSS_SELECTOR),
        ("div.content", By.CSS_SELECTOR),
        (".article-body", By.CSS_SELECTOR),
        ("#article-body", By.CSS_SELECTOR),
        (".entry-content", By.CSS_SELECTOR),
        (".post-content", By.CSS_SELECTOR),
        (".story-body", By.CSS_SELECTOR),
        ("main", By.TAG_NAME)
    ]
    
    for selector_text, selector_type in content_selectors:
        try:
            element = driver.find_element(selector_type, selector_text)
            paragraphs = element.find_elements(By.TAG_NAME, "p")
            
            if paragraphs:
                # Join paragraph texts into a single string
                content = "\n\n".join(p.text.strip() for p in paragraphs if p.text.strip())
                if content:
                    return content
        except:
            continue
            
    # Last resort - get all paragraphs from the page
    try:
        paragraphs = driver.find_elements(By.TAG_NAME, "p")
        if paragraphs:
            return "\n\n".join(p.text.strip() for p in paragraphs if p.text.strip())
    except:
        pass
        
    return "Could not extract content."
