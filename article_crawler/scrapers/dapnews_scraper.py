"""
Scraper for DAP News website.
"""

from ..scrapers.generic_scraper import generic_scrape
from ..config import SCRAPER_MAP

def scrape_dapnews(url, category):
    """
    Scrape articles from DAP News website.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dict containing article data if successful, None otherwise
    """
    return generic_scrape(url, category, "title", "content-main", is_id=True)

# Register the scraper in the SCRAPER_MAP
SCRAPER_MAP["https://dap-news.com"] = scrape_dapnews
