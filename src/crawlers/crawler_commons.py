"""
Common functions shared across different web crawlers.
"""

import os
import time
import logging
from typing import Set, Dict, List, Optional, Callable
import traceback
from selenium import webdriver

from src.utils.chrome_setup import setup_chrome_driver
from src.utils.page_utils import fetch_page, scroll_page
from src.utils.url_utils import extract_urls_with_pattern, filter_urls

def generic_category_crawler(source_url: str, category: str, 
                           url_extractor: Callable, 
                           max_pages: int = -1,
                           pagination_type: str = 'query',
                           scroll_strategy: str = 'simple',
                           max_consecutive_empty: int = 2,
                           initial_wait: int = 5) -> Set[str]:
    """
    Generic category crawler that can be customized for different sites.
    
    Args:
        source_url: Start URL for the category
        category: Category being crawled
        url_extractor: Function that extracts URLs from HTML
        max_pages: Maximum number of pages to crawl (-1 for unlimited)
        pagination_type: Type of pagination ('query', 'path', 'wordpress')
        scroll_strategy: Scrolling strategy ('simple', 'thorough', 'none')
        max_consecutive_empty: Stop after this many consecutive empty pages
        initial_wait: Initial wait time after page load (seconds)
        
    Returns:
        Set of all collected URLs - No saving to disk (handled by master controller)
    """
    from src.utils.url_utils import construct_pagination_url
    
    all_urls = set()
    driver = None
    page = 1  # Start with page 1
    consecutive_empty = 0
    consecutive_no_new_urls = 0
    start_time = time.time()
    
    # Setup logger with additional info
    logger = logging.getLogger('crawler_commons')
    logger.info(f"[GENERIC] Starting crawl of '{category}' from {source_url}")
    logger.info(f"[GENERIC] Parameters: max_pages={max_pages}, pagination={pagination_type}, scroll={scroll_strategy}")
    
    try:
        # Process the first/main page
        logger.info(f"[GENERIC] [PAGE-1] Accessing {source_url}")
        
        # Log driver setup
        logger.info(f"[GENERIC] [PAGE-1] Setting up WebDriver")
        driver = setup_chrome_driver(
            headless=True, 
            disable_images=True,
            random_user_agent=True
        )
        logger.info(f"[GENERIC] [PAGE-1] WebDriver setup complete")
        
        # Access page and log timings
        page_start_time = time.time()
        logger.info(f"[GENERIC] [PAGE-1] Loading URL: {source_url}")
        driver.get(source_url)
        page_load_time = time.time() - page_start_time
        logger.info(f"[GENERIC] [PAGE-1] Page loaded in {page_load_time:.2f}s, waiting {initial_wait}s for content")
        time.sleep(initial_wait)  # Initial wait
        
        # Log page info
        logger.info(f"[GENERIC] [PAGE-1] Current URL: {driver.current_url}")
        logger.info(f"[GENERIC] [PAGE-1] Page title: {driver.title}")
        
        # Apply scrolling based on strategy
        if scroll_strategy == 'thorough':
            logger.debug(f"[GENERIC] [PAGE-1] Using thorough scrolling strategy")
            scroll_page(driver, max_attempts=-1)
        elif scroll_strategy == 'simple':
            # Simple scrolling
            logger.debug(f"[GENERIC] [PAGE-1] Using simple scrolling strategy (3 scrolls)")
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                logger.debug(f"[GENERIC] [PAGE-1] Scroll #{i+1} complete")
                time.sleep(1)
                
        # Extract URLs from first page
        extraction_start = time.time()
        logger.info(f"[GENERIC] [PAGE-1] Extracting URLs using provided extractor function")
        main_page_urls = url_extractor(driver.page_source, source_url)
        extraction_time = time.time() - extraction_start
        
        if main_page_urls:
            all_urls.update(main_page_urls)
            logger.info(f"[GENERIC] [PAGE-1] Found {len(main_page_urls)} URLs in {extraction_time:.2f}s")
            logger.debug(f"[GENERIC] [PAGE-1] Sample URLs: {list(main_page_urls)[:3]}")
        else:
            logger.warning(f"[GENERIC] [PAGE-1] No URLs found on main page after {extraction_time:.2f}s")
            # Add some debugging info about the page content
            html_length = len(driver.page_source)
            logger.debug(f"[GENERIC] [PAGE-1] Page HTML size: {html_length} bytes")
            if html_length > 0:
                logger.debug(f"[GENERIC] [PAGE-1] Page HTML preview: {driver.page_source[:300]}...")
        
        # Close driver after first page
        logger.info(f"[GENERIC] [PAGE-1] Closing WebDriver")
        driver.quit()
        driver = None
        
        # Continue with pagination if needed
        page = 2
        
        # For unlimited pages, use a large number
        effective_max_pages = 10000 if max_pages == -1 else max_pages
        
        while (page <= effective_max_pages and 
               consecutive_empty < max_consecutive_empty and 
               consecutive_no_new_urls < max_consecutive_empty):
            
            # Construct page URL according to pagination type
            page_url = construct_pagination_url(source_url, page, pagination_type)
            
            logger.info(f"[PAGE-{page}] Accessing {page_url}")
            
            # Initialize driver for this page
            driver = setup_chrome_driver(
                headless=True, 
                disable_images=True,
                random_user_agent=True
            )
            
            try:
                # Fetch and process page
                page_start_time = time.time()
                driver.get(page_url)
                page_load_time = time.time() - page_start_time
                logger.info(f"[PAGE-{page}] Load time: {page_load_time:.2f}s, waiting {initial_wait}s for content")
                time.sleep(initial_wait)
                
                # Apply scrolling
                if scroll_strategy == 'thorough':
                    logger.debug(f"[PAGE-{page}] Using thorough scrolling strategy")
                    scroll_page(driver, max_attempts=-1)
                elif scroll_strategy == 'simple':
                    logger.debug(f"[PAGE-{page}] Using simple scrolling strategy (3 scrolls)")
                    for i in range(3):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        logger.debug(f"[PAGE-{page}] Scroll #{i+1} complete")
                        time.sleep(1)
                
                # Extract URLs
                extraction_start = time.time()
                page_urls = url_extractor(driver.page_source, page_url)
                extraction_time = time.time() - extraction_start
                
                if page_urls:
                    # Check if we got new unique URLs
                    old_count = len(all_urls)
                    all_urls.update(page_urls)
                    new_unique_count = len(all_urls) - old_count
                    
                    if new_unique_count > 0:
                        consecutive_empty = 0
                        consecutive_no_new_urls = 0
                        logger.info(f"[PAGE-{page}] Found {len(page_urls)} URLs, {new_unique_count} new unique in {extraction_time:.2f}s")
                        logger.debug(f"[PAGE-{page}] Sample new URLs: {list(page_urls)[:3]}")
                    else:
                        consecutive_no_new_urls += 1
                        logger.warning(f"[PAGE-{page}] Found {len(page_urls)} URLs but none are new ({consecutive_no_new_urls}/{max_consecutive_empty})")
                else:
                    consecutive_empty += 1
                    logger.warning(f"[PAGE-{page}] No URLs found after {extraction_time:.2f}s ({consecutive_empty}/{max_consecutive_empty})")
                    # Log page title for debugging
                    if driver.title:
                        logger.debug(f"[PAGE-{page}] Page title: {driver.title}")
                
            except Exception as e:
                logger.error(f"[PAGE-{page}] Error: {str(e)}")
                logger.debug(f"[PAGE-{page}] Error details: {traceback.format_exc()}")
                consecutive_empty += 1
            finally:
                if driver:
                    driver.quit()
                    driver = None
            
            # Move to next page
            page += 1
            time.sleep(2)  # Prevent overloading server
            
            # Stop if we've reached circuit breakers
            if consecutive_empty >= max_consecutive_empty:
                logger.info(f"[STOPPING] Reached {consecutive_empty} consecutive empty pages limit")
                break
                
            if consecutive_no_new_urls >= max_consecutive_empty:
                logger.info(f"[STOPPING] Reached {consecutive_no_new_urls} pages with no new URLs limit")
                break
                
    except Exception as e:
        logger.error(f"[ERROR] Crawler exception: {str(e)}")
        logger.debug(f"[ERROR] Traceback: {traceback.format_exc()}")
    finally:
        if driver:
            driver.quit()
    
    # Log summary statistics
    total_time = time.time() - start_time
    pages_crawled = page - 1
    urls_per_page = len(all_urls) / pages_crawled if pages_crawled > 0 else 0
    
    logger.info(f"[COMPLETED] {category} crawl: {len(all_urls)} total URLs from {pages_crawled} pages in {total_time:.2f}s")
    logger.info(f"[STATS] Average: {urls_per_page:.1f} URLs/page, {total_time/pages_crawled:.2f}s/page")
    
    return all_urls
