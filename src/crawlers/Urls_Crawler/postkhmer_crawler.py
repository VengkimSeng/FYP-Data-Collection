from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os
import sys
import warnings
import urllib3
import json
from typing import Set

# Add parent directory to sys.path to import chrome_setup module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver

# Import the url_saver module
from src.utils.url_saver import save_urls_to_file

# Import URLManager
from src.crawlers.url_manager import URLManager

from src.utils.log_utils import get_crawler_logger

# Replace old logging setup with new logger
logger = get_crawler_logger('postkhmer')

# Suppress the urllib3 warning about OpenSSL
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)

def setup_selenium():
    """Setup Selenium WebDriver with headless mode."""
    try:
        # Use the chrome_setup module to get a configured WebDriver
        logger.info("Setting up Selenium WebDriver...")
        driver = setup_chrome_driver(
            headless=True,
            disable_images=True,
            random_user_agent=True
        )
        logger.info("WebDriver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Error setting up WebDriver: {e}")
        raise

def scroll_and_click(driver, category):
    """Scroll to the load more button and click it."""
    try:
        # Try different strategies to find the load more button
        wait = WebDriverWait(driver, 15)  # Wait up to 15 seconds
        
        # Strategy 1: Try with category in button text (most specific)
        try:
            xpath = f"//div[contains(@class, 'load-more')]//button[contains(@class, 'btn-load') and contains(text(), '{category}')]"
            load_more_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            logger.info(f"Found button with category text: {category}")
        except:
            # Strategy 2: Try any btn-load inside load-more div
            try:
                xpath = "//div[contains(@class, 'load-more')]//button[contains(@class, 'btn-load')]"
                load_more_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                logger.info("Found button with class btn-load")
            except:
                # Strategy 3: Try with CSS selector
                try:
                    css_selector = "div.load-more button.btn-load"
                    load_more_btn = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
                    )
                    logger.info("Found button with CSS selector")
                except:
                    # Strategy 4: Just try to find any button with class btn-load
                    load_more_btn = wait.until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "btn-load"))
                    )
                    logger.info("Found button with simple class name")
        
        # Scroll to button - ensure it's in view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", load_more_btn)
        time.sleep(2)  # Let the page settle after scrolling
        
        # Print button text for debugging
        button_text = load_more_btn.text
        logger.info(f"Button text: '{button_text}'")
        
        # Click button using JavaScript (more reliable than direct click)
        logger.info("Clicking 'load more' button")
        driver.execute_script("arguments[0].click();", load_more_btn)
        
        # Wait for new content to load
        time.sleep(5)  # Increased wait time to ensure content loads
        return True
    except Exception as e:
        logger.error(f"Error clicking load more button: {e}")
        
        # Fallback - try to find the button by JavaScript directly
        try:
            logger.info("Trying fallback JavaScript button click")
            # Try to click any button with class btn-load
            driver.execute_script("document.querySelector('.btn-load').click();")
            time.sleep(5)
            return True
        except:
            logger.error("Fallback JavaScript click also failed")
            return False

def extract_article_urls(soup, base_url):
    """Extract article URLs from the more-content section."""
    urls = set()
    
    # Log the structure to debug
    more_content = soup.find("div", class_="more-contents")
    if more_content:
        logger.info("Found more-contents div")
        article_items = more_content.find_all("div", class_="more-item")
        logger.info(f"Found {len(article_items)} article items")
        
        # Process each article item
        for item in article_items:
            # Get the main article link (heading link)
            more_text = item.find("div", class_="more-text")
            if more_text:
                article_link = more_text.find("a")
                if article_link and "href" in article_link.attrs:
                    href = article_link["href"]
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
                    
            # Also check the image link which sometimes differs
            img_container = item.find("div", class_="more-img")
            if img_container:
                img_link = img_container.find("a")
                if img_link and "href" in img_link.attrs:
                    href = img_link["href"]
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
    else:
        # If more-contents not found, try alternative selectors
        logger.warning("more-contents div not found, trying alternate selectors")
        
        # Try to extract URLs from article-news section if it exists
        article_news = soup.find("div", class_="article-news")
        if article_news:
            logger.info("Found article-news div")
            for a_tag in article_news.find_all("a", href=True):
                href = a_tag["href"]
                if href and not href == "#" and not href.startswith("javascript"):
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
        
        # Extract all article links from the page as a fallback
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Filter links to make sure they're articles
            if href and href.startswith(("/politics/", "/business/", "/national/", "/sport/", "/lifestyle/", "/world/")):
                full_url = urljoin(base_url, href)
                urls.add(full_url)
    
    return urls

def scrape_page_content(driver, base_url, category, max_click=-1) -> Set[str]:
    """
    Scrape URLs from the page and return them.
    
    Args:
        driver: WebDriver instance
        base_url: Base URL of the page
        category: Category being scraped
        max_click: Maximum number of load more clicks (-1 for unlimited clicking)
    """
    visited_urls = set()
    click_attempts = 0
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    # Initial page load
    soup = BeautifulSoup(driver.page_source, "html.parser")
    initial_urls = extract_article_urls(soup, base_url)
    visited_urls.update(initial_urls)
    
    while (max_click == -1 or click_attempts < max_click) and consecutive_failures < max_consecutive_failures:
        if scroll_and_click(driver, category):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            new_urls = extract_article_urls(soup, base_url)
            
            # Check if we found new URLs
            old_count = len(visited_urls)
            visited_urls.update(new_urls)
            if len(visited_urls) > old_count:
                consecutive_failures = 0
                logger.info(f"Found {len(visited_urls) - old_count} new URLs")
            else:
                consecutive_failures += 1
                logger.warning(f"No new URLs found (attempt {consecutive_failures}/{max_consecutive_failures})")
        else:
            consecutive_failures += 1
            logger.warning(f"Click failed (attempt {consecutive_failures}/{max_consecutive_failures})")
            
        click_attempts += 1
        logger.info(f"Click attempt {click_attempts}/{max_click}")
    
    return visited_urls

def crawl_category(url: str, category: str, max_click: int = -1) -> set:
    """
    Crawl a single category page.
    
    Args:
        url: URL to crawl
        category: Category name
        max_click: Maximum number of load more clicks (-1 for unlimited clicking)
    
    Returns:
        Set of collected URLs
    """
    driver = setup_selenium()
    try:
        logger.info(f"Crawling {category}: {url}")
        driver.get(url)
        time.sleep(5)  # Initial load
        
        urls = scrape_page_content(driver, url, category, max_click=max_click)
        return filter_postkhmer_urls(list(urls))
        
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
        return set()
    finally:
        driver.quit()

def filter_postkhmer_urls(urls):
    """Filter PostKhmer URLs based on specific criteria."""
    filtered_urls = []
    
    for url in urls:
        # Parse URL to analyze components
        parsed = urlparse(url)
        
        # Basic validation
        if not parsed.netloc or not parsed.scheme:
            continue
            
        # Make sure it's from postkhmer.com
        if "postkhmer.com" not in parsed.netloc:
            continue
            
        # Filter out non-article pages
        path = parsed.path.lower()
        if any(exclude in path for exclude in [
            "/search", "/tag/", "/category/", "/author/", 
            "/page/", "/about", "/contact", "/privacy", 
            "/terms", "/subscribe", "/login", "/register"
        ]):
            continue
            
        # Ensure it's a content page
        if not path.startswith(("/politics/", "/business/", "/national/", 
                               "/sport/", "/lifestyle/", "/world/", 
                               "/financial/")):
            continue
            
        # Additional check for article pages (they usually have a numeric ID)
        if path.count('/') < 2:  # Need at least /category/article-title
            continue
            
        # Keep only HTML pages
        if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp3", ".mp4")):
            continue
            
        # Add to filtered list
        filtered_urls.append(url)
    
    logger.info(f"Filtered {len(filtered_urls)} URLs out of {len(urls)} total URLs")
    return filtered_urls

def main():
    # Initialize URL manager
    url_manager = URLManager("output/urls", "postkhmer")
    
    try:
        driver = setup_selenium()
        # Process categories that have PostKhmer sources
        for category in url_manager.category_sources:
            sources = url_manager.get_sources_for_category(category, "postkhmer")
            if sources:
                for url in sources:
                    logger.info(f"Scraping category: {url}")
                    driver.get(url)
                    time.sleep(5)
                    
                    urls = scrape_page_content(driver, url, category)
                    filtered_urls = filter_postkhmer_urls(list(urls))
                    
                    added = url_manager.add_urls(category, filtered_urls)
                    logger.info(f"Added {added} filtered URLs from {url}")
    finally:
        if 'driver' in locals():
            driver.quit()
        
        # Save final results
        results = url_manager.save_final_results()
        logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()
