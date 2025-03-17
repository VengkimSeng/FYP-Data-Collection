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
import argparse
from typing import Set
import traceback

# Add parent directory to sys.path to import chrome_setup module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.utils.log_utils import get_crawler_logger
from src.utils.page_utils import scroll_page, click_load_more
from src.utils.url_utils import filter_urls
from src.utils.source_manager import get_source_urls, get_site_categories  # New imports
from src.utils.cmd_utils import parse_crawler_args, get_categories_from_args

# Remove existing urllib3 warning handlers and replace with comprehensive handling
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)
warnings.simplefilter('ignore', UserWarning)
# Attempt multiple warning suppression strategies
try:
    # Try urllib3 specific warnings
    warnings.simplefilter('ignore', urllib3.exceptions.NotOpenSSLWarning)
except (AttributeError, ImportError):
    pass

try:
    # Try to suppress all urllib3 warnings
    urllib3.disable_warnings()
except:
    pass

# Setup logger
logger = get_crawler_logger('postkhmer')

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
    # Use shared click_load_more function with specific selectors for PostKhmer
    button_selectors = [
        f"//div[contains(@class, 'load-more')]//button[contains(@class, 'btn-load') and contains(text(), '{category}')]",
        "//div[contains(@class, 'load-more')]//button[contains(@class, 'btn-load')]",
        "div.load-more button.btn-load",
        ".btn-load"
    ]
    
    return click_load_more(driver, button_selectors=button_selectors, wait_time=5)

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
    Scrape URLs from the page by repeatedly clicking the "load more" button.
    
    Args:
        driver: WebDriver instance
        base_url: Base URL of the page
        category: Content category
        max_click: Maximum click attempts (-1 for unlimited)
        
    Returns:
        Set of collected URLs
    """
    all_urls = set()
    click_attempts = 0
    consecutive_failures = 0
    max_consecutive_failures = 3
    consecutive_no_new_urls = 0
    max_consecutive_no_new = 3
    
    # Output file path for saving URLs incrementally
    output_file = os.path.join("output/urls", f"{category}.json")
    
    # Initial page load
    soup = BeautifulSoup(driver.page_source, "html.parser")
    initial_urls = extract_article_urls(soup, base_url)
    all_urls.update(initial_urls)
    
    logger.info(f"Initial page: Found {len(initial_urls)} URLs")
    
    # SAVE INITIAL URLS
    if initial_urls:
        filtered_urls = filter_postkhmer_urls(list(initial_urls), category)
        if filtered_urls:
            from src.crawlers.master_crawler_controller import save_urls
            save_urls(output_file, filtered_urls)
            logger.info(f"Saved {len(filtered_urls)} URLs from initial page")
    
    while (max_click == -1 or click_attempts < max_click) and consecutive_failures < max_consecutive_failures and consecutive_no_new_urls < max_consecutive_no_new:
        if scroll_and_click(driver, category):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            new_urls = extract_article_urls(soup, base_url)
            
            # Check if we found new URLs
            old_count = len(all_urls)
            all_urls.update(new_urls)
            new_unique_count = len(all_urls) - old_count
            
            if new_unique_count > 0:
                consecutive_failures = 0
                consecutive_no_new_urls = 0
                logger.info(f"Found {new_unique_count} new unique URLs")
                
                # SAVE URLS AFTER EACH SUCCESSFUL CLICK WITH NEW CONTENT
                filtered_urls = filter_postkhmer_urls(list(new_urls), category)
                if filtered_urls:
                    from src.crawlers.master_crawler_controller import save_urls
                    save_urls(output_file, filtered_urls)
                    logger.info(f"Saved {len(filtered_urls)} URLs after click {click_attempts+1}")
            else:
                consecutive_no_new_urls += 1
                logger.warning(f"No new URLs found (attempt {consecutive_no_new_urls}/{max_consecutive_no_new})")
        else:
            consecutive_failures += 1
            logger.warning(f"Click failed (attempt {consecutive_failures}/{max_consecutive_failures})")
            
        click_attempts += 1
        logger.info(f"Click attempt {click_attempts}/{max_click}")
    
    if consecutive_no_new_urls >= max_consecutive_no_new:
        logger.info("Stopping: No new unique URLs found in consecutive attempts")
    
    return all_urls

def filter_postkhmer_urls(urls, category) -> list:
    """
    Filter PostKhmer URLs based on specific criteria and category.
    
    Args:
        urls: List or set of URLs to filter
        category: Category being crawled
        
    Returns:
        Filtered list of URLs
    """
    # Use shared filter_urls function with specific criteria for PostKhmer
    filtered = filter_urls(
        urls,
        domain="postkhmer.com",
        contains=None,
        excludes=["/search", "/tag/", "/category/", "/author/", 
                "/page/", "/about", "/contact", "/privacy", 
                "/terms", "/subscribe", "/login", "/register"],
        path_pattern=r"^/(politics|business|national|sport|lifestyle|world|financial)/.*"
    )
    
    # Additional category-specific filtering if needed
    result = set()
    for url in filtered:
        # Skip media files
        if url.endswith(('.jpg', '.jpeg', '.png', '.pdf')):
            continue
            
        # Skip URLs with parameters suggesting non-articles
        if '?' in url and any(param in url for param in ['s=', 'page=', 'tag=']):
            continue
            
        result.add(url)
    
    logger.info(f"Filtered {len(urls)} URLs down to {len(result)} valid articles")
    return list(result)  # Convert set to list before returning

def crawl_category(source_url: str, category: str, max_click: int = -1) -> list:
    """
    Crawl a single category page.
    
    Args:
        source_url: URL to crawl (renamed from url for consistency)
        category: Category name
        max_click: Maximum number of load more clicks (-1 for unlimited clicking)
    
    Returns:
        List of collected and filtered URLs
    """
    driver = setup_selenium()
    try:
        logger.info(f"Crawling {category}: {source_url}")
        driver.get(source_url)
        time.sleep(5)  # Initial load
        
        urls = scrape_page_content(driver, source_url, category, max_click=max_click)
        # Apply filtering directly here
        filtered_urls = filter_postkhmer_urls(list(urls), category)
        logger.info(f"Total unique URLs after filtering: {len(filtered_urls)}")
        return filtered_urls
        
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
        return []
    finally:
        driver.quit()

def main():
    """Main entry point for the PostKhmer crawler."""
    # Parse command line arguments using the utility
    args = parse_crawler_args("postkhmer")
    
    # All URLs collected (used only for standalone run)
    all_urls = {}
    
    try:
        # Get categories from source manager using the utility
        args["site_name"] = "postkhmer"
        categories = get_categories_from_args(args)
        
        for category in categories:
            all_urls[category] = set()
            # Get source URLs for this category
            sources = get_source_urls(category, "postkhmer")
            if sources:
                for url in sources:
                    logger.info(f"Scraping category {category} from {url}")
                    urls = crawl_category(url, category, max_click=args["max_click"])
                    all_urls[category].update(urls)
                    logger.info(f"Total URLs for category {category}: {len(all_urls[category])}")
            else:
                logger.warning(f"No source URLs found for category: {category}")
    
        # Print final summary when running standalone
        logger.info("Crawling complete. Summary:")
        for cat, urls in all_urls.items():
            logger.info(f"  {cat}: {len(urls)} URLs")
    
    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        logger.error(traceback.format_exc())
        
if __name__ == "__main__":
    main()
