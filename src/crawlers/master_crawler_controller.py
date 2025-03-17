#!/usr/bin/env python3
"""
Master Crawler Controller

This module provides a centralized way to run all crawlers for specific categories.
It handles URL saving and the coordination of multiple crawler types.
"""

import os
import sys
import time
import json
import argparse
import inspect
import logging
import traceback
import importlib
from typing import List, Dict, Set, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import platform
from urllib.parse import urlparse

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.utils.log_utils import get_crawler_logger
from src.utils.source_manager import get_source_urls, get_site_categories, default_source_manager
from src.utils.incremental_saver import IncrementalURLSaver
from src.utils.url_utils import filter_urls  # For URL filtering

# Set up logger
logger = get_crawler_logger("master_controller")

def save_urls(file_path, new_urls):
    """Save URLs with proper merging of existing data"""
    existing_urls = []
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_urls = json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error reading {file_path}, treating as empty")
    
    # Merge URLs and remove duplicates
    all_urls = list(set(existing_urls + new_urls))
    
    # Write to temp file first
    temp_file = f"{file_path}.tmp"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(all_urls, f, indent=2)
    
    # Atomic replace
    os.replace(temp_file, file_path)
    
    logger.info(f"Updated {file_path} with {len(new_urls)} new URLs, total: {len(all_urls)}")
    return len(all_urls)

def check_url_count(file_path, max_urls):
    """Check if the URL count in a file has reached the maximum"""
    if max_urls <= 0:  # No limit
        return False
    
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = json.load(f)
                url_count = len(urls)
                logger.info(f"Current URL count for {os.path.basename(file_path)}: {url_count}/{max_urls}")
                return url_count >= max_urls
        except json.JSONDecodeError:
            logger.error(f"Error reading {file_path}, treating as empty")
    
    return False  # File doesn't exist or is empty

class CrawlerManager:
    """
    Manages and executes multiple crawlers across different categories.
    """
    
    def __init__(self, output_dir: str = "output/urls", log_dir: str = "logs/crawlers",
                max_workers: int = 3):
        """
        Initialize the crawler manager.
        
        Args:
            output_dir: Directory to save URL files
            log_dir: Directory to save log files
            max_workers: Maximum number of concurrent crawler processes
        """
        self.output_dir = output_dir
        self.log_dir = log_dir
        self.max_workers = max_workers
        
        # Create output and log directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        
        # Keep track of loaded crawler modules
        self.crawler_modules = {}
        self.crawler_names = self._discover_crawlers()
        
        # IncrementalURLSaver instances by site name
        self.savers = {}
        
        logger.info(f"CrawlerManager initialized with {len(self.crawler_names)} crawlers")
        logger.info(f"Available crawlers: {', '.join(self.crawler_names)}")
    
    def _discover_crawlers(self) -> List[str]:
        """Discover available crawler modules by scanning the directory."""
        crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")
        crawler_names = []
        
        try:
            for file in os.listdir(crawler_dir):
                if file.endswith("_crawler.py"):
                    # Extract crawler name (e.g., "btv" from "btv_crawler.py")
                    crawler_name = file.replace("_crawler.py", "").lower()
                    if crawler_name:
                        crawler_names.append(crawler_name)
            return sorted(crawler_names)
        except Exception as e:
            logger.error(f"Error discovering crawlers: {e}")
            return []
    
    def _import_crawler_module(self, crawler_name: str):
        """Import a crawler module by name."""
        if crawler_name in self.crawler_modules:
            return self.crawler_modules[crawler_name]
        
        try:
            # Standardize crawler name format
            crawler_name = crawler_name.lower()
            module_name = f"{crawler_name}_crawler"
            crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")

            # Case-insensitive file matching
            module_path = None
            for filename in os.listdir(crawler_dir):
                if filename.lower() == f"{module_name}.py":
                    module_path = os.path.join(crawler_dir, filename)
                    break
            
            if not module_path:
                logger.error(f"Crawler module file not found: {crawler_name}")
                return None
                
            # Using direct Python import mechanism instead of importlib.util
            sys.path.insert(0, os.path.dirname(module_path))
            try:
                module = importlib.import_module(module_name)
                self.crawler_modules[crawler_name] = module
                logger.debug(f"Successfully imported {crawler_name} crawler module")
                return module
            finally:
                # Remove the added path to avoid import conflicts
                if os.path.dirname(module_path) in sys.path:
                    sys.path.remove(os.path.dirname(module_path))
                
        except Exception as e:
            logger.error(f"Failed to import {crawler_name} module: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _get_saver(self, site_name: str) -> IncrementalURLSaver:
        """Get or create an IncrementalURLSaver for a site."""
        if site_name not in self.savers:
            # Create a site-specific logger
            site_logger = get_crawler_logger(site_name)
            
            # Create a new saver instance
            self.savers[site_name] = IncrementalURLSaver(
                output_dir=self.output_dir,
                site_name=site_name,
                backup_interval=20,  # Default to saving every 20 new URLs
                logger=site_logger
            )
            
        return self.savers[site_name]
    
    def _crawl_site(self, crawler_module, site_name: str, category: str, 
                   saver: IncrementalURLSaver, max_urls: int) -> Dict[str, Any]:
        """
        Crawl a single site for a specific category.
        
        Args:
            crawler_module: Imported crawler module
            site_name: Name of the site
            category: Category to crawl
            saver: IncrementalURLSaver instance
            max_urls: Maximum URLs to collect
            
        Returns:
            Dictionary with results for the site
        """
        site_start_time = time.time()
        category_logger = get_crawler_logger(f"category_{category}")
        
        try:
            # Get sources for this category and site
            sources = get_source_urls(category, site_name)
            category_logger.info(f"[SITE:{site_name}] Found {len(sources)} source URLs")
            
            # Get file path for checking URL count
            category_file_path = saver.get_file_path(category)
            
            # Track initial URL count for comparison
            initial_url_count = saver.get_url_count(category)
            category_logger.info(f"[SITE:{site_name}] Initial URL count: {initial_url_count}")
            
            # Track URLs collected for this site
            site_urls = set()
            consecutive_no_new = 0
            max_consecutive_no_new = 3
            
            # Check if we've already reached max_urls before starting
            if check_url_count(category_file_path, max_urls):
                category_logger.info(f"[SITE:{site_name}] Max URLs ({max_urls}) already reached before starting. Skipping.")
                return {
                    "status": "skipped",
                    "reason": "max_urls_reached",
                    "source_count": len(sources),
                    "urls_found": 0,
                    "unique_urls_added": 0,
                    "total_urls": saver.get_url_count(category),
                    "duration_seconds": 0
                }
            
            # Process each source URL
            for source_idx, source_url in enumerate(sources):
                source_start_time = time.time()
                category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}/{len(sources)}] Processing: {source_url}")
                
                # Determine the parameter name for max_urls based on crawler type
                param_name = self._get_crawler_param_name(site_name)
                category_logger.debug(f"[SITE:{site_name}] Using parameter name '{param_name}={max_urls}' for limiting URLs")
                
                try:
                    # Prepare arguments based on parameter inspection
                    kwargs = self._prepare_crawler_arguments(
                        crawler_module.crawl_category,
                        source_url=source_url,
                        category=category,
                        **{param_name: max_urls}
                    )
                    
                    # Add more detailed logging
                    category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Calling crawl_category with args: {kwargs}")
                    
                    # Call crawler
                    crawl_start_time = time.time()
                    urls = crawler_module.crawl_category(**kwargs)
                    crawl_duration = time.time() - crawl_start_time
                    
                    # Add detailed logging about the result
                    if urls is None:
                        category_logger.error(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] crawl_category returned None! Check the crawler implementation.")
                        continue
                    
                    category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] crawl_category returned {type(urls)} with {len(urls) if urls else 0} URLs in {crawl_duration:.2f}s")
                    
                    if urls:
                        # Log a few sample URLs for debugging
                        sample_urls = list(urls)[:3]
                        category_logger.debug(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Sample URLs: {sample_urls}")
                        
                        # Check for new unique URLs
                        old_count = len(site_urls)
                        site_urls.update(urls)
                        new_site_urls = len(site_urls) - old_count
                        
                        if new_site_urls > 0:
                            consecutive_no_new = 0  # Reset counter when new URLs found
                            
                            # Convert to list if needed - ensure we're always passing a list to add_urls
                            urls_list = list(urls) if isinstance(urls, set) else urls
                            
                            # Save the URLs - IMMEDIATE SAVING
                            save_start_time = time.time()
                            added = saver.add_urls(category, urls_list, save_immediately=True)
                            
                            # CRITICAL FIX: Force an immediate save to disk after adding URLs
                            saver.save_to_file(category)
                            
                            save_duration = time.time() - save_start_time
                            
                            category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Added {added} new URLs in {save_duration:.2f}s")
                            category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Crawled {len(urls)} URLs in {crawl_duration:.2f}s")
                            category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Statistics: {new_site_urls} new for site, {added} saved (unique)")
                            
                            # Save using the save_urls function and check total count
                            total_count = save_urls(saver.get_file_path(category), urls_list)
                            category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Total URLs after save: {total_count}")
                            
                            # Check if we've hit the max_urls limit
                            if max_urls > 0 and total_count >= max_urls:
                                category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Reached max URLs limit ({max_urls}). Stopping.")
                                break
                                
                        else:
                            # No new unique URLs found
                            consecutive_no_new += 1
                            category_logger.warning(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] No new unique URLs ({consecutive_no_new}/{max_consecutive_no_new})")
                            
                            if consecutive_no_new >= max_consecutive_no_new:
                                category_logger.info(f"[SITE:{site_name}] Stopping after {consecutive_no_new} sources with no new URLs")
                                break
                    else:
                        # No URLs found at all
                        consecutive_no_new += 1
                        category_logger.warning(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] No URLs found after {crawl_duration:.2f}s")
                        
                        if consecutive_no_new >= max_consecutive_no_new:
                            category_logger.info(f"[SITE:{site_name}] Stopping after {consecutive_no_new} sources with no URLs")
                            break
                    
                    # CRITICAL FIX: Force save after EVERY source URL processing, regardless of new URLs
                    category_logger.info(f"[SITE:{site_name}] Forcing save for category {category}")
                    saver.save_to_file(category)
                    
                    # Check if we've hit the max_urls limit after each source URL processing
                    if check_url_count(category_file_path, max_urls):
                        category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Reached max URLs limit ({max_urls}) after processing source. Stopping.")
                        break
                    
                except Exception as e:
                    category_logger.error(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Error: {str(e)}")
                    category_logger.debug(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Traceback: {traceback.format_exc()}")
                    consecutive_no_new += 1  # Count errors as empty results
                    
                    if consecutive_no_new >= max_consecutive_no_new:
                        category_logger.info(f"[SITE:{site_name}] Stopping after {consecutive_no_new} consecutive failures")
                        break
                        
                source_duration = time.time() - source_start_time
                category_logger.info(f"[SITE:{site_name}] [SOURCE:{source_idx+1}] Completed in {source_duration:.2f}s")
            
            # Calculate stats
            final_url_count = saver.get_url_count(category)
            new_urls_added = final_url_count - initial_url_count
            site_duration = time.time() - site_start_time
            
            # CRITICAL FIX: Force save one final time
            category_logger.info(f"[SITE:{site_name}] Final save for category {category}")
            saver.save_to_file(category)
            
            save_urls(saver.get_file_path(category), list(site_urls))
            
            return {
                "status": "success",
                "source_count": len(sources),
                "urls_found": len(site_urls),
                "unique_urls_added": new_urls_added,
                "total_urls": final_url_count,
                "duration_seconds": site_duration
            }
            
        except Exception as e:
            category_logger.error(f"[SITE:{site_name}] Error processing site: {str(e)}")
            category_logger.debug(f"[SITE:{site_name}] Traceback: {traceback.format_exc()}")
            
            # CRITICAL FIX: Try to save even in case of an error
            try:
                category_logger.info(f"[SITE:{site_name}] Emergency save after error")
                saver.save_to_file(category)
                save_urls(saver.get_file_path(category), list(site_urls))
            except Exception as save_error:
                category_logger.error(f"[SITE:{site_name}] Failed to save after error: {save_error}")
                
            return {
                "status": "error",
                "error": str(e),
                "duration_seconds": time.time() - site_start_time
            }

    def crawl_category(self, category: str, site_filter: Optional[List[str]] = None, 
                      max_urls_per_site: int = -1, max_urls_per_category: int = 2500) -> Dict[str, Any]:
        """
        Crawl a specific category across all sites.
        
        Args:
            category: Category to crawl
            site_filter: Optional list of site names to include (None = all sites)
            max_urls_per_site: Maximum number of URLs to collect per site (-1 = unlimited)
            max_urls_per_category: Maximum total URLs to collect per category (default: 2500)
            
        Returns:
            Dictionary with results by site
        """
        start_time = time.time()
        results = {}
        total_category_urls = 0
        category_logger = get_crawler_logger(f"category_{category}")
        
        # Get output file path for checking total URL count
        category_file_path = os.path.join(self.output_dir, f"{category}.json")
        
        # Check if we've already reached max_urls_per_category before starting
        if check_url_count(category_file_path, max_urls_per_category):
            category_logger.info(f"[CATEGORY:{category}] Max URLs ({max_urls_per_category}) already reached before starting. Skipping.")
            return {
                "summary": {
                    "category": category,
                    "success_count": 0,
                    "error_count": 0,
                    "total_urls_collected": self._get_actual_url_count(category_file_path),  # Changed this to use a method for getting count
                    "total_duration_seconds": 0,
                    "status": "skipped",
                    "reason": "max_urls_reached"
                }
            }
        
        # Get all sites that have sources for this category
        available_sites = []
        for crawler_name in self.crawler_names:
            sources = get_source_urls(category, crawler_name)
            if sources:
                if site_filter and crawler_name not in site_filter:
                    category_logger.info(f"Skipping {crawler_name} (not in filter)")
                    continue
                available_sites.append(crawler_name)
        
        category_logger.info(f"[CATEGORY:{category}] Starting crawl across {len(available_sites)} sites: {', '.join(available_sites)}")
        
        # Process sites in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Keep track of all running futures
            future_to_site = {}
            
            # Start crawling for each site
            for site_name in available_sites:
                # Skip if we've already hit the category URL limit
                if check_url_count(category_file_path, max_urls_per_category):
                    category_logger.info(f"[CATEGORY:{category}] Reached URL limit ({max_urls_per_category}). Skipping {site_name}.")
                    continue
                    
                category_logger.info(f"[SITE:{site_name}] Starting crawler for category '{category}'")
                
                # Import the crawler module
                crawler_module = self._import_crawler_module(site_name)
                if not crawler_module:
                    category_logger.error(f"[SITE:{site_name}] Failed to import crawler module")
                    results[site_name] = {"status": "error", "error": "Module import failed"}
                    continue
                
                # Check for required function
                if not hasattr(crawler_module, 'crawl_category'):
                    category_logger.error(f"[SITE:{site_name}] Crawler module missing crawl_category function")
                    results[site_name] = {"status": "error", "error": "Missing crawl_category function"}
                    continue
                
                # Get or create incremental saver
                saver = self._get_saver(site_name)
                
                # Calculate remaining URLs we can collect for this category
                remaining_urls = max_urls_per_category - total_category_urls if max_urls_per_category > 0 else -1
                
                # Adjust max_urls_per_site based on remaining category limit
                effective_max_urls = min(max_urls_per_site, remaining_urls) if remaining_urls > 0 and max_urls_per_site > 0 else \
                                    remaining_urls if remaining_urls > 0 else max_urls_per_site
                
                category_logger.info(f"[SITE:{site_name}] URL limit set to {effective_max_urls if effective_max_urls > 0 else 'unlimited'}")
                
                # Submit the task to the executor
                future = executor.submit(
                    self._crawl_site, 
                    crawler_module, 
                    site_name, 
                    category, 
                    saver, 
                    effective_max_urls
                )
                future_to_site[future] = site_name
                
            # Process results as they complete
            for future in as_completed(future_to_site):
                site_name = future_to_site[future]
                try:
                    site_result = future.result()
                    results[site_name] = site_result
                    
                    # Update total category URLs
                    urls_added = site_result.get("unique_urls_added", 0)
                    total_category_urls += urls_added
                    
                    category_logger.info(f"[SITE:{site_name}] Added {urls_added} URLs, category total now: {total_category_urls}")
                    
                    # Check if we've hit the category limit by reading the actual file
                    if check_url_count(category_file_path, max_urls_per_category):
                        category_logger.info(f"[CATEGORY:{category}] Reached URL limit ({max_urls_per_category}). Cancelling remaining tasks.")
                        
                        # Cancel remaining tasks
                        for f in future_to_site:
                            if not f.done():
                                f.cancel()
                        break
                        
                except Exception as e:
                    category_logger.error(f"[SITE:{site_name}] Error: {str(e)}")
                    category_logger.debug(f"[SITE:{site_name}] Traceback: {traceback.format_exc()}")
                    results[site_name] = {
                        "status": "error",
                        "error": str(e)
                    }

        # Get actual URL count from file
        final_url_count = 0
        if os.path.exists(category_file_path):
            try:
                with open(category_file_path, 'r') as f:
                    final_url_count = len(json.load(f))
            except:
                category_logger.error(f"Error reading final URL count from {category_file_path}")
        
        # Calculate overall statistics
        total_duration = time.time() - start_time
        success_count = sum(1 for site in results.values() if site.get("status") == "success")
        error_count = sum(1 for site in results.values() if site.get("status") == "error")
        
        # Add summary to results
        results["summary"] = {
            "category": category,
            "success_count": success_count,
            "error_count": error_count,
            "total_urls_collected": final_url_count,
            "total_duration_seconds": total_duration
        }
        
        category_logger.info(f"[CATEGORY:{category}] Crawl completed in {total_duration:.2f}s")
        category_logger.info(f"[CATEGORY:{category}] Success: {success_count} sites, Errors: {error_count} sites")
        category_logger.info(f"[CATEGORY:{category}] Total URLs collected: {final_url_count}")
        
        return results
    
    def crawl_all_categories(self, category_filter: Optional[List[str]] = None, 
                            site_filter: Optional[List[str]] = None,
                            max_urls_per_site: int = -1,
                            max_urls_per_category: int = 2500) -> Dict[str, Any]:
        """
        Crawl all available categories across all sites.
        
        Args:
            category_filter: Optional list of categories to include (None = all categories)
            site_filter: Optional list of site names to include (None = all sites)
            max_urls_per_site: Maximum number of URLs to collect per site (-1 = unlimited)
            max_urls_per_category: Maximum total URLs to collect per category (default: 2500)
            
        Returns:
            Dictionary with results by category and site
        """
        start_time = time.time()
        results = {}
        
        # Get all available categories
        all_categories = default_source_manager.get_categories()
        categories_to_crawl = category_filter or all_categories
        
        # Log the plan
        logger.info(f"Starting crawl of {len(categories_to_crawl)} categories")
        if category_filter:
            logger.info(f"Category filter active: {', '.join(category_filter)}")
        if site_filter:
            logger.info(f"Site filter active: {', '.join(site_filter)}")
        if max_urls_per_site > 0:
            logger.info(f"URL limit per site: {max_urls_per_site}")
        if max_urls_per_category > 0:
            logger.info(f"URL limit per category: {max_urls_per_category}")
        
        # Process each category one at a time
        for idx, category in enumerate(categories_to_crawl):
            logger.info(f"Processing category {idx+1}/{len(categories_to_crawl)}: {category}")
            
            try:
                category_results = self.crawl_category(
                    category=category,
                    site_filter=site_filter,
                    max_urls_per_site=max_urls_per_site,
                    max_urls_per_category=max_urls_per_category
                )
                results[category] = category_results
                
                # Save incremental results after each category
                self._save_results_to_file(results, "master_crawler_results.json")
                
            except Exception as e:
                logger.error(f"Error processing category {category}: {e}")
                logger.error(traceback.format_exc())
                results[category] = {"status": "error", "error": str(e)}
                
            # Force all savers to save their current state
            for site_name, saver in self.savers.items():
                saver.save_all_categories()
        
        # Calculate overall statistics
        total_duration = time.time() - start_time
        category_success = sum(1 for cat, data in results.items() 
                            if "summary" in data and data["summary"]["success_count"] > 0)
        category_errors = len(categories_to_crawl) - category_success
        total_urls = sum(data["summary"]["total_urls_collected"] for cat, data in results.items() 
                         if "summary" in data)
        
        # Add summary to results
        results["overall_summary"] = {
            "total_categories": len(categories_to_crawl),
            "categories_with_success": category_success,
            "categories_with_errors": category_errors,
            "total_urls_collected": total_urls,
            "total_duration_seconds": total_duration,
            "completion_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save final results
        self._save_results_to_file(results, "master_crawler_results.json")
        
        logger.info(f"Crawl completed in {total_duration:.1f}s")
        logger.info(f"Categories: {category_success} success, {category_errors} with errors")
        logger.info(f"Total URLs collected: {total_urls}")
        
        return results
    
    def _save_results_to_file(self, results: Dict, filename: str):
        """Save results to a JSON file."""
        try:
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.debug(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving results to {filename}: {e}")
    
    def _get_crawler_param_name(self, site_name: str) -> str:
        """
        Determine the parameter name for max_urls based on crawler type.
        Different crawlers use different parameter names.
        """
        param_mapping = {
            "rfanews": "max_clicks",
            "postkhmer": "max_click",
            "kohsantepheapdaily": "max_scroll",
            # All others default to "max_pages"
        }
        return param_mapping.get(site_name.lower(), "max_pages")
    
    def _prepare_crawler_arguments(self, func, **kwargs):
        """
        Prepare arguments for crawler function based on its signature.
        Only pass arguments that the function accepts.
        """
        try:
            # Inspect the function signature
            sig = inspect.signature(func)
            valid_params = sig.parameters.keys()
            
            # Special parameter mapping for different crawlers
            # This handles crawlers that expect 'url' instead of 'source_url'
            if 'url' in valid_params and 'source_url' in kwargs and 'url' not in kwargs:
                kwargs['url'] = kwargs['source_url']
            
            # Handle sites that use different parameter names for the category
            if 'category' in kwargs:
                # Some crawlers use 'cat' instead of 'category'
                if 'cat' in valid_params and 'category' not in valid_params:
                    kwargs['cat'] = kwargs['category']
                    kwargs.pop('category', None)  # Remove 'category' if not in valid params
            
            # Filter kwargs to only include valid parameters
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
            
            # Log prepared arguments for debugging
            param_str = ", ".join(f"{k}={v}" for k, v in filtered_kwargs.items())
            logger.debug(f"Prepared arguments: {param_str}")
            
            return filtered_kwargs
            
        except Exception as e:
            logger.error(f"Error preparing arguments: {e}")
            logger.debug(traceback.format_exc())
            # Fall back to original kwargs
            return kwargs
    
    def cleanup(self):
        """Clean up resources before exit."""
        # Save all data from savers
        for site_name, saver in self.savers.items():
            logger.info(f"Finalizing saver for {site_name}")
            saver.save_all_categories()

    # Add a helper method for getting actual URL count from file
    def _get_actual_url_count(self, file_path: str) -> int:
        """Get the actual URL count from a file."""
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return len(json.load(f))
            except Exception as e:
                logger.error(f"Error reading URL count from {file_path}: {e}")
        return 0

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Master Crawler Controller")
    parser.add_argument("--category", dest="category", help="Specific category to crawl")
    parser.add_argument("--categories", dest="categories", nargs="+", help="List of categories to crawl")
    parser.add_argument("--sites", dest="sites", nargs="+", help="List of sites/crawlers to use")
    parser.add_argument("--max-urls", dest="max_urls", type=int, default=-1, 
                       help="Maximum URLs per site (-1 for unlimited)")
    parser.add_argument("--max-urls-per-category", dest="max_urls_per_category", type=int, default=2500,
                       help="Maximum URLs per category (default: 2500, -1 for unlimited)")
    parser.add_argument("--workers", dest="max_workers", type=int, default=4,
                       help="Maximum concurrent workers")
    parser.add_argument("--output-dir", dest="output_dir", default="output/urls",
                       help="Output directory for URL files")
    parser.add_argument("--log-dir", dest="log_dir", default="logs/crawlers",
                       help="Output directory for log files")
    parser.add_argument("--list", dest="list_mode", action="store_true",
                       help="List available categories and sites and exit")
    return parser.parse_args()

def show_available_options():
    """Show available categories and sites."""
    print("\n=== Available Categories ===")
    categories = default_source_manager.get_categories()
    for category in sorted(categories):
        print(f"  - {category}")
    
    print("\n=== Available Crawlers ===")
    crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")
    crawlers = []
    for file in os.listdir(crawler_dir):
        if file.endswith("_crawler.py"):
            crawler_name = file.replace("_crawler.py", "").lower()
            crawlers.append(crawler_name)
    for crawler in sorted(crawlers):
        print(f"  - {crawler}")
    
    print("\nExample usage:")
    print("  python master_crawler_controller.py --category sport")
    print("  python master_crawler_controller.py --categories sport technology --sites btv dapnews")
    print("  python master_crawler_controller.py --max-urls 100")

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Configure logging to file - update the path to use output/logs
    log_dir = os.path.join("output", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "master_controller.log")
    
    # Set up file handler for logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Print available options if requested
    if args.list_mode:
        show_available_options()
        return
    
    logger.info(f"Master Crawler Controller starting")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Command line arguments: {args}")
    
    # Initialize crawler manager
    manager = CrawlerManager(
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        max_workers=args.max_workers
    )
    
    try:
        # Determine categories to crawl
        if args.category:
            categories = [args.category]
        elif args.categories:
            categories = args.categories
        else:
            categories = None  # All categories
        
        # Run crawler
        results = manager.crawl_all_categories(
            category_filter=categories,
            site_filter=args.sites,
            max_urls_per_site=args.max_urls,
            max_urls_per_category=args.max_urls_per_category
        )
        
        # Check if we have any successful crawls
        if "overall_summary" in results:
            total_urls = results["overall_summary"]["total_urls_collected"]
            logger.info(f"Crawling completed successfully, total URLs: {total_urls}")
        else:
            logger.warning("Crawling completed but no summary found in results")
            
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user. Cleaning up...")
    except Exception as e:
        logger.error(f"Error during crawling: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up resources
        manager.cleanup()
        logger.info("Master Crawler Controller finished")

if __name__ == "__main__":
    main()
