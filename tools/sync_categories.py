#!/usr/bin/env python3
"""
Sync Category URLs

This script ensures the output/urls directory exists for storing category URL files.
"""

import os
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Main function to sync categories to directory structure."""
    categories_file = "config/categories.json"
    output_dir = "output/urls"
    
    # Check if categories file exists
    if not os.path.exists(categories_file):
        logger.error(f"Categories file not found: {categories_file}")
        return False
    
    try:
        # Load categories from file
        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        logger.info(f"Loaded {len(categories)} categories from {categories_file}")
        
        # Create main output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Ensured output directory exists: {output_dir}")
        
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
