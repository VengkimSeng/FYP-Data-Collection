"""
Scraper for Kohsantepheap website.
"""

from ..scrapers.generic_scraper import generic_scrape
from ..config import SCRAPER_MAP

def scrape_kohsantepheap(url, category):
    """
    Scrape articles from Kohsantepheap website.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dict containing article data if successful, None otherwise
    """
    return generic_scrape(url, category, "div.article-recap h1", "content-text")

# Register the scraper in the SCRAPER_MAP
SCRAPER_MAP["https://kohsantepheapdaily.com.kh"] = scrape_kohsantepheap
