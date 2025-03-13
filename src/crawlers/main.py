# !/usr/bin/env python3
"""
Master Crawler Controller

This script orchestrates multiple crawlers to extract article URLs from different websites
based on categories defined in categories.json.
"""

import os
import sys
import json
import random
import argparse
import logging
import time
import importlib
import threading
import concurrent.futures
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urlparse
import shutil

# Add the project root and src directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("master_crawler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("master_crawler")

# Local imports (after path setup)
from utils.chrome_setup import setup_chrome_driver, setup_chrome_options
from utils.crawler_components import CrawlerComponents
from crawlers.crawler_utils import check_required_packages, setup_smart_components 
from crawlers.category_handler import CategoryHandler
from crawlers.url_processor import save_urls_to_file, filter_article_urls

# Check for required packages before proceeding
check_required_packages()

# Define required packages
REQUIRED_PACKAGES = ["selenium", "bs4"]

# Check for required packages before proceeding
def check_required_packages():
    """Check if required packages are installed."""
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("\n⚠️  Missing required Python packages ⚠️")
        print("Please install the following packages before running this script:")
        print(f"pip install {' '.join(missing_packages)}")
        print("\nFull installation command:")
        print(f"pip install {' '.join(REQUIRED_PACKAGES)}")
        sys.exit(1)

# Check for required packages before attempting imports
check_required_packages()

# Import the chrome_setup module for driver configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.utils.chrome_setup import setup_chrome_driver, setup_chrome_options

# Add the URL improve directory to the path for importing crawlers
CRAWLERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Urls_Crawler")
sys.path.append(CRAWLERS_DIR)

# Override crawler save functions to redirect output to specified directory
def override_crawler_save_functions(output_dir):
    """Override URL saving functions in crawler modules to use our output directory."""
    try:
        # Override Dapnews_crawler save function
        import crawlers.Urls_Crawler.Dapnews_crawler as Dapnews_crawler
        Dapnews_crawler.save_to_file = lambda category, links: save_urls_to_file(
            links, 
            os.path.join(output_dir, f"{category}.json")
        )
        
        # Override BTV_crawler save function
        import crawlers.Urls_Crawler.BTV_crawler as BTV_crawler
        BTV_crawler.save_to_file = lambda category, links: save_urls_to_file(
            links, 
            os.path.join(output_dir, f"{category}.json")
        )
        
        # Override kohsantepheapdaily_crawler save function
        import crawlers.Urls_Crawler.kohsantepheapdaily_crawler as kohsantepheapdaily_crawler
        kohsantepheapdaily_crawler.save_to_file = lambda category, links: save_urls_to_file(
            links, 
            os.path.join(output_dir, f"{category}.json")
        )
        
        # Override sabaynews_crawler save_urls function
        import crawlers.Urls_Crawler.sabaynews_crawler as sabaynews_crawler
        sabaynews_crawler.save_urls = lambda txt_file, json_file, urls: save_urls_to_file(
            urls,
            os.path.join(output_dir, f"{os.path.basename(json_file).split('_')[0]}.json")
        )
        
        # Override postkhmer_crawler save function
        import crawlers.Urls_Crawler.postkhmer_crawler as postkhmer_crawler
        postkhmer_crawler.save_urls_to_file = lambda file_path, urls: save_urls_to_file(
            urls,
            os.path.join(output_dir, f"{os.path.basename(file_path).split('_')[0]}.json")
        )
        
        # Override rfanews_crawler save function
        import crawlers.Urls_Crawler.rfanews_crawler as rfanews_crawler
        rfanews_crawler.save_to_json = lambda data, filename: save_urls_to_file(
            data,
            os.path.join(output_dir, f"{os.path.basename(filename).split('_')[0]}.json")
        )
        
        logger.info("Successfully overrode crawler save functions to use unified output directory")
    except Exception as e:
        logger.error(f"Error overriding crawler save functions: {e}")

# Try to import the url_saver module (used by some crawlers)
try:
    from src.utils.url_saver import save_urls_to_file
except ImportError:
    # Create a simple version if not available
    def save_urls_to_file(urls, output_path, format_type="json", **kwargs):
        """Simple implementation of save_urls_to_file function."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        unique_urls = list(set(urls))
        if format_type.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(unique_urls, f, ensure_ascii=False, indent=4)
        elif format_type.lower() == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
        logger.info(f"Saved {len(unique_urls)} URLs to {output_path}")
        return True

# Define a mapping of domain patterns to crawler modules
DOMAIN_TO_CRAWLER = {
    "btv.com.kh": "BTV_crawler",
    "rfa.org": "rfanews_crawler",
    "postkhmer.com": "postkhmer_crawler",
    "dap-news.com": "Dapnews_crawler",
    "kohsantepheapdaily.com.kh": "kohsantepheapdaily_crawler",
    "news.sabay.com.kh": "sabaynews_crawler"
}

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Master crawler controller for multiple websites")
    parser.add_argument("--urls-per-category", type=int, default=2500,
                        help="Target number of URLs per category (default: 2500)")
    parser.add_argument("--max-workers", type=int, default=3,
                        help="Maximum number of concurrent crawlers (default: 3)")
    parser.add_argument("--categories-file", type=str, default="config/categories.json",
                        help="Path to categories.json file (default: categories.json)")
    parser.add_argument("--output-dir", type=str, default="output/urls",
                        help="Directory for storing output files (default: Selected_URLs)")
    parser.add_argument("--randomize", action="store_true", default=True,
                        help="Randomize URLs across sources (default: True)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from previous crawl (keeps existing URLs)")
    parser.add_argument("--min-urls-per-source", type=int, default=50,
                        help="Minimum URLs to try extracting from each source (default: 50)")
    return parser.parse_args()

def load_categories(categories_file: str) -> Dict[str, List[str]]:
    """
    Load categories and their URLs from the specified JSON file.
    
    Args:
        categories_file: Path to the categories JSON file
        
    Returns:
        Dictionary mapping category names to lists of URLs
    """
    try:
        with open(categories_file, "r", encoding="utf-8") as f:
            categories = json.load(f)
            
        # Log information about each category and its URLs
        for category, urls in categories.items():
            logger.info(f"Category '{category}': {len(urls)} URLs")
            for url in urls[:3]:  # Log the first 3 URLs of each category
                logger.info(f"  - {url}")
            if len(urls) > 3:
                logger.info(f"  - ... and {len(urls) - 3} more URLs")
                
        return categories
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading categories file '{categories_file}': {e}")
        return {}

def get_crawler_for_url(url: str) -> Optional[str]:
    """
    Determine the appropriate crawler module for a given URL.
    
    Args:
        url: URL to be crawled
        
    Returns:
        Name of the crawler module or None if no match
    """
    try:
        domain = urlparse(url).netloc.lower()
        for pattern, crawler in DOMAIN_TO_CRAWLER.items():
            if pattern in domain:
                return crawler
    except Exception as e:
        logger.error(f"Error determining crawler for URL '{url}': {e}")
    return None

def crawl_url(url: str, category: str, output_dir: str, min_urls_per_source: int = 50) -> Set[str]:
    """
    Crawl a specific URL using the appropriate crawler.
    
    Args:
        url: URL to crawl
        category: Category of the URL
        output_dir: Directory for temporary output files
        min_urls_per_source: Minimum URLs to extract from this source
        
    Returns:
        Set of article URLs found
    """
    crawler_name = get_crawler_for_url(url)
    if not crawler_name:
        logger.warning(f"No suitable crawler found for URL: {url}")
        return set()
    
    logger.info(f"Using {crawler_name} to crawl {url} (category: {category})")
    
    # Temporary output directory for this crawl
    temp_dir = os.path.join(output_dir, f"{int(time.time())}_{crawler_name}")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Try to import the crawler module
        if os.path.exists(os.path.join(CRAWLERS_DIR, f"{crawler_name}.py")):
            sys.path.insert(0, os.path.dirname(CRAWLERS_DIR))  # Add parent directory to path
            crawler_module = importlib.import_module(f"crawlers.Urls_Crawler.{crawler_name}")
            
            # Remove file handlers for postkhmer_crawler to prevent log file creation
            if crawler_name == "postkhmer_crawler" and hasattr(crawler_module, "logger"):
                # Keep only non-file handlers
                crawler_module.logger.handlers = [h for h in crawler_module.logger.handlers 
                                                 if not isinstance(h, logging.FileHandler)]
                logger.info("Disabled file logging for postkhmer_crawler")
            
            # Different crawlers have different APIs, so we'll need to adapt
            collected_urls = set()
            
            if crawler_name == "postkhmer_crawler":
                # PostKhmer crawler has a specific function signature
                driver = setup_chrome_driver(headless=True, disable_images=True)
                try:
                    logger.info(f"Navigating to URL: {url}")
                    driver.get(url)
                    time.sleep(5)
                    output_file = os.path.join(temp_dir, f"{category}_urls.txt")
                    logger.info(f"Executing scrape_page_content for {url}")
                    crawler_module.scrape_page_content(driver, url, output_file)
                    logger.info(f"Completed scraping content from {url}")
                finally:
                    driver.quit()
                
            elif crawler_name == "rfanews_crawler":
                # RFA crawler has a scrape_urls function
                logger.info(f"Starting RFA crawler for {url} with target of {min_urls_per_source} URLs")
                # Fix for RFA crawler - need to handle lack of separate load_progress function
                # by setting up a progress dict manually
                try:
                    category_path = urlparse(url).path.split('/')[-2]  # Extract category from path
                    progress = {
                        "current_url": url,
                        "unique_urls": [],
                        "pages_scraped": 0
                    }
                    # Monkey patch the crawler's load_progress function
                    crawler_module.load_progress = lambda x: progress
                    
                    result = crawler_module.scrape_urls(url, max_urls=min_urls_per_source*2, retry_count=2)
                    output_file = os.path.join(temp_dir, f"{category}_urls.json")
                    save_urls_to_file(result, output_file)
                    collected_urls.update(result)
                except Exception as e:
                    logger.error(f"Error with RFA crawler: {e}")
                
            elif crawler_name == "kohsantepheapdaily_crawler":
                # Kohsantepheap crawler - Working with the actual function name
                shared_links = set()
                lock = threading.Lock()
                logger.info(f"Starting kohsantepheapdaily crawler for {url}")
                
                # Check if the function name is crawl_url or fetch_and_save_links
                if hasattr(crawler_module, "crawl_url"):
                    crawler_module.crawl_url(url, shared_links, lock, category)
                elif hasattr(crawler_module, "fetch_and_save_links"):
                    driver = setup_chrome_driver(headless=True, disable_images=True)
                    try:
                        links = crawler_module.fetch_and_save_links(driver, url, category)
                        shared_links.update(links)
                    finally:
                        driver.quit()
                    
                output_file = os.path.join(temp_dir, f"{category}_urls.json")
                save_urls_to_file(shared_links, output_file)
                collected_urls.update(shared_links)
                
            elif crawler_name == "Dapnews_crawler":
                # Dapnews crawler - Fix import and function call issues
                driver = setup_chrome_driver(headless=True, disable_images=True)
                try:
                    logger.info(f"Starting Dapnews crawler for {url}")
                    from bs4 import BeautifulSoup  # Ensure BeautifulSoup is available
                    html = crawler_module.fetch_page_with_scroll(driver, url)
                    soup = BeautifulSoup(html, "html.parser")
                    links = crawler_module.parse_links(soup, url)
                    output_file = os.path.join(temp_dir, f"{category}_urls.json")
                    save_urls_to_file(links, output_file)
                    collected_urls.update(links)
                finally:
                    driver.quit()
                
            elif crawler_name == "sabaynews_crawler":
                # Sabay news crawler
                logger.info(f"Starting sabaynews crawler for {url}")
                class ConfigMock:
                    chrome_driver_path = None
                    wait_time = 2
                    max_workers = 1
                
                # Special handling for Sabay URLs
                output_prefix = os.path.join(temp_dir, category)
                
                # Adjust URL format - Sabay expects specific formats
                if "topics" in url:
                    topic = url.split("/")[-1]
                    # Remove trailing slash if present
                    topic = topic.rstrip('/')
                    ajax_url = f"https://news.sabay.com.kh/ajax/topics/{topic}"
                    logger.info(f"Adjusted Sabay URL to: {ajax_url}")
                    result = crawler_module.scrape_category(ajax_url, output_prefix, ConfigMock())
                else:
                    result = crawler_module.scrape_category(url, output_prefix, ConfigMock())
                
                # Extract URLs from result files
                if result and "json_file" in result:
                    try:
                        with open(result["json_file"], "r", encoding="utf-8") as f:
                            urls_list = json.load(f)
                            collected_urls.update(urls_list)
                    except Exception as e:
                        logger.error(f"Error loading Sabay result file: {e}")
                
            elif crawler_name == "BTV_crawler":
                # BTV crawler
                shared_links = set()
                lock = threading.Lock()
                
                # For BTV we'll crawl multiple pages to get enough articles
                logger.info(f"Starting BTV crawler for {url}")
                num_pages_to_crawl = max(5, min_urls_per_source // 10)  # Each page has ~10 articles
                
                for page_idx in range(1, num_pages_to_crawl + 1):
                    logger.info(f"Crawling BTV page {page_idx}/{num_pages_to_crawl}")
                    try:
                        crawler_module.crawl_page(url, page_idx, shared_links, lock, category)
                    except Exception as page_error:
                        logger.error(f"Error crawling page {page_idx}: {page_error}")
                    
                    # Check if we have enough URLs already
                    if len(shared_links) >= min_urls_per_source:
                        logger.info(f"Collected enough URLs from BTV: {len(shared_links)}")
                        break
                        
                output_file = os.path.join(temp_dir, f"{category}_urls.json")
                save_urls_to_file(shared_links, output_file)
                collected_urls.update(shared_links)
                
                # If we didn't get enough URLs, try deep crawling more pages
                if len(shared_links) < min_urls_per_source:
                    logger.info(f"Not enough URLs collected from {url}. Attempting deep crawl.")
                    additional_pages_to_crawl = 10
                    for page_idx in range(num_pages_to_crawl + 1, num_pages_to_crawl + additional_pages_to_crawl + 1):
                        logger.info(f"Deep crawling BTV page {page_idx}")
                        try:
                            crawler_module.crawl_page(url, page_idx, shared_links, lock, category)
                        except Exception as page_error:
                            logger.error(f"Error in deep crawl of page {page_idx}: {page_error}")
                        
                        # Check if we have enough URLs now
                        if len(shared_links) >= min_urls_per_source:
                            logger.info(f"Deep crawl: Collected enough URLs: {len(shared_links)}")
                            break
                            
                    # Update output file with additional URLs
                    save_urls_to_file(shared_links, output_file)
                    collected_urls.update(shared_links)
                
            else:
                # Generic approach using the main function
                logger.info(f"Using generic approach for {crawler_name} with {url}")
                original_argv = sys.argv.copy()
                sys.argv = [crawler_name, url, "--output-dir", temp_dir, "--category", category]
                try:
                    if hasattr(crawler_module, "main"):
                        crawler_module.main()
                    else:
                        logger.error(f"No main() function found in {crawler_name}")
                finally:
                    sys.argv = original_argv
            
            # If we still don't have collected URLs, try finding them from the temp directory
            if not collected_urls:
                collected_urls = collect_urls_from_dir(temp_dir, category)
                
            logger.info(f"Collected {len(collected_urls)} URLs from {url}")
            return collected_urls
            
        else:
            logger.error(f"Crawler module {crawler_name}.py not found!")
            return set()
            
    except Exception as e:
        logger.error(f"Error while crawling {url} with {crawler_name}: {e}", exc_info=True)
        return set()

def collect_urls_from_dir(directory: str, category: str = None) -> Set[str]:
    """
    Collect URLs from all files in a directory.
    
    Args:
        directory: Directory containing URL files
        category: Optional category filter
        
    Returns:
        Set of collected URLs
    """
    all_urls = set()
    
    if not os.path.exists(directory):
        return all_urls
        
    for root, _, files in os.walk(directory):
        for file in files:
            # Only process JSON and TXT files
            if not (file.endswith(".json") or file.endswith(".txt")):
                continue
                
            # If category filter is provided, only process matching files
            if category and category not in file:
                continue
                
            file_path = os.path.join(root, file)
            try:
                if file.endswith(".json"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        urls = json.load(f)
                        # Handle both list and dictionary formats
                        if isinstance(urls, dict) and "unique_urls" in urls:
                            urls = urls["unique_urls"]
                        all_urls.update(url for url in urls if url)
                elif file.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        all_urls.update(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.warning(f"Error reading URLs from {file_path}: {e}")
                
    return all_urls

def filter_article_urls(urls: List[str], domain: str) -> List[str]:
    """
    Filter URLs to ensure they are article URLs.
    
    Args:
        urls: List of URLs to filter
        domain: Domain of the website
        
    Returns:
        Filtered list of article URLs
    """
    filtered = []
    
    # Domain-specific filtering rules
    domain_patterns = {
        "btv.com.kh": "/article/",
        "rfa.org": ["/news/", ".html"],
        "postkhmer.com": ["/politics/", "/business/", "/financial/", "/sport/"],
        "dap-news.com": ["/economic/", "/sport/", "/politic/", "/technology/", "/health/"],
        "kohsantepheapdaily.com.kh": ["/article/", ".html"],
        "news.sabay.com.kh": "/article/"
    }
    
    # Get appropriate patterns for this domain
    patterns = []
    for key, value in domain_patterns.items():
        if key in domain:
            if isinstance(value, list):
                patterns.extend(value)
            else:
                patterns.append(value)
                
    # If no specific patterns, use generic filtering
    if not patterns:
        # Generic filters to detect article URLs
        patterns = ["/article/", "/news/", ".html", "/detail/", "/story/"]
        
    # Filter URLs
    for url in urls:
        # Skip empty or non-string URLs
        if not url or not isinstance(url, str):
            continue
            
        # Check if URL contains any of the patterns
        if any(pattern in url for pattern in patterns):
            filtered.append(url)
            
    logger.info(f"Filtered {len(filtered)} article URLs out of {len(urls)} for domain '{domain}'")
    return filtered

def select_random_urls(urls: List[str], count: int) -> List[str]:
    """
    Select random URLs from the list, up to the specified count.
    
    Args:
        urls: List of URLs to select from
        count: Number of URLs to select
        
    Returns:
        List of randomly selected URLs
    """
    if len(urls) <= count:
        return urls
    return random.sample(urls, count)

def process_categories(categories: Dict[str, List[str]], args):
    """
    Process all categories and their URLs.
    
    Args:
        categories: Dictionary mapping categories to lists of URLs
        args: Command-line arguments
    """
    # Create the output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Temporary directory for intermediate results
    temp_dir = os.path.join(args.output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Override crawler save functions to use our output directory
    override_crawler_save_functions(args.output_dir)
    
    # Load any existing URLs if in resume mode
    category_urls = {category: set() for category in categories}
    if args.resume:
        logger.info("Resume mode: Loading existing URLs from output directory")
        for category in categories:
            output_file = os.path.join(args.output_dir, f"{category}.json")
            if os.path.exists(output_file):
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        existing_urls = json.load(f)
                        category_urls[category].update(existing_urls)
                        logger.info(f"Loaded {len(existing_urls)} existing URLs for {category}")
                except Exception as e:
                    logger.error(f"Error loading existing URLs for {category}: {e}")
    
    # Track crawled URLs to avoid duplicating effort
    already_crawled = {}
    
    # Process each category
    for category, urls in categories.items():
        logger.info(f"Processing category: {category} ({len(urls)} source URLs)")
        
        # Skip if we already have enough URLs for this category
        if len(category_urls[category]) >= args.urls_per_category:
            logger.info(f"Already have {len(category_urls[category])} URLs for {category}, skipping")
            continue
            
        # Randomize URLs if requested to get a better distribution
        category_source_urls = urls.copy()
        if args.randomize:
            random.shuffle(category_source_urls)
        
        # Calculate how many URLs we need from each source to reach our target
        urls_still_needed = args.urls_per_category - len(category_urls[category])
        min_urls_per_source = max(args.min_urls_per_source, urls_still_needed // max(1, len(category_source_urls)))
        logger.info(f"Need {urls_still_needed} more URLs for {category}, aiming for at least {min_urls_per_source} per source")
        
        # Process each URL for this category
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            # Submit crawling tasks for URLs that haven't been crawled yet
            future_to_url = {}
            for url in category_source_urls:
                if url in already_crawled:
                    logger.info(f"URL already crawled in another category: {url}")
                    category_urls[category].update(filter_article_urls(list(already_crawled[url]), urlparse(url).netloc))
                else:
                    future_to_url[executor.submit(crawl_url, url, category, temp_dir, min_urls_per_source)] = url
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_urls = future.result()
                    domain = urlparse(url).netloc
                    filtered_urls = filter_article_urls(list(article_urls), domain)
                    
                    # Store the crawled URLs for potential reuse in other categories
                    already_crawled[url] = set(filtered_urls)
                    
                    # Add to our collection for this category
                    category_urls[category].update(filtered_urls)
                    
                    logger.info(f"Added {len(filtered_urls)} article URLs from {url} to {category}. " +
                                f"Total in category: {len(category_urls[category])}")
                    
                    # Save intermediate results
                    intermediate_file = os.path.join(temp_dir, f"{category}_intermediate.json")
                    try:
                        save_urls_to_file(list(category_urls[category]), intermediate_file)
                        logger.info(f"Saved intermediate results to {intermediate_file}")
                    except Exception as e:
                        logger.error(f"Error saving intermediate results: {e}")
                    
                    # If we have enough URLs, move on to the next category
                    if len(category_urls[category]) >= args.urls_per_category:
                        logger.info(f"Reached target URL count for category {category}. Moving to next category.")
                        break
                    
                except Exception as e:
                    logger.error(f"Error processing {url} for category {category}: {e}")
    
    # Select random URLs up to the target count and save to JSON files
    for category, urls in category_urls.items():
        # Convert to list for random selection
        urls_list = list(urls)
        
        # Select random URLs if we have more than the target
        if len(urls_list) > args.urls_per_category:
            selected_urls = select_random_urls(urls_list, args.urls_per_category)
            logger.info(f"Selected {len(selected_urls)} random URLs from {len(urls_list)} available for {category}")
        else:
            selected_urls = urls_list
            logger.info(f"Using all {len(selected_urls)} URLs for {category}")
        
        # Save to JSON file
        output_file = os.path.join(args.output_dir, f"{category}.json")
        save_urls_to_file(selected_urls, output_file)
        logger.info(f"Saved {len(selected_urls)} URLs for category {category} to {output_file}")
    
    # Clean up temporary files if successful
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Error cleaning up temporary directory: {e}")

import os
import sys
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set
import time
import random

# Add parent directory to Python path for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.category_handler import CategoryHandler

def main():
    """Main entry point for the crawler controller."""
    args = parse_arguments()
    
    # Initialize components
    components = setup_smart_components(args)
    
    # Load categories
    categories = load_categories(args.categories_file)
    if not categories:
        logger.error("No categories found or error loading categories file.")
        return
        
    # Process categories directly
    process_categories(categories, args)
    
    logger.info("Crawling completed successfully")

if __name__ == "__main__":
    main()