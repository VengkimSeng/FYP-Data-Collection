"""
Scraper for Post Khmer website.
"""

from ..scrapers.generic_scraper import generic_scrape
from ..config import SCRAPER_MAP

def scrape_postkhmer(url, category):
    """
    Scrape articles from Post Khmer website.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dict containing article data if successful, None otherwise
    """
    return generic_scrape(url, category, "div.section-article-header h2", "article-text")

# Register the scraper in the SCRAPER_MAP
SCRAPER_MAP["https://www.postkhmer.com"] = scrape_postkhmer
