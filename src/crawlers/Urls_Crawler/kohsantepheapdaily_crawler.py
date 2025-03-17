import warnings
warnings.filterwarnings('ignore', message='.*urllib3 v2 only supports OpenSSL 1.1.1.*')

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import sys
import os
import argparse
import re
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver
from src.utils.log_utils import get_crawler_logger
from src.utils.page_utils import scroll_page
from src.utils.url_utils import extract_urls_with_pattern, filter_urls
from src.crawlers.crawler_commons import generic_category_crawler
from src.utils.incremental_saver import IncrementalURLSaver
from src.utils.source_manager import get_source_urls, get_site_categories
from src.utils.cmd_utils import parse_crawler_args, get_categories_from_args

logger = get_crawler_logger('kohsantepheap')

def setup_selenium():
    """Initialize WebDriver with basic settings"""
    return setup_chrome_driver(
        headless=True,
        disable_images=True,
        random_user_agent=True
    )

def extract_kohsantepheap_urls(html, base_url):
    """Extract article URLs from page"""
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Find all potential article links
    for a_tag in soup.find_all("a", href=True):
        url = urljoin(base_url, a_tag["href"])
        if '/article/' in url or url.endswith('.html'):
            urls.add(url)
            
    return urls

def scrape_page_content(driver, url, category, max_scroll=-1):
    """
    Scrape page content by scrolling and extracting URLs.
    
    Args:
        driver: WebDriver instance
        url: Page URL
        category: Content category
        max_scroll: Maximum scroll attempts (-1 for unlimited)
        
    Returns:
        Set of collected URLs
    """
    all_urls = set()
    scroll_count = 0
    consecutive_no_new = 0
    max_consecutive_no_new = 3
    
    # Output file path for saving URLs incrementally
    output_file = os.path.join("output/urls", f"{category}.json")
    
    # Initial page load
    html = driver.page_source
    initial_urls = extract_kohsantepheap_urls(html, url)
    all_urls.update(initial_urls)
    logger.info(f"Initial page: Found {len(initial_urls)} URLs")
    
    # Save initial URLs
    if initial_urls:
        filtered_urls = filter_kohsantepheap_urls(initial_urls, category)
        if filtered_urls:
            from src.crawlers.master_crawler_controller import save_urls
            save_urls(output_file, filtered_urls)
            logger.info(f"Saved {len(filtered_urls)} URLs from initial page")
    
    # Scroll and collect more URLs
    while (max_scroll == -1 or scroll_count < max_scroll) and consecutive_no_new < max_consecutive_no_new:
        old_count = len(all_urls)
        scroll_page(driver)
        scroll_count += 1
        
        # Extract new URLs
        html = driver.page_source
        new_urls = extract_kohsantepheap_urls(html, url)
        all_urls.update(new_urls)
        
        # Check if we found new URLs
        new_count = len(all_urls) - old_count
        if new_count > 0:
            logger.info(f"Scroll {scroll_count}: Found {new_count} new URLs")
            consecutive_no_new = 0
            
            # Save after each scroll that yields new URLs
            filtered_urls = filter_kohsantepheap_urls(new_urls, category)
            if filtered_urls:
                from src.crawlers.master_crawler_controller import save_urls
                save_urls(output_file, filtered_urls)
                logger.info(f"Saved {len(filtered_urls)} URLs after scroll {scroll_count}")
        else:
            consecutive_no_new += 1
            logger.info(f"Scroll {scroll_count}: No new URLs found (attempt {consecutive_no_new}/{max_consecutive_no_new})")
            
        # Short delay between scrolls
        time.sleep(2)
    
    logger.info(f"Completed: {scroll_count} scrolls, found {len(all_urls)} total URLs")
    # Final save
    filtered_urls = filter_kohsantepheap_urls(all_urls, category)
    if filtered_urls:
        from src.crawlers.master_crawler_controller import save_urls
        save_urls(output_file, filtered_urls)
        logger.info(f"Final save: {len(filtered_urls)} total URLs")
        
    return all_urls

def filter_kohsantepheap_urls(urls: set, category: str) -> list:
    """
    Filter Kohsantepheap URLs to ensure only valid article URLs are returned.
    
    Args:
        urls: Set of URLs to filter
        category: Category being crawled
        
    Returns:
        Filtered list of URLs
    """
    if not urls:
        return []
    
    # Extract domain from URLs (handles both .com and .com.kh)
    domains = ['kohsantepheap.com.kh', 'kohsantepheapdaily.com.kh', 'kohsantepheapdaily.com']
    
    # Basic filtering
    filtered = filter_urls(
        list(urls),
        domain=None,  # We'll check domains manually
        excludes=['/tag/', '/category/', '/author/', '/page/'],
        contains=None
    )
    
    # Further filtering with custom rules
    result = set()
    for url in filtered:
        parsed = urlparse(url)
        
        # Check domain
        if not any(domain in parsed.netloc for domain in domains):
            continue
        
        # Keep article URLs
        if '/article/' in url or url.endswith('.html'):
            result.add(url)
            continue
    
    logger.info(f"Filtered {len(urls)} URLs down to {len(result)} valid articles")
    return list(result)  # Convert set to list before returning

def crawl_category(source_url: str, category: str, max_scroll: int = -1) -> list:
    """
    Crawl a single category page.
    
    Args:
        source_url: URL to crawl (the master controller will send this as source_url)
        category: Category name
        max_scroll: Maximum number of scroll attempts (-1 for unlimited)
    
    Returns:
        List of collected and filtered URLs
    """
    driver = setup_selenium()
    try:
        logger.info(f"Crawling {category}: {source_url}")
        driver.get(source_url)
        time.sleep(5)  # Initial load
        
        urls = scrape_page_content(driver, source_url, category, max_scroll=max_scroll)
        # Apply filtering directly here
        filtered_urls = filter_kohsantepheap_urls(urls, category)
        logger.info(f"Total unique URLs after filtering: {len(filtered_urls)}")
        
        # Final save
        output_file = os.path.join("output/urls", f"{category}.json")
        from src.crawlers.master_crawler_controller import save_urls
        save_urls(output_file, filtered_urls)
        logger.info(f"Final save: {len(filtered_urls)} URLs to {output_file}")
        
        return filtered_urls
        
    except Exception as e:
        logger.error(f"Error crawling {category}: {e}")
        return []
    finally:
        driver.quit()

def main():
    """Main crawler entry point"""
    # Parse command line arguments using the utility
    args = parse_crawler_args("kohsantepheapdaily")
    
    # All URLs collected (used only for standalone run)
    all_urls = {}
    
    try:
        # Get categories from source manager using the utility
        args["site_name"] = "kohsantepheap"
        categories = get_categories_from_args(args)
        
        for category in categories:
            all_urls[category] = set()
            # Get source URLs for this category
            sources = get_source_urls(category, "kohsantepheap")
            if sources:
                for url in sources:
                    logger.info(f"Crawling category {category} from {url}")
                    urls = crawl_category(
                        url, 
                        category, 
                        max_scroll=args["max_scroll"]
                    )
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

