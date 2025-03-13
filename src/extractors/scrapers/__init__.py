"""
Initialize the scrapers package and register all available scrapers.
"""

# Import all scrapers to register them
from . import btv_scraper
from . import postkhmer_scraper
from . import rfa_scraper
from . import dapnews_scraper
from . import sabay_scraper
from . import kohsantepheap_scraper

# Now config.SCRAPER_MAP should be populated with all scrapers
