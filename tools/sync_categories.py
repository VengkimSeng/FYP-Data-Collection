#!/usr/bin/env python3
"""Sync Category URLs and create required directory structure"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def setup_directory_structure():
    """Create all required directories."""
    base_dirs = [
        "src/config",
        "src/crawlers/Urls_Crawler",
        "src/utils",
        "src/tests",
        "output/articles"
    ]
    
    for dir_path in base_dirs:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

def create_empty_json_files(categories, base_path):
    """Create empty JSON files for each category."""
    for category in categories:
        json_path = os.path.join(base_path, f"{category}.json")
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            logger.info(f"Created empty JSON file: {json_path}")

def main():
    """Main function to sync categories to directory structure."""
    categories_file = "config/categories.json"
    urls_dir = "output/urls"
    test_urls_dir = "output/test_urls"
    test_results_dir = "output/test_results"
    
    # Check if categories file exists
    if not os.path.exists(categories_file):
        logger.error(f"Categories file not found: {categories_file}")
        return False
    
    try:
        # Load categories from file
        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        logger.info(f"Loaded {len(categories)} categories from {categories_file}")
        
        # Create directories and empty JSON files
        for directory in [urls_dir, test_urls_dir, test_results_dir]:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
            create_empty_json_files(categories, directory)
        
        # Log the categories that will be processed
        for category in categories:
            logger.info(f"Ready to process category: {category}")
        
        logger.info("Category sync completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing categories: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
