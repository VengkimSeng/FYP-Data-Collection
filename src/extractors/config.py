"""
Configuration settings for the article crawler.
"""

# Global constants
CHECKPOINT_FILE = "checkpoint.json"
MAX_WAIT_TIME = 40  # seconds
MAX_RETRIES = 3     # number of retries for failed operations
RETRY_DELAY = 20    # seconds between retry attempts

# Mapping of base URLs to their respective scraper functions
# (This will be populated by the scraper modules)
SCRAPER_MAP = {}
