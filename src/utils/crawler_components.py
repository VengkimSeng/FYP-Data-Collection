"""
CrawlerComponents - Smart components for web crawling

This module provides the container class for smart crawler components
like rate limiters, browser managers, and URL queues.
"""

class CrawlerComponents:
    """Container for smart crawler components."""
    
    def __init__(self):
        self.rate_limiter = None
        self.browser_manager = None
        self.url_queue = None
        self.quality_analyzer = None 
        self.fingerprinter = None
        self.crawler_state = None
        self.url_fetcher = None
