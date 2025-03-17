"""
Command Line Utilities

This module provides standard command line argument parsing for crawlers.
"""

import argparse
from typing import Dict, Any, Optional, List

def create_crawler_parser(crawler_name: str) -> argparse.ArgumentParser:
    """
    Create a standardized argument parser for crawlers.
    
    Args:
        crawler_name: Name of the crawler
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(description=f"{crawler_name.capitalize()} web crawler")
    
    # Common arguments for all crawlers
    parser.add_argument("--category", help="Specific category to crawl (optional)")
    parser.add_argument("--output-dir", dest="output_dir", default="output/urls",
                      help="Output directory for URL files")
    parser.add_argument("--backup-interval", dest="backup_interval", type=int, default=20,
                      help="Create backup after this many new URLs")
    
    return parser

def parse_crawler_args(crawler_name: str, custom_args: List[str] = None) -> Dict[str, Any]:
    """
    Parse command line arguments for a specific crawler with optional custom arguments.
    
    Args:
        crawler_name: Name of the crawler
        custom_args: List of additional argument definitions to add to the parser
                     Each item should be a tuple of (name, kwargs_dict)
    
    Returns:
        Dictionary with parsed arguments
    """
    parser = create_crawler_parser(crawler_name)
    
    # Add crawler-specific arguments
    if crawler_name == "btv":
        parser.add_argument("--max-pages", dest="max_pages", type=int, default=-1, 
                          help="Maximum pages to crawl (-1 for unlimited)")
    elif crawler_name == "dapnews":
        parser.add_argument("--max-pages", dest="max_pages", type=int, default=-1, 
                          help="Maximum pages to crawl (-1 for unlimited)")
    elif crawler_name == "postkhmer":
        parser.add_argument("--max-click", dest="max_click", type=int, default=-1, 
                          help="Maximum load more clicks (-1 for unlimited)")
    elif crawler_name == "rfanews" or crawler_name == "rfa":
        parser.add_argument("--max-clicks", dest="max_clicks", type=int, default=-1, 
                          help="Maximum load more clicks (-1 for unlimited)")
    elif crawler_name == "kohsantepheapdaily" or crawler_name == "kohsantepheap":
        parser.add_argument("--max-scroll", dest="max_scroll", type=int, default=-1, 
                          help="Maximum scroll attempts (-1 for unlimited)")
    elif crawler_name == "sabaynews" or crawler_name == "sabay":
        parser.add_argument("--max-pages", dest="max_pages", type=int, default=-1, 
                          help="Maximum pages to crawl (-1 for unlimited)")
        # Keep only essential options, remove redundant ones
        parser.add_argument("--categories", nargs="+", default=None,
                          help="List of categories to scrape (space-separated)")
    
    # Add any custom arguments
    if custom_args:
        for arg_name, arg_kwargs in custom_args:
            parser.add_argument(arg_name, **arg_kwargs)
    
    # Parse arguments
    args = parser.parse_args()
    return vars(args)  # Convert to dictionary

def get_categories_from_args(args: Dict[str, Any]) -> List[str]:
    """
    Get list of categories from command line arguments.
    
    Args:
        args: Dictionary of parsed arguments
    
    Returns:
        List of categories to process
    """
    from src.utils.source_manager import get_site_categories
    
    site_name = args.get("site_name", "")
    
    # If single category is specified, use it
    if "category" in args and args["category"]:
        return [args["category"]]
    
    # If categories list is specified, use it
    elif "categories" in args and args["categories"]:
        return args["categories"]
    
    # Otherwise, get all categories for the site
    else:
        return get_site_categories(site_name)
