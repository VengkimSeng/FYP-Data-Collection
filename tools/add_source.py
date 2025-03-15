#!/usr/bin/env python3
"""
Add Source URLs to Categories Configuration

This script helps add new source URLs to the categories.json configuration file.
"""

import os
import json
import argparse
import sys

def load_categories():
    """Load categories from configuration file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "config", "categories.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading categories config: {e}")
        return {}

def save_categories(categories):
    """Save categories to configuration file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "config", "categories.json")
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        print(f"Categories saved to {config_path}")
        return True
    except Exception as e:
        print(f"Error saving categories config: {e}")
        return False

def add_source(category, crawler, url):
    """Add a source URL for a specific crawler and category."""
    categories = load_categories()
    
    if category not in categories:
        print(f"Creating new category: {category}")
        categories[category] = {}
    
    # Handle different category storage formats
    if isinstance(categories[category], dict):
        categories[category][crawler] = url
    elif isinstance(categories[category], list):
        # Check if URL already exists
        if url in categories[category]:
            print(f"URL already exists in {category}")
            return False
        categories[category].append(url)
    else:
        print(f"Unexpected category format for {category}")
        return False
    
    return save_categories(categories)

def main():
    parser = argparse.ArgumentParser(description="Add source URL to categories")
    parser.add_argument("category", help="Category name (e.g., sport, politic)")
    parser.add_argument("crawler", help="Crawler name (e.g., postkhmer, rfanews)")
    parser.add_argument("url", help="Source URL to add")
    
    args = parser.parse_args()
    
    if add_source(args.category, args.crawler, args.url):
        print(f"Successfully added {args.url} for {args.crawler} in {args.category}")
        return 0
    else:
        print("Failed to add source URL")
        return 1

if __name__ == "__main__":
    sys.exit(main())
