import os
import sys
import time
from typing import Set, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
import re
import traceback

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
crawler_dir = os.path.dirname(current_dir)
src_dir = os.path.dirname(crawler_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

# Now imports will work whether script is run directly or through master controller
from src.utils.chrome_setup import setup_chrome_driver
from src.utils.log_utils import get_crawler_logger
from src.utils.page_utils import fetch_page
from src.utils.url_utils import extract_urls_with_pattern, filter_urls
from src.crawlers.crawler_commons import generic_category_crawler
from src.utils.source_manager import get_source_urls, get_site_categories
from src.utils.cmd_utils import parse_crawler_args, get_categories_from_args

# Initialize logger
logger = get_crawler_logger('btv')

def extract_btv_urls(html: str, base_url: str) -> Set[str]:
    """Extract article URLs from page HTML."""
    urls = set()
    soup = BeautifulSoup(html, "html.parser")
    
    # Log extensive details about the HTML for debugging
    logger.info(f"Extracting URLs from HTML (length: {len(html)}, title: {soup.title.text if soup.title else 'None'})")
    
    # Collect all potential article URLs first
    potential_urls = set()
    
    # Approach 1: Direct article links with numeric ID pattern
    article_links = soup.select("a[href*='/article/']")
    logger.info(f"Found {len(article_links)} article links with article pattern")
    for a_tag in article_links:
        if href := a_tag.get("href"):
            url = urljoin(base_url, href)
            potential_urls.add(url)
    
    # Approach 2: Extract article IDs from social sharing links
    for link in soup.select("a[href*='sharer'], a[href*='share']"):
        href = link.get("href")
        if href:
            # Extract the embedded BTV URL from sharing links
            embedded_url = None
            if "u=" in href:
                # Format: ?u=https://btv.com.kh/article/69469/
                parts = href.split("u=")
                if len(parts) > 1:
                    embedded_url = parts[1].split("&")[0]
            elif "url=" in href:
                # Format: ?url=https://btv.com.kh/article/69469
                parts = href.split("url=")
                if len(parts) > 1:
                    embedded_url = parts[1].split("&")[0]
                
            if embedded_url and "btv.com.kh/article/" in embedded_url:
                potential_urls.add(embedded_url)
    
    # Extract only the article IDs and create clean URLs
    btv_domain = 'btv.com.kh'
    for url in potential_urls:
        if match := re.search(r'/article/(\d+)', url):
            article_id = match.group(1)
            clean_url = f"https://{btv_domain}/article/{article_id}/"
            urls.add(clean_url)
    
    # Log results
    logger.info(f"Extracted {len(urls)} clean article URLs from {len(potential_urls)} potential URLs")
    if urls:
        logger.info(f"Sample clean URLs: {list(urls)[:3]}")
    
    return urls

def filter_btv_urls(urls: Set[str], category: str) -> list:
    """
    Filter BTV URLs to ensure only valid article URLs are returned.
    
    Args:
        urls: Set of URLs to filter
        category: Category being crawled
        
    Returns:
        Filtered list of URLs
    """
    if not urls:
        return []
    
    logger.info(f"Starting filter with {len(urls)} URLs")
    
    # Define BTV domain
    btv_domain = 'btv.com.kh'
    
    # Standardize all URLs to the same format: https://btv.com.kh/article/{id}/
    result = set()
    for url in urls:
        # Ensure URL is from BTV domain
        parsed = urlparse(url)
        if not parsed.netloc.endswith('btv.com.kh'):
            logger.debug(f"Skipping non-BTV URL: {url}")
            continue
            
        # Check for article pattern
        if match := re.search(r'/article/(\d+)', url):
            article_id = match.group(1)
            # Ensure URL has consistent format with trailing slash
            clean_url = f"https://{btv_domain}/article/{article_id}/"
            result.add(clean_url)
        else:
            logger.debug(f"Skipping non-article URL: {url}")
            
    logger.info(f"Standardized to {len(result)} article URLs")
    
    # Filter out pagination, category, tag, and search pages
    filtered_result = set()
    for url in result:
        # Skip URLs with pagination parameters
        if "?page=" in url or "&page=" in url:
            logger.debug(f"Skipping pagination URL: {url}")
            continue
            
        # Skip URLs with common non-article patterns
        if any(pattern in url for pattern in ['/category/', '/tag/', '/search/', '/page/']):
            logger.debug(f"Skipping non-article section URL: {url}")
            continue
        
        # Include the URL if it passes all filters
        filtered_result.add(url)
    
    # Log some sample results for debugging
    if filtered_result:
        sample = list(filtered_result)[:5]
        logger.debug(f"Sample filtered URLs: {sample}")
    else:
        logger.warning(f"All URLs were filtered out")
    
    logger.info(f"Filtered {len(urls)} URLs down to {len(filtered_result)} valid articles")
    return list(filtered_result)  # Convert set to list before returning

def crawl_category(source_url: str, category: str, max_pages: int = -1) -> Set[str]:
    """
    Crawl a category from source URL using the generic crawler.
    
    Args:
        source_url: The base URL for the category
        category: Category being crawled
        max_pages: Maximum number of pages to crawl (default: -1 for unlimited)
    
    Returns:
        Set of collected and filtered URLs
    """
    logger.info(f"STARTING BTV CRAWL: Category={category}, URL={source_url}, MaxPages={max_pages}")
    
    try:
        # Direct browser-based crawling for more reliability
        driver = setup_chrome_driver(
            headless=True, 
            disable_images=True, 
            random_user_agent=True
        )
        
        try:
            all_urls = set()
            page_num = 1
            consecutive_empty = 0
            max_consecutive_empty = 3
            
            # Output file path for this category
            output_file = os.path.join("output/urls", f"{category}.json")
            
            # Process first page
            logger.info(f"Loading page 1: {source_url}")
            driver.get(source_url)
            time.sleep(5)  # Wait for page to load
            
            # Extract URLs from first page
            html = driver.page_source
            first_page_urls = extract_btv_urls(html, source_url)
            all_urls.update(first_page_urls)
            logger.info(f"Found {len(first_page_urls)} URLs on page 1")
            
            # SAVE AFTER FIRST PAGE
            if first_page_urls:
                filtered_urls = filter_btv_urls(first_page_urls, category)
                if filtered_urls:
                    from src.crawlers.master_crawler_controller import save_urls
                    save_urls(output_file, filtered_urls)
                    logger.info(f"Saved {len(filtered_urls)} URLs after page 1")
            
            # Check if we should stop based on max_pages
            if max_pages == 1:
                logger.info("Reached max_pages=1, stopping")
                return filter_btv_urls(all_urls, category)
            
            # Process pagination
            while consecutive_empty < max_consecutive_empty and (max_pages == -1 or page_num < max_pages):
                page_num += 1
                
                # Construct pagination URL (BTV uses ?page=X format)
                if '?' in source_url:
                    page_url = f"{source_url}&page={page_num}"
                else:
                    page_url = f"{source_url}?page={page_num}"
                
                logger.info(f"Loading page {page_num}: {page_url}")
                
                try:
                    driver.get(page_url)
                    time.sleep(5)  # Wait for page to load
                    
                    # Extract URLs
                    html = driver.page_source
                    page_urls = extract_btv_urls(html, page_url)
                    
                    # Check for new URLs
                    old_count = len(all_urls)
                    all_urls.update(page_urls)
                    new_urls = len(all_urls) - old_count
                    
                    if new_urls > 0:
                        logger.info(f"Found {len(page_urls)} URLs on page {page_num}, {new_urls} new unique")
                        consecutive_empty = 0
                        
                        # SAVE AFTER EACH PAGE WITH NEW URLS
                        filtered_urls = filter_btv_urls(page_urls, category)
                        if filtered_urls:
                            from src.crawlers.master_crawler_controller import save_urls
                            save_urls(output_file, filtered_urls)
                            logger.info(f"Saved {len(filtered_urls)} URLs after page {page_num}")
                    else:
                        consecutive_empty += 1
                        logger.warning(f"No new URLs on page {page_num} ({consecutive_empty}/{max_consecutive_empty})")
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {e}")
                    consecutive_empty += 1
                
                # Check if we should stop
                if consecutive_empty >= max_consecutive_empty:
                    logger.info(f"Stopping after {consecutive_empty} consecutive pages with no new URLs")
                    break
            
            # Apply filtering before returning
            return filter_btv_urls(all_urls, category)
        
        finally:
            if driver:
                driver.quit()
        
    except Exception as e:
        logger.error(f"Error during crawl: {str(e)}")
        logger.error(traceback.format_exc())
        return set()  # Return empty set on error

def test_btv_crawler(category: str = "sport", max_pages: int = 3, source_url: str = None):
    """
    Run a standalone test for the BTV crawler.
    
    Args:
        category: Category to crawl
        max_pages: Maximum pages to crawl
        source_url: Source URL (if None, will be fetched from source manager)
    """
    logger.info(f"===== TESTING BTV CRAWLER =====")
    logger.info(f"Category: {category}, MaxPages: {max_pages}")
    
    if not source_url:
        sources = get_source_urls(category, "btv")
        if not sources:
            logger.error(f"No sources found for category '{category}'")
            return
        source_url = sources[0]
    
    logger.info(f"Source URL: {source_url}")
    
    # Run the crawler
    start_time = time.time()
    urls = crawl_category(source_url, category, max_pages)
    duration = time.time() - start_time
    
    # Display results
    logger.info(f"===== TEST RESULTS =====")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"URLs found: {len(urls)}")
    
    if urls:
        logger.info("Sample URLs:")
        for i, url in enumerate(list(urls)[:10]):  # Show up to 10 URLs
            logger.info(f"  {i+1}. {url}")
    else:
        logger.error("No URLs found!")

def main():
    """Main entry point for the BTV crawler."""
    parser = argparse.ArgumentParser(description="BTV News Crawler")
    parser.add_argument("--category", default="sport", help="Category to crawl")
    parser.add_argument("--pages", type=int, default=3, help="Maximum pages to crawl")
    parser.add_argument("--url", help="Custom source URL (optional)")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    args = parser.parse_args()
    
    if args.test:
        test_btv_crawler(args.category, args.pages, args.url)
        return
    
    # Regular crawler execution
    logger.info("Starting BTV crawler")
    
    # Parse command line arguments using the utility
    cmd_args = parse_crawler_args("btv")
    
    # All URLs collected (used only for standalone run)
    all_urls = {}
    
    try:
        # Get categories using the utility
        cmd_args["site_name"] = "btv"
        categories = get_categories_from_args(cmd_args)
        
        # Process each category
        for category in categories:
            all_urls[category] = set()
            # Get source URLs for this category
            sources = get_source_urls(category, "btv")
            if not sources:
                logger.warning(f"No source URLs found for category: {category}")
                continue
                
            for source_url in sources:
                logger.info(f"Starting crawl of {category} from {source_url}")
                urls = crawl_category(source_url, category, max_pages=cmd_args["max_pages"])
                all_urls[category].update(urls)
                logger.info(f"Found {len(urls)} URLs for {category}, total in category: {len(all_urls[category])}")
    
        # Print summary
        logger.info("Crawling complete. Summary:")
        total_count = 0
        for cat, urls in all_urls.items():
            count = len(urls)
            total_count += count
            logger.info(f"  {cat}: {count} URLs")
        logger.info(f"Total URLs collected: {total_count}")
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
