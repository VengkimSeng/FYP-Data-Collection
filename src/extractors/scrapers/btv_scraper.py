"""
Scraper for BTV website.
"""

from ..scrapers.generic_scraper import generic_scrape
from ..config import SCRAPER_MAP

def scrape_btv(url, category):
    """
    Scrape articles from BTV website.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dict containing article data if successful, None otherwise
    """
    return generic_scrape(url, category, "h4.color", "font-size-detail.textview")

# Register the scraper in the SCRAPER_MAP
SCRAPER_MAP["https://btv.com.kh"] = scrape_btv
