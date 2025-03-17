import os
import time
import random
import warnings
import sys
import argparse
import traceback
from urllib.parse import urlparse, urljoin
from typing import Set, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.utils.log_utils import get_crawler_logger
from src.utils.page_utils import click_load_more
from src.utils.url_utils import filter_urls
from src.utils.incremental_saver import IncrementalURLSaver
from src.utils.source_manager import get_source_urls, get_site_categories  # New imports
from src.utils.cmd_utils import parse_crawler_args, get_categories_from_args

# Suppress warnings
warnings.simplefilter('ignore')

logger = get_crawler_logger('rfa')

def setup_driver():
    """Setup WebDriver with standard configuration."""
    logger.info("[SETUP] Initializing WebDriver for RFA News...")
    
    options = {
        "headless": True,
        "disable_images": True,
        "random_user_agent": True,
        "additional_arguments": ["--ignore-certificate-errors"]
    }
    
    driver = setup_chrome_driver(**options)
    logger.info("[SETUP] WebDriver initialized successfully")
    return driver

def filter_article_urls(urls: List[str], base_domain: str, category: str) -> List[str]:
    """
    Filter URLs to keep only article pages from the base domain that match the category.
    
    Args:
        urls: List of URLs to filter
        base_domain: Base domain to match
        category: Category to match
        
    Returns:
        Filtered list of URLs
    """
    logger.info(f"[FILTER] Filtering {len(urls)} URLs for domain {base_domain} and category {category}")
    start_time = time.time()
    
    # Track filtering stats
    stats = {
        "original": len(urls),
        "domain_filtered": 0,
        "path_filtered": 0,
        "category_filtered": 0,
        "final": 0
    }
    
    # Map common category names to RFA URL paths
    category_map = {
        'politic': 'politics',
        'economic': 'economy',
        'technology': 'tech',
        'sport': 'sport',
        'health': 'health',
        'environment': 'environment'
    }
    
    # Get the correct category path
    category_path = category_map.get(category, category)
    logger.debug(f"[FILTER] Mapped category '{category}' to path '{category_path}'")
    
    # Use the shared filter_urls function with RFA-specific criteria
    domain_filtered = filter_urls(
        urls,
        domain=base_domain,
        contains=None,
        excludes=None,
        path_pattern=r".*\.html$"
    )
    
    stats["domain_filtered"] = len(urls) - len(domain_filtered)
    
    # Additional filtering for RFA-specific patterns
    path_filtered = []
    for url in domain_filtered:
        # Skip URLs with parameters suggesting non-articles
        if '?' in url and any(param in url for param in ['s=', 'page=', 'tag=']):
            continue
            
        # Skip gallery pages
        if '/gallery/' in url:
            continue
            
        path_filtered.append(url)
    
    stats["path_filtered"] = len(domain_filtered) - len(path_filtered)
    
    # Filter by category
    result = []
    for url in path_filtered:
        # Match URLs containing the category path
        if f"/khmer/news/{category_path}/" in url:
            result.append(url)
    
    stats["category_filtered"] = len(path_filtered) - len(result)
    stats["final"] = len(result)
    
    filter_time = time.time() - start_time
    logger.info(f"[FILTER] Stats: {stats}")
    logger.info(f"[FILTER] Filtered {len(urls)} URLs down to {len(result)} valid articles in {filter_time:.2f}s")
    
    # Log sample URLs
    if result:
        sample_urls = result[:3]
        logger.debug(f"[FILTER] Sample filtered URLs: {sample_urls}")
    else:
        logger.warning("[FILTER] No URLs passed filtering")
    
    return result

def click_rfa_load_more(driver):
    """Click the 'មើលច្រើនជាងនេះ' (Load More) button using shared function."""
    logger.info("[CLICK] Attempting to click 'Load More' button")
    
    button_selectors = [
        "//button[@aria-label='សូមមើលរឿងច្រើនទៀតអំពីប្រធានបទនេះ']",
        "//button[contains(@class, 'c-button--primary') and .//span[contains(text(), 'មើលច្រើនជាងនេះ')]]",
        "//button[.//span[contains(text(), 'មើលច្រើនជាងនេះ')]]",
        "//button[contains(@class, 'c-button') and contains(@class, 'my-button')]"
    ]
    
    clicked = click_load_more(driver, button_selectors=button_selectors, wait_time=3)
    if clicked:
        logger.info("[CLICK] Successfully clicked 'Load More' button")
    else:
        logger.warning("[CLICK] Failed to click 'Load More' button")
    
    return clicked

def extract_article_urls(driver, base_domain: str, category: str) -> Set[str]:
    """Extract article URLs using BeautifulSoup's direct parsing."""
    start_time = time.time()
    logger.info("[EXTRACT] Extracting article URLs from page")
    
    urls = set()
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Log page structure for debugging
    page_title = soup.title.text.strip() if soup.title else "No title"
    html_length = len(driver.page_source)
    logger.info(f"[EXTRACT] Processing page: '{page_title}' | HTML size: {html_length/1024:.1f}KB | URL: {driver.current_url}")
    
    # Define RFA's specific article patterns
    article_patterns = [
        # Archive page patterns
        {"element": "div", "class": "archive_story"},
        {"element": "div", "class": "archive-story"},
        {"element": "div", "class": "sectionteaser"},
        {"element": "div", "class": "searchresult"},
        # Story grid patterns
        {"element": "div", "class": "story_grid"},
        {"element": "div", "class": "story_teaser"},
    ]
    
    # Try each pattern
    found_elements = 0
    found_links = 0
    
    for pattern in article_patterns:
        elements = soup.find_all(pattern["element"], class_=pattern["class"])
        logger.debug(f"[EXTRACT] Found {len(elements)} elements matching {pattern}")
        found_elements += len(elements)
        
        for element in elements:
            # Look for links within the element
            links = element.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(driver.current_url, href)
                    if base_domain in full_url and ".html" in full_url:
                        urls.add(full_url)
                        found_links += 1
                        
    # Fallback: try direct article links
    if len(urls) == 0:
        logger.warning("[EXTRACT] No URLs found with specific patterns, trying direct HTML links")
        direct_links = soup.find_all('a', href=lambda x: x and '.html' in x)
        for link in direct_links:
            href = link.get('href')
            if href:
                full_url = urljoin(driver.current_url, href)
                if base_domain in full_url:
                    urls.add(full_url)
                    found_links += 1
    
    extraction_time = time.time() - start_time
    logger.info(f"[EXTRACT] Found {len(elements)} elements and {len(urls)} unique URLs in {extraction_time:.2f}s")
    
    # Log sample URLs and more details for debugging
    if urls:
        sample_urls = list(urls)[:3]
        logger.debug(f"[EXTRACT] Sample URLs: {sample_urls}")
    else:
        logger.warning("[EXTRACT] No URLs found on page")
        logger.debug(f"[EXTRACT] Page source preview: {soup.prettify()[:300]}...")
    
    return urls

def crawl_category(url: str, category: str, max_clicks: int = -1) -> Set[str]:
    """
    Crawl a category using both direct article extraction and load more button.
    
    Args:
        url: Category URL to crawl
        category: Category name
        max_clicks: Maximum load more button clicks (-1 for unlimited)
        
    Returns:
        Set of filtered URLs
    """
    start_time = time.time()
    all_urls = set()  # All collected URLs
    filtered_urls = set()  # Only keep filtered URLs
    clicks = 0
    consecutive_empty = 0
    
    # Create output file path for saving URLs incrementally
    output_file = os.path.join("output/urls", f"{category}.json")
    
    logger.info(f"[CRAWL] Starting crawl of '{category}' from URL: {url}")
    logger.info(f"[CRAWL] Configuration - Category: {category}, URL: {url}, Max Clicks: {max_clicks}")
    
    # Extract base domain from URL
    base_domain = urlparse(url).netloc
    logger.info(f"[CRAWL] Base domain: {base_domain}")
    
    driver = setup_driver()
    
    try:
        # Load initial page
        page_start_time = time.time()
        logger.info(f"[CRAWL] Loading initial page: {url}")
        driver.get(url)
        page_load_time = time.time() - page_start_time
        logger.info(f"[CRAWL] Page loaded in {page_load_time:.2f}s, waiting 5s for content")
        time.sleep(5)
        
        # Extract and save URLs from initial page
        initial_urls = extract_article_urls(driver, base_domain, category)
        all_urls.update(initial_urls)
        logger.info(f"[CRAWL] Extracted {len(initial_urls)} URLs from initial page")
        
        # Filter and save initial URLs
        if initial_urls:
            filtered_initial = filter_article_urls(list(initial_urls), base_domain, category)
            filtered_urls.update(filtered_initial)
            
            # Save URLs from initial page
            from src.crawlers.master_crawler_controller import save_urls
            save_urls(output_file, filtered_initial)
            logger.info(f"[CRAWL] Saved {len(filtered_initial)} URLs from initial page")
        
        # Process content and click "load more" button until max clicks or no new content
        while (max_clicks == -1 or clicks < max_clicks) and consecutive_empty < 3:
            click_time_start = time.time()
            
            # Extract URLs from current page state
            new_urls = extract_article_urls(driver, base_domain, category)
            
            # Check if we found new URLs
            old_count = len(all_urls)
            all_urls.update(new_urls)
            new_unique_count = len(all_urls) - old_count
            
            if new_unique_count > 0:
                consecutive_empty = 0
                logger.info(f"[CRAWL] Extracted {len(new_urls)} URLs, {new_unique_count} new unique")
                
                # Filter new URLs and add to filtered set
                filtered = filter_article_urls(list(new_urls), base_domain, category)
                filtered_urls.update(filtered)
                logger.info(f"[CRAWL] Added {len(filtered)} filtered URLs, total filtered: {len(filtered_urls)}")
                
                # Save new URLs immediately
                if filtered:
                    from src.crawlers.master_crawler_controller import save_urls
                    save_urls(output_file, filtered)
                    logger.info(f"[CRAWL] Saved {len(filtered)} new URLs after extraction")
            else:
                consecutive_empty += 1
                logger.warning(f"[CRAWL] No new unique URLs found (attempt {consecutive_empty}/3)")
            
            # Attempt to click "load more" button
            if click_rfa_load_more(driver):
                clicks += 1
                click_time = time.time() - click_time_start
                logger.info(f"[CRAWL] Click #{clicks} successful in {click_time:.2f}s, waiting 5s...")
                time.sleep(5)
                
                # Save URLs after each successful click
                if filtered_urls:
                    from src.crawlers.master_crawler_controller import save_urls
                    save_urls(output_file, list(filtered_urls))
                    logger.info(f"[CRAWL] Saved {len(filtered_urls)} URLs after click #{clicks}")
            else:
                consecutive_empty += 1
                logger.warning(f"[CRAWL] Could not click load more button (attempt {consecutive_empty}/3)")
                
        # Log crawl completion
        crawl_time = time.time() - start_time
        if consecutive_empty >= 3:
            logger.info(f"[CRAWL] Stopped after {consecutive_empty} consecutive pages with no new content")
        elif max_clicks != -1 and clicks >= max_clicks:
            logger.info(f"[CRAWL] Reached maximum click limit ({max_clicks})")
            
        logger.info(f"[CRAWL] Crawl completed in {crawl_time:.2f}s")
        logger.info(f"[CRAWL] Total clicks: {clicks}, raw URLs: {len(all_urls)}, filtered URLs: {len(filtered_urls)}")
        
        # Final save to ensure everything is written to disk
        if filtered_urls:
            from src.crawlers.master_crawler_controller import save_urls
            save_urls(output_file, list(filtered_urls))
            logger.info(f"[CRAWL] Final save: {len(filtered_urls)} URLs to {output_file}")
        
    except Exception as e:
        logger.error(f"[CRAWL] Error during crawl: {str(e)}")
        logger.error(f"[CRAWL] {traceback.format_exc()}")
        
        # Try to save URLs even if there's an error
        if filtered_urls:
            try:
                from src.crawlers.master_crawler_controller import save_urls
                save_urls(output_file, list(filtered_urls))
                logger.info(f"[CRAWL] Emergency save after error: {len(filtered_urls)} URLs to {output_file}")
            except Exception as save_error:
                logger.error(f"[CRAWL] Failed to save after error: {str(save_error)}")
    finally:
        driver.quit()
        logger.info("[CRAWL] WebDriver closed")
        
    return filtered_urls

def main():
    """Main entry point."""
    logger.info("[MAIN] Starting RFA News crawler")
    
    # Parse command line arguments using the utility
    args = parse_crawler_args("rfanews")
    
    # All URLs collected (used only for standalone run)
    all_urls = {}
    
    try:
        # Get categories using the utility
        args["site_name"] = "rfanews"
        categories = get_categories_from_args(args)
        logger.info(f"[MAIN] Crawling {len(categories)} categories: {categories}")
        
        for category in categories:
            all_urls[category] = set()
            try:
                # Get source URLs for this category, try both "rfanews" and "rfa"
                sources = get_source_urls(category, "rfanews")
                if not sources:
                    # Try alternative source name
                    logger.info(f"[MAIN] No sources found for 'rfanews', trying 'rfa'")
                    sources = get_source_urls(category, "rfa")
                
                if sources:
                    logger.info(f"[MAIN] Found {len(sources)} source URLs for category '{category}'")
                    
                    for url in sources:
                        logger.info(f"[MAIN] Processing source: {url}")
                        urls = crawl_category(
                            url, 
                            category,
                            max_clicks=args["max_clicks"]
                        )
                        
                        if urls:
                            all_urls[category].update(urls)
                            logger.info(f"[MAIN] Added {len(urls)} URLs, total for '{category}': {len(all_urls[category])}")
                        else:
                            logger.warning(f"[MAIN] No URLs returned from {url}")
                else:
                    logger.warning(f"[MAIN] No source URLs found for category: {category}")
            except Exception as e:
                logger.error(f"[MAIN] Error processing category {category}: {str(e)}")
                logger.error(f"[MAIN] {traceback.format_exc()}")
                continue
    
        # Print final summary when running standalone
        logger.info("[MAIN] Crawling complete. Summary:")
        total_count = 0
        for cat, urls in all_urls.items():
            count = len(urls)
            total_count += count
            logger.info(f"[MAIN] {cat}: {count} URLs")
        logger.info(f"[MAIN] Total URLs collected: {total_count}")
            
    except Exception as e:
        logger.error(f"[MAIN] Error during crawling: {e}")
        logger.error(f"[MAIN] {traceback.format_exc()}")

if __name__ == "__main__":
    main()
