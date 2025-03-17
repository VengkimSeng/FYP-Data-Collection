"""
File processor for the article extractor.

Handles loading URLs from JSON files and processing them using appropriate site extractors.
"""

import os
import json
import time
import random
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
import importlib
import sys

from src.extractors.logger import log_scrape_status, log_debug
from src.extractors.config import CHECKPOINT_FILE, MAX_RETRIES
from src.extractors.utils import load_checkpoint, update_checkpoint, retry_on_exception
from src.extractors.shutdown import check_for_shutdown
from colorama import Fore, Style

def get_extractor_for_domain(domain: str):
    """
    Get the appropriate extractor module for a domain.
    
    Args:
        domain: The domain name (e.g., 'btv.com.kh')
        
    Returns:
        The extractor module if available, otherwise None
    """
    try:
        # Use our adapter to create an extractor that uses the appropriate scraper
        from src.extractors.scrapers.extractor_adapter import create_extractor_for_domain
        return create_extractor_for_domain(domain)
    except ImportError as e:
        log_scrape_status(f"{Fore.RED}Failed to load extractor adapter: {e}{Style.RESET_ALL}")
        return None

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc

def process_url(url: str, category: str, output_dir: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Process a single URL to extract article content.
    
    Args:
        url: URL to process
        category: Category of the URL
        output_dir: Directory to save output files
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary with processing result
    """
    start_time = time.time()
    domain = extract_domain(url)
    
    try:
        # Skip URL if it doesn't look like a valid article URL
        if not url.startswith('http'):
            return {
                'url': url,
                'success': False,
                'error': 'Invalid URL format'
            }
            
        log_debug(f"Processing URL: {url} (domain: {domain}, category: {category})")
        
        # Get the appropriate extractor for this domain
        extractor_module = get_extractor_for_domain(domain)
        
        if not extractor_module:
            return {
                'url': url,
                'success': False,
                'error': f'No extractor available for domain: {domain}'
            }
            
        # Call the extract_article function from the extractor
        if hasattr(extractor_module, 'extract_article'):
            article_data = extractor_module.extract_article(url, category)
            
            if not article_data:
                return {
                    'url': url,
                    'success': False,
                    'error': 'Extractor returned no data'
                }
                
            # Ensure category directory exists
            category_dir = os.path.join(output_dir, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # Generate filename from URL and timestamp
            from hashlib import md5
            url_hash = md5(url.encode()).hexdigest()[:10]
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{category}_{url_hash}_{timestamp}.json"
            filepath = os.path.join(category_dir, filename)
            
            # Save article data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
                
            duration = time.time() - start_time
            if verbose:
                log_scrape_status(f"{Fore.GREEN}✓ {url} -> {filepath} ({duration:.2f}s){Style.RESET_ALL}")
            
            return {
                'url': url,
                'success': True,
                'output_file': filepath,
                'duration': duration
            }
        else:
            return {
                'url': url,
                'success': False,
                'error': f'Extractor module has no extract_article function'
            }
    except Exception as e:
        log_debug(f"Error processing URL {url}: {str(e)}")
        log_debug(traceback.format_exc())
        return {
            'url': url,
            'success': False,
            'error': str(e)
        }

def process_file(filepath: str, output_dir: str = "output/articles", verbose: bool = False) -> Dict[str, Any]:
    """
    Process a JSON file containing URLs for a category.
    
    Args:
        filepath: Path to the JSON file
        output_dir: Directory to save output files
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary with processing statistics
    """
    category = os.path.splitext(os.path.basename(filepath))[0]
    log_scrape_status(f"{Fore.CYAN}Processing category: {category} from {filepath}{Style.RESET_ALL}")
    
    try:
        # Load URLs from file
        with open(filepath, 'r', encoding='utf-8') as f:
            urls = json.load(f)
            
        if not urls:
            return {
                'category': category,
                'total': 0,
                'processed': 0,
                'failed': 0,
                'error': 'No URLs in file'
            }
            
        log_scrape_status(f"Loaded {len(urls)} URLs for category {category}")
        
        # Check for checkpoint
        checkpoint = load_checkpoint()
        processed_urls = checkpoint.get('processed_urls', [])
        
        # Filter out already processed URLs
        remaining_urls = [url for url in urls if url not in processed_urls]
        
        if len(remaining_urls) < len(urls):
            log_scrape_status(f"Resuming {category}: {len(remaining_urls)} URLs remaining out of {len(urls)}")
        
        # Ensure category directory exists
        category_dir = os.path.join(output_dir, category)
        os.makedirs(category_dir, exist_ok=True)
           
        # Process each URL
        processed_count = 0
        failed_count = 0
        
        for i, url in enumerate(remaining_urls):
            # Check for shutdown request periodically
            if i % 10 == 0 and check_for_shutdown():
                log_scrape_status(f"{Fore.YELLOW}Shutdown requested. Stopping processing for {category}.{Style.RESET_ALL}")
                break
                
            # Process the URL
            result = process_url(url, category, output_dir, verbose)
            
            if result['success']:
                processed_count += 1
                # Update checkpoint
                processed_urls.append(url)
                update_checkpoint({'processed_urls': processed_urls})
            else:
                failed_count += 1
                log_scrape_status(f"{Fore.RED}Failed to process {url}: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")
                
            # Sleep briefly to avoid overloading servers
            time.sleep(random.uniform(0.5, 1.0))
        
        # Return processing statistics
        return {
            'category': category,
            'total': len(urls),
            'processed': processed_count,
            'failed': failed_count
        }
    except Exception as e:
        log_scrape_status(f"{Fore.RED}Error processing file {filepath}: {str(e)}{Style.RESET_ALL}")
        log_debug(traceback.format_exc())
        return {
            'category': category,
            'error': str(e)
        }
