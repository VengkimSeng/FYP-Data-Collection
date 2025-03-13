#!/usr/bin/env python3
"""
Test script to verify that all crawlers are working correctly.
This performs a basic test of each crawler to ensure it can extract URLs.

Usage:
    python test_crawlers.py
"""

import os
import sys
import json
import logging
import importlib
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_crawlers")

# Import the master controller utilities
from master_crawler_controller import get_crawler_for_url, crawl_url

def main():
    # Load categories
    try:
        with open("categories.json", "r", encoding="utf-8") as f:
            categories = json.load(f)
    except Exception as e:
        logger.error(f"Error loading categories.json: {e}")
        return

    # Create temp directory for testing
    os.makedirs("test_output", exist_ok=True)

    # Test one URL from each domain
    tested_domains = set()
    
    for category, urls in categories.items():
        logger.info(f"Testing category: {category}")
        
        for url in urls:
            domain = urlparse(url).netloc
            if domain in tested_domains:
                continue  # Skip if we've already tested this domain
                
            crawler_name = get_crawler_for_url(url)
            if not crawler_name:
                logger.warning(f"No crawler found for {url}")
                continue
                
            logger.info(f"Testing {crawler_name} with URL: {url}")
            try:
                result = crawl_url(url, category, "test_output", min_urls_per_source=10)
                if result and len(result) > 0:
                    logger.info(f"✓ SUCCESS: {crawler_name} extracted {len(result)} URLs")
                else:
                    logger.error(f"✗ FAILED: {crawler_name} did not extract any URLs")
            except Exception as e:
                logger.error(f"✗ ERROR with {crawler_name}: {e}")
                
            # Mark this domain as tested
            tested_domains.add(domain)
                
    logger.info("Crawler tests completed")

if __name__ == "__main__":
    main()
