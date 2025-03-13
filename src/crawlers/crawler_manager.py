"""
CrawlerManager - Manages the crawling process using smart components

This module provides functionality to manage the crawling process using
smart components such as URL queue, rate limiter, and content analyzer.
"""

import os
import json
import logging
import shutil
from typing import Dict, List
from src.utils.crawler_components import CrawlerComponents
from src.utils.category_handler import CategoryHandler
from .url_processor import filter_article_urls, save_urls_to_file

logger = logging.getLogger(__name__)

def process_categories(categories: Dict[str, List[str]], args, components: CrawlerComponents, category_handler: CategoryHandler):
    """
    Process all categories and their URLs using smart components.
    
    Args:
        categories: Dictionary mapping categories to lists of URLs
        args: Command-line arguments
        components: Smart crawler components
        category_handler: CategoryHandler instance
    """
    # Temporary directory for intermediate results
    temp_dir = os.path.join(args.output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Initialize URL queue if available
        if components.url_queue:
            process_with_queue(categories, args, components, category_handler, temp_dir)
        else:
            process_traditional(categories, args, components, category_handler, temp_dir)
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary directory: {e}")

def process_with_queue(
    categories: Dict[str, List[str]], 
    args, 
    components: CrawlerComponents,
    category_handler: CategoryHandler,
    temp_dir: str
):
    """
    Process categories using the smart URL queue.
    
    Args:
        categories: Dictionary mapping categories to lists of URLs
        args: Command-line arguments
        components: Smart crawler components
        category_handler: CategoryHandler instance
        temp_dir: Directory for temporary files
    """
    # Add category quotas to URL queue
    category_quotas = {category: args.urls_per_category for category in categories}
    components.url_queue.category_quotas = category_quotas
    
    # Add source URLs to queue with priorities
    for category, source_urls in categories.items():
        for url in source_urls:
            # Skip if URL has been processed
            if category_handler.has_processed_url(url):
                continue
                
            # Give higher priority to known good sources
            priority = 0.5  # Default priority
            if url in category_handler.get_processed_urls(url):
                priority = 0.25  # Higher priority for previously successful sources
                
            components.url_queue.add_url(url, category, priority=priority)
    
    # Process URLs from queue
    while not components.url_queue.is_empty():
        # Check if all categories are complete
        stats = category_handler.get_category_stats()
        if all(cat_data["completion"] >= 100 for cat_data in stats.values()):
            logger.info("All categories have reached their target URL count")
            break
        
        # Get next URL from queue
        next_url_info = components.url_queue.get_next_url()
        if not next_url_info:
            break
            
        url, category, source_url = next_url_info
        logger.info(f"Processing URL: {url} (Category: {category})")
        
        try:
            # Crawl the URL using smart components
            article_urls = crawl_url(url, category, components, args.min_urls_per_source)
            
            if article_urls:
                # Filter and verify URLs
                filtered_urls = process_article_urls(
                    article_urls,
                    url,
                    category,
                    components,
                    args
                )
                
                # Add URLs to category handler
                added_count = category_handler.add_urls(category, filtered_urls, source_url=url)
                logger.info(f"Added {added_count} new URLs to category {category}")
                
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            if components.crawler_state:
                components.crawler_state.record_url_completion(
                    url=url,
                    category=category,
                    success=False,
                    result_data={"error": str(e)}
                )

def process_traditional(
    categories: Dict[str, List[str]], 
    args,
    components: CrawlerComponents,
    category_handler: CategoryHandler,
    temp_dir: str
):
    """
    Process categories using traditional sequential method.
    
    Args:
        categories: Dictionary mapping categories to lists of URLs
        args: Command-line arguments
        components: Smart crawler components
        category_handler: CategoryHandler instance
        temp_dir: Directory for temporary files
    """
    # Load existing URLs if resuming
    if args.resume:
        category_handler.load_existing_urls()
    
    # Process each category sequentially
    for category, urls in categories.items():
        logger.info(f"Processing category: {category} ({len(urls)} source URLs)")
        
        # Skip if category is complete
        if not category_handler.needs_more_urls(category):
            logger.info(f"Category {category} has reached its target URL count, skipping")
            continue
        
        # Process URLs with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_url = {}
            for url in urls:
                # Skip if already processed
                if category_handler.has_processed_url(url):
                    logger.info(f"URL already processed: {url}")
                    continue
                
                future = executor.submit(
                    crawl_url,
                    url,
                    category,
                    components,
                    args.min_urls_per_source
                )
                future_to_url[future] = url
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_urls = future.result()
                    
                    if article_urls:
                        # Filter and verify URLs
                        filtered_urls = process_article_urls(
                            article_urls,
                            url,
                            category,
                            components,
                            args
                        )
                        
                        # Add URLs to category handler
                        category_handler.add_urls(category, filtered_urls, source_url=url)
                        
                        # Break if we have enough URLs
                        if not category_handler.needs_more_urls(category):
                            logger.info(f"Reached target URL count for {category}")
                            break
                            
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    if components.crawler_state:
                        components.crawler_state.record_url_completion(
                            url=url,
                            category=category,
                            success=False,
                            result_data={"error": str(e)}
                        )

def process_article_urls(
    article_urls: Set[str],
    source_url: str,
    category: str,
    components: CrawlerComponents,
    args
) -> Set[str]:
    """
    Filter and verify article URLs using smart components.
    
    Args:
        article_urls: Set of URLs to process
        source_url: Source URL these were collected from
        category: Category being processed
        components: Smart crawler components
        args: Command-line arguments
        
    Returns:
        Set of verified article URLs
    """
    domain = urlparse(source_url).netloc
    filtered_urls = filter_article_urls(list(article_urls), domain)
    verified_urls = set()
    
    for url in filtered_urls:
        # Skip if already processed
        if components.crawler_state and components.crawler_state.has_processed_url(url):
            continue
        
        # Verify content quality if enabled
        if args.quality_threshold > 0 and components.quality_analyzer:
            try:
                is_quality, metadata = verify_url_quality(url, components, threshold=args.quality_threshold)
                if not is_quality:
                    logger.debug(f"Skipping low quality URL: {url} ({metadata.get('reason', 'Unknown reason')})")
                    continue
            except Exception as e:
                logger.warning(f"Error verifying quality for {url}: {e}")
                continue
        
        verified_urls.add(url)
    
    logger.info(f"Verified {len(verified_urls)} out of {len(filtered_urls)} article URLs from {source_url}")
    return verified_urls

def crawl_url(url: str, category: str, components: CrawlerComponents, min_urls_per_source: int = 50) -> Set[str]:
    """Crawl a specific URL using components."""
    try:
        # Use rate limiter
        if components.rate_limiter:
            components.rate_limiter.wait()
            
        # Get browser from pool
        browser = components.browser_manager.get_browser() if components.browser_manager else None
        
        # Crawl using appropriate crawler
        article_urls = components.url_fetcher.fetch_urls(url, browser)
        
        # Filter URLs using domain-specific rules
        domain = urlparse(url).netloc
        filtered_urls = filter_article_urls(list(article_urls), domain)
        
        # Update state
        if components.crawler_state:
            components.crawler_state.record_url_completion(
                url=url,
                category=category,
                success=True,
                result_data={"urls_found": len(filtered_urls)}
            )
            
        return filtered_urls
        
    except Exception as e:
        logger.error(f"Error crawling {url}: {e}")
        if components.crawler_state:
            components.crawler_state.record_url_completion(
                url=url,
                category=category,
                success=False,
                result_data={"error": str(e)}
            )
        return set()
    finally:
        if browser:
            components.browser_manager.return_browser(browser)